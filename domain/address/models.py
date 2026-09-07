from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Address(Base):
    __tablename__ = "address"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    street_address: Mapped[str] = mapped_column(String)
    apt_suite: Mapped[str | None] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    state_province: Mapped[str] = mapped_column(String)
    postal_zip: Mapped[str] = mapped_column(String)
    country: Mapped[str] = mapped_column(String)

    user = relationship("User", back_populates="address", uselist=False)
