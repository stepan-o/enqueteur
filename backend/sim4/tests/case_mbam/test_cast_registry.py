from __future__ import annotations

import pytest

from backend.sim4.case_mbam import get_cast_entry, get_cast_registry, list_cast_ids


def test_cast_registry_contains_fixed_mbam_five() -> None:
    assert list_cast_ids() == ("elodie", "marc", "samira", "laurent", "jo")

    registry = get_cast_registry()
    assert set(registry.keys()) == {"elodie", "marc", "samira", "laurent", "jo"}


def test_cast_registry_entries_match_locked_identity_roles_and_names() -> None:
    elodie = get_cast_entry("elodie")
    assert elodie.display_name == "Élodie Marchand"
    assert elodie.identity_role == "curator"

    marc = get_cast_entry("marc")
    assert marc.display_name == "Marc Dutil"
    assert marc.identity_role == "guard"

    samira = get_cast_entry("samira")
    assert samira.display_name == "Samira B."
    assert samira.identity_role == "intern"

    laurent = get_cast_entry("laurent")
    assert laurent.display_name == "Laurent Vachon"
    assert laurent.identity_role == "donor"

    jo = get_cast_entry("jo")
    assert jo.display_name == "Jo Leclerc"
    assert jo.identity_role == "barista"


def test_cast_registry_entries_include_profile_and_portrait_metadata() -> None:
    for npc_id in list_cast_ids():
        entry = get_cast_entry(npc_id)
        assert entry.baseline_traits != ()
        assert entry.baseline_register != ""
        assert entry.tell_profile != ()
        assert entry.trust_triggers != ()
        assert entry.anti_triggers != ()
        assert entry.portrait_config.base_portrait_id != ""
        assert entry.portrait_config.state_variants != ()
        assert entry.portrait_config.card_theme_id != ""


def test_get_cast_registry_returns_copy_and_not_mutable_source() -> None:
    first = get_cast_registry()
    first.pop("elodie")
    second = get_cast_registry()

    assert "elodie" in second
    assert set(second.keys()) == {"elodie", "marc", "samira", "laurent", "jo"}


def test_get_cast_entry_rejects_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_cast_entry("outsider")
