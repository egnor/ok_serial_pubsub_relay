"""Unit tests for ok_serial_relay.protocol"""

import msgspec

import ok_serial_relay.protocol as proto

class ExamplePayload(msgspec.Struct):
    ACTION = b"EXAMPLE"
    a: int
    b: str

LINE_CHECKS = [
    (b"ACTION", [1,2,{"x": 3}], b'ACTION[1,2,{"x":3}]-aS'),
    (b"", {"foo": "bar"}, b'{"foo":"bar"}rTj'),
    (b"", None, b"null 28q"),
    (b"ACTION", None, b"ACTION null hmW"),
    (b"", [], b"[]RRw"),
    (b"ACTION", [], b"ACTION[]qA-"),
    (b"", 0, b"0 xcB"),
    (b"ACTION", 0, b"ACTION 0 4FE"),
    (b"", 31337, b"31337 WZx"),
    (b"ACTION", 31337, b"ACTION 31337 WNd"),
    (b"", 1.2345, b"1.2345 _eX"),
    (b"ACTION", 1.2345, b"ACTION 1.2345 mUw"),
]


def test_line_to_bytes():
    for (action, payload, data) in LINE_CHECKS:
        line = proto.Line(action, msgspec.json.encode(payload))
        assert(proto.line_to_bytes(line) == data)


def test_line_from_bytes():
    for (action, payload, data) in LINE_CHECKS:
        line = proto.try_parse_line(data)
        assert line.action == action
        assert msgspec.json.decode(line.json) == payload


def test_line_from_bytes_unchecked():
    for (action, payload, data) in LINE_CHECKS:
        line_ltag = proto.try_parse_line(data[:-3] + b"!ck")
        line_utag = proto.try_parse_line(data[:-3] + b"!CK")
        assert line_ltag.action == line_utag.action == action
        assert msgspec.json.decode(line_ltag.json) == payload
        assert msgspec.json.decode(line_utag.json) == payload


def test_try_decode_json():
    example_line = proto.Line(b"EXAMPLE", b'{"a":1,"b":"x"}')
    example_payload = proto.try_decode_json(example_line, ExamplePayload)
    assert example_payload == ExamplePayload(1, "x")

    example_line = proto.Line(b"OTHER", b'{"a":2,"b":"y"}')
    example_payload = proto.try_decode_json(example_line, ExamplePayload)
    assert example_payload is None

    example_line = proto.Line(b"EXAMPLE", b'{"a":"x","b":1}')
    example_payload = proto.try_decode_json(example_line, ExamplePayload)
    assert example_payload is None


def test_line_from_payload():
    line = proto.line_from_payload(ExamplePayload(1, "x"))
    assert line == proto.Line(b"EXAMPLE", b'{"a":1,"b":"x"}')
