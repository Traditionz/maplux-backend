from datetime import date

from pydantic import EmailStr, Field, field_validator

from domain.camel_model import CamelModel


def _age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


class StatusMessageSchema(CamelModel):
    status: str
    message: str


class UserPublicSchema(CamelModel):
    user_id: int
    first_name: str
    last_name: str


class UserBaseSchema(CamelModel):
    user_id: int
    email: EmailStr
    activated: bool
    first_name: str
    last_name: str
    date_of_birth: date
    phone_number: str
    is_admin: bool = False


class UserCreateSchema(CamelModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    phone_number: str = Field(min_length=7, max_length=32)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("Date of birth cannot be in the future.")
        if _age_on(value, today) < 18:
            raise ValueError("User must be at least 18 years old.")
        return value


class UserCreateInternalSchema(CamelModel):
    user_id: int
    email: EmailStr
    activated: bool = False
    first_name: str
    last_name: str
    date_of_birth: date
    phone_number: str
    password_salt: bytes
    password_hashed: bytes
    is_admin: bool = False


class PasswordResetSchema(CamelModel):
    password: str = Field(min_length=8, max_length=72)


class ForgotPasswordSchema(CamelModel):
    email: EmailStr
