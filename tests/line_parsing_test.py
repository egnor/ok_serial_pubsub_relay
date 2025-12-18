"""Unit tests for ok_serial_relay.protocol"""

import json
import msgspec

from ok_serial_relay import line_parsing
from ok_serial_relay import line_types


class ExamplePayload(msgspec.Struct, array_like=True, omit_defaults=True):
    a: int
    b: str = "def"


ExamplePayload.PREFIX = b"EXAMPLE"  # type: ignore[attr-defined]


LINE_CHECKS = [
    (b"PFX", [1, 2, {"x": 3}], b'PFX[1,2,{"x":3}]Xwb'),
    (b"", {"foo": "bar"}, b'{"foo":"bar"}rTj'),
    (b"", None, b"null 28q"),
    (b"PFX", None, b"PFX null 1Dw"),
    (b"", [], b"[]RRw"),
    (b"PFX", [], b"PFX[]LQk"),
    (b"", 0, b"0 xcB"),
    (b"PFX", 0, b"PFX 0 yK0"),
    (b"", 31337, b"31337 WZx"),
    (b"PFX", 31337, b"PFX 31337 M6b"),
    (b"", 1.2345, b"1.2345 _eX"),
    (b"PFX", 1.2345, b"PFX 1.2345 Zor"),
]


def test_to_bytes():
    for prefix, payload_data, data in LINE_CHECKS:
        line = line_types.Line(
            prefix=prefix,
            payload=json.dumps(payload_data, separators=(",", ":")).encode(),
        )
        assert line_parsing.to_bytes(line) == data


def test_try_parse():
    for prefix, payload_data, data in LINE_CHECKS:
        line = line_parsing.try_from_bytes(data)
        assert line.prefix == prefix
        assert msgspec.json.decode(line.payload) == payload_data


def test_try_parse_unchecked():
    for prefix, payload_data, data in LINE_CHECKS:
        line_ltag = line_parsing.try_from_bytes(data[:-3] + b"~~~")
        line_utag = line_parsing.try_from_bytes(data[:-3] + b"~~~")
        assert line_ltag.prefix == line_utag.prefix == prefix
        assert msgspec.json.decode(line_ltag.payload) == payload_data
        assert msgspec.json.decode(line_utag.payload) == payload_data


def test_try_as():
    example_line = line_types.Line(prefix=b"EXAMPLE", payload=b'[1,"x"]')
    example_payload = line_parsing.try_payload(example_line, ExamplePayload)
    assert example_payload == ExamplePayload(a=1, b="x")

    example_line = line_types.Line(prefix=b"EXAMPLE", payload=b"[1]")
    example_payload = line_parsing.try_payload(example_line, ExamplePayload)
    assert example_payload == ExamplePayload(a=1, b="def")

    example_line = line_types.Line(prefix=b"OTHER", payload=b'[1,"x"]')
    example_payload = line_parsing.try_payload(example_line, ExamplePayload)
    assert example_payload is None

    example_line = line_types.Line(prefix=b"EXAMPLE", payload=b'["x",1]')
    example_payload = line_parsing.try_payload(example_line, ExamplePayload)
    assert example_payload is None


def test_from_payload():
    line = line_parsing.from_payload(ExamplePayload(a=1, b="x"))
    assert line == line_types.Line(prefix=b"EXAMPLE", payload=b'[1,"x"]')

    # we wish the default value was elided!
    line = line_parsing.from_payload(ExamplePayload(a=1, b="def"))
    assert line == line_types.Line(prefix=b"EXAMPLE", payload=b'[1,"def"]')
