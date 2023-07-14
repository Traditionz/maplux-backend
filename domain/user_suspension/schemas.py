from pydantic import BaseModel
from sqlalchemy import DateTime


class UserSuspensionBase(BaseModel):
    user_id: int
    release_date: DateTime

    class Config:
        orm_mode = True


class UserSuspensionCreate(UserSuspensionBase):
    pass


class UserSuspension(UserSuspensionBase):
    pass
