import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from bs4 import BeautifulSoup
from bs4.element import NavigableString
from bs4.element import Tag
from loguru import logger

from src.handler.utils import canonicalize
from src.handler.utils import fetch_soup
from src.handler.utils import handle_type_str
from src.handler.utils import make_media_type
from src.openapi_spec import BuildInType
from src.openapi_spec import Component
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


def handle_components(link: str, soup: BeautifulSoup) -> Component:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Components object.
    """
    json_response = ResponseObject(
        description="Represents a JSON object.",
        content={"application/json": make_media_type(SchemaObject(type="object", additionalProperties=True))},
    )
    spec = {
        "Empty": ResponseObject(
            description="Empty content",
            content={
                "text/plain": make_media_type(SchemaObject(type="null")),
            },
        ),
        "Streaming": ResponseObject(
            description="Represents an error message.",
            content={"text/event-stream": make_media_type(SchemaObject(type="string"))},
        ),
        "JSON": json_response,
        "Hash": ResponseObject(
            description="Represents a JSON/Hash object.",
            content={"application/json": make_media_type(SchemaObject(type="object", additionalProperties=True))},
        ),
        "History": ResponseObject(
            description="Usage statistics for given days",
            content={
                "application/json": make_media_type(
                    SchemaObject(
                        type="object",
                        properties={
                            "key": SchemaObject(type="string"),
                            "human_key": SchemaObject(type="string"),
                            "value": SchemaObject(type="string"),
                        },
                    )
                ),
            },
        ),
    }
    entities = soup.find_all("a", href=lambda href: href and href.startswith("/entities/"))
    seen_hrefs = set()
    entity_links = []
    for entity in entities:
        href = entity["href"]
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        entity_links.append(f"{link}{href}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(handle_component, el): el for el in entity_links}
        for future in as_completed(futures):
            spec.update(future.result())

    component = Component(responses=spec, securitySchemes=default_security_scheme())
    return post_handle_components(component)


def handle_component(link: str) -> dict[str, ResponseObject | ReferenceObject]:
    """
    Handle the Mastodon entity from the API documentation and return the OpenAPI SchemaObject.
    """
    logger.info(f"handle entity {link=}")

    soup = fetch_soup(link)

    spec = {}
    content = soup.find("div", class_="e-content")
    parts = list(content.children)
    index = [content.index(dom) for dom in content.find_all("h2", recursive=False)] + [len(parts) - 1]
    attrs = [parts[pos : index[idx + 1]] for idx, pos in enumerate(index[:-1])]

    for attr, *columns in reversed(attrs):
        name = attr.find("span", class_="heading__text").text
        if not (name == "Attributes" or name.endswith("attributes")):
            logger.debug(f"skip the handle component {name=}")
            continue

        logger.info(f"processing component {name=}")
        schema_object = SchemaObject(type="object", properties={})
        for column in columns:
            if not isinstance(column, Tag) or not column.find("span", class_="heading__text"):
                continue

            code = column.find("code")
            if code is not None:
                attr_name = code.text
            else:
                # Some Mastodon docs headings (e.g. AnnualReport's data[*] fields)
                # have malformed markdown that renders the name as a literal
                # backtick string instead of a <code> element. Fall back to the
                # heading text and strip the stray backticks.
                attr_name = column.find("span", class_="heading__text").text.strip().strip("`")
            prop = handle_parameter(attr_name, column.find_next("p"))
            schema_object.properties[attr_name] = prop

        match name:
            case "Attributes":
                main_resp_dom = soup.find("h1")
                main_desc_dom = main_resp_dom.find_next("p")

                name = main_resp_dom.text
                desc = main_desc_dom.text
            case _:
                matched = re.search(r"^([\w:]+?) (?:entity )?attributes", name)
                if not matched:
                    raise ValueError(f"cannot find the entity name {name=}")

                (name,) = matched.groups()
                desc = ""

        spec[canonicalize(name)] = ResponseObject(
            description=desc,
            content={"application/json": make_media_type(schema_object)},
        )

    return spec


def post_handle_components(component: Component) -> Component:
    component.schemas = {}
    for key, resp in component.responses.items():
        for mime in resp.content or []:
            schema = resp.content[mime].schema_object
            component.schemas[key] = schema

            resp.content[mime].schema_object = ReferenceObject.model_validate(
                {"$ref": f"#/components/schemas/{canonicalize(key)}"}
            )

    # Case 1: convert the Array of Hash to History
    for schema in {"AdminEmailDomainBlock", "Tag", "TrendsLink"}:
        history_item = component.schemas[schema].properties["history"].items
        history_item.ref = "#/components/schemas/History"

    # Case 2: convert the Array of Hash in AdminDimension
    component.schemas["AdminDimension"].properties["data"].items = SchemaObject(
        type="object",
        properties={
            "key": SchemaObject(type="string"),
            "human_key": SchemaObject(type="string"),
            "value": SchemaObject(type="string"),
        },
    )

    # Case 3: convert the Array of Hash in AdminMeasure
    component.schemas["AdminMeasure"].properties["data"].items = SchemaObject(
        type="object",
        properties={
            "date": SchemaObject(type="string"),
            "value": SchemaObject(type="string"),
        },
    )

    return component


def handle_parameter(name, tag: Tag) -> SchemaObject | ReferenceObject:
    desc, nullable, typ, items = "", False, "", None
    tag_text = tag.text
    for strong in tag.find_all(["strong", "em"]):
        match text := strong.text:
            case "Description:":
                desc = re.search(r"Description:([\s\S]*?)Type: ", tag_text).group(1)
                desc = desc.strip()
            case "Type:":
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
                pass
            case _:
                raise ValueError(f"unknown tag {text=}")

    typ, items = handle_type_str(typ, items)
    logger.info(f"handle parameter {name}: {nullable=} {typ=}")
    return handle_schema(typ, desc, nullable, items)


def handle_schema(
    typ: str, desc: str, nullable: bool = False, items: str | None = None
) -> ReferenceObject | SchemaObject:
    if typ.lower() in BuildInType:
        schema = SchemaObject(
            type=[typ.lower(), "null"] if nullable else typ.lower(),
            description=desc.strip(),
        )

        if typ.lower() == "array":
            schema.items = handle_schema(items, "")

        return schema
    elif typ.lower() == "null":
        return SchemaObject(type="null", description=desc.strip())
    elif typ.lower().endswith("or null"):
        typ = typ[: -len(" or null")]
        return handle_schema(typ, desc, True, items)
    else:
        return ReferenceObject.model_validate(
            {
                "$ref": f"#/components/schemas/{canonicalize(typ)}",
                "description": desc.strip(),
            }
        )
