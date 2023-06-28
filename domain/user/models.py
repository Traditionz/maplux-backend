from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hashed = Column(String)
    password_salt = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(String)
    email_confirmation_token = Column(String)
    phone_number = Column(String)

    user_status = relationship("UserStatus", back_populates="user", uselist=False)
