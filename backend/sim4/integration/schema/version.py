from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationSchemaVersion:
    """Version tag for viewer-facing integration schemas.

    - Start at 1.0.0
    - Pure metadata; no behavior
    - Rust-portable (ints only)
    """

    major: int
    minor: int
    patch: int
