"""Unit tests for Foxglove schema resources"""

from ok_serial_relay import foxglove_jsonschema


def test_foxglove_jsonschema():
    assert foxglove_jsonschema.get("does-not-exist") == b""
    assert b'"foxglove.Log"' in foxglove_jsonschema.get("Log")

    # test cached responses
    assert foxglove_jsonschema.get("does-not-exist") == b""
    assert b'"foxglove.Log"' in foxglove_jsonschema.get("Log")
