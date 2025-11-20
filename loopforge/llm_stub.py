# Deprecated shim — canonical implementation lives in loopforge.llm.llm_stub
from __future__ import annotations
from loopforge.llm import llm_stub as _core  # pragma: no cover

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

# Ensure test monkeypatches on this shim are reflected in the canonical module
# before delegating calls. Tests patch attributes like USE_LLM_POLICY, chat_json,
# and deterministic fallback helpers.

def _sync_patched_to_core() -> None:  # pragma: no cover
    try:
        for _name in (
            "USE_LLM_POLICY",
            "chat_json",
            "_deterministic_robot_policy",
            "_deterministic_supervisor_policy",
        ):
            if _name in globals():
                setattr(_core, _name, globals()[_name])
    except Exception:
        pass


def decide_robot_action(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.decide_robot_action(*args, **kwargs)


def decide_supervisor_action(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.decide_supervisor_action(*args, **kwargs)


def decide_robot_action_plan(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.decide_robot_action_plan(*args, **kwargs)


def decide_robot_action_plan_and_dict(*args, **kwargs):  # type: ignore[override]
    _sync_patched_to_core()
    return _core.decide_robot_action_plan_and_dict(*args, **kwargs)

# Perform an initial sync at import time so first calls see patched flags/functions
_sync_patched_to_core()
