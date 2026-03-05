### UI-Stage — Current Test Failures Report (Vitest)

Date: 2025-11-27 08:17 local

Scope: Frontend only (ui-stage). This is a diagnostic report only — no production code changes were made as per the request.

Commands executed
- npm --prefix ui-stage test --silent
- npm --prefix ui-stage test --silent -- src/AppRouter.test.tsx
- npm --prefix ui-stage exec vitest run --reporter=basic --no-color src/AppRouter.test.tsx

Environment notes
- jsdom test environment
- Vitest v2.x

High-level summary
- Test files: 53 total
- Tests: 178 total
- Passed: 52 files, 173 tests
- Failed: 1 file, 5 tests (all in AppRouter.test.tsx)
- Notable console noise: React Router future-flag warnings (informational), occasional “tasks still running after test environment was torn down” from route-mounting tests

Failing spec file
- File: ui-stage/src/AppRouter.test.tsx
- Suites affected: “AppRouter routes — nav highlighting …”

Failing tests (by name)
1) nav highlighting — Stage active at root /
2) nav highlighting — Stage active on /episodes/:id/stage
3) nav highlighting — Details active on /episodes/:id
4) nav highlighting — Details active on /episodes/latest
5) nav highlighting — Episodes active only on /episodes index

Observed error patterns
- Timeouts while waiting for expected aria-current states on the main nav links inside waitFor blocks:
  - Example symptom: Timed out in waitFor(() => expect(stageLink).toHaveAttribute("aria-current", "page"))
- In some runs, an additional teardown-time message: “This error was caught after test environment was torn down. Make sure to cancel any running tasks before test finishes.”

Context (why these tests are sensitive)
- AppRouter test mounts the real AppShell plus route components. StageView/LatestEpisodeView trigger async episode loading via useEpisodeLoader. This can cause multiple renders and microtasks during initial mount.
- The nav highlighting logic in AppShell is synchronous, but route components may still be mounting/unmounting as the tests assert, which can lead to transient states.

What is already implemented in tests
- The nav-highlighting assertions use waitFor and jest-dom matchers (toHaveAttribute / not.toHaveAttribute) instead of immediate attribute reads.
- Tests await the presence of the main navigation region (role="navigation", name=/Main navigation/i) before asserting.
- A microtask tick (await Promise.resolve()) is introduced before waitFor in nav tests to reduce races.

Why failures still occur
- Despite the above, the expected aria-current may not stabilize within the default or extended waitFor timeout on this environment. Root causes likely include:
  - Concurrent async mounts from route components producing additional re-renders while assertions run.
  - Occasional pending timers/microtasks from child components that extend mount time (e.g., storyboard/timeline interactions setTimeout in other views, though not directly interacted with here).

Non-failing areas (sanity)
- TimelineStrip tests: pass and no React key warnings are observed after recent fixes.
- DayStoryboard tests: pass and there are no invalid nested <button> warnings in the logs.
- Other route/component suites: pass consistently.

Recommendations (documentation only; no code changes applied in this report)
- If allowed in a follow-up, consider one of these minimal options to fully stabilize these five nav tests without altering production code:
  - Mock getLatestEpisode to resolve immediately in nav-only tests to eliminate loader-induced re-renders.
  - Alternatively, mock child routes to inert placeholders for nav-only tests so only AppShell + router render.
  - If teardown warnings persist, use vi.useFakeTimers()/vi.runAllTimers()/vi.useRealTimers() in afterEach of the affected test file to flush any incidental timers.

Appendix: Sample run snapshots
- Full suite run: 53 files, 178 tests → 52 files passed, 1 file failed; 173 tests passed, 5 failed; failures all in AppRouter.test.tsx (nav highlighting set).
- Focused run: src/AppRouter.test.tsx → 13 tests total; 8 passed, 5 failed; failing tests are the nav-highlighting set listed above.

— Junie
