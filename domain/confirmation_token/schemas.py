from pydantic import BaseModel

from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationTokenBaseSchema(BaseModel):
    user_id: int | None
    token: str
    token_salt: str
    token_type: ConfirmationTokenType
    max_age: int

    class Config:
        orm_mode = True


class ConfirmationTokenCreateSchema(ConfirmationTokenBaseSchema):
    pass
