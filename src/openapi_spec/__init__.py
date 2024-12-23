from __future__ import annotations

from pydantic import BaseModel

from .basic import Contact
from .basic import Info
from .basic import License
from .path import Operation
from .path import PathItem
from .path import Paths


class OpenAPI(BaseModel):
    """
    The root of the OpenAPI document

    ref: https://swagger.io/specification/#openapi-object
    """

    openapi: str = "3.1.0"
    info: Info
    paths: Paths = Paths({})


__all__ = list(
    {
        "OpenAPI",
        "Contact",
        "Info",
        "License",
        "Paths",
        "PathItem",
        "Operation",
    }
)
