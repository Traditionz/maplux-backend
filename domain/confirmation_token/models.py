from sqlalchemy import BigInteger, Column, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base
from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationToken(Base):
    __tablename__ = "confirmation_token"
    __table_args__ = (
        UniqueConstraint("user_id", "token_type", name="uq_confirmation_token_user_type"),
    )

    user_id = Column(BigInteger, ForeignKey("user.user_id"), nullable=False)
    token = Column(String, primary_key=True)
    token_salt = Column(String, nullable=False)
    token_type = Column(Enum(ConfirmationTokenType), nullable=False)
    max_age = Column(Integer, nullable=False)

    user = relationship("User", back_populates="confirmation_token", uselist=False)
