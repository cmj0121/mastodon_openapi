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
