from typing import Union, Type

from sqlalchemy.orm import Session

from . import models, schemas
from .models import Address


def get_address(db: Session, user_id: int) -> Union[Type[Address], None]:
    return db.query(models.Address).filter(models.Address.user_id == user_id).first()


def update_address(db: Session, address: schemas.Address) -> Union[Type[Address], None]:
    db_address = db.query(models.Address). \
        filter(models.Address.user_id == address.user_id).first()
    setattr(db_address, "street_address", address.street_address)
    setattr(db_address, "apt_suite", address.street_address)
    setattr(db_address, "city", address.street_address)
    setattr(db_address, "state_province", address.street_address)
    setattr(db_address, "postal_zip", address.street_address)
    setattr(db_address, "country", address.street_address)
    db.commit()
    db.refresh(db_address)
    return db_address


def create_address(db: Session, address: schemas.AddressCreate) -> Address:
    address = models.Address(
        user_id=address.user_id,
        street_address=address.street_address,
        apt_suite=address.apt_suite,
        city=address.city,
        state_province=address.state_province,
        postal_zip=address.postal_zip,
        country=address.country
    )
    db.add(address)
    db.commit()
    return address
