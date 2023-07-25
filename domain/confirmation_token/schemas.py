from typing import Union

from pydantic import BaseModel
from pydantic.schema import datetime

from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationTokenBase(BaseModel):
    user_id: Union[int, None]
    token_hash: str
    token_salt: str
    token_type: ConfirmationTokenType
    expiration_date: datetime

    class Config:
        orm_mode = True


class ConfirmationTokenCreate(ConfirmationTokenBase):
    pass


class ConfirmationToken(ConfirmationTokenBase):
    pass
