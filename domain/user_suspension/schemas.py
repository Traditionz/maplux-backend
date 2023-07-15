from pydantic import BaseModel
from pydantic.schema import datetime


class UserSuspensionBase(BaseModel):
    user_id: int
    release_date: datetime

    class Config:
        orm_mode = True


class UserSuspensionCreate(UserSuspensionBase):
    pass


class UserSuspension(UserSuspensionBase):
    pass
