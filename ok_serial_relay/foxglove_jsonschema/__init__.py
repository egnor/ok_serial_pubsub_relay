"""Present Foxglove JSON schemas as bytes"""

import importlib.resources
import pydantic

_PACKAGE_NAME = "ok_serial_relay.foxglove_jsonschema"

_available_schemas = {
    resource.name[:-5]: resource
    for resource in importlib.resources.files(_PACKAGE_NAME).iterdir()
    if resource.is_file() and resource.name.endswith(".json")
}

_loaded_schemas: dict[str, bytes] = {}


@pydantic.validate_call
def get(name: str) -> bytes:
    if loaded := _loaded_schemas.get(name):
        return loaded

    if not (resource := _available_schemas.get(name)):
        return b""

    schema = _loaded_schemas[name] = resource.read_bytes()
    return schema
