"""
Distributed IoT Device Management Architecture - Device Registry Service
Manages device inventory, registration, activation/deactivation, metadata, and status lookups.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from src.database import get_connection, DEFAULT_DB_PATH


class DeviceRegistry:
    """Provides methods for registering, querying, and updating IoT device metadata in SQLite."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def list_devices(
        self,
        search: Optional[str] = None,
        device_type: Optional[str] = None,
        location: Optional[str] = None,
        connection_status: Optional[str] = None,
        include_inactive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves devices with optional filtering by query, type, location, and status.
        """
        query = "SELECT * FROM devices WHERE 1=1"
        params: List[Any] = []

        if not include_inactive:
            query += " AND is_active = 1"

        if search:
            search_pattern = f"%{search.strip()}%"
            query += " AND (device_id LIKE ? OR name LIKE ? OR location LIKE ?)"
            params.extend([search_pattern, search_pattern, search_pattern])

        if device_type and device_type != "All":
            query += " AND device_type = ?"
            params.append(device_type)

        if location and location != "All":
            query += " AND location = ?"
            params.append(location)

        if connection_status and connection_status != "All":
            query += " AND connection_status = ?"
            params.append(connection_status)

        query += " ORDER BY device_id ASC;"

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single device by its unique ID."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE device_id = ?;", (device_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def register_device(
        self,
        device_id: str,
        device_type: str,
        name: str,
        location: str,
        reporting_interval: int = 10,
        firmware_version: str = "v1.0.0"
    ) -> Dict[str, Any]:
        """
        Registers a new device with input validation and duplicate prevention.
        """
        # Clean and validate device_id
        device_id = device_id.strip().upper()
        if not re.match(r"^[A-Z0-9_\-]+$", device_id):
            raise ValueError("Device ID must only contain alphanumeric characters, hyphens, and underscores.")

        if not name.strip():
            raise ValueError("Device name cannot be empty.")

        if not location.strip():
            raise ValueError("Device location cannot be empty.")

        valid_types = {"temperature", "humidity", "environmental", "battery_monitor"}
        if device_type not in valid_types:
            raise ValueError(f"Invalid device type '{device_type}'. Valid types: {', '.join(valid_types)}")

        if reporting_interval < 1 or reporting_interval > 3600:
            raise ValueError("Reporting interval must be between 1 and 3600 seconds.")

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # Check existing
            cursor.execute("SELECT device_id FROM devices WHERE device_id = ?;", (device_id,))
            if cursor.fetchone():
                raise ValueError(f"Device with ID '{device_id}' already exists.")

            cursor.execute("""
                INSERT INTO devices (
                    device_id, device_type, name, location, registration_time,
                    connection_status, last_seen, firmware_version, config_version,
                    battery_level, reporting_interval, is_active
                ) VALUES (?, ?, ?, ?, ?, 'online', ?, ?, 1, 100.0, ?, 1);
            """, (device_id, device_type, name.strip(), location.strip(), now_iso, now_iso, firmware_version, reporting_interval))

            # Create default config record
            cursor.execute("""
                INSERT INTO device_configurations (
                    device_id, version, reporting_interval, applied_at, status
                ) VALUES (?, 1, ?, ?, 'active');
            """, (device_id, reporting_interval, now_iso))

            # Event log
            cursor.execute("""
                INSERT INTO event_logs (device_id, event_type, description, timestamp)
                VALUES (?, 'DEVICE_REGISTERED', ?, ?);
            """, (device_id, f"Registered new device {name} ({device_type}) at {location}", now_iso))

            conn.commit()

        return self.get_device(device_id)

    def set_active_state(self, device_id: str, is_active: bool) -> bool:
        """Deactivates or reactivates a device in the inventory."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        status_text = "Activated" if is_active else "Deactivated"

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices
                SET is_active = ?, connection_status = CASE WHEN ? = 0 THEN 'offline' ELSE connection_status END
                WHERE device_id = ?;
            """, (1 if is_active else 0, 1 if is_active else 0, device_id))

            if cursor.rowcount == 0:
                return False

            cursor.execute("""
                INSERT INTO event_logs (device_id, event_type, description, timestamp)
                VALUES (?, 'STATUS_CHANGE', ?, ?);
            """, (device_id, f"Device {status_text} by administrator.", now_iso))

            conn.commit()
            return True

    def update_connection_status(self, device_id: str, status: str, last_seen: Optional[str] = None) -> bool:
        """Updates device connection status ('online' / 'offline') and last_seen timestamp."""
        now_iso = last_seen or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices
                SET connection_status = ?, last_seen = ?
                WHERE device_id = ?;
            """, (status, now_iso, device_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_summary_stats(self) -> Dict[str, Any]:
        """Computes key fleet performance indicators directly from database records."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN connection_status = 'online' AND is_active = 1 THEN 1 ELSE 0 END) as online,
                    SUM(CASE WHEN connection_status = 'offline' AND is_active = 1 THEN 1 ELSE 0 END) as offline,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive,
                    AVG(CASE WHEN battery_level IS NOT NULL AND is_active = 1 THEN battery_level ELSE NULL END) as avg_battery,
                    SUM(CASE WHEN battery_level < 20.0 AND is_active = 1 THEN 1 ELSE 0 END) as low_battery
                FROM devices;
            """)
            row = dict(cursor.fetchone())

            cursor.execute("SELECT COUNT(*) as active_alerts FROM alerts WHERE resolved = 0;")
            row["active_alerts"] = cursor.fetchone()["active_alerts"]

            return {
                "total": row["total"] or 0,
                "online": row["online"] or 0,
                "offline": row["offline"] or 0,
                "inactive": row["inactive"] or 0,
                "avg_battery": round(row["avg_battery"] or 0.0, 1),
                "low_battery": row["low_battery"] or 0,
                "active_alerts": row["active_alerts"] or 0
            }

    def get_all_locations(self) -> List[str]:
        """Returns sorted distinct device locations."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT location FROM devices WHERE location IS NOT NULL ORDER BY location ASC;")
            return [row["location"] for row in cursor.fetchall()]

    def get_all_types(self) -> List[str]:
        """Returns distinct device types."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT device_type FROM devices WHERE device_type IS NOT NULL ORDER BY device_type ASC;")
            return [row["device_type"] for row in cursor.fetchall()]


# Singleton instance
_device_registry = DeviceRegistry()


def get_device_registry() -> DeviceRegistry:
    return _device_registry
