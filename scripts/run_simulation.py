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

from loopforge.simulation import run_simulation
from loopforge.config import get_settings
from loopforge.logging_utils import read_action_log_entries
from loopforge.day_runner import run_one_day_with_supervisor, compute_day_summary
from loopforge.reporting import summarize_episode, EpisodeSummary, AgentEpisodeStats, DaySummary
from loopforge.reporting import AgentDayStats
from loopforge.types import ActionLogEntry
from loopforge.supervisor_activity import compute_supervisor_activity
from loopforge.analysis_api import analyze_episode, episode_summary_to_dict
from pathlib import Path
from collections import Counter, defaultdict
from typing import Optional, Dict

app = typer.Typer(add_completion=False, help="Run the Loopforge City simulation loop")


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
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    reflection_log_path: Path | None = typer.Option(None, help="Where to write reflections JSONL (optional)"),
    supervisor_log_path: Path | None = typer.Option(None, help="Where to write supervisor JSONL (optional)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    day_index: int = typer.Option(0, help="Day index to summarize (0-based)"),
) -> None:
    """Summarize one day of Loopforge from JSONL logs.

    Reads action entries, builds a minimal env + agent stubs, runs the day runner
    with supervisor, and prints a compact report for devs.
    """
    entries: list[ActionLogEntry] = read_action_log_entries(action_log_path)
    if not entries:
        typer.echo(f"No action entries found at {action_log_path}")
        raise typer.Exit(code=0)

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
        day_index=day_index,
        action_log_path=action_log_path,
        reflection_log_path=reflection_log_path,
        supervisor_log_path=supervisor_log_path,
    )

    # Slice entries for this day for stats
    start = day_index * steps_per_day
    end = (day_index + 1) * steps_per_day
    day_entries = [e for e in entries if start <= e.step < end]

    # Prepare aggregates
    by_agent: dict[str, list[ActionLogEntry]] = defaultdict(list)
    for e in day_entries:
        by_agent[e.agent_name].append(e)

    typer.echo(f"Day {day_index} — Summary")
    typer.echo("=" * 25)
    typer.echo("")

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
        typer.echo(f"{name} ({role})")
        typer.echo(f"- Intents: {top3}")
        typer.echo(
            f"- Emotions: stress={_avg(stress_vals):.2f}, curiosity={_avg(curiosity_vals):.2f}, satisfaction={_avg(satisfaction_vals):.2f}"
        )
        # Best-effort reflection summary: take the last narrative for the agent on that day
        summary_line = None
        for e in reversed(rows):
            if e.narrative:
                summary_line = e.narrative
                break
        typer.echo(f"- Reflection: \"{summary_line or '—'}\"")
        typer.echo("")

    typer.echo("Supervisor")
    sup_intents = ", ".join(f"\"{m.intent}\"" for m in messages) or "(none)"
    typer.echo(f"- Messages: {sup_intents}")


@app.command()
def view_episode(
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
) -> None:
    """Summarize a multi-day Loopforge episode from JSONL logs."""
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

    episode = summarize_episode(day_summaries)

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
        try:
            from loopforge.episode_recaps import build_episode_recap
            from loopforge.characters import CHARACTERS
        except Exception:
            build_episode_recap = None
            CHARACTERS = {}
        if build_episode_recap is not None:
            recap_obj = build_episode_recap(episode, episode.days, CHARACTERS)
            typer.echo("\nEPISODE RECAP")
            typer.echo("=" * 30)
            typer.echo(recap_obj.intro)
            # Deterministic ordering of agents
            for name in sorted(recap_obj.per_agent_blurbs.keys()):
                typer.echo(f"- {name}: {recap_obj.per_agent_blurbs[name]}")
            typer.echo(recap_obj.closing)
            # Sprint 8: optional STORY ARC block
            if getattr(recap_obj, "story_arc_lines", None):
                typer.echo("\nSTORY ARC")
                typer.echo("-" * 30)
                for line in recap_obj.story_arc_lines:  # type: ignore[union-attr]
                    typer.echo(line)
            # Sprint 10: optional MEMORY DRIFT block
            if getattr(recap_obj, "memory_lines", None):
                typer.echo("\nMEMORY DRIFT")
                typer.echo("-" * 30)
                for line in recap_obj.memory_lines:  # type: ignore[union-attr]
                    typer.echo(line)

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
