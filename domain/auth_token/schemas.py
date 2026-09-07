from pydantic import BaseModel

from domain.camel_model import CamelModel


class TokenSchema(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenDataSchema(BaseModel):
    user_id: int
    token_type: str
