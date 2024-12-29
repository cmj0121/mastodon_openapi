import re

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from bs4.element import Tag
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
        "Empty": ResponseObject(
            description="Empty content",
            content={
                "text/plain": MediaTypeObject.model_validate({"schema": SchemaObject(type="null")}),
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
        "Hash": ResponseObject(
            description="Represents an JSON/Hash object.",
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

    component = Component(responses=spec, securitySchemes=default_security_scheme())
    return post_handle_components(component)


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
            logger.info(f"skip the handle component {entity_dom.text=}")
            continue

        logger.info(f"processing component {entity_dom.text=}")

        schema_object = SchemaObject(type="object", properties={})
        attrs_dom = entity_dom.parent.find_all("li")

        for attr_dom in attrs_dom:
            logger.debug(f"processing component {attr_dom.text=}")

            attr_id = attr_dom.find("a").get("href")[1:]
            attr_name = attr_dom.find("code").text

            prop = handle_parameter(attr_name, soup.find("h3", {"id": attr_id}).find_next("p"))
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


def post_handle_components(component: Component) -> Component:
    """copy the response object to the schema object and setup the reference object"""
    component.schemas = {}
    for key, resp in component.responses.items():
        for mime in resp.content or []:
            schema = resp.content[mime].schema_object
            component.schemas[key] = schema

            resp.content[mime].schema_object = ReferenceObject.model_validate(
                {"$ref": f"#/components/schemas/{canonicalize(key)}"}
            )

    return component


def handle_parameter(name, tag: Tag) -> SchemaObject | ReferenceObject:
    desc, nullable, typ, items, version = "", False, "", None, ""
    for strong in tag.find_all("strong"):
        match text := strong.text:
            case "Description:":
                desc = re.search(r"Description:([\s\S]*?)Type: ", tag.text).group(1)
                desc = desc.strip()
            case "Type:":
                candidate = strong.next_sibling.strip()
                candidate = strong.next_sibling
                while True:
                    if isinstance(candidate, NavigableString):
                        text = candidate.strip()
                        if text:
                            typ = text
                            if typ == "Array of":
                                items = candidate.next_sibling.text

                            break
                    elif isinstance(candidate, Tag):
                        if candidate.name == "a":
                            typ = candidate.text
                            break
                        elif candidate.name == "span" and candidate["class"] == ["api-method-parameter-required"]:
                            nullable = True

                    candidate = candidate.next_sibling
            case "Version history:":
                version = strong.next_sibling.next_sibling.text.strip()
            case _:
                raise ValueError(f"unknown tag {text=}")

    if typ == "Array of":
        typ = "array"
    if typ == "Array of Strings":
        typ = "array"
        items = "String"
    elif typ.startswith("String"):
        typ = "String"
    elif typ.startswith("Integer"):
        typ = "Integer"
    elif typ.startswith("Number"):
        typ = "Number"
    elif typ.startswith("Array of"):
        items = typ.split()[2]
        typ = "array"

    logger.info(f"handle parameter {name}: {nullable=} {typ=} {version=}")
    return handle_schema(typ, desc, nullable, items)


def handle_schema(
    typ: str, desc: str, nullable: bool = False, items: str | None = None
) -> ReferenceObject | SchemaObject:
    if typ.lower() in BuildInType:
        schema = SchemaObject(
            type=[typ.lower(), "null"] if nullable else typ.lower(),
            description=desc.strip(),
        )

        if schema.type == "array":
            schema.items = handle_schema(items, "")

        return schema
    else:
        return ReferenceObject.model_validate(
            {
                "$ref": f"#/components/schemas/{canonicalize(typ)}",
                "description": desc.strip(),
            }
        )
