from datetime import datetime

from domain.camel_model import CamelModel


class UserSuspensionBaseSchema(CamelModel):
    user_id: int
    expiration_date: datetime


class UserSuspensionCreateSchema(UserSuspensionBaseSchema):
    pass
