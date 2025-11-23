🌌 Loopforge Memory Subsystem Spec

(A.K.A. “How the Robots Remember You”)
Version: 0.1 – Design-Only

0. Intent

Build a first-class memory system for Loopforge that:

Gives agents stable, structured long-term memory across episodes/runs.

Makes the Supervisor / Architect intent a real object in the system, not just vibes.

Provides deterministic, testable behavior around what is remembered, forgotten, and surfaced.

Reuses and extends existing types you already have:

BeliefState

AgentLongMemory

AgentReflectionState

EpisodeStoryArc

SupervisorIntentSnapshot

ActionLogEntry, ReflectionLogEntry, etc.

This spec is design only—no code is assumed changed yet.

1. Goals & Non-Goals
   1.1 Goals

Give each agent:

A long-term memory of key facts, relationships, and events.

A short-term “working context” for decisions within a day.

A threaded story of what’s going on (EpisodeStoryArc).

Make memory:

Grounded: everything ultimately traceable back to logs/episodes.

Domain-aware: Pinterest campaigns vs. Loopforge architecture vs. supervision, etc.

Identity-safe: uses consistent (run_id, episode_id, episode_index) invariants.

Provide:

Clear APIs for “observe → store → retrieve → decay”.

A supervisor-level view of “what matters” via SupervisorIntentSnapshot.

Hooks for analytics to understand how memory influenced behavior.

1.2 Non-Goals (For Now)

No semantic embeddings / vector DB.

No multi-environment distributed memory.

No “internet-scale” storage optimization.

No auto-healing/human-like meta-cognition (yet).

We’re building a clean, deterministic scaffold. You can plug fancy stuff in later.

2. High-Level Conceptual Model

Think of Loopforge memory as 3 stacked layers:

Perception & Belief Layer (per step / per day)

What the agent thinks is true right now.

Types: AgentPerception, BeliefState, AgentEmotionState.

Episode Story Layer (per episode)

How the episode is threaded into a story: arcs, tensions, roles, conflicts.

Types: EpisodeStoryArc, EpisodeTensionSnapshot, AgentReflectionState.

Long-Term Memory Layer (cross episodes, cross runs)

Durable knowledge: recurring facts, preferences, relationships.

Types: AgentLongMemory, SupervisorIntentSnapshot.

Data flows up from logs → summaries → stories → long-term memory, and down from long-term memory into per-step context.

3. Core Data Structures

Below are conceptual shapes, not final code. Assume they live in loopforge/types.py or a new loopforge/memory/types.py depending on your existing layout.

3.1 Memory Domains

You run multiple “engines” in your life; Loopforge will too.

@dataclass
class MemoryDomain:
"""Logical grouping of memories (like 'PinterestAgency' or 'LoopforgeBackend')."""
name: str                    # e.g. "PinterestAgency", "BloomWhispers", "Loopforge"
description: str | None = None

3.2 Memory Item

Fundamental unit of long-term memory.

@dataclass
class MemoryItem:
id: str                      # stable ID for this memory
domain: str                  # MemoryDomain.name
owner_agent: str             # agent name ("Junie", "Producer", etc.)

    # Content
    title: str                   # short label
    body: str                    # human-readable description
    tags: list[str]              # e.g. ["client", "bug", "spec", "sprint-plan"]
    
    # Identity & provenance
    run_id: str | None = None
    episode_id: str | None = None
    episode_index: int | None = None
    day_index: int | None = None
    step: int | None = None

    # Scoring signals
    importance: float = 0.0      # manual/supervisor hint
    frequency: int = 1           # how often this fact was reinforced
    last_seen_at: str | None = None  # ISO timestamp of last reinforcement
    created_at: str | None = None    # ISO timestamp
    source: str | None = None        # "simulation", "reflection", "supervisor-note"

    # Lifecycle
    active: bool = True          # soft deletion / decay flag

3.3 AgentLongMemory

Per-agent persistent memory collection.

@dataclass
class AgentLongMemory:
agent_name: str
items: list[MemoryItem]

    # Optional index/cache for faster lookups (in-memory only)
    # domain_index: dict[str, list[str]]  # domain → [memory_id]


You can later switch this to chunked storage (JSONL, SQLite, etc.), but from the type perspective it’s just a list + invariants.

3.4 BeliefState (Working Context)

This already exists in your types; we’ll extend its semantics.

@dataclass
class BeliefState:
agent_name: str
current_domain: str | None
# The “active” beliefs at this step:
facts: dict[str, Any]        # key-value beliefs: {"latest_run_id": "..."}
active_memories: list[str]   # MemoryItem ids surfaced for this step

    # Optionally:
    source_episode_id: str | None = None
    step_index: int | None = None


BeliefState becomes the bridge between long-term memory and current decision context.

3.5 SupervisorIntentSnapshot

We turn “the Architect’s will” into a first-class structure.

@dataclass
class SupervisorIntentSnapshot:
"""High-level goals and constraints injected into agents."""
timestamp: str               # ISO
global_objectives: list[str]  # e.g. ["Stabilize ID invariants", "Fix /episodes/latest"]
per_agent_objectives: dict[str, list[str]]  # agent_name → [objectives]
priority_domains: list[str]  # e.g. ["Loopforge", "PinterestAgency"]
notes: str | None = None     # natural language situational notes


Agents use this to weight which memories matter more right now.

3.6 EpisodeStoryArc (Threading)

You already have this type; we define how memory interacts with it:

Each EpisodeStoryArc can:

Reference key MemoryItem ids.

Emit MemoryCandidates at the end of the episode (what should be persisted).

Conceptual helper structure:

@dataclass
class MemoryCandidate:
"""Candidate to be promoted from episode-level insight to long-term memory."""
owner_agent: str
domain: str
title: str
body: str
tags: list[str]
importance: float
run_id: str | None = None
episode_id: str | None = None
episode_index: int | None = None
day_index: int | None = None
step: int | None = None
source: str | None = None     # "episode-summary", "reflection", "supervisor"

4. Memory Lifecycle

We define a canonical loop:

Observe → Evaluate → Consolidate → Retrieve → Decay

4.1 Observe (Within Episode)

Data sources:

ActionLogEntrys

DaySummarys

EpisodeSummary

AgentReflections

SupervisorMessages

These generate MemoryCandidate objects via simple heuristics:

Significant tension spikes.

New agent or environment attributes.

Supervisor “this is important” messages.

User/Architect explicit annotation.

4.2 Evaluate & Consolidate (Episode Boundary)

At the end of an episode (or day, depending on granularity):

Collect a list of MemoryCandidates from:

EpisodeStoryArc

AgentReflectionState

SupervisorIntentSnapshot

De-duplicate:

Same domain + similar title + same agent → increment frequency instead of new item.

Promote to MemoryItem:

Assign importance based on:

Supervisor hints.

Tension/pain.

Frequency across days.

Set identity fields (run_id, episode_id, episode_index, day_index).

Append to the agent’s AgentLongMemory.

Important invariant:

Every MemoryItem must have a path back to the logs/episode it came from.

That’s the memory version of your “million dollar identity rules.”

4.3 Retrieve (At Decision Time)

Before an agent decides what to do:

Start from:

BeliefState.current_domain

SupervisorIntentSnapshot.priority_domains

Current EpisodeStoryArc state

Retrieve top-K MemoryItems using a scoring function (spec below).

Update BeliefState:

belief_state.active_memories = [item.id for item in top_k_items]
belief_state.facts["memory_context"] = [
{"title": i.title, "body": i.body, "tags": i.tags} for i in top_k_items
]


Agents then “see” a small, prioritized subset of their long-term memory.

4.4 Decay & Pruning (Maintenance)

Periodically (per episode, per N episodes):

Lower importance or mark active=False for items that:

Haven’t been referenced in a long time.

Are contradicted by newer memories.

Keep everything append-only on disk; use flags in memory.

5. Scoring: How to Choose Which Memories Surface

We define a scoring function for MemoryItems:

score(item, context) =
w_domain    * domain_match(item, context) +
w_tags      * tag_overlap(item, context) +
w_recency   * recency_score(item) +
w_freq      * frequency_score(item) +
w_import    * item.importance +
w_super     * supervisor_boost(item, snapshot)


Where:

domain_match

1.0 if item.domain == current_domain

0.5 if item.domain in priority_domains

0 otherwise.

tag_overlap

Jaccard-like overlap between item.tags and context tags (e.g. ["identity", "logs", "episodes"]).

recency_score

Based on last_seen_at and/or (episode_index, day_index). More recent → higher.

frequency_score

log(1 + frequency) or similar.

importance

Straight from the MemoryItem.importance.

supervisor_boost

If SupervisorIntent talks about the same domain/tags, give a fixed bonus.

All weights w_* are config-driven, not hardcoded.

6. Module Responsibilities

Let’s sketch the module layout.

6.1 loopforge/memory/core.py

Pure logic, no I/O.

Key functions:

def make_memory_candidate_from_day_summary(...): -> list[MemoryCandidate]
def make_memory_candidate_from_reflection(...): -> list[MemoryCandidate]
def consolidate_candidates(
existing_memory: AgentLongMemory,
candidates: list[MemoryCandidate],
) -> AgentLongMemory

def score_memory_item(
item: MemoryItem,
belief_state: BeliefState,
supervisor: SupervisorIntentSnapshot | None,
context_tags: list[str],
) -> float

def retrieve_top_memories(
memory: AgentLongMemory,
belief_state: BeliefState,
supervisor: SupervisorIntentSnapshot | None,
context_tags: list[str],
k: int = 5,
) -> list[MemoryItem]

6.2 loopforge/memory/storage.py

Handles persistence (JSONL, SQLite, whatever).

Above-the-seam, similar pattern to run registry.

Functions:

def load_agent_memory(agent_name: str) -> AgentLongMemory
def save_agent_memory(memory: AgentLongMemory) -> None


Initially: one JSON file per agent under logs/memory/agent_<name>.json.

6.3 loopforge/memory/integration.py

Orchestrates memory across episodes.

Hooks:

After sim run → call update_memory_from_episode(...).

Before agent step/episode → call hydrate_belief_state_with_memory(...).

def update_memory_from_episode(
episode: EpisodeSummary,
reflections: list[AgentReflection],
supervisor_snapshot: SupervisorIntentSnapshot | None,
) -> None

def hydrate_belief_state_with_memory(
belief_state: BeliefState,
episode_story: EpisodeStoryArc,
supervisor: SupervisorIntentSnapshot | None,
) -> BeliefState

7. Integration with Existing Loopforge Types

We integrate, not reinvent.

7.1 With ActionLogEntry & Identity Rules

Each MemoryItem:

MUST have (run_id, episode_id, episode_index) if it was derived from logs.

Optionally day_index, step.

Use the same “million dollar identity rules”:

Never invent IDs that don’t exist in logs.

Memory is anchored to reality, not hallucination.

7.2 With EpisodeSummary, DaySummary

At end of view-episode / analyze_episode path:

Extract MemoryCandidates from:

High tension days.

Agents with large trait changes.

Supervisor actions.

7.3 With AgentReflectionState

When agents reflect:

They can explicitly propose memory candidates:

“I learned that /episodes/latest fails when registry IDs don’t match logs.”

Tag: ["bug", "identity", "api"].

This is the “Junie writes down what matters” channel.

8. Memory API Design (Agent-Facing)

From an agent’s POV (e.g., Junie), we provide a simple API:

class AgentMemoryFacade:
def __init__(self, agent_name: str):
...

    def recall(self, belief_state: BeliefState, context_tags: list[str], k: int = 5) -> list[MemoryItem]:
        ...

    def remember(self, candidate: MemoryCandidate) -> None:
        """Immediately commit a high-priority memory (e.g. supervisor orders)."""

    def reinforce(self, memory_id: str) -> None:
        """Increment frequency / update last_seen_at."""


The sim loop doesn’t need to know about scoring specifics. It just:

Loads agent memory.

Calls recall(...).

Places result into BeliefState.

Lets the agent use this in decision-making.

9. Phased Implementation Plan
   Phase 0 – Types Only

Add MemoryDomain, MemoryItem, AgentLongMemory, MemoryCandidate.

Add SupervisorIntentSnapshot semantics.

No behavior yet. Just types + tests for JSON round-trip.

Phase 1 – Offline Episode Consolidation (No Runtime Changes)

Implement:

make_memory_candidate_from_episode(...)

consolidate_candidates(...)

load_agent_memory / save_agent_memory (JSON)

Add a dev CLI command:

loopforge-sim export-memory --agent Junie --episode-latest

No agents using memory yet, but you can generate memory archives.

Phase 2 – Read-Only Memory for Agents

Implement retrieve_top_memories(...).

Wire hydrate_belief_state_with_memory(...) into:

view-episode, replay-episode, or a dedicated “analysis mode”.

Agents now see memories but don’t write new ones during sim.

Phase 3 – Full Bidirectional Memory

Let sim loop:

Promote candidates at end-of-day or end-of-episode.

Persist memory on disk.

Agents can call remember and reinforce via integration hooks.

Phase 4 – API Exposure (Optional)

Add an API endpoint:

/agents/{name}/memory (read-only)

/agents/{name}/memory/search?tags=... (debug/dev)

10. Testing Strategy

We treat memory like the identity spec: fuzzed, tested, deterministic.

10.1 Unit Tests

MemoryCandidate → MemoryItem promotion:

Ensures identity fields are copied.

Merges duplicates by domain + title + owner_agent.

Scoring function:

Domain match vs. mismatch.

Supervisor boosts.

Recency, frequency.

Storage:

Round-trip JSON for AgentLongMemory.

10.2 Integration Tests

Small artificial episode:

2 agents.

2 days.

Known tension spike.

Generate EpisodeSummary.

Run memory consolidation.

Assert:

At least one MemoryItem referencing the correct run/episode/day.

10.3 End-to-End Scenario

Run sim.

Run episode analysis.

Update memory.

Run another sim episode that:

Calls recall(...).

Confirm agent has access to previous bug/lesson.

11. Future Directions (a.k.a. Soul Hooks)

Not for now, but we leave hooks for:

Semantic embeddings for MemoryItem retrieval.

Cross-agent shared memory (“organizational memory”).

Emotion-weighted memory (link importance with AgentEmotionState).

Memory conflict detection (contradicting facts).

Architect notebooks:

Structured SupervisorIntentSnapshot series that look suspiciously like your actual brain.