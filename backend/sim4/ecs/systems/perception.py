from ..components import Transform, Perception

PERCEPTION_RADIUS = 8.0

def perception_system(world, dt):
    # Query for all agents with Transform + Perception
    for ent, (t1, p) in world.query(Transform, Perception):
        p.visible_entities.clear()

        for other, (t2,) in world.query(Transform):
            if other == ent:
                continue

            dx = t2.x - t1.x
            dy = t2.y - t1.y
            if dx*dx + dy*dy <= PERCEPTION_RADIUS * PERCEPTION_RADIUS:
                p.visible_entities.append(other)
