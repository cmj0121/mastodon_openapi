import re

import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.handler.utils import canonicalize
from src.openapi_spec import BuildInType
from src.openapi_spec import Component
from src.openapi_spec import MediaTypeObject
from src.openapi_spec import ReferenceObject
from src.openapi_spec import ResponseObject
from src.openapi_spec import SchemaObject
from src.openapi_spec import SecuritySchemeObject


def default_security_scheme() -> dict[str, SecuritySchemeObject]:
    spec = SecuritySchemeObject(
        type="http",
        description="Bearer token",
        scheme="bearer",
    )
    return {"BearerAuth": spec}


def handle_components(link: str, html: str) -> Component:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Components object.
    """
    spec = {
        "Empty": ResponseObject(description="Empty content"),
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
        "JSON": ResponseObject(
            description="Represents an JSON object.",
            content={
                "text/event-stream": MediaTypeObject.model_validate(
                    {
                        "schema": SchemaObject(
                            type="object",
                        )
                    }
                )
            },
        ),
    }
    soup = BeautifulSoup(html, "html.parser")

    entities = soup.find_all("a", href=lambda href: href and href.startswith("/entities/"))
    for entity in entities:
        entity_link = f'{link}{entity["href"]}'
        spec.update(handle_component(entity_link))

    return Component(responses=spec, securitySchemes=default_security_scheme())


def handle_component(link: str) -> dict[str, ResponseObject | ReferenceObject]:
    """
    Handle the Mastodon entity from the API documentation and return the OpenAPI SchemaObject.
    """
    logger.info(f"handle entity {link=}")

    response = requests.get(link)
    response.raise_for_status()

    spec = {}
    soup = BeautifulSoup(response.text, "html.parser")

    toc = soup.find("nav", {"id": "TableOfContents"})
    attrs = toc.find_next("ul").find_next("li").find_next("ul").findChildren("li", recursive=False)

    for attr in reversed(attrs):
        entity_dom = attr.find("a")
        if not (entity_dom.text == "Attributes" or entity_dom.text.endswith("attributes")):
            logger.debug(f"skip the handle component {entity_dom.text=}")
            continue

        schema_object = SchemaObject(type="object", properties={})
        attrs_dom = entity_dom.parent.find_all("li")

        for attr_dom in attrs_dom:
            logger.debug(f"processing component {attr_dom.text=}")

            attr_id = attr_dom.find("a").get("href")[1:]
            attr_name = attr_dom.find("code").text

            text = soup.find("h3", {"id": attr_id}).find_next("p").text
            matched = re.search(
                r"Description:([\s\S]*?)Type: (nullable )?(\S+)(?: .*?)?(?:Version history:)?(.+?)", text
            )
            if not matched:
                raise ValueError(f"failed to find the attribute {text=}")

            desc, nullable, typ, version = matched.groups()
            if typ == "StringVersion":
                # special case for the attribute type
                typ = "String"

            if typ.lower() in BuildInType:
                prop = SchemaObject(
                    type=[typ.lower(), "null"] if nullable else typ.lower(),
                    description=desc.strip(),
                )
            else:
                prop = ReferenceObject.model_validate(
                    {
                        "$ref": f"#/components/responses/{canonicalize(typ)}",
                        "description": desc.strip(),
                    }
                )

            schema_object.properties[attr_name] = prop

        match entity_dom.text:
            case "Attributes":
                main_resp_dom = soup.find("h1")
                main_desc_dom = main_resp_dom.find_next("p")

                name = main_resp_dom.text
                desc = main_desc_dom.text
            case _:
                matched = re.search(r"^([\w:]+?) (?:entity )?attributes", entity_dom.text)
                if not matched:
                    raise ValueError(f"cannot find the entity name {entity_dom.text=}")

                (name,) = matched.groups()
                desc = ""

        spec[canonicalize(name)] = ResponseObject(
            description=desc,
            content={"application/json": MediaTypeObject.model_validate({"schema": schema_object})},
        )

    return spec
