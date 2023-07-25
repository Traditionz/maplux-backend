from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.testing.schema import Column

from database import Base


class ConfirmationToken(Base):
    __tablename__ = "confirmation_token"

    user_id = Column(Integer, ForeignKey("user.user_id"))
    token_hash = Column(String, primary_key=True)
    token_salt = Column(String)
    token_type = Column(String)
    expiration_date = Column(String)

    user = relationship("User", back_populates="confirmation_token")
