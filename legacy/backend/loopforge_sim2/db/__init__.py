# Loopforge DB package public API
# Explicitly re-export the canonical DB surface so tests and core code share the same symbols.
# This avoids ambiguity between module and package imports and ensures monkeypatching works.

from contextlib import contextmanager
from typing import Iterator

from .db import Base, get_engine  # pragma: no cover
from .db import SessionLocal as _UnderlyingSessionLocal  # pragma: no cover
from .models import Robot, Memory, ActionLog, EnvironmentEvent  # pragma: no cover
from .memory_store import MemoryStore  # pragma: no cover

# Expose SessionLocal at the package level so tests can monkeypatch it
SessionLocal = _UnderlyingSessionLocal  # type: ignore[assignment]

@contextmanager
def session_scope() -> Iterator["Session"]:
    """Transactional scope using the package-level SessionLocal.

    This indirection ensures test monkeypatching of loopforge.db.SessionLocal
    is respected everywhere, including callers that import session_scope from
    the package. Behavior remains identical otherwise.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

__all__ = [
    "Base",
    "get_engine",
    "SessionLocal",
    "session_scope",
    "Robot",
    "Memory",
    "ActionLog",
    "EnvironmentEvent",
    "MemoryStore",
]
