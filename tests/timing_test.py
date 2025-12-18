"""Unit tests for ok_serial_relay.timing"""

from ok_serial_relay import line_types
from ok_serial_relay import timing

JAN_1_2025_123456Z = 1735734896


def test_outgoing_query_timing():
    start = JAN_1_2025_123456Z
    tracker = timing.TimeTracker(when=start, profile_id=0, profile_len=0)
    assert tracker.has_payload_to_send(when=start)
    assert tracker.has_payload_to_send(when=start + 1.5)
    tqp = line_types.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123457555)
    assert tracker.get_payload_to_send(when=start + 1.555) == tqp
    assert not tracker.has_payload_to_send(when=start + 1.555)
    assert tracker.get_payload_to_send(when=start + 1.555) is None

    # Last publish was T+1.555s, next publish slips to T+5.555s
    assert not tracker.has_payload_to_send(when=start + 5.5)
    assert tracker.get_payload_to_send(when=start + 5.5) is None
    assert tracker.has_payload_to_send(when=start + 5.556)  # slipped forward
    tqp = line_types.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123502000)
    assert tracker.get_payload_to_send(when=start + 6.0) == tqp
    assert not tracker.has_payload_to_send(when=start + 6.0)
    assert tracker.get_payload_to_send(when=start + 6.0) is None

    # Actual publish was T+6s, next publish stays at T+10.555s (limited slip)
    assert not tracker.has_payload_to_send(when=start + 10.5)
    assert tracker.get_payload_to_send(when=start + 10.5) is None
    assert tracker.has_payload_to_send(when=start + 10.556)  # limited slip
    tqp = line_types.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123506600)
    assert tracker.get_payload_to_send(when=start + 10.6) == tqp
    assert not tracker.has_payload_to_send(when=start + 10.6)
    assert tracker.get_payload_to_send(when=start + 10.6) is None


def test_incoming_query_replying():
    start = JAN_1_2025_123456Z
    tracker = timing.TimeTracker(when=start, profile_id=123, profile_len=456)
    tracker.get_payload_to_send(when=start)
    assert not tracker.has_payload_to_send(when=start + 3)

    tracker.on_query_received(
        line_types.TimeQueryPayload(yyyymmdd=20260501, hhmmssmmm=123456888),
        when=start + 3,
    )
    trp = line_types.TimeReplyPayload(
        yyyymmdd=20260501,
        hhmmssmmm=123456888,
        rx_msec=3000,
        tx_msec=3456,
        profile_id=123,
        profile_len=456,
    )
    assert tracker.get_payload_to_send(when=start + 3.456) == trp
    assert not tracker.has_payload_to_send(when=start + 4)

    assert tracker.has_payload_to_send(when=start + 6)  # regular outgoing query
    tqp = line_types.TimeQueryPayload(yyyymmdd=20260501, hhmmssmmm=123502888)
    tracker.on_query_received(tqp, when=start + 6)
    trp = line_types.TimeReplyPayload(  # reply has priority
        yyyymmdd=20260501,
        hhmmssmmm=123502888,
        rx_msec=6000,
        tx_msec=6100,
        profile_id=123,
        profile_len=456,
    )
    assert tracker.get_payload_to_send(when=start + 6.1) == trp
    tqp = line_types.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123502200)
    assert tracker.get_payload_to_send(when=start + 6.2) == tqp
    assert not tracker.has_payload_to_send(when=start + 6.3)  # done for now
