"""Basic serial-line protocol definitions"""

import msgspec


class Line(msgspec.Struct, frozen=True):
    prefix: bytes
    payload: msgspec.Raw


class MessagePayload(
    msgspec.Struct, array_like=True, frozen=True, omit_defaults=True
):
    PREFIX = b""
    topic: str
    body: msgspec.Raw
    msec: int = 0
    schema: str = ""


class ProfileEntryPayload(msgspec.Struct, array_like=True, frozen=True):
    PREFIX = b"Pe"
    index: int
    type: str
    data: list


class TimeQueryPayload(msgspec.Struct, array_like=True, frozen=True):
    PREFIX = b"Tq"
    yyyymmdd: int
    hhmmssmmm: int


class TimeReplyPayload(msgspec.Struct, array_like=True, frozen=True):
    PREFIX = b"Tr"
    yyyymmdd: int
    hhmmssmmm: int
    rx_msec: int
    tx_msec: int
    profile_id: int
    profile_len: int
