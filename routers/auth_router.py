import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from domain import confirmation_token, user
from domain.auth_token.schemas import TokenSchema
from domain.confirmation_token.schemas import ConfirmationTokenCreateSchema
from domain.user.models import User
from domain.user.schemas import (
    ForgotPasswordSchema,
    LoginSchema,
    PasswordResetSchema,
    RefreshSchema,
    StatusMessageSchema,
    UserCreateInternalSchema,
    UserCreateSchema,
)
from enums.confirmation_token_type import ConfirmationTokenType
from exception.UserExceptions import InvalidConfirmationTokenException, SendEmailException
from routers.deps import CurrentUserAllowUnactivated, DbSession
from security.authentication import (
    TokenType,
    authenticate_user,
    clear_auth_cookies,
    confirm_activation_token,
    decode_token,
    generate_activation_token,
    hash_password,
    issue_token_pair,
    set_auth_cookies,
)
from security.cookie import REFRESH_COOKIE
from utils.email_utils import Email
from utils.ids import generate_id
from utils.urls import build_api_url, build_client_url

router = APIRouter(tags=["auth"])

ACTIVATION_TOKEN_MAX_AGE = 1200
PASSWORD_RESET_TOKEN_MAX_AGE = 900


def _store_confirmation_token(
    db: DbSession,
    db_user: User,
    token_type: ConfirmationTokenType,
    max_age: int,
) -> str:
    confirmation_token.repository.delete_confirmation_tokens_for_user(
        db=db,
        user_id=db_user.user_id,
        token_type=token_type,
    )
    token_salt = secrets.token_urlsafe(16)
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


def _issue_auth_response(response: Response, db_user: User) -> TokenSchema:
    tokens = issue_token_pair(db_user)
    set_auth_cookies(response, tokens)
    return tokens


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=StatusMessageSchema)
async def register(new_user: UserCreateSchema, db: DbSession):
    db_user = user.repository.get_user_by_email(db=db, email=new_user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    internal_user = UserCreateInternalSchema(
        user_id=generate_id(),
        email=new_user.email,
        activated=False,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        date_of_birth=new_user.date_of_birth,
        phone_number=new_user.phone_number,
        password_hash=hash_password(new_user.password),
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
        url = build_api_url(f"/verify-email/{token}")
        await Email(db_user, url).send_activation_email()
    except SendEmailException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Account created but activation email could not be sent. Please try resending."
            ),
        ) from exc

    return StatusMessageSchema(status="success", message="Activation email sent.")


@router.post("/login", response_model=TokenSchema)
async def login(payload: LoginSchema, response: Response, db: DbSession):
    db_user = authenticate_user(db=db, email=payload.email, password=payload.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_auth_response(response, db_user)


@router.post("/token", response_model=TokenSchema)
async def login_with_form(
    response: Response,
    db: DbSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    db_user = authenticate_user(db=db, email=form_data.username, password=form_data.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_auth_response(response, db_user)


@router.post("/refresh", response_model=TokenSchema)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: DbSession,
    payload: RefreshSchema | None = None,
):
    refresh_token = (payload.refresh_token if payload is not None else None) or request.cookies.get(
        REFRESH_COOKIE
    )
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    db_user = user.repository.get_user(db, user_id=token_data.user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_auth_response(response, db_user)


@router.post("/logout", response_model=StatusMessageSchema)
async def logout(response: Response):
    clear_auth_cookies(response)
    return StatusMessageSchema(status="success", message="Logged out.")


@router.post("/verify-email/resend", response_model=StatusMessageSchema)
async def resend_verification_email(current_user: CurrentUserAllowUnactivated, db: DbSession):
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
        url = build_api_url(f"/verify-email/{token}")
        await Email(current_user, url).send_activation_email()
    except SendEmailException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error sending activation email.",
        ) from exc
    return StatusMessageSchema(status="success", message="Activation email sent.")


@router.get("/verify-email/{token}", response_model=StatusMessageSchema)
async def verify_email(token: str, db: DbSession):
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
    return StatusMessageSchema(status="success", message="Account activated.")


@router.post("/password/forgot", response_model=StatusMessageSchema)
async def forgot_password(payload: ForgotPasswordSchema, db: DbSession):
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


@router.post("/password/reset", response_model=StatusMessageSchema)
async def reset_password(payload: PasswordResetSchema, db: DbSession):
    db_token = confirmation_token.repository.get_confirmation_token(
        db=db,
        token=payload.token,
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
            token=payload.token,
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
            token=payload.token,
            token_type=ConfirmationTokenType.PASSWORD_RESET,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is expired or invalid.",
        )

    updated_user = user.repository.update_user_password(
        db=db,
        user_id=current_user.user_id,
        password_hash=hash_password(payload.password),
    )
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reset user password.",
        )
    confirmation_token.repository.delete_confirmation_token(
        db=db,
        token=payload.token,
        token_type=ConfirmationTokenType.PASSWORD_RESET,
    )
    return StatusMessageSchema(status="success", message="Password has been reset.")
