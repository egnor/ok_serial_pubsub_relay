"""Protocol parser"""

import anycrc  # type: ignore
import base64
import logging
import msgspec
import re
import typing

from ok_serial_relay import serial_protocol

logger = logging.getLogger(__name__)

json_encoder = msgspec.json.Encoder()


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

_ST = typing.TypeVar("ST", bound=msgspec.Struct)


def try_parse(data: bytes) -> serial_protocol.Line | None:
    match = _LINE_RE.fullmatch(data)
    if not match:
        logger.debug("Bad format: %s", data)
        return None
    prefix, json, check = match.groups()
    if not check.startswith(b"~"):
        check_bytes = base64.urlsafe_b64decode(b"A" + check)
        check_value = int.from_bytes(check_bytes, "big")
        actual_crc = _crc18.calc(prefix + json)
        if check_value != actual_crc:
            logger.warning(
                "CRC mismatch: 0x%x (%s) != 0x%x",
                check_value,
                check_bytes.decode(),
                actual_crc,
                exc_info=True,
            )
            return None
    return serial_protocol.Line(prefix, msgspec.Raw(json))


def to_bytes(line: serial_protocol.Line | None) -> bytes:
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


def try_as(line: serial_protocol.Line | None, as_type: type[_ST]) -> _ST | None:
    prefix = getattr(as_type, "PREFIX")
    assert isinstance(prefix, bytes), f"No/bad PREFIX: {as_type.__name__}"
    if line and prefix == line.prefix:
        try:
            return msgspec.json.decode(line.payload, type=as_type)
        except msgspec.DecodeError:
            name, json = as_type.__name__, line.payload
            logger.warning("Bad decode (%s): %s", name, json, exc_info=True)
    return None


def from_payload(payload: msgspec.Struct) -> serial_protocol.Line:
    prefix = getattr(payload, "PREFIX")
    assert isinstance(prefix, bytes), f"no/bad PREFIX: {payload}"
    return serial_protocol.Line(
        prefix, msgspec.Raw(json_encoder.encode(payload))
    )
