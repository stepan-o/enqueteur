import pytest

from legacy.backend.loopforge_sim3.config.scenario_config import ScenarioConfig
from legacy.backend.loopforge_sim3 import SCENARIO_WORLDS
from loopforge.narrative.characters import CHARACTERS


# ------------------------------------------------------------
# Basic initialization
# ------------------------------------------------------------

def test_default_config_initializes():
    cfg = ScenarioConfig()

    assert cfg.world_id == "factory_floor_v1"
    assert cfg.cast_mode == "default"
    assert cfg.ticks_per_day == 8
    assert cfg.episode_length_days == 3

    # default world resolves correctly
    assert cfg.world_spec["id"] == "factory_floor_v1"

    # default cast = full cast
    assert set(cfg.cast) == set(CHARACTERS.keys())


# ------------------------------------------------------------
# World validation
# ------------------------------------------------------------

def test_invalid_world():
    with pytest.raises(ValueError) as exc:
        ScenarioConfig(world_id="not_real")

    assert "Unknown world_id" in str(exc.value)


def test_valid_world_override():
    for world_id in SCENARIO_WORLDS:
        cfg = ScenarioConfig(world_id=world_id)
        assert cfg.world_spec["id"] == world_id


# ------------------------------------------------------------
# Cast logic
# ------------------------------------------------------------

def test_default_cast_mode_uses_all_characters():
    cfg = ScenarioConfig(cast_mode="default")
    assert set(cfg.cast) == set(CHARACTERS.keys())


def test_custom_cast_valid():
    pick = ["STILETTO-9", "CAGEWALKER"]
    cfg = ScenarioConfig(cast_mode="custom", custom_cast=pick)
    assert cfg.cast == pick


def test_custom_cast_unknown_character():
    with pytest.raises(ValueError) as exc:
        ScenarioConfig(cast_mode="custom", custom_cast=["STILETTO-9", "FOOBAR"])

    assert "Unknown characters" in str(exc.value)


def test_custom_cast_too_small():
    with pytest.raises(ValueError) as exc:
        ScenarioConfig(cast_mode="custom", custom_cast=["STILETTO-9"])

    assert "Cast size too small" in str(exc.value)


# ------------------------------------------------------------
# Parameter validation
# ------------------------------------------------------------

def test_ticks_per_day_validation():
    with pytest.raises(ValueError):
        ScenarioConfig(ticks_per_day=0)


def test_episode_length_validation():
    with pytest.raises(ValueError):
        ScenarioConfig(episode_length_days=0)


# ------------------------------------------------------------
# Immutability
# ------------------------------------------------------------

def test_frozen_config_is_immutable():
    cfg = ScenarioConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.ticks_per_day = 99
