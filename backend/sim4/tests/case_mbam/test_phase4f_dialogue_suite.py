from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    apply_dialogue_turn_to_progress,
    build_debug_dialogue_projection,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_mbam_scene_definitions,
    build_visible_dialogue_projection,
    enter_dialogue_scene,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    get_mbam_scene_definition,
    initialize_mbam_npc_states_from_case_state,
    list_dialogue_intent_ids,
    make_dialogue_turn_log_entry,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str, *, elapsed_seconds: float = 0.0):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    context = build_dialogue_execution_context(
        progress,
        npc_states,
        elapsed_seconds=elapsed_seconds,
    )
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    return case_state, npc_states, progress, context, runtime


def _with_npc_values(context, npc_id: str, *, trust: float | None = None, stress: float | None = None):
    states = dict(context.npc_states)
    npc = states[npc_id]
    states[npc_id] = replace(
        npc,
        trust=npc.trust if trust is None else trust,
        stress=npc.stress if stress is None else stress,
    )
    return replace(context, npc_states=states)


def test_phase4f_scene_validity_and_metadata() -> None:
    case_state = generate_case_state_for_seed_id("A")
    defs = build_mbam_scene_definitions(case_state)
    catalog = set(list_dialogue_intent_ids())

    for scene_id in ("S1", "S2", "S3", "S4", "S5"):
        definition = get_mbam_scene_definition(defs, scene_id)
        assert definition.scene_id == scene_id
        assert definition.primary_npc_id != ""
        assert definition.goal_summary != ""
        assert definition.scene_state.allowed_intents
        assert set(definition.scene_state.allowed_intents).issubset(catalog)
        assert set(definition.case_gate.required_fact_ids).issubset(set(definition.scene_state.allowed_fact_ids))


def test_phase4f_scene_gating_is_deterministic_for_blocked_vs_enterable() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    blocked = enter_dialogue_scene(
        case_state,
        runtime,
        scene_id="S3",
        npc_id="samira",
        context=context,
    )
    assert blocked.status == "blocked_gate"
    assert blocked.code == "missing_required_facts"
    assert blocked.gate_check.missing_fact_ids == ("N2",)

    allowed_context = replace(context, known_fact_ids=tuple(sorted(set(context.known_fact_ids).union({"N2"}))))
    entered = enter_dialogue_scene(
        case_state,
        runtime,
        scene_id="S3",
        npc_id="samira",
        context=allowed_context,
    )
    assert entered.status == "entered"
    assert entered.scene_state_after.completion_state == "in_progress"


def test_phase4f_turn_handling_routes_valid_invalid_and_missing_slot_paths() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    gate_context = _with_npc_values(replace(context, elapsed_seconds=120.0), "marc", trust=0.9)

    valid = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="je dois vérifier le journal"),),
        ),
        context=gate_context,
    )
    assert valid.turn_result.status == "accepted"

    invalid = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="request_access"),
        context=context,
    )
    assert invalid.turn_result.status == "invalid_intent"
    assert invalid.turn_result.code == "intent_not_allowed_for_scene"

    missing = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="present_evidence",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="voici une preuve"),),
        ),
        context=gate_context,
    )
    assert missing.turn_result.status == "repair"
    assert missing.turn_result.code == "missing_required_slots"
    assert set(missing.turn_result.missing_required_slots) == {"item"}


def test_phase4f_fact_reveal_legality_never_leaks_hidden_truth_on_illegal_turns() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    gate_context = _with_npc_values(
        replace(
            context,
            elapsed_seconds=120.0,
            known_evidence_ids=tuple(sorted(set(context.known_evidence_ids).union({"E3_METHOD_TRACE"}))),
        ),
        "marc",
        trust=0.9,
    )

    reveal = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="present_evidence",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="reason", value="trace matérielle"),
                DialogueTurnSlotValue(slot_name="item", value="trace du loquet"),
            ),
            presented_evidence_ids=("E3_METHOD_TRACE",),
        ),
        context=gate_context,
    )
    assert reveal.turn_result.status == "accepted"
    assert reveal.turn_result.revealed_fact_ids == ("N7",)
    allowed_facts = set(get_mbam_scene_definition(build_mbam_scene_definitions(case_state), "S2").scene_state.allowed_fact_ids)
    assert set(reveal.turn_result.revealed_fact_ids).issubset(allowed_facts)
    assert "N8" not in reveal.turn_result.revealed_fact_ids

    illegal = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="present_evidence",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="reason", value="preuve inconnue"),
                DialogueTurnSlotValue(slot_name="item", value="reçu"),
            ),
            presented_evidence_ids=("E2_CAFE_RECEIPT",),  # unknown in context
        ),
        context=gate_context,
    )
    assert illegal.turn_result.status == "refused"
    assert illegal.turn_result.code == "presented_evidence_not_known"
    assert illegal.turn_result.revealed_fact_ids == ()


def test_phase4f_trust_stress_and_gate_failure_behavior_is_deterministic() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    reassure = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="reassure"),
        context=context,
    )
    assert reassure.turn_result.status == "accepted"
    assert reassure.turn_result.trust_delta > 0.0
    assert reassure.turn_result.stress_delta < 0.0

    wrong_register = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="ask_what_happened",
            utterance_text="REGISTER:WRONG blunt",
        ),
        context=context,
    )
    assert wrong_register.turn_result.status == "repair"
    assert wrong_register.turn_result.code == "wrong_register"
    assert wrong_register.turn_result.trust_delta < 0.0
    assert wrong_register.turn_result.stress_delta > 0.0

    trust_fail = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="vérifier"),),
        ),
        context=_with_npc_values(replace(context, elapsed_seconds=120.0), "marc", trust=0.05),
    )
    assert trust_fail.turn_result.status == "blocked_gate"
    assert trust_fail.turn_result.code == "trust_below_threshold"


def test_phase4f_summary_required_scenes_enforce_summary_logic() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    s5_context = _with_npc_values(
        replace(
            context,
            known_fact_ids=("N1", "N3", "N4", "N8"),
            known_evidence_ids=("E2_CAFE_RECEIPT",),
            collected_evidence_ids=("E2_CAFE_RECEIPT",),
        ),
        "elodie",
        trust=0.9,
    )

    insufficient = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S5",
            npc_id="elodie",
            intent_id="summarize_understanding",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="person", value="samira"),
                DialogueTurnSlotValue(slot_name="reason", value="contradiction horaire"),
            ),
            presented_fact_ids=("N1",),
        ),
        context=s5_context,
    )
    assert insufficient.turn_result.status == "repair"
    assert insufficient.turn_result.code == "summary_insufficient_facts"
    assert insufficient.summary_check is not None
    assert insufficient.summary_check.passed is False

    needs_summary = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="goodbye"),
        context=context,
    )
    assert needs_summary.turn_result.status == "repair"
    assert needs_summary.turn_result.code == "summary_needed"


def test_phase4f_dialogue_projection_sanity_and_hidden_truth_boundaries() -> None:
    case_state, _npc_states, progress, context, runtime = _setup("A")

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S4",
            npc_id="jo",
            intent_id="summarize_understanding",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h52"),),
            presented_fact_ids=("N1",),
        ),
        context=replace(context, elapsed_seconds=720.0),
    )
    progress_after = apply_dialogue_turn_to_progress(progress, turn)
    log_entry = make_dialogue_turn_log_entry(turn)

    visible = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress_after,
        recent_turns=(log_entry,),
    )
    assert visible["active_scene_id"] is None
    assert visible["revealed_fact_ids"] == ["N1", "N4", "N5"]
    assert visible["recent_turns"][0]["revealed_fact_ids"] == ["N4", "N5"]
    assert "N8" not in str(visible)

    debug = build_debug_dialogue_projection(
        case_state=case_state,
        runtime_state=replace(turn.runtime_after, revealed_fact_ids=("N1", "N4", "N5", "N8")),
        progress=progress_after,
        recent_turns=(log_entry,),
    )
    assert debug["debug_scope"] == "dialogue_state_private"
    assert "N8" in debug["runtime_state"]["revealed_fact_ids"]


def test_phase4f_visible_dialogue_projection_localizes_presentation_lines_by_locale() -> None:
    case_state, _npc_states, progress, context, runtime = _setup("A")

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="ask_what_happened",
        ),
        context=context,
    )
    progress_after = apply_dialogue_turn_to_progress(progress, turn)
    entry = make_dialogue_turn_log_entry(
        turn,
        npc_utterance_text="Très bien. Restons précis.",
        short_rephrase_line="Essaie avec une phrase guide simple.",
        hint_line="Indice: garde la structure qui, où, quand.",
        summary_prompt_line="Fais un court résumé en français avant de continuer.",
    )

    fr = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress_after,
        recent_turns=(entry,),
        locale="fr",
    )
    fr_turn = fr["recent_turns"][-1]
    assert fr_turn["npc_utterance_text"] == "Très bien. Restons précis."
    assert fr_turn["short_rephrase_line"] == "Essaie avec une phrase guide simple."
    assert fr_turn["hint_line"] == "Indice: garde la structure qui, où, quand."
    assert fr_turn["summary_prompt_line"] == "Fais un court résumé en français avant de continuer."

    en = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress_after,
        recent_turns=(entry,),
        locale="en",
    )
    en_turn = en["recent_turns"][-1]
    assert en_turn["npc_utterance_text"] == "Alright. Let's stay precise."
    assert en_turn["short_rephrase_line"] == "Try a simple guided sentence."
    assert en_turn["hint_line"] == "Hint: keep the who, where, when structure."
    assert en_turn["summary_prompt_line"] == "Give a short French summary before continuing."


def test_phase4f_same_seed_and_turn_sequence_is_deterministic() -> None:
    def run_sequence():
        case_state, _npc_states, progress, context, runtime = _setup("A")
        log = []

        t1 = execute_dialogue_turn(
            case_state,
            runtime,
            DialogueTurnRequest(
                scene_id="S1",
                npc_id="elodie",
                intent_id="summarize_understanding",
                presented_fact_ids=("N1",),
            ),
            context=context,
        )
        runtime = t1.runtime_after
        progress = apply_dialogue_turn_to_progress(progress, t1)
        log.append(make_dialogue_turn_log_entry(t1))

        t2 = execute_dialogue_turn(
            case_state,
            runtime,
            DialogueTurnRequest(
                scene_id="S4",
                npc_id="jo",
                intent_id="summarize_understanding",
                provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h52"),),
                presented_fact_ids=("N1",),
            ),
            context=replace(context, elapsed_seconds=720.0, known_fact_ids=progress.known_fact_ids),
        )
        runtime = t2.runtime_after
        progress = apply_dialogue_turn_to_progress(progress, t2)
        log.append(make_dialogue_turn_log_entry(t2))

        t3 = execute_dialogue_turn(
            case_state,
            runtime,
            DialogueTurnRequest(
                scene_id="S2",
                npc_id="marc",
                intent_id="request_access",
                provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="procédure"),),
            ),
            context=_with_npc_values(
                replace(context, elapsed_seconds=120.0, known_fact_ids=progress.known_fact_ids),
                "marc",
                trust=0.9,
            ),
        )
        runtime = t3.runtime_after
        progress = apply_dialogue_turn_to_progress(progress, t3)
        log.append(make_dialogue_turn_log_entry(t3))

        visible = build_visible_dialogue_projection(
            case_state=case_state,
            runtime_state=runtime,
            progress=progress,
            recent_turns=tuple(log),
        )
        return runtime, progress, tuple(log), visible

    first = run_sequence()
    second = run_sequence()
    assert first == second
