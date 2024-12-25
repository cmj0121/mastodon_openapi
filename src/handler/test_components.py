import pytest
import responses

from src.handler.components import handle_component
from src.openapi_spec import ResponseObject
from src.openapi_spec import SchemaObject


class TestHandleComponent:
    @responses.activate
    @pytest.mark.parametrize("component", ["account", "admin_account"])
    def test_handle_component(self, load_component_html_fn, component):
        link = f"https://docs.joinmastodon.org/entities/{component}/"
        load_component_html_fn(component)

        resp = handle_component(link)

        for key in resp:
            response = resp[key]
            assert isinstance(response, ResponseObject)
            assert "application/json" in response.content

            schema_object = response.content["application/json"].schema_object
            assert isinstance(schema_object, SchemaObject)
            assert schema_object.type == "object"
            assert schema_object.items is None

    @responses.activate
    def test_handle_nested_component(self, load_component_html_fn):
        component = "account"
        link = f"https://docs.joinmastodon.org/entities/{component}/"
        load_component_html_fn(component)

        resp = handle_component(link)

        assert "Account" in resp
        for attr in {"id", "username", "acct", "url"}:
            schema_object = resp["Account"].content["application/json"].schema_object
            assert schema_object.type == "object"
            assert attr in schema_object.properties

        assert "CredentialAccount" in resp
        for attr in {"source", "role"}:
            schema_object = resp["CredentialAccount"].content["application/json"].schema_object
            assert schema_object.type == "object"
            assert attr in schema_object.properties

        assert "MutedAccount" in resp
        for attr in {"mute_expires_at"}:
            schema_object = resp["MutedAccount"].content["application/json"].schema_object
            assert schema_object.type == "object"
            assert attr in schema_object.properties

        assert "Field" in resp
        for attr in {"name", "value", "verified_at"}:
            schema_object = resp["Field"].content["application/json"].schema_object
            assert schema_object.type == "object"
            assert attr in schema_object.properties
