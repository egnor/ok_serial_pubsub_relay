"""Unit tests for ok_serial_relay.protocol"""

import msgspec

from ok_serial_relay import parser
from ok_serial_relay import protocol


class ExamplePayload(msgspec.Struct):
    PREFIX = b"EXAMPLE"
    a: int
    b: str


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


def test_line_to_bytes():
    for prefix, payload, data in LINE_CHECKS:
        line = protocol.Line(prefix, msgspec.json.encode(payload))
        assert parser.line_to_bytes(line) == data


def test_line_from_bytes():
    for prefix, payload, data in LINE_CHECKS:
        line = parser.try_parse_line(data)
        assert line.prefix == prefix
        assert msgspec.json.decode(line.payload) == payload


def test_line_from_bytes_unchecked():
    for prefix, payload, data in LINE_CHECKS:
        line_ltag = parser.try_parse_line(data[:-3] + b"~~~")
        line_utag = parser.try_parse_line(data[:-3] + b"~~~")
        assert line_ltag.prefix == line_utag.prefix == prefix
        assert msgspec.json.decode(line_ltag.payload) == payload
        assert msgspec.json.decode(line_utag.payload) == payload


def test_try_decode_json():
    example_line = protocol.Line(b"EXAMPLE", b'{"a":1,"b":"x"}')
    example_payload = parser.try_decode_json(example_line, ExamplePayload)
    assert example_payload == ExamplePayload(1, "x")

    example_line = protocol.Line(b"OTHER", b'{"a":2,"b":"y"}')
    example_payload = parser.try_decode_json(example_line, ExamplePayload)
    assert example_payload is None

    example_line = protocol.Line(b"EXAMPLE", b'{"a":"x","b":1}')
    example_payload = parser.try_decode_json(example_line, ExamplePayload)
    assert example_payload is None


def test_line_from_payload():
    line = parser.line_from_payload(ExamplePayload(1, "x"))
    assert line == protocol.Line(b"EXAMPLE", msgspec.Raw(b'{"a":1,"b":"x"}'))
