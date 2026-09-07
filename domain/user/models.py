from sqlalchemy import BigInteger, Boolean, Column, Date, LargeBinary, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(BigInteger, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    activated = Column(Boolean, nullable=False, default=False)
    password_salt = Column(LargeBinary, nullable=False)
    password_hashed = Column(LargeBinary, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    phone_number = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)

    user_suspension = relationship("UserSuspension", back_populates="user", uselist=False)
    address = relationship("Address", back_populates="user", uselist=False)
    user_image = relationship("UserImage", back_populates="user", uselist=False)
    confirmation_token = relationship("ConfirmationToken", back_populates="user")
