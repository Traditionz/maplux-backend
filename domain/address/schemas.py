from domain.camel_model import CamelModel


class AddressBaseSchema(CamelModel):
    user_id: int | None
    street_address: str | None
    apt_suite: str | None
    city: str | None
    state_province: str | None
    postal_zip: str | None
    country: str | None

class AddressCreateSchema(AddressBaseSchema):
    pass
