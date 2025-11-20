# Director's monitor
## Quick usage cheatsheet
* `view-episode --latest --recap` = high-level beat sheet
* `view-day --latest` = day-level emotional telemetry view
```bash
# Reset local state - delete log files and SQLite databases
make reset-local
```

```bash
# Run a basic simulation
uv run python -m scripts.run_simulation --steps 10
```

```bash
# List everything
uv run loopforge-sim list-runs
```

```bash
# Latest episode (IDs auto)
uv run loopforge-sim view-episode --latest
```

```bash
# Latest episode (IDs auto)
uv run loopforge-sim view-episode --latest --recap
```

```bash
# Latest day (new from previous sprint)
uv run loopforge-sim view-day --latest        # day 0
```

```bash
# Latest day (new from previous sprint)
uv run loopforge-sim view-day --latest 1      # specific day, if exists
```

```bash
# Explicit targeting
uv run loopforge-sim view-episode RUN_ID EPISODE_ID
```

```bash
# Explicit targeting
uv run loopforge-sim view-day RUN_ID EPISODE_ID 0
```