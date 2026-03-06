# Enqueteur

Enqueteur is a deterministic living-world investigation game runtime, now scoped to the MBAM Case 1 foundation.

## Active Repo Spine

- `backend/sim4`: deterministic simulation runtime, ECS substrate, world model, snapshots/diffs, KVP transport integration.
- `frontend/enqueteur-webview`: Pixi/webview live + offline viewer with debug controls, scrubber, inspector, and protocol client.
- `docs/enqueteur/case_1_implementation_spec.md`: locked MBAM implementation spec.
- `scripts/run_sim4_kvp_demo.py`: generates a deterministic offline run artifact bundle for viewer/debug workflows.

## Quick Start

### Backend tests

```bash
python -m pytest backend/sim4/tests -q
```

### Generate offline run artifacts

```bash
python scripts/run_sim4_kvp_demo.py --ticks 1800 --tick-rate 30 --agents 6
```

### Run webview

```bash
cd frontend/enqueteur-webview
npm install
npm run dev
```

Use the top-left controls in the viewer to switch between `Live` and `Offline` playback.

## Notes

- The repository has been cleaned of Loopforge domain/gameplay stacks and art assets.
- `sim4` naming is intentionally retained as the reusable runtime foundation.
- Future MBAM game logic should be layered on top of existing deterministic runtime and transport contracts.
