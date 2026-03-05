from __future__ import annotations

"""Load + validate sim_sim_1 config from YAML (or JSON-subset YAML)."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from backend.sim_sim.config.model import SimSimConfig, parse_sim_sim_config


DEFAULT_CONFIG_PATH = Path(__file__).with_name("sim_sim_1.default.yaml")


@dataclass(frozen=True)
class LoadedSimSimConfig:
    config: SimSimConfig
    source_path: Path
    config_hash: str
    config_id: str
    raw: Mapping[str, Any]


def load_sim_sim_config(path: str | Path | None = None) -> LoadedSimSimConfig:
    source_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not source_path.exists():
        raise FileNotFoundError(f"sim_sim config not found: {source_path}")

    raw_text = source_path.read_text(encoding="utf-8")
    raw_obj = _load_yaml_like_text(raw_text, source_path=source_path)
    if not isinstance(raw_obj, Mapping):
        raise ValueError(f"sim_sim config root must be an object: {source_path}")

    config = parse_sim_sim_config(raw_obj)
    canonical_json = json.dumps(raw_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    config_hash = hashlib.sha1(canonical_json.encode("utf-8")).hexdigest()
    config_id = config_hash[:12]

    return LoadedSimSimConfig(
        config=config,
        source_path=source_path,
        config_hash=config_hash,
        config_id=config_id,
        raw=raw_obj,
    )


def _load_yaml_like_text(text: str, *, source_path: Path) -> Any:
    # PyYAML is optional in this repo. We support JSON-subset YAML without external deps.
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "sim_sim config requires PyYAML for non-JSON YAML syntax; "
                f"could not parse {source_path}: {exc}"
            ) from exc
