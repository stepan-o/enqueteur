from ..components import Transform, MovementIntent

def movement_system(world, dt):
    for ent, (t, move) in world.query(Transform, MovementIntent):
        if move.target_x is None:
            continue

        dx = move.target_x - t.x
        dy = move.target_y - t.y
        dist = (dx*dx + dy*dy) ** 0.5

        if dist < 0.05:
            continue

        step = move.speed * dt / max(0.0001, dist)
        t.x += dx * step
        t.y += dy * step
