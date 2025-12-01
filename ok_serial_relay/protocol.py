"""Basic serial-line protocol definitions"""

import anycrc  # type: ignore
import base64
import logging
import msgspec
import re

logger = logging.getLogger(__name__)

class Line(msgspec.Struct):
    """Basic unit of serial port exchange"""
    action: bytes
    json: bytes


class TimeQueryPayload(msgspec.Struct, array_like=True):
    ACTION = b"Tq"
    yyyymmdd: int
    hhmmssmmm: int


class TimeReplyPayload(msgspec.Struct, array_like=True):
    ACTION = b"Tr"
    yyyymmdd: int
    hhmmssmmm: int
    rx_msec: int
    tx_msec: int
    profile_id: int
    profile_len: int


class ProfileQueryPayload(msgspec.Struct, array_like=True):
    ACTION = b"Pq"
    start: int
    count: int


class ProfileReplyPayload(msgspec.Struct, array_like=True):
    ACTION = b"Pr"
    type: str
    data: list


TIME_QUERY_ACTION = "Tq"  # [YYYYMMDD, HHMMSSmmm]
TIME_REPLY_ACTION = "Tr"  # [Tq1, Tq2, rx-msec, tx-msec, prof-id, prof-len]

PROFILE_QUERY_ACTION = "Pq"  # [start, count]
PROFILE_REPLY_ACTION = "Pr"  # [entry-type (str), ...]

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

def line_from_bytes(data: bytes) -> Line | None:
    match = _LINE_RE.fullmatch(data)
    if not match:
        logger.debug("No match: %s", data)
        return None
    action, json, check = match.groups()
    if not check.startswith(b"!"):
        check_bytes = base64.urlsafe_b64decode(b"A" + check)
        check_value = int.from_bytes(check_bytes, "big")
        actual_crc = _crc18.calc(action + json)
        if check_value != actual_crc:
            logger.warning(
                "CRC mismatch: 0x%x (%s) != 0x%x",
                check_value, check_bytes.decode(), actual_crc
            )
            return None
    return Line(action, json)


_ACTION_RE = re.compile(rb"\w*")

def line_to_bytes(line: Line) -> bytes:
    assert _ACTION_RE.fullmatch(line.action)
    out = bytearray(line.action)
    if line.action and line.json[0] not in b'"[{':
        out.extend(b" ")
    out.extend(line.json)
    if line.json[-1] not in b'}]"':
        out.extend(b" ")
    check_bytes = _crc18.calc(out).to_bytes(3, "big")
    out.extend(base64.urlsafe_b64encode(check_bytes)[1:])
    return bytes(out)
