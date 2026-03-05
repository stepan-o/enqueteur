# SIM4 — Sprint 12 Risk Pre-Mortem: Deterministic Layout (S12.2)
_Date: 2025-12-18_  
_Owner: Architecture_  
_Scope: Sprint 12.2 deterministic room placement for viewer render specs._

## Purpose
Sprint 12.2 introduces a **deterministic** room layout algorithm used at the **export boundary** (integration layer). This doc lists the failure modes that commonly break determinism, stability, or viewer usefulness, plus concrete guardrails and tests to prevent regressions.

---

## What “success” means (non-negotiable)
A layout algorithm is **deterministic** if, given the same input identities/topology:
- It produces the **same coordinates** across runs/machines/Python versions.
- It is independent of runtime tick timing and independent of non-export state.
- It is stable under changes that should not matter (e.g., adding an unrelated room far away should not reorder existing placements unless topology requires it).
- All exported floats are quantized consistently (one policy, everywhere).

---

## The usual ways deterministic layout fails

### 1) Hidden nondeterminism from data structures
**Symptom:** coordinates differ across runs; room order “shifts” randomly.  
**Root causes:**
- Iterating over `dict` / `set` / `defaultdict` without explicit sorting.
- Graph neighbors retrieved from a set; traversal order changes.
- JSON decode order assumptions (or depending on insertion order from upstream).
  **Guardrails:**
- Always sort room IDs, edge lists, neighbor lists.
- Canonical iteration order = `(room_id asc)` and for edges `(min(a,b), max(a,b))`.
  **Tests:**
- Run layout twice in same test process with randomized insertion order; assert identical output.
- Build graph inputs using shuffled insertion; assert identical output.

---

### 2) Floating point chaos (and “almost deterministic”)
**Symptom:** outputs differ at ~1e-12, viewer diffs churn, replay diffs bloat.  
**Root causes:**
- Accumulating floats across iterative solvers (spring layout, force-directed).
- Using trig / sqrt repeatedly across thousands of steps.
- Cross-platform float differences (BLAS, CPU, Python minor versions).
  **Guardrails:**
- Prefer integer/grid layouts for MVP; avoid iterative solvers.
- If any float math is required: quantize at each step, not just at the end.
- Use `integration.util.quantize` everywhere; never raw floats into TickFrame.
  **Tests:**
- Assert all exported floats are multiples of the quantization step.
- Snapshot test of layout output (rooms + coords) is byte-stable across reruns.

---

### 3) Graph layout algorithms are rarely deterministic by default
**Symptom:** “same graph, different layout,” especially after library upgrades.  
**Root causes:**
- Using external layout libs (networkx spring layout, graphviz) that depend on RNG or internal hash order.
- Default seeds not set, or seed derived from unstable hash.
  **Guardrails:**
- Avoid external layout libraries for MVP.
- If a graph-based placement is required:
    - Use a **deterministic traversal** (BFS/DFS) from a canonical root.
    - Use deterministic tie-breakers for neighbor order.
    - Use stable, explicit “root selection” rules.
      **Tests:**
- Layout should be identical even if node creation order is randomized.

---

### 4) Picking the “root room” inconsistently
**Symptom:** layout flips/rotates/reanchors between runs or after small changes.  
**Root causes:**
- Choosing root as “first” in dict.
- Choosing root based on degree ties without tie-break.
  **Guardrails:**
- Root selection must be canonical:
    - e.g., smallest `room_id` OR smallest `(degree desc, room_id asc)`—but always explicit.
      **Tests:**
- For graphs with degree ties, verify root chosen is stable and documented.

---

### 5) Layout flips, rotates, or mirrors unexpectedly
**Symptom:** same topology but mirrored layout across runs; viewer orientation changes.  
**Root causes:**
- Using centroid-based normalization with float jitter.
- Using PCA/eigenvectors (sign ambiguity) for orientation.
  **Guardrails:**
- Define a canonical orientation rule:
    - after placement, rotate/flip deterministically based on a landmark:
        - e.g., ensure the root’s highest-sorted neighbor lies in +X direction.
- Avoid PCA/eigen-based orientation for MVP.
  **Tests:**
- Assert orientation invariants: landmark neighbor has `x >= root.x` etc.

---

### 6) Layout instability under incremental changes
**Symptom:** adding one room causes the whole map to rearrange drastically.  
**Root causes:**
- Algorithms that “rebalance” globally.
- Sorting changes from new IDs if order influences placement.
  **Guardrails:**
- MVP: deterministic grid fallback based purely on sorted IDs is stable.
- Graph-based: place rooms by BFS layers; within a layer, order by room_id.
- Use consistent spacing; do not “compact” based on total node count.
  **Tests:**
- Add an isolated room; assert existing rooms keep same positions.

---

### 7) Disconnected graphs and “navgraph stub” edge cases
**Symptom:** rooms overlap, pile into one spot, or drift far apart.  
**Root causes:**
- Graph traversal only covers one connected component.
- Missing neighbors list treated as empty but not handled.
  **Guardrails:**
- Always handle multiple components:
    - Layout each component deterministically, then pack components in a deterministic strip/grid.
- If navgraph absent/stub:
    - Place by sorted room_id grid (documented).
      **Tests:**
- Graph with 3 components produces deterministic, non-overlapping placements.

---

### 8) Coordinate system mismatch with viewer expectations
**Symptom:** viewer places rooms “inside out,” wrong Z layering, wrong origin.  
**Root causes:**
- World_x/world_y assumed pixels vs tiles vs meters.
- Z layer semantics inconsistent.
  **Guardrails:**
- Document units: “viewer units” (VU) and stable tile size.
- Define origin: `(0,0)` at root room top-left (or center) — pick one and lock it.
- Z layer: deterministic integer (e.g., component index or BFS depth).
  **Tests:**
- Validation test that no two rooms overlap given width/height and spacing policy.

---

### 9) Diffs explode because layout changes every export
**Symptom:** scrubbing works but diff size huge; every frame “moves everything.”  
**Root causes:**
- Layout computed per tick from data that changes (occupancy, tension, etc.).
- Layout recomputed without caching stable topology result.
  **Guardrails:**
- Layout must be computed from **identity/topology only**, not per-tick state.
- Compute layout once per run export (or once per world_id) and reuse.
- If layout depends on topology that can change, define “topology versioning” rules.
  **Tests:**
- For a 100-tick run with constant topology, room positions must be identical across all TickFrames.

---

### 10) “Stable hash” mistakes
**Symptom:** seed or ordering differs between machines.  
**Root causes:**
- Using Python’s built-in `hash()` (salted per process).
- Using unstable serialization for seeding.
  **Guardrails:**
- Never use `hash()` for determinism.
- If any seeding is necessary, use `integration.util.stable_hash` and lock the exact canonical input string.
  **Tests:**
- Seed derived from stable_hash is stable across runs; unit test asserts known value.

---

## Recommended MVP algorithm (safe + boring + correct)
This is not the full spec—just the “least risky” approach for Sprint 12.2:

1) If navgraph exists:
- Choose canonical root (smallest room_id).
- BFS layers from root.
- Within each BFS depth, order rooms by room_id.
- Place each layer on a deterministic grid row (or diagonal strip for iso feel).
- Deterministic spacing constants: `room_w`, `room_h`, `gap_x`, `gap_y`.

2) If navgraph stub or missing:
- Place rooms in sorted room_id order on a grid:
    - columns = fixed constant (e.g., 6) OR derived deterministically from room count using integer math.
- No floating solvers.

3) Quantize coordinates immediately and always.

---

## Guardrail checklist (Sprint 12.2 must satisfy)
- [ ] All iteration is explicitly sorted.
- [ ] No use of Python `hash()`.
- [ ] No external layout library (unless locked with deterministic seed + stable order and proven).
- [ ] Layout depends only on identity/topology, not per-tick state.
- [ ] Handles disconnected graphs deterministically.
- [ ] Quantization enforced at every coordinate write.
- [ ] Orientation rule prevents flips/mirrors across runs.
- [ ] “Add isolated room” does not perturb existing placements.
- [ ] Tests cover shuffled insertion order + repeatability + quantization.

---

## Test plan (minimum set)
1) **Determinism under shuffled insertion**
- Build same graph with nodes/edges inserted in random order; assert identical output.

2) **Quantization enforcement**
- Assert `world_x/world_y` are quantized (multiples of epsilon).

3) **Disconnected components**
- Provide 2–3 components; assert deterministic component packing and no overlaps.

4) **Stability under unrelated addition**
- Add isolated node; assert prior nodes retain exact coordinates.

5) **Tick invariance**
- Export multiple TickFrames; assert room render specs identical across all frames for same run.

---

## “Stop the line” conditions
If any of these happen in Sprint 12.2, stop and fix before proceeding:
- Layout differs between consecutive test runs.
- Layout changes when only per-tick state changes (occupancy, emotion).
- Viewer diffs show “room moved” every tick with no topology change.
- Any use of unordered iteration in layout code.
- Any float output not passing quantization tests.