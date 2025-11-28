from ..prefabs import make_robot
from ..rooms import Room, RoomIdentity
from ..world import WorldContext


def spawn_initial_robots(ctx: WorldContext, count: int = 5):
    """
    Initializes a minimal Era V world:
    - Creates two rooms (A, B)
    - Spawns robots and places them in room A
    """

    # ---------------------------------------------------------
    # Create rooms with full identity metadata
    # ---------------------------------------------------------
    ctx.rooms["A"] = Room(
        identity=RoomIdentity(
            id="A",
            label="Lab Room",
            kind="default"
        )
    )

    ctx.rooms["B"] = Room(
        identity=RoomIdentity(
            id="B",
            label="Hallway",
            kind="corridor"
        )
    )

    # ---------------------------------------------------------
    # Spawn robots into Room A
    # ---------------------------------------------------------
    for _ in range(count):
        ent = make_robot(ctx.ecs)   # ECS entity creation
        ctx.rooms["A"].add(ent)     # Assign to room A
