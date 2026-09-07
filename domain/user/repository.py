from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User
from .schemas import UserCreateInternalSchema, UserUpdateSchema


def create_user(db: Session, user: UserCreateInternalSchema) -> User:
    db_user = User(
        user_id=user.user_id,
        email=user.email,
        activated=user.activated,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hash=user.password_hash,
        date_of_birth=user.date_of_birth,
        phone_number=user.phone_number,
        is_admin=user.is_admin,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> User | None:
    return db.execute(select(User).where(User.user_id == user_id)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return list(db.execute(select(User).offset(skip).limit(limit)).scalars().all())


def activate_user(db: Session, user_id: int) -> User | None:
    db_user = get_user(db, user_id)
    if db_user is None:
        return None
    db_user.activated = True
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(db: Session, user_id: int, password_hash: str) -> User | None:
    db_user = get_user(db, user_id)
    if db_user is None:
        return None
    db_user.password_hash = password_hash
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_profile(db: Session, user_id: int, updates: UserUpdateSchema) -> User | None:
    db_user = get_user(db, user_id)
    if db_user is None:
        return None
    data = updates.model_dump(exclude_unset=True, by_alias=False)
    for field, value in data.items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user
