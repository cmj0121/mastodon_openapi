from __future__ import annotations

from enum import StrEnum
from enum import auto

from pydantic import BaseModel
from pydantic import Field


class BuildInType(StrEnum):
    boolean = auto()
    integer = auto()
    number = auto()
    string = auto()


class SchemaObject(BaseModel):
    """
    The Schema Object allows the definition of input and output data types.

    ref: https://swagger.io/specification/#schema-object
    """

    type: str
    description: str | None = None
    nullable: bool | None = None
    items: list[SchemaObject] | None = None
    properties: dict[str, SchemaObject] | None = None


class MediaTypeObject(BaseModel):
    """
    Each Media Type Object provides schema and examples for the media type identified
    by its key.

    ref: https://swagger.io/specification/#media-type-object
    """

    schema_object: SchemaObject = Field(..., alias="schema")


class ReferenceObject(BaseModel):
    """
    A simple object to allow referencing other components in the OpenAPI Description,
    internally and externally.

    ref: https://swagger.io/specification/#reference-object
    """

    ref: str = Field(..., alias="$ref")
    description: str | None = None


class ResponseObject(BaseModel):
    """
    Describes a single response from an API operation, including design-time, static
    links to operations based on the response.

    ref: https://swagger.io/specification/#response-object
    """

    description: str
    content: dict[str, MediaTypeObject]
