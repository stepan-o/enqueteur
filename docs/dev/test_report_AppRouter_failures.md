### Investigation Report: AppRouter.test.tsx Failures (ui-stage)

Date: 2025-11-27 00:49 local

#### Scope
- No production code changes were made in this task.
- Focused on reproducing and characterizing current failures in ui-stage/src/AppRouter.test.tsx.
- Ran tests directly via Vitest (jsdom env), without using or relying on output.txt.

#### What I Ran
- npm --prefix ui-stage test --silent -- src/AppRouter.test.tsx
- Filtered reruns to probe specific suites:
  - npm --prefix ui-stage test --silent -t "nav highlighting — Stage active at root /" -- src/AppRouter.test.tsx
  - npm --prefix ui-stage test --silent -t "nav highlighting — Details active on /episodes/:id" -- src/AppRouter.test.tsx
  - npm --prefix ui-stage test --silent -t "Episodes active only on /episodes index" -- src/AppRouter.test.tsx

#### High-level Outcomes
- AppRouter.test.tsx consistently reports:
  - Test Files: 1 failed (the file itself)
  - Tests: 13 total with 5 failing and 8 passing (counts observed across runs)
  - Additionally, Vitest throws a teardown-time error: “This error was caught after test environment was torn down. Make sure to cancel any running tasks before test finishes”
- React Router v7 future flag warnings appear but are not test-failing; they are harmless noise.

#### Symptoms Observed
- Interleaved console logs from LatestEpisodeView during AppRouter tests (e.g., loader start, fetching…, [LatestEpisodeView] loading: heading rendered) indicate that routes rendering LatestEpisodeView are being mounted even in tests primarily targeting nav highlighting. This is expected because AppRouter contains those routes, but the logs confirm async activity during the nav tests.
- Failures include:
  - Nav highlighting assertions (aria-current="page") not matching expectations in some routes.
  - A teardown-time error about running tasks after environment shutdown.

#### Likely Root Causes
1) Teardown-time error (running tasks after environment shutdown)
- LatestEpisodeView/useEpisodeLoader performs an async call (mocked getLatestEpisode) and logs during the lifecycle. The loader’s effect uses an ignoreRef to prevent state updates after unmount, which is correct, but there may still be pending microtasks/timers in the tree.
- Possible sources:
  - setTimeout calls inside LatestEpisodeView to scroll Day Detail into view (onSelectDay and onSelectNarrativeItem). While these are only invoked upon interactions, other components (or future changes) may also schedule microtasks.
  - Other descendant components (e.g., TimelineStrip or DayStoryboardList) could schedule timeouts or animations without cleanup, causing Vitest to complain when the test ends quickly after expectations.
- Why it surfaces in AppRouter.test.tsx: The tests render full routes (including async loaders) and then immediately assert nav state. If the test finishes while async tasks are still pending (e.g., loader still resolving on a different test), Vitest flags the lingering tasks.

2) Nav highlighting assertion mismatches
- AppShell active logic is explicit and designed to ensure exactly one active item among Stage/Details/Episodes:
  - Stage active when path === "/" OR matches /episodes/:id/stage
  - Details active when path === "/episodes/latest" OR matches /episodes/:id (non-stage)
  - Episodes active only when path === "/episodes"
- The tests assert aria-current for each nav item based on MemoryRouter entries. Failures may arise from:
  - Timing/ordering: The test asserts immediately after render without ensuring that AppShell has rendered and stabilized. While AppShell’s logic is synchronous with useLocation, concurrent rendering or nested route mounts (which trigger async loaders and re-renders) can create brief transitions where assertions read stale attributes.
  - Overlapping renders: During test execution, other routes in the same file also mount/dismount and trigger async logs; if the test ends before waiting for the nav to settle, aria-current attributes might not reflect the expected final state when the assertion runs.
  - Attribute expectation strictness: The tests use element.getAttribute("aria-current") === "page" for active, and null for inactive. Our code sets aria-current only when active (undefined otherwise). getAttribute returns null when the attribute is absent, which should pass, but any interim re-render could briefly set/unset attributes while the assertion runs.

3) Historical duplicate heading issue
- Previously, tests saw multiple matches for “Episode Agents Overview” during LatestEpisodeView rendering. That has been resolved by ensuring this heading only renders in the fully-loaded state and by removing a similarly-named heading from EpisodeAgentsPanel. AppRouter tests have since moved beyond that specific failure; current failures appear unrelated to duplicate headings.

#### Evidence Pointers (Code Paths)
- useEpisodeLoader.ts: async fetch, ignoreRef cleanup, and logs.
- LatestEpisodeView.tsx: logs, EpisodeMoodBanner computation, StageMap VM creation, and setTimeout usage inside click handlers for scrolling (potential timer source if triggered in tests or during internal list mounting).
- AppShell.tsx: explicit active-state logic using pathname regexes and aria-current toggling.
- AppRouter.test.tsx: nav tests use MemoryRouter and immediate expectations on aria-current; route tests mount LatestEpisodeView and StageView which can introduce async behavior into the render lifecycle.

#### Pending Changes (Proposed, no code applied yet)

A) Testing stabilizations (preferred minimal changes in tests)
- Add a small wait for AppShell to fully render before asserting nav highlighting:
  - Use waitFor(() => expect(stageLink).toHaveAttribute("aria-current", "page")) instead of immediate getAttribute checks.
  - Alternatively, assert after awaiting a stable breadcrumb/heading that AppShell always renders (e.g., wait for presence of the main navigation region: screen.findByRole('navigation', { name: /Main navigation/i })).
- Reduce cross-test interference by isolating route mounts:
  - For nav highlighting tests that don’t require LatestEpisodeView/StageView to finish loading episodes, mock getLatestEpisode to resolve immediately and/or make expectations after a microtask tick (await Promise.resolve()).
  - Optionally mock child routes to inert placeholders for nav-only tests to avoid async loaders entirely.
- Address the teardown-time error within tests:
  - In tests that may have triggered timers (e.g., by interacting with timeline or storyboard), either avoid those interactions or use vi.useFakeTimers()/vi.runAllTimers() and vi.useRealTimers() in afterEach to flush pending timers.
  - Ensure all awaited findBy* calls resolve before the test exits; avoid querying DOM synchronously while async loaders are still in-flight.

B) Non-breaking code-level hardening (optional if we choose to fix at source)
- Gate noisy console.log in components under NODE_ENV !== 'test' to cut noise and reduce confusion in test output.
- In LatestEpisodeView, consider safeguarding the setTimeout scroll calls:
  - Track timeout IDs and clear them in a useEffect cleanup when component unmounts, preventing teardown complaints if any timers were scheduled by user interactions in tests.
- In useEpisodeLoader, retain the ignoreRef pattern (already present); optional: add an AbortController to cancel the fetch if implementation changes to a real fetch in-browser. Not required for current mocked environment.

C) Assertion robustness for headings (follow-up on historical issue)
- Prefer querying by data-testid for the unique heading in LatestEpisodeView (data-testid="episode-agents-overview-heading") in router tests that assert presence of that specific heading, to avoid accidental matches if similar text appears elsewhere in the future.

#### Likely Reasons for Each Currently Failing Test Group
- “nav highlighting — Stage active at root /” and similar nav tests:
  - Likely failing due to immediate assert without ensuring navigation render is stable in the presence of concurrently mounting async routes (from the same tree). A short waitFor around the aria-current expectations typically stabilizes these.
- Teardown error (running tasks after test finish):
  - Likely due to pending timers/microtasks from route components (either in LatestEpisodeView scrolling helpers or other children like TimelineStrip) not being flushed/cleared before the test ends. Using fake timers or awaiting component settle points should resolve this.

#### Checklist of Suggested Changes (Pending Approval)
- Tests (AppRouter.test.tsx)
  - [ ] For each nav highlighting test, wrap aria-current assertions in waitFor.
  - [ ] Precede nav assertions by awaiting a stable element in AppShell (e.g., the nav by role/name) to ensure mount.
  - [ ] If any test causes interactions that could set timers, either remove the interaction for nav-only tests or flush timers with vi.runAllTimers().
  - [ ] Where asserting the presence of the LatestEpisodeView heading, use screen.findByTestId('episode-agents-overview-heading') instead of text match to avoid ambiguity, or keep text and ensure only one render source exists (already satisfied).
- Optional source hardening (no behavioral change)
  - [ ] Guard component console logs under NODE_ENV !== 'test'.
  - [ ] Track and clear any setTimeout IDs in LatestEpisodeView if interactions are part of tests.

#### Conclusion
- The failing AppRouter tests are most plausibly caused by timing/async effects around route mounting and nav assertions that don’t wait for a stable render, combined with a teardown-time warning that suggests at least one pending timer/microtask at test end.
- Recommended next step (upon approval): adjust AppRouter.test.tsx to waitFor the nav state and, if needed, flush timers in affected tests. If we prefer fixing at the source, add minimal cleanups for any timers scheduled in LatestEpisodeView during unmount.

— Junie
