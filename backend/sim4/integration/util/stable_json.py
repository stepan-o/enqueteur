from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

# Reuse the stable JSON dump from stable_hash to keep a single canonical policy
from .stable_hash import stable_json_dumps as _stable_json_dumps


def to_primitive(obj: Any) -> Any:
    """Convert dataclasses to dicts; pass through primitives/lists/dicts.

    This is a shallow helper; nested dataclasses inside lists/dicts will be
    handled by asdict if the top-level object is a dataclass.
    """
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def stable_json_dumps(obj: Any) -> str:
    """Stable JSON serialization with sorted keys and fixed separators.

    Ensures byte-stable output across runs. Appends no newline by itself.
    """
    return _stable_json_dumps(to_primitive(obj))


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = stable_json_dumps(obj) + "\n"  # newline at EOF
    p.write_text(data, encoding="utf-8")


def write_jsonl(path: str | Path, iterable: Iterable[Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as f:
        for obj in iterable:
            line = stable_json_dumps(obj) + "\n"
            f.write(line)
