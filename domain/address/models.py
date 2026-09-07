from sqlalchemy import BigInteger, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from database import Base


class Address(Base):
    __tablename__ = "address"

    user_id = Column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    street_address = Column(String, nullable=False)
    apt_suite = Column(String)
    city = Column(String, nullable=False)
    state_province = Column(String, nullable=False)
    postal_zip = Column(String, nullable=False)
    country = Column(String, nullable=False)

    user = relationship("User", back_populates="address", uselist=False)
