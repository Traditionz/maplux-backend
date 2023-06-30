from typing import Union, Type

from sqlalchemy.orm import Session

from . import models, schemas
from .models import User


def get_user(db: Session, user_id: int) -> Union[Type[User], None]:
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Union[Type[User], None]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[User]]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> User:
    db_user = models.User(
        user_id=user.user_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hashed=user.password_hashed,
        password_salt=user.password_salt
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
