# action.py (Million Dollar Version)
import random
from ..components import IntentState, ActionState, MovementIntent, Transform, CognitiveState
from ...ecs.entity import EntityID


def action_system(world, dt):
    """
    Converts intention into actionable movement/plans.
    Supports:
      - approach target
      - avoid target
      - freeze
      - wander
      - investigate
      - idle
    """

    for ent, (intent, action, move, t, cog) in world.query(
            IntentState, ActionState, MovementIntent, Transform, CognitiveState):

        match intent.intent:
            # ----------------------------------------------------------
            case "approach":
                target = cog.focus_entity
                if target:
                    t2 = world.get_component(target, Transform)
                    move.target_entity = target
                    move.target_x = t2.x
                    move.target_y = t2.y
                    move.speed = 1.0 + (0.5 * intent.strength)
                    action.action = "walk"

            # ----------------------------------------------------------
            case "avoid":
                target = cog.focus_entity
                if target:
                    t2 = world.get_component(target, Transform)
                    dx = t.x - t2.x
                    dy = t.y - t2.y
                    # Move directly away
                    move.target_x = t.x + dx
                    move.target_y = t.y + dy
                    move.speed = 1.2
                    action.action = "run"

            # ----------------------------------------------------------
            case "investigate":
                # Similar to approach but with small steps
                target = cog.focus_entity
                if target:
                    t2 = world.get_component(target, Transform)
                    move.target_x = (t.x + t2.x) / 2
                    move.target_y = (t.y + t2.y) / 2
                    move.speed = 0.7
                    action.action = "walk"

            # ----------------------------------------------------------
            case "freeze":
                move.target_x = None
                move.target_y = None
                move.target_entity = None
                action.action = "freeze"

            # ----------------------------------------------------------
            case "wander":
                # Simple random wandering
                move.target_x = t.x + random.uniform(-2, 2)
                move.target_y = t.y + random.uniform(-2, 2)
                move.speed = 0.5
                action.action = "walk"

            # ----------------------------------------------------------
            case "idle":
                move.target_x = None
                move.target_y = None
                move.target_entity = None
                action.action = "idle"
