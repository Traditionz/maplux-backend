from pydantic import BaseModel
from pydantic.schema import date


class UserBaseSchema(BaseModel):
    user_id: int | None
    email: str | None
    activated: bool | None
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None
    phone_number: str | None

    class Config:
        orm_mode = True


class UserCreateSchema(UserBaseSchema):
    password: str | None
    password_salt: str | None
    password_hashed: str | None
