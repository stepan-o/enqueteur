from ..ecs.components import (
    Transform, Velocity, MovementIntent,
    Perception, Memory, CognitiveState,
    EmotionalState, SocialState,
    IntentState, ActionState,
    VisualProps, AgentTag
)

def make_robot(ecs_world):
    return ecs_world.create_entity(
        Transform(),
        Velocity(),
        MovementIntent(),
        Perception(),
        Memory(),
        CognitiveState(),
        EmotionalState(),
        SocialState(),
        IntentState(),
        ActionState(),
        VisualProps(color="#44CCFF"),
        AgentTag(role="robot"),
    )
