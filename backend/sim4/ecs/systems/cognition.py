# cognition.py (Million Dollar Version)
import random
from ..components import Perception, CognitiveState, EmotionalState
from ..components import Transform
from ...ecs.entity import EntityID


def cognition_system(world, dt):
    """
    EntityID-safe cognition system with salience scoring, focus retention,
    and curiosity/confusion dynamics.

    This is the Era V–VI cognition core:
    - Agents build a salience map
    - They maintain focus unless disrupted
    - They adjust cognitive signals over time
    """

    for ent, (p, cog, emo, t) in world.query(
            Perception, CognitiveState, EmotionalState, Transform):

        # ------------------------------------------------------------------
        # 1. If entity sees nothing, lose focus and drift cognitively
        # ------------------------------------------------------------------
        if not p.visible_entities:
            cog.focus_entity = None
            cog.curiosity = max(0.0, cog.curiosity - 0.3 * dt)
            cog.confusion = min(1.0, cog.confusion + 0.2 * dt)
            continue

        # ------------------------------------------------------------------
        # 2. If currently focusing someone, retain focus if still visible
        # ------------------------------------------------------------------
        if cog.focus_entity and cog.focus_entity in p.visible_entities:
            cog.curiosity += 0.15 * dt
            cog.confusion *= 0.97  # reduce confusion if focus is stable
            continue

        # ------------------------------------------------------------------
        # 3. Otherwise, select a new focus target using salience
        # ------------------------------------------------------------------
        target = select_focus_target(ent, p.visible_entities, world)

        cog.focus_entity = target
        cog.curiosity = min(1.0, cog.curiosity + 0.2 * dt)
        cog.confusion *= 0.9


def select_focus_target(ent: EntityID, visible: list, world):
    """
    Select the most salient entity in view.

    This scoring will grow into:
    - spatial proximity
    - emotional gradients
    - relationship history
    - narrative goals
    - role affinity
    - surprise / novelty metrics (Sim6)

    Return: EntityID
    """

    if len(visible) == 1:
        return visible[0]

    # Future: softmax salience model
    # For now: random weighted by (distance + noise)
    scores = []
    _, (t1,) = next(world.query_one(ent, components=[...]))  # placeholder for Sim6; see below

    for other in visible:
        # We only need Transform for spatial heuristics
        t2 = world.get_component(other, Transform)

        # Simple salience: closer entities have higher score
        dx = t2.x - t1.x
        dy = t2.y - t1.y
        dist_sq = dx*dx + dy*dy

        score = 1.0 / (dist_sq + 0.1)  # avoid div-zero
        score += random.uniform(-0.05, 0.05)  # tiny noise

        scores.append((score, other))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[0][1]
