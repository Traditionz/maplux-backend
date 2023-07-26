from pydantic import BaseModel

from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationTokenBase(BaseModel):
    user_id: int | None
    token: str
    token_salt: str
    token_type: ConfirmationTokenType

    class Config:
        orm_mode = True


class ConfirmationTokenCreate(ConfirmationTokenBase):
    pass


class ConfirmationToken(ConfirmationTokenBase):
    pass
