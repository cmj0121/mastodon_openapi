import yaml

from src.openapi_spec import Info
from src.openapi_spec import License
from src.openapi_spec import OpenAPI


def run(link: str) -> str:
    info = Info(
        title="Mastodon OpenAPI API",
        version="0.1.0",
        summary="The self-hosted Mastodon OpenAPI specifcation",
        description="""
            The official Mastodon API documentation is available at https://docs.joinmastodon.org/api/ but
            it does not provide an OpenAPI specification. This script generates an OpenAPI specification
            from the website.
        """,
        license=License(name="MIT"),
    )

    spec = OpenAPI(info=info)
    return to_openapi_spec_text(spec)


def to_openapi_spec_text(spec: OpenAPI) -> str:
    spec_dict = spec.model_dump(exclude_none=True)
    return yaml.dump(spec_dict, default_flow_style=False, sort_keys=False)
