from typing import Type

from sqlalchemy.orm import Session

from . import models, schemas
from .models import ConfirmationToken


def create_confirmation_token(db: Session, confirmation_token: schemas.ConfirmationTokenCreate) -> ConfirmationToken:
    db_confirmation_token = models.ConfirmationToken(
        user_id=confirmation_token.user_id,
        token_hash=confirmation_token.token_hash,
        token_salt=confirmation_token.token_salt,
        token_type=confirmation_token.token_type,
        expiration_date=confirmation_token.expiration_date
    )
    db.add(db_confirmation_token)
    db.commit()
    return db_confirmation_token


def get_confirmation_token(db: Session, token_hash: str) -> Type[ConfirmationToken] | None:
    return db.query(models.ConfirmationToken).filter(models.ConfirmationToken.token_hash == token_hash).first()
