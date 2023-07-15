from typing import Union

from pydantic import BaseModel


class AddressBase(BaseModel):
    user_id: Union[int, None]
    street_address: Union[str, None]
    apt_suite: Union[str, None]
    city: Union[str, None]
    state_province: Union[str, None]
    postal_zip: Union[str, None]
    country: Union[str, None]

    class Config:
        orm_mode = True


class AddressCreate(AddressBase):
    pass


class Address(AddressBase):
    pass
