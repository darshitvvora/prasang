"""Base models: camelCase JSON on the wire, snake_case in Python."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class RequestModel(CamelModel):
    """Request bodies reject unknown fields so typos surface as 422s."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Page[T](CamelModel):
    items: list[T]
    total: int
    page: int
    size: int
