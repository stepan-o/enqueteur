from __future__ import annotations

"""Runtime message-key helpers for backend-to-frontend localization contracts."""

from typing import Any
import re

_NON_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")


def command_rejected_message_contract(
    *,
    reason_code: str,
    client_cmd_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    key = f"live.command_rejected.{_normalize_token(reason_code)}"
    params: dict[str, Any] = {"reason_code": reason_code}
    if isinstance(client_cmd_id, str) and client_cmd_id:
        params["client_cmd_id"] = client_cmd_id
    return key, params


def live_warn_message_contract(*, code: str) -> tuple[str, dict[str, Any]]:
    return f"live.warn.{_normalize_token(code)}", {"code": code}


def live_error_message_contract(*, code: str, fatal: bool) -> tuple[str, dict[str, Any]]:
    return f"live.error.{_normalize_token(code)}", {"code": code, "fatal": bool(fatal)}


def launch_error_message_contract(
    *,
    code: str,
    field: str | None = None,
    phase_gate: str | None = None,
    status_code: int | None = None,
) -> tuple[str, dict[str, Any]]:
    key = f"launch.error.{_normalize_token(code)}"
    params: dict[str, Any] = {"code": code}
    if isinstance(field, str) and field:
        params["field"] = field
    if isinstance(phase_gate, str) and phase_gate:
        params["phase_gate"] = phase_gate
    if isinstance(status_code, int):
        params["status_code"] = status_code
    return key, params


def _normalize_token(value: str) -> str:
    normalized = _NON_TOKEN_PATTERN.sub("_", value.strip().lower()).strip("_")
    return normalized or "unknown"
