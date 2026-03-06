from __future__ import annotations

"""Minimal runtime-facing boundary for MBAM Case Truth.

This is intentionally small for Phase 1A and does not integrate tick flow.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .models import CaseState


@dataclass(frozen=True)
class MbamCaseBundle:
    """Container for canonical MBAM Case Truth state."""

    case_state: CaseState


@runtime_checkable
class CaseTruthProvider(Protocol):
    """Protocol for systems that can provide canonical case truth."""

    def get_case_state(self) -> CaseState: ...


__all__ = ["MbamCaseBundle", "CaseTruthProvider"]
