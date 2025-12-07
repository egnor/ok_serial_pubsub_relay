"""Session-level protocol state"""

import logging

from ok_serial_relay import protocol
from ok_serial_relay import parser
import ok_serial_relay.timing

logger = logging.getLogger(__name__)

INCOMING_LINE_MAX = 65536


class Session:
    def __init__(
        self,
        *,
        when: float,
        profile: list[protocol.ProfileEntryPayload] = [],
    ) -> None:
        self._in_bytes = bytearray()
        self._in_bytes_time = 0.0
        self._in_messages: list[protocol.PublishPayload] = []
        self._local_profile = profile[:]
        self._remote_profile: list[protocol.ProfileEntryPayload] = []
        self._time_tracker = ok_serial_relay.timing.TimeTracker(
            when=when,
            profile_id=hash(tuple(profile)),
            profile_len=len(profile),
        )

    def get_bytes_to_send(self, *, when: float, buffer_empty: bool) -> bytes:
        to_send: protocol.Line | None = None
        if self._time_tracker.has_payload_to_send(when=when):
            if not buffer_empty:
                return b""  # priority buffer-empty for timed message
            if payload := self._time_tracker.get_payload_to_send(when=when):
                to_send = parser.line_from_payload(payload)

        if to_send:
            logger.debug("Sending: %s", to_send)
            return parser.line_to_bytes(to_send)
        else:
            return b""

    def on_bytes_received(self, data: bytes, *, when: float) -> None:
        while data:
            if not self._in_bytes:
                self._in_bytes_time = when
            if (newline_pos := data.find(b"\n")) >= 0:
                self._in_bytes.extend(data[:newline_pos])
                self._parse_buffered_line()
                self._in_bytes[:] = b""
                data = data[newline_pos + 1 :]
            else:
                self._in_bytes.extend(data)
                if len(self._in_bytes) >= INCOMING_LINE_MAX:
                    self._in_bytes[:] = b""
                return

    def get_received_messages(self) -> list[protocol.PublishPayload]:
        out, self._in_messages = self._in_messages, []
        return out

    def _parse_buffered_line(self) -> None:
        if not (line := parser.try_parse_line(self._in_bytes)):
            return
        logger.debug("Received: %s", line)
        if qp := parser.try_decode_json(line, protocol.TimeQueryPayload):
            self._time_tracker.on_query_received(qp, when=self._in_bytes_time)
        elif rp := parser.try_decode_json(line, protocol.TimeReplyPayload):
            self._time_tracker.on_reply_received(rp, when=self._in_bytes_time)
        elif mp := parser.try_decode_json(line, protocol.PublishPayload):
            self._in_messages.append(mp)
