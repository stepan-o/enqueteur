from __future__ import annotations

"""Canonical JSON (RFC 8785-ish) encoder for deterministic bytes.

- UTF-8 output without BOM
- Objects: string keys only, sorted lexicographically by Unicode code points
- Arrays: preserve input order
- Numbers: deterministic formatting using Decimal(str(x));
  - reject NaN and Infinity/-Infinity
  - emit integers without leading zeros (except zero itself)
  - emit decimals without scientific notation where reasonable, with
    trailing zeros removed; "1.0" -> "1"
- Whitespace: none (compact)

This module intentionally avoids json.dumps defaults to ensure stable
number formatting and cross-platform determinism.
"""

from decimal import Decimal
from typing import Any
import math


def _escape_str(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def _format_decimal(d: Decimal) -> str:
    # Normalize to remove trailing zeros but keep a plain notation when possible
    # Build a non-scientific representation.
    sign, digits, exp = d.normalize().as_tuple()
    # Handle zero specially (normalize may produce exponent arbitrary)
    if not digits:
        return "0"
    int_digits = ''.join(str(x) for x in digits)
    if exp >= 0:
        # integer with trailing zeros
        s = int_digits + ("0" * exp)
        return ("-" + s) if sign else s
    # exp < 0 => decimal point
    point_pos = len(int_digits) + exp  # exp is negative
    if point_pos > 0:
        s = int_digits[:point_pos] + "." + int_digits[point_pos:]
    else:
        s = "0." + ("0" * (-point_pos)) + int_digits
    # strip trailing zeros after decimal
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return ("-" + s) if sign and s != "0" else s


def _format_number(n: Any) -> str:
    # bool must be handled elsewhere (since bool is int subclass)
    if isinstance(n, int) and not isinstance(n, bool):
        return str(n)
    if isinstance(n, float):
        if not math.isfinite(n):
            raise ValueError("Non-finite floats are not allowed (NaN/Infinity)")
        d = Decimal(str(n))
        return _format_decimal(d)
    raise TypeError("Unsupported number type for canonical JSON")


def _encode(obj: Any) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, str):
        return _escape_str(obj)
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return _format_number(obj)
    if isinstance(obj, list):
        return "[" + ",".join(_encode(v) for v in obj) + "]"
    if isinstance(obj, dict):
        # keys must be strings
        for k in obj.keys():
            if not isinstance(k, str):
                raise TypeError("Object keys must be strings for canonical JSON")
        parts = []
        for k in sorted(obj.keys()):
            parts.append(_escape_str(k) + ":" + _encode(obj[k]))
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"Unsupported type for canonical JSON: {type(obj).__name__}")


def canonical_json_bytes(obj: Any) -> bytes:
    """Encode obj into deterministic canonical JSON bytes (UTF-8, no BOM)."""
    s = _encode(obj)
    return s.encode("utf-8")


__all__ = ["canonical_json_bytes"]
