from sqlalchemy.orm import Session

from .models import UserImage
from .schemas import UserImageCreateSchema, UserImageBaseSchema


def create_user_image(db: Session, user_image: UserImageCreateSchema) -> UserImage:
    db_user_image = UserImage(
        user_id=user_image.user_id,
        image_ext=user_image.image_ext
    )
    db.add(db_user_image)
    db.commit()
    return db_user_image


def get_user_image(db: Session, user_id: int) -> UserImage | None:
    return db.query(UserImage).filter(UserImage.user_id == user_id).first()


def update_user_image(db: Session, user_image: UserImageBaseSchema) -> UserImage | None:
    db_user_image = db.query(UserImage). \
        filter(UserImage.user_id == user_image.user_id).first()
    setattr(db_user_image, "image_ext", user_image.image_ext)
    db.commit()
    return db_user_image
