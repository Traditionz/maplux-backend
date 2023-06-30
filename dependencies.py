from fastapi.security import OAuth2PasswordBearer

from database import SessionLocal


def get_db():
    """ Method to configure database """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/user/login")
