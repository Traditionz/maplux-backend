import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from domain import address, confirmation_token, user, user_image, user_suspension
from domain.address.schemas import AddressCreateSchema
from domain.auth_token.schemas import TokenSchema
from domain.confirmation_token.schemas import ConfirmationTokenCreateSchema
from domain.user.models import User
from domain.user.schemas import (
    ForgotPasswordSchema,
    PasswordResetSchema,
    StatusMessageSchema,
    UserBaseSchema,
    UserCreateInternalSchema,
    UserCreateSchema,
    UserPublicSchema,
)
from domain.user_image.schemas import UserImageCreateSchema
from enums.confirmation_token_type import ConfirmationTokenType
from exception.UserExceptions import InvalidConfirmationTokenException, SendEmailException
from security.authentication import (
    authenticate_user,
    clear_auth_cookie,
    confirm_activation_token,
    create_access_token,
    generate_activation_token,
    get_current_user,
    get_current_user_allow_unactivated,
    hash_password,
    set_auth_cookie,
)
from utils.email_utils import Email
from utils.ids import generate_id
from utils.urls import build_api_url, build_client_url

router = APIRouter()

ACTIVATION_TOKEN_MAX_AGE = 1200
PASSWORD_RESET_TOKEN_MAX_AGE = 900


def _store_confirmation_token(
    db: Session,
    db_user: User,
    token_type: ConfirmationTokenType,
    max_age: int,
) -> str:
    confirmation_token.repository.delete_confirmation_tokens_for_user(
        db=db,
        user_id=db_user.user_id,
        token_type=token_type,
    )
    token_salt = bcrypt.gensalt(12).decode("utf-8")
    token = generate_activation_token(email=db_user.email, token_salt=token_salt)
    confirmation_token.repository.create_confirmation_token(
        db=db,
        confirmation_token=ConfirmationTokenCreateSchema(
            user_id=db_user.user_id,
            token=token,
            token_salt=token_salt,
            token_type=token_type,
            max_age=max_age,
        ),
    )
    return token


@router.post(
    "/users/",
    status_code=status.HTTP_201_CREATED,
    response_model=StatusMessageSchema,
)
async def create_user(new_user: UserCreateSchema, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(db=db, email=new_user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    password_salt, password_hashed = hash_password(new_user.password)
    internal_user = UserCreateInternalSchema(
        user_id=generate_id(),
        email=new_user.email,
        activated=False,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        date_of_birth=new_user.date_of_birth,
        phone_number=new_user.phone_number,
        password_salt=password_salt,
        password_hashed=password_hashed,
    )
    try:
        db_user = user.repository.create_user(db=db, user=internal_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        ) from exc

    try:
        token = _store_confirmation_token(
            db=db,
            db_user=db_user,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
            max_age=ACTIVATION_TOKEN_MAX_AGE,
        )
        url = build_api_url(f"/users/me/activate/{token}")
        await Email(db_user, url).send_activation_email()
    except SendEmailException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Account created but activation email could not be sent. Please try resending."
            ),
        ) from exc

    return StatusMessageSchema(
        status="success",
        message="Activation email sent.",
    )


@router.put(
    "/users/me/activate/resend/",
    response_model=StatusMessageSchema,
)
async def resend_activation_token(
    current_user: User = Depends(get_current_user_allow_unactivated),
    db: Session = Depends(get_db),
):
    if current_user.activated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account is already activated.",
        )
    try:
        token = _store_confirmation_token(
            db=db,
            db_user=current_user,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
            max_age=ACTIVATION_TOKEN_MAX_AGE,
        )
        url = build_api_url(f"/users/me/activate/{token}")
        await Email(current_user, url).send_activation_email()
    except SendEmailException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error sending activation email.",
        ) from exc
    return StatusMessageSchema(
        status="success",
        message="Activation email sent.",
    )


@router.get(
    "/users/me/activate/{token}",
    response_model=StatusMessageSchema,
)
async def activate_user(token: str, db: Session = Depends(get_db)):
    db_token = confirmation_token.repository.get_confirmation_token(
        db=db,
        token=token,
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
    )
    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account activation token is expired or invalid.",
        )
    try:
        email = confirm_activation_token(db_token)
    except InvalidConfirmationTokenException as exc:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token=token,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account activation token is expired or invalid.",
        ) from exc

    current_user = user.repository.get_user_by_email(db=db, email=email)
    if current_user is None:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token=token,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account activation token is expired or invalid.",
        )

    activated_user = user.repository.activate_user(db=db, user_id=current_user.user_id)
    if activated_user is None or not activated_user.activated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not activate user.",
        )
    confirmation_token.repository.delete_confirmation_token(
        db=db,
        token=token,
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
    )
    return StatusMessageSchema(
        status="success",
        message="Account activated.",
    )


@router.post(
    "/users/me/password/forgot/",
    response_model=StatusMessageSchema,
)
async def forgot_password(payload: ForgotPasswordSchema, db: Session = Depends(get_db)):
    db_user = user.repository.get_user_by_email(db=db, email=payload.email)
    if db_user is not None:
        try:
            token = _store_confirmation_token(
                db=db,
                db_user=db_user,
                token_type=ConfirmationTokenType.PASSWORD_RESET,
                max_age=PASSWORD_RESET_TOKEN_MAX_AGE,
            )
            url = build_client_url(f"/password/reset/{token}")
            await Email(db_user, url).send_password_reset_email()
        except SendEmailException:
            pass
    return StatusMessageSchema(
        status="success",
        message="If that email is registered, a password reset email has been sent.",
    )


@router.patch(
    "/users/me/password/reset/{token}",
    response_model=StatusMessageSchema,
)
async def reset_password(
    token: str, user_update: PasswordResetSchema, db: Session = Depends(get_db)
):
    db_token = confirmation_token.repository.get_confirmation_token(
        db=db,
        token=token,
        token_type=ConfirmationTokenType.PASSWORD_RESET,
    )
    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is expired or invalid.",
        )
    try:
        email = confirm_activation_token(db_token)
    except InvalidConfirmationTokenException as exc:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token=token,
            token_type=ConfirmationTokenType.PASSWORD_RESET,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is expired or invalid.",
        ) from exc

    current_user = user.repository.get_user_by_email(db=db, email=email)
    if current_user is None:
        confirmation_token.repository.delete_confirmation_token(
            db=db,
            token=token,
            token_type=ConfirmationTokenType.PASSWORD_RESET,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is expired or invalid.",
        )

    password_salt, password_hashed = hash_password(user_update.password)
    updated_user = user.repository.update_user_password(
        db=db,
        user_id=current_user.user_id,
        password_salt=password_salt,
        password_hashed=password_hashed,
    )
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reset user password.",
        )
    confirmation_token.repository.delete_confirmation_token(
        db=db,
        token=token,
        token_type=ConfirmationTokenType.PASSWORD_RESET,
    )
    return StatusMessageSchema(
        status="success",
        message="Password has been reset.",
    )


@router.post("/login/", response_model=TokenSchema)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    db_user = authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": db_user.email})
    set_auth_cookie(response, access_token)
    return TokenSchema(access_token=access_token, token_type="bearer")


@router.post("/users/me/logout/", response_model=StatusMessageSchema)
async def logout_user(response: Response):
    clear_auth_cookie(response)
    return StatusMessageSchema(status="success", message="Logged out.")


@router.post("/users/me/address/", response_model=StatusMessageSchema)
async def create_new_user_address(
    new_address: AddressCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_address = address.repository.get_address(db=db, user_id=current_user.user_id)
    if db_address is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Address already exists.",
        )
    address.repository.create_address(db=db, user_id=current_user.user_id, address=new_address)
    return StatusMessageSchema(status="success", message="Address created.")


@router.put("/users/me/address/", response_model=StatusMessageSchema)
async def update_new_user_address(
    new_address: AddressCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_address = address.repository.update_address(
        db=db,
        user_id=current_user.user_id,
        new_address=new_address,
    )
    if db_address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )
    return StatusMessageSchema(status="success", message="Address updated.")


@router.post("/users/me/profile/image/", response_model=StatusMessageSchema)
async def create_new_user_image(
    new_user_image: UserImageCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user_image = user_image.repository.get_user_image(db=db, user_id=current_user.user_id)
    if db_user_image is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User image already exists.",
        )
    user_image.repository.create_user_image(
        db=db,
        user_id=current_user.user_id,
        user_image=new_user_image,
    )
    return StatusMessageSchema(status="success", message="User image created.")


@router.put("/users/me/profile/image/", response_model=StatusMessageSchema)
async def update_user_image(
    user_image_update: UserImageCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user_image = user_image.repository.update_user_image(
        db=db,
        user_id=current_user.user_id,
        user_image=user_image_update,
    )
    if db_user_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User image not found.",
        )
    return StatusMessageSchema(status="success", message="User image updated.")


@router.get("/users/me/", response_model=UserBaseSchema)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users/{user_id}", response_model=UserPublicSchema)
async def get_user(
    user_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return db_user


@router.get("/home")
async def home():
    return ["Hello"]


@router.post(
    "/users/{user_id}/suspend/temporary/",
    response_model=StatusMessageSchema,
)
async def suspend_user_temporary(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user_suspension.repository.create_user_suspension_short(db=db, user_id=user_id)
    return StatusMessageSchema(
        status="success",
        message="User has been suspended for 5 days.",
    )
