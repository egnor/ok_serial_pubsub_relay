"""Session-level protocol state"""

import logging
import msgspec

import ok_serial_relay.protocol as proto
import ok_serial_relay.timing

logger = logging.getLogger(__name__)

INCOMING_LINE_MAX = 131072

class Session:
    def __init__(
        self, *, 
        when: float,
        profile: list[msgspec.Struct] = [],
    ) -> None:
        self._incoming_bytes = bytearray()
        self._local_profile = profile[:]
        self._time_tracker = ok_serial_relay.timing.TimeTracker(
            when=when,
            profile_id=hash(tuple(profile)),
            profile_len=len(profile),
        )

    def data_to_send(self, *, when: float, buffer_empty: bool) -> bytes:
        to_send: proto.Line | None = None
        if self._time_tracker.ready_to_send(when=when):
            if not buffer_empty:
                return b""  # priority buffer-empty for timed message
            payload = self._time_tracker.payload_to_send(when=when)
            if payload:
                json = msgspec.json.encode(payload)
                to_send = proto.Line(payload.ACTION, json)

        if to_send:
            logger.debug("Sending: %s", to_send)
            return proto.line_to_bytes(to_send)
        else:
            return b""

    def data_received(self, data: bytes, *, when: float) -> None:
        while data:
            newline_pos = data.find(b"\n")
            if newline_pos < 0:
                self._incoming_bytes.extend(data)
                if len(self._incoming_bytes) >= INCOMING_LINE_MAX:
                    self._incoming_bytes[:] = b""
                return

            self._incoming_bytes.extend(data[:newline_pos])
            self._line_data_received(self._incoming_bytes, when=when)
            self._incoming_bytes[:] = b""
            data = data[newline_pos + 1:]

    def _line_data_received(self, data: bytes, *, when: float) -> None:
        if not (line := proto.line_from_bytes(data)):
            return
        if line.action == proto.TimeQueryPayload.ACTION:
            query = msgspec.json.decode(line.json, type=proto.TimeQueryPayload)
            self._time_tracker.query_received(query, when=when)
        elif line.action == proto.TimeReplyPayload.ACTION:
            reply = msgspec.json.decode(line.json, type=proto.TimeReplyPayload)
            self._time_tracker.reply_received(reply, when=when)
