"""CLI entrypoint for Loopforge City simulation.

Usage (uv):
  uv run python -m scripts.run_simulation --steps 10

Or via installed script:
  loopforge-sim --steps 10
"""
from __future__ import annotations

import sys
import json
import typer

from loopforge.core.simulation import run_simulation
from loopforge.core.config import get_settings
from loopforge.core.logging_utils import read_action_log_entries
from loopforge.core.day_runner import run_one_day_with_supervisor, compute_day_summary
from loopforge.reporting import summarize_episode, EpisodeSummary, AgentEpisodeStats, DaySummary
from loopforge.reporting import AgentDayStats
from loopforge.schema.types import ActionLogEntry
from loopforge.supervisor_activity import compute_supervisor_activity
from loopforge.analysis_api import analyze_episode, episode_summary_to_dict, analyze_episode_from_record
from pathlib import Path
from collections import Counter, defaultdict
from typing import Optional, Dict, Optional as _Optional

app = typer.Typer(add_completion=False, help="Run the Loopforge City simulation loop")


# ---------------- Shared Printers ----------------

def _print_episode_recap(episode: EpisodeSummary) -> None:
    try:
        from loopforge.episode_recaps import build_episode_recap
        from loopforge.characters import CHARACTERS
    except Exception:
        build_episode_recap = None
        CHARACTERS = {}
    if build_episode_recap is None:
        return
    recap_obj = build_episode_recap(episode, episode.days, CHARACTERS)
    typer.echo("\nEPISODE RECAP")
    typer.echo("=" * 30)
    typer.echo(recap_obj.intro)
    # Deterministic ordering of agents
    for name in sorted(recap_obj.per_agent_blurbs.keys()):
        typer.echo(f"- {name}: {recap_obj.per_agent_blurbs[name]}")
    typer.echo(recap_obj.closing)
    # STORY ARC
    if getattr(recap_obj, "story_arc_lines", None):
        typer.echo("\nSTORY ARC")
        typer.echo("-" * 30)
        for line in recap_obj.story_arc_lines:  # type: ignore[union-attr]
            typer.echo(line)
    # WORLD PULSE — after STORY ARC and before ARC COHESION
    if getattr(recap_obj, "world_pulse_lines", None):
        typer.echo("\nWORLD PULSE")
        typer.echo("-" * 30)
        for line in recap_obj.world_pulse_lines:  # type: ignore[union-attr]
            typer.echo(line)
    # MICRO-INCIDENTS — after WORLD PULSE, before ARC COHESION
    if getattr(recap_obj, "micro_incident_lines", None):
        typer.echo("\nMICRO-INCIDENTS")
        typer.echo("-" * 30)
        for line in recap_obj.micro_incident_lines:  # type: ignore[union-attr]
            typer.echo(line)
    # ARC COHESION
    if getattr(recap_obj, "arc_cohesion", None):
        typer.echo("\nARC COHESION")
        typer.echo("-" * 30)
        typer.echo(str(recap_obj.arc_cohesion))
    # MEMORY LINE
    if getattr(recap_obj, "memory_line", None):
        typer.echo("\nMEMORY LINE")
        typer.echo("-" * 30)
        typer.echo(str(recap_obj.memory_line))
    # MEMORY DRIFT
    if getattr(recap_obj, "memory_lines", None):
        typer.echo("\nMEMORY DRIFT")
        typer.echo("-" * 30)
        for line in recap_obj.memory_lines:  # type: ignore[union-attr]
            typer.echo(line)
    # DISTORTIONS (Attribution Drift)
    if getattr(recap_obj, "distortion_lines", None):
        typer.echo("\nDISTORTIONS")
        typer.echo("-" * 30)
        for line in recap_obj.distortion_lines:  # type: ignore[union-attr]
            typer.echo(line)
    # PRESSURE NOTES
    if getattr(recap_obj, "pressure_lines", None):
        typer.echo("\nPRESSURE NOTES")
        typer.echo("-" * 30)
        for line in recap_obj.pressure_lines:  # type: ignore[union-attr]
            typer.echo(line)


# Allow invoking the module without an explicit subcommand, e.g.:
#   uv run python -m scripts.run_simulation --no-db --steps 10
# This preserves backward compatibility with the Makefile target `make run`.
@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    steps: int = typer.Option(None, "--steps", "-n", help="Number of simulation steps to run"),
    no_db: bool = typer.Option(False, "--no-db", help="Run without database persistence (in-memory test)"),
) -> None:
    if ctx.invoked_subcommand is None:
        # Defer to the main run command implementation
        main(steps=steps, no_db=no_db)


@app.command()
def main(
    steps: int = typer.Option(None, "--steps", "-n", help="Number of simulation steps to run"),
    no_db: bool = typer.Option(False, "--no-db", help="Run without database persistence (in-memory test)"),
) -> None:
    settings = get_settings()
    num_steps = steps if steps is not None else settings.simulate_steps
    persist = settings.persist_to_db and not no_db
    mode = "no-DB (in-memory)" if not persist else "DB-backed"
    typer.echo(f"Starting Loopforge City simulation for {num_steps} steps ({mode})...")
    run_simulation(num_steps=num_steps, persist_to_db=persist)


@app.command()
def view_day(
    run_id: Optional[str] = typer.Argument(
        None,
        help="Run ID (ignored when using --latest)",
    ),
    episode_id: Optional[str] = typer.Argument(
        None,
        help="Episode ID (ignored when using --latest)",
    ),
    day_index: Optional[int] = typer.Argument(
        None,
        help="Day index (0-based). When using --latest, this is the only positional arg.",
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Use the latest episode from the run registry and infer run_id/episode_id.",
    ),
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    reflection_log_path: Path | None = typer.Option(None, help="Where to write reflections JSONL (optional)"),
    supervisor_log_path: Path | None = typer.Option(None, help="Where to write supervisor JSONL (optional)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    registry_base: Path | None = None,
) -> None:
    """
    View a day-level summary for a given run / episode / day.

    With --latest:
      - Automatically picks the latest episode from the registry
      - 'day_index' is taken from the single positional argument (defaults to 0)
    """
    from loopforge import run_registry
    from loopforge.core.logging_utils import read_action_log_entries_for_episode

    import typer as _typer

    # Branch 1: --latest path
    if latest:
        # Convenience: allow a single positional argument as day_index when using --latest
        # Typer will bind it to run_id in our signature. If episode_id and day_index are None
        # and run_id looks like an int, reinterpret it as day_index and clear run_id.
        if run_id is not None and episode_id is None and day_index is None:
            try:
                maybe_idx = int(str(run_id))
                day_index = maybe_idx
                run_id = None
            except Exception:
                # leave as-is; will be caught by mix guard below
                pass

        # Disallow mixing explicit IDs with --latest for now (keeps UX predictable)
        if run_id is not None or episode_id is not None:
            raise _typer.BadParameter(
                "Do not provide RUN_ID/EPISODE_ID when using --latest. Use either explicit IDs OR --latest."
            )

        # Resolve latest episode record
        record = run_registry.latest_episode_record(base_dir=registry_base)
        if record is None:
            _typer.echo("No episodes found in the registry yet.", err=True)
            raise _typer.Exit(code=1)

        # Decide day index: use argument if provided, else default to 0
        if day_index is None:
            day_index_resolved = 0
        else:
            day_index_resolved = int(day_index)

        # Validate day index against record.days
        if getattr(record, "days", 0) <= 0:
            _typer.echo(
                f"Latest episode has 0 full days (run_id={record.run_id}, episode_id={record.episode_id}). "
                "Run with more steps or use 'view-episode' instead.",
                err=True,
            )
            raise _typer.Exit(code=1)

        if not (0 <= day_index_resolved < int(getattr(record, "days", 0) or 0)):
            _typer.echo(
                f"Invalid day index {day_index_resolved} for latest episode (days={record.days}).",
                err=True,
            )
            raise _typer.Exit(code=1)

        # Override IDs with the latest record
        run_id = record.run_id
        episode_id = record.episode_id
        day_index = day_index_resolved

    # Branch 2: legacy / explicit IDs path (no --latest)
    else:
        # Enforce that all three are provided
        if run_id is None or episode_id is None or day_index is None:
            raise _typer.BadParameter(
                "Usage: loopforge-sim view-day RUN_ID EPISODE_ID DAY_INDEX\n"
                "Or:    loopforge-sim view-day --latest [DAY_INDEX]"
            )

    # At this point we have concrete run_id, episode_id, day_index
    assert run_id is not None and episode_id is not None and day_index is not None

    # Load entries limited strictly to this episode
    try:
        raw_entries = read_action_log_entries_for_episode(action_log_path, str(run_id), str(episode_id))
    except Exception:
        raw_entries = []

    # If no entries found, fall back to reading all and continue (maintain fail-soft UX)
    if not raw_entries:
        entries: list[ActionLogEntry] = read_action_log_entries(action_log_path)
    else:
        # Convert to ActionLogEntry objects for uniform downstream handling
        entries = []
        for d in raw_entries:
            try:
                entries.append(ActionLogEntry.from_dict(d))
            except Exception:
                continue

    if not entries:
        _typer.echo(f"No action entries found at {action_log_path}")
        raise _typer.Exit(code=0)

    # Build minimal env + agent stubs inferred from entries
    class _Env:
        def __init__(self) -> None:
            self.supervisor_messages = {}
    env = _Env()

    # Deduce agents (name, role)
    agent_roles: dict[str, str] = {}
    for e in entries:
        agent_roles.setdefault(e.agent_name, e.role)
    agents = [type("AgentStub", (), {"name": n, "role": r, "traits": {}})() for n, r in sorted(agent_roles.items())]

    # Run day orchestration (reads logs, not env)
    messages = run_one_day_with_supervisor(
        env=env,
        agents=agents,
        steps_per_day=steps_per_day,
        day_index=int(day_index),
        action_log_path=action_log_path,
        reflection_log_path=reflection_log_path,
        supervisor_log_path=supervisor_log_path,
    )

    # Slice entries for this day for stats
    start = int(day_index) * steps_per_day
    end = (int(day_index) + 1) * steps_per_day
    day_entries = [e for e in entries if start <= e.step < end]

    # Prepare aggregates
    by_agent: dict[str, list[ActionLogEntry]] = defaultdict(list)
    for e in day_entries:
        by_agent[e.agent_name].append(e)

    _typer.echo(f"Day {int(day_index)} — Summary")
    _typer.echo("=" * 25)
    _typer.echo("")

    for name in sorted(agent_roles.keys()):
        role = agent_roles[name]
        rows = by_agent.get(name, [])
        intents = Counter(e.intent for e in rows if e.intent)
        # Average emotions from perception snapshot if available
        stress_vals = []
        curiosity_vals = []
        satisfaction_vals = []
        for e in rows:
            emo = (e.perception or {}).get("emotions") or {}
            if isinstance(emo, dict):
                stress_vals.append(float(emo.get("stress", 0.0)))
                curiosity_vals.append(float(emo.get("curiosity", 0.0)))
                satisfaction_vals.append(float(emo.get("satisfaction", 0.0)))
        def _avg(vs: list[float]) -> float:
            return sum(vs) / len(vs) if vs else 0.0
        top3 = ", ".join(f"{k} ({v})" for k, v in intents.most_common(3)) or "(no intents)"
        _typer.echo(f"{name} ({role})")
        _typer.echo(f"- Intents: {top3}")
        _typer.echo(
            f"- Emotions: stress={_avg(stress_vals):.2f}, curiosity={_avg(curiosity_vals):.2f}, satisfaction={_avg(satisfaction_vals):.2f}"
        )
        # Best-effort reflection summary: take the last narrative for the agent on that day
        summary_line = None
        for e in reversed(rows):
            if e.narrative:
                summary_line = e.narrative
                break
        _typer.echo(f"- Reflection: \"{summary_line or '—'}\"")
        _typer.echo("")

    _typer.echo("Supervisor")
    sup_intents = ", ".join(f"\"{m.intent}\"" for m in messages) or "(none)"
    _typer.echo(f"- Messages: {sup_intents}")


@app.command()
def view_episode(
    run_id: Optional[str] = typer.Argument(
        None,
        help="Run ID (ignored when using --latest).",
    ),
    episode_id: Optional[str] = typer.Argument(
        None,
        help="Episode ID (ignored when using --latest).",
    ),
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    supervisor_log_path: Path | None = typer.Option(None, help="Path to supervisor JSONL (optional)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    days: int = typer.Option(3, help="Number of days to include in the episode"),
    narrative: bool = typer.Option(
        False,
        "--narrative",
        help="Print day-level narrative snippets in addition to numeric stats.",
    ),
    recap: bool = typer.Option(
        False,
        "--recap",
        help="Print an episode-level recap and per-agent spotlights.",
    ),
    daily_log: bool = typer.Option(
        False,
        "--daily-log",
        help="Print compact daily narrative logs (intro, agent beats, general beats, closing).",
    ),
    psych_board: bool = typer.Option(
        False,
        "--psych-board",
        help="Print compact episode-level Psychology Board (per-agent, per-day codes).",
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Use the latest episode from the run registry (no RUN_ID/EPISODE_ID needed).",
    ),
) -> None:
    """Summarize a multi-day Loopforge episode from JSONL logs.

    Explicit mode:
        loopforge-sim view-episode RUN_ID EPISODE_ID [--recap] [--narrative]

    Latest mode:
        loopforge-sim view-episode --latest [--recap] [--narrative]
    """
    import typer as _typer

    # Resolve IDs based on --latest flag
    if latest:
        # Disallow mixing explicit IDs with --latest to avoid confusing precedence.
        # When invoked via CLI (Click context present), raise a BadParameter to inform the user.
        # When invoked programmatically (no Click context), be permissive and ignore provided IDs.
        if run_id is not None or episode_id is not None:
            try:
                import click as _click
                ctx = _click.get_current_context(silent=True)
            except Exception:
                ctx = None
            if ctx is not None:
                raise _typer.BadParameter(
                    "Do not provide RUN_ID/EPISODE_ID when using --latest.\n"
                    "Use either: loopforge-sim view-episode RUN_ID EPISODE_ID [OPTIONS]\n"
                    "   or:       loopforge-sim view-episode --latest [OPTIONS]"
                )
            # Programmatic usage: ignore explicit IDs and proceed with latest
            run_id = None
            episode_id = None
        from loopforge import run_registry as _rr
        # Respect test monkeypatch of loopforge.run_registry.registry_path by deriving base_dir
        base_dir = None
        try:
            _reg_path = _rr.registry_path()
            base_dir = _reg_path.parent if _reg_path is not None else None
        except Exception:
            base_dir = None
        record = _rr.latest_episode_record(base_dir=base_dir)
        if record is None:
            _typer.echo("No episodes found in the registry yet.", err=True)
            raise _typer.Exit(code=1)
        run_id = record.run_id
        episode_id = record.episode_id
        # Optionally honor recorded steps_per_day/days if user didn't override
        try:
            if isinstance(getattr(record, "steps_per_day", None), int) and steps_per_day == 50:
                steps_per_day = int(record.steps_per_day)
            if isinstance(getattr(record, "days", None), int) and days == 3:
                days = int(record.days)
        except Exception:
            pass
    else:
        # Explicit mode: allow missing IDs when invoked programmatically.
        # Historical behavior generated IDs later in the function when absent.
        # We keep CLI UX via Typer (help text) but avoid raising here so tests that
        # call view_episode(...) directly without IDs still pass (IDs will be generated
        # in the identity fallback below).
        pass

    # Preload supervisor entries (fail-soft) and group by day
    supervisor_entries_by_day: Dict[int, list[dict]] = {}
    try:
        if supervisor_log_path is not None:
            import json as _json
            p = Path(supervisor_log_path)
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = _json.loads(line)
                        except Exception:
                            continue
                        # SupervisorMessage JSON has day_index; fall back to step//steps_per_day if present
                        day_idx = obj.get("day_index")
                        if not isinstance(day_idx, int):
                            step_val = obj.get("step")
                            try:
                                day_idx = int(step_val) // int(steps_per_day) if step_val is not None else 0
                            except Exception:
                                day_idx = 0
                        supervisor_entries_by_day.setdefault(int(day_idx), []).append(obj)
    except Exception:
        supervisor_entries_by_day = {}

    # Compute day summaries using the shared compute path
    day_summaries: list[DaySummary] = []
    prev_stats: Optional[Dict[str, AgentDayStats]] = None
    for day_index in range(days):
        sup_entries_for_day = supervisor_entries_by_day.get(day_index, [])
        sup_activity = compute_supervisor_activity(sup_entries_for_day, steps_per_day=steps_per_day)
        ds = compute_day_summary(
            day_index=day_index,
            action_log_path=action_log_path,
            steps_per_day=steps_per_day,
            previous_day_stats=prev_stats,
            supervisor_activity=sup_activity,
        )
        day_summaries.append(ds)
        prev_stats = ds.agent_stats

    # Identity for this episode summary: prefer resolved IDs when available
    if run_id is None or episode_id is None:
        try:
            from loopforge.core.ids import generate_run_id, generate_episode_id
            run_id = generate_run_id()
            episode_index = 0
            episode_id = generate_episode_id(run_id, episode_index)
        except Exception:
            run_id = "run-unknown"
            episode_index = 0
            try:
                import time as _time
                episode_id = f"ep-{int(_time.time())}"
            except Exception:
                episode_id = "ep-unknown"
    else:
        # Keep episode_index at 0 unless a registry record was used
        episode_index = 0

    episode = summarize_episode(day_summaries, episode_id=episode_id, run_id=run_id, episode_index=episode_index)

    # Append episode metadata to the append-only Run & Episode Registry (fail-soft)
    try:
        from loopforge.run_registry import EpisodeRecord, append_episode_record, utc_now_iso
        record = EpisodeRecord(
            run_id=str(getattr(episode, "run_id", run_id) or run_id),
            episode_id=str(getattr(episode, "episode_id", episode_id) or episode_id),
            episode_index=int(getattr(episode, "episode_index", episode_index) or 0),
            created_at=utc_now_iso(),
            steps_per_day=int(steps_per_day),
            days=int(days),
        )
        append_episode_record(record)
    except Exception:
        # Registry must not affect CLI behavior
        pass

    # Psychology Board: render only this view when requested, then exit
    if psych_board:
        try:
            from loopforge.psych_board import build_psych_board
        except Exception:
            build_psych_board = None  # type: ignore
        if build_psych_board is not None:
            lines = []
            try:
                lines = build_psych_board(episode)
            except Exception:
                lines = []
            for line in lines:
                typer.echo(line)
        return

    _print_episode_summary(episode)

    if recap:
        _print_episode_recap(episode)

    if narrative:
        from loopforge.narrative_viewer import build_day_narrative
        typer.echo("\nDAY NARRATIVES")
        typer.echo("==============================")
        for idx, day in enumerate(episode.days):
            prev = episode.days[idx - 1] if idx > 0 else None
            dn = build_day_narrative(day, idx, previous_day_summary=prev)
            _print_day_narrative(dn)

    if daily_log:
        try:
            from loopforge.daily_logs import build_daily_log
        except Exception:
            build_daily_log = None
        if build_daily_log is not None:
            # Lazy import to avoid circulars at module import time
            try:
                from loopforge.daily_logs import build_psych_snapshot_block
            except Exception:
                build_psych_snapshot_block = None  # type: ignore
            typer.echo("\nDAILY LOG")
            typer.echo("----------")
            for idx, day in enumerate(episode.days):
                prev = episode.days[idx - 1] if idx > 0 else None
                log = build_daily_log(day, idx, previous_day_summary=prev)
                # Render
                typer.echo(f"\nDay {log.day_index}")
                typer.echo(f"{log.intro}")
                # Agent sections in deterministic order
                for agent_name in sorted(log.agent_beats.keys()):
                    typer.echo(f"[{agent_name}]")
                    for line in log.agent_beats[agent_name]:
                        typer.echo(f"- {line}")
                if log.general_beats:
                    typer.echo("General:")
                    for line in log.general_beats:
                        typer.echo(f"- {line}")
                # Psychology Snapshot block (debug view)
                if build_psych_snapshot_block is not None:
                    try:
                        lines = build_psych_snapshot_block(day)
                    except Exception:
                        lines = []
                    if lines:
                        typer.echo("\nPsychology Snapshot:")
                        for line in lines:
                            typer.echo(f"  {line}")
                if log.closing:
                    typer.echo(log.closing)


def _print_episode_summary(episode: EpisodeSummary) -> None:
    # Per-day blocks
    for d in episode.days:
        typer.echo(f"DAY {d.day_index} — perception={d.perception_mode}  tension={d.tension_score:.2f}")
        # Align agent names to improve readability
        if not d.agent_stats:
            typer.echo("  (no agent entries)")
            continue
        width = max(len(n) for n in d.agent_stats.keys())
        for name in sorted(d.agent_stats.keys()):
            s = d.agent_stats[name]
            typer.echo(
                f"  {name.ljust(width)}: guardrail={s.guardrail_count}, context={s.context_count}, avg_stress={s.avg_stress:.2f}"
            )
        typer.echo("")

    # Episode-level aggregates
    typer.echo("EPISODE SUMMARY")
    typer.echo("=" * 30)
    # Character sheets per agent
    typer.echo("\n=== CHARACTER SHEETS ===\n")
    # Determine width for agent names
    if episode.agents:
        width = max(len(n) for n in episode.agents.keys())
    else:
        width = 0
    for name in sorted(episode.agents.keys()):
        a = episode.agents[name]
        # Header
        typer.echo(f"{name}")
        typer.echo("-" * len(name))
        # Role + vibe
        if getattr(a, "vibe", ""):
            typer.echo(f"Role: {a.role} — {a.vibe}")
        else:
            typer.echo(f"Role: {a.role}")
        # Visual
        if getattr(a, "visual", ""):
            typer.echo(f"Visual: {a.visual}")
        # Tagline
        if getattr(a, "tagline", ""):
            typer.echo(f"Tagline: “{a.tagline}”")
        # Guardrail/context totals
        typer.echo(f"Guardrail vs context (episode): {a.guardrail_total} / {a.context_total}")
        # Stress arc
        if a.stress_start is not None and a.stress_end is not None:
            trend = "rising" if a.stress_end > a.stress_start else ("falling" if a.stress_end < a.stress_start else "flat")
            typer.echo(f"Stress arc: {a.stress_start:.2f} → {a.stress_end:.2f} ({trend})")
        else:
            typer.echo("Stress arc: n/a")
        # Traits placeholder/deltas
        if a.trait_deltas:
            deltas = ", ".join(f"{k}: {v:+.2f}" for k, v in a.trait_deltas.items())
            typer.echo(f"Traits: {deltas}")
        else:
            typer.echo("Traits: (deltas not tracked)")
        # Reflection quote snippet (first line)
        if a.representative_reflection and getattr(a.representative_reflection, "summary_of_day", ""):
            quote_full = a.representative_reflection.summary_of_day.strip()
            quote_one_line = quote_full.split("\n")[0]
            typer.echo(f"Reflection: “{quote_one_line}”")
        typer.echo("")

    # Tension trend and simple canaries
    trend_str = ", ".join(f"{v:.2f}" for v in episode.tension_trend)
    typer.echo(f"Tension trend: [{trend_str}]")

    # Oscillation detection: strictly increasing trend across days
    def _strictly_increasing(xs: list[float]) -> bool:
        return all(b > a for a, b in zip(xs, xs[1:])) if len(xs) >= 2 else False

    if _strictly_increasing(episode.tension_trend) and len(episode.tension_trend) >= 3:
        typer.echo("⚠ Tension increased every day this episode. Check for runaway feedback loops.")

    # Heavy guardrail skew warnings
    for name, a in episode.agents.items():
        total = a.guardrail_total + a.context_total
        if total >= 5 and a.guardrail_total >= 0.8 * total:
            typer.echo(f"⚠ {name} relied heavily on guardrails this episode ({a.guardrail_total} / {a.context_total}).")


@app.command("explain-episode")
def explain_episode(
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    days: int = typer.Option(3, help="Number of days to include in the episode"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name to explain"),
) -> None:
    """Explain one agent's episode using deterministic, rule-based templates."""
    # Compute day summaries via the shared path
    day_summaries = []
    for day_index in range(days):
        ds = compute_day_summary(
            day_index=day_index,
            action_log_path=action_log_path,
            steps_per_day=steps_per_day,
        )
        day_summaries.append(ds)

    episode = summarize_episode(day_summaries)

    # Build contexts and explanation text
    try:
        from loopforge.characters import CHARACTERS
        from loopforge.explainer_context import build_episode_context, build_agent_focus_context
        from loopforge.explainer import explain_agent_episode
    except Exception as e:
        typer.echo(f"Explainer modules not available: {e}")
        raise typer.Exit(code=1)

    episode_ctx = build_episode_context(episode, episode.days, CHARACTERS)
    agent_ctx = build_agent_focus_context(episode, episode.days, CHARACTERS, agent)
    text = explain_agent_episode(agent_ctx)

    typer.echo("EPISODE EXPLAINER")
    typer.echo("==================")
    typer.echo(f"Agent: {agent}")
    typer.echo("")
    typer.echo(text)


@app.command()
def export_episode(
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    supervisor_log_path: Path | None = typer.Option(None, help="Path to supervisor JSONL (optional)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    days: int = typer.Option(3, help="Number of days to include in the episode"),
    output: Path = typer.Option(Path("logs/episode_export.json"), help="Where to write JSON export"),
) -> None:
    """Export a JSON summary of an episode (read-only analysis path).

    Uses the same computation as view-episode but writes a JSON file instead of
    printing, including derived blame timelines/counts per agent.
    """
    try:
        episode = analyze_episode(
            action_log_path=action_log_path,
            supervisor_log_path=supervisor_log_path,
            steps_per_day=steps_per_day,
            days=days,
        )
        data = episode_summary_to_dict(episode)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        typer.echo(f"Wrote episode export to {output}")
    except Exception as e:
        typer.echo(f"Failed to export episode: {e}")
        raise typer.Exit(code=1)


@app.command("lens-agent")
def lens_agent(
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    day_index: int = typer.Option(0, help="Day index to summarize (0-based)"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name to build lens for"),
) -> None:
    """Build and print the LLM perception lens input + fake output for a single agent (read-only)."""
    # Build the DaySummary for the selected day
    ds = compute_day_summary(
        day_index=day_index,
        action_log_path=action_log_path,
        steps_per_day=steps_per_day,
    )

    try:
        from loopforge.llm_lens import build_llm_perception_lens_input, fake_llm_perception_lens
    except Exception as e:
        typer.echo(f"LLM lens module not available: {e}")
        raise typer.Exit(code=1)

    lens_in = build_llm_perception_lens_input(ds, agent)
    if lens_in is None:
        typer.echo(f"No stats found for agent '{agent}' on day {day_index}.")
        raise typer.Exit(code=0)

    lens_out = fake_llm_perception_lens(lens_in)

    # Pretty-print (small JSON-ish block)
    import json as _json
    typer.echo("LLM PERCEPTION LENS (input)")
    typer.echo("-----------------------------")
    typer.echo(_json.dumps({
        "agent_name": lens_in.agent_name,
        "role": lens_in.role,
        "day_index": lens_in.day_index,
        "perception_mode": lens_in.perception_mode,
        "avg_stress": lens_in.avg_stress,
        "guardrail_count": lens_in.guardrail_count,
        "context_count": lens_in.context_count,
        "tension": lens_in.tension,
        "supervisor_tone_hint": lens_in.supervisor_tone_hint,
    }, indent=2))

    typer.echo("")
    typer.echo("LLM PERCEPTION LENS (fake output)")
    typer.echo("----------------------------------")
    typer.echo(_json.dumps({
        "emotional_read": lens_out.emotional_read,
        "risk_assessment": lens_out.risk_assessment,
        "suggested_focus": lens_out.suggested_focus,
        "supervisor_comment_prompt": lens_out.supervisor_comment_prompt,
    }, indent=2))


@app.command("list-runs")
def list_runs(
    limit: int = typer.Option(20, help="Max number of records to show (most recent last)."),
    registry_base: Path | None = None,
) -> None:
    """List recent run/episode history from the append-only registry.

    - Prints a simple, grep-friendly summary oldest → newest, truncated by `limit`.
    - When `registry_base` is provided (tests), the registry file is resolved under that directory.
    """
    try:
        from loopforge.run_registry import load_registry
    except Exception as e:
        typer.echo(f"Registry unavailable: {e}")
        raise typer.Exit(code=1)

    try:
        records = load_registry(base_dir=registry_base)
    except Exception:
        records = []

    # Take the tail of the list to show most recent records while preserving order
    if isinstance(limit, int) and limit > 0:
        records = records[-limit:]

    typer.echo("RUN HISTORY")
    typer.echo("===========")
    if not records:
        typer.echo("(no records)")
        return

    for r in records:
        # Keep formatting compact and stable
        created = getattr(r, "created_at", "")
        line = (
            f"run_id={r.run_id}  episode_id={r.episode_id}  idx={int(getattr(r, 'episode_index', 0) or 0)}  "
            f"days={int(getattr(r, 'days', 0) or 0)}  steps_per_day={int(getattr(r, 'steps_per_day', 0) or 0)}  "
            f"created_at={created}"
        )
        typer.echo(line)


@app.command("replay-episode")
def replay_episode(
    run_id: str | None = typer.Option(None, "--run-id", help="Run ID to replay (ignored if --latest)."),
    episode_index: int = typer.Option(0, "--episode-index", help="Episode index within the run."),
    latest: bool = typer.Option(False, "--latest", help="Replay the latest recorded episode."),
    recap: bool = typer.Option(False, "--recap", help="Print an episode-level recap."),
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    supervisor_log_path: Path | None = typer.Option(None, help="Path to supervisor JSONL (optional)"),
    registry_base: Path | None = None,
) -> None:
    """Replay a recorded episode from the registry without running the sim.

    - Selects an EpisodeRecord via --latest or (--run-id, --episode-index).
    - Loads action/supervisor logs and analyzes strictly by (run_id, episode_id).
    - Prints a recap when --recap is supplied; otherwise prints numeric summary.
    """
    try:
        from loopforge.run_registry import latest_episode_record, find_episode_record
    except Exception as e:
        typer.echo(f"Registry unavailable: {e}")
        raise typer.Exit(code=1)

    record = None
    if latest:
        record = latest_episode_record(base_dir=registry_base)
        if record is None:
            typer.echo("No records found in registry.")
            raise typer.Exit(code=1)
    else:
        if not run_id:
            typer.echo("Missing required --run-id (or use --latest).")
            raise typer.Exit(code=1)
        record = find_episode_record(run_id, episode_index=episode_index, base_dir=registry_base)
        if record is None:
            typer.echo(f"No registry entry found for run_id={run_id} episode_index={episode_index}.")
            raise typer.Exit(code=1)

    # Analyze using the adapter (strict ID rules inside)
    try:
        episode = analyze_episode_from_record(
            record,
            action_log_path=action_log_path,
            supervisor_log_path=supervisor_log_path,
        )
    except Exception as e:
        typer.echo(f"Failed to analyze episode: {e}")
        raise typer.Exit(code=1)

    # Print summary and optional recap to mirror view-episode
    _print_episode_summary(episode)
    if recap:
        _print_episode_recap(episode)


if __name__ == "__main__":
    app()



def _print_day_narrative(dn):
    """Pretty-print a DayNarrative produced by narrative_viewer."""
    try:
        import typer as _ty
    except Exception:  # fail-soft; fallback to print
        _ty = None

    def _echo(s: str):
        if _ty is not None:
            _ty.echo(s)
        else:
            print(s)

    _echo(f"\nDay {dn.day_index} — {dn.day_intro}")
    for beat in dn.agent_beats:
        _echo(f"  [{beat.name} ({beat.role})]")
        _echo(f"    {beat.intro}")
        _echo(f"    {beat.perception_line}")
        _echo(f"    {beat.actions_line}")
        _echo(f"    {beat.closing_line}")
    if dn.supervisor_line:
        _echo(f"  Supervisor: {dn.supervisor_line}")
    if dn.day_outro:
        _echo(f"  {dn.day_outro}")
