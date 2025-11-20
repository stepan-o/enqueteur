# scripts/reset_local_state.py
from __future__ import annotations

import os
import glob
from pathlib import Path

from loopforge.config import get_settings

ROOT = Path(__file__).resolve().parents[1]


def _remove(path: Path) -> None:
    if path.exists():
        print(f"Removing {path}")
        path.unlink()


def main() -> None:
    # 1) DB file(s)
    settings = get_settings()
    db_url = settings.database_url

    # Only auto-delete if we’re on SQLite and pointing to a local file
    if db_url.startswith("sqlite:///"):
        db_path_str = db_url.replace("sqlite:///", "")
        db_path = (ROOT / db_path_str).resolve()
        _remove(db_path)
    else:
        print(f"DATABASE_URL is not SQLite (got {db_url}); not touching it.")

    # 2) Logs directory
    logs_dir = ROOT / "logs"
    if logs_dir.exists():
        # Registry
        _remove(logs_dir / "loopforge_run_registry.jsonl")
        # All JSONL logs
        for p in glob.glob(str(logs_dir / "*.jsonl")):
            _remove(Path(p))
    else:
        print("No logs/ directory found; nothing to clean.")

    # 3) Ad-hoc test DBs (optional, adjust as needed)
    for pattern in [
        "tests/*.db",
        "/tmp/loopforge_*.db",
    ]:
        for p in glob.glob(pattern):
            _remove(Path(p))


if __name__ == "__main__":
    main()
