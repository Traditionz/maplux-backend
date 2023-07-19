from typing import Union

from pydantic import BaseModel


class UserImageBase(BaseModel):
    user_id: Union[int, None]
    image_ext: str

    class Config:
        orm_mode = True


class UserImageCreate(UserImageBase):
    pass


class UserImage(UserImageBase):
    pass
