### Phase 3 — Agent Identity & Expression (Summary)

Phase 3 made agents feel like characters across the UI using a consistent identity system.

Overview
- Identity language: AgentAvatar v2 (circular ring + organic blob) with vibeColorKey hues and stress glow tiers.
- Surfaces updated:
  - EpisodeAgentsOverview — card grid with avatar, name, role, tagline.
  - EpisodeAgentsPanel — identity card rows with stats, badges, and sparkline.
  - DayStoryboard — up to 3 agent cameos per strip (tiny avatars) and an inline “belief vs reality” mini-panel.

Data flow
- AgentViewModel (vm/agentVm.ts):
  - Adds optional, additive fields: vibeColorKey (teal|indigo|green|amber|neutral), stressTier (none|medium|high|cooldown), displayTagline.
  - buildPanelAgents(vm) enriches agents for the panel with avgStress, latestAttributionCause, sparkPoints.
- Day Storyboard VM (vm/dayStoryboardVm.ts):
  - Derives agentCameos per day from StageEpisode.days[day_index].agents.
  - Reuses AgentViewModel identity via buildAgentViews; maps stressTier → cameo tiers (low|mid|high).
- LatestEpisodeView (routes/LatestEpisodeView.tsx):
  - Keeps selectedBelief { dayIndex, agentName } in local state.
  - Rules: strip click selects + scrolls and clears belief; cameo click toggles belief (no scroll); narrative and timeline selections clear belief.

Identity tokens (styles/tokens.css)
- Vibe families: --lf-agent-vibe-<key>-base|ring|muted for teal, indigo, green, amber, neutral.
- Stress glow: --lf-agent-stressGlow-none|med|high|cooldown applied via .stress-* classes on AgentAvatar.

Non-goals / future work
- Attribution iconography and richer belief/misalignment overlays are deferred.
- Story-mode interactions and cameo animations planned for Phase 4/5 (Era II/III).

Implementation note (closure)
- Phase 3D cleanup: AgentAvatarV1 has been removed. All surfaces now render avatars via AgentAvatar v2 using vibeColorKey + stressTier.
- Edge cases verified: no agents → no cameos; missing belief text → neutral fallback; single-day episodes behave correctly.
- Phase 3 is stable and ready for Phase 4.
