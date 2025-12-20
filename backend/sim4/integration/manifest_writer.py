from __future__ import annotations

"""Manifest writer for Sprint 14.4 (manifest.kvp.json).

Writes deterministic UTF-8 (no BOM) compact JSON with sorted keys.
Validation is enforced via ManifestV0_1.validate() inside the writer.

No transport/session logic; artifacts only.
"""

from pathlib import Path
from typing import Union
import json

from .manifest_schema import ManifestV0_1


def write_manifest(path: Union[str, Path], manifest: ManifestV0_1) -> None:
    """Validate and write the manifest to the given path as JSON.

    - Calls manifest.validate() before writing
    - Serializes manifest.to_dict() with stable channels order
    - Uses separators to keep it compact and sort_keys=True for determinism
    - Writes UTF-8 without BOM
    """
    # Validate strictly
    manifest.validate()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    obj = manifest.to_dict()
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    p.write_bytes(data.encode("utf-8"))


__all__ = ["write_manifest"]
