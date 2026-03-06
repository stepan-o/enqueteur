# Contributing

## Scope

This repository is Enqueteur-first.

- Keep runtime and transport deterministic.
- Keep simulation primitives generic and case-agnostic when possible.
- Keep MBAM-specific logic/content in explicit case modules.

## Development

```bash
python -m pytest backend/sim4/tests -q
```

For frontend:

```bash
cd frontend/enqueteur-webview
npm install
npm run dev
```

## Guardrails

- Do not reintroduce Loopforge domain terms or fiction into core runtime modules.
- Avoid adding non-deterministic behavior to runtime tick/state pipelines.
- Preserve replay and diff/snapshot compatibility unless a versioned schema change is explicitly made.
