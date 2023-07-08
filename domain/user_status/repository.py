from typing import Type, Union

from sqlalchemy.orm import Session

from . import models
from .models import UserStatus


def get_user_status(db: Session, user_id: int) -> Union[Type[UserStatus], None]:
    return db.query(models.UserStatus).filter(models.UserStatus.user_id == user_id).first()


def set_user_status(db: Session, new_user_status: Type[UserStatus]) -> Union[Type[UserStatus], None]:
    db_user_status: Union[Type[UserStatus], None] = db.query(models.UserStatus).\
        filter(models.UserStatus.user_id == new_user_status.user_id).first()
    db_user_status.is_active = new_user_status.is_active
    db.add(db_user_status)
    db.commit()
    return db_user_status


def create_user_status(db: Session, user_id: int):
    db_user_status = models.UserStatus(
        user_id=user_id,
        is_active=False,
        is_banned=False
    )
    db.add(db_user_status)
    db.commit()
    db.refresh(db_user_status)
    return db_user_status
