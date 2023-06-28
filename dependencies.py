from database import SessionLocal


def get_db():
    """ Method to configure database """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
