import base64
from datetime import timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import EmailStr
from snowflake import SnowflakeGenerator
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse, Response

from database import get_db
from domain import user, user_status
from domain.token.schemas import Token
from domain.user import repository
from domain.user_status import repository
from domain.user.schemas import UserBase, UserCreate, User
from exception.UserExceptions import SendActivationEmailException
from security.authentication import create_access_token, authenticate_user, get_current_active_user, BasicAuth, \
    basic_auth, generate_activation_token
from utils.email_utils import Email

router = APIRouter()


@router.post('/user/', status_code=status.HTTP_201_CREATED)
async def create_user(new_user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(db=db, email=new_user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered.')
    id_generator = SnowflakeGenerator(42)
    new_user.user_id = next(id_generator)
    new_user.password_salt = bcrypt.gensalt(12)
    new_user.password_hashed = bcrypt.hashpw(new_user.password.encode('utf-8'), new_user.password_salt)
    try:
        user.repository.create_user(db=db, user=new_user)
        user_status.repository.create_user_status(db=db, user_id=new_user.user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Error creating user. Please try again later.')
    try:
        token = generate_activation_token(new_user=new_user)
        url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/auth/user/activate/{token}"
        await Email(new_user, url, [EmailStr(new_user.email)]).send_activation_email()
    except SendActivationEmailException:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Error sending activation email.')

    return {'status': 'success', 'message': 'Activation token successfully sent to your email'}


@router.get('/user/{user_id}', response_model=UserBase)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found.')
    return db_user


@router.get('/user/login/', response_model=Token)
async def login_user(auth: BasicAuth = Depends(basic_auth), db: Session = Depends(get_db)):
    if not auth:
        response = Response(headers={"WWW-Authenticate": "Basic"}, status_code=401)
        return response

    decoded = base64.b64decode(auth).decode("ascii")
    username, _, password = decoded.partition(":")

    db_user = authenticate_user(db, username, password)

    if db_user is None:
        raise HTTPException(status_code=401, detail='Incorrect username or password.')

    access_token = create_access_token(data=dict(sub=username), expires=timedelta(days=365))

    # return {'access_token': access_token, 'token_type': 'bearer'}

    response = Response()
    response.set_cookie(key='access_token', value=f'Bearer {access_token}', httponly=True)
    return response


@router.get('/user/logout/')
async def login_user():
    response = RedirectResponse(url='/')
    response.delete_cookie("access_token")
    return response


@router.get('/user/me/', response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get('/home')
async def home():
    return ["Hello"]
