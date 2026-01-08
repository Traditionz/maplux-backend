from datetime import date

from domain.camel_model import CamelModel


class UserBaseSchema(CamelModel):
    user_id: int | None = None
    email: str | None
    activated: bool | None
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None
    phone_number: str | None


class UserCreateSchema(UserBaseSchema):
    password: str | None
    password_salt: bytes | None = None
    password_hashed: bytes | None = None
