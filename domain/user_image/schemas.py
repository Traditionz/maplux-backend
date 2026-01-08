from domain.camel_model import CamelModel


class UserImageBaseSchema(CamelModel):
    user_id: int | None
    image_ext: str


class UserImageCreateSchema(UserImageBaseSchema):
    pass

