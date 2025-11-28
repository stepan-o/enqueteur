# backend/sim4/world/spawn_initial_world/spawn_initial_world.py

from ..rooms import Room, RoomIdentity
from ..world import WorldContext
from ..prefabs import make_robot
from ..default_layouts import make_default_two_room_layout
from ..assets import AssetIdentity, AssetInstance



def spawn_initial_world(ctx: WorldContext, count: int = 5) -> None:
    """
    Canonical AAA bootstrap for a minimal world:

    - Creates static layout (A <-> B)
    - Creates Room objects with identity
    - Spawns N robots into ECS
    - Places all robots into Room A
    """

    # ---------------------------------------------------------
    # 1) STATIC LAYOUT (identity layer)
    # ---------------------------------------------------------
    layout = make_default_two_room_layout()
    ctx.layout = layout

    # ---------------------------------------------------------
    # 2) CREATE ROOMS from layout
    # ---------------------------------------------------------
    for room_id in layout.rooms:
        ctx.rooms[room_id] = Room(
            room_id=room_id,
            identity=RoomIdentity(
                id=room_id,
                label=f"Room {room_id}",
                kind="default",
            )
        )

    # ---------------------------------------------------------
    # 3) SPAWN ROBOTS INTO ECS + PLACE INTO ROOM "A"
    # ---------------------------------------------------------
    room_a = ctx.rooms["A"]

    for _ in range(count):
        ent = make_robot(ctx.ecs)
        room_a.add(ent)


    # ---------------------------------------------------------
    # 4) SAMPLE ASSETS
    # ---------------------------------------------------------
    chair_id = AssetIdentity(
        id="chair_basic",
        label="Basic Chair",
        category="furniture",
        interactable=True
    )

    chair_instance = AssetInstance(
        asset_id="chair_basic",
        identity=chair_id,
        instance_id="chair_basic_01",
        room="A"
    )

    ctx.register_asset(chair_instance)

    # Finished
    return None
