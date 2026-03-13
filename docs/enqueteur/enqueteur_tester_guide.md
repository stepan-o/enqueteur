# Enquêteur Tester Guide

## 1. What this build is
Enquêteur is a live, French-language investigation game prototype.  
This build is the MBAM vertical slice: **MBAM / Le Petit Vol du Musée**.

What to expect in this build:
- One playable case (MBAM).
- Live runtime flow (menu -> case launch -> connecting -> playable session).
- Working investigation, conversation, case-notes/minigame, and final-decision panels.
- Prototype UX: functional, but still rough in places.

## 2. Your goal in this case
Your objective is to **recover the missing medallion** by building a reliable timeline and corroborating clues.

In practical terms, you are trying to:
- Inspect key objects.
- Question characters (in French flow).
- Collect/confirm facts and evidence.
- Build contradiction support where needed.
- Attempt a final resolution (Recovery or Accusation).

## 3. How to start playing
From the UI:

1. On **Main Menu**, click `Start Case`.
2. On **Choose A Case**, click MBAM (`Le Petit Vol du Musée`).
3. Wait through Connecting steps:
    1. Opening case file
    2. Joining live session
    3. Confirming session
    4. Loading first scene
4. You should enter **LIVE_GAME** with the world map and side panels visible.

If startup fails, use:
- `Retry Launch` or `Retry Connection` when shown.
- `Back To Cases` or `Back To Main Menu` to reset flow.

## 4. Understanding the current screen
Main live UI regions:

- **Center:** isometric world/map view (rooms and characters).
- **Top-left:** `Back To Cases` and `Main Menu`.
- **Top-right:** **Case Status** (session/case/day/phase/time + quick lead/status feed).
- **Right panel (upper):** **Conversations** (NPC read, scene progress, dialogue intents, submit).
- **Right panel (lower):** **Case Notes** (case brief, leads, facts/evidence, contradictions, minigames).
- **Bottom-left:** **Final Decision** (readiness + `Attempt Recovery` / `Attempt Accusation` + recap).
- **Left contextual panel:** **Inspect panel** appears when you select a room/agent/object.

## 5. Core actions you can take
You can currently do all of the following:

- **Navigate/inspect map context**
    - Double-click a room/building to focus it.
    - Double-click again to exit focus.
    - Click empty map area to clear selection.
- **Inspect objects**
    - Select an object, then use action buttons (examples: inspect, read, check lock, view logs, read receipt).
- **Talk to characters**
    - Use intent buttons in Conversations.
    - Fill required slot fields when shown.
    - Submit your line.
- **Use Case Notes minigames**
    - MG1 Wall Label
    - MG2 Badge Log
    - MG3 Receipt
    - MG4 Torn Note Rebuild
- **Attempt ending**
    - `Attempt Recovery`
    - `Attempt Accusation` (choose suspect)

## 6. Basic play loop
Use this loop for a normal run:

1. Start with starter object checks (Display Case + Wall Label guidance).
2. Open Conversations and do early questioning (Elodie first guidance is shown in UI).
3. Log corroboration via Case Notes and complete at least one minigame.
4. Follow timeline clues (badge log + receipt are important for contradiction progress).
5. Re-enter Conversations for evidence/contradiction intents as scenes surface.
6. Watch Final Decision readiness.
7. Attempt Recovery or Accusation.
8. Review recap/outcome panel.

## 7. How to make progress
Progress signals in current build:

- **Evidence/Facts**
    - Case Notes -> `Evidence Tray` and `Known Facts` should grow.
- **Object progression**
    - `Key Object Leads` shows checked vs remaining affordances.
- **Dialogue progression**
    - Conversations -> `Scene Progress` and recent turns advance.
- **Contradiction progression**
    - Case Notes/Conversations show contradiction status moving from building -> lead found -> ready.
- **Readiness for ending**
    - Final Decision shows `Recovery` / `Accusation` readiness as `blocked`, `risky`, or `available`.

## 8. Final decision flow
How endings currently work:

- Use **Final Decision** panel.
- `Attempt Recovery` is available earlier but may be marked risky if support is thin.
- `Attempt Accusation` can be blocked until contradiction support is satisfied.
- Suspect is chosen from dropdown (`Laurent`, `Samira`, `Outside Actor`).
- Supporting facts/evidence are currently pulled from known state automatically.
- After an accepted attempt, wait for live update and recap text.

## 9. What testers should pay attention to
High-value feedback areas:

- Where progression feels unclear (“what do I do next?” moments).
- Actions that appear available but return confusing blocked/invalid outcomes.
- Dialogue flow confusion (intent choice, slot fields, FR summary requirement).
- Contradiction readiness clarity (when it unlocks, where to use it).
- Readability of panel copy and status language.
- Pacing/dead-end moments before final decision.
- Any startup/connect instability or unexplained error screens.

## 10. Known prototype caveats
Current non-final behavior to keep in mind:

- UI mixes player-facing copy with internal-ish labels/codes in places.
- Room/object interaction is not fully tutorialized; room focus (double-click) is easy to miss.
- Some conversation constraints are strict (scene-gated intents, required slots, summary requirements).
- Some controls are functional but still “playtest tooling” in tone.
- MBAM is the only playable case in this build.

## 11. Recommended smoke test path
Use the canonical defaults:

- Case: **MBAM**
- Seed: **A**
- Difficulty: **D0**
- Mode/profile: **playtest**

Practical smoke path:

1. Launch MBAM from Case Select.
2. Confirm Connecting completes and live map loads.
3. Do starter object checks (Display Case + Wall Label).
4. Submit at least one conversation turn with Elodie.
5. Complete at least one Case Notes minigame.
6. Surface/use timeline clues for contradiction progress.
7. Attempt Recovery or Accusation.
8. Confirm recap/outcome appears and UI remains stable.

## 12. Bug reporting checklist
When filing a bug, include:

- Build context: MBAM, Seed A/B/C, D0/D1, profile (`playtest`).
- Exact step path (what you clicked, in order).
- Panel/area where issue occurred (Map, Inspect, Conversations, Case Notes, Final Decision, Connecting/Error).
- Expected result vs actual result.
- Any visible status/error code or message text.
- Screenshot/video if possible.
- Whether retry/relaunch changes behavior.

---

## Appendix A: Repo modules used as evidence
- [frontend/enqueteur-webview/src/app/appFlow.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/appFlow.ts)
- [frontend/enqueteur-webview/src/app/appState.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/appState.ts)
- [frontend/enqueteur-webview/src/app/screens/MainMenuScreen.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/screens/MainMenuScreen.ts)
- [frontend/enqueteur-webview/src/app/screens/CaseSelectScreen.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/screens/CaseSelectScreen.ts)
- [frontend/enqueteur-webview/src/app/screens/ConnectingScreen.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/screens/ConnectingScreen.ts)
- [frontend/enqueteur-webview/src/app/screens/ErrorScreen.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/screens/ErrorScreen.ts)
- [frontend/enqueteur-webview/src/app/cases/caseCatalog.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/cases/caseCatalog.ts)
- [frontend/enqueteur-webview/src/app/api/caseLaunchClient.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/api/caseLaunchClient.ts)
- [frontend/enqueteur-webview/src/app/actionBridge.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/actionBridge.ts)
- [frontend/enqueteur-webview/src/app/live/enqueteurLiveClient.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/live/enqueteurLiveClient.ts)
- [frontend/enqueteur-webview/src/app/boot.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/boot.ts)
- [frontend/enqueteur-webview/src/render/pixiScene.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/pixiScene.ts)
- [frontend/enqueteur-webview/src/ui/hud.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/hud.ts)
- [frontend/enqueteur-webview/src/ui/inspectPanel.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/inspectPanel.ts)
- [frontend/enqueteur-webview/src/ui/dialoguePanel.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/dialoguePanel.ts)
- [frontend/enqueteur-webview/src/ui/notebookPanel.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/notebookPanel.ts)
- [frontend/enqueteur-webview/src/ui/resolutionPanel.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/resolutionPanel.ts)
- [frontend/enqueteur-webview/src/ui/mbamOnboarding.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/mbamOnboarding.ts)
- [frontend/enqueteur-webview/src/styles/app.css](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/styles/app.css)
- [frontend/enqueteur-webview/src/__tests__/shellPanels.phase5_shell.test.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/__tests__/shellPanels.phase5_shell.test.ts)
- [frontend/enqueteur-webview/src/__tests__/resolutionPanel.phase7_paths.test.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/__tests__/resolutionPanel.phase7_paths.test.ts)
- [frontend/enqueteur-webview/src/__tests__/mbamFixtures.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/__tests__/mbamFixtures.ts)

## Appendix B: Cautious inference notes
- **Room/object exact placement wording:** onboarding copy says starter checks are in the gallery, while fixture data places one starter object in lobby in test snapshots; guide uses “starter object checks” language to avoid overclaiming location.
- **Readiness thresholds:** exact “strong enough” logic is inferred from current Final Decision panel behavior and may still be tuned in backend rules.
- **Dialogue aux fields:** the Conversations panel exposes optional fact/evidence/utterance inputs; their immediate gameplay effect appears limited/indirect in the current command wiring, so testers should treat them as prototype-level.