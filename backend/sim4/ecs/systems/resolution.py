from ..components import Perception

def resolution_system(world, dt):
    for ent, (p,) in world.query(Perception):
        p.noises.clear()
        p.messages.clear()
