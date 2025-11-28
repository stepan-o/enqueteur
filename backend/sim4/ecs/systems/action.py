from ..components import IntentState, ActionState, MovementIntent
from ..components import Transform

def action_system(world, dt):
    for ent, (intent, action, move, t) in world.query(
            IntentState, ActionState, MovementIntent, Transform):

        if intent.intent == "approach" and intent.strength > 0:
            action.action = "walk"

            # Move toward focus point (simplified)
            # real version uses target entity Transform
            # this version uses local offset for demo
            move.target_x = t.x + 1.0
            move.target_y = t.y + 0.0
            move.speed = 1.0
        else:
            action.action = "idle"
            move.target_x = None
            move.target_y = None
