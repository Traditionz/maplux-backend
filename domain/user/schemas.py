from typing import Union

from pydantic import BaseModel


class UserBase(BaseModel):
    user_id: Union[int, None]
    email: Union[str, None]
    activated: Union[bool, None]
    first_name: Union[str, None]
    last_name: Union[str, None]
    date_of_birth: Union[str, None]

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: Union[str, None]
    password_hashed: Union[str, None]
    password_salt: Union[str, None]


class User(UserBase):
    phone_number: Union[str, None]
