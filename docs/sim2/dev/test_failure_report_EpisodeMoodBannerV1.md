### Test Failure Report — EpisodeMoodBannerV1

Date: 2025-11-25
Component: ui-stage/src/components/EpisodeMoodBannerV1
Test: ui-stage/src/components/EpisodeMoodBannerV1.test.tsx

---

Summary
- We executed the targeted Vitest run for EpisodeMoodBannerV1 and observed a single snapshot mismatch.
- No production code was modified. This report documents the failure details, likely cause, and proposed next steps.

Command Executed
```
cd ui-stage && npx -y vitest run src/components/EpisodeMoodBannerV1.test.tsx
```

Observed Outcome
- Vitest version: v2.1.9 (in ui-stage workspace)
- Result: 1 failed test (1/1)
- Failure type: Snapshot mismatch

Relevant Console Excerpt
```
FAIL  src/components/EpisodeMoodBannerV1.test.tsx > EpisodeMoodBannerV1 > renders icon, label, and summary with correct aria-label
Error: Snapshot `EpisodeMoodBannerV1 > renders icon, label, and summary with correct aria-label 1` mismatched
- Expected
+ Received
@@
  <span
    aria-hidden="false"
-   aria-label="Episode mood: Building Pressure — Systems show strain under load."
+   aria-label="Episode arc mood: Building Pressure. Episode-wide summary: Systems show strain under load."
    class="_icon_11fbfa"
    role="img"
  >
    🔺
  </span>
```

What The Test Asserts
- Renders the icon with role="img" and a matching accessible name containing the prefix "Episode arc mood:".
- Renders label and summary line.
- Applies the mood class ("medium") on the banner wrapper via data-testid="episode-mood-banner".
- Matches a stored snapshot for the component structure and attributes.

Failure Analysis
- The runtime DOM matches the updated accessibility copy: `aria-label="Episode arc mood: ... Episode-wide summary: ..."`.
- The stored snapshot expects previous copy: `aria-label="Episode mood: ... — ..."` (different prefix and punctuation).
- This indicates the test snapshot is stale relative to the current component text used for the aria-label.

Likely Root Cause
- A prior copy clarification landed in EpisodeMoodBannerV1 to better communicate that the banner represents an episode-wide arc, not day-to-day direction. The test snapshot was not updated after this a11y text adjustment.

Scope of Impact
- Only this component test’s snapshot is failing. Functional assertions (presence of icon, label, summary, and CSS class) still pass before the snapshot check.
- No backend, VM contracts, or rendering logic failures were observed.

Proposed Next Steps (No code changes performed yet)
- Option A: Update the snapshot with `-u` to reflect the current accessible label.
- Option B: Make the snapshot less brittle by focusing on structural aspects and asserting key text nodes separately, while asserting the aria-label pattern via regex (already partially done). This preserves intent and reduces churn when non-functional copy changes occur.
- Option C: If the clarified copy is unintended, revert the aria-label in the component to the previously snapshotted wording and re-run tests. Note: this would reduce clarity per the recent “global arc vs daily direction” detour docs.

Recommendation
- Prefer Option A or B to keep the improved accessibility copy. If stability is paramount, Option B balances stability with intent by keeping snapshot structural while verifying aria-label via pattern matching.

Verification Not Performed (per instruction)
- No snapshot updates executed.
- No component or test source changes made.

Appendix
- Test file: ui-stage/src/components/EpisodeMoodBannerV1.test.tsx
- Snapshot file: ui-stage/src/components/__snapshots__/EpisodeMoodBannerV1.test.tsx.snap
