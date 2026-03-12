from __future__ import annotations

"""Run helper for the canonical local runtime host: `python -m backend.server`."""

from .app import run_dev


def main() -> None:
    run_dev()


if __name__ == "__main__":
    main()
