from sqlalchemy import Boolean, Column, Integer, ForeignKey
from sqlalchemy.orm import Mapped, relationship

from database import Base


class UserStatus(Base):
    __tablename__ = "user_status"

    user_id: Mapped[int] = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    is_verified = Column(Boolean)
    is_active = Column(Boolean)
    is_banned = Column(Boolean)

    user = relationship("User", back_populates="user_status", uselist=False)
