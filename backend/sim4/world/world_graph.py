from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class GraphNode:
    room: str
    neighbors: List[str] = field(default_factory=list)


@dataclass
class WorldGraph:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)

    def connect(self, a: str, b: str):
        self.nodes.setdefault(a, GraphNode(a)).neighbors.append(b)
        self.nodes.setdefault(b, GraphNode(b)).neighbors.append(a)
