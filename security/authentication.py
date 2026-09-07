from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired, URLSafeTimedSerializer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from config import settings
from database import get_db
from domain import user, user_suspension
from domain.auth_token.schemas import TokenDataSchema
from domain.confirmation_token.models import ConfirmationToken
from domain.user.models import User
from exception.UserExceptions import InvalidConfirmationTokenException
from security.cookie import OAuth2PasswordBearerCookie

oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="/auth/login/")

# Precomputed bcrypt hash so missing-user lookups take a similar amount of time.
_DUMMY_PASSWORD_HASH = b"$2b$12$kb..kFbBjij2ZnJpeXTp0OziKUrD9768P/URCPFW0rT9CGVj8jJeK"

COOKIE_NAME = "Authorization"


def get_hashed_password(password: bytes, password_salt: bytes) -> bytes:
    return bcrypt.hashpw(password, password_salt)


def hash_password(plain_password: str) -> tuple[bytes, bytes]:
    password_salt = bcrypt.gensalt(12)
    password_hashed = get_hashed_password(plain_password.encode("utf-8"), password_salt)
    return password_salt, password_hashed


def check_password(password: bytes, password_hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password, password_hashed)
    except (TypeError, ValueError):
        return False


def generate_activation_token(email: str, token_salt: str) -> str:
    serializer = URLSafeTimedSerializer(settings.activate_secret_key)
    return serializer.dumps(email, salt=token_salt)


def confirm_activation_token(activation_token: ConfirmationToken) -> str:
    try:
        serializer = URLSafeTimedSerializer(settings.activate_secret_key)
        return serializer.loads(
            activation_token.token,
            salt=activation_token.token_salt,
            max_age=activation_token.max_age,
        )
    except (BadSignature, SignatureExpired, BadTimeSignature) as exc:
        raise InvalidConfirmationTokenException("Token is expired or invalid.") from exc


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    db_user = user.repository.get_user_by_email(db=db, email=email)
    password_hashed = (
        db_user.password_hashed
        if db_user is not None and db_user.password_hashed
        else _DUMMY_PASSWORD_HASH
    )
    password_ok = check_password(password.encode("utf-8"), password_hashed)
    if db_user is None or not password_ok:
        return None
    return db_user


def create_access_token(data: dict, expires: timedelta | None = None) -> str:
    to_encode = data.copy()
    lifetime = expires if expires is not None else timedelta(minutes=settings.jwt_expire_minutes)
    expire = datetime.now(UTC) + lifetime
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def set_auth_cookie(response: Response, access_token: str) -> None:
    max_age = settings.jwt_expire_minutes * 60
    response.set_cookie(
        key=COOKIE_NAME,
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=max_age,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def decode_access_token(token: str) -> TokenDataSchema:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("sub")
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenDataSchema(email=email)


def check_banned_user(current_user: User, db: Session) -> None:
    db_user_suspension = user_suspension.repository.get_user_suspension(
        db=db, user_id=current_user.user_id
    )
    if user_suspension.repository.is_suspension_active(db_user_suspension):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="User is suspended.",
        )


def check_current_active_user(current_user: User) -> None:
    if not current_user.activated:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Account is not activated.",
        )


async def _get_user_from_token(token: str, db: Session, *, require_activated: bool) -> User:
    token_data = decode_access_token(token)
    current_user = user.repository.get_user_by_email(db, email=token_data.email)
    if current_user is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    check_banned_user(current_user=current_user, db=db)
    if require_activated:
        check_current_active_user(current_user=current_user)
    return current_user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    return await _get_user_from_token(token, db, require_activated=True)


async def get_current_user_allow_unactivated(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    return await _get_user_from_token(token, db, require_activated=False)
