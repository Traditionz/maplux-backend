from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from enums.confirmation_token_type import ConfirmationTokenType


class ConfirmationToken(Base):
    __tablename__ = "confirmation_token"
    __table_args__ = (
        UniqueConstraint("user_id", "token_type", name="uq_confirmation_token_user_type"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"))
    token: Mapped[str] = mapped_column(String, primary_key=True)
    token_salt: Mapped[str] = mapped_column(String)
    token_type: Mapped[ConfirmationTokenType] = mapped_column(Enum(ConfirmationTokenType))
    max_age: Mapped[int] = mapped_column(Integer)

    user = relationship("User", back_populates="confirmation_token", uselist=False)
