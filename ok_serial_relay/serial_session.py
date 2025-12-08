"""Session-level protocol state"""

import logging
import msgspec

from ok_serial_relay import foxglove_jsonschema
from ok_serial_relay import serial_protocol
from ok_serial_relay import serial_parser
import ok_serial_relay.timing

logger = logging.getLogger(__name__)

INCOMING_LINE_MAX = 65536


class ReceivedMessage(msgspec.Struct, frozen=True):
    topic: str
    body: msgspec.Raw
    schema: bytes
    unixtime: float = 0.0
    msec: int = 0


class Session:
    def __init__(
        self,
        *,
        when: float,
        profile: list[serial_protocol.ProfileEntryPayload] = [],
    ) -> None:
        self._in_bytes = bytearray()
        self._in_bytes_time = 0.0
        self._in_messages: list[ReceivedMessage] = []
        self._local_profile = profile[:]
        self._remote_profile: list[serial_protocol.ProfileEntryPayload] = []
        self._time_tracker = ok_serial_relay.timing.TimeTracker(
            when=when,
            profile_id=hash(tuple(profile)),
            profile_len=len(profile),
        )

    def get_bytes_to_send(self, *, when: float, buffer_empty: bool) -> bytes:
        to_send: serial_protocol.Line | None = None
        if self._time_tracker.has_payload_to_send(when=when):
            if not buffer_empty:
                return b""  # priority buffer-empty for timed message
            if payload := self._time_tracker.get_payload_to_send(when=when):
                to_send = serial_parser.from_payload(payload)

        if to_send:
            logger.debug("To send: %s", to_send)
            return serial_parser.to_bytes(to_send)
        else:
            return b""

    def on_bytes_received(self, data: bytes, *, when: float) -> None:
        while data:
            if not self._in_bytes:
                self._in_bytes_time = when
            if (newline_pos := data.find(b"\n")) >= 0:
                self._in_bytes.extend(data[:newline_pos])
                self._parse_one_line()
                self._in_bytes[:] = b""
                data = data[newline_pos + 1 :]
            else:
                self._in_bytes.extend(data)
                if len(self._in_bytes) >= INCOMING_LINE_MAX:
                    self._in_bytes[:] = b""
                return

    def get_received_messages(self) -> list[ReceivedMessage]:
        out, self._in_messages = self._in_messages, []
        return out

    def _parse_one_line(self) -> None:
        if not (line := serial_parser.try_parse(self._in_bytes)):
            return
        if qp := serial_parser.try_as(line, serial_protocol.TimeQueryPayload):
            logger.debug("Received: %s", qp)
            self._time_tracker.on_query_received(qp, when=self._in_bytes_time)
        elif rp := serial_parser.try_as(line, serial_protocol.TimeReplyPayload):
            logger.debug("Received: %s", qp)
            self._time_tracker.on_reply_received(rp, when=self._in_bytes_time)
        elif mp := serial_parser.try_as(line, serial_protocol.MessagePayload):
            logger.debug("Received: %s", qp)
            self._in_messages.append(self._import_message(mp))
        else:
            logger.warning("Unknown: %s", line)

    def _import_message(
        self, m: serial_protocol.MessagePayload
    ) -> ReceivedMessage:
        if not m.schema:
            schema_data = b""
        elif m.schema.startswith("json:"):
            schema_data = m.schema[5:].encode()
        elif m.schema.startswith("fox:"):
            logger.warning("Bad Foxglove schema: %s", m)
            schema_data = foxglove_jsonschema.get(m.schema[4:])
            schema_data = schema_data or b"ERROR:NOTFOUND:" + m.schema.encode()
        else:
            logger.warning("Bad schema type: %s", m)
            schema_data = b"ERROR:INVALID:" + m.schema.encode()

        return ReceivedMessage(
            topic=m.topic,
            body=m.body,
            schema=schema_data,
            unixtime=self._time_tracker.try_convert(m.msec),
            msec=m.msec,
        )
