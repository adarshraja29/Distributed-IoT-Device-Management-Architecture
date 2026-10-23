"""
Distributed IoT Device Management Architecture - Telemetry Service
Validates incoming telemetry messages, normalizes data, persists to SQLite,
and provides historical query APIs for analytics.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from src.database import get_connection, DEFAULT_DB_PATH
from src.message_bus import MessageBusInterface, get_default_message_bus


class TelemetryService:
    """Handles validation, ingestion, and querying of device telemetry readings."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, bus: Optional[MessageBusInterface] = None):
        self.db_path = db_path
        self.bus = bus or get_default_message_bus()

        # Wire up message bus listener for automatic ingestion
        self.bus.subscribe("iot/devices/+/telemetry", self._on_telemetry_message)
        self.bus.subscribe("iot/devices/+/heartbeat", self._on_heartbeat_message)

    def validate_and_normalize(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validates telemetry payload structure and types.
        Returns (is_valid, normalized_dict, error_message).
        """
        if not isinstance(payload, dict):
            return False, None, "Payload must be a JSON dictionary."

        device_id = payload.get("device_id")
        if not device_id or not isinstance(device_id, str):
            return False, None, "Missing or invalid 'device_id'."

        timestamp = payload.get("timestamp")
        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Normalize and bound numeric metrics safely
        def safe_float(val: Any) -> Optional[float]:
            if val is None or val == "":
                return None
            try:
                f = float(val)
                return None if f != f else f  # check NaN
            except (ValueError, TypeError):
                return None

        temperature = safe_float(payload.get("temperature"))
        humidity = safe_float(payload.get("humidity"))
        battery_level = safe_float(payload.get("battery_level"))
        signal_strength = safe_float(payload.get("signal_strength"))

        uptime_raw = payload.get("uptime_seconds", 0)
        try:
            uptime_seconds = int(uptime_raw) if uptime_raw is not None else 0
        except (ValueError, TypeError):
            uptime_seconds = 0

        status = str(payload.get("status", "NORMAL"))[:20]

        normalized = {
            "device_id": device_id.strip(),
            "timestamp": timestamp,
            "temperature": temperature,
            "humidity": humidity,
            "battery_level": battery_level,
            "signal_strength": signal_strength,
            "uptime_seconds": uptime_seconds,
            "status": status
        }
        return True, normalized, None

    def record_telemetry(self, payload: Dict[str, Any]) -> bool:
        """Validates and persists a telemetry reading, updating device last_seen and battery."""
        is_valid, data, err = self.validate_and_normalize(payload)
        if not is_valid or not data:
            return False

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert telemetry record
            cursor.execute("""
                INSERT INTO telemetry (
                    device_id, timestamp, temperature, humidity,
                    battery_level, signal_strength, uptime_seconds, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data["device_id"],
                data["timestamp"],
                data["temperature"],
                data["humidity"],
                data["battery_level"],
                data["signal_strength"],
                data["uptime_seconds"],
                data["status"]
            ))

            # Update device last_seen, battery, and mark online
            cursor.execute("""
                UPDATE devices
                SET last_seen = ?,
                    connection_status = 'online',
                    battery_level = COALESCE(?, battery_level)
                WHERE device_id = ?;
            """, (data["timestamp"], data["battery_level"], data["device_id"]))

            conn.commit()
            return True

    def get_latest_readings_all(self) -> List[Dict[str, Any]]:
        """Returns the most recent telemetry reading for all devices."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, d.name, d.location, d.device_type
                FROM telemetry t
                INNER JOIN (
                    SELECT device_id, MAX(id) as max_id
                    FROM telemetry
                    GROUP BY device_id
                ) latest ON t.id = latest.max_id
                INNER JOIN devices d ON t.device_id = d.device_id
                ORDER BY t.timestamp DESC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_device_history(
        self,
        device_id: Optional[str] = None,
        limit: int = 200,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves chronological telemetry history with optional filtering."""
        query = "SELECT * FROM telemetry WHERE 1=1"
        params: List[Any] = []

        if device_id and device_id != "All":
            query += " AND device_id = ?"
            params.append(device_id)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?;"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            # Return in ascending chronological order for charts
            rows.reverse()
            return rows

    def get_aggregated_stats(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates min, max, avg for temperature, humidity, and battery."""
        query = """
            SELECT
                COUNT(*) as count,
                AVG(temperature) as avg_temp,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(humidity) as avg_hum,
                MIN(humidity) as min_hum,
                MAX(humidity) as max_hum,
                AVG(battery_level) as avg_battery,
                MIN(battery_level) as min_battery,
                MAX(battery_level) as max_battery
            FROM telemetry
            WHERE 1=1
        """
        params: List[Any] = []
        if device_id and device_id != "All":
            query += " AND device_id = ?"
            params.append(device_id)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = dict(cursor.fetchone() or {})
            return {
                "count": row.get("count", 0),
                "avg_temp": round(row["avg_temp"], 1) if row.get("avg_temp") is not None else None,
                "min_temp": round(row["min_temp"], 1) if row.get("min_temp") is not None else None,
                "max_temp": round(row["max_temp"], 1) if row.get("max_temp") is not None else None,
                "avg_hum": round(row["avg_hum"], 1) if row.get("avg_hum") is not None else None,
                "min_hum": round(row["min_hum"], 1) if row.get("min_hum") is not None else None,
                "max_hum": round(row["max_hum"], 1) if row.get("max_hum") is not None else None,
                "avg_battery": round(row["avg_battery"], 1) if row.get("avg_battery") is not None else None,
                "min_battery": round(row["min_battery"], 1) if row.get("min_battery") is not None else None,
                "max_battery": round(row["max_battery"], 1) if row.get("max_battery") is not None else None,
            }

    # Bus event callbacks
    def _on_telemetry_message(self, topic: str, payload: Dict[str, Any]) -> None:
        self.record_telemetry(payload)

    def _on_heartbeat_message(self, topic: str, payload: Dict[str, Any]) -> None:
        device_id = payload.get("device_id")
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        battery = payload.get("battery_level")

        if device_id:
            with get_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE devices
                    SET last_seen = ?,
                        connection_status = 'online',
                        battery_level = COALESCE(?, battery_level)
                    WHERE device_id = ?;
                """, (timestamp, battery, device_id))
                conn.commit()


# Singleton instance
_telemetry_service = TelemetryService()


def get_telemetry_service() -> TelemetryService:
    return _telemetry_service
