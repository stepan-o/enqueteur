from __future__ import annotations


def qf(x: float, step: float = 1e-4) -> float:
    """Quantize a float to the nearest multiple of `step` deterministically.

    This reduces float drift for export/viewer contracts. Default step=1e-4.
    """
    # Guard against non-floats that are still numeric
    try:
        xf = float(x)
    except Exception:
        return x  # type: ignore[return-value]
    # Quantize via rounding; Python's round is deterministic.
    return round(xf / step) * step
