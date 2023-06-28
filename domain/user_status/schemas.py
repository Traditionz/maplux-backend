from pydantic import BaseModel


class UserStatusBase(BaseModel):
    user_id: int
    is_verified: bool
    is_active: bool
    is_banned: bool


class UserStatusCreate(UserStatusBase):
    pass


class UserStatus(UserStatusBase):
    pass

    class Config:
        orm_mode = True
