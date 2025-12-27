"""Session-level protocol state"""

import logging
import msgspec
import typing

from ok_serial_relay import foxglove_jsonschema
from ok_serial_relay import line_types
from ok_serial_relay import line_parsing
from ok_serial_relay import time_tracker

logger = logging.getLogger(__name__)

INCOMING_LINE_MAX = 65536


class IncomingMessage(msgspec.Struct):
    topic: str
    body: typing.Any  # JSON payload
    schema_data: bytes
    unixtime: float = 0.0
    msec: int = 0


class Session:
    def __init__(
        self,
        *,
        when: float,
        profile: list[line_types.ProfileEntryBase] = [],
    ) -> None:
        self._in_bytes = bytearray()
        self._in_bytes_time = 0.0
        self._in_messages: list[IncomingMessage] = []
        self._local_profile = profile[:]
        self._remote_profile: list[line_types.ProfileEntryBase] = []
        self._time_tracker = time_tracker.TimeTracker(
            when=when,
            profile_id=hash(tuple(profile)),
            profile_len=len(profile),
        )

    def get_bytes_to_send(self, *, when: float, buffer_empty: bool) -> bytes:
        to_send: line_types.Line | None = None
        if self._time_tracker.has_payload_to_send(when=when):
            if not buffer_empty:
                return b""  # priority buffer-empty for timed message
            if payload := self._time_tracker.get_payload_to_send(when=when):
                to_send = line_parsing.from_payload(payload)

        if to_send:
            logger.debug("To send: %s", to_send)
            return line_parsing.to_bytes(to_send)
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

    def get_received_messages(self) -> list[IncomingMessage]:
        out, self._in_messages = self._in_messages, []
        return out

    def _parse_one_line(self) -> None:
        if not (line := line_parsing.try_from_bytes(self._in_bytes)):
            return
        if payload := line_parsing.try_get_payload(line):
            logger.debug("Received: %s", payload)
            when = self._in_bytes_time
            match payload:
                case line_types.TimeQueryPayload as tqp:
                    self._time_tracker.on_query_received(tqp, when=when)
                case line_types.TimeReplyPayload as trp:
                    self._time_tracker.on_reply_received(trp, when=when)
                case line_types.PublishPayload as mp:
                    self._in_messages.append(self._import_message(mp))
                case _ as unk:
                    logger.warning("Unknown payload: %s", unk)
        else:
            logger.warning("Unknown: %s", line)

    def _import_message(self, m: line_types.PublishPayload) -> IncomingMessage:
        schema = m.schema_name
        if not schema:
            schema_data = b""
        elif schema.startswith("json:"):
            schema_data = schema[5:].encode()
        elif schema.startswith("fox:"):
            logger.warning("Bad Foxglove schema: %s", m)
            schema_data = foxglove_jsonschema.get(schema[4:])
            schema_data = schema_data or b"ERROR:NOTFOUND:" + schema.encode()
        else:
            logger.warning("Bad schema type: %s", m)
            schema_data = b"ERROR:INVALID:" + schema.encode()

        return IncomingMessage(
            topic=m.topic,
            body=m.body,
            schema_data=schema_data,
            unixtime=self._time_tracker.try_from_msec(m.msec),
            msec=m.msec,
        )
