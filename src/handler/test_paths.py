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

    def test_handle_deprecated_path_item(self, load_api_html_fn):
        link = "https://docs.joinmastodon.org/methods/instance"
        load_api_html_fn("instance")

        resp = handle_path_item("instance", link)
        assert "/api/v1/instance" in resp
        assert "get" in resp["/api/v1/instance"].root

        operation = resp["/api/v1/instance"].root["get"]
        assert operation.deprecated is True

        assert "/api/v2/instance" in resp
        assert "get" in resp["/api/v2/instance"].root

        operation = resp["/api/v2/instance"].root["get"]
        assert operation.deprecated is None

    def test_handle_response(self, load_api_html_fn):
        link = "https://docs.joinmastodon.org/methods/instance"
        load_api_html_fn("instance")

        resp = handle_path_item("instance", link)
        assert "/api/v1/instance" in resp
        assert "get" in resp["/api/v1/instance"].root

        operation = resp["/api/v1/instance"].root["get"]
        assert 200 in operation.responses.root

        assert "/api/v1/instance/peers" in resp
        assert "get" in resp["/api/v1/instance/peers"].root

        operation = resp["/api/v1/instance/peers"].root["get"]
        assert 200 in operation.responses.root
        assert 401 in operation.responses.root
