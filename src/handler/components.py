import re

import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.handler.utils import canonicalize
from src.openapi_spec import Component
from src.openapi_spec import MediaTypeObject
from src.openapi_spec import ReferenceObject
from src.openapi_spec import ResponseObject
from src.openapi_spec import SchemaObject


def default_streaming_response() -> ResponseObject:
    return ResponseObject(
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
    )


def handle_components(link: str, html: str) -> Component:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Components object.
    """
    spec = {"Streaming": default_streaming_response()}
    soup = BeautifulSoup(html, "html.parser")

    entities = soup.find_all("a", href=lambda href: href and href.startswith("/entities/"))
    for entity in entities:
        entity_link = f'{link}{entity["href"]}'
        spec.update(handle_component(entity_link))

    return Component(responses=spec)


def handle_component(link: str) -> dict[str, ResponseObject | ReferenceObject]:
    """
    Handle the Mastodon entity from the API documentation and return the OpenAPI SchemaObject.
    """
    logger.info(f"handle entity {link=}")

    response = requests.get(link)
    response.raise_for_status()

    spec = {}
    soup = BeautifulSoup(response.text, "html.parser")

    schema_object = SchemaObject(type="object", properties={})
    main_attr_dom = soup.find("a", href="#attributes").find_next("ul").findChildren("li", recursive=False)

    for attr_dom in main_attr_dom:
        logger.debug(f"processing component {attr_dom.text=}")

        attr_id = attr_dom.find("a").get("href")[1:]
        attr_name = attr_dom.find("code").text

        text = soup.find("h3", {"id": attr_id}).find_next("p").text
        matched = re.search(r"Description:([\s\S]*?)Type: (nullable )?(\S+)(?: .*?)?(?:Version history:)?(.+?)", text)
        if not matched:
            raise ValueError(f"failed to find the attribute {text=}")

        desc, nullable, typ, version = matched.groups()
        schema_object.properties[attr_name] = SchemaObject(
            type=typ,
            nullable=True if nullable else None,
            description=desc.strip(),
        )

    main_resp_dom = soup.find("h1")
    main_desc_dom = main_resp_dom.find_next("p")

    spec[canonicalize(main_resp_dom.text)] = ResponseObject(
        description=main_desc_dom.text,
        content={"application/json": MediaTypeObject.model_validate({"schema": schema_object})},
    )
    return spec
