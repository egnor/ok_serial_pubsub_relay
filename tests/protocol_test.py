"""Unit tests for ok_serial_relay.protocol"""

import ok_serial_relay.protocol as proto

import logging
import msgspec

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
        line = proto.line_from_bytes(data)
        assert line.action == action
        assert line.json == msgspec.json.encode(payload)


def test_line_from_bytes_unchecked():
    for (action, payload, data) in LINE_CHECKS:
        line_ltag = proto.line_from_bytes(data[:-3] + b"!ck")
        line_utag = proto.line_from_bytes(data[:-3] + b"!CK")
        assert line_ltag.action == line_utag.action == action
        assert line_ltag.json == line_utag.json == msgspec.json.encode(payload)
