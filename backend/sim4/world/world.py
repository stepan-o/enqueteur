from dataclasses import dataclass
from typing import Dict, Optional

from .assets import AssetInstance
from .rooms import Room
from ..ecs.scheduler import ECSWorld
from ..ecs.phases import PhaseScheduler
from ..runtime.logger import RuntimeLogger
from .board_layout import BoardLayoutSpec


@dataclass
class WorldIdentity:
    world_name: str = "Loopforge World"
    version: str = "Era-V"
    seed: Optional[int] = None


class WorldContext:
    """
    High-level wrapper for:
      - identity
      - ECS world
      - rooms and world graph
      - logger
      - future metadata (biomes, scripts, narrative seeds)
    """

    def __init__(self, logger: Optional[RuntimeLogger] = None):
        self.identity = WorldIdentity()
        self.ecs = ECSWorld(logger=logger)

        # Room ID → Room instance
        self.rooms: Dict[str, "Room"] = {}

        # World graph (connections, types, costs)
        self.graph = None

        self.layout: BoardLayoutSpec | None = None
        self.assets: Dict[str, AssetInstance] = {}

        self.scheduler = PhaseScheduler()

        # Tick supplied by runtime
        self.tick = 0

    def step(self, dt: float):
        """Forward simulation tick."""
        self.tick += 1
        self.scheduler.run(self.ecs, dt)

    def register_asset(self, inst: AssetInstance):
        self.assets[inst.instance_id] = inst