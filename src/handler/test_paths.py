import pytest
import responses

from src.handler.paths import handle_path_item
from src.openapi_spec import ReferenceObject
from src.openapi_spec import ResponseObject
from src.openapi_spec import SchemaObject


class TestHandlePaths:
    @responses.activate
    @pytest.mark.parametrize("app", ["apps", "bookmarks", "admin", "filters"])
    def test_handle_path_item(self, load_api_html_fn, app):
        link = f"https://docs.joinmastodon.org/methods/{app}/"
        load_api_html_fn(app)

        resp = handle_path_item(app, link)
        assert len(resp) == 0 if app == "admin" else len(resp) > 0

    @responses.activate
    def test_handle_deprecated_path_item(self, load_api_html_fn):
        link = "https://docs.joinmastodon.org/methods/instance/"
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

    @responses.activate
    def test_handle_response(self, load_api_html_fn):
        link = "https://docs.joinmastodon.org/methods/instance/"
        load_api_html_fn("instance")

        resp = handle_path_item("instance", link)

        assert "/api/v1/instance/rules" in resp
        assert "get" in resp["/api/v1/instance/rules"].root

        operation = resp["/api/v1/instance/rules"].root["get"]
        assert 200 in operation.responses.root

        response = operation.responses.root[200]
        assert isinstance(response, ResponseObject)
        assert isinstance(response.content["application/json"].schema_object, SchemaObject)

        schema_object = response.content["application/json"].schema_object
        assert schema_object.type == "array"

        items = schema_object.items
        assert isinstance(items, ReferenceObject) and items.ref == "#/components/schemas/Rule"

    @responses.activate
    def test_handle_parameter(self, load_api_html_fn, app="accounts"):
        link = f"https://docs.joinmastodon.org/methods/{app}/"
        load_api_html_fn(app)

        resp = handle_path_item(app, link)
        assert "/api/v1/accounts/{:id}/unmute" in resp

        operation = resp["/api/v1/accounts/{:id}/unmute"].root["post"]
        assert operation.parameters is not None

    @responses.activate
    def test_handle_operation_filter(self, load_api_html_fn, app="filters"):
        link = f"https://docs.joinmastodon.org/methods/{app}/"
        load_api_html_fn(app)

        resp = handle_path_item(app, link)
        assert len(resp) == 8
        assert "/api/v1/filters/{:id}" in resp

    @responses.activate
    def test_handle_operation_ip_blocks(self, load_api_html_fn, app="ip_blocks"):
        link = f"https://docs.joinmastodon.org/methods/{app}/"
        load_api_html_fn(app)

        resp = handle_path_item(app, link)
        assert len(resp) == 2
        assert "/api/v1/admin/ip_blocks" in resp
        assert "/api/v1/admin/ip_blocks/{:id}" in resp

        path = resp["/api/v1/admin/ip_blocks/{:id}"].root
        assert "get" in path
        assert "put" in path
        assert "delete" in path

        path = resp["/api/v1/admin/ip_blocks"].root
        assert "get" in path
        assert "post" in path
