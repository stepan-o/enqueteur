# sim4/runtime/logger.py
import time
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

# Optional color output (terminal pretty mode)
try:
    from colorama import Fore, Style
    COLOR = True
except ImportError:
    COLOR = False


# ---------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------

@dataclass
class LogRecord:
    tick: int
    event: str
    message: str
    payload: Optional[Dict[str, Any]] = None
    ts: float = 0.0  # wall-clock timestamp

    def to_dict(self):
        d = asdict(self)
        d["ts"] = round(self.ts, 6)
        return d


@dataclass
class SystemTiming:
    system: str
    duration_ms: float


# ---------------------------------------------------------
# LOGGER
# ---------------------------------------------------------

class RuntimeLogger:
    """
    A high-performance logger designed for ECS simulations.

    Features:
      - Structured tick-by-tick logs
      - System-level profiling
      - Supports text mode + JSON mode
      - Zero overhead when disabled
      - Global singleton recommended
    """

    def __init__(self, enabled: bool = True, json_mode: bool = False):
        self.enabled = enabled
        self.json_mode = json_mode

        self.records: List[LogRecord] = []
        self.timings: List[SystemTiming] = []

    # -----------------------------------------------------
    # Core Logging
    # -----------------------------------------------------
    def log(self, tick: int, event: str, message: str, payload=None):
        if not self.enabled:
            return

        rec = LogRecord(
            tick=tick,
            event=event,
            message=message,
            payload=payload,
            ts=time.time(),
        )
        self.records.append(rec)

        if not self.json_mode:
            self._print_pretty(rec)

    def _print_pretty(self, rec: LogRecord):
        if not COLOR:
            print(f"[{rec.tick}] {rec.event}: {rec.message}")
            return

        color = {
            "INFO": Fore.GREEN,
            "WARN": Fore.YELLOW,
            "ERROR": Fore.RED,
            "SYSTEM": Fore.CYAN,
            "ENTITY": Fore.MAGENTA,
        }.get(rec.event.upper(), Fore.WHITE)

        msg = f"{color}[{rec.tick}] {rec.event}{Style.RESET_ALL}: {rec.message}"
        print(msg)

    # -----------------------------------------------------
    # System Profiling
    # -----------------------------------------------------
    def profile(self, system_name: str, dt_start: float, dt_end: float):
        if not self.enabled:
            return

        duration_ms = (dt_end - dt_start) * 1000.0
        self.timings.append(SystemTiming(system=system_name, duration_ms=duration_ms))

    def flush_timings(self):
        """Return all collected timings and clear buffer."""
        out = [asdict(t) for t in self.timings]
        self.timings.clear()
        return out

    # -----------------------------------------------------
    # Export / Persistence
    # -----------------------------------------------------
    def export_json(self):
        """Export ALL logs as a JSON array."""
        return json.dumps([rec.to_dict() for rec in self.records],
                          ensure_ascii=False, indent=2)

    def clear(self):
        self.records.clear()
        self.timings.clear()
