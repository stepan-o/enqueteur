# 🔵 SOT #1 — ECS LAYER (REVISED, FINAL)
_**Canonical Source of Truth for Entity–Component–System Storage & Execution**_

**Status:** Era IV–VI
**Owner:** Loopforge Architecture Council (The Topologist lineage)

---

## 1. Purpose
The ECS Layer is responsible ONLY for agent-internal state and intra-agent transformations.

It **does NOT** know about:
* rooms
* world graph
* assets
* world events
* narrative
* snapshots
* episodes
* rendering
* UI/Viz

ECS = **mind + body mechanics**
World = **environment + physics + structure**

Clear separation of concerns.

---

## 2. ECSWorld Responsibilities
**ECSWorld MUST provide:**
### 2.1 Entity Lifecycle
```text
create_entity(**components)
destroy_entity(ent)
entity_exists(ent)
```

---

### 2.2 Component Access
```text
get_component(ent, Type)
get_component_safe(ent, Type)
set_component(ent, Type, value)
add_component(ent, Type, value)
remove_component(ent, Type)
```

---

### 2.3 Queries
```text
query(TypeA, TypeB, ...)
```

---

Deterministic, structure-of-arrays, archetype-based.

---

### 2.4 Archetype Management
Automatically moves entities across archetypes when components change.

---

### 2.5 System Execution
NONE.  
System execution is handled by **PhaseScheduler** inside WorldContext.

---

## 3. Storage Model
_**Archetype = unique sorted tuple of component types**_

Each archetype contains:
```text
entities[]: [EntityID, ...]
components[ComponentType]: [value, ...]
entity_to_row: {EntityID → row_index}
```

Mutation model:
* O(1) add
* O(1) remove via swap-delete
* contiguous arrays
* deterministic iteration

---

## 4. Component Rules
Components:
* are dataclasses
* contain only POD-like data
* may reference other EntityIDs
* contain **no logic**
* must serialize to JSON-friendly structures
* must not depend on WorldContext

**Identity is type-level, not instance-level.**

---

## 5. System Rules
Systems are pure transformations:
```
def system(world, dt):
    mutate components exclusively
```

**Systems are grouped by Phase:**
```text
perception
emotion
cognition
intention
action
movement
narrative
identity
resolution
```

Systems may:  
✓ mutate components  
✓ add/remove components (buffered)  
✓ read ECSWorld data  
✓ request world-level info via callbacks (visibility, room id)  
✗ NOT modify rooms  
✗ NOT modify assets  
✗ NOT perform world snapshots  
✗ NOT talk to Godot

---

## 6. Determinism

ECS **must:**
* produce identical sequences for identical seeds
* remain stable under multi-era evolution
* be Rust-portable

---

## 7. Constraints
**Forbidden inside ECS:**
* global state
* I/O
* randomness without injected RNG
* room-level logic
* narrative
* world graph access
* asset manipulation

ECS is **pure agent state + transformations.**