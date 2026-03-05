### Phase 3A — Agent Identity Foundation (Avatar + VibeColor + Stress Glow)

This document summarizes the minimal, additive implementation for Phase 3A.

Scope delivered:
- Era II design tokens for VibeColor families and stress glow tiers.
- Agent ViewModel additive fields to support avatar rendering across screens.
- AgentAvatar v2 (SVG blob + circular ring + stress glow) with a11y label.
- EpisodeAgentsOverview switched to AgentCard v2 skeleton using AgentAvatar, name, and tagline.

Out of scope (reserved for later 3B/3C):
- Attribution icon cluster
- Tagline reveal/micro-interactions
- Belief mini-panel and cameo integration in DayStoryboard

VibeColor derivation (AgentViewModel.vibeColorKey):
- supervisor/lead → "amber"
- primary/delta/operator/optimizer → "teal"
- observer/monitor/analyst/reflective → "indigo"
- coordinator/support/ops → "green"
- unknown/misc → "neutral"

Stress tier derivation (AgentViewModel.stressTier):
- cooldown: stressDelta <= -0.15
- high: end ≥ 0.66 OR delta ≥ 0.4
- medium: end ≥ 0.3 OR delta ≥ 0.15
- none: otherwise

Tagline derivation (AgentViewModel.displayTagline):
1) Prefer existing agent tagline if a non-empty string.
2) Else construct role-based generic:
   - supervisor/lead → "Analytic supervisor"
   - operator/primary/optimizer → "Primary operator"
   - observer/analyst → "Reflective observer"
   - coordinator/support/ops → "Support coordinator"
   - fallback → "System agent"

Design tokens
- File: ui-stage/src/styles/tokens.css
- VibeColor families:
  - --lf-agent-vibe-teal-*, --lf-agent-vibe-indigo-*, --lf-agent-vibe-green-*, --lf-agent-vibe-amber-*, --lf-agent-vibe-neutral-*
  - Each defines -base (blob fill), -ring (circle stroke), -muted (auxiliary text/icon color)
- Stress glow tiers:
  - --lf-agent-stressGlow-none
  - --lf-agent-stressGlow-med
  - --lf-agent-stressGlow-high
  - --lf-agent-stressGlow-cooldown

AgentAvatar v2
- File: ui-stage/src/components/AgentAvatar/index.tsx (+ CSS module)
- Circular frame with ring + organic blob path.
- Colors are driven via CSS variables set by .vibe-* classes.
- StressGlow via .stress-* classes mapping to tokens.
- A11y label: "Agent avatar for {name}. Vibe: {vibeColorKey}. Stress: {stressTier}."; if name missing, "Agent avatar".

EpisodeAgentsOverview (AgentCard v2 skeleton)
- Files: ui-stage/src/components/EpisodeAgentsOverview.tsx + .module.css
- Renders grid of cards. Each card includes:
  - AgentAvatar (left, fixed size)
  - Name (prominent) + role label
  - Tagline (secondary line; uses displayTagline → tagline → fallback)
- Defensive to missing optional fields.

Testing
- VM tests validate role→vibe mapping, stress tier thresholds, and tagline fallback.
- AgentAvatar tests validate rendering (ring + blob), vibe/stress classes, and a11y role/label.
- EpisodeAgentsOverview tests confirm one card per agent, avatar present, name/role/tagline visible, and empty-list handling.

Compatibility
- No backend or schema changes.
- AgentViewModel additions are optional, preserving existing callers.
- data-testid and data-size on AgentAvatar kept for stability across tests.
