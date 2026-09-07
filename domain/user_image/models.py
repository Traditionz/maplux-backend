from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserImage(Base):
    __tablename__ = "user_image"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), primary_key=True)
    image_ext: Mapped[str] = mapped_column(String)

    user = relationship("User", back_populates="user_image", uselist=False)
