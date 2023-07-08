from pydantic import BaseModel


class UserStatusBase(BaseModel):
    user_id: int
    is_active: bool
    is_banned: bool

    class Config:
        orm_mode = True


class UserStatusCreate(UserStatusBase):
    pass


class UserStatus(UserStatusBase):
    pass
