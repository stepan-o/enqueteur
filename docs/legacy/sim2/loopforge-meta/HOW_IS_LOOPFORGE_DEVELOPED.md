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

## Related Work

Loopforge builds on several established research threads in agent reasoning, tool-use, and iterative code generation. While prior work explores parts of this space, Loopforge combines them into a cohesive architecture tailored for multi-step software development with long-horizon planning, structured memory, and human-governed safety boundaries.

---

### ReAct: Reasoning + Acting

The [ReAct](https://arxiv.org/abs/2210.03629) paradigm demonstrated that LLMs benefit from alternating between free-form reasoning and structured tool use. This work introduced the idea of **explicit thought–action loops,** which inspired the Architect’s internal planning cycle in Loopforge.  
However, ReAct itself is _stateless_: it does not define persistent memory, multi-step workflows, agent roles, or task decomposition for engineering domains.

Loopforge extends ReAct by layering on:
* episodic memory reconstruction
* sprint-based workflows
* division of responsibilities
* controlled execution by a separate agent

This turns ReAct from an inference-level pattern into a **reusable engineering protocol.**

---

### Reflexion and Memory-Augmented Agents

Memory-augmented agents such as those explored in [Reflexion](https://arxiv.org/abs/2303.11366) showed that LLMs can improve performance across episodes when given structured self-feedback. This work motivates the Architect’s **retro → belief update → next-cycle onboarding** loop.

Loopforge builds on this idea by treating retrospectives not merely as error-correction, but as **architectural memory** that guides long-term structural decisions. Unlike Reflexion-style systems, memory is not free-form LLM notes; it is a curated, human-readable record that defines architectural intent for future cycles.

---

### Planner–Executor Architectures

Several research efforts explore splitting agent behavior into a high-level planner and a low-level executor. These systems demonstrate that:
* planners should reason broadly
* executors should follow constraints strictly
* tool-use should be grounded in external actions
* decomposition improves reliability

Loopforge adopts this separation but formalizes it more strongly:
* The **Architect** is the persistent reasoning agent with memory.
* The **Executor** is strictly a tool: narrow, mechanical, deterministic.
* Humans maintain control over context provisioning and merging.

This avoids the common failure mode where planners and executors blur roles and produce runaway changes.

---

### Skill Libraries & Lifelong Agents

Work on lifelong learning agents (e.g., “skill libraries,” “self-growing agents,” and exploratory frameworks) has explored agents that accumulate knowledge across episodes. These systems demonstrate the value of:
* persistent agent identity
* reusable patterns
* long-term self-improvement

Loopforge adapts this idea to software engineering by giving the Architect onboarding - **a structured memory of product vision, project constraints, design decisions, and sprint histories,** enabling it to plan coherently across weeks or months of system evolution.

---

### Program Synthesis & LLM Code Generation

Research in LLM-based program synthesis and code editing highlights two central challenges:
(1) LLMs can generate correct code, but (2) they lack reliability when making multi-step or multi-file changes.

Loopforge addresses these challenges by:

isolating architectural reasoning from code editing

constraining the Executor to file-scoped, reversible tasks

introducing acceptance criteria for every change

inserting human oversight at every transition

enforcing strict boundaries around what agents may modify

This turns multi-step code generation into a structured, auditable process.

Human-in-the-Loop AI Systems

There is extensive research emphasizing the need for human governance in agentic workflows. Loopforge adopts this principle explicitly:

humans provide context

humans approve plans

humans mediate uncertainties

humans merge code

Rather than pursuing autonomous agents, Loopforge focuses on collaborative intelligence—agents that assist humans within a disciplined engineering framework.

Summary

While individual components of Loopforge resemble prior work—ReAct-style reasoning, memory-augmented agents, planner–executor decomposition, skill accumulation, and LLM-based code generation—these approaches are often treated in isolation.

Loopforge contributes:

a unified structure that combines these ideas

a long-memory Architect designed for evolving systems

a deterministic Executor with strict boundaries

a sprint-based protocol grounded in real engineering practice

an explicit, safe human-in-the-loop design

This positions Loopforge as a practical and principled approach for exploring multi-agent software development, distinct from previous research efforts that focus on single-episode problem solving or loosely structured agent behaviors.