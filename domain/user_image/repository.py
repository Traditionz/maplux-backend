from sqlalchemy.orm import Session

from .models import UserImage
from .schemas import UserImageCreateSchema


def create_user_image(db: Session, user_id: int, user_image: UserImageCreateSchema) -> UserImage:
    db_user_image = UserImage(
        user_id=user_id,
        image_ext=user_image.image_ext,
    )
    db.add(db_user_image)
    db.commit()
    db.refresh(db_user_image)
    return db_user_image


def get_user_image(db: Session, user_id: int) -> UserImage | None:
    return db.query(UserImage).filter(UserImage.user_id == user_id).first()


def update_user_image(
    db: Session, user_id: int, user_image: UserImageCreateSchema
) -> UserImage | None:
    db_user_image = get_user_image(db, user_id)
    if db_user_image is None:
        return None
    db_user_image.image_ext = user_image.image_ext
    db.commit()
    db.refresh(db_user_image)
    return db_user_image
