"""Basic serial-line protocol definitions"""

import anycrc  # type: ignore
import base64
import logging
import msgspec
import re
import typing

logger = logging.getLogger(__name__)

json_encoder = msgspec.json.Encoder()

class Line(msgspec.Struct, frozen=True):
    """Basic unit of serial port exchange"""
    action: bytes
    json: bytes

class TimeQueryPayload(msgspec.Struct, array_like=True, frozen=True):
    ACTION = b"Tq"
    yyyymmdd: int
    hhmmssmmm: int

class TimeReplyPayload(msgspec.Struct, array_like=True, frozen=True):
    ACTION = b"Tr"
    yyyymmdd: int
    hhmmssmmm: int
    rx_msec: int
    tx_msec: int
    profile_id: int
    profile_len: int

class ProfileQueryPayload(msgspec.Struct, array_like=True, frozen=True):
    ACTION = b"Pq"
    start: int
    count: int

class ProfileReplyPayload(msgspec.Struct, array_like=True, frozen=True):
    ACTION = b"Pr"
    index: int
    type: str
    data: list

# https://users.ece.cmu.edu/~koopman/crc/c18/0x25f53.txt
# an 18-bit (3-base64-char) CRC with decent protection across lengths
_crc18 = anycrc.CRC(
  width=18, poly=0xbea7, init=0x00000,
  refin=False, refout=False, xorout=0x00000
)
assert _crc18.calc("123456789") == 0x23a17

_LINE_RE = re.compile(
    rb"\s*(\w*)"                           # action
    rb"(^.*\s|\s.*\s|\[.*\]|{.*}|\".*\")"  # json
    rb"([\w-]{3}|![Cc][Kk])\s*"            # crc18-base64 OR "!ck" marker
)

def try_parse_line(data: bytes) -> Line | None:
    match = _LINE_RE.fullmatch(data)
    if not match:
        logger.debug("Bad format: %s", data)
        return None
    action, json, check = match.groups()
    if not check.startswith(b"!"):
        check_bytes = base64.urlsafe_b64decode(b"A" + check)
        check_value = int.from_bytes(check_bytes, "big")
        actual_crc = _crc18.calc(action + json)
        if check_value != actual_crc:
            logger.warning(
                "CRC mismatch: 0x%x (%s) != 0x%x",
                check_value, check_bytes.decode(), actual_crc, exc_info=True
            )
            return None
    return Line(action, json)


_ACTION_RE = re.compile(rb"\w*")

def line_to_bytes(line: Line) -> bytes:
    assert _ACTION_RE.fullmatch(line.action)
    out = bytearray(line.action)
    if out and line.json[0] not in b'"[{':
        out.extend(b" ")
    out.extend(line.json)
    if line.json[-1] not in b'}]"':
        out.extend(b" ")
    check_bytes = _crc18.calc(out).to_bytes(3, "big")
    out.extend(base64.urlsafe_b64encode(check_bytes)[1:])
    return bytes(out)


ST = typing.TypeVar("ST", bound=msgspec.Struct)

def try_decode_json(line: Line, as_type: type[ST]) -> ST | None:
    action = getattr(as_type, "ACTION")
    assert isinstance(action, bytes), f"no/bad ACTION: {as_type.__name__}"
    if action == line.action:
        try:
            return msgspec.json.decode(line.json, type=as_type)
        except msgspec.DecodeError:
            logger.warning(
                "Decode error (%s): %s", as_type.__name__, line.json,
                exc_info=True
            )
    return None


def line_from_payload(payload: msgspec.Struct) -> Line:
    action = getattr(payload, "ACTION")
    assert isinstance(action, bytes), f"no/bad ACTION: {payload}"
    return Line(action, json_encoder.encode(payload))
