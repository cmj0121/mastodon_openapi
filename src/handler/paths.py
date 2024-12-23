import re

import requests
from bs4 import BeautifulSoup
from bs4 import Tag
from loguru import logger

from src.openapi_spec import Operation
from src.openapi_spec import PathItem
from src.openapi_spec import Paths


def handle_paths(link: str, html: str) -> Paths:
    """
    Handle the base URL of the Mastodon API documentation and return the OpenAPI Paths object.
    """
    spec = {}

    soup = BeautifulSoup(html, "html.parser")
    methods = soup.find_all("a", href=lambda href: href and href.startswith("/methods/"))
    for method in methods:
        method_link = f'{link}{method["href"]}'
        for path, path_item in handle_path_item(method.text, method_link).items():
            spec[path] = path_item

    return Paths(spec)


def handle_path_item(tag: str, link: str) -> dict[str, PathItem]:
    """
    Handle the API method per tag and return the OpenAPI PathItem object.
    """
    logger.info(f"handle API method {tag=} {link=}")

    response = requests.get(link)
    response.raise_for_status()

    spec = {}
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("nav", attrs={"id": "TableOfContents"})
    if not table:
        logger.info("no table of content found in {link=}")
        return spec

    content_id = [link["href"][1:] for link in table.find_all("a", href=True)]

    content = table.find_next("div", {"class": "e-content"})
    methods = [content.find("h2", {"id": id}) for id in content_id]
    methods = [method for method in methods if method]

    for method_dom in reversed(methods):
        index = content.index(method_dom)
        logger.debug(f"processing #{index=} methods")

        code = method_dom.find_next("code", class_="language-http", attrs={"data-lang": "http"})
        logger.debug(f"processing {code=} on {method_dom.text=}")
        if code:
            matched = re.search(r"(\w+) (/\S+)(?: HTTP/1.1)?", code.text)

            if matched:
                method, endpoint = matched.groups()

                deprecated = method_dom.find("span", class_="api-method-parameter-deprecated", string="deprecated")
                operation = handle_operation(code)
                # add the method link to the operation description
                operation.description += f'\n\n[{method_dom.text.strip()}]({link}#{method_dom["id"]})'
                operation.tags = [tag]
                operation.deprecated = True if deprecated else None

                spec[endpoint] = PathItem({method.lower(): operation})

        # extract the content of the method
        while len(content) > index + 1:
            elm = content.contents[index + 1]
            elm.extract()

    return spec


def handle_operation(tag: Tag) -> Operation:
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

    return Operation(summary=summary, description=description)


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

    return f"\n## Version history\n\n- {'\n- '.join(versions)}"
