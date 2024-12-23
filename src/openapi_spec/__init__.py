from __future__ import annotations

from pydantic import BaseModel

from .basic import Contact
from .basic import Info
from .basic import License
from .component import Component
from .path import Operation
from .path import PathItem
from .path import Paths
from .path import Responses
from .types import MediaTypeObject
from .types import ReferenceObject
from .types import ResponseObject
from .types import SchemaObject


class OpenAPI(BaseModel):
    """
    The root of the OpenAPI document

    ref: https://swagger.io/specification/#openapi-object
    """

    openapi: str = "3.1.0"
    info: Info
    paths: Paths = Paths({})
    components: Component | None = None


__all__ = list(
    {
        "OpenAPI",
        "Contact",
        "Info",
        "License",
        "Paths",
        "PathItem",
        "Operation",
        "Responses",
        "MediaTypeObject",
        "ResponseObject",
        "ReferenceObject",
        "SchemaObject",
        "Component",
    }
)
