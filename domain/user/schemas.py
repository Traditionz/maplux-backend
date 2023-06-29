from typing import Union

from pydantic import BaseModel


class UserBase(BaseModel):
    user_id: Union[int, None]
    email: str
    first_name: str
    last_name: str

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: Union[str, None]
    password_hashed: Union[str, None]
    password_salt: Union[str, None]


class User(UserBase):
    date_of_birth: Union[str, None]
    email_confirmation_number: Union[str, None]
    phone_number: Union[str, None]
