# movement.py (Million Dollar Version)
from ..components import Transform, MovementIntent, EmotionalState
from ...ecs.entity import EntityID


def movement_system(world, dt):
    """
    Million-dollar movement:
    - support for EntityID targets
    - position updates with speed control
    - tension-driven jitter for visual drama
    """

    for ent, (t, move, emo) in world.query(Transform, MovementIntent, EmotionalState):

        # --------------------------------------------------------------
        # If there's a target entity, update target_x/y automatically
        # --------------------------------------------------------------
        if move.target_entity:
            t2 = world.get_component(move.target_entity, Transform)
            move.target_x = t2.x
            move.target_y = t2.y

        # --------------------------------------------------------------
        # If no target, skip
        # --------------------------------------------------------------
        if move.target_x is None or move.target_y is None:
            continue

        dx = move.target_x - t.x
        dy = move.target_y - t.y
        dist = (dx*dx + dy*dy) ** 0.5

        # --------------------------------------------------------------
        # If close enough, consider the destination reached
        # --------------------------------------------------------------
        if dist < 0.1:
            continue

        # --------------------------------------------------------------
        # Compute movement
        # --------------------------------------------------------------
        nx = dx / dist
        ny = dy / dist

        step = move.speed * dt

        t.x += nx * step
        t.y += ny * step

        # --------------------------------------------------------------
        # Emotional jitter → tension drives micro-movement
        # --------------------------------------------------------------
        if emo.tension > 0.8:
            jitter = (emo.tension - 0.8) * 0.05
            t.x += jitter * (0.5 - random.random())
            t.y += jitter * (0.5 - random.random())
