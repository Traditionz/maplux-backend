from datetime import timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm
from snowflake import SnowflakeGenerator
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from database import get_db
from domain import user
from domain.user import repository
from domain.user.schemas import UserBase, UserCreate, User
from security.authentication import create_access_token, authenticate_user, get_current_active_user

router = APIRouter()


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


# @router.post('/user/login2', response_model=Token)
# async def login_user(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     db_user = authenticate_user(db, data.username, data.password)
#
#     if db_user is None:
#         raise HTTPException(status_code=401, detail="Incorrect username or password.")
#
#     access_token = create_access_token(data=dict(sub=data.username), expires=timedelta(days=365))
#
#     return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/user/login')
async def login_user2(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(db, form.username, form.password)

    if db_user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    access_token = create_access_token(data=dict(sub=form.username), expires=timedelta(days=365))

    response = RedirectResponse(url="/auth/home", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
    )
    return response


@router.get('/user/me/', response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get('/home')
async def home():
    return ["Hello"]
