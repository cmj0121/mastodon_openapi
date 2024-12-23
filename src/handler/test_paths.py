import pytest
import responses

from src.handler.paths import handle_path_item


class TestHandlePaths:
    @responses.activate
    @pytest.mark.parametrize("app", ["apps", "bookmarks", "admin"])
    def test_handle_path_item(self, load_api_html_fn, app):
        link = f"https://docs.joinmastodon.org/methods/{app}/"
        load_api_html_fn(app)

        resp = handle_path_item(app, link)
        assert len(resp) == 0 if app == "admin" else len(resp) > 0
