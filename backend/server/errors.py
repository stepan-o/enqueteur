from __future__ import annotations

"""Runtime-host transport exceptions."""


class ServerShellError(RuntimeError):
    """Base exception for runtime-host orchestration errors.

    Historical class name is kept to avoid broad churn.
    """


class TransportRouteError(ServerShellError):
    """Base transport-facing route error with HTTP mapping metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str,
        field: str | None = None,
        phase_gate: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.field = field
        self.phase_gate = phase_gate


class TransportRequestError(TransportRouteError):
    """Raised when raw transport payload is malformed before core validation."""

    def __init__(self, message: str, *, field: str = "payload") -> None:
        super().__init__(
            message,
            status_code=400,
            code="INVALID_REQUEST",
            field=field,
        )


class HostNotReadyError(TransportRouteError):
    """Raised when required transport-layer dependencies are not initialized."""

    def __init__(self, message: str, *, phase_gate: str) -> None:
        super().__init__(
            message,
            status_code=503,
            code="HOST_NOT_READY",
            phase_gate=phase_gate,
        )


class LaunchExecutionError(TransportRouteError):
    """Raised when core launch execution fails before a response is produced."""

    def __init__(self, message: str = "Case launch failed in backend launch service.") -> None:
        super().__init__(
            message,
            status_code=502,
            code="LAUNCH_FAILED",
        )


class LaunchContractError(TransportRouteError):
    """Raised when a launch response cannot satisfy transport/registry adapter needs."""

    def __init__(self, message: str = "Case launch backend returned an invalid response contract.") -> None:
        super().__init__(
            message,
            status_code=502,
            code="INVALID_LAUNCH_RESPONSE",
        )


class RunNotFoundError(ServerShellError):
    """Raised when an operation references an unknown run id."""


class SessionNotFoundError(ServerShellError):
    """Raised when an operation references an unknown connection id."""
