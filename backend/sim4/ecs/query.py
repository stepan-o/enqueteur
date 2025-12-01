from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, Tuple

from .entity import EntityID


@dataclass(frozen=True)
class QuerySignature:
    """
    Canonical query descriptor for ECSWorld.query.

    - read: required component types; matched entities must have all.
    - write: required component types; matched entities must have all.
    - optional: optional component types; rows include a slot for each in
      the components tuple, using None when the entity lacks that component.
    - without: exclusion component types; entities possessing any of these
      are excluded from the result.
    """
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
      Layout: (all read comps) + (all write comps) + (all optional comps).
      For optional components, if the entity does not have the component,
      the corresponding slot is None. The order within each group matches
      the order in QuerySignature.
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
