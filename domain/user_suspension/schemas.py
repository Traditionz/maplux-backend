from pydantic import BaseModel
from pydantic.schema import datetime


class UserSuspensionBaseSchema(BaseModel):
    user_id: int
    expiration_date: datetime

    class Config:
        orm_mode = True


class UserSuspensionCreateSchema(UserSuspensionBaseSchema):
    pass
