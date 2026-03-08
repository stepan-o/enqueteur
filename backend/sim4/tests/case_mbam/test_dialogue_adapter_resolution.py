from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DeterministicDialoguePresentationAdapter,
    DialogueAdapterOutput,
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    build_dialogue_adapter_input,
    build_dialogue_execution_context,
    build_deterministic_fallback_output,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_learning_state,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
    normalize_and_validate_adapter_output,
    resolve_dialogue_adapter_output,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


class _RaisesAdapter:
    def render_turn(self, payload):  # noqa: ANN001
        raise RuntimeError("provider down")


class _DictAdapter:
    def __init__(self, row):
        self._row = row

    def render_turn(self, payload):  # noqa: ANN001
        _ = payload
        return self._row


class _OutputAdapter:
    def __init__(self, output: DialogueAdapterOutput):
        self._output = output

    def render_turn(self, payload):  # noqa: ANN001
        _ = payload
        return self._output


def _setup(seed: str = "A"):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    return case_state, npc_states, progress


def _build_payload(
    seed: str,
    request: DialogueTurnRequest,
    *,
    elapsed_seconds: float = 0.0,
    extra_known_fact_ids: tuple[str, ...] = (),
):
    case_state, npc_states, progress = _setup(seed)
    if extra_known_fact_ids:
        progress = replace(
            progress,
            known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union(extra_known_fact_ids))),
        )
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=elapsed_seconds)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    turn = execute_dialogue_turn(case_state, runtime, request, context=context)
    learning_state = build_learning_state(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress,
        recent_turns=(make_dialogue_turn_log_entry(turn),),
    )
    return build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states.get(request.npc_id),
        learning_state=learning_state,
    )


def test_fallback_templates_cover_all_turn_status_categories() -> None:
    accepted = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_what_happened"))
    blocked = _build_payload(
        "A",
        DialogueTurnRequest(
            scene_id="S4",
            npc_id="jo",
            intent_id="ask_when",
            provided_slots=(),
        ),
        elapsed_seconds=0.0,
    )
    repaired = _build_payload(
        "A",
        DialogueTurnRequest(scene_id="S3", npc_id="samira", intent_id="ask_when"),
        elapsed_seconds=720.0,
        extra_known_fact_ids=("N2",),
    )
    refused = _build_payload(
        "A",
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="present_evidence",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="time", value="17h58"),
                DialogueTurnSlotValue(slot_name="item", value="ticket"),
            ),
            presented_fact_ids=("N999_UNKNOWN",),
        ),
        elapsed_seconds=720.0,
        extra_known_fact_ids=("N2",),
    )
    invalid_intent = _build_payload(
        "A",
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="request_access"),
        elapsed_seconds=0.0,
    )
    invalid_scene_state = _build_payload(
        "A",
        DialogueTurnRequest(scene_id="S5", npc_id="samira", intent_id="accuse"),
        elapsed_seconds=0.0,
    )
    assert accepted.turn_status == "accepted"
    assert blocked.turn_status == "blocked_gate"
    assert repaired.turn_status == "repair"
    assert refused.turn_status == "refused"
    assert invalid_intent.turn_status == "invalid_intent"
    assert invalid_scene_state.turn_status == "invalid_scene_state"

    for payload in (accepted, blocked, repaired, refused, invalid_intent, invalid_scene_state):
        fallback = build_deterministic_fallback_output(payload, reason_code="adapter_unavailable")
        assert fallback.npc_utterance_text
        if payload.turn_status == "repair":
            assert fallback.short_rephrase_line is not None


def test_resolution_uses_fallback_when_adapter_disabled_or_missing_or_exception() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))

    disabled = resolve_dialogue_adapter_output(payload, adapter=DeterministicDialoguePresentationAdapter(), adapter_enabled=False)
    assert disabled.source == "fallback"
    assert disabled.reason_code == "adapter_disabled"

    missing = resolve_dialogue_adapter_output(payload, adapter=None, adapter_enabled=True)
    assert missing.source == "fallback"
    assert missing.reason_code == "adapter_unavailable"

    broken = resolve_dialogue_adapter_output(payload, adapter=_RaisesAdapter(), adapter_enabled=True)
    assert broken.source == "fallback"
    assert broken.reason_code == "adapter_exception"


def test_resolution_accepts_valid_mapping_output_after_normalization() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))
    adapter = _DictAdapter(
        {
            "npc_utterance_text": "Réponse structurée",
            "response_mode_metadata": ["mode:accept", "source:adapter"],
            "referenced_fact_ids": [],
        }
    )
    resolved = resolve_dialogue_adapter_output(payload, adapter=adapter, adapter_enabled=True)
    assert resolved.source == "adapter"
    assert resolved.reason_code == "adapter_ok"
    assert resolved.normalized_from_mapping is True
    assert resolved.output.response_mode_metadata == ("mode:accept", "source:adapter")


def test_resolution_falls_back_for_invalid_or_unsafe_adapter_outputs() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))

    illegal_fact = _OutputAdapter(
        DialogueAdapterOutput(
            npc_utterance_text="texte",
            referenced_fact_ids=("N8",),
        )
    )
    out_illegal = resolve_dialogue_adapter_output(payload, adapter=illegal_fact, adapter_enabled=True)
    assert out_illegal.source == "fallback"
    assert out_illegal.reason_code == "adapter_illegal_fact_reference"

    bad_structure = _DictAdapter({"short_rephrase_line": "x"})
    out_struct = resolve_dialogue_adapter_output(payload, adapter=bad_structure, adapter_enabled=True)
    assert out_struct.source == "fallback"
    assert out_struct.reason_code == "adapter_invalid_structure"


def test_resolution_falls_back_when_output_conflicts_with_deterministic_turn_status() -> None:
    payload = _build_payload(
        "A",
        DialogueTurnRequest(scene_id="S3", npc_id="samira", intent_id="ask_when"),
        elapsed_seconds=720.0,
        extra_known_fact_ids=("N2",),
    )
    assert payload.turn_status == "repair"

    missing_repair_line = _OutputAdapter(
        DialogueAdapterOutput(
            npc_utterance_text="Tu dois reformuler",
            short_rephrase_line=None,
        )
    )
    resolved = resolve_dialogue_adapter_output(payload, adapter=missing_repair_line, adapter_enabled=True)
    assert resolved.source == "fallback"
    assert resolved.reason_code == "adapter_turn_conflict"

    summary_required_payload = replace(payload, summary_check_code="summary_required")
    no_summary_prompt = _OutputAdapter(
        DialogueAdapterOutput(
            npc_utterance_text="Resume requis",
            short_rephrase_line="mode:sentence_stem",
            summary_prompt_line=None,
        )
    )
    resolved_summary = resolve_dialogue_adapter_output(
        summary_required_payload,
        adapter=no_summary_prompt,
        adapter_enabled=True,
    )
    assert resolved_summary.source == "fallback"
    assert resolved_summary.reason_code == "adapter_turn_conflict"


def test_normalization_rejects_non_mapping_non_output_objects() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))
    try:
        normalize_and_validate_adapter_output(123, payload)
    except TypeError as exc:
        assert "DialogueAdapterOutput or mapping" in str(exc)
    else:
        raise AssertionError("normalize_and_validate_adapter_output should reject unsupported output types")


def test_normalization_canonicalizes_whitespace_and_length_for_presented_lines() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))
    long_line = "  " + ("mot " * 120) + "  "
    normalized, _ = normalize_and_validate_adapter_output(
        {
            "npc_utterance_text": long_line,
            "hint_line": "   indice   simple   ",
            "response_mode_metadata": ["source:adapter", "mode:accept"],
            "referenced_fact_ids": [],
        },
        payload,
    )
    assert normalized.npc_utterance_text is not None
    assert len(normalized.npc_utterance_text) <= 220
    assert "  " not in normalized.npc_utterance_text
    assert normalized.hint_line == "indice simple"


def test_normalization_rejects_unsupported_response_metadata_tokens() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))
    resolved = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": "ok",
                "response_mode_metadata": ["secret:N8_hidden"],
                "referenced_fact_ids": [],
            }
        ),
        adapter_enabled=True,
    )
    assert resolved.source == "fallback"
    assert resolved.reason_code == "adapter_invalid_value"


def test_normalization_rejects_metadata_that_conflicts_with_deterministic_turn_semantics() -> None:
    payload = _build_payload("A", DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"))

    wrong_mode = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": "ok",
                "response_mode_metadata": ["mode:repair", "source:adapter"],
                "referenced_fact_ids": [],
            }
        ),
        adapter_enabled=True,
    )
    assert wrong_mode.source == "fallback"
    assert wrong_mode.reason_code == "adapter_invalid_value"

    reserved_reason = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": "ok",
                "response_mode_metadata": ["reason:hidden_path", "source:adapter"],
                "referenced_fact_ids": [],
            }
        ),
        adapter_enabled=True,
    )
    assert reserved_reason.source == "fallback"
    assert reserved_reason.reason_code == "adapter_invalid_value"
