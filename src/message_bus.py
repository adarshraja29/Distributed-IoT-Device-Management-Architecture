"""
Distributed IoT Device Management Architecture - Communication Layer (Local Message Bus)
Provides a clean publish-subscribe interface for local simulation without external brokers.
"""

import fnmatch
import json
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Dict, List, Any, Optional


class MessageBusInterface:
    """Abstract interface defining required messaging methods for interchangeable bus adapters."""

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def subscribe(self, topic_pattern: str, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        raise NotImplementedError

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError

    def get_mode_name(self) -> str:
        raise NotImplementedError


class LocalMessageBus(MessageBusInterface):
    """
    Local in-memory publish/subscribe message bus with wildcard topic matching
    and bounded message history buffer for diagnostics.
    """

    def __init__(self, max_history: int = 100):
        self._handlers: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        self._history: deque = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._is_running = True

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """
        Publishes a message to a topic, stores it in the debug activity buffer,
        and synchronously delivers it to all matching subscribers.
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "topic": topic,
            "payload": payload,
            "timestamp": now_iso,
            "source": "LocalSimulatorBus"
        }

        with self._lock:
            self._history.appendleft(entry)
            handlers_to_invoke = []
            for pattern, funcs in self._handlers.items():
                if self._topic_matches(pattern, topic):
                    handlers_to_invoke.extend(funcs)

        for handler in handlers_to_invoke:
            try:
                handler(topic, payload)
            except Exception as e:
                # Log or swallow safely to avoid crashing bus callers
                print(f"[LocalMessageBus] Handler error on topic {topic}: {e}")

        return True

    def subscribe(self, topic_pattern: str, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """Subscribes a callable handler to a topic or topic pattern (e.g. 'iot/devices/*/telemetry')."""
        with self._lock:
            if topic_pattern not in self._handlers:
                self._handlers[topic_pattern] = []
            if handler not in self._handlers[topic_pattern]:
                self._handlers[topic_pattern].append(handler)

    def unsubscribe(self, topic_pattern: str, handler: Optional[Callable] = None) -> None:
        """Removes a handler or all handlers for a topic pattern."""
        with self._lock:
            if topic_pattern in self._handlers:
                if handler:
                    self._handlers[topic_pattern] = [h for h in self._handlers[topic_pattern] if h != handler]
                else:
                    del self._handlers[topic_pattern]

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent messages up to the specified limit."""
        with self._lock:
            return list(self._history)[:limit]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def is_connected(self) -> bool:
        return self._is_running

    def get_mode_name(self) -> str:
        return "Local Simulator (Zero-Config)"

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """
        Matches MQTT-style wildcard topics or fnmatch patterns:
        e.g., 'iot/devices/+/telemetry' -> '+' matches single level, '#' matches multiple levels.
        """
        if pattern == topic or pattern == "#":
            return True
        # Convert MQTT wildcards to fnmatch if present
        fn_pattern = pattern.replace("+", "*").replace("#", "*")
        return fnmatch.fnmatch(topic, fn_pattern)


# Global default instance
_default_bus = LocalMessageBus()


def get_default_message_bus() -> LocalMessageBus:
    """Returns the singleton local simulator message bus."""
    global _default_bus
    return _default_bus
