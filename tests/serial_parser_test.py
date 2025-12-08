"""Unit tests for ok_serial_relay.protocol"""

import msgspec

from ok_serial_relay import serial_parser
from ok_serial_relay.serial_protocol import Line


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


def test_to_bytes():
    for prefix, payload, data in LINE_CHECKS:
        line = Line(prefix, msgspec.json.encode(payload))
        assert serial_parser.to_bytes(line) == data


def test_try_parse():
    for prefix, payload, data in LINE_CHECKS:
        line = serial_parser.try_parse(data)
        assert line.prefix == prefix
        assert msgspec.json.decode(line.payload) == payload


def test_try_parse_unchecked():
    for prefix, payload, data in LINE_CHECKS:
        line_ltag = serial_parser.try_parse(data[:-3] + b"~~~")
        line_utag = serial_parser.try_parse(data[:-3] + b"~~~")
        assert line_ltag.prefix == line_utag.prefix == prefix
        assert msgspec.json.decode(line_ltag.payload) == payload
        assert msgspec.json.decode(line_utag.payload) == payload


def test_try_as():
    example_line = Line(b"EXAMPLE", b'{"a":1,"b":"x"}')
    example_payload = serial_parser.try_as(example_line, ExamplePayload)
    assert example_payload == ExamplePayload(1, "x")

    example_line = Line(b"OTHER", b'{"a":2,"b":"y"}')
    example_payload = serial_parser.try_as(example_line, ExamplePayload)
    assert example_payload is None

    example_line = Line(b"EXAMPLE", b'{"a":"x","b":1}')
    example_payload = serial_parser.try_as(example_line, ExamplePayload)
    assert example_payload is None


def test_from_payload():
    line = serial_parser.from_payload(ExamplePayload(1, "x"))
    assert line == Line(b"EXAMPLE", msgspec.Raw(b'{"a":1,"b":"x"}'))
