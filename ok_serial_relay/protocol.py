"""Basic serial-line protocol definitions"""

import anycrc  # type: ignore
import logging
import msgspec
import re

class Line(msgspec.Struct):
    """Basic unit of serial port exchange"""

    action: bytes
    value: object


_logger = logging.getLogger(__name__)

# https://reveng.sourceforge.io/crc-catalogue/16.htm#crc.cat.crc-16-opensafety-b
# https://users.ece.cmu.edu/~koopman/crc/c16/0xbaad_len.txt
_crc16 = anycrc.Model("CRC16-OPENSAFETY-B")

_ACTION_RE = re.compile(rb"\w*")
_LINE_RE = re.compile(rb"\s*(\w*)(\W.*\W)([0-9A-Fa-f]{4}|!CRC)\s*")


def line_from_bytes(data: bytes) -> Line | None:
    match = _LINE_RE.fullmatch(data)
    if not match:
        return None
    action, json, check = match.groups()
    if check != b"!CRC":
        message_crc = int(check, 16)
        actual_crc = _crc16.calc(action + json)
        if message_crc != actual_crc:
            return None
    try:
        return Line(action, msgspec.json.decode(json))
    except msgspec.DecodeError:
        return None


def line_to_bytes(line: Line) -> bytes:
    assert _ACTION_RE.fullmatch(line.action)
    json = msgspec.json.encode(line.value)
    out = bytearray(line.action)
    out.extend(b" " if line.action and json[0] not in b'"[{' else b"")
    out.extend(json)
    out.extend(b" " if json[-1] not in b'}]"' else b"")
    out.extend(b"%04x" % _crc16.calc(out))
    return bytes(out)
