from sqlalchemy import BigInteger, Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class UserSuspension(Base):
    __tablename__ = "user_suspension"

    user_id = Column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    expiration_date = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="user_suspension", uselist=False)
