from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password_hashed: str
    password_salt: str


class User(UserBase):
    user_id: int
    date_of_birth: str
    email_confirmation_number: str
    phone_number: str
