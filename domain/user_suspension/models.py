from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from database import Base


class UserSuspension(Base):
    __tablename__ = "user_suspension"

    user_id = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    release_date = Column(DateTime)

    user = relationship("User", back_populates="user_suspension", uselist=False)
