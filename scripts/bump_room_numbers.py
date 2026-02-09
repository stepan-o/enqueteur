#!/usr/bin/env python3
"""
Renumber concept art room files by bumping their leading numeric prefix.

Example:
  02_loopforge_rooms_dispatch.png
  -> 03_loopforge_rooms_dispatch.png  (if --start 2 --delta 1)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_DIR = (
    "../frontend/loopforge-webview/public/assets/concept_art/rooms"
)
FILENAME_RE = re.compile(r"^(?P<num>\d+)_loopforge_.*rooms_.*\.png$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bump numeric prefixes on loopforge room concept art files."
        )
    )
    parser.add_argument(
        "--start",
        type=int,
        required=True,
        help="Only files with prefix >= this number are bumped.",
    )
    parser.add_argument(
        "--delta",
        type=int,
        default=1,
        help="Amount to add to the numeric prefix (default: 1).",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(DEFAULT_DIR),
        help="Directory containing room images.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned renames without applying them.",
    )
    return parser.parse_args()


def build_plan(directory: Path, start: int, delta: int) -> list[tuple[Path, Path]]:
    plan: list[tuple[Path, Path]] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        num_str = match.group("num")
        num = int(num_str)
        if num < start:
            continue
        new_num = num + delta
        if new_num < 0:
            raise ValueError(
                f"Negative result for {path.name}: {new_num}"
            )
        width = len(num_str)
        new_num_str = str(new_num).zfill(width)
        new_name = path.name.replace(num_str, new_num_str, 1)
        plan.append((path, path.with_name(new_name)))
    return plan


def validate_plan(plan: list[tuple[Path, Path]]) -> None:
    targets = {}
    for src, dst in plan:
        if dst in targets and targets[dst] != src:
            raise ValueError(
                f"Multiple sources map to the same target: {dst.name}"
            )
        targets[dst] = src

    if not plan:
        return
    existing = {p for p in plan[0][0].parent.iterdir()}
    for src, dst in plan:
        if dst in existing and dst not in targets:
            raise ValueError(
                f"Target already exists and won't be renamed: {dst.name}"
            )


def apply_plan(plan: list[tuple[Path, Path]], dry_run: bool, delta: int) -> None:
    if not plan:
        print("No files matched the pattern and start threshold.")
        return

    if delta > 0:
        plan = sorted(plan, key=lambda pair: int(FILENAME_RE.match(pair[0].name).group("num")), reverse=True)
    else:
        plan = sorted(plan, key=lambda pair: int(FILENAME_RE.match(pair[0].name).group("num")))

    for src, dst in plan:
        if dry_run:
            print(f"{src.name} -> {dst.name}")
        else:
            src.rename(dst)
            print(f"Renamed {src.name} -> {dst.name}")


def main() -> None:
    args = parse_args()
    directory = args.dir.resolve()
    if not directory.exists():
        raise SystemExit(f"Directory does not exist: {directory}")

    plan = build_plan(directory, args.start, args.delta)
    validate_plan(plan)
    apply_plan(plan, args.dry_run, args.delta)


if __name__ == "__main__":
    main()
