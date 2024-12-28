from pydantic import BaseModel

from .types import ReferenceObject
from .types import ResponseObject
from .types import SchemaObject
from .types import SecuritySchemeObject


class Component(BaseModel):
    """
    Holds a set of reusable objects for different aspects of the OAS.

    ref: https://swagger.io/specification/#components-object
    """

    responses: dict[str, ResponseObject | ReferenceObject] = {}
    schemas: dict[str, SchemaObject] | None = None
    securitySchemes: dict[str, SecuritySchemeObject] | None = None
