# Contributing to Loopforge City

Thanks for contributing! This project uses Conventional Commits and lightweight tooling to keep history clean and automatable.

## Commit messages

Follow the Conventional Commits spec:
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Optional scope: `feat(simulation)`, `build(docker)`, `db(alembic)`, `chore(make)`
- Subject: imperative mood, lower case, no trailing period

Example:
```
feat(simulation): add basic error event on every 7th step

Include context in the body when helpful.
```

## Local environment

- Install dependencies (including dev tools):
  ```bash
  make uv-sync
  ```
- Use the commit template:
  ```bash
  git config commit.template .gitmessage
  ```
- Install the commit-msg hook (checks message format):
  ```bash
  make hooks-install
  ```
- Optional helper commands:
  ```bash
  make cz-commit   # interactive commit prompt (Commitizen)
  make cz-check    # check format for the last commit
  make cz-bump     # bump version and tag (uses Commitizen config)
  ```

## Running the app and migrations

- Local quick test (no DB):
  ```bash
  make uv-sync
  make run  # runs in-memory, prints step summaries
  ```
- Containerized app + db (recommended):
  ```bash
  make docker-up
  make docker-logs  # Ctrl+C to exit logs; containers keep running
  ```
  Migrations run automatically inside the app container before the simulation.
- If you intentionally manage a local Postgres for development, you can run Alembic manually:
  ```bash
  uv run alembic upgrade head
  ```
  But typical development should avoid a local Postgres; prefer the containerized flow above.

## Housekeeping

- Local virtual environments and caches are ignored via `.gitignore`.
- If `loopforge_city.egg-info/` was accidentally committed previously, run:
  ```bash
  make untrack-egg
  ```

## Code style

- Keep code idiomatic and consistent with the surrounding module.
- Prefer small, focused commits with clear messages.


## 🎭 Producer Rules of Development

These rules define the creative intent of Loopforge. Every technical contribution must follow them.

1. If it doesn’t help story or insight, cut it.
2. Every infra sprint must be followed by a visible output sprint.
3. No black boxes — every system must be narratable.
4. Keep the Perception → Policy → Plan seam holy.
5. Make it fun to watch — boring episodes are bugs.

Full vision: docs/PRODUCER_VISION.md

## Investigation and Incident Reports (Required for bug work)

When investigating failing tests, bugs, or regressions, write a detailed report and attach/link it in the PR description. Use the template at:

- docs/dev_reporting.md

At minimum, your report must include:
- Executive summary: 3–5 bullet points of what failed and why.
- Test/Environment matrix: OS, Python/Node versions, dependency pins, DB URL used.
- Reproduction steps: exact commands and any required env vars.
- Failure surface: which tests/files fail, stack traces (trimmed to signal), and scope of impact.
- Root cause analysis: primary cause, secondary factors, and how you validated this.
- Proposed fix options: minimal change first, tradeoffs, and why chosen.
- Backward-compatibility and stability analysis: API, schema, logs, and The Seam.
- Verification plan: tests to run, manual checks, and expected outputs.
- Risks and rollbacks: known risks, mitigations, and a simple rollback plan.

PRs that change backend or frontend behavior without an accompanying detailed report may be held for revision.
