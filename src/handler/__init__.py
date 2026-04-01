from concurrent.futures import ThreadPoolExecutor

import yaml
from loguru import logger

from src.handler.utils import fetch_soup
from src.openapi_spec import Info
from src.openapi_spec import License
from src.openapi_spec import OpenAPI

from .components import handle_components
from .paths import handle_paths

description = """
The official Mastodon API documentation is available at https://docs.joinmastodon.org/api/ but
it does not provide an OpenAPI specification. This script generates an OpenAPI specification
from the website.
"""


def run(link: str) -> str:
    info = Info(
        title="Mastodon OpenAPI API",
        version="0.1.0",
        summary="The self-hosted Mastodon OpenAPI specifcation",
        description=description,
        license=License(name="MIT", identifier="MIT"),
    )

    logger.info(f"starting to generate OpenAPI spec from {link=}")

    soup = fetch_soup(link)

    spec = OpenAPI(info=info)

    with ThreadPoolExecutor(max_workers=2) as executor:
        paths_future = executor.submit(handle_paths, link, soup)
        components_future = executor.submit(handle_components, link, soup)
        spec.paths = paths_future.result()
        spec.components = components_future.result()

    return to_openapi_spec_text(spec)


def to_openapi_spec_text(spec: OpenAPI) -> str:
    spec_dict = spec.model_dump(exclude_none=True, by_alias=True)
    return yaml.dump(spec_dict, default_flow_style=False, sort_keys=True)
