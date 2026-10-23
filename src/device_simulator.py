"""
Distributed IoT Device Management Architecture - Virtual Device Simulator Layer
Simulates independent virtual IoT device agents that generate realistic telemetry,
heartbeats, and respond to remote commands over the message bus.
"""

import time
import random
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from src.message_bus import MessageBusInterface, get_default_message_bus


class VirtualDeviceAgent:
    """
    Represents an individual simulated IoT device agent.
    Maintains internal physical state, sensor characteristics, and handles incoming commands.
    """

    def __init__(
        self,
        device_id: str,
        device_type: str,
        name: str,
        location: str,
        battery_level: float = 85.0,
        reporting_interval: int = 10,
        firmware_version: str = "v1.2.0",
        config_version: int = 1,
        is_connected: bool = True
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.name = name
        self.location = location
        self.battery_level = battery_level
        self.reporting_interval = reporting_interval
        self.firmware_version = firmware_version
        self.config_version = config_version
        self.is_connected = is_connected

        # Internal state for realistic simulation
        self.uptime_seconds = 3600
        self.last_reported_time: Optional[float] = None
        self._target_temp_min = 18.0
        self._target_temp_max = 28.0

        # Base physical baseline values based on device type & location
        if "Server" in location:
            self._base_temp = 24.5
            self._base_hum = 42.0
        elif "Cold Storage" in location:
            self._base_temp = 3.5
            self._base_hum = 65.0
        elif "Boiler" in location:
            self._base_temp = 48.0
            self._base_hum = 30.0
        elif "Outdoor" in location:
            self._base_temp = 26.0
            self._base_hum = 58.0
        else:
            self._base_temp = 22.0
            self._base_hum = 50.0

        self._current_temp = self._base_temp
        self._current_hum = self._base_hum

    def generate_telemetry_payload(self) -> Dict[str, Any]:
        """Generates realistic sensor readings tailored to device type."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Slight continuous physical drift
        self._current_temp += random.uniform(-0.4, 0.4)
        # Pull slightly towards base temp to avoid runaway drift
        self._current_temp += (self._base_temp - self._current_temp) * 0.1

        self._current_hum += random.uniform(-0.8, 0.8)
        self._current_hum = max(10.0, min(95.0, self._current_hum + (self._base_hum - self._current_hum) * 0.1))

        # Battery discharge (slower for monitors, slight solar recharge for solar devices)
        if "Solar" in self.name:
            self.battery_level = min(100.0, self.battery_level + random.uniform(0.0, 0.2))
        else:
            self.battery_level = max(2.0, self.battery_level - random.uniform(0.01, 0.05))

        self.uptime_seconds += self.reporting_interval
        signal_strength = round(random.uniform(-78.0, -50.0), 1)

        payload = {
            "device_id": self.device_id,
            "timestamp": now_iso,
            "device_type": self.device_type,
            "uptime_seconds": self.uptime_seconds,
            "battery_level": round(self.battery_level, 1),
            "signal_strength": signal_strength,
            "status": "NORMAL"
        }

        # Apply device-type specific metrics
        if self.device_type in ("temperature", "environmental"):
            payload["temperature"] = round(self._current_temp, 2)
        else:
            payload["temperature"] = None

        if self.device_type in ("humidity", "environmental"):
            payload["humidity"] = round(self._current_hum, 1)
        else:
            payload["humidity"] = None

        return payload

    def generate_heartbeat_payload(self) -> Dict[str, Any]:
        """Generates periodic heartbeat packet."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "device_id": self.device_id,
            "timestamp": now_iso,
            "battery_level": round(self.battery_level, 1),
            "firmware_version": self.firmware_version,
            "config_version": self.config_version,
            "uptime_seconds": self.uptime_seconds,
            "status": "ALIVE"
        }

    def handle_command(self, command_id: str, command_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes simulated remote command on the device agent.
        Returns execution result and acknowledgement dictionary.
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # If device is disconnected from network, it cannot acknowledge
        if not self.is_connected:
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "failed",
                "response": "Device unreachable: simulated connection is offline.",
                "timestamp": now_iso
            }

        if command_type == "restart":
            self.uptime_seconds = 0
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "acknowledged",
                "response": "Device rebooted successfully. Uptime reset to 0.",
                "timestamp": now_iso
            }

        elif command_type == "set_interval":
            new_interval = int(payload.get("reporting_interval", 10))
            if new_interval < 1 or new_interval > 3600:
                return {
                    "command_id": command_id,
                    "device_id": self.device_id,
                    "status": "failed",
                    "response": f"Invalid reporting interval {new_interval}s. Must be between 1 and 3600s.",
                    "timestamp": now_iso
                }
            self.reporting_interval = new_interval
            self.config_version += 1
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "acknowledged",
                "response": f"Reporting interval updated to {new_interval}s. Config version is now v{self.config_version}.",
                "timestamp": now_iso
            }

        elif command_type == "request_telemetry":
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "acknowledged",
                "response": "Immediate telemetry cycle dispatched.",
                "timestamp": now_iso
            }

        elif command_type == "status_poll":
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "acknowledged",
                "response": f"Device operational. Battery={round(self.battery_level, 1)}%, Uptime={self.uptime_seconds}s.",
                "timestamp": now_iso
            }

        else:
            return {
                "command_id": command_id,
                "device_id": self.device_id,
                "status": "failed",
                "response": f"Unsupported command action '{command_type}'.",
                "timestamp": now_iso
            }


class FleetSimulator:
    """
    Manages the collection of virtual device agents, schedules bounded simulation ticks,
    and bridges simulated agents to the active MessageBusInterface.
    """

    def __init__(self, message_bus: Optional[MessageBusInterface] = None):
        self.bus = message_bus or get_default_message_bus()
        self.devices: Dict[str, VirtualDeviceAgent] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Subscribe to device command topics
        self.bus.subscribe("iot/devices/+/commands", self._on_command_received)

    def register_device(self, agent: VirtualDeviceAgent) -> None:
        """Adds a virtual device agent to the fleet simulator."""
        with self._lock:
            self.devices[agent.device_id] = agent

    def remove_device(self, device_id: str) -> None:
        """Removes a virtual device from simulation."""
        with self._lock:
            self.devices.pop(device_id, None)

    def set_device_connection(self, device_id: str, connected: bool) -> bool:
        """Toggles simulated device connectivity for offline demonstration."""
        with self._lock:
            if device_id in self.devices:
                self.devices[device_id].is_connected = connected
                return True
            return False

    def load_from_db_records(self, device_records: List[Dict[str, Any]]) -> None:
        """Initializes virtual agents from loaded database device records."""
        with self._lock:
            for rec in device_records:
                d_id = rec["device_id"]
                conn_status = rec.get("connection_status", "online")
                is_conn = (conn_status == "online")
                agent = VirtualDeviceAgent(
                    device_id=d_id,
                    device_type=rec.get("device_type", "environmental"),
                    name=rec.get("name", d_id),
                    location=rec.get("location", "Campus Building"),
                    battery_level=float(rec.get("battery_level", 85.0)),
                    reporting_interval=int(rec.get("reporting_interval", 10)),
                    firmware_version=rec.get("firmware_version", "v1.2.0"),
                    config_version=int(rec.get("config_version", 1)),
                    is_connected=is_conn
                )
                self.devices[d_id] = agent

    def step(self) -> int:
        """
        Executes a single simulation tick across all active connected virtual devices.
        Publishes heartbeats and telemetry to the active message bus.
        Returns the number of messages emitted.
        """
        emitted_count = 0
        with self._lock:
            agents = list(self.devices.values())

        for agent in agents:
            if not agent.is_connected:
                continue

            # Publish heartbeat
            hb_topic = f"iot/devices/{agent.device_id}/heartbeat"
            hb_payload = agent.generate_heartbeat_payload()
            self.bus.publish(hb_topic, hb_payload)
            emitted_count += 1

            # Publish telemetry
            tel_topic = f"iot/devices/{agent.device_id}/telemetry"
            tel_payload = agent.generate_telemetry_payload()
            self.bus.publish(tel_topic, tel_payload)
            emitted_count += 1

        return emitted_count

    def start_background_loop(self, interval_seconds: float = 8.0) -> None:
        """Starts a bounded background simulator thread if not already running."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._run_loop,
                args=(interval_seconds,),
                daemon=True,
                name="FleetSimulatorWorker"
            )
            self._worker_thread.start()

    def stop_background_loop(self) -> None:
        """Stops the background simulator thread cleanly."""
        self._stop_event.set()
        with self._lock:
            self._running = False
            self._worker_thread = None

    def is_running(self) -> bool:
        return self._running

    def _run_loop(self, interval_seconds: float) -> None:
        while not self._stop_event.is_set():
            try:
                self.step()
            except Exception as e:
                print(f"[FleetSimulator] Simulation tick exception: {e}")
            self._stop_event.wait(interval_seconds)

    def _on_command_received(self, topic: str, payload: Dict[str, Any]) -> None:
        """Internal callback invoked when a command is published on the bus."""
        parts = topic.split("/")
        if len(parts) >= 3:
            device_id = parts[2]
            with self._lock:
                agent = self.devices.get(device_id)

            if agent:
                cmd_id = payload.get("command_id", "CMD-UNKNOWN")
                cmd_type = payload.get("command_type", "unknown")
                cmd_payload = payload.get("payload", {})
                ack_response = agent.handle_command(cmd_id, cmd_type, cmd_payload)

                ack_topic = f"iot/devices/{device_id}/ack"
                self.bus.publish(ack_topic, ack_response)


# Singleton simulator instance
_fleet_simulator = FleetSimulator()


def get_fleet_simulator() -> FleetSimulator:
    return _fleet_simulator
