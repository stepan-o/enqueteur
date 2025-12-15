from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_dumps(obj: Any) -> str:
    """Serialize obj to a deterministic JSON string.

    - Sorted keys
    - Stable separators (no spaces)
    - Ensure non-ASCII is preserved plainly
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(obj: Any) -> int:
    """Return a stable integer hash for any JSON-serializable object.

    Uses sha256 of the stable JSON dump, reduced to a signed 63-bit range.
    """
    data = stable_json_dumps(obj).encode("utf-8")
    digest = hashlib.sha256(data).digest()
    # Take 8 bytes for 64-bit, then fit into signed 63-bit positive space
    val = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return val % (2**63 - 1)
