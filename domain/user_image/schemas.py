from pydantic import Field, field_validator

from domain.camel_model import CamelModel

ALLOWED_IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp", "gif"})


class UserImageCreateSchema(CamelModel):
    image_ext: str = Field(min_length=1, max_length=10)

    @field_validator("image_ext")
    @classmethod
    def normalize_ext(cls, value: str) -> str:
        ext = value.lower().lstrip(".")
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError("Unsupported image extension.")
        return ext


class UserImageBaseSchema(UserImageCreateSchema):
    user_id: int
