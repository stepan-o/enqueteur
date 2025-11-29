# sim4/runtime/event_bus.py
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# EVENT MODELS
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """
    Core event object.
    - name: identifier ("emotion.changed", "agent.spoke", etc.)
    - payload: arbitrary data
    - ent: optional entity ID (Agent context)
    - tick: simulation tick index (filled in by EventBus)
    """
    name: str
    payload: Any
    ent: Optional[int] = None
    tick: Optional[int] = None


# ---------------------------------------------------------------------------
# EVENT BUS
# ---------------------------------------------------------------------------

class EventBus:
    """
    High-performance synchronous + deferred event bus.

    FEATURES
    --------
    ✔ emit()              : immediate dispatch
    ✔ emit_deferred()     : queue → flush_deferred()
    ✔ subscribe(name)     : subscribe to specific event
    ✔ subscribe_all()     : wildcard '*' listener
    ✔ tick-index tracking : crucial for replay + debugging
    ✔ tracing hooks       : for Godot overlay + writer
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._wildcard_subs: List[Callable[[Event], None]] = []

        self._queue: List[Event] = []
        self._deferred: List[Event] = []

        # debug tracing
        self.last_emitted: List[Event] = []

        # filled in by world each tick
        self.current_tick: int = 0

    # ----------------------------------------------------------------------
    # SUBSCRIPTIONS
    # ----------------------------------------------------------------------

    def subscribe(self, event_name: str, callback: Callable[[Event], None]):
        """ Subscribe to a specific event name. """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def subscribe_all(self, callback: Callable[[Event], None]):
        """ Subscribe to ALL events ('wildcard'). """
        self._wildcard_subs.append(callback)

    # ----------------------------------------------------------------------
    # EMIT
    # ----------------------------------------------------------------------

    def emit(self, name: str, payload: Any = None, ent: Optional[int] = None):
        """
        Emit an event IMMEDIATELY during tick execution.
        Used by systems (emotion, cognition, social…)
        """
        e = Event(name=name, payload=payload, ent=ent, tick=self.current_tick)
        self._dispatch(e)

    def emit_deferred(self, name: str, payload: Any = None, ent: Optional[int] = None):
        """
        Emit an event AFTER all systems run.
        Collected and dispatched by world at end of tick.
        """
        e = Event(name=name, payload=payload, ent=ent, tick=self.current_tick)
        self._deferred.append(e)

    # ----------------------------------------------------------------------
    # INTERNAL DISPATCH
    # ----------------------------------------------------------------------

    def _dispatch(self, event: Event):
        """
        Deliver an event to:
            - direct subscribers
            - wildcard subscribers
        """
        self.last_emitted.append(event)

        # direct subs
        if event.name in self._subscribers:
            for cb in self._subscribers[event.name]:
                cb(event)

        # wildcard subs
        for cb in self._wildcard_subs:
            cb(event)

    # ----------------------------------------------------------------------
    # FLUSH DEFERRED
    # ----------------------------------------------------------------------

    def flush_deferred(self):
        """
        Called by the world at the end of each tick.
        Moves deferred → queue and dispatches all.
        """
        if not self._deferred:
            return

        for e in self._deferred:
            self._dispatch(e)

        self._deferred.clear()
