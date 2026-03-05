from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Tuple, Dict, List


@dataclass(frozen=True)
class ArchetypeSignature:
    """
    Hashable, deterministic representation of an entity's component set.

    - Uses a normalized, sorted ascending tuple of unique integer type codes.
    - Rust-portable: only stores primitives (tuple[int, ...]).
    - Equality and hashing depend solely on the normalized tuple.
    """

    component_type_codes: Tuple[int, ...]

    @classmethod
    def from_type_codes(cls, type_codes: Iterable[int]) -> "ArchetypeSignature":
        """
        Build a normalized signature from an iterable of type codes.

        Normalization:
        - Cast elements to int.
        - Remove duplicates.
        - Sort ascending and store as a tuple[int, ...].
        """
        unique = {int(tc) for tc in type_codes}
        normalized = tuple(sorted(unique))
        return cls(component_type_codes=normalized)

    def with_component(self, type_code: int) -> "ArchetypeSignature":
        """
        Return a new signature with the given component type code included.

        - If already present, returns an equal signature (may be same instance).
        - Keeps sorted ascending order; no duplicates.
        """
        tc = int(type_code)
        if tc in self.component_type_codes:
            return self  # already present; immutable so safe to return self
        # Insert maintaining sorted order without resorting whole list if possible
        # Simpler and deterministic: create new tuple from set and sort.
        new_tuple = tuple(sorted((*self.component_type_codes, tc)))
        return ArchetypeSignature(new_tuple)

    def without_component(self, type_code: int) -> "ArchetypeSignature":
        """
        Return a new signature without the given component type code.

        - If absent, returns an equal signature (may be same instance).
        """
        tc = int(type_code)
        if tc not in self.component_type_codes:
            return self
        new_tuple = tuple(c for c in self.component_type_codes if c != tc)
        return ArchetypeSignature(new_tuple)


@dataclass
class ArchetypeRegistry:
    """
    Deterministic registry mapping ArchetypeSignature <-> small integer IDs.

    - IDs are assigned in insertion order of previously unseen signatures.
    - ID base: 0-based (first registered signature gets ID 0). This is
      arbitrary but consistent; document and keep consistent across usage.
    - Rust-portable: dict and list of signatures only.
    """

    _signature_to_id: Dict[ArchetypeSignature, int] = field(default_factory=dict)
    _id_to_signature: List[ArchetypeSignature] = field(default_factory=list)

    def get_or_register(self, signature: ArchetypeSignature) -> int:
        """
        Return existing ID for signature, or register a new one deterministically.
        """
        if signature in self._signature_to_id:
            return self._signature_to_id[signature]
        new_id = len(self._id_to_signature)  # 0-based
        self._signature_to_id[signature] = new_id
        self._id_to_signature.append(signature)
        return new_id

    def get_signature(self, archetype_id: int) -> ArchetypeSignature:
        """
        Return the signature for the given ID.

        Raises IndexError with a clear message if out of range.
        """
        try:
            return self._id_to_signature[archetype_id]
        except IndexError as e:
            raise IndexError(f"Archetype ID out of range: {archetype_id}") from e

    def ensure_signature(self, type_codes: Iterable[int]) -> int:
        """
        Convenience helper: normalize from type codes and register/get ID.
        """
        sig = ArchetypeSignature.from_type_codes(type_codes)
        return self.get_or_register(sig)
