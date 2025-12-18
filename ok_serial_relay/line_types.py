"""Basic serial-line protocol definitions"""

from typing import Any, NamedTuple

from pydantic import BaseModel, ConfigDict, TypeAdapter


class Line(BaseModel):
    model_config = ConfigDict(frozen=True)
    prefix: bytes
    payload: bytes  # Raw JSON bytes


# Decorator for payload types associated with a prefix and adapter for parsing
def payload(prefix: bytes):
    def decorator(cls: type) -> type:
        cls.PREFIX = prefix  # type: ignore[attr-defined]
        cls.Adapter = TypeAdapter(cls)  # type: ignore[attr-defined]
        return cls

    return decorator


@payload(b"")
class MessagePayload(NamedTuple):
    topic: str
    body: Any  # Parsed JSON value (not bytes) for embedding in array
    msec: int = 0
    schema_name: str = ""


@payload(b"Pe")
class ProfileEntryPayload(NamedTuple):
    entry_index: int
    type: str
    data: list


@payload(b"Tq")
class TimeQueryPayload(NamedTuple):
    yyyymmdd: int
    hhmmssmmm: int


@payload(b"Tr")
class TimeReplyPayload(NamedTuple):
    yyyymmdd: int
    hhmmssmmm: int
    rx_msec: int
    tx_msec: int
    profile_id: int
    profile_len: int
