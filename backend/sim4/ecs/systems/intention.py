from ..components import CognitiveState, IntentState

def intention_system(world, dt):
    for ent, (cog, intent) in world.query(CognitiveState, IntentState):
        if cog.focus_entity is not None:
            intent.intent = "approach"
            intent.strength = min(1.0, cog.curiosity)
        else:
            intent.intent = "idle"
            intent.strength = 0.0
