# Shim wrapper — canonical CLI lives in loopforge.cli.sim_cli
from __future__ import annotations

from loopforge.cli import sim_cli as _core  # pragma: no cover

# Mirror all non-dunder attributes so tests and legacy imports keep working
for _n, _v in vars(_core).items():  # pragma: no cover
    if not _n.startswith("__"):
        globals()[_n] = _v

# Define __all__ to match canonical intent
__all__ = list(
    getattr(
        _core,
        "__all__",
        [n for n in vars(_core).keys() if not n.startswith("__")]
    )
)

# Provide wrappers for test monkeypatching to take effect when calling functions directly
# Tests monkeypatch attributes on this shim module; we mirror those onto the core module
# before delegating, so patches influence the canonical implementation.

def _sync_patched_to_core() -> None:  # pragma: no cover
    for _name, _obj in globals().items():
        if _name.startswith("__"):
            continue
        # Only sync callables used by tests (safe operation)
        if _name in {"summarize_episode", "compute_day_summary"}:
            try:
                setattr(_core, _name, _obj)
            except Exception:
                pass


def view_episode(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.view_episode(*args, **kwargs)


def list_runs(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.list_runs(*args, **kwargs)


# Allow running as a module directly
if __name__ == "__main__":  # pragma: no cover
    _app = globals().get("app", None)
    if _app is not None:
        _app()
