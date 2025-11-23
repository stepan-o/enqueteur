from __future__ import annotations

"""
Snapshot Orchestrator

Coordinates:
- Repo acquisition (local or GitHub)
- File scanning + "Extract Data"-style payload
- LLM call using Snapshotter prompts
- Writing ARCHITECTURE_SUMMARY_SNAPSHOT to disk

Assumptions:
- Prompts live in loopforge_meta/agents_meta/snapshotter/prompts.py
- LLM client lives in loopforge_meta/llm_client.py
"""

import argparse
import dataclasses
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loopforge_meta.agents_meta.snapshotter.prompts import (
    snapshotter_system_prompt,
    snapshotter_trigger_prompt,
)

# Adjust this import if your client lives elsewhere
from loopforge_meta.llm_client import LLMClient, LLMClientError


# -------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------

@dataclasses.dataclass
class ExtractedFile:
    """
    Minimal "Extract Data" analogue: { path, content }

    This mirrors the Dust tool schema you were using:
      { "path": "...", "content": "..." }
    """
    path: str
    content: str


# -------------------------------------------------------------------
# Repo acquisition helpers
# -------------------------------------------------------------------

def clone_github_repo(remote: str, ref: str = "main") -> Path:
    """
    Clone a GitHub repo into a temporary directory and checkout the given ref.

    remote: e.g. "https://github.com/owner/repo.git"
    ref: branch, tag, or commit SHA
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="snapshotter_repo_"))
    subprocess.run(["git", "clone", remote, str(tmp_dir)], check=True)

    if ref:
        subprocess.run(["git", "checkout", ref], cwd=tmp_dir, check=True)

    return tmp_dir


def resolve_repo_root(
        source: str,
        local_path: Optional[str],
        github_remote: Optional[str],
        github_ref: str,
) -> Path:
    if source == "local":
        if not local_path:
            raise ValueError("local_path is required when source='local'")
        repo_root = Path(local_path).resolve()
        if not repo_root.exists():
            raise FileNotFoundError(f"Local repo path does not exist: {repo_root}")
        return repo_root

    if source == "github":
        if not github_remote:
            raise ValueError("github_remote is required when source='github'")
        return clone_github_repo(github_remote, github_ref)

    raise ValueError(f"Unknown source: {source}")


# -------------------------------------------------------------------
# Repo scanning & "Extract Data" payload
# -------------------------------------------------------------------

def should_include_path(path: Path) -> bool:
    """
    Filter for which files to feed to Snapshotter.

    Right now: all *.py files, skipping typical junk.
    You can tighten this later if needed (e.g., only loopforge/ and scripts/).
    """
    if path.suffix != ".py":
        return False

    # Skip vendor/venv-ish dirs
    parts = set(path.parts)
    if any(p in parts for p in (".venv", "venv", "site-packages", "__pycache__")):
        return False

    return True


def extract_files(repo_root: Path, max_chars_per_file: int = 12000) -> List[ExtractedFile]:
    """
    Walk the repo and build a list of ExtractedFile objects.

    NOTE: We truncate each file's content to max_chars_per_file to avoid
    blowing up context. Snapshotter is structural, not line-perfect.
    """
    extracted: List[ExtractedFile] = []

    for path in repo_root.rglob("*.py"):
        if not should_include_path(path):
            continue

        rel_path = str(path.relative_to(repo_root))

        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # If something is unreadable, keep a stub entry and surface that via uncertainties.
            extracted.append(
                ExtractedFile(
                    path=rel_path,
                    content="__ERROR_READING_FILE__",
                )
            )
            continue

        if len(raw) > max_chars_per_file:
            raw = raw[:max_chars_per_file] + "\n\n# [TRUNCATED BY SNAPSHOT ORCHESTRATOR]\n"

        extracted.append(ExtractedFile(path=rel_path, content=raw))

    if not extracted:
        raise RuntimeError(f"No Python files found under {repo_root}")

    return extracted


def build_snapshotter_context_payload(
        repo_root: Path,
        source: str,
        github_remote: Optional[str],
        github_ref: str,
        files: List[ExtractedFile],
) -> Dict[str, Any]:
    """
    This is the JSON object that will be interpolated into {context} in the
    snapshotter trigger prompt.
    """

    # Try to capture git metadata when running on a real repo
    commit = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
    except Exception:
        # Non-fatal, just skip commit info
        commit = None

    payload = {
        "repo": {
            "name": repo_root.name,
            "source": source,
            "root_path": str(repo_root),
            "git": {
                "remote": github_remote,
                "ref": github_ref,
                "commit": commit,
            } if source == "github" or commit is not None else None,
        },
        "files": [
            {
                "path": f.path,
                "content": f.content,
            }
            for f in files
        ],
    }

    return payload


# -------------------------------------------------------------------
# LLM interaction
# -------------------------------------------------------------------

def call_snapshotter_llm(
        client: LLMClient,
        context_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Call the Snapshotter LLM with:
    - system prompt from snapshotter_system_prompt()
    - trigger prompt from snapshotter_trigger_prompt(), with {context} filled

    Returns the parsed ARCHITECTURE_SUMMARY_SNAPSHOT dict.
    """
    system_prompt = snapshotter_system_prompt()

    context_json = json.dumps(context_payload, indent=2)
    user_prompt = snapshotter_trigger_prompt().format(context=context_json)

    try:
        # We assume LLMClient supports a JSON mode and returns a dict.
        response = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
    except LLMClientError as e:
        raise RuntimeError(f"Snapshotter LLM call failed: {e}") from e

    # The prompts say output MUST be:
    # {
    #   "ARCHITECTURE_SUMMARY_SNAPSHOT": { ... }
    # }
    # But we defensively handle minor deviations.
    if isinstance(response, dict) and "ARCHITECTURE_SUMMARY_SNAPSHOT" in response:
        snapshot = response["ARCHITECTURE_SUMMARY_SNAPSHOT"]
    elif isinstance(response, dict):
        # Might be the snapshot itself, if the model ignored the wrapper key.
        snapshot = response
    else:
        raise RuntimeError(
            "Unexpected LLM response type; expected JSON object with "
            "'ARCHITECTURE_SUMMARY_SNAPSHOT' key or a snapshot dict."
        )

    # Basic schema sanity checks
    if "modules" not in snapshot or not isinstance(snapshot["modules"], list):
        raise RuntimeError("Snapshot is missing required 'modules' list")

    if "generated_at" not in snapshot:
        # If model forgot, we patch with now (still valid for our purposes).
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()

    if "uncertainties" not in snapshot:
        snapshot["uncertainties"] = []

    return snapshot


# -------------------------------------------------------------------
# Snapshot persistence
# -------------------------------------------------------------------

def write_snapshot_to_disk(
        snapshot: Dict[str, Any],
        repo_root: Path,
        out_dir: Optional[Path] = None,
) -> Path:
    """
    Writes:
      { "ARCHITECTURE_SUMMARY_SNAPSHOT": { ... } }
    to docs/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_<timestamp>.json
    """
    if out_dir is None:
        out_dir = repo_root / "docs" / "architecture" / "architecture_snapshots"

    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = snapshot.get("generated_at") or datetime.now(timezone.utc).isoformat()
    safe_ts = timestamp.replace(":", "-")

    filename = f"ARCH_SUMMARY_SNAPSHOT_{safe_ts}.json"
    out_path = out_dir / filename

    wrapper = {"ARCHITECTURE_SUMMARY_SNAPSHOT": snapshot}

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(wrapper, f, indent=2, sort_keys=False)

    return out_path


# -------------------------------------------------------------------
# Orchestrator entrypoint
# -------------------------------------------------------------------

def run_snapshotter_orchestration(
        *,
        source: str,
        local_path: Optional[str] = None,
        github_remote: Optional[str] = None,
        github_ref: str = "main",
        model: str = "gpt-4.1-mini",
) -> Path:
    """
    High-level orchestrator:
    1. Resolve repo root (local or GitHub)
    2. Extract files as {path, content}
    3. Build context payload
    4. Call snapshotter LLM
    5. Write snapshot to disk
    """
    repo_root = resolve_repo_root(source, local_path, github_remote, github_ref)

    extracted_files = extract_files(repo_root)
    context_payload = build_snapshotter_context_payload(
        repo_root=repo_root,
        source=source,
        github_remote=github_remote,
        github_ref=github_ref,
        files=extracted_files,
    )

    client = LLMClient(
        model=model,
        temperature=0.0,
        max_tokens=8000,
    )

    snapshot = call_snapshotter_llm(client, context_payload)
    out_path = write_snapshot_to_disk(snapshot, repo_root)

    print(f"[Snapshotter] Wrote architecture snapshot to: {out_path}")
    return out_path


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Loopforge Snapshotter orchestrator."
    )
    parser.add_argument(
        "--source",
        choices=["local", "github"],
        default="local",
        help="Where to load the repo from.",
    )
    parser.add_argument(
        "--local-path",
        type=str,
        help="Path to local repo root (when --source=local).",
    )
    parser.add_argument(
        "--github-remote",
        type=str,
        help="GitHub remote URL (when --source=github).",
    )
    parser.add_argument(
        "--github-ref",
        type=str,
        default="main",
        help="Git ref / branch / tag / SHA (when --source=github).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4.1-mini",
        help="OpenAI model name for Snapshotter.",
    )

    args = parser.parse_args()

    run_snapshotter_orchestration(
        source=args.source,
        local_path=args.local_path,
        github_remote=args.github_remote,
        github_ref=args.github_ref,
        model=args.model,
    )


if __name__ == "__main__":
    main()
