from pathlib import Path

from loopforge.day_runner import compute_day_summary

ds0 = compute_day_summary(
    day_index=0,
    action_log_path=Path("logs/loopforge_actions.jsonl"),
    steps_per_day=20,
    supervisor_activity=0.0,
)

ds1 = compute_day_summary(
    day_index=0,
    action_log_path=Path("logs/loopforge_actions.jsonl"),
    steps_per_day=20,
    supervisor_activity=0.9,
    previous_day_stats=None,
)

print("Day 0 agent_stats keys:", list(ds0.agent_stats.keys()))
print("Day 0 reflection_states (no supervisor):")
for name, rs in ds0.reflection_states.items():
    print(" ", name, "supervisor_presence=", rs.supervisor_presence)

print("\nDay 0 agent_stats keys (heavy supervisor):", list(ds1.agent_stats.keys()))
print("Day 0 reflection_states (heavy supervisor):")
for name, rs in ds1.reflection_states.items():
    print(" ", name, "supervisor_presence=", rs.supervisor_presence)
