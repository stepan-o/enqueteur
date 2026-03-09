from __future__ import annotations

"""API contract and handler skeleton for deterministic case launch."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Mapping
import uuid

from backend.sim4.case_mbam import DifficultyProfile, resolve_seed_id

CASE_START_PATH = "/api/cases/start"
SUPPORTED_CASE_ID = "MBAM_01"
ENQUETEUR_ENGINE_NAME = "enqueteur"
ENQUETEUR_SCHEMA_VERSION = "enqueteur_mbam_1"
DEFAULT_WS_BASE_URL = "ws://localhost:7777/live"

StartCaseMode = Literal["playtest", "dev"]


class CaseStartValidationError(ValueError):
    """Raised when a start-case payload fails contract validation."""

    def __init__(self, message: str, *, field: str, code: str = "INVALID_REQUEST") -> None:
        super().__init__(message)
        self.field = field
        self.code = code


@dataclass(frozen=True)
class CaseStartRequest:
    """POST /api/cases/start request payload contract."""

    case_id: Literal["MBAM_01"]
    seed: str | int
    difficulty_profile: DifficultyProfile
    mode: StartCaseMode = "playtest"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "CaseStartRequest":
        case_id = payload.get("case_id")
        seed = payload.get("seed")
        difficulty_profile = payload.get("difficulty_profile")
        mode = payload.get("mode", "playtest")

        if case_id != SUPPORTED_CASE_ID:
            raise CaseStartValidationError(
                f"Unsupported case_id '{case_id}'. Expected '{SUPPORTED_CASE_ID}'.",
                field="case_id",
                code="UNSUPPORTED_CASE",
            )
        if not isinstance(seed, (str, int)):
            raise CaseStartValidationError(
                "seed must be a string or integer.",
                field="seed",
            )
        if isinstance(seed, str) and not seed.strip():
            raise CaseStartValidationError(
                "seed must be non-empty when provided as a string.",
                field="seed",
            )
        if difficulty_profile not in ("D0", "D1"):
            raise CaseStartValidationError(
                "difficulty_profile must be one of: D0, D1.",
                field="difficulty_profile",
            )
        if mode not in ("playtest", "dev"):
            raise CaseStartValidationError(
                "mode must be one of: playtest, dev.",
                field="mode",
            )

        return cls(
            case_id=SUPPORTED_CASE_ID,
            seed=seed.strip() if isinstance(seed, str) else seed,
            difficulty_profile=difficulty_profile,
            mode=mode,
        )


@dataclass(frozen=True)
class CaseStartResponse:
    """POST /api/cases/start success payload contract."""

    run_id: str
    world_id: str
    case_id: Literal["MBAM_01"]
    seed: str | int
    resolved_seed_id: str
    difficulty_profile: DifficultyProfile
    mode: StartCaseMode
    engine_name: Literal["enqueteur"]
    schema_version: Literal["enqueteur_mbam_1"]
    ws_url: str
    started_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "world_id": self.world_id,
            "case_id": self.case_id,
            "seed": self.seed,
            "resolved_seed_id": self.resolved_seed_id,
            "difficulty_profile": self.difficulty_profile,
            "mode": self.mode,
            "engine_name": self.engine_name,
            "schema_version": self.schema_version,
            "ws_url": self.ws_url,
            "started_at": self.started_at,
        }


@dataclass(frozen=True)
class StartedCaseRun:
    """Internal run registration record for future live-session wiring."""

    run_id: str
    world_id: str
    request: CaseStartRequest
    resolved_seed_id: str
    ws_url: str
    started_at: str


class CaseRunRegistry:
    """Small in-memory run registry placeholder for upcoming live host integration."""

    def __init__(self) -> None:
        self._runs: dict[str, StartedCaseRun] = {}

    def register(self, record: StartedCaseRun) -> None:
        self._runs[record.run_id] = record

    def get(self, run_id: str) -> StartedCaseRun | None:
        return self._runs.get(run_id)


class CaseStartService:
    """Launch service skeleton for deterministic MBAM case runs."""

    def __init__(self, *, ws_base_url: str = DEFAULT_WS_BASE_URL, registry: CaseRunRegistry | None = None) -> None:
        self._ws_base_url = ws_base_url.rstrip("/")
        self._registry = registry if registry is not None else CaseRunRegistry()

    def start_case(self, req: CaseStartRequest) -> CaseStartResponse:
        # Deterministic case mapping check now; full runtime/session startup is wired in next phase.
        resolved_seed_id = resolve_seed_id(req.seed)

        run_id = str(uuid.uuid4())
        world_id = str(uuid.uuid4())
        ws_url = f"{self._ws_base_url}?run_id={run_id}"
        started_at = datetime.now(UTC).isoformat()

        self._registry.register(
            StartedCaseRun(
                run_id=run_id,
                world_id=world_id,
                request=req,
                resolved_seed_id=resolved_seed_id,
                ws_url=ws_url,
                started_at=started_at,
            )
        )

        return CaseStartResponse(
            run_id=run_id,
            world_id=world_id,
            case_id=req.case_id,
            seed=req.seed,
            resolved_seed_id=resolved_seed_id,
            difficulty_profile=req.difficulty_profile,
            mode=req.mode,
            engine_name=ENQUETEUR_ENGINE_NAME,
            schema_version=ENQUETEUR_SCHEMA_VERSION,
            ws_url=ws_url,
            started_at=started_at,
        )

    @property
    def registry(self) -> CaseRunRegistry:
        return self._registry


def handle_post_cases_start(
    payload: Mapping[str, Any],
    *,
    service: CaseStartService | None = None,
) -> tuple[int, dict[str, Any]]:
    """Route handler skeleton for POST /api/cases/start."""
    case_service = service if service is not None else CaseStartService()
    try:
        req = CaseStartRequest.from_payload(payload)
    except CaseStartValidationError as exc:
        return (
            400,
            {
                "error": {
                    "code": exc.code,
                    "field": exc.field,
                    "message": str(exc),
                }
            },
        )

    response = case_service.start_case(req)
    return 200, response.to_payload()


__all__ = [
    "CASE_START_PATH",
    "SUPPORTED_CASE_ID",
    "ENQUETEUR_ENGINE_NAME",
    "ENQUETEUR_SCHEMA_VERSION",
    "DEFAULT_WS_BASE_URL",
    "StartCaseMode",
    "CaseStartValidationError",
    "CaseStartRequest",
    "CaseStartResponse",
    "StartedCaseRun",
    "CaseRunRegistry",
    "CaseStartService",
    "handle_post_cases_start",
]
