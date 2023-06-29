import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from snowflake import SnowflakeGenerator
from sqlalchemy.orm import Session

from dependencies import get_db
from domain.user import repository, schemas

router = APIRouter()


@router.post("/user/", response_model=schemas.UserBase)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = repository.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    id_generator = SnowflakeGenerator(42)
    user.user_id = next(id_generator)
    user.password_salt = bcrypt.gensalt(12)
    user.password_hashed = bcrypt.hashpw(user.password.encode("utf-8"), user.password_salt)
    return repository.create_user(db=db, user=user)


@router.get("/user/{user_id}", response_model=schemas.UserBase)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
