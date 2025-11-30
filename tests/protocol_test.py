"""Unit tests for ok_serial_relay.protocol"""

import ok_serial_relay.protocol as proto


def test_line_from_bytes():
    pass


def test_line_to_bytes():
    assert (
        proto.line_to_bytes(proto.Line(b"ACTION", [1,2,{"x": 3}])) ==
        b'ACTION[1,2,{"x":3}]ff88'
    )
    assert (
        proto.line_to_bytes(proto.Line(b"ACTION", 31337)) ==
        b'ACTION 31337 28ac'
    )
    assert (
        proto.line_to_bytes(proto.Line(b"", {"foo": "bar"})) ==
        b'{"foo":"bar"}27b3'
    )
    assert (
        proto.line_to_bytes(proto.Line(b"", None)) ==
        b'null 4f28'
    )
