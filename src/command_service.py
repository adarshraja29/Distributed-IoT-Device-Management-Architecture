"""
Distributed IoT Device Management Architecture - Command & Configuration Service
Coordinates remote command dispatch, lifecycle tracking (pending -> sent -> acknowledged / failed),
and device configuration updates over the message bus.
"""

import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.database import get_connection, DEFAULT_DB_PATH
from src.message_bus import MessageBusInterface, get_default_message_bus


class CommandService:
    """Manages command dispatch, acknowledgement processing, and configuration updates."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, bus: Optional[MessageBusInterface] = None):
        self.db_path = db_path
        self.bus = bus or get_default_message_bus()

        # Listen for acknowledgements on the message bus
        self.bus.subscribe("iot/devices/+/ack", self._on_acknowledgement_received)

    def dispatch_command(
        self,
        device_id: str,
        command_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a unique command record and publishes it to the device's command topic.
        State transition: created (pending) -> published (sent) -> ack received.
        """
        command_id = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        payload_data = payload or {}
        payload_json = json.dumps(payload_data)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commands (
                    command_id, device_id, command_type, payload,
                    status, response, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', NULL, ?, ?);
            """, (command_id, device_id, command_type, payload_json, now_iso, now_iso))

            cursor.execute("""
                INSERT INTO event_logs (device_id, event_type, description, timestamp)
                VALUES (?, 'COMMAND_DISPATCH', ?, ?);
            """, (device_id, f"Dispatched command '{command_type}' with ID {command_id}", now_iso))

            conn.commit()

        # Publish command on bus topic
        topic = f"iot/devices/{device_id}/commands"
        msg = {
            "command_id": command_id,
            "device_id": device_id,
            "command_type": command_type,
            "payload": payload_data,
            "timestamp": now_iso
        }

        # Transition status to 'sent'
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE commands
                SET status = 'sent', updated_at = ?
                WHERE command_id = ?;
            """, (now_iso, command_id))
            conn.commit()

        self.bus.publish(topic, msg)

        return self.get_command(command_id) or {"command_id": command_id, "status": "sent"}

    def update_configuration(
        self,
        device_id: str,
        reporting_interval: int,
        target_temp_min: float = 18.0,
        target_temp_max: float = 28.0,
        alert_threshold_battery: float = 20.0
    ) -> Dict[str, Any]:
        """
        Applies a configuration revision to a device and issues a configuration update command.
        """
        if reporting_interval < 1 or reporting_interval > 3600:
            raise ValueError("Reporting interval must be between 1 and 3600 seconds.")

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Determine next version
            cursor.execute("SELECT config_version FROM devices WHERE device_id = ?;", (device_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Device {device_id} not found.")

            next_version = (row["config_version"] or 1) + 1

            # Insert configuration record
            cursor.execute("""
                INSERT INTO device_configurations (
                    device_id, version, reporting_interval, target_temp_min,
                    target_temp_max, alert_threshold_battery, applied_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active');
            """, (device_id, next_version, reporting_interval, target_temp_min, target_temp_max, alert_threshold_battery, now_iso))

            # Update device table
            cursor.execute("""
                UPDATE devices
                SET config_version = ?, reporting_interval = ?
                WHERE device_id = ?;
            """, (next_version, reporting_interval, device_id))

            conn.commit()

        # Dispatch command to device
        return self.dispatch_command(
            device_id=device_id,
            command_type="set_interval",
            payload={"reporting_interval": reporting_interval, "version": next_version}
        )

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single command by ID."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM commands WHERE command_id = ?;", (command_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_commands(
        self,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Returns recent commands with optional device and status filters."""
        query = "SELECT * FROM commands WHERE 1=1"
        params: List[Any] = []

        if device_id and device_id != "All":
            query += " AND device_id = ?"
            params.append(device_id)

        if status and status != "All":
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def check_and_update_timeouts(self, timeout_seconds: int = 30) -> int:
        """Transitions sent commands exceeding timeout_seconds without ack to 'timed_out'."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE commands
                SET status = 'timed_out',
                    response = 'Command timed out waiting for device response.',
                    updated_at = ?
                WHERE status IN ('pending', 'sent') AND created_at < ?;
            """, (now_iso, cutoff))
            updated = cursor.rowcount
            conn.commit()
            return updated

    def _on_acknowledgement_received(self, topic: str, payload: Dict[str, Any]) -> None:
        """Processes incoming acknowledgement and updates command lifecycle state."""
        cmd_id = payload.get("command_id")
        status = payload.get("status", "acknowledged")
        response_text = payload.get("response", "Acknowledgement received.")
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if not cmd_id:
            return

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE commands
                SET status = ?, response = ?, updated_at = ?
                WHERE command_id = ?;
            """, (status, response_text, now_iso, cmd_id))

            cursor.execute("""
                INSERT INTO event_logs (device_id, event_type, description, timestamp)
                VALUES (?, 'COMMAND_ACK', ?, ?);
            """, (payload.get("device_id"), f"Command {cmd_id} status updated to {status}: {response_text}", now_iso))

            conn.commit()


# Singleton instance
_command_service = CommandService()


def get_command_service() -> CommandService:
    return _command_service
