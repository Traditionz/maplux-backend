from sqlalchemy.orm import Session

from .models import User
from .schemas import UserCreateInternalSchema


def create_user(db: Session, user: UserCreateInternalSchema) -> User:
    db_user = User(
        user_id=user.user_id,
        email=user.email,
        activated=user.activated,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hashed=user.password_hashed,
        password_salt=user.password_salt,
        date_of_birth=user.date_of_birth,
        phone_number=user.phone_number,
        is_admin=user.is_admin,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def activate_user(db: Session, user_id: int) -> User | None:
    db_user = get_user(db, user_id)
    if db_user is None:
        return None
    db_user.activated = True
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(
    db: Session, user_id: int, password_salt: bytes, password_hashed: bytes
) -> User | None:
    db_user = get_user(db, user_id)
    if db_user is None:
        return None
    db_user.password_salt = password_salt
    db_user.password_hashed = password_hashed
    db.commit()
    db.refresh(db_user)
    return db_user
