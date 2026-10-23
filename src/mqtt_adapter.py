"""
Distributed IoT Device Management Architecture - Optional MQTT Adapter
Implements MessageBusInterface over an actual MQTT broker using paho-mqtt.
Gracefully handles connection failures, timeouts, and missing broker instances.
"""

import json
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Dict, List, Any, Optional

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

from src.message_bus import MessageBusInterface


class MQTTAdapter(MessageBusInterface):
    """
    MQTT client adapter connecting to a broker such as Eclipse Mosquitto.
    Implements publish/subscribe matching the MessageBusInterface.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, client_id: str = "iot_dss_dashboard", max_history: int = 100):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self._history: deque = deque(maxlen=max_history)
        self._handlers: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._connected = False
        self._last_error = None
        self._client: Optional[Any] = None

        if PAHO_AVAILABLE:
            try:
                # Support both paho-mqtt v1 and v2 API versions
                if hasattr(mqtt, "CallbackAPIVersion"):
                    self._client = mqtt.Client(
                        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                        client_id=client_id
                    )
                else:
                    self._client = mqtt.Client(client_id=client_id)

                self._client.on_connect = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message = self._on_message
            except Exception as e:
                self._last_error = f"Failed to initialize MQTT client: {str(e)}"
        else:
            self._last_error = "paho-mqtt library is not installed."

    def connect(self, timeout: float = 3.0) -> bool:
        """
        Attempts to connect to the configured MQTT broker.
        Returns True if connected successfully, False otherwise without raising uncaught exceptions.
        """
        if not PAHO_AVAILABLE or not self._client:
            self._last_error = "paho-mqtt library is not available."
            return False

        try:
            self._last_error = None
            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            # Wait briefly for connection acknowledgement
            import time
            start = time.time()
            while time.time() - start < timeout:
                if self._connected:
                    return True
                time.sleep(0.1)

            if not self._connected:
                self._last_error = f"Connection timeout to {self.broker_host}:{self.broker_port}. Ensure Mosquitto service is running."
                return False
            return True
        except Exception as e:
            self._connected = False
            self._last_error = f"Connection failed to {self.broker_host}:{self.broker_port}: {str(e)}"
            return False

    def disconnect(self) -> None:
        """Disconnects and stops the network loop."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Publishes JSON-serialized payload to topic."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "topic": topic,
            "payload": payload,
            "timestamp": now_iso,
            "source": f"MQTT ({self.broker_host}:{self.broker_port})"
        }
        with self._lock:
            self._history.appendleft(entry)

        if not self._connected or not self._client:
            return False

        try:
            payload_str = json.dumps(payload)
            result = self._client.publish(topic, payload_str, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self._last_error = f"MQTT Publish error: {str(e)}"
            return False

    def subscribe(self, topic_pattern: str, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """Registers a handler and subscribes with MQTT broker."""
        with self._lock:
            if topic_pattern not in self._handlers:
                self._handlers[topic_pattern] = []
            if handler not in self._handlers[topic_pattern]:
                self._handlers[topic_pattern].append(handler)

        if self._connected and self._client:
            try:
                self._client.subscribe(topic_pattern, qos=1)
            except Exception as e:
                self._last_error = f"Subscription error: {str(e)}"

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)[:limit]

    def is_connected(self) -> bool:
        return self._connected

    def get_last_error(self) -> Optional[str]:
        return self._last_error

    def get_mode_name(self) -> str:
        return f"MQTT Broker ({self.broker_host}:{self.broker_port})"

    # Internal MQTT Callbacks
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc if isinstance(rc, int) else getattr(rc, "value", 0)
        if rc_code == 0:
            self._connected = True
            self._last_error = None
            # Resubscribe to all registered topics upon connection
            with self._lock:
                for pattern in self._handlers.keys():
                    try:
                        self._client.subscribe(pattern, qos=1)
                    except Exception:
                        pass
        else:
            self._connected = False
            self._last_error = f"Broker refused connection with code {rc_code}."

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self._connected = False
        if rc != 0:
            self._last_error = f"Unexpected disconnection from broker (rc={rc})."

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "topic": topic,
            "payload": payload,
            "timestamp": now_iso,
            "source": f"MQTT-Inbound ({self.broker_host}:{self.broker_port})"
        }
        with self._lock:
            self._history.appendleft(entry)
            handlers_to_invoke = []
            for pattern, funcs in self._handlers.items():
                if mqtt.topic_matches_sub(pattern, topic):
                    handlers_to_invoke.extend(funcs)

        for handler in handlers_to_invoke:
            try:
                handler(topic, payload)
            except Exception as e:
                print(f"[MQTTAdapter] Handler error on topic {topic}: {e}")
