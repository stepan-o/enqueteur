from dataclasses import dataclass, field
from typing import List, Dict, Optional
from ..ecs.entity import EntityID


# ---------------------------------------------------------------------------
# 1. Spatial Components
# ---------------------------------------------------------------------------

@dataclass
class Transform:
    x: float = 0.0
    y: float = 0.0
    rot: float = 0.0


@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class MovementIntent:
    """
    Move toward target entity or target coords.
    FULL EntityID support.
    Godot gets pure coords in snapshot builder.
    """
    target_entity: Optional[EntityID] = None
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    speed: float = 1.0


# ---------------------------------------------------------------------------
# 2. Perception + Cognition
# ---------------------------------------------------------------------------

@dataclass
class Perception:
    """
    Now stores EntityID directly.
    Systems always use EntityID.
    Snapshot=>Godot converts to ints.
    """
    visible_entities: List[EntityID] = field(default_factory=list)
    noises: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


@dataclass
class Memory:
    """
    Memory keys may reference entities.
    Upgrade: keys become tuples ("tag", EntityID)
    """
    tokens: Dict[str, float] = field(default_factory=dict)


@dataclass
class CognitiveState:
    focus_entity: Optional[EntityID] = None
    curiosity: float = 0.0
    confusion: float = 0.0
    aggression: float = 0.0


# ---------------------------------------------------------------------------
# 3. Emotion / Narrative
# ---------------------------------------------------------------------------

@dataclass
class EmotionalState:
    valence: float = 0.0
    arousal: float = 0.0
    tension: float = 0.0


@dataclass
class SocialState:
    """
    Entity relationships now keyed by EntityID.
    """
    relationships: Dict[EntityID, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 4. Intent / Action
# ---------------------------------------------------------------------------

@dataclass
class IntentState:
    intent: str = "idle"
    strength: float = 0.0


@dataclass
class ActionState:
    action: str = "none"
    progress: float = 0.0


# ---------------------------------------------------------------------------
# 5. Render Hooks (Godot)
# ---------------------------------------------------------------------------

@dataclass
class VisualProps:
    color: str = "#FFFFFF"
    scale: float = 1.0
    visible: bool = True


@dataclass
class AgentTag:
    role: str = "robot"
