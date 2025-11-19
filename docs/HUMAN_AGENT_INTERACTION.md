# Loopforge Human–Agent Interaction Framework for App Development
**A structured workflow for collaborating with a Planning Agent (“Architect”) and an Execution Agent (“Executor”) in multi-step engineering cycles.**
## 0. What This Document Defines

Loopforge uses a two-agent + human supervisor structure for engineering work:
* **LLM-Architect** — a ReAct-style reasoning agent responsible for  
**planning, validation, and architectural thinking**
* **LLM-Executor** — any deterministic code-generation / code-editing tool you choose to use, responsible for  
**implementing small, precise code changes and returning structured results**  
(e.g., an LLM code assistant, API-based tool, CLI helper, or even manual human execution)

This document describes **how humans interact with these agents** safely and effectively.

It avoids giving the agents open-ended instructions such as:
* “scan the repo”
* “inspect all commits before yours”
* “analyze the entire project”

Instead, the system operates strictly on **explicitly provided context.**

1. Roles & Responsibilities
1.1 Human (Project Lead)

The human:

sets sprint goals

initiates Architect cycles

provides necessary code snippets, diffs, or logs

passes Architect-approved tasks to the Executor

reviews outputs and merges code

controls architectural direction and final decisions

The human is always in the loop.

1.2 Architect (Reasoner, Planner, Validator)

The Architect is the thinking agent.

Architect Responsibilities

Understanding goals

interpret user objectives

ask for clarification if required

Planning

produce sprint plans

generate small, atomic task specifications for the Executor

define acceptance criteria and boundaries

Validation (start of each sprint)
Compare:

the previous sprint’s task specs

the Executor’s reports

the diffs/logs the human provides

Architect then generates a Validation Report and any follow-up tasks.

Retrospective

identify what worked

note where specs were unclear

propose improvements to future tasks

Architect Boundaries

The Architect must not:

search or scan the repository

infer unseen context

design large refactors without explicit human approval

modify architectural constraints

assume access beyond what the human explicitly provides

Architect is a context-limited planner, not a repo explorer.

1.3 Executor (Your Code Tool of Choice)

The Executor is the implementation mechanism.
This can be:

an LLM with code editing capabilities

a Dust agent

a local script

a JetBrains / VSCode tool

or even a human performing the changes

Executor Responsibilities

perform precise, narrow edits described in the task spec

modify only the explicitly listed files

run tests or diagnostics (when available)

return a structured report containing:

changed files

test results

errors / warnings

any deviations from spec

Executor Boundaries

The Executor must not:

explore or interpret project structure beyond what the task describes

rewrite files not listed in the task

perform broad refactors

produce code outside the specified scope

The Executor is intentionally mechanical and constrained.

2. The Loopforge Sprint Cycle

A sprint follows a structured loop:

Validate → Plan → Execute → Review → Retro → Next Sprint

2.1 Phase 1 — Validation (Architect)

At the beginning of each sprint, the human provides:

previous sprint’s task specs

Executor reports

code diffs

logs/test outputs if relevant

Architect builds a Validation Report:

{
  "sprint": 6,
  "overall_status": "met | partially_met | not_met",
  "per_task": [...],
  "follow_up_tasks": [...],
  "executor_feedback": [...]
}


This grounds the new sprint in reality.

2.2 Phase 2 — Sprint Planning (Architect)

Architect then:

summarizes goals

defines constraints

produces a structured sprint plan

outputs a set of narrow, well-scoped Executor task specs

Each spec includes:

file paths

required changes

acceptance criteria

any tests that should pass

The human approves or adjusts.

2.3 Phase 3 — Execution (Executor)

For each task:

The human gives the task spec to the Executor

The Executor makes minimal changes

The Executor returns a structured report

Human validates or collects additional logs

You may optionally send this output back to Architect for mid-sprint checks.

2.4 Phase 4 — Mid-Sprint Architect Checks (Optional)

Architect can review individual tasks:

check if implementation matches the spec

detect inconsistencies

propose micro-fix tasks

2.5 Phase 5 — Sprint Retro (Architect)

Architect evaluates:

what patterns caused issues

how tasks can be written better

where technical debt is emerging

what constraints should be updated in the next sprint

3. Guiding Principles
3.1 Context is explicit

Neither Architect nor Executor ever “explores” the repo.

All reasoning is based solely on what the human provides.

3.2 Tasks are small and reversible

Executor tasks are:

atomic

deterministic

bounded to specific files

easy to validate based on acceptance criteria

3.3 Strategic vs. Mechanical split

Architect does: reasoning, planning, validation

Executor does: deterministic code edits and test runs

This mirrors a real engineering team’s separation of concerns.

3.4 Human oversight is continuous

Humans:

approve plans

route tasks

review outputs

merge changes

mediate architectural direction

Agents do not self-direct.

4. Sprint Deliverables

Each sprint yields:

Validation Report (Architect)

Sprint Plan (Architect)

Executor Task Specs (Architect)

Executor Reports

Retro Summary (Architect)

These artifacts form Loopforge’s evolving technical memory.

5. Summary

This framework enables Loopforge to run structured, safe multi-agent engineering cycles by:

giving the Architect clear reasoning responsibilities

giving the Executor minimal, precise implementation work

keeping humans in control

avoiding unconstrained agent behavior

supporting long-horizon architectural progress

It defines a reproducible way for humans, planning agents, and code-execution tools to collaborate productively.