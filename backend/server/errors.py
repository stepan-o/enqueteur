from __future__ import annotations

"""Server shell exceptions."""


class ServerShellError(RuntimeError):
    """Base exception for server-shell orchestration errors."""


class NotReadyError(ServerShellError):
    """Raised when a requested server action is not yet implemented/wired."""


class RunNotFoundError(ServerShellError):
    """Raised when an operation references an unknown run id."""


class SessionNotFoundError(ServerShellError):
    """Raised when an operation references an unknown connection id."""

