from pydantic import BaseModel

from domain.camel_model import CamelModel


class TokenSchema(CamelModel):
    access_token: str
    token_type: str


class TokenDataSchema(BaseModel):
    email: str
