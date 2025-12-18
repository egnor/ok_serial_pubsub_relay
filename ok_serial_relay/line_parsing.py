"""Protocol parser"""

import anycrc  # type: ignore
import base64
import json
import logging
import re
from typing import NamedTuple, TypeVar

from pydantic import ValidationError

from ok_serial_relay.line_types import Line

logger = logging.getLogger(__name__)

_NT = TypeVar("_NT", bound=NamedTuple)

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
    prefix, json_bytes, check = match.groups()
    if not check.startswith(b"~"):
        check_bytes = base64.urlsafe_b64decode(b"A" + check)
        check_value = int.from_bytes(check_bytes, "big")
        actual_crc = _crc18.calc(prefix + json_bytes)
        if check_value != actual_crc:
            logger.warning(
                "CRC mismatch: 0x%x (%s) != 0x%x",
                check_value,
                check_bytes.decode(),
                actual_crc,
                exc_info=True,
            )
            return None
    return Line(prefix=prefix, payload=json_bytes)


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


def try_payload(line: Line | None, payload_type: type[_NT]) -> _NT | None:
    prefix = getattr(payload_type, "PREFIX", b"")
    adapter = getattr(payload_type, "Adapter", None)
    if adapter is None:
        raise ValueError(
            f"{payload_type.__name__} missing .Adapter (use @payload)"
        )
    if line and prefix == line.prefix:
        try:
            return adapter.validate_json(line.payload)
        except ValidationError:
            logger.warning(
                "Bad decode (%s): %s",
                payload_type.__name__,
                line.payload,
                exc_info=True,
            )
    return None


def from_payload(payload: _NT, *, omit_defaults: bool = False) -> Line:
    prefix = getattr(type(payload), "PREFIX", b"")

    if omit_defaults and hasattr(payload, "_field_defaults"):
        defaults = payload._field_defaults
        values = list(payload)
        # Trim trailing default values
        while values and payload._fields:
            field = payload._fields[len(values) - 1]
            if field in defaults and values[-1] == defaults[field]:
                values.pop()
            else:
                break
    else:
        values = list(payload)

    json_bytes = json.dumps(values, separators=(",", ":")).encode()
    return Line(prefix=prefix, payload=json_bytes)
