# What Loopforge Is — and Why It Uses an Extended ReAct Architecture

## How is Loopforge Built?

Loopforge is a multi-agent engineering system designed to explore how large language models can meaningfully contribute to real software development. At its core, Loopforge builds on the principle that effective engineering requires **two kinds of intelligence:**

**1. Architectural reasoning**

Long-horizon thinking, memory, planning, understanding of plumbing, interpretation of technical constraints, the ability to create structured workflows and assess if they have reached their desired results.

Need to first understand the project structure and domain knowledge, the current state of the codebase, and the constraints imposed by the team, propose the plan, control its execution, and adjust the plan according to feedback.

**2. Deterministic execution**

Precise, scoped implementation of code changes with clear boundaries and reproducible results according to best practices and detailed instructions from the Architect.

Loopforge formalizes these into two distinct agents:
* **The Architect** — a ReAct-style LLM-based planner equipped with **episodic memory,** used to retain architectural intent, previous sprint history, domain constraints, and accumulated “beliefs.”
* **The Executor** — a deterministic code-editing and test-running tool (LLM-based or otherwise), which performs only the small, atomic tasks defined by the Architect.

Humans remain firmly in control of direction, context provisioning, approval, and merging.

This separation mirrors how real engineering teams work:  
the Architect thinks, the Executor does, and the Human guides.

---

## Where ReAct Fits — and Why We Extend It

The [ReAct](https://arxiv.org/abs/2210.03629) (Reason + Act) framework provides a foundational insight:  
agents must _think_ and _use tools iteratively_ to solve complex tasks.

Loopforge adopts this loop for the Architect:
> **Think → Ask for context → Plan → Produce tasks → Validate → Think again**

But pure ReAct has well-known limitations when applied to long-form engineering work:
* it has no memory
* it cannot retain architectural constraints across sessions
* it is not structured for multi-step sprints
* it does not distinguish between planner and executor roles
* it does not define validation, retrospectives, or task decomposition for real codebases

Thus, Loopforge introduces a layer that ReAct does not specify:

> **ReAct + Episodic Memory + Role Specialization + Sprint Protocols**

This is where Loopforge pushes beyond existing research:
* The Architect’s memory is reconstructed every cycle, giving it a persistent self and an evolving understanding of the project.
* The Architect never touches code directly; it only defines the smallest safe actions.
* The Executor is kept intentionally simple and mechanical to stay focused.
* The sprint structure formalizes how agents collaborate, validate, and improve.

Loopforge essentially turns ReAct into a **full engineering methodology,** not just a reasoning loop.

---

## How Loopforge Relates to Existing Research

Several strands of academic work explore pieces of this puzzle:
* **ReAct** — iterative reasoning and tool use
* **Reflexion-style agents** — self-improvement through episodic memory
* **Voyager-style explorers** — long-lived planners with skill libraries
* **Planner–Executor architectures** — dividing thinking from acting

Loopforge synthesizes these threads, but introduces a set of capabilities that the literature typically treats separately:

**1. A persistent planning agent with structured onboarding**

The Architect receives a full rebuilt memory state each sprint, giving it long-term architectural coherence.

**2. A deterministic Executor with strict boundaries**

The Executor never improvises, never explores, and never extends the plan — preventing hallucinated refactors and runaway edits.

**3. A sprint-based workflow for agents**

Validation → Planning → Execution → Review → Retro
— a real engineering cycle rarely formalized in agent systems.

**4. Human-governed safety and context control**

Agents operate only on what humans explicitly provide — protecting against uncontrolled repo mutation or unintended autonomy.

**5. A practical path toward layered, multi-agent engineering**

Loopforge offers a design pattern for **scaling complexity without losing control:**  
Architect (memory + reasoning)  
→ Executor (mechanical precision)  
→ Human (direction + oversight)

This structure is conceptually simple but operationally powerful.

---

## Why Loopforge Matters

Loopforge explores the idea that:
> **If we want agents to build real software, they must behave like real engineers.**

This means:
* long-term memory
* constraints
* accountability
* validation
* decomposed tasks
* respect for context boundaries
* iterative improvement
* safe tool use
* reusable state
* human supervision

Loopforge is not an “autonomous coder.”  
It is a **repeatable engineering protocol** where agents assist—not replace—humans in building and evolving complex systems.

It aims to demonstrate a practical blueprint for agent-driven development that is:
* safe
* interpretable
* auditable
* structured
* collaborative
* grounded in real workflows

This combination — ReAct reasoning + architectural memory + deterministic execution + a structured sprint cycle — is what makes Loopforge distinct in the rapidly evolving landscape of agent research.