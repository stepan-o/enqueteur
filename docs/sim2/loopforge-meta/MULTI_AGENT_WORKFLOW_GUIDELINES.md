# 🌀 Loopforge Multi-Agent Workflow Guidelines (v0.2)
_**Rigid Execution. Flexible Architecture.**_

This version replaces the overly rigid “all roles follow schemas” model with the **true separation of powers:**
* **Rigid layer:** Extract → Compare → Execute
* **Flexible layer:** Plan → Reason → Strategize → Course-correct

This is closer to how real engineering organizations operate — planning is flexible, execution is precise.

Below is the corrected operational model.

---

## 1. 🎛 Two-Layer System: Elastic Top, Rigid Base
### Layer 1 — Elastic Cognitive Agents (Architect family)
These are allowed to:
* hold long memory
* reason freely
* propose strategies
* integrate founder instruction
* weave narrative context
* make uncertain calls
* build sprint plans
* negotiate future goals
* adjust the system itself

But still must:
* follow hard constraints when given (e.g. layered architecture rules)
* never write code
* never modify files
* never hallucinate repo content
* maintain consistent handoffs to execution layers

**Agents in this tier:**
Architect, Producers (Showrunner, Puppetteer), Meta-Coordinators, Sages, “Cartographer-Prime” if you ever need one.

---

## Layer 2 — Rigid Execution Agents

Agents in this tier **must be deterministic** (or as close to it as possible):

| Agent            | Behavior                                                         |
|------------------|------------------------------------------------------------------|
| Snapshotter      | Pure extract → snapshot; strict schema                           |
| Drift Analyst    | 	Pure compare → drift report; strict schema                      |
| Executor (Junie) | 	Code edits only within prompt constraints; strict sprint report |
| Validators       | 	run tests, report pass/fail                                     |

These agents do not think — they follow schemas.

---

## 2. 🧠 Architect Role: Structured Freedom

The Architect should be conceptualized as:
* **a planner with access to long-term strategic memory**
* **a constraint-satisfying reasoning engine**
* **a negotiation partner for the human founder**
* **a high-level systems thinker that reflects, anticipates, and adjusts**

Architects operate in a _semi-structured_ mode:

### Architects must follow:
* sprint checklist
* layering rules
* seam boundaries
* safety constraints
* deterministic instructions when explicitly given

### Architects may freely:
* reason in prose
* propose multiple options
* reference long-term goals
* maintain cross-sprint history
* update project “story arc”
* connect distant events and constraints
* suggest new agent roles and workflows
* critique system design
* push back on founder requests when misaligned

### Architects must output structured artifacts only when requested, e.g.:
* SPRINT_PLAN.md
* long-term roadmap
* vision statements
* architecture guidelines

But **their thinking process is open-ended,** unlike the rigid agents.

---

## 3. 🔁 Revised Sprint Workflow — Hybrid Flex + Determinism

Here is the correct architecture, capturing your insight:

```
1. Snapshotter (Rigid)
   - Extracts repo → architecture snapshot
   - Trigger: at the start of new Architect's cycle
 
2. Drift Analyst (Rigid)
   - Compares new snapshot with the start of previous cycle → drift report
   - Trigger: at the start of Architect's cycle, after Snapshotter

3. Architect (Flexible)
   - Thinks freely within role specificaitons (and optional persona)
   - MUST Revise long-term vision and plan, understand current state
   - Talks to Founder to identify the desired direction
   - MUST Produce the cycle spec and plans the sprints
   - MUST Produce sprint prompts for each sprint for Executor that clearly define scope, suggested implementation method, exclusions, safety constraints and acceptance criteria
   - Revises, corrects and approves Executor's execution plan for each sprint

2. Executor (Rigid)
   - Performs code changes deterministically
   - Performs testing according to specified acceptance criteria for each sprint
   - Commits changes to repo
   - Produces structured Sprint Report

5. Architect (Flexible)
   - MUST Revise Executor's completion reports, test results, perform additional validation checks to confirm sprint can be closed
   - MUST Write sprint closure report
   - Courses corrects long-term plan
   - Confirms with Founder that sprint is complete, moves on to next sprint
   - Vision and initial spec revisions are not needed between sprints, unless new information is discovered or provided by Founder
   - Once all sprints are completed, confirms next steps with the founder, completes end-of-cycle documentation 
```

**🧱 The hard rules sit below**  
**🧠 The flexible reasoning sits above**

This “elastic top / rigid base” model is **how we avoid chaos while enabling creativity.**

---

## 4. 📐 Guidelines for Designing Flexible Planning Agents
### 4.1 Flexibility is allowed in reasoning, not in outputs

Planning agents can write paragraphs of reasoning, but must produce formal artifacts when needed.

---

### 4.2 Long memory is a feature, not a bug

Architects should track:
* sprint history
* undone tasks
* risks
* founder preferences
* long-term design direction

Execution agents must not.

---

### 4.3 Architect’s Prose Is Allowed — But Not Handed to Execution

Architect’s thought process can be creative, narrative, multi-step.  
Executor receives only the crisp sprint prompt, not the free reasoning.

This prevents leakage of ambiguity.

---

### 4.4 Architect Must Constrain Executor Rigorously

Even if the Architect is fluid, the Executor’s job is small, crisp, and well-specified.

If Executor hesitates, becomes uncertain, or is struggling to effectively complete the sprint → **Architect failed at scoping.**

---

### 4.5 Architect Can Trigger Introspection Cycles

Architect may decide to:
* run a “meta-sprint”
* rewrite its own guidelines
* create a new agent
* revise the sprint architecture
* adjust the layering Philosophy

Execution agents must never do this.

---

## 5. 🔧 Agent Design Rules (Updated)

For **Execution Agents:**
* strict schema
* single responsibility
* zero reasoning overhead
* deterministic behavior
* no long memory

For **Planning Agents:**
* may reason openly
* must understand and follow constraints
* must output structured artifacts when asked
* must remember the multi-sprint plan and execute it step by step (each step includes multiple interactions with the user)
* must track the cross-sprint state and course-correct the multi-sprint plan as needed
* may reference versions, history, or roadmap
* can interpret and re-interpret drift
* can form hypotheses
* can generate strategy proposals

## 6. 🪶 Closing Note

The earlier model was too rigid because it treated all agents as static tools.

This corrected model reflects the reality of Loopforge:
**✔ We need deterministic execution**  
**✔ We need flexible planning**  
**✔ We must explicitly separate those roles**  
**✔ We must preserve structure where failure would be catastrophic**  
**✔ We must preserve creativity where planning requires intelligence**