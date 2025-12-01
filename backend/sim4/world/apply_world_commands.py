"""
Apply world commands — deterministic world-layer mutation and event emission.

This module defines the canonical entry point for applying WorldCommand batches
to a WorldContext and emitting corresponding WorldEvent instances.

Scope (Sub‑Sprint 5.3):
- Deterministically sort by command.seq and apply in order (stable sort).
- Handle core commands: SET_AGENT_ROOM, SPAWN_ITEM, OPEN_DOOR.
- Optionally handle CLOSE_DOOR and DESPAWN_ITEM if available.

Notes:
- Pure world-layer implementation (SOP-100): imports only world.* modules.
- Deterministic and Rust-portable (SOP-200): uses only primitive datatypes.
- Errors from WorldContext helpers propagate; no events are emitted for failed
  commands.

TODO[WORLD-CMDS]: Extend dispatcher when additional command kinds are finalized
in SOTs (e.g., SET_ITEM_STATE, portal navigation constraints, etc.).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import List

from .context import WorldContext, ItemRecord
from .commands import WorldCommand, WorldCommandKind
from .events import WorldEvent, WorldEventKind


def apply_world_commands(
    world_ctx: WorldContext,
    commands: Iterable[WorldCommand],
) -> List[WorldEvent]:
    """Apply a batch of WorldCommand to the given WorldContext.

    - Commands are applied deterministically by sorting ascending on `seq`.
    - The world_ctx is mutated in place via its public helper methods.
    - Returns a list of WorldEvent instances describing observable outcomes,
      in the same order as applied commands.

    Raises:
        Propagates ValueError/KeyError from WorldContext operations.
        NotImplementedError for unknown/unhandled command kinds.
    """

    cmds = list(commands)
    # Deterministic stable sort by seq; Python's sort is stable for tie-breakers.
    cmds.sort(key=lambda c: c.seq)

    events: List[WorldEvent] = []

    for cmd in cmds:
        kind = cmd.kind

        if kind is WorldCommandKind.SET_AGENT_ROOM:
            if cmd.agent_id is None or cmd.room_id is None:
                raise ValueError("SET_AGENT_ROOM requires agent_id and room_id")
            agent_id = cmd.agent_id
            new_room = cmd.room_id
            prev_room = world_ctx.get_agent_room(agent_id)
            # Enforce strict semantics: agent must already be registered
            world_ctx.move_agent(agent_id=agent_id, new_room_id=new_room)
            events.append(
                WorldEvent(
                    kind=WorldEventKind.AGENT_MOVED_ROOM,
                    agent_id=agent_id,
                    previous_room_id=prev_room,
                    room_id=new_room,
                )
            )

        elif kind is WorldCommandKind.SPAWN_ITEM:
            if cmd.item_id is None or cmd.room_id is None:
                raise ValueError("SPAWN_ITEM requires item_id and room_id")
            item = ItemRecord(id=cmd.item_id, room_id=cmd.room_id)
            world_ctx.register_item(item)
            events.append(
                WorldEvent(
                    kind=WorldEventKind.ITEM_SPAWNED,
                    item_id=item.id,
                    room_id=item.room_id,
                )
            )

        elif kind is WorldCommandKind.OPEN_DOOR:
            if cmd.door_id is None:
                raise ValueError("OPEN_DOOR requires door_id")
            world_ctx.set_door_open(door_id=cmd.door_id, is_open=True)
            events.append(
                WorldEvent(
                    kind=WorldEventKind.DOOR_OPENED,
                    door_id=cmd.door_id,
                )
            )

        elif kind is WorldCommandKind.CLOSE_DOOR:
            # Optional extension: handle CLOSE_DOOR if present in the enum
            if cmd.door_id is None:
                raise ValueError("CLOSE_DOOR requires door_id")
            world_ctx.set_door_open(door_id=cmd.door_id, is_open=False)
            events.append(
                WorldEvent(
                    kind=WorldEventKind.DOOR_CLOSED,
                    door_id=cmd.door_id,
                )
            )

        elif kind is WorldCommandKind.DESPAWN_ITEM:
            # Optional extension: unplace item (keep registry minimal in 5.3)
            if cmd.item_id is None:
                raise ValueError("DESPAWN_ITEM requires item_id")
            # Move item to None (unplaced). We keep the item record for now;
            # full removal can be decided in future SOT updates.
            world_ctx.move_item(item_id=cmd.item_id, new_room_id=None)
            events.append(
                WorldEvent(
                    kind=WorldEventKind.ITEM_DESPAWNED,
                    item_id=cmd.item_id,
                )
            )

        else:
            raise NotImplementedError(f"Unhandled WorldCommand kind: {kind}")

    return events
