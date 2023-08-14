from pydantic import BaseModel


class UserImageBaseSchema(BaseModel):
    user_id: int | None
    image_ext: str

    class Config:
        orm_mode = True


class UserImageCreateSchema(UserImageBaseSchema):
    pass

