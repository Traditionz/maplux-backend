from datetime import timedelta, datetime
from typing import Union, Type

import bcrypt
import jwt
from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from config import SECRET_KEY, ALGORITHM
from database import get_db
from domain import user
from domain.token.schemas import TokenData
from domain.user import repository
from domain.user.models import User
from security.cookie import OAuth2PasswordBearerCookie

oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="/auth/user/login")


def get_hashed_password(password: bytes, password_salt: bytes) -> bytes:
    return bcrypt.hashpw(password, password_salt)


def check_password(password: bytes, password_hashed: bytes) -> bool:
    return bcrypt.checkpw(password, password_hashed)


def authenticate_user(db, email, password) -> Union[Type[User], None]:
    db_user = repository.get_user_by_email(db=db, email=email)
    if db_user is None:
        return None
    if not check_password(password.encode('utf-8'), db_user.password_hashed):
        return None
    return db_user


def create_access_token(data: dict, expires: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires:
        expire = datetime.utcnow() + expires
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    # to_encode.update({"exp": expire.strftime("%m/%d/%Y")})
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Type[User]:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get('sub')
    if email is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token_data = TokenData(email=email)

    current_user = user.repository.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    return current_user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
