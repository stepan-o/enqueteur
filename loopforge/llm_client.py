# Deprecated shim — canonical implementation lives in loopforge.llm.llm_client
from __future__ import annotations
from loopforge.llm import llm_client as _core  # pragma: no cover

# Mirror all non-dunder attributes
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

# Ensure test monkeypatches applied to this shim affect the canonical module before delegation.
# In particular, tests patch `get_client` on this module; we sync it into the core module so that
# `_core.chat_json(...)` uses the patched client provider.

def _sync_patched_to_core() -> None:  # pragma: no cover
    try:
        if "get_client" in globals():
            setattr(_core, "get_client", globals()["get_client"])
    except Exception:
        pass


def chat_json(system_prompt: str, messages, schema_hint: str):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.chat_json(system_prompt, messages, schema_hint)
