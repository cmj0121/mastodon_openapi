from src.openapi_spec import Component
from src.openapi_spec import MediaTypeObject
from src.openapi_spec import ResponseObject
from src.openapi_spec import SchemaObject


def handle_components(link: str, html: str) -> Component:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Components object.
    """

    return Component(
        responses={
            "Error": ResponseObject(
                description="Represents an error message.",
                content={
                    "application/json": MediaTypeObject.model_validate(
                        {
                            "schema": SchemaObject(
                                type="object",
                                properties={
                                    "error": SchemaObject(type="string", description="The error message."),
                                },
                            )
                        }
                    )
                },
            ),
            "Streaming": ResponseObject(
                description="Represents an error message.",
                content={
                    "text/event-stream": MediaTypeObject.model_validate(
                        {
                            "schema": SchemaObject(
                                type="string",
                            )
                        }
                    )
                },
            ),
        },
    )
