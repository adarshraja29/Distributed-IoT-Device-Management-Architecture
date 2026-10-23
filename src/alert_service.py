"""
Distributed IoT Device Management Architecture - Health & Alert Service
Monitors device heartbeats, detects stale/offline devices, raises alerts for low battery
and abnormal telemetry, prevents duplicate alerts, and maintains event logs.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.database import get_connection, DEFAULT_DB_PATH


class AlertService:
    """Evaluates device health conditions, generates alerts without duplication, and manages event logs."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def evaluate_fleet_health(
        self,
        offline_timeout_seconds: int = 60,
        low_battery_threshold: float = 20.0,
        temp_high_threshold: float = 45.0,
        temp_low_threshold: float = 2.0
    ) -> Dict[str, int]:
        """
        Runs comprehensive health evaluation across all registered devices.
        Returns counts of actions taken: {'marked_offline': X, 'new_alerts': Y}.
        """
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.strftime("%Y-%m-%d %H:%M:%S")
        cutoff_time = (now_utc - timedelta(seconds=offline_timeout_seconds)).strftime("%Y-%m-%d %H:%M:%S")

        marked_offline = 0
        new_alerts = 0

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. Detect stale heartbeats for active devices marked 'online'
            cursor.execute("""
                SELECT device_id, name, last_seen
                FROM devices
                WHERE is_active = 1
                  AND connection_status = 'online'
                  AND (last_seen IS NULL OR last_seen < ?);
            """, (cutoff_time,))
            stale_devices = [dict(row) for row in cursor.fetchall()]

            for dev in stale_devices:
                d_id = dev["device_id"]
                # Mark offline
                cursor.execute("UPDATE devices SET connection_status = 'offline' WHERE device_id = ?;", (d_id,))
                marked_offline += 1

                # Create DEVICE_OFFLINE alert if not already active
                if self._create_alert_if_not_exists(
                    conn,
                    device_id=d_id,
                    alert_type="DEVICE_OFFLINE",
                    severity="critical",
                    message=f"Device {d_id} ({dev['name']}) missed heartbeat threshold and is now offline."
                ):
                    new_alerts += 1

                # Log event
                cursor.execute("""
                    INSERT INTO event_logs (device_id, event_type, description, timestamp)
                    VALUES (?, 'OFFLINE_DETECTED', 'Device marked offline due to heartbeat timeout.', ?);
                """, (d_id, now_iso))

            # 2. Check for low battery alerts
            cursor.execute("""
                SELECT device_id, name, battery_level
                FROM devices
                WHERE is_active = 1
                  AND battery_level IS NOT NULL
                  AND battery_level < ?;
            """, (low_battery_threshold,))
            low_batt_devs = [dict(row) for row in cursor.fetchall()]

            for dev in low_batt_devs:
                d_id = dev["device_id"]
                batt = dev["battery_level"]
                if self._create_alert_if_not_exists(
                    conn,
                    device_id=d_id,
                    alert_type="LOW_BATTERY",
                    severity="warning",
                    message=f"Device {d_id} battery is critically low ({batt}%)."
                ):
                    new_alerts += 1

            # 3. Check latest telemetry for abnormal readings
            cursor.execute("""
                SELECT t.device_id, t.temperature, d.name
                FROM telemetry t
                INNER JOIN (
                    SELECT device_id, MAX(id) as max_id FROM telemetry GROUP BY device_id
                ) latest ON t.id = latest.max_id
                INNER JOIN devices d ON t.device_id = d.device_id
                WHERE d.is_active = 1
                  AND t.temperature IS NOT NULL
                  AND (t.temperature > ? OR t.temperature < ?);
            """, (temp_high_threshold, temp_low_threshold))
            abnormal_devs = [dict(row) for row in cursor.fetchall()]

            for dev in abnormal_devs:
                d_id = dev["device_id"]
                temp = dev["temperature"]
                if self._create_alert_if_not_exists(
                    conn,
                    device_id=d_id,
                    alert_type="TEMPERATURE_ANOMALY",
                    severity="warning",
                    message=f"Abnormal temperature detected on {d_id}: {temp}°C."
                ):
                    new_alerts += 1

            conn.commit()

        return {"marked_offline": marked_offline, "new_alerts": new_alerts}

    def _create_alert_if_not_exists(
        self,
        conn,
        device_id: str,
        alert_type: str,
        severity: str,
        message: str
    ) -> bool:
        """Helper to create an alert only if an unresolved alert for the same type does not exist."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM alerts
            WHERE device_id = ? AND alert_type = ? AND resolved = 0;
        """, (device_id, alert_type))
        if cursor.fetchone():
            return False  # Avoid duplicate unresolved alert

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO alerts (device_id, alert_type, severity, message, resolved, created_at)
            VALUES (?, ?, ?, ?, 0, ?);
        """, (device_id, alert_type, severity, message, now_iso))
        return True

    def resolve_alert(self, alert_id: int) -> bool:
        """Marks an alert as resolved with timestamp."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE alerts
                SET resolved = 1, resolved_at = ?
                WHERE id = ? AND resolved = 0;
            """, (now_iso, alert_id))
            resolved = cursor.rowcount > 0
            if resolved:
                cursor.execute("""
                    INSERT INTO event_logs (device_id, event_type, description, timestamp)
                    SELECT device_id, 'ALERT_RESOLVED', 'Alert ' || alert_type || ' resolved by user.', ?
                    FROM alerts WHERE id = ?;
                """, (now_iso, alert_id))
            conn.commit()
            return resolved

    def list_alerts(
        self,
        unresolved_only: bool = False,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieves alerts with filtering."""
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List[Any] = []

        if unresolved_only:
            query += " AND resolved = 0"

        if device_id and device_id != "All":
            query += " AND device_id = ?"
            params.append(device_id)

        if severity and severity != "All":
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def list_event_logs(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent system and device event logs."""
        query = "SELECT * FROM event_logs WHERE 1=1"
        params: List[Any] = []

        if device_id and device_id != "All":
            query += " AND device_id = ?"
            params.append(device_id)

        query += " ORDER BY timestamp DESC LIMIT ?;"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_alert_service = AlertService()


def get_alert_service() -> AlertService:
    return _alert_service
