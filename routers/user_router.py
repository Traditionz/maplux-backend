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
from domain import user, user_suspension, address, user_image, confirmation_token
from domain.address import repository
from domain.address.schemas import AddressCreateSchema
from domain.auth_token.schemas import TokenSchema
from domain.confirmation_token import repository
from domain.confirmation_token.schemas import ConfirmationTokenCreateSchema
from domain.user import repository
from domain.user.schemas import UserBaseSchema, UserCreateSchema
from domain.user_image import repository
from domain.user_image.schemas import UserImageBaseSchema, UserImageCreateSchema
from domain.user_suspension import repository
from enums.confirmation_token_type import ConfirmationTokenType
from exception.UserExceptions import SendActivationEmailException, InvalidConfirmationTokenException
from security.authentication import create_access_token, authenticate_user, get_current_user, \
    generate_activation_token, confirm_activation_token
from utils.email_utils import Email

router = APIRouter()


@router.post('/users/', status_code=status.HTTP_201_CREATED)
async def create_user(request: Request, new_user: UserCreateSchema, db: Session = Depends(get_db)):
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user. Please try again later."
        )
    try:
        token_salt = bcrypt.gensalt(12).decode('utf-8')
        token = generate_activation_token(
            current_user=new_user,
            token_salt=token_salt
        )
        activation_token = ConfirmationTokenCreateSchema(
            user_id=new_user.user_id,
            token=token,
            token_salt=token_salt,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
            max_age=1200
        )
        confirmation_token.repository.create_confirmation_token(
            db=db,
            confirmation_token=activation_token
        )
        url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/auth/user/activate/{token}"
        await Email(new_user, url, [EmailStr(new_user.email)]).send_activation_email()
    except SendActivationEmailException:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error sending activation email.")

    return {
        "status": "success",
        "message": f"Activation token successfully sent to {new_user.user_id}'s email."
    }


@router.put('/users/me/activate/resend/')
async def resend_activation_token(request: Request,
                                  current_user: UserBaseSchema = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    if current_user.activated:
        return {
            "status": "failed",
            "message": f"User {current_user.user_id} is already activated."
        }
    db_token = confirmation_token.repository.get_confirmation_token(
        db=db,
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION
    )
    if db_token is not None:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
    token_salt = bcrypt.gensalt(12).decode('utf-8')
    token = generate_activation_token(
        current_user=current_user,
        token_salt=token_salt
    )
    activation_token = ConfirmationTokenCreateSchema(
        user_id=current_user.user_id,
        token=token,
        token_salt=token_salt,
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
        max_age=1200
    )
    confirmation_token.repository.create_confirmation_token(
        db=db,
        confirmation_token=activation_token
    )
    url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/auth/user/activate/{token}"
    await Email(current_user, url, [EmailStr(current_user.email)]).send_activation_email()
    return {
        "status": "success",
        "message": f"Activation token successfully has been resent to {current_user.user_id}'s email."
    }


@router.get('/users/me/activate/{token}')
async def activate_user(token: str, db: Session = Depends(get_db)):
    try:
        db_token = confirmation_token.repository.get_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        if db_token is None:
            return {
                "status": "failed",
                "message": "Account activation token is expired or invalid."
            }
        if db_token.token != token:
            return {
                "status": "failed",
                "message": "Account activation token is invalid."
            }
        email = confirm_activation_token(db_token)
        current_user = user.repository.get_user_by_email(
            db=db,
            email=email
        )
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Invalid activation token.'
            )

        user_update = UserBaseSchema()
        user_update.user_id = current_user.user_id
        user_update.activated = True

        current_user = user.repository.update_user_activate(
            db=db,
            user_update=user_update
        )
        if not current_user.activated:
            raise Exception
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        # TODO: redirect to You're almost done page if address is empty.
        return {
            "status": "success",
            "message": f"User {current_user.user_id} activated."
        }
    except InvalidConfirmationTokenException:
        confirmation_token.repository.delete_confirmation_token(
            db=db, token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token is expired or invalid."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not activate user."
        )


@router.get("/users/me/password/forgot/{email}")
async def forgot_password(request: Request, email: str, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(
        db=db,
        email=email
    )
    if db_user is None:
        return {
            "status": "success",
            "message": "The password reset email has been sent."
        }
    db_token = confirmation_token.repository.get_confirmation_token(
        db=db,
        token_type=ConfirmationTokenType.PASSWORD_RESET
    )
    if db_token is not None:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.PASSWORD_RESET
        )
    token_salt = bcrypt.gensalt(12).decode('utf-8')
    token = generate_activation_token(
        current_user=db_user,
        token_salt=token_salt
    )
    password_reset_token = ConfirmationTokenCreateSchema(
        user_id=db_user.user_id,
        token=token,
        token_salt=token_salt,
        token_type=ConfirmationTokenType.PASSWORD_RESET,
        max_age=900
    )
    confirmation_token.repository.create_confirmation_token(
        db=db,
        confirmation_token=password_reset_token
    )
    # TODO: reset password will redirect to a webpage
    url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/auth/pages/user/password/reset/{token}"
    await Email(db_user, url, [EmailStr(db_user.email)]).send_password_reset_email()
    return {
        "status": "success",
        "message": "The password reset email has been sent."
    }


@router.patch('/users/me/password/reset/{token}')
async def reset_password(token: str, user_update: UserCreateSchema, db: Session = Depends(get_db)):
    try:
        db_token = confirmation_token.repository.get_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.PASSWORD_RESET
        )
        if db_token is None:
            return {
                "status": "failed",
                "message": "Password reset URL is expired or invalid."
            }
        if db_token.token != token:
            return {
                "status": "failed",
                "message": "Password reset URL is invalid."
            }
        email = confirm_activation_token(db_token)
        current_user = user.repository.get_user_by_email(
            db=db,
            email=email
        )
        old_password_salt = current_user.password_salt
        old_password_hash = current_user.password_hashed
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Invalid password reset URL.'
            )
        user_update.user_id = current_user.user_id
        user_update.password_salt = bcrypt.gensalt(12)
        user_update.password_hashed = bcrypt.hashpw(user_update.password.encode('utf-8'), current_user.password_salt)

        current_user = user.repository.update_user_password(
            db=db,
            user_update=user_update
        )
        if current_user.password_hashed is None or current_user.password_salt is None:
            current_user.password_salt = old_password_salt
            current_user.password_hashed = old_password_hash
            user.repository.update_user_password(
                db=db,
                user_update=current_user
            )
            raise Exception
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.PASSWORD_RESET
        )
        return {
            "status": "success",
            "message": f"User {current_user.user_id} has reset their password."
        }
    except InvalidConfirmationTokenException:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token_type=ConfirmationTokenType.PASSWORD_RESET
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset URL is expired or invalid."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reset user password."
        )


@router.post("/auth_token/", response_model=TokenSchema)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password
    )
    if not db_user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password."
        )
    access_token = create_access_token(
        data=dict(sub=db_user.email), expires=timedelta(days=365)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get('/users/me/logout/')
async def logout_user():
    response = Response()
    response.delete_cookie("Authorization")
    return response


@router.post('/users/me/address/create/')
async def create_new_user_address(new_address: AddressCreateSchema,
                                  current_user: UserBaseSchema = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    new_address.user_id = current_user.user_id
    db_address = address.repository.get_address(
        db=db,
        user_id=current_user.user_id
    )
    if db_address is not None:
        return {
            "status": "failed",
            "message": f"{current_user.user_id} has already created their address."
        }
    address.repository.create_address(
        db=db,
        address=new_address
    )
    return {
        "status": "success",
        "message": f"{current_user.user_id} has created their address."
    }


@router.put('/users/me/address/update/')
async def update_new_user_address(new_address: AddressCreateSchema,
                                  current_user: UserBaseSchema = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    new_address.user_id = current_user.user_id
    address.repository.update_address(
        db=db,
        new_address=new_address
    )
    return {
        "status": "success",
        "message": f"{current_user.user_id} has updated their address."
    }


@router.post('/users/profile/image/create/')
async def create_new_user_image(new_user_image: UserImageCreateSchema,
                                current_user: UserBaseSchema = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    # TODO: Front end will validate image ext and upload to s3
    new_user_image.user_id = current_user.user_id
    db_user_image = user_image.repository.get_user_image(
        db=db,
        user_id=current_user.user_id
    )
    if db_user_image is not None:
        return {
            "status": "failed",
            "message": f"{current_user.user_id} has already created their user image."
        }
    user_image.repository.create_user_image(
        db=db,
        user_image=new_user_image
    )
    return {
        "status": "success",
        "message": f"{new_user_image.user_id} has created their user image."
    }


@router.put('/users/me/profile/image/update/')
async def update_user_image(user_image_update: UserImageBaseSchema,
                            current_user: UserBaseSchema = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    user_image_update.user_id = current_user.user_id
    user_image.repository.update_user_image(
        db=db,
        user_image=user_image_update
    )
    return {
        "status": "success",
        "message": f"{user_image_update.user_id} has updated their user image."
    }


@router.get('/user/{user_id}', response_model=UserBaseSchema)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user.repository.get_user(
        db=db,
        user_id=user_id
    )
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )
    return db_user


@router.get('/users/me/', response_model=UserBaseSchema)
async def read_user_me(current_user: UserBaseSchema = Depends(get_current_user)):
    return current_user


@router.get('/home')
async def home():
    return ["Hello"]


@router.get('/users/{user_id}/suspend/temporary/')
async def suspend_user_temporary(user_id: int, db: Session = Depends(get_db)):
    db_user = user.repository.get_user(
        db=db,
        user_id=user_id
    )
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail='User not found.'
        )
    user_suspension.repository.create_user_suspension_short(
        db=db,
        user_id=user_id
    )
    return {
        "status": "success",
        "message": f"{user_id} has been suspended for 5 days."
    }
