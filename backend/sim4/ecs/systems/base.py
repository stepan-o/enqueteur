from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Any, Iterable

import random

from ..world import ECSWorld
from ..commands import (
    ECSCommand,
    ECSCommandKind,
    cmd_set_field,
    cmd_set_component,
    cmd_add_component,
    cmd_remove_component,
    cmd_create_entity,
    cmd_destroy_entity,
)


class SimulationRNG:
    """
    Deterministic RNG wrapper for systems.

    - Wraps a local random.Random instance.
    - All methods must be pure and seedable for replay.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def random(self) -> float:
        """Return a float in [0.0, 1.0)."""
        return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        """Return a float in [a, b]."""
        return self._rng.uniform(a, b)

    # Optional future helpers (randint, choice, etc.) can be added later.


class WorldViewsHandle(Protocol):
    """
    Read-only world views used by systems.

    This sprint defines only the interface placeholders. Concrete implementations
    live in the world/runtime layer. Tests can satisfy this Protocol with simple
    dummy classes.
    """

    # Example placeholders for future expansion:
    # def agents_in_room(self, room_id: int) -> Iterable[int]: ...
    # def room_neighbors(self, room_id: int) -> Iterable[int]: ...
    ...


@dataclass
class SystemContext:
    """
    Context passed into each ECS system's run() method.

    - world: ECSWorld, treated as read-only by systems.
    - dt: delta time for this tick.
    - rng: deterministic RNG handle for this system/tick.
    - views: read-only world views.
    - commands: ECSCommandBuffer where systems enqueue ECS mutations.
    - tick_index: current tick index (int).
    """

    world: ECSWorld
    dt: float
    rng: SimulationRNG
    views: WorldViewsHandle
    commands: "ECSCommandBuffer"
    tick_index: int


@dataclass
class ECSCommandBuffer:
    """
    Deterministic command buffer for ECS systems (S2.4).

    - Assigns a monotonically increasing sequence number (seq) starting at 0.
    - Provides convenience methods to enqueue canonical ECSCommand instances.
    - Exposes a defensive copy of the queued commands via the `commands` property.

    This buffer is layer‑pure within ECS and Rust‑portable (dataclasses, lists, ints).
    """

    _next_seq: int = 0
    _commands: List[ECSCommand] = field(default_factory=list)

    @property
    def commands(self) -> List[ECSCommand]:
        """
        Return a defensive copy of the currently queued commands.
        Mutating the returned list must not affect the internal buffer.
        """
        return list(self._commands)

    # --- API methods mapping to command helpers ---
    def set_component(self, entity_id, component_instance) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_set_component(seq=seq, entity_id=entity_id, component_instance=component_instance)
        self._commands.append(cmd)

    def set_field(self, entity_id, component_type, field_name: str, value) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_set_field(
            seq=seq,
            entity_id=entity_id,
            component_type=component_type,
            field_name=field_name,
            value=value,
        )
        self._commands.append(cmd)

    def add_component(self, entity_id, component_instance) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_add_component(seq=seq, entity_id=entity_id, component_instance=component_instance)
        self._commands.append(cmd)

    def remove_component(self, entity_id, component_type) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_remove_component(seq=seq, entity_id=entity_id, component_type=component_type)
        self._commands.append(cmd)

    def create_entity(self, components: Optional[List[object]] | None = None) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_create_entity(seq=seq, components=components)
        self._commands.append(cmd)

    def destroy_entity(self, entity_id) -> None:
        seq = self._next_seq
        self._next_seq += 1
        cmd = cmd_destroy_entity(seq=seq, entity_id=entity_id)
        self._commands.append(cmd)
