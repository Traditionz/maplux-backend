from pydantic import BaseModel


class UserImageBase(BaseModel):
    user_id: int | None
    image_ext: str

    class Config:
        orm_mode = True


class UserImageCreate(UserImageBase):
    pass


class UserImage(UserImageBase):
    pass
