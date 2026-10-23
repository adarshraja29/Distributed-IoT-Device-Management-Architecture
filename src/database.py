"""
Distributed IoT Device Management Architecture - Database Layer
Provides idempotent SQLite table creation, parameterized queries, indexes,
and sample data initialization.
"""

import os
import sqlite3
import csv
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iot_management.db")
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_devices.csv")


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory and foreign keys."""
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Initializes database tables and indexes safely and idempotently.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Devices Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                registration_time TEXT NOT NULL,
                connection_status TEXT NOT NULL DEFAULT 'offline',
                last_seen TEXT,
                firmware_version TEXT NOT NULL DEFAULT 'v1.0.0',
                config_version INTEGER NOT NULL DEFAULT 1,
                battery_level REAL,
                reporting_interval INTEGER NOT NULL DEFAULT 10,
                is_active INTEGER NOT NULL DEFAULT 1
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(connection_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);")

        # 2. Telemetry Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                battery_level REAL,
                signal_strength REAL,
                uptime_seconds INTEGER,
                status TEXT NOT NULL DEFAULT 'NORMAL',
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry(device_id, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry(timestamp);")

        # 3. Device Configurations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                reporting_interval INTEGER NOT NULL,
                target_temp_min REAL DEFAULT 18.0,
                target_temp_max REAL DEFAULT 28.0,
                alert_threshold_battery REAL DEFAULT 20.0,
                applied_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_config_device ON device_configurations(device_id, version);")

        # 4. Commands Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL, -- pending, sent, acknowledged, failed, timed_out
                response TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_device ON commands(device_id, created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);")

        # 5. Alerts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL, -- info, warning, critical
                message TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_device_resolved ON alerts(device_id, resolved);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);")

        # 6. Event Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON event_logs(timestamp);")

        conn.commit()


def seed_initial_data(db_path: str = DEFAULT_DB_PATH, csv_path: str = DEFAULT_CSV_PATH) -> bool:
    """
    Populates sample devices and initial baseline telemetry if database is empty.
    Prevents duplicates on repeated calls. Returns True if seeded, False if already populated.
    """
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM devices;")
        row = cursor.fetchone()
        if row and row["cnt"] > 0:
            return False  # Already seeded

        if not os.path.exists(csv_path):
            return False

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d_id = row["device_id"]
                conn_status = row.get("connection_status", "online")
                last_seen = now_iso if conn_status == "online" else (datetime.now(timezone.utc) - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO devices (
                        device_id, device_type, name, location, registration_time,
                        connection_status, last_seen, firmware_version, config_version,
                        battery_level, reporting_interval, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    d_id,
                    row["device_type"],
                    row["name"],
                    row["location"],
                    row.get("registration_time", now_iso),
                    conn_status,
                    last_seen,
                    row.get("firmware_version", "v1.0.0"),
                    int(row.get("config_version", 1)),
                    float(row.get("battery_level", 85.0)),
                    int(row.get("reporting_interval", 10))
                ))

                # Insert default configuration
                cursor.execute("""
                    INSERT INTO device_configurations (
                        device_id, version, reporting_interval, target_temp_min, target_temp_max,
                        alert_threshold_battery, applied_at, status
                    ) VALUES (?, ?, ?, 18.0, 28.0, 20.0, ?, 'active')
                """, (d_id, int(row.get("config_version", 1)), int(row.get("reporting_interval", 10)), now_iso))

                # Generate a few historical telemetry records for realistic first load
                import random
                for minutes_ago in range(30, 0, -5):
                    t_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")
                    dev_type = row["device_type"]
                    temp = round(21.5 + random.uniform(-2.5, 3.5), 1) if dev_type in ("temperature", "environmental") else None
                    hum = round(52.0 + random.uniform(-6.0, 7.0), 1) if dev_type in ("humidity", "environmental") else None
                    batt = round(max(5.0, float(row.get("battery_level", 85.0)) - random.uniform(0.0, 0.4)), 1)
                    sig = round(random.uniform(-75.0, -45.0), 1)

                    cursor.execute("""
                        INSERT INTO telemetry (
                            device_id, timestamp, temperature, humidity, battery_level,
                            signal_strength, uptime_seconds, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'NORMAL')
                    """, (d_id, t_time, temp, hum, batt, sig, 3600 + (30 - minutes_ago) * 60))

                # Seed alerts for devices with low battery or offline
                if float(row.get("battery_level", 100)) <= 20:
                    cursor.execute("""
                        INSERT INTO alerts (
                            device_id, alert_type, severity, message, resolved, created_at
                        ) VALUES (?, 'LOW_BATTERY', 'warning', 'Device battery level is below 20%', 0, ?)
                    """, (d_id, now_iso))

                if conn_status == "offline":
                    cursor.execute("""
                        INSERT INTO alerts (
                            device_id, alert_type, severity, message, resolved, created_at
                        ) VALUES (?, 'DEVICE_OFFLINE', 'critical', 'Device missed heartbeat threshold and is offline', 0, ?)
                    """, (d_id, now_iso))

        # Initial system event log
        cursor.execute("""
            INSERT INTO event_logs (device_id, event_type, description, timestamp)
            VALUES (NULL, 'SYSTEM_INIT', 'Initial database seed completed successfully with sample devices', ?)
        """, (now_iso,))

        conn.commit()
    return True


def prune_old_telemetry(max_records_per_device: int = 200, db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Prunes excess old telemetry records per device to maintain bound memory/disk usage on 8 GB RAM machines.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM telemetry
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp DESC) as rn
                    FROM telemetry
                ) WHERE rn <= ?
            )
        """, (max_records_per_device,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted
