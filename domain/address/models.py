from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Address(Base):
    __tablename__ = "address"

    user_id = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    street_address = Column(String)
    apt_suite = Column(String)
    city = Column(String)
    state_province = Column(String)
    postal_zip = Column(String)
    country = Column(String)

    user = relationship("User", back_populates="address", uselist=False)
