from sqlalchemy.orm import Session

from .models import Address
from .schemas import AddressCreateSchema, AddressBaseSchema


def get_address(db: Session, user_id: int) -> Address | None:
    return db.query(Address).filter(Address.user_id == user_id).first()


def update_address(db: Session, new_address: AddressBaseSchema) -> Address | None:
    db_address = db.query(Address).filter(Address.user_id == new_address.user_id).first()
    setattr(db_address, "street_address", new_address.street_address)
    setattr(db_address, "apt_suite", new_address.apt_suite)
    setattr(db_address, "city", new_address.city)
    setattr(db_address, "state_province", new_address.state_province)
    setattr(db_address, "postal_zip", new_address.postal_zip)
    setattr(db_address, "country", new_address.country)
    db.commit()
    db.refresh(db_address)
    return db_address


def create_address(db: Session, address: AddressCreateSchema) -> Address:
    db_address = Address(
        user_id=address.user_id,
        street_address=address.street_address,
        apt_suite=address.apt_suite,
        city=address.city,
        state_province=address.state_province,
        postal_zip=address.postal_zip,
        country=address.country
    )
    db.add(db_address)
    db.commit()
    return db_address
