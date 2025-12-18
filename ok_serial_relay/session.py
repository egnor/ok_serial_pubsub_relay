"""Session-level protocol state"""

import logging
import pydantic
import typing

from ok_serial_relay import foxglove_jsonschema
from ok_serial_relay import line_types
from ok_serial_relay import line_parsing
from ok_serial_relay import timing

logger = logging.getLogger(__name__)

INCOMING_LINE_MAX = 65536


class ReceivedMessage(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)
    topic: str
    body: typing.Any  # JSON payload
    schema_data: bytes
    unixtime: float = 0.0
    msec: int = 0


class Session:
    @pydantic.validate_call
    def __init__(
        self,
        *,
        when: float,
        profile: list[line_types.ProfileEntryPayload] = [],
    ) -> None:
        self._in_bytes = bytearray()
        self._in_bytes_time = 0.0
        self._in_messages: list[ReceivedMessage] = []
        self._local_profile = profile[:]
        self._remote_profile: list[line_types.ProfileEntryPayload] = []
        self._time_tracker = timing.TimeTracker(
            when=when,
            profile_id=hash(tuple(profile)),
            profile_len=len(profile),
        )

    @pydantic.validate_call
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

    @pydantic.validate_call
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

    @pydantic.validate_call
    def get_received_messages(self) -> list[ReceivedMessage]:
        out, self._in_messages = self._in_messages, []
        return out

    def _parse_one_line(self) -> None:
        if not (line := line_parsing.try_from_bytes(self._in_bytes)):
            return
        if qp := line_parsing.try_payload(line, line_types.TimeQueryPayload):
            logger.debug("Received: %s", qp)
            self._time_tracker.on_query_received(qp, when=self._in_bytes_time)
        elif rp := line_parsing.try_payload(line, line_types.TimeReplyPayload):
            logger.debug("Received: %s", rp)
            self._time_tracker.on_reply_received(rp, when=self._in_bytes_time)
        elif mp := line_parsing.try_payload(line, line_types.MessagePayload):
            logger.debug("Received: %s", mp)
            self._in_messages.append(self._import_message(mp))
        else:
            logger.warning("Unknown: %s", line)

    def _import_message(self, m: line_types.MessagePayload) -> ReceivedMessage:
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

        return ReceivedMessage(
            topic=m.topic,
            body=m.body,
            schema_data=schema_data,
            unixtime=self._time_tracker.try_from_msec(m.msec),
            msec=m.msec,
        )
