import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from bs4 import BeautifulSoup
from bs4 import Tag
from loguru import logger

from src.handler.utils import canonicalize
from src.handler.utils import fetch_soup
from src.handler.utils import handle_type_str
from src.handler.utils import make_media_type
from src.openapi_spec import BuildInType
from src.openapi_spec import OneOfObject
from src.openapi_spec import Operation
from src.openapi_spec import ParameterIn
from src.openapi_spec import ParameterObject
from src.openapi_spec import PathItem
from src.openapi_spec import Paths
from src.openapi_spec import ReferenceObject
from src.openapi_spec import ResponseObject
from src.openapi_spec import Responses
from src.openapi_spec import SchemaObject
from src.openapi_spec import SecurityRequirementObject


def canonicalize_path(path: str) -> str:
    """replace /:id with /{:id}"""
    return re.sub(r"/(:\w+)", r"/{\1}", path)


def handle_paths(link: str, soup: BeautifulSoup) -> Paths:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Paths object.
    """
    spec = {}
    methods = soup.find_all("a", href=lambda href: href and href.startswith("/methods/"))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(handle_path_item, method.text, f"{link}{method['href']}"): method for method in methods
        }
        for future in as_completed(futures):
            for path, path_item in future.result().items():
                spec[path] = path_item

    return Paths(spec)


def handle_path_item(tag: str, link: str) -> dict[str, PathItem]:
    """
    Handle the API method per tag and return the OpenAPI PathItem object.
    """
    logger.info(f"handle API method {tag=} {link=}")

    soup = fetch_soup(link)

    spec = {}
    content = soup.find("div", class_="e-content")
    if not content:
        logger.warning(f"no content found in {link=}")
        return spec

    methods = content.find_all("code", class_="language-http", attrs={"data-lang": "http"})

    for method_dom in methods:
        subject = method_dom.find_previous("h3" if tag == "filters" else "h2", class_="heading")
        matched = re.search(r"(\w+) (/\S+)(?: HTTP/1.1)?", method_dom.text)
        if not matched:
            logger.warning(f"no method found in {method_dom.text=}")
            continue

        method, endpoint = matched.groups()
        endpoint = canonicalize_path(endpoint)

        removed = subject.find("span", class_="api-method-parameter-removed", string="removed")
        deprecated = subject.find("span", class_="api-method-parameter-deprecated", string="deprecated")
        logger.info(f"process {subject.text.strip()}: [{method}] {endpoint=} {removed=} {deprecated=}")
        if removed:
            continue

        operation, response_object = handle_operation(method_dom)
        operation.description += f"\n\n[{subject.text.strip()}]({link}#{subject['id']})"
        operation.tags = [tag]
        operation.deprecated = True if deprecated else None

        if endpoint == "/api/v1/instance/activity" and method == "GET":
            response_object = ResponseObject(
                description="Array of Hash",
                content={
                    "application/json": make_media_type(
                        SchemaObject(
                            type="array",
                            items=SchemaObject(
                                type="object",
                                properties={
                                    "week": SchemaObject(type="string"),
                                    "statuses": SchemaObject(type="string"),
                                    "logins": SchemaObject(type="string"),
                                    "registrations": SchemaObject(type="string"),
                                },
                            ),
                        )
                    ),
                },
            )

        match tag:
            case "streaming":
                ref = ReferenceObject.model_validate(
                    {
                        "$ref": "#/components/schemas/Streaming",
                        "description": "The streaming response.",
                    }
                )
                streaming_response = ResponseObject(
                    description="The streaming response.",
                    content={
                        "text/event-stream": make_media_type(ref),
                    },
                )
                operation.responses = Responses({200: streaming_response})
            case _:
                operation.responses = handle_response(method_dom, response_object)

        spec[endpoint] = spec[endpoint] if endpoint in spec else PathItem({})
        spec[endpoint].root[method.lower()] = operation

    return spec


def handle_operation(tag: Tag) -> tuple[Operation, ResponseObject | None]:
    """
    Handle the API method per bs4 Tag and return the OpenAPI Operation object.
    """
    summaries = []
    while tag:
        tag = tag.find_next("p")
        if not tag or tag.text.startswith("Returns:"):
            break

        logger.debug(f"handle summary {tag.text=}")
        summaries.append(tag.text)

    summary = summaries[0] if summaries else None
    description = "\n".join(summaries) + handle_description(tag.text if tag else "")

    parameters, response_object = handle_parameters(tag)
    security = None
    if parameters:
        for idx, param in enumerate(parameters):
            if isinstance(param, ParameterObject) and param.name == "Authorization":
                parameters.pop(idx)
                security = [SecurityRequirementObject({"BearerAuth": []})]
                break

    operation = Operation(summary=summary, description=description, parameters=parameters, security=security)
    return operation, response_object


def handle_parameters(tag: Tag) -> tuple[list[ParameterObject | ReferenceObject], ResponseObject | None]:
    """
    Handle the parameters of the API method, based on the ParameterIn enum.

    at the same time, get the default response object in the API method.
    """
    if not tag:
        return [], None

    response_object = parse_response_object(tag)

    parameters = [param for param_type in ParameterIn for param in handle_parameter_by_type(tag, param_type)]
    return (parameters or []), response_object


def handle_parameter_by_type(tag: Tag, param_type: ParameterIn) -> list[ParameterObject | ReferenceObject]:
    parameters = []
    logger.debug(f"try to handle parameter by {param_type=}")
    if not (dom := tag.find_next("h5", {"id": lambda x: x and x.startswith(param_type)})):
        logger.warning(f"no parameter found in {param_type=}")
        return parameters

    logger.debug(f"handle parameter by type {param_type=} {dom.text=}")
    if not (param_based_dom := dom.find_next("dl")):
        logger.warning(f"no parameter found in {param_type=}")
        return parameters

    for param_dom in param_based_dom.find_all("dt") if dom else []:
        name = param_dom.text
        desc = param_dom.find_next("dd")

        logger.debug(f"handle parameter {name=} {param_type=} {desc.text=}")
        required = desc.find("span", class_="api-method-parameter-required")

        match param_type:
            case ParameterIn.header:
                vtype = "string"
            case _:
                raw_type = desc.find("strong")
                raw_type = raw_type.text if raw_type else "string"
                vtype, _ = handle_type_str(raw_type)
                vtype = canonicalize(vtype) if vtype.lower() in BuildInType else "string"

        param = ParameterObject.model_validate(
            {
                "name": name,
                "in": param_type.value,
                "description": desc.text if desc else None,
                "schema": SchemaObject(type=vtype),
                "required": True if required else None,
            }
        )

        parameters.append(param)

    return parameters


def handle_description(text: str) -> str:
    """
    Handle the description of the API method.
    """
    logger.debug(f"handle description {text=}")

    pattern = r"^Returns:([\s\S]+?)OAuth:([\s\S]+?)Version(?: history)?:([\s\S]*?)$"
    matched = re.search(pattern, text)
    if not matched:
        return text

    rvalue, auth, version = matched.groups()
    versions = re.split(r"(\d+\.\d+\.\d+ -)", version)[1:]
    versions = ["".join(versions[n : n + 2]).strip() for n in range(0, len(versions), 2)]

    return f"\n## Version history\n\n- {'\n- '.join(versions)}" if versions else ""


def handle_response(tag: Tag, response_object: ResponseObject | None) -> Responses:
    response = {}

    for code in tag.find_all_next(["h4", "h5"], class_="heading"):
        logger.debug(f"handle response {code.text=}")

        matched = re.search(r"(\d+): \w+", code.text)
        if not matched:
            logger.warning(f"no status code found in {code.text=}")
            continue

        status_code = int(matched.groups()[0])
        next_p = code.find_next("p")
        description = next_p.text if next_p else ""

        if status_code == 200 and response_object:
            response[status_code] = response_object
        else:
            ref = ReferenceObject.model_validate(
                {
                    "$ref": "#/components/schemas/Error",
                    "description": description,
                }
            )
            err_response_object = ResponseObject(
                description=description,
                content={"application/json": make_media_type(ref)},
            )
            response[status_code] = err_response_object

    return Responses(response)


def parse_response_object(tag: Tag) -> ResponseObject | None:
    """parse and return the API response object."""
    matched = re.search(r"^Returns:([\s\S]+?)OAuth", tag.text)
    if not matched:
        logger.warning(f"no response object found {tag.text=}")
        return None

    (rvalue,) = matched.groups()
    rvalue = rvalue.strip()
    schema_object = parse_schema_object(rvalue)
    return ResponseObject(
        description=rvalue,
        content={"application/json": make_media_type(schema_object)},
    )


def parse_schema_object(text: str) -> SchemaObject:
    text = text.strip()

    logger.debug(f"try to parse SchemaObject: {text=}")
    if matched := re.match(r"(?:Array|List) of ([\w:]+)", text):
        (value,) = matched.groups()

        schema_object = SchemaObject(
            type="array",
            description=text,
            items=parse_schema_object(value),
        )
    elif "String (URL) or HTML response" == text:
        schema_object = SchemaObject(type="string", description=text)
    elif "Preferences by key and value" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/JSON"})
    elif "the user\u2019s own Account with source attribute" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/Account"})
    elif "MediaAttachment, but without a URL" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/MediaAttachment"})
    elif "Hash of timeline key and associated Marker" == text:
        schema_object = SchemaObject(
            description=text,
            type="object",
        )
    elif "Hash with a single key of count" == text:
        schema_object = SchemaObject(
            description=text,
            type="object",
            properties={"count": SchemaObject(type="integer")},
        )
    elif "JSON as per the above description" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/JSON"})
    elif "OEmbed metadata" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/JSON"})
    elif "Object with source language codes as keys and arrays of target language codes as values." == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/JSON"})
    elif "Search, but hashtags is an array of strings instead of an array of Tag." == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/Search"})
    elif "Status. When scheduled_at is present, ScheduledStatus is returned instead." == text:
        schema_object = OneOfObject(
            oneOf=[
                ReferenceObject.model_validate({"$ref": "#/components/schemas/Status"}),
                ReferenceObject.model_validate({"$ref": "#/components/schemas/ScheduledStatus"}),
            ]
        )
    elif "Status with source text and poll or media_attachments" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/Status"})
    elif "Health status" == text:
        schema_object = ReferenceObject.model_validate({"$ref": "#/components/schemas/Hash"})
    elif text.lower() in BuildInType:
        schema_object = SchemaObject(type=text.lower())
    else:
        schema_object = ReferenceObject.model_validate({"$ref": f"#/components/schemas/{canonicalize(text)}"})

    logger.info(f"parse {text=} as {schema_object}")
    return schema_object
