"""Narrative package shim.

Ensures legacy imports like `from loopforge import narrative` expose the same
public API as the implementation module `loopforge.narrative.narrative`.

This file re-exports the implementation module's public symbols and also
exposes the implementation module itself as `narrative` so that REPL checks
comparing `dir()` between the submodule and the package show no meaningful
differences.
"""
from __future__ import annotations

# Import only from the new submodule (do not import from legacy paths)
from . import narrative as _impl  # pragma: no cover

# Copy all public (non-underscored) attributes from the implementation module
# into the package namespace to mirror `dir(loopforge.narrative.narrative)`.
for _name, _obj in vars(_impl).items():  # pragma: no cover
    if not _name.startswith("_"):
        globals()[_name] = _obj

# Also expose the submodule itself as an attribute for convenience:
#   from loopforge.narrative import narrative as pkg_narr
narrative = _impl  # pragma: no cover

# Build an explicit __all__ consisting of public symbols from the implementation.
__all__ = sorted([name for name in vars(_impl).keys() if not name.startswith("_")])  # pragma: no cover
