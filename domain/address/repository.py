from sqlalchemy.orm import Session

from .models import Address
from .schemas import AddressCreateSchema


def get_address(db: Session, user_id: int) -> Address | None:
    return db.query(Address).filter(Address.user_id == user_id).first()


def create_address(db: Session, user_id: int, address: AddressCreateSchema) -> Address:
    db_address = Address(
        user_id=user_id,
        street_address=address.street_address,
        apt_suite=address.apt_suite,
        city=address.city,
        state_province=address.state_province,
        postal_zip=address.postal_zip,
        country=address.country,
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address


def update_address(db: Session, user_id: int, new_address: AddressCreateSchema) -> Address | None:
    db_address = get_address(db, user_id)
    if db_address is None:
        return None
    db_address.street_address = new_address.street_address
    db_address.apt_suite = new_address.apt_suite
    db_address.city = new_address.city
    db_address.state_province = new_address.state_province
    db_address.postal_zip = new_address.postal_zip
    db_address.country = new_address.country
    db.commit()
    db.refresh(db_address)
    return db_address
