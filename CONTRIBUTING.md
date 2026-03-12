# Contributing

## Scope

This repository is Enqueteur-first.

- Keep runtime and transport deterministic.
- Keep simulation primitives generic and case-agnostic when possible.
- Keep MBAM-specific logic/content in explicit case modules.

## Development

Canonical local topology:

- Python ASGI backend host on `127.0.0.1:7777`
- Frontend Vite dev server on `127.0.0.1:5173`

Start local live playtest:

```bash
make server-dev
make web-dev-local
```

Backend test suite:

```bash
make test
```

For frontend:

```bash
cd frontend/enqueteur-webview
npm install
npm test
```

Local playtest runbook: [docs/enqueteur/local_playtest_workflow.md](docs/enqueteur/local_playtest_workflow.md)

## Guardrails

- Do not reintroduce Loopforge domain terms or fiction into core runtime modules.
- Avoid adding non-deterministic behavior to runtime tick/state pipelines.
- Preserve replay and diff/snapshot compatibility unless a versioned schema change is explicitly made.
