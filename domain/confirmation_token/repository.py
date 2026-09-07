from sqlalchemy.orm import Session

from enums.confirmation_token_type import ConfirmationTokenType

from .models import ConfirmationToken
from .schemas import ConfirmationTokenCreateSchema


def create_confirmation_token(
    db: Session, confirmation_token: ConfirmationTokenCreateSchema
) -> ConfirmationToken:
    db_confirmation_token = ConfirmationToken(
        user_id=confirmation_token.user_id,
        token=confirmation_token.token,
        token_salt=confirmation_token.token_salt,
        token_type=confirmation_token.token_type,
        max_age=confirmation_token.max_age,
    )
    db.add(db_confirmation_token)
    db.commit()
    db.refresh(db_confirmation_token)
    return db_confirmation_token


def get_confirmation_token(
    db: Session, token: str, token_type: ConfirmationTokenType
) -> ConfirmationToken | None:
    return (
        db.query(ConfirmationToken)
        .filter(
            ConfirmationToken.token == token,
            ConfirmationToken.token_type == token_type,
        )
        .first()
    )


def delete_confirmation_tokens_for_user(
    db: Session, user_id: int, token_type: ConfirmationTokenType
) -> int:
    deleted = (
        db.query(ConfirmationToken)
        .filter(
            ConfirmationToken.user_id == user_id,
            ConfirmationToken.token_type == token_type,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def delete_confirmation_token(db: Session, token: str, token_type: ConfirmationTokenType) -> int:
    deleted = (
        db.query(ConfirmationToken)
        .filter(
            ConfirmationToken.token == token,
            ConfirmationToken.token_type == token_type,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted
