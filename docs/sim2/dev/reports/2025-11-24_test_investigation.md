Developer Investigation & Incident Report — Frontend Vitest Failures
===================================================================

1) Executive Summary
- What failed: Two Vitest tests in ui-stage for EpisodeStoryPanel were failing due to ambiguous text queries matching multiple elements.
- Scope of impact: Frontend test suite only; backend pytest was fully passing. No runtime app breakage.
- Root cause (brief): Tests queried by generic text that collided with other rendered nodes (empty state and pretty-printed JSON in <pre>), and DOM from a prior test wasn’t explicitly cleaned, causing multiple matches.
- Chosen fix: Adjust test queries to be more specific (role-based for heading, getAllByText where ambiguity is expected) and add cleanup() afterEach to isolate DOM between tests.
- Verification outcome: All frontend tests now pass (22 files, 58 tests). Backend tests pass (100%).

2) Environment Matrix
- OS: macOS 14 (Apple Silicon)
- Node: v24.11.1, npm bundled with Node 24
- Python: 3.11.x (per project), pytest runner via uv/pip
- Database URL during backend tests: sqlite+pysqlite:///loopforge_test.db (configured by tests/conftest.py per docs)
- Extra services: none

3) Reproduction Steps

    # Backend
    pytest -q

    # Frontend
    cd ui-stage
    npm test

4) Failure Surface
- Failing tests/modules:
  - ui-stage/src/components/EpisodeStoryPanel.test.tsx
    - “renders JSON for story arc when present”
    - “renders narrative blocks when present”
- Error types and key messages:
  - TestingLibraryElementError: Found multiple elements with the text: /Story Arc/i
  - TestingLibraryElementError: Found multiple elements with the text: /beat/i
- Phase: Test execution (not import/collection). Rendering created multiple matching nodes: empty-state text and <h3> heading for “Story Arc”; JSON in <pre> also contained the word “beat”.
- Nondeterminism: None observed; failures were consistent.

5) Root Cause Analysis
- Primary cause: Overly broad text queries (getByText(/Story Arc/i), getByText(/beat/i)) matched multiple elements due to legitimate duplicates in the DOM (empty-state message and pretty-printed JSON in <pre>), causing Testing Library to throw on ambiguity.
- Contributing factors: Lack of explicit cleanup between tests led to parallel renders in the JSDOM document during the same test file, increasing match counts.
- Why now: New EpisodeStoryPanel introduced additional UI text and <pre> JSON rendering; tests were added with generic queries.
- Validation: Inspecting Vitest’s DOM dump in the failure logs showed two sections present simultaneously and JSON containing “beat”. Targeted queries resolved the ambiguity.

6) Proposed Fix Options
1) Test-only adjustments (minimal):
   - Use role-based queries for headings (getByRole('heading', { name: /Story Arc/i })).
   - Use getAllByText for terms expected to appear multiple times or narrow the selector to a specific container.
   - Add afterEach(cleanup) to ensure isolated DOM between tests.
   Pros: No product behavior changes. Aligns with Testing Library best practices.
   Cons: None significant.
   Risk: Low.
   B/C notes: No runtime API or UI changes.
   Blast radius: Limited to tests for EpisodeStoryPanel.
2) Component change:
   - Alter empty-state rendering to not include words that collide with headings, or avoid pretty-printing JSON that includes common words.
   Pros: Might simplify tests.
   Cons: Changes UI copy and intent; unnecessary.
   Risk: Medium (UI text regressions).

Chosen: Option 1 (test-only adjustments) to preserve UI and minimize risk.

7) Verification Plan
- Re-run frontend suite: npm test (all tests in ui-stage).
- Re-run backend suite: pytest -q.
- Confirm no UI snapshots require updates beyond existing episode VM snapshot.

8) Risks, Mitigations, and Rollback
- Risks: Minimal; only test queries changed. If brittleness persists, we can scope queries to container nodes.
- Mitigations: Role-based queries and DOM cleanup reduce ambiguity.
- Rollback: Revert changes to EpisodeStoryPanel.test.tsx.

9) Follow-ups (Non-blocking)
- Consider using screen.within(container) to scope queries to specific sections when testing components that render multiple <section> siblings in the same test file.
- Add a lint rule or testing guideline to prefer role-based queries for headings and labels.

10) Implemented Fix & Current State — 2025-11-24 17:51
- Implemented fix:
  - Updated ui-stage/src/components/EpisodeStoryPanel.test.tsx
    • Added afterEach(cleanup)
    • Switched to getByRole for the Story Arc heading
    • Used getAllByText for ambiguous tokens like “beat”
- Current state:
  - Backend: pytest -q → all tests pass.
  - Frontend: npm test → 22 files, 58 tests passing.
  - Stability: No runtime code changes; tests only.
