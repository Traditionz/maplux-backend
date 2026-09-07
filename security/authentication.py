from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from fastapi import Depends, HTTPException
from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired, URLSafeTimedSerializer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from config import settings
from database import get_db
from domain import user, user_suspension
from domain.auth_token.schemas import TokenDataSchema, TokenSchema
from domain.confirmation_token.models import ConfirmationToken
from domain.user.models import User
from exception.UserExceptions import InvalidConfirmationTokenException
from security.cookie import ACCESS_COOKIE, REFRESH_COOKIE, BearerOrCookieAuth

oauth2_scheme = BearerOrCookieAuth()
password_hasher = PasswordHash((BcryptHasher(),))

# Precomputed bcrypt hash so missing-user lookups take a similar amount of time.
_DUMMY_PASSWORD_HASH = "$2b$12$BdMVCRkRZ1gEXAbdyPCFkOVvSmbgjW9TXnkLfd9r4O6wEvAX2goQO"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(plain_password, password_hash)
    except (TypeError, ValueError, UnknownHashError):
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
    password_hash = (
        db_user.password_hash
        if db_user is not None and db_user.password_hash
        else _DUMMY_PASSWORD_HASH
    )
    password_ok = verify_password(password, password_hash)
    if db_user is None or not password_ok:
        return None
    return db_user


def encode_token(payload: dict, expires: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(UTC) + expires
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: int, expires: timedelta | None = None) -> str:
    lifetime = expires if expires is not None else timedelta(minutes=settings.jwt_expire_minutes)
    return encode_token({"sub": str(user_id), "typ": TokenType.ACCESS.value}, lifetime)


def create_refresh_token(*, user_id: int, expires: timedelta | None = None) -> str:
    lifetime = expires if expires is not None else timedelta(days=settings.jwt_refresh_expire_days)
    return encode_token({"sub": str(user_id), "typ": TokenType.REFRESH.value}, lifetime)


def issue_token_pair(db_user: User) -> TokenSchema:
    access_token = create_access_token(user_id=db_user.user_id)
    refresh_token = create_refresh_token(user_id=db_user.user_id)
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


def set_auth_cookies(response: Response, tokens: TokenSchema) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens.access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    for key in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(
            key=key,
            path="/",
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )


def decode_token(token: str, *, expected_type: TokenType) -> TokenDataSchema:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    token_type = payload.get("typ")
    if not isinstance(subject, str) or not subject or token_type != expected_type.value:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenDataSchema(user_id=user_id, token_type=expected_type.value)


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
    token_data = decode_token(token, expected_type=TokenType.ACCESS)
    current_user = user.repository.get_user(db, user_id=token_data.user_id)
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


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user
