from pydantic import BaseModel

from .types import ReferenceObject
from .types import ResponseObject


class Component(BaseModel):
    """
    Holds a set of reusable objects for different aspects of the OAS.

    ref: https://swagger.io/specification/#components-object
    """

    responses: dict[str, ResponseObject | ReferenceObject] = {}
