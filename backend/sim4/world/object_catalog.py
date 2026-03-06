"""Canonical object class catalog (data-only, Rust-friendly)."""

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
    "LOBBY_DESK": ObjectClassSpec(
        class_code="LOBBY_DESK",
        label="Lobby Desk",
        base_output=0.3,
        durability_max=1.0,
        efficiency_base=0.9,
        wear_rate_idle=0.00004,
        wear_rate_load=0.0001,
        efficiency_decay_idle=0.00002,
        efficiency_decay_load=0.00005,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.1,
        overdrive_wear_multiplier=1.8,
    ),
    "DISPLAY_CASE": ObjectClassSpec(
        class_code="DISPLAY_CASE",
        label="Display Case",
        base_output=0.5,
        durability_max=1.0,
        efficiency_base=0.95,
        wear_rate_idle=0.00003,
        wear_rate_load=0.00008,
        efficiency_decay_idle=0.00002,
        efficiency_decay_load=0.00005,
        efficiency_recovery_idle=0.00004,
        overdrive_multiplier=1.05,
        overdrive_wear_multiplier=1.5,
    ),
    "SECURITY_TERMINAL": ObjectClassSpec(
        class_code="SECURITY_TERMINAL",
        label="Security Terminal",
        base_output=1.2,
        durability_max=1.0,
        efficiency_base=0.88,
        wear_rate_idle=0.00005,
        wear_rate_load=0.00016,
        efficiency_decay_idle=0.00003,
        efficiency_decay_load=0.00009,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.2,
        overdrive_wear_multiplier=2.0,
    ),
    "DELIVERY_CART": ObjectClassSpec(
        class_code="DELIVERY_CART",
        label="Delivery Cart",
        base_output=0.7,
        durability_max=1.0,
        efficiency_base=0.86,
        wear_rate_idle=0.00005,
        wear_rate_load=0.00014,
        efficiency_decay_idle=0.00003,
        efficiency_decay_load=0.00008,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.25,
        overdrive_wear_multiplier=2.1,
    ),
    "CAFE_COUNTER": ObjectClassSpec(
        class_code="CAFE_COUNTER",
        label="Cafe Counter",
        base_output=0.9,
        durability_max=1.0,
        efficiency_base=0.9,
        wear_rate_idle=0.00004,
        wear_rate_load=0.00012,
        efficiency_decay_idle=0.00002,
        efficiency_decay_load=0.00007,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.2,
        overdrive_wear_multiplier=2.0,
    ),
    "RECEIPT_PRINTER": ObjectClassSpec(
        class_code="RECEIPT_PRINTER",
        label="Receipt Printer",
        base_output=1.0,
        durability_max=1.0,
        efficiency_base=0.85,
        wear_rate_idle=0.00004,
        wear_rate_load=0.00012,
        efficiency_decay_idle=0.00003,
        efficiency_decay_load=0.00008,
        efficiency_recovery_idle=0.00005,
        overdrive_multiplier=1.3,
        overdrive_wear_multiplier=2.2,
    ),
    "BULLETIN_BOARD": ObjectClassSpec(
        class_code="BULLETIN_BOARD",
        label="Bulletin Board",
        base_output=0.4,
        durability_max=1.0,
        efficiency_base=0.92,
        wear_rate_idle=0.00002,
        wear_rate_load=0.00006,
        efficiency_decay_idle=0.00001,
        efficiency_decay_load=0.00003,
        efficiency_recovery_idle=0.00003,
        overdrive_multiplier=1.05,
        overdrive_wear_multiplier=1.4,
    ),
    "BENCH": ObjectClassSpec(
        class_code="BENCH",
        label="Bench",
        base_output=0.2,
        durability_max=1.0,
        efficiency_base=0.95,
        wear_rate_idle=0.00001,
        wear_rate_load=0.00003,
        efficiency_decay_idle=0.00001,
        efficiency_decay_load=0.00002,
        efficiency_recovery_idle=0.00002,
        overdrive_multiplier=1.0,
        overdrive_wear_multiplier=1.1,
    ),
}


DEFAULT_OBJECT_CLASS_SPEC = ObjectClassSpec(
    class_code="DEFAULT",
    label="Generic Object",
    base_output=0.6,
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
