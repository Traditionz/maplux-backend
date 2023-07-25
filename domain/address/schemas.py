from pydantic import BaseModel


class AddressBase(BaseModel):
    user_id: int | None
    street_address: str | None
    apt_suite: str | None
    city: str | None
    state_province: str | None
    postal_zip: str | None
    country: str | None

    class Config:
        orm_mode = True


class AddressCreate(AddressBase):
    pass


class Address(AddressBase):
    pass
