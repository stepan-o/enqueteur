"""Canonical object class catalog (data-only, Rust-friendly).

Defines class-level simulation defaults for static objects/workstations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ObjectClassSpec:
    class_code: str
    label: str
    base_output: float
    durability_max: float
    efficiency_base: float
    wear_rate_idle: float
    wear_rate_load: float
    efficiency_decay_idle: float
    efficiency_decay_load: float
    efficiency_recovery_idle: float
    overdrive_multiplier: float
    overdrive_wear_multiplier: float


OBJECT_CLASS_SPECS: Dict[str, ObjectClassSpec] = {
    "RIBBON_SPOOL": ObjectClassSpec(
        class_code="RIBBON_SPOOL",
        label="Ribbon Spool",
        base_output=0.8,
        durability_max=1.0,
        efficiency_base=0.9,
        wear_rate_idle=0.00005,
        wear_rate_load=0.00015,
        efficiency_decay_idle=0.00003,
        efficiency_decay_load=0.00008,
        efficiency_recovery_idle=0.00006,
        overdrive_multiplier=1.2,
        overdrive_wear_multiplier=2.0,
    ),
    "WEAVING_MACHINE": ObjectClassSpec(
        class_code="WEAVING_MACHINE",
        label="Weaving Machine",
        base_output=2.5,
        durability_max=1.0,
        efficiency_base=0.95,
        wear_rate_idle=0.00008,
        wear_rate_load=0.00025,
        efficiency_decay_idle=0.00005,
        efficiency_decay_load=0.00012,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.4,
        overdrive_wear_multiplier=2.4,
    ),
}


DEFAULT_OBJECT_CLASS_SPEC = ObjectClassSpec(
    class_code="DEFAULT",
    label="Generic Object",
    base_output=1.0,
    durability_max=1.0,
    efficiency_base=0.85,
    wear_rate_idle=0.00005,
    wear_rate_load=0.0002,
    efficiency_decay_idle=0.00005,
    efficiency_decay_load=0.0001,
    efficiency_recovery_idle=0.00005,
    overdrive_multiplier=1.25,
    overdrive_wear_multiplier=2.0,
)


def get_object_class_spec(class_code: str) -> ObjectClassSpec:
    return OBJECT_CLASS_SPECS.get(class_code, DEFAULT_OBJECT_CLASS_SPEC)


__all__ = ["ObjectClassSpec", "OBJECT_CLASS_SPECS", "get_object_class_spec"]
