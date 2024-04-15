from sqlalchemy import Column, Integer, String, Boolean, Date, LargeBinary
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    activated = Column(Boolean)
    password_salt = Column(LargeBinary)
    password_hashed = Column(LargeBinary)
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    phone_number = Column(String)

    user_suspension = relationship("UserSuspension", back_populates="user", uselist=False)
    address = relationship("Address", back_populates="user", uselist=False)
    user_image = relationship("UserImage", back_populates="user", uselist=False)
    confirmation_token = relationship("ConfirmationToken", back_populates="user")
