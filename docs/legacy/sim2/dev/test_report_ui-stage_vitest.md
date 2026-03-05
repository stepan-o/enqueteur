### UI-Stage Test Run Report (Vitest)

Date: 2025-11-25 13:49 local

Scope: Frontend only (ui-stage)

Commands executed
- npm run test (from ui-stage)

Environment notes
- jsdom test environment
- Vitest v2.1.9

Summary of results
- Test files: 39 total
- Tests: 118 total
- Passed: 38 files, 117 tests
- Failed: 1 file, 1 test

Failing spec
- File: ui-stage/src/routes/LatestEpisodeView.moodBanner.test.tsx
- Suite: "LatestEpisodeView — EpisodeMoodBannerV1"
- Test: "renders the mood banner above the episode header when mood is computable"

Observed error (excerpt)
```
AssertionError: Expected values to be truthy:

> Received: null

  43|     // The banner should appear
  44|     const banner = document.querySelector('[data-testid="episode-mood-banner"]');
  45|     expect(banner).toBeTruthy();
      |                    ^
  46|     // And the label text should be present (label varies by delta; we…
```

Related console output (trimmed)
```
loader start { episode: null, error: null, isLoading: true }
Render LatestEpisodeView { episode: null, error: null, isLoading: true }
fetching…
setting episode { id: 'ep-mood', runId: 'run-mood', index: 0, stageVersion: 1, days: [], agents: [], tensionTrend: [0.1, 0.5], story: { … }, _raw: {} }
finally: setting isLoading=false
Render LatestEpisodeView { episode: { … }, error: null, isLoading: false }
```

What the test expects
- After rendering the route with a mocked latest episode (tensionTrend [0.1, 0.5] and a top-level narrative text), the component should render the EpisodeMoodBannerV1 above the header.
- The test waits for the "Timeline" heading (ensures mount), then queries for the banner via data-testid="episode-mood-banner" and expects it to be present.

Relevant production code paths
- LatestEpisodeView.tsx statically imports buildEpisodeArcMood and EpisodeMoodBannerV1 and renders the banner within a try/catch guard:
  - If buildEpisodeArcMood returns a VM, it renders <EpisodeMoodBannerV1 mood={mood} />.
  - If an error occurs, it omits the banner (fail-soft).

Initial hypotheses (no code changes made)
1) Timing/race in render assertions
   - Although the test awaits the "Timeline" heading, the banner render is sync relative to the episode value. However, if any microtask scheduling defers the IIFE returning the banner, the immediate DOM query might still be racing.

2) Unexpected error thrown inside buildEpisodeArcMood
   - The try/catch would omit the banner if buildEpisodeArcMood throws. The episode has tensionTrend [0.1, 0.5], which should be valid. A throw would indicate an edge case (e.g., undefined fields) or module graph mocking interference (see next point).

3) Module mocking/graph isolation side effect
   - The test mocks buildEpisodeView as a passthrough and imports LatestEpisodeView statically. If any prior mocks or cached modules affect episodeArcMoodVm, it could change behavior. Vitest requires mocks to be applied before module import; out-of-order mocks can lead to unexpected real implementations or mixed graphs.

4) Data-testid mismatch or banner gating condition not met
   - The banner component wrapper uses data-testid="episode-mood-banner" in production. If the mood object computed is falsy or missing a required field (tensionClass), rendering returns null.

Artifacts aiding investigation
- Full command output with console logs saved at project root: .output.txt
  - Contains detailed render logs from LatestEpisodeView during the failing test.

Next-step recommendations (pending maintainer direction; no fixes applied yet)
- Add a debug assertion/log in the test to print any caught errors from buildEpisodeArcMood by temporarily spying on the module (test-only) to confirm whether the try/catch path is taken.
- Ensure the test does not inadvertently mock or reset modules that could affect episodeArcMoodVm for the "computable" case. Keep mocks minimal (only API getLatestEpisode and episodeVm passthrough).
- Optionally wait for the summary text (derived from top-level narrative) instead of the generic Timeline heading before asserting the banner, to further guarantee rendering order in the DOM for this case.
- If the test remains flaky, consider querying with Testing Library (screen.findByTestId) rather than direct document.querySelector to align with the library’s async utilities.

Backend status
- Backend tests were not part of this run per scope; no backend actions taken.

Notes
- No production code was altered in this step; this report is observational and diagnostic only, as requested.

— Junie
