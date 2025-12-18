"""Protocol parser"""

import anycrc  # type: ignore
import base64
import logging
import msgspec
import re
import typing

from ok_serial_relay.line_types import Line

logger = logging.getLogger(__name__)

# https://users.ece.cmu.edu/~koopman/crc/c18/0x25f53.txt
# an 18-bit (3-base64-char) CRC with decent protection across lengths
_crc18 = anycrc.CRC(
    width=18,
    poly=0xBEA7,
    init=0x00000,
    refin=False,
    refout=False,
    xorout=0x00000,
)
assert _crc18.calc("123456789") == 0x23A17

_PREFIX_RE = re.compile(rb"\w*")

_LINE_RE = re.compile(
    rb"\s*(\w*)"  # prefix
    rb"(\s*(?:\".*\"|{.*}|\[.*\]|(?:^|\s)[\w.-]+\s)\s*)"  # json
    rb"([\w-]{3}|~~~)\s*"  # crc/bypass
)


def try_from_bytes(data: bytes) -> Line | None:
    match = _LINE_RE.fullmatch(data)
    if not match:
        logger.debug("Bad format: %s", data)
        return None
    prefix, payload, check = match.groups()
    if not check.startswith(b"~"):
        check_bytes = base64.urlsafe_b64decode(b"A" + check)
        check_value = int.from_bytes(check_bytes, "big")
        actual_crc = _crc18.calc(prefix + payload)
        if check_value != actual_crc:
            logger.warning(
                "CRC mismatch: 0x%x (%s) != 0x%x",
                check_value,
                check_bytes.decode(),
                actual_crc,
                exc_info=True,
            )
            return None
    return Line(prefix=prefix, payload=msgspec.Raw(payload))


def to_bytes(line: Line | None) -> bytes:
    if not line:
        return b""
    assert _PREFIX_RE.fullmatch(line.prefix)
    out = bytearray(line.prefix)
    if out and line.payload[0] not in b'"[{':
        out.extend(b" ")
    out.extend(line.payload)
    if line.payload[-1] not in b'}]"':
        out.extend(b" ")
    check_bytes = _crc18.calc(out).to_bytes(3, "big")
    out.extend(base64.urlsafe_b64encode(check_bytes)[1:])
    return bytes(out)


_T = typing.TypeVar("_T", bound=msgspec.Struct)


def try_payload(line: Line | None, payload_type: type[_T]) -> _T | None:
    if line and line.prefix == getattr(payload_type, "PREFIX", None):
        try:
            return msgspec.json.decode(line.payload, type=payload_type)
        except msgspec.DecodeError:
            name = payload_type.__name__
            logger.warning("Bad %s: %s", name, line.payload, exc_info=True)
    return None


def from_payload(payload: _T) -> Line:
    prefix = getattr(type(payload), "PREFIX")
    payload_json = msgspec.json.encode(payload)
    return Line(prefix=prefix, payload=msgspec.Raw(payload_json))
