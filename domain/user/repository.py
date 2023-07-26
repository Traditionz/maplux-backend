from typing import Type

from sqlalchemy.orm import Session

from . import models, schemas
from .schemas import User


def create_user(db: Session, user: schemas.UserCreate) -> User:
    db_user = models.User(
        user_id=user.user_id,
        email=user.email,
        activated=user.activated,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hashed=user.password_hashed,
        password_salt=user.password_salt,
        date_of_birth=user.date_of_birth
    )
    db.add(db_user)
    db.commit()
    return db_user


def get_user(db: Session, user_id: int) -> Type[User] | None:
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Type[User] | None:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[User]]:
    return db.query(models.User).offset(skip).limit(limit).all()


def update_user_activate(db: Session, user_update: Type[schemas.User]) -> Type[User]:
    db_user = db.query(models.User). \
        filter(models.User.user_id == user_update.user_id).first()
    setattr(db_user, "activated", user_update.activated)
    db.commit()
    return user_update
