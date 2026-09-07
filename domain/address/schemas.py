from pydantic import Field

from domain.camel_model import CamelModel


class AddressCreateSchema(CamelModel):
    street_address: str = Field(min_length=1, max_length=200)
    apt_suite: str | None = None
    city: str = Field(min_length=1, max_length=100)
    state_province: str = Field(min_length=1, max_length=100)
    postal_zip: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=1, max_length=100)


class AddressBaseSchema(AddressCreateSchema):
    user_id: int
