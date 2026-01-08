from domain.camel_model import CamelModel
from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationTokenBaseSchema(CamelModel):
    user_id: int | None
    token: str
    token_salt: str
    token_type: ConfirmationTokenType
    max_age: int


class ConfirmationTokenCreateSchema(ConfirmationTokenBaseSchema):
    pass
