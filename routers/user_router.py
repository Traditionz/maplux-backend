from datetime import timedelta, datetime
from typing import Union, Type

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from snowflake import SnowflakeGenerator
from sqlalchemy.orm import Session

from config import ALGORITHM, SECRET_KEY
from dependencies import get_db, oauth2_scheme
from domain import user
from domain.token.schemas import Token, TokenData
from domain.user import repository
from domain.user.models import User
from domain.user.schemas import UserBase, UserCreate, User

router = APIRouter()


def get_hashed_password(password: bytes, password_salt: bytes) -> bytes:
    return bcrypt.hashpw(password, password_salt)


def check_password(password: bytes, password_hashed: bytes) -> bool:
    return bcrypt.checkpw(password, password_hashed)


def authenticate_user(db, data) -> Union[Type[User], None]:
    db_user = repository.get_user_by_email(db=db, email=data.username)
    if db_user is None:
        return None
    if not check_password(data.password.encode('utf-8'), db_user.password_hashed):
        return None
    return db_user


def create_access_token(data: dict, expires: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires:
        expire = datetime.utcnow() + expires
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"expire": expire.strftime("%m/%d/%Y")})
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


@router.post('/user/', response_model=UserBase)
async def create_user(new_user: UserCreate, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(db=db, email=new_user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered.')
    id_generator = SnowflakeGenerator(42)
    new_user.user_id = next(id_generator)
    new_user.password_salt = bcrypt.gensalt(12)
    new_user.password_hashed = bcrypt.hashpw(new_user.password.encode("utf-8"), new_user.password_salt)
    return repository.create_user(db=db, user=new_user)


@router.get('/user/{user_id}', response_model=UserBase)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found.')
    return db_user


@router.post('/user/login', response_model=Token)
async def login_user(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(db, data)

    if db_user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    access_token = create_access_token(data=dict(sub=data.username), expires=timedelta(days=365))

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/user/me/', response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user
