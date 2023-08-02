from pydantic import BaseModel
from pydantic.schema import date


class UserBase(BaseModel):
    user_id: int | None
    email: str | None
    activated: bool | None
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str | None
    password_salt: str | None
    password_hashed: str | None


class User(UserBase):
    phone_number: str | None
