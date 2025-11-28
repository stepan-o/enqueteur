# perception.py
import math
import random
from ..components import Transform, Perception, VisualProps
from ...ecs.entity import EntityID

PERCEPTION_RADIUS = 8.0
PERCEPTION_RADIUS_SQ = PERCEPTION_RADIUS * PERCEPTION_RADIUS
NOISE_STDDEV = 0.05        # tiny noise for realism


def perception_system(world, dt):
    """
    Million-Dollar Perception System:
    ---------------------------------
    - EntityID-safe
    - range-based detection
    - future-ready for FOV cones, occlusion, multi-sensor perception
    - salience metadata for downstream cognition/intention
    - deterministic ordering for replay + Godot visualization
    """

    # Cache all transforms once per frame (massively faster)
    transforms = {
        ent: t for ent, (t,) in world.query(Transform)
    }

    # ------------------------------------------------------------------
    # Main perception pass
    # ------------------------------------------------------------------
    for ent, (t1, p) in world.query(Transform, Perception):
        p.visible_entities.clear()

        # ------------------------------------------------------------------
        # Scan all transforms (in real engine this would use spatial partitioning)
        # ------------------------------------------------------------------
        for other, t2 in transforms.items():
            if other == ent:
                continue

            dx = t2.x - t1.x
            dy = t2.y - t1.y
            dist_sq = dx*dx + dy*dy

            if dist_sq > PERCEPTION_RADIUS_SQ:
                continue

            # Add with EntityID reference
            p.visible_entities.append(other)

        # ------------------------------------------------------------------
        # Sort by salience (distance + noise)
        # ------------------------------------------------------------------
        if p.visible_entities:
            p.visible_entities = sort_by_salience(ent, t1, p.visible_entities, transforms)


def sort_by_salience(ent: EntityID, t1: Transform, visibles, transforms):
    """
    Salience = how important something is to perceive.
    This will grow into:
    - emotional relevance
    - social affinity/hostility
    - surprise detectors
    - novelty detection
    - narrative role awareness
    """

    scored = []
    for other in visibles:
        t2 = transforms[other]

        dx = t2.x - t1.x
        dy = t2.y - t1.y
        dist_sq = dx*dx + dy*dy

        # Inverse distance weighting; add tiny noise for realism
        score = (1.0 / (dist_sq + 0.01)) + random.gauss(0, NOISE_STDDEV)

        # Compute angle for future FOV (Sim6)
        angle = math.atan2(dy, dx)

        scored.append((score, angle, other))

    # Sort by descending score → most salient first
    scored.sort(reverse=True, key=lambda x: x[0])

    # For now return only ordered EntityIDs
    return [triple[2] for triple in scored]
