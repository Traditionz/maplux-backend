from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base class for all models that should accept camelCase input"""
    model_config = ConfigDict(
        alias_generator=to_camel,          # snake_case → camelCase for incoming JSON
        populate_by_name=True,             # allows both snake_case and camelCase when creating model in Python
        from_attributes=True,              # still needed for ORM/from_attributes mode
        serialize_by_alias=True,
        # Optional but often useful:
        # coerce_numbers_to_str=True,
        # str_strip_whitespace=True,

    )