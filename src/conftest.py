import sys
from functools import wraps

import pytest
import responses
from loguru import logger


@pytest.fixture(autouse=True)
def override_log_level():
    logger.remove()
    logger.add(sys.stderr, level="INFO")


@pytest.fixture
def load_api_html_fn():
    @wraps(load_api_html_fn)
    def loader(app: str) -> str:
        with open(f"src/tests/html/api_{app}.html") as f:
            link = f"https://docs.joinmastodon.org/methods/{app}/"

            html = f.read()
            responses.add(responses.GET, link, body=html, status=200)

            return html

    return loader


@pytest.fixture
def load_component_html_fn():
    @wraps(load_api_html_fn)
    def loader(component: str) -> str:
        with open(f"src/tests/html/component_{component}.html") as f:
            link = f"https://docs.joinmastodon.org/entities/{component}/"

            html = f.read()
            responses.add(responses.GET, link, body=html, status=200)

            return html

    return loader
