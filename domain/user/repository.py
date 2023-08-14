from typing import Type

from sqlalchemy.orm import Session

from .models import User
from .schemas import UserCreateSchema, UserBaseSchema


def create_user(db: Session, user: UserCreateSchema) -> User:
    db_user = User(
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


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[User]]:
    return db.query(User).offset(skip).limit(limit).all()


def update_user_activate(db: Session, user_update: UserBaseSchema) -> User | None:
    db_user = db.query(User).filter(User.user_id == user_update.user_id).first()
    setattr(db_user, "activated", user_update.activated)
    db.commit()
    return db_user


def update_user_password(db: Session, user_update: UserCreateSchema) -> User | None:
    db_user = db.query(User).filter(User.user_id == user_update.user_id).first()
    setattr(db_user, "password_salt", user_update.password_salt)
    setattr(db_user, "password_hashed", user_update.password_hashed)
    db.commit()
    return db_user
