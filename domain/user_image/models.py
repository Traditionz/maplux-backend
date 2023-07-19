from sqlalchemy import Integer, String, ForeignKey, Column
from sqlalchemy.orm import relationship

from database import Base


class UserImage(Base):
    __tablename__ = "user_image"

    user_id = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    image_ext = Column(String)

    user = relationship("User", back_populates="user_image", uselist=False)
