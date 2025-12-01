from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, Tuple

from .entity import EntityID


@dataclass(frozen=True)
class QuerySignature:
    read: Tuple[type, ...]
    write: Tuple[type, ...]
    optional: Tuple[type, ...] = ()
    without: Tuple[type, ...] = ()


@dataclass(frozen=True)
class RowView:
    """
    Deterministic row view returned by ECSWorld.query.

    - entity: the EntityID.
    - components: positional tuple of component instances in a canonical order.
      For now: (all read comps) + (all write comps) + (all optional comps).
    """
    entity: EntityID
    components: Tuple[object, ...]


class QueryResult:
    """
    Deterministic iterable of RowView instances.
    """

    def __init__(self, rows: Sequence[RowView]) -> None:
        self._rows = tuple(rows)

    def __iter__(self) -> Iterator[RowView]:
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)
