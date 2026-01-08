from sqlalchemy.orm import Session

from enums.confirmation_token_type import ConfirmationTokenType
from .models import ConfirmationToken
from .schemas import ConfirmationTokenCreateSchema


def create_confirmation_token(db: Session, confirmation_token: ConfirmationTokenCreateSchema) -> ConfirmationToken:
    db_confirmation_token = ConfirmationToken(
        user_id=confirmation_token.user_id,
        token=confirmation_token.token,
        token_salt=confirmation_token.token_salt,
        token_type=confirmation_token.token_type,
        max_age=confirmation_token.max_age
    )
    db.add(db_confirmation_token)
    db.commit()
    return db_confirmation_token


def get_confirmation_token(db: Session, token_type: ConfirmationTokenType) -> \
        ConfirmationToken | None:
    return db.query(ConfirmationToken).filter(ConfirmationToken.token_type == token_type).first()


def delete_confirmation_token(db: Session, token_type: ConfirmationTokenType) -> None:
    db_confirmation_token = db.query(ConfirmationToken).filter(ConfirmationToken.token_type == token_type).first()
    db.delete(db_confirmation_token)
    db.commit()

# def get_confirmation_token(db: Session, token: str, token_type: ConfirmationTokenType) -> \
#         Type[ConfirmationToken] | None:
#     return db.query(models.ConfirmationToken).filter(
#         models.ConfirmationToken.token.like(token),
#         models.ConfirmationToken.token_type.like(token_type)
#     ).first()
