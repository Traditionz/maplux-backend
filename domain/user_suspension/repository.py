from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import UserSuspension
from .schemas import UserSuspensionBaseSchema


def get_user_suspension(db: Session, user_id: int) -> UserSuspension | None:
    return db.query(UserSuspension).filter(UserSuspension.user_id == user_id).first()


def update_user_suspension(db: Session, user_suspension_update: UserSuspensionBaseSchema) -> \
        UserSuspension | None:
    db_user_suspension = db.query(UserSuspension).\
        filter(UserSuspension.user_id == user_suspension_update.user_id).first()
    setattr(user_suspension_update, "expiration_date", user_suspension_update.expiration_date)
    db_user_suspension.expiration_date = user_suspension_update.expiration_date
    db.add(db_user_suspension)
    db.commit()
    db.refresh(db_user_suspension)
    return db_user_suspension


def create_user_suspension_short(db: Session, user_id: int) -> UserSuspension:
    db_user_status = UserSuspension(
        user_id=user_id,
        release_date=datetime.now() + timedelta(days=5),
    )
    db.add(db_user_status)
    db.commit()
    return db_user_status


def create_user_suspension_indefinite(db: Session, user_id: int) -> UserSuspension:
    db_user_status = UserSuspension(
        user_id=user_id,
        release_date=datetime.now() + timedelta(days=36525),
    )
    db.add(db_user_status)
    db.commit()
    return db_user_status
