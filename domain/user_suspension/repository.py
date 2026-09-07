from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from .models import UserSuspension
from .schemas import UserSuspensionBaseSchema


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_user_suspension(db: Session, user_id: int) -> UserSuspension | None:
    return db.query(UserSuspension).filter(UserSuspension.user_id == user_id).first()


def update_user_suspension(
    db: Session, user_suspension_update: UserSuspensionBaseSchema
) -> UserSuspension | None:
    db_user_suspension = get_user_suspension(db, user_suspension_update.user_id)
    if db_user_suspension is None:
        return None
    db_user_suspension.expiration_date = user_suspension_update.expiration_date
    db.commit()
    db.refresh(db_user_suspension)
    return db_user_suspension


def _upsert_suspension(db: Session, user_id: int, expiration_date: datetime) -> UserSuspension:
    db_user_suspension = get_user_suspension(db, user_id)
    if db_user_suspension is None:
        db_user_suspension = UserSuspension(user_id=user_id, expiration_date=expiration_date)
        db.add(db_user_suspension)
    else:
        db_user_suspension.expiration_date = expiration_date
    db.commit()
    db.refresh(db_user_suspension)
    return db_user_suspension


def create_user_suspension_short(db: Session, user_id: int) -> UserSuspension:
    return _upsert_suspension(db, user_id, _utc_now() + timedelta(days=5))


def create_user_suspension_indefinite(db: Session, user_id: int) -> UserSuspension:
    return _upsert_suspension(db, user_id, _utc_now() + timedelta(days=36525))


def is_suspension_active(suspension: UserSuspension | None) -> bool:
    if suspension is None:
        return False
    expiration = suspension.expiration_date
    if expiration.tzinfo is not None:
        expiration = expiration.replace(tzinfo=None)
    return expiration > _utc_now()
