"""Basic serial-line protocol definitions"""

import pydantic
import typing


class Line(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)
    prefix: bytes
    payload: bytes  # Raw JSON bytes


class MessagePayload(typing.NamedTuple):
    topic: str
    body: typing.Any  # Parsed JSON value (not bytes) for embedding in array
    msec: int = 0
    schema_name: str = ""


class ProfileEntryPayload(typing.NamedTuple):
    entry_index: int
    type: str
    data: list


class TimeQueryPayload(typing.NamedTuple):
    yyyymmdd: int
    hhmmssmmm: int


class TimeReplyPayload(typing.NamedTuple):
    yyyymmdd: int
    hhmmssmmm: int
    rx_msec: int
    tx_msec: int
    profile_id: int
    profile_len: int


MessagePayload.PREFIX = b""  # type: ignore[attr-defined]
ProfileEntryPayload.PREFIX = b"Pe"  # type: ignore[attr-defined]
TimeQueryPayload.PREFIX = b"Tq"  # type: ignore[attr-defined]
TimeReplyPayload.PREFIX = b"Tr"  # type: ignore[attr-defined]
