"""
Pytest configuration for Sim4 tests.

Ensures the repository's 'backend' directory is on sys.path so imports like
`from backend.sim4.ecs import ...` work consistently across environments.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
# We need the PROJECT ROOT (parent of 'backend') on sys.path so that
# 'import backend' resolves to the package in the repository.
_PROJECT_ROOT = _HERE.parents[3]  # .../repo root

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
