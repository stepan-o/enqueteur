from __future__ import annotations

"""Host-level Sim4 runner for KVP-0001 live + offline exports.

This module sits ABOVE the SOP-100 DAG and is allowed to import runtime,
snapshot, and integration to wire the system end-to-end. The kernel layers
remain untouched; this is pure orchestration.
"""

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence
import hashlib

from backend.sim4.case_mbam import (
    CaseCompletionAttemptResult,
    CaseState,
    ContradictionExecutionResult,
    DifficultyProfile,
    DialogueExecutionContext,
    DialogueSceneRuntimeState,
    DialogueTurnLogEntry,
    DialogueTurnRequest,
    DialogueSceneTurnExecutionResult,
    InvestigationCommand,
    InvestigationExecutionResult,
    InvestigationProgressState,
    MbamOutcomeEvaluationResult,
    MbamObjectStateBundle,
    NPCState,
    action_flags_from_dialogue_turn,
    apply_execution_result_to_progress,
    apply_dialogue_turn_to_progress,
    apply_investigation_timeline_state,
    apply_outcome_branch_transitions,
    apply_case_timeline_to_npc_states,
    attempt_accusation_completion,
    attempt_recovery_completion,
    build_debug_dialogue_projection,
    build_debug_investigation_projection,
    build_debug_run_recap_projection,
    build_debug_outcome_projection,
    build_debug_case_projection,
    build_debug_npc_semantic_projection,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_initial_mbam_object_state,
    build_visible_dialogue_projection,
    build_visible_investigation_projection,
    build_visible_run_recap_projection,
    build_visible_outcome_projection,
    build_visible_case_projection,
    build_visible_npc_semantic_projection,
    build_visible_learning_projection,
    build_debug_learning_projection,
    evaluate_mbam_case_outcome,
    execute_contradiction_edge,
    execute_dialogue_turn,
    execute_investigation_command,
    generate_case_state,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
)
from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick as run_tick
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext

from backend.sim4.snapshot.output import TickOutputSink
from backend.sim4.snapshot.world_snapshot import WorldSnapshot

from backend.sim4.integration.kvp_state_history import KvpStateHistory
from backend.sim4.integration.live_session import LiveSession
from backend.sim4.integration.live_sink import LiveKvpStateSink
from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.integration.run_anchors import RunAnchors
from backend.sim4.integration.render_spec import RenderSpec
from backend.sim4.integration.export_state import export_state_records
from backend.sim4.integration.export_overlays import (
    export_ui_events_jsonl,
    export_psycho_frames_jsonl,
    export_static_map_jsonl,
)
from backend.sim4.integration.export_verify import reconstruct_state_at_tick
from backend.sim4.integration.manifest_schema import (
    ManifestV0_1,
    RecordPointer,
    DiffInventory,
    IntegritySpec,
    LayoutHints,
    OverlayPointer,
    ALLOWED_CHANNELS,
)
from backend.sim4.integration.manifest_writer import write_manifest


@dataclass(frozen=True)
class LiveSessionConfig:
    session: LiveSession
    channels: Sequence[str] | None = None


@dataclass(frozen=True)
class OfflineExportConfig:
    run_root: str | Path
    channels: Sequence[str]
    # None means "use fallback default" unless explicit keyframe_ticks are provided.
    keyframe_interval: int | None = None
    keyframe_ticks: Sequence[int] | None = None
    ui_events: List[Dict[str, Any]] | None = None
    psycho_frames: List[Dict[str, Any]] | None = None
    ui_event_batch_span_ticks: int = 2
    validate: bool = False


@dataclass(frozen=True)
class MbamCaseConfig:
    """Host-level bootstrap config for MBAM Case Truth attachment."""

    seed: str | int
    difficulty_profile: DifficultyProfile | None = None
    runtime_clock_start: str | None = None
    truth_epoch: int = 1


class CompositeSink:
    """Fan-out sink for multiple downstream consumers (TickOutputSink)."""

    def __init__(self, sinks: Sequence[TickOutputSink]) -> None:
        self._sinks = list(sinks)

    def on_tick_output(
        self,
        *,
        tick_index: int,
        dt: float,
        world_snapshot: WorldSnapshot,
        runtime_events: Sequence[Any],
        narrative_fragments: Sequence[Any],
    ) -> None:
        for s in self._sinks:
            try:
                s.on_tick_output(
                    tick_index=tick_index,
                    dt=dt,
                    world_snapshot=world_snapshot,
                    runtime_events=runtime_events,
                    narrative_fragments=narrative_fragments,
                )
            except Exception:
                # Sinks must never break deterministic kernel
                pass


class SimRunner:
    """End-to-end Sim4 runner with optional live + offline KVP outputs."""

    def __init__(
        self,
        *,
        clock: TickClock,
        ecs_world: ECSWorld,
        world_ctx: WorldContext,
        rng_seed: int,
        system_scheduler: Any,
        run_anchors: RunAnchors,
        render_spec: RenderSpec,
        channels: Sequence[str],
        live_sessions: Sequence[LiveSessionConfig] | None = None,
        offline: OfflineExportConfig | None = None,
        case_config: MbamCaseConfig | None = None,
    ) -> None:
        self._clock = clock
        self._ecs_world = ecs_world
        self._world_ctx = world_ctx
        self._rng_seed = int(rng_seed)
        self._system_scheduler = system_scheduler
        self._run_anchors = run_anchors
        self._render_spec = render_spec

        self._channels = _normalize_channels(channels)

        self._offline_cfg = offline
        self._live_cfgs = list(live_sessions or [])
        self._case_state: CaseState | None = None
        self._case_visible_projection: Dict[str, Any] | None = None
        self._case_debug_projection: Dict[str, Any] | None = None
        self._npc_states: dict[str, NPCState] | None = None
        self._npc_timeline_applied_beat_ids: tuple[str, ...] = ()
        self._investigation_object_state: MbamObjectStateBundle | None = None
        self._investigation_progress: InvestigationProgressState | None = None
        self._dialogue_runtime_state: DialogueSceneRuntimeState | None = None
        self._dialogue_turn_log: tuple[DialogueTurnLogEntry, ...] = ()
        self._manual_case_action_flags: tuple[str, ...] = ()
        self._manual_case_relationship_flags: tuple[str, ...] = ()
        self._manual_case_outcome_flags: tuple[str, ...] = ()

        if case_config is not None:
            truth_epoch = int(case_config.truth_epoch)
            if truth_epoch <= 0:
                raise ValueError("MbamCaseConfig.truth_epoch must be >= 1")
            self._case_state = generate_case_state(
                seed=case_config.seed,
                difficulty_profile=case_config.difficulty_profile,
                runtime_clock_start=case_config.runtime_clock_start,
            )
            self._case_visible_projection = build_visible_case_projection(
                self._case_state,
                truth_epoch=truth_epoch,
            )
            self._case_debug_projection = build_debug_case_projection(
                self._case_state,
                truth_epoch=truth_epoch,
            )
            self._npc_states = initialize_mbam_npc_states_from_case_state(
                self._world_ctx,
                self._case_state,
            )
            self._npc_states, self._npc_timeline_applied_beat_ids = apply_case_timeline_to_npc_states(
                case_state=self._case_state,
                npc_states=self._npc_states,
                elapsed_seconds=0.0,
                applied_beat_ids=(),
            )
            self._investigation_object_state = build_initial_mbam_object_state(self._case_state)
            self._investigation_progress = build_initial_investigation_progress(self._case_state)
            self._investigation_object_state, _timeline_effects, _timeline_transitions = apply_investigation_timeline_state(
                self._investigation_object_state,
                elapsed_seconds=0.0,
            )
            dialogue_context = self._build_dialogue_context(elapsed_seconds=0.0)
            if dialogue_context is not None:
                self._dialogue_runtime_state = build_initial_dialogue_scene_runtime(
                    self._case_state,
                    context=dialogue_context,
                )
            self._apply_case_outcome_branch_transitions(elapsed_seconds=0.0)

        # Build sinks
        sinks: List[TickOutputSink] = []
        npc_visible_provider = self._make_npc_semantic_visible_projection
        npc_debug_provider = self._make_npc_semantic_debug_projection
        investigation_visible_provider = self._make_investigation_visible_projection
        investigation_debug_provider = self._make_investigation_debug_projection
        dialogue_visible_provider = self._make_dialogue_visible_projection
        dialogue_debug_provider = self._make_dialogue_debug_projection
        learning_visible_provider = self._make_learning_visible_projection
        learning_debug_provider = self._make_learning_debug_projection
        outcome_visible_provider = self._make_outcome_visible_projection
        outcome_debug_provider = self._make_outcome_debug_projection
        recap_visible_provider = self._make_case_recap_visible_projection
        recap_debug_provider = self._make_case_recap_debug_projection

        self._history: KvpStateHistory | None = None
        if self._offline_cfg is not None:
            # Offline history uses its own channel set
            offline_channels = _normalize_channels(self._offline_cfg.channels)
            self._history = KvpStateHistory(
                channels=offline_channels,
                case_visible_projection=self._case_visible_projection,
                case_debug_projection=self._case_debug_projection,
                npc_semantic_visible_provider=npc_visible_provider,
                npc_semantic_debug_provider=npc_debug_provider,
                investigation_visible_provider=investigation_visible_provider,
                investigation_debug_provider=investigation_debug_provider,
                dialogue_visible_provider=dialogue_visible_provider,
                dialogue_debug_provider=dialogue_debug_provider,
                learning_visible_provider=learning_visible_provider,
                learning_debug_provider=learning_debug_provider,
                outcome_visible_provider=outcome_visible_provider,
                outcome_debug_provider=outcome_debug_provider,
                case_recap_visible_provider=recap_visible_provider,
                case_recap_debug_provider=recap_debug_provider,
            )
            sinks.append(self._history)

        for cfg in self._live_cfgs:
            live_channels = _normalize_channels(cfg.channels or self._channels)
            sinks.append(
                LiveKvpStateSink(
                    cfg.session,
                    channels=live_channels,
                    case_visible_projection=self._case_visible_projection,
                    case_debug_projection=self._case_debug_projection,
                    npc_semantic_visible_provider=npc_visible_provider,
                    npc_semantic_debug_provider=npc_debug_provider,
                    investigation_visible_provider=investigation_visible_provider,
                    investigation_debug_provider=investigation_debug_provider,
                    dialogue_visible_provider=dialogue_visible_provider,
                    dialogue_debug_provider=dialogue_debug_provider,
                    learning_visible_provider=learning_visible_provider,
                    learning_debug_provider=learning_debug_provider,
                    outcome_visible_provider=outcome_visible_provider,
                    outcome_debug_provider=outcome_debug_provider,
                    case_recap_visible_provider=recap_visible_provider,
                    case_recap_debug_provider=recap_debug_provider,
                )
            )

        self._sink: TickOutputSink | None = CompositeSink(sinks) if sinks else None

    def get_case_state(self) -> CaseState | None:
        """Return attached MBAM CaseState for this run, if configured."""
        return self._case_state

    def get_npc_states(self) -> dict[str, NPCState]:
        """Return a copy of initialized MBAM runtime NPC states."""
        if self._npc_states is None:
            return {}
        return dict(self._npc_states)

    def get_npc_state(self, npc_id: str) -> NPCState | None:
        """Return one MBAM runtime NPC state by id, if initialized."""
        if self._npc_states is None:
            return None
        return self._npc_states.get(npc_id)

    def get_investigation_object_state(self) -> MbamObjectStateBundle | None:
        """Return MBAM investigation object-state bundle for this run, if configured."""
        return self._investigation_object_state

    def get_investigation_progress(self) -> InvestigationProgressState | None:
        """Return MBAM investigation progression state for this run, if configured."""
        return self._investigation_progress

    def get_dialogue_runtime_state(self) -> DialogueSceneRuntimeState | None:
        """Return MBAM dialogue runtime state for this run, if configured."""
        return self._dialogue_runtime_state

    def get_dialogue_turn_log(self) -> tuple[DialogueTurnLogEntry, ...]:
        """Return deterministic dialogue turn log for replay/debug."""
        return tuple(self._dialogue_turn_log)

    def get_case_outcome_evaluation(self) -> MbamOutcomeEvaluationResult | None:
        """Evaluate current deterministic MBAM outcome state for this run."""
        return self._build_case_outcome_evaluation()

    def record_case_action_flags(self, *action_flags: str) -> None:
        """Record deterministic outcome action flags from external adapters."""
        incoming = tuple(sorted({flag for flag in action_flags if isinstance(flag, str) and flag}))
        if not incoming:
            return
        merged = tuple(sorted(set(self._manual_case_action_flags).union(incoming)))
        self._manual_case_action_flags = merged

    def record_case_relationship_flags(self, *relationship_flags: str) -> None:
        """Record deterministic relationship flags from external adapters."""
        incoming = tuple(sorted({flag for flag in relationship_flags if isinstance(flag, str) and flag}))
        if not incoming:
            return
        merged = tuple(sorted(set(self._manual_case_relationship_flags).union(incoming)))
        self._manual_case_relationship_flags = merged

    def record_case_outcome_flags(self, *outcome_flags: str) -> None:
        """Record deterministic outcome-state flags from external adapters."""
        incoming = tuple(sorted({flag for flag in outcome_flags if isinstance(flag, str) and flag}))
        if not incoming:
            return
        merged = tuple(sorted(set(self._manual_case_outcome_flags).union(incoming)))
        self._manual_case_outcome_flags = merged

    def submit_investigation_command(
        self,
        command: InvestigationCommand,
        *,
        available_prerequisites: Iterable[str] = (),
    ) -> InvestigationExecutionResult | None:
        """Execute one deterministic MBAM investigation command against runtime state."""
        if (
            self._case_state is None
            or self._investigation_object_state is None
            or self._investigation_progress is None
        ):
            return None
        elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
        execution = execute_investigation_command(
            command,
            case_state=self._case_state,
            object_state=self._investigation_object_state,
            elapsed_seconds=elapsed_seconds,
            available_prerequisites=available_prerequisites,
            consumed_action_keys=self._investigation_progress.consumed_action_keys,
        )
        self._investigation_object_state = execution.object_state_after
        update = apply_execution_result_to_progress(
            self._case_state,
            self._investigation_progress,
            execution,
        )
        self._investigation_progress = update.progress_after
        self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)
        return execution

    def submit_contradiction_edge(
        self,
        *,
        edge_id: str,
    ) -> ContradictionExecutionResult | None:
        """Record a deterministic contradiction edge when ingredient facts are known."""
        if self._case_state is None or self._investigation_progress is None:
            return None
        result = execute_contradiction_edge(
            self._case_state,
            self._investigation_progress,
            edge_id=edge_id,
        )
        if result.status == "success":
            self._investigation_progress = result.progress_after
            elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
            self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)
        return result

    def attempt_case_recovery(
        self,
        *,
        quiet: bool = True,
    ) -> CaseCompletionAttemptResult | None:
        """Attempt deterministic recovery-path case completion."""
        if (
            self._case_state is None
            or self._investigation_progress is None
            or self._investigation_object_state is None
        ):
            return None
        elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
        result = attempt_recovery_completion(
            case_state=self._case_state,
            progress=self._investigation_progress,
            object_state=self._investigation_object_state,
            dialogue_runtime_state=self._dialogue_runtime_state,
            npc_states=self._npc_states,
            elapsed_seconds=elapsed_seconds,
            extra_action_flags=self._manual_case_action_flags,
            relationship_flags=self._manual_case_relationship_flags,
            outcome_flags=self._manual_case_outcome_flags,
            quiet=quiet,
        )
        self._investigation_progress = result.progress_after
        if result.object_state_after is not None:
            self._investigation_object_state = result.object_state_after
        if result.applied_outcome_flags:
            self.record_case_outcome_flags(*result.applied_outcome_flags)
        self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)
        return result

    def attempt_case_accusation(
        self,
        *,
        accused_id: str,
        public: bool = False,
    ) -> CaseCompletionAttemptResult | None:
        """Attempt deterministic accusation-path case completion."""
        if self._case_state is None or self._investigation_progress is None:
            return None
        elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
        result = attempt_accusation_completion(
            case_state=self._case_state,
            progress=self._investigation_progress,
            object_state=self._investigation_object_state,
            dialogue_runtime_state=self._dialogue_runtime_state,
            npc_states=self._npc_states,
            elapsed_seconds=elapsed_seconds,
            accused_id=accused_id,
            extra_action_flags=self._manual_case_action_flags,
            relationship_flags=self._manual_case_relationship_flags,
            outcome_flags=self._manual_case_outcome_flags,
            public=public,
        )
        self._investigation_progress = result.progress_after
        if result.object_state_after is not None:
            self._investigation_object_state = result.object_state_after
        if result.applied_outcome_flags:
            self.record_case_outcome_flags(*result.applied_outcome_flags)
        self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)
        return result

    def submit_dialogue_turn(
        self,
        request: DialogueTurnRequest,
        *,
        max_log_entries: int = 16,
    ) -> DialogueSceneTurnExecutionResult | None:
        """Execute one deterministic dialogue turn and apply resulting runtime updates."""
        if (
            self._case_state is None
            or self._dialogue_runtime_state is None
            or self._investigation_progress is None
        ):
            return None
        context = self._build_dialogue_context(
            elapsed_seconds=float(self._clock.tick_index) * float(self._clock.dt),
        )
        if context is None:
            return None
        result = execute_dialogue_turn(
            self._case_state,
            self._dialogue_runtime_state,
            request,
            context=context,
        )
        self._dialogue_runtime_state = result.runtime_after
        self._investigation_progress = apply_dialogue_turn_to_progress(
            self._investigation_progress,
            result,
        )
        prior_summary_pass_count = sum(1 for row in self._dialogue_turn_log if row.summary_check_code == "summary_passed")
        derived_action_flags = action_flags_from_dialogue_turn(
            self._case_state,
            request,
            result,
            prior_summary_pass_count=prior_summary_pass_count,
        )
        if derived_action_flags:
            self._investigation_progress = replace(
                self._investigation_progress,
                satisfied_action_flags=tuple(
                    sorted(
                        set(self._investigation_progress.satisfied_action_flags).union(derived_action_flags)
                    )
                ),
            )
        entry = make_dialogue_turn_log_entry(result)
        existing = list(self._dialogue_turn_log)
        existing.append(entry)
        cap = max(0, int(max_log_entries))
        if cap > 0 and len(existing) > cap:
            existing = existing[-cap:]
        self._dialogue_turn_log = tuple(existing)
        elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
        self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)
        return result

    def _apply_case_outcome_branch_transitions(self, *, elapsed_seconds: float) -> None:
        if self._case_state is None or self._investigation_progress is None:
            return
        transition = apply_outcome_branch_transitions(
            case_state=self._case_state,
            progress=self._investigation_progress,
            object_state=self._investigation_object_state,
            npc_states=self._npc_states,
            elapsed_seconds=float(elapsed_seconds),
            extra_action_flags=self._manual_case_action_flags,
            relationship_flags=self._manual_case_relationship_flags,
            outcome_flags=self._manual_case_outcome_flags,
        )
        self._investigation_progress = transition.progress_after
        if transition.object_state_after is not None:
            self._investigation_object_state = transition.object_state_after
        self._manual_case_outcome_flags = transition.outcome_flags_after

    def _build_dialogue_context(self, *, elapsed_seconds: float) -> DialogueExecutionContext | None:
        if self._investigation_progress is None or self._npc_states is None:
            return None
        return build_dialogue_execution_context(
            self._investigation_progress,
            self._npc_states,
            elapsed_seconds=float(elapsed_seconds),
        )

    def _make_npc_semantic_visible_projection(self) -> list[dict[str, Any]] | None:
        if self._npc_states is None:
            return None
        return build_visible_npc_semantic_projection(self._npc_states)

    def _make_npc_semantic_debug_projection(self) -> list[dict[str, Any]] | None:
        if self._npc_states is None:
            return None
        return build_debug_npc_semantic_projection(self._npc_states)

    def _make_investigation_visible_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._investigation_object_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_visible_investigation_projection(
            case_state=self._case_state,
            object_state=self._investigation_object_state,
            progress=self._investigation_progress,
        )

    def _make_investigation_debug_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._investigation_object_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_debug_investigation_projection(
            case_state=self._case_state,
            object_state=self._investigation_object_state,
            progress=self._investigation_progress,
        )

    def _make_dialogue_visible_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._dialogue_runtime_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_visible_dialogue_projection(
            case_state=self._case_state,
            runtime_state=self._dialogue_runtime_state,
            progress=self._investigation_progress,
            recent_turns=self._dialogue_turn_log,
        )

    def _make_dialogue_debug_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._dialogue_runtime_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_debug_dialogue_projection(
            case_state=self._case_state,
            runtime_state=self._dialogue_runtime_state,
            progress=self._investigation_progress,
            recent_turns=self._dialogue_turn_log,
        )

    def _make_learning_visible_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._dialogue_runtime_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_visible_learning_projection(
            case_state=self._case_state,
            runtime_state=self._dialogue_runtime_state,
            progress=self._investigation_progress,
            recent_turns=self._dialogue_turn_log,
        )

    def _make_learning_debug_projection(self) -> dict[str, Any] | None:
        if (
            self._case_state is None
            or self._dialogue_runtime_state is None
            or self._investigation_progress is None
        ):
            return None
        return build_debug_learning_projection(
            case_state=self._case_state,
            runtime_state=self._dialogue_runtime_state,
            progress=self._investigation_progress,
            recent_turns=self._dialogue_turn_log,
        )

    def _build_case_outcome_evaluation(self) -> MbamOutcomeEvaluationResult | None:
        if self._case_state is None or self._investigation_progress is None:
            return None
        elapsed_seconds = float(self._clock.tick_index) * float(self._clock.dt)
        return evaluate_mbam_case_outcome(
            case_state=self._case_state,
            progress=self._investigation_progress,
            object_state=self._investigation_object_state,
            npc_states=self._npc_states,
            dialogue_turn_log=self._dialogue_turn_log,
            elapsed_seconds=elapsed_seconds,
            extra_action_flags=self._manual_case_action_flags,
            relationship_flags=self._manual_case_relationship_flags,
            outcome_flags=self._manual_case_outcome_flags,
        )

    def _make_outcome_visible_projection(self) -> dict[str, Any] | None:
        evaluation = self._build_case_outcome_evaluation()
        if evaluation is None:
            return None
        return build_visible_outcome_projection(evaluation)

    def _make_outcome_debug_projection(self) -> dict[str, Any] | None:
        evaluation = self._build_case_outcome_evaluation()
        if evaluation is None:
            return None
        return build_debug_outcome_projection(evaluation)

    def _make_case_recap_visible_projection(self) -> dict[str, Any] | None:
        evaluation = self._build_case_outcome_evaluation()
        if evaluation is None:
            return None
        return build_visible_run_recap_projection(evaluation)

    def _make_case_recap_debug_projection(self) -> dict[str, Any] | None:
        evaluation = self._build_case_outcome_evaluation()
        if evaluation is None:
            return None
        return build_debug_run_recap_projection(evaluation)

    def run(
        self,
        *,
        num_ticks: int,
        episode_id: int = 0,
        narrative_ctx: Any | None = None,
        world_commands_provider: Callable[[int], Iterable[Any]] | None = None,
    ) -> None:
        """Run the simulation for a fixed number of ticks."""
        for _ in range(int(num_ticks)):
            if self._case_state is not None and self._npc_states is not None:
                # Project semantic state for the tick that run_tick(...) is about to emit.
                # tick() advances the clock at start-of-step; use next tick time here.
                elapsed_seconds = float(self._clock.tick_index + 1) * float(self._clock.dt)
                self._npc_states, self._npc_timeline_applied_beat_ids = apply_case_timeline_to_npc_states(
                    case_state=self._case_state,
                    npc_states=self._npc_states,
                    elapsed_seconds=elapsed_seconds,
                    applied_beat_ids=self._npc_timeline_applied_beat_ids,
                )
                if self._investigation_object_state is not None:
                    self._investigation_object_state, _effects, _transitions = apply_investigation_timeline_state(
                        self._investigation_object_state,
                        elapsed_seconds=elapsed_seconds,
                    )
                self._apply_case_outcome_branch_transitions(elapsed_seconds=elapsed_seconds)

            wc = None
            if world_commands_provider is not None:
                try:
                    wc = list(world_commands_provider(self._clock.tick_index))
                except Exception:
                    wc = None
            run_tick(
                clock=self._clock,
                ecs_world=self._ecs_world,
                world_ctx=self._world_ctx,
                rng_seed=self._rng_seed,
                system_scheduler=self._system_scheduler,
                previous_events=None,
                world_commands_in=wc,
                episode_id=episode_id,
                narrative_ctx=narrative_ctx,
                tick_output_sink=self._sink,
                run_id=None,
            )

        # Finalize offline export if configured
        if self._offline_cfg is not None and self._history is not None:
            self._write_offline_artifacts(self._offline_cfg, self._history)

    # ---- Offline export helpers ----
    def _write_offline_artifacts(self, cfg: OfflineExportConfig, history: KvpStateHistory) -> None:
        ticks = history.ticks()
        if not ticks:
            raise ValueError("No ticks recorded; cannot export artifacts")
        if ticks != list(range(min(ticks), max(ticks) + 1)):
            raise ValueError("Ticks are not contiguous; export requires full per-tick coverage")

        start_tick = min(ticks)
        end_tick = max(ticks)

        # Keyframe policy (XOR)
        if cfg.keyframe_ticks is not None and cfg.keyframe_interval is not None:
            raise ValueError("Provide exactly one of keyframe_interval or keyframe_ticks")
        keyframe_ticks = list(cfg.keyframe_ticks) if cfg.keyframe_ticks is not None else None
        keyframe_interval = int(cfg.keyframe_interval) if cfg.keyframe_interval is not None else None
        if keyframe_ticks is None and keyframe_interval is None:
            keyframe_interval = 100

        # Build draft manifest (integrity placeholder)
        draft_manifest = _build_manifest(
            run_anchors=self._run_anchors,
            render_spec=self._render_spec,
            channels=_normalize_channels(cfg.channels),
            start_tick=start_tick,
            end_tick=end_tick,
            keyframe_interval=keyframe_interval,
            keyframe_ticks=keyframe_ticks,
            integrity_map=_placeholder_integrity_map(start_tick, end_tick, keyframe_interval, keyframe_ticks),
            overlays=None,
        )

        run_root = Path(cfg.run_root)
        export_state_records(run_root, draft_manifest, history)

        # Overlays (optional)
        overlays_map: Dict[str, OverlayPointer] | None = {}
        # Static map (single-line JSONL envelope)
        static_rel = export_static_map_jsonl(run_root, self._world_ctx, self._render_spec)
        overlays_map["static_map"] = OverlayPointer(rel_path=static_rel, format="JSONL", notes="X_STATIC_MAP")

        # Other overlays (optional)
        if cfg.ui_events is not None:
            ui_rel = export_ui_events_jsonl(
                run_root,
                start_tick=start_tick,
                end_tick=end_tick,
                events=cfg.ui_events,
                batch_span_ticks=int(cfg.ui_event_batch_span_ticks),
            )
            overlays_map["ui_events"] = OverlayPointer(rel_path=ui_rel, format="JSONL", notes="X_UI_EVENT_BATCH")
        if cfg.psycho_frames is not None:
            psy_rel = export_psycho_frames_jsonl(run_root, cfg.psycho_frames)
            overlays_map["psycho_frames"] = OverlayPointer(rel_path=psy_rel, format="JSONL", notes="X_PSYCHO_FRAME")

        # Compute integrity hashes from written records
        integrity_map = _compute_integrity_map(run_root, draft_manifest)

        final_manifest = _build_manifest(
            run_anchors=self._run_anchors,
            render_spec=self._render_spec,
            channels=_normalize_channels(cfg.channels),
            start_tick=start_tick,
            end_tick=end_tick,
            keyframe_interval=keyframe_interval,
            keyframe_ticks=keyframe_ticks,
            integrity_map=integrity_map,
            overlays=overlays_map,
        )

        write_manifest(run_root / "manifest.kvp.json", final_manifest)

        if cfg.validate:
            # Validate reconstruction at the final tick
            reconstruct_state_at_tick(run_root, final_manifest, end_tick)


def _normalize_channels(channels: Sequence[str]) -> List[str]:
    out = sorted({c for c in channels if c in ALLOWED_CHANNELS})
    if not out:
        raise ValueError("channels must be a non-empty subset of ALLOWED_CHANNELS")
    return out


def _build_manifest(
    *,
    run_anchors: RunAnchors,
    render_spec: RenderSpec,
    channels: Sequence[str],
    start_tick: int,
    end_tick: int,
    keyframe_interval: int | None,
    keyframe_ticks: Sequence[int] | None,
    integrity_map: Dict[str, str],
    overlays: Dict[str, OverlayPointer] | None,
) -> ManifestV0_1:
    channels_norm = _normalize_channels(channels)

    # Keyframe policy XOR
    if keyframe_interval is not None and keyframe_ticks is not None:
        raise ValueError("Provide exactly one of keyframe_interval or keyframe_ticks")

    snaps: Dict[int, RecordPointer] = {}
    diffs: Dict[int, RecordPointer] = {}

    kf_ticks: List[int]
    if keyframe_ticks is not None:
        kf_ticks = list(keyframe_ticks)
    else:
        kf_ticks = []
        k = int(keyframe_interval) if keyframe_interval is not None else 1
        t = int(start_tick)
        while t <= int(end_tick):
            kf_ticks.append(t)
            t += k

    for t in kf_ticks:
        rp = RecordPointer(
            id=f"snap:{t}",
            rel_path=f"state/snapshots/tick_{t:010d}.kvp.json",
            format="SINGLE_JSON",
            msg_type="FULL_SNAPSHOT",
            tick=int(t),
        )
        snaps[int(t)] = rp

    for ft in range(int(start_tick), int(end_tick)):
        rp = RecordPointer(
            id=f"diff:{ft}->{ft+1}",
            rel_path=f"state/diffs/from_{ft:010d}_to_{ft+1:010d}.kvp.json",
            format="SINGLE_JSON",
            msg_type="FRAME_DIFF",
            from_tick=int(ft),
            to_tick=int(ft + 1),
        )
        diffs[int(ft)] = rp

    layout = LayoutHints(
        records_root=".",
        snapshots_dir="state/snapshots",
        diffs_dir="state/diffs",
        overlays_dir="overlays" if overlays else None,
        index_dir="index",
        diff_storage="PER_TICK_FILES",
    )

    integrity = IntegritySpec.from_dict(
        {
            "hash_alg": "SHA-256",
            "records_sha256": integrity_map,
        }
    )

    return ManifestV0_1(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=run_anchors,
        render_spec=render_spec,
        available_start_tick=int(start_tick),
        available_end_tick=int(end_tick),
        channels=list(channels_norm),
        keyframe_interval=int(keyframe_interval) if keyframe_interval is not None else None,
        keyframe_ticks=list(keyframe_ticks) if keyframe_ticks is not None else None,
        snapshots=snaps,
        diffs=DiffInventory(diffs_by_from_tick=diffs),
        integrity=integrity,
        layout=layout,
        overlays=overlays,
    )


def _placeholder_integrity_map(
    start_tick: int,
    end_tick: int,
    keyframe_interval: int | None,
    keyframe_ticks: Sequence[int] | None,
) -> Dict[str, str]:
    # Provide a non-empty placeholder map (required by IntegritySpec)
    placeholder = "0" * 64
    out: Dict[str, str] = {}

    kf_ticks: List[int]
    if keyframe_ticks is not None:
        kf_ticks = list(keyframe_ticks)
    else:
        kf_ticks = []
        k = int(keyframe_interval) if keyframe_interval is not None else 1
        t = int(start_tick)
        while t <= int(end_tick):
            kf_ticks.append(t)
            t += k

    for t in kf_ticks:
        out[f"state/snapshots/tick_{int(t):010d}.kvp.json"] = placeholder
    for ft in range(int(start_tick), int(end_tick)):
        out[f"state/diffs/from_{int(ft):010d}_to_{int(ft+1):010d}.kvp.json"] = placeholder

    if not out:
        out["placeholder"] = placeholder
    return out


def _compute_integrity_map(run_root: Path, manifest: ManifestV0_1) -> Dict[str, str]:
    out: Dict[str, str] = {}
    # snapshots + diffs only
    for rp in list(manifest.snapshots.values()) + list(manifest.diffs.diffs_by_from_tick.values()):
        path = run_root / rp.rel_path
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        out[rp.rel_path] = sha
    return out


__all__ = [
    "LiveSessionConfig",
    "OfflineExportConfig",
    "MbamCaseConfig",
    "CompositeSink",
    "SimRunner",
]
