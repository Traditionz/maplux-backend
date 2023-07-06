from sqlalchemy.orm import Session

from domain import user, user_status
from domain.user import repository
from domain.user_status import repository
from domain.user.schemas import UserCreate


def create_user_base(db: Session,
                     new_user: UserCreate):
    user.repository.create_user(db=db, user=new_user)
    user_status.repository.create_user_status(db=db, user_id=new_user.user_id)

