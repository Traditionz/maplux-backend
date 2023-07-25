from sqlalchemy import Integer, ForeignKey, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.testing.schema import Column

from database import Base
from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationToken(Base):
    __tablename__ = "confirmation_token"

    user_id = Column(Integer, ForeignKey("user.user_id"))
    token_hash = Column(String, primary_key=True)
    token_salt = Column(String)
    token_type = Column(Enum(ConfirmationTokenType))
    expiration_date = Column(String)

    user = relationship("User", back_populates="confirmation_token")
