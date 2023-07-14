from datetime import datetime, timedelta
from typing import Type, Union

from sqlalchemy.orm import Session

from . import models
from .models import UserSuspension


def get_user_suspension(db: Session, user_id: int) -> Union[Type[UserSuspension], None]:
    return db.query(models.UserSuspension).filter(models.UserSuspension.user_id == user_id).first()


def set_user_suspension(db: Session, user_suspension_update: Type[UserSuspension]) -> Union[Type[UserSuspension], None]:
    db_user_suspension = db.query(models.UserSuspension).\
        filter(models.UserSuspension.user_id == user_suspension_update.user_id).first()
    setattr(user_suspension_update, "release_date", user_suspension_update.release_date)
    db_user_suspension.release_date = user_suspension_update.release_date
    db.add(db_user_suspension)
    db.commit()
    db.refresh(db_user_suspension)
    return db_user_suspension


def create_user_suspension_short(db: Session, user_id: int):
    db_user_status = models.UserSuspension(
        user_id=user_id,
        release_date=datetime.now() + timedelta(days=5),
    )
    db.add(db_user_status)
    db.commit()
    return db_user_status


def create_user_suspension_indefinite(db: Session, user_id: int):
    db_user_status = models.UserSuspension(
        user_id=user_id,
        release_date=datetime.now() + timedelta(days=36525),
    )
    db.add(db_user_status)
    db.commit()
    return db_user_status
