"""Unit tests for ok_serial_relay.timing"""

import ok_serial_relay.protocol as proto
import ok_serial_relay.timing as timing

JAN_1_2025_123456Z = 1735734896

def test_outgoing_query_timing():
    start = JAN_1_2025_123456Z
    tracker = timing.TimeTracker(when=start, profile_id=0, profile_len=0)
    assert tracker.has_payload_to_send(when=start)
    assert tracker.has_payload_to_send(when=start + 1.5)
    assert (
        tracker.get_payload_to_send(when=start + 1.555) ==  # late publish
        proto.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123457555)
    )
    assert not tracker.has_payload_to_send(when=start + 1.555)
    assert tracker.get_payload_to_send(when=start + 1.555) is None

    # Last publish was T+1.555s, next publish slips to T+5.555s
    assert not tracker.has_payload_to_send(when=start + 5.5)
    assert tracker.get_payload_to_send(when=start + 5.5) is None
    assert tracker.has_payload_to_send(when=start + 5.556)  # slipped forward
    assert (
        tracker.get_payload_to_send(when=start + 6.0) ==    # late again
        proto.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123502000)
    )
    assert not tracker.has_payload_to_send(when=start + 6.0)
    assert tracker.get_payload_to_send(when=start + 6.0) is None

    # Actual publish was T+6s, next publish stays at T+10.555s (limited slip)
    assert not tracker.has_payload_to_send(when=start + 10.5)
    assert tracker.get_payload_to_send(when=start + 10.5) is None
    assert tracker.has_payload_to_send(when=start + 10.556)  # limited slip
    assert (
        tracker.get_payload_to_send(when=start + 10.6) ==
        proto.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123506600)
    )
    assert not tracker.has_payload_to_send(when=start + 10.6)
    assert tracker.get_payload_to_send(when=start + 10.6) is None


def test_incoming_query_replies():
    start = JAN_1_2025_123456Z
    tracker = timing.TimeTracker(when=start, profile_id=123, profile_len=456)
    tracker.get_payload_to_send(when=start)
    assert not tracker.has_payload_to_send(when=start + 3)

    tracker.handle_received_query(
        proto.TimeQueryPayload(yyyymmdd=20260501, hhmmssmmm=123456888),
        when=start + 3
    )
    assert(
        tracker.get_payload_to_send(when=start + 3.456) ==
        proto.TimeReplyPayload(20260501, 123456888, 3000, 3456, 123, 456)
    )
    assert not tracker.has_payload_to_send(when=start + 4)

    assert tracker.has_payload_to_send(when=start + 6)  # regular outgoing query
    tracker.handle_received_query(
        proto.TimeQueryPayload(yyyymmdd=20260501, hhmmssmmm=123502888),
        when=start + 6
    )
    assert(
        tracker.get_payload_to_send(when=start + 6.1) ==  # reply has priority
        proto.TimeReplyPayload(20260501, 123502888, 6000, 6100, 123, 456)
    )
    assert(
        tracker.get_payload_to_send(when=start + 6.2) ==  # then query happens
        proto.TimeQueryPayload(yyyymmdd=20250101, hhmmssmmm=123502200)
    )
    assert not tracker.has_payload_to_send(when=start + 6.3)  # done for now
