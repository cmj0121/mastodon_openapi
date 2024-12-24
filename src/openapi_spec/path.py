from pydantic import BaseModel
from pydantic import RootModel

from .types import ParameterObject
from .types import ReferenceObject
from .types import ResponseObject


class Responses(RootModel[dict[int, ResponseObject | ReferenceObject]]):
    """
    A container for the expected responses of an operation.

    ref: https://swagger.io/specification/#response-object
    """


class Operation(BaseModel):
    """
    Describes a single API operation on a path.

    ref: https://swagger.io/specification/#operation-object
    """

    tags: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    deprecated: bool | None = None
    parameters: list[ParameterObject | ReferenceObject] | None = None
    responses: Responses | None = None


class PathItem(RootModel[dict[str, Operation]]):
    """
    Describes the operations available on a single path.

    ref: https://swagger.io/specification/#path-item-object
    """


class Paths(RootModel[dict[str, PathItem]]):
    """
    Holds the relative paths to the individual endpoints and their operations.

    ref: https://swagger.io/specification/#paths-object
    """
