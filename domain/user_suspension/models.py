from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserSuspension(Base):
    __tablename__ = "user_suspension"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    expiration_date: Mapped[datetime] = mapped_column(DateTime)

    user = relationship("User", back_populates="user_suspension", uselist=False)
