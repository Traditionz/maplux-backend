from sqlalchemy.orm import Session

from . import models


def get_user_status(db: Session, user_id: int):
    return db.query(models.UserStatus).filter(models.UserStatus.user_id == user_id).first()


def create_user_status(db: Session, user_id: int):
    db_user_status = models.UserStatus(
        user_id=user_id,
        is_verified=False,
        is_active=False,
        is_banned=False
    )
    db.add(db_user_status)
    db.commit()
    db.refresh(db_user_status)
    return db_user_status
