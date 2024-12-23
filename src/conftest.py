from functools import wraps

import pytest
import responses


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
