from __future__ import annotations

from backend.sim4.case_mbam import (
    apply_case_timeline_to_npc_states,
    build_debug_npc_semantic_projection,
    build_visible_npc_semantic_projection,
    generate_case_state_for_seed_id,
    get_cast_registry,
    initialize_mbam_npc_states_from_case_state,
    list_cast_ids,
)
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.host.kvp_defaults import (
    default_render_spec,
    default_run_anchors,
    tick_rate_hz_from_clock,
)
from backend.sim4.host.sim_runner import MbamCaseConfig, SimRunner
from backend.sim4.runtime.clock import TickClock
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


class _NoopScheduler:
    def iter_phase_systems(self, phase: str):  # noqa: ARG002
        return ()


def _build_world_ctx() -> WorldContext:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    return world_ctx


def _build_runner(*, seed: str, rng_seed: int, dt: float = 1.0) -> SimRunner:
    clock = TickClock(dt=dt)
    return SimRunner(
        clock=clock,
        ecs_world=ECSWorld(),
        world_ctx=_build_world_ctx(),
        rng_seed=rng_seed,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(
            seed=rng_seed,
            tick_rate_hz=tick_rate_hz_from_clock(clock),
            time_origin_ms=0,
        ),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed=seed),
    )


def test_phase2f_cast_registry_is_complete_and_populated() -> None:
    registry = get_cast_registry()
    assert tuple(registry.keys()) == list_cast_ids()
    assert tuple(registry.keys()) == ("elodie", "marc", "samira", "laurent", "jo")

    for npc_id in list_cast_ids():
        entry = registry[npc_id]
        assert entry.npc_id == npc_id
        assert entry.display_name != ""
        assert entry.identity_role != ""
        assert entry.baseline_traits != ()
        assert entry.baseline_register != ""
        assert entry.tell_profile != ()
        assert entry.trust_triggers != ()
        assert entry.anti_triggers != ()
        assert entry.portrait_config.base_portrait_id != ""
        assert entry.portrait_config.state_variants != ()
        assert entry.portrait_config.card_theme_id != ""


def test_phase2f_npc_state_initialization_is_complete_and_deterministic() -> None:
    case_state = generate_case_state_for_seed_id("A")
    world_ctx = _build_world_ctx()

    first = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    second = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    assert first == second
    assert tuple(first.keys()) == list_cast_ids()

    for npc_id in list_cast_ids():
        state = first[npc_id]
        assert state.npc_id == npc_id
        assert state.current_room_id != ""
        assert state.availability in {"available", "busy", "gone", "restricted"}
        assert 0.0 <= state.trust <= 1.0
        assert 0.0 <= state.stress <= 1.0
        assert state.schedule_state.next_beat_id is not None
        assert state.card_state.portrait_variant != ""
        assert state.card_state.trust_trend in {"up", "flat", "down"}


def test_phase2f_seeded_overlay_differences_match_locked_abc() -> None:
    world_ctx = _build_world_ctx()
    states_a = initialize_mbam_npc_states_from_case_state(world_ctx, generate_case_state_for_seed_id("A"))
    states_b = initialize_mbam_npc_states_from_case_state(world_ctx, generate_case_state_for_seed_id("B"))
    states_c = initialize_mbam_npc_states_from_case_state(world_ctx, generate_case_state_for_seed_id("C"))

    assert states_a["marc"].overlay_role_slot == "ALLY"
    assert states_b["samira"].overlay_role_slot == "CULPRIT"
    assert states_c["laurent"].overlay_role_slot == "CULPRIT"
    assert states_b["jo"].overlay_role_slot == "ALLY"
    assert states_c["elodie"].overlay_role_slot == "ALLY"

    assert "method_badge_borrow" in states_b["samira"].hidden_flags
    assert "method_case_left_unlatched" in states_c["laurent"].hidden_flags
    assert states_a["samira"].overlay_role_slot != states_b["samira"].overlay_role_slot


def test_phase2f_timeline_runtime_updates_are_deterministic_and_beat_linked() -> None:
    case_state = generate_case_state_for_seed_id("C")
    world_ctx = _build_world_ctx()
    base_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)

    at_2m, applied_2m = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=base_states,
        elapsed_seconds=120.0,
        applied_beat_ids=(),
    )
    assert at_2m["elodie"].availability == "busy"
    assert at_2m["elodie"].schedule_state.current_beat_id == "T_PLUS_02_CURATOR_CONTAINMENT"

    at_12m, applied_12m = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=at_2m,
        elapsed_seconds=720.0,
        applied_beat_ids=applied_2m,
    )
    assert at_12m["jo"].schedule_state.current_beat_id == "T_PLUS_12_BARISTA_WITNESS_WINDOW"
    assert at_12m["laurent"].schedule_state.current_beat_id == "T_PLUS_10_DONOR_EVENT"

    at_15m, applied_15m = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=at_12m,
        elapsed_seconds=900.0,
        applied_beat_ids=applied_12m,
    )
    assert at_15m["marc"].availability == "restricted"
    assert at_15m["marc"].schedule_state.current_beat_id == "T_PLUS_15_TERMINAL_ARCHIVE"

    replay_at_15m, replay_applied = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=base_states,
        elapsed_seconds=900.0,
        applied_beat_ids=(),
    )
    assert at_15m == replay_at_15m
    assert applied_15m == replay_applied


def test_phase2f_projection_visible_vs_debug_boundaries() -> None:
    world_ctx = _build_world_ctx()
    states = initialize_mbam_npc_states_from_case_state(world_ctx, generate_case_state_for_seed_id("B"))

    visible = build_visible_npc_semantic_projection(states)
    debug = build_debug_npc_semantic_projection(states)

    assert len(visible) == 5
    assert len(debug) == 5
    visible_by_id = {row["npc_id"]: row for row in visible}
    debug_by_id = {row["npc_id"]: row for row in debug}

    for npc_id in list_cast_ids():
        v = visible_by_id[npc_id]
        d = debug_by_id[npc_id]
        assert "overlay_role_slot" not in v
        assert "overlay_helpfulness" not in v
        assert "known_fact_flags" not in v
        assert "belief_flags" not in v
        assert "hidden_flags" not in v
        assert "misremember_flags" not in v
        assert "profile_id" not in v["card_state"]
        assert "profile_id" in d["card_state"]
        assert "hidden_flags" in d
        assert "known_fact_flags" in d
        assert all(not flag.startswith("overlay_role_") for flag in v["visible_behavior_flags"])
        assert all(not flag.startswith("overlay_helpfulness_") for flag in v["visible_behavior_flags"])


def test_phase2f_runner_npc_semantics_are_seed_deterministic_and_rng_independent() -> None:
    runner_a_1 = _build_runner(seed="A", rng_seed=1)
    runner_a_2 = _build_runner(seed="A", rng_seed=777)

    runner_a_1.run(num_ticks=900)
    runner_a_2.run(num_ticks=900)

    # Case semantic progression should depend only on CaseState + elapsed time.
    assert runner_a_1.get_npc_states() == runner_a_2.get_npc_states()

    runner_b = _build_runner(seed="B", rng_seed=1)
    runner_c = _build_runner(seed="C", rng_seed=1)
    runner_b.run(num_ticks=1)
    runner_c.run(num_ticks=1)

    assert runner_b.get_npc_state("samira") is not None
    assert runner_c.get_npc_state("samira") is not None
    assert runner_b.get_npc_state("samira") != runner_c.get_npc_state("samira")
