from sqlalchemy import Integer, ForeignKey, String, Enum, Column
from sqlalchemy.orm import relationship

from database import Base
from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationToken(Base):
    __tablename__ = "confirmation_token"

    user_id = Column(Integer, ForeignKey("user.user_id"))
    token = Column(String, primary_key=True)
    token_salt = Column(String)
    token_type = Column(Enum(ConfirmationTokenType))

    user = relationship("User", back_populates="confirmation_token", uselist=False)
