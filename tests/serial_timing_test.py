"""Unit tests for ok_serial_relay.timing"""

from ok_serial_relay import serial_protocol
from ok_serial_relay import serial_timing

JAN_1_2025_123456Z = 1735734896


def test_outgoing_query_timing():
    start = JAN_1_2025_123456Z
    tracker = serial_timing.TimeTracker(when=start, profile_id=0, profile_len=0)
    assert tracker.has_payload_to_send(when=start)
    assert tracker.has_payload_to_send(when=start + 1.5)
    assert tracker.get_payload_to_send(
        when=start + 1.555
    ) == serial_protocol.TimeQueryPayload(  # late publish
        yyyymmdd=20250101, hhmmssmmm=123457555
    )
    assert not tracker.has_payload_to_send(when=start + 1.555)
    assert tracker.get_payload_to_send(when=start + 1.555) is None

    # Last publish was T+1.555s, next publish slips to T+5.555s
    assert not tracker.has_payload_to_send(when=start + 5.5)
    assert tracker.get_payload_to_send(when=start + 5.5) is None
    assert tracker.has_payload_to_send(when=start + 5.556)  # slipped forward
    assert tracker.get_payload_to_send(
        when=start + 6.0
    ) == serial_protocol.TimeQueryPayload(  # late again
        yyyymmdd=20250101, hhmmssmmm=123502000
    )
    assert not tracker.has_payload_to_send(when=start + 6.0)
    assert tracker.get_payload_to_send(when=start + 6.0) is None

    # Actual publish was T+6s, next publish stays at T+10.555s (limited slip)
    assert not tracker.has_payload_to_send(when=start + 10.5)
    assert tracker.get_payload_to_send(when=start + 10.5) is None
    assert tracker.has_payload_to_send(when=start + 10.556)  # limited slip
    assert tracker.get_payload_to_send(
        when=start + 10.6
    ) == serial_protocol.TimeQueryPayload(
        yyyymmdd=20250101, hhmmssmmm=123506600
    )
    assert not tracker.has_payload_to_send(when=start + 10.6)
    assert tracker.get_payload_to_send(when=start + 10.6) is None


def test_incoming_query_replying():
    start = JAN_1_2025_123456Z
    tracker = serial_timing.TimeTracker(
        when=start, profile_id=123, profile_len=456
    )
    tracker.get_payload_to_send(when=start)
    assert not tracker.has_payload_to_send(when=start + 3)

    tracker.on_query_received(
        serial_protocol.TimeQueryPayload(
            yyyymmdd=20260501, hhmmssmmm=123456888
        ),
        when=start + 3,
    )
    assert tracker.get_payload_to_send(
        when=start + 3.456
    ) == serial_protocol.TimeReplyPayload(
        20260501, 123456888, 3000, 3456, 123, 456
    )
    assert not tracker.has_payload_to_send(when=start + 4)

    assert tracker.has_payload_to_send(when=start + 6)  # regular outgoing query
    tracker.on_query_received(
        serial_protocol.TimeQueryPayload(
            yyyymmdd=20260501, hhmmssmmm=123502888
        ),
        when=start + 6,
    )
    assert tracker.get_payload_to_send(
        when=start + 6.1
    ) == serial_protocol.TimeReplyPayload(  # reply has priority
        20260501, 123502888, 6000, 6100, 123, 456
    )
    assert tracker.get_payload_to_send(
        when=start + 6.2
    ) == serial_protocol.TimeQueryPayload(  # then query happens
        yyyymmdd=20250101, hhmmssmmm=123502200
    )
    assert not tracker.has_payload_to_send(when=start + 6.3)  # done for now
