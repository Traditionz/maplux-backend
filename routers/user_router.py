import base64
from datetime import timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from snowflake import SnowflakeGenerator
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response

from database import get_db
from domain import user, user_suspension, address, user_image
from domain.address.schemas import AddressCreate, Address
from domain.token.schemas import Token
from domain.user.schemas import UserBase, UserCreate, User
from domain.user_image.schemas import UserImageBase, UserImageCreate, UserImage
from domain.user import repository
from domain.user_suspension import repository
from domain.address import repository
from domain.user_image import repository

from exception.UserExceptions import SendActivationEmailException, InvalidActivationTokenException
from security.authentication import create_access_token, authenticate_user, get_current_active_user, BasicAuth, \
    basic_auth, generate_activation_token, confirm_activation_token
from utils.email_utils import Email

router = APIRouter()


@router.post('/user/', status_code=status.HTTP_201_CREATED)
async def create_user(new_user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(db=db, email=new_user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    id_generator = SnowflakeGenerator(42)
    new_user.user_id = next(id_generator)
    new_user.activated = False
    new_user.password_salt = bcrypt.gensalt(12)
    new_user.password_hashed = bcrypt.hashpw(new_user.password.encode('utf-8'), new_user.password_salt)
    try:
        user.repository.create_user(db=db, user=new_user)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error creating user. Please try again later.")
    try:
        token = generate_activation_token(new_user=new_user)
        url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/auth/user/activate/{token}"
        await Email(new_user, url, [EmailStr(new_user.email)]).send_activation_email()
    except SendActivationEmailException:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error sending activation email.")

    return {
        "status": "success",
        "message": "Activation token successfully sent to your email"
    }


@router.get('/user/activate/{token}')
async def activate_user(token: str, db: Session = Depends(get_db)):
    try:
        # TODO: expire old activation email (store in db)
        email = confirm_activation_token(token)
        current_user = user.repository.get_user_by_email(db=db, email=email)
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Invalid activation token.')
        current_user.activated = True
        current_user = user.repository.update_user_activate(db=db, user_update=current_user)
        if not current_user.activated:
            raise Exception
        # TODO: redirect to You're almost done page if address is empty.
        return {
            "status": "success",
            "message": "Account verified successfully"
        }
    except InvalidActivationTokenException:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Token is expired or invalid.")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not activate user.")


@router.post("/token/", response_model=Token)
async def route_login_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(db=db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data=dict(sub=db_user.email), expires=timedelta(days=365)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get('/user/login/')
async def login_user(auth: BasicAuth = Depends(basic_auth), db: Session = Depends(get_db)):
    if not auth:
        response = Response(headers={"WWW-Authenticate": "Basic"}, status_code=401)
        return response

    decoded = base64.b64decode(auth).decode("ascii")
    username, _, password = decoded.partition(":")

    db_user = authenticate_user(db, username, password)

    if db_user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    access_token = create_access_token(data=dict(sub=username), expires=timedelta(days=365))

    response = Response()
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True
    )
    return response


# TODO: separate confirmation tokens (see comment in create user)
#  to another table and make forget password endpoint

@router.get('/user/logout/')
async def logout_user():
    response = Response()
    response.delete_cookie("Authorization")
    return response


@router.post('/user/address/create/')
async def create_new_user_address(new_address: AddressCreate,
                                  current_user: User = Depends(get_current_active_user),
                                  db: Session = Depends(get_db)):
    new_address.user_id = current_user.user_id
    address.repository.create_address(db=db, address=new_address)
    return {
        "status": "success",
        "message": f"{current_user.user_id} has created their address"
    }


@router.put('/user/address/update/')
async def update_new_user_address(new_address: Address,
                                  current_user: User = Depends(get_current_active_user),
                                  db: Session = Depends(get_db)):
    new_address.user_id = current_user.user_id
    address.repository.update_address(db=db, address=new_address)
    return {
        "status": "success",
        "message": f"{current_user.user_id} has created their address"
    }


@router.post('/user/profile/image/create/')
async def create_new_user_image(new_user_image: UserImageCreate,
                                current_user: User = Depends(get_current_active_user),
                                db: Session = Depends(get_db)):
    # TODO: Front end will validate image ext and upload to s3
    new_user_image.user_id = current_user.user_id
    user_image.repository.create_user_image(db=db, user_image=new_user_image)
    return {
        "status": "success",
        "message": f"{new_user_image.user_id} has created their user image"
    }


@router.put('/user/profile/image/update/', response_model=UserImageBase)
async def update_user_image(user_image_update: UserImage,
                            current_user: User = Depends(get_current_active_user),
                            db: Session = Depends(get_db)):
    user_image_update.user_id = current_user.user_id
    user_image.repository.update_user_image(db=db, user_image=user_image_update)
    return {
        "status": "success",
        "message": f"{user_image_update.user_id} has updated their user image"
    }


@router.get('/user/{user_id}', response_model=UserBase)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return db_user


@router.get('/user/me/', response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get('/home')
async def home():
    return ["Hello"]


@router.get('/user/suspend/temporary/{user_id}')
async def suspend_user_temporary(user_id: int, db: Session = Depends(get_db)):
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found.')
    user_suspension.repository.create_user_suspension_short(db=db, user_id=user_id)
    return {
        "status": "success",
        "message": f"{user_id} has been suspended for 5 days."
    }
