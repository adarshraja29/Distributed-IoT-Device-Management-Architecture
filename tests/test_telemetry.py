"""
Unit tests for Telemetry Ingestion, History Queries, and Alert Service.
Uses isolated temporary SQLite databases.
"""

import os
import tempfile
import pytest
from src.database import init_db
from src.device_registry import DeviceRegistry
from src.telemetry_service import TelemetryService
from src.alert_service import AlertService
from src.message_bus import LocalMessageBus


@pytest.fixture
def isolated_env():
    """Provides an isolated database, bus, registry, telemetry service, and alert service."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)

    bus = LocalMessageBus()
    registry = DeviceRegistry(db_path=path)
    telemetry_svc = TelemetryService(db_path=path, bus=bus)
    alert_svc = AlertService(db_path=path)

    # Register sample devices for testing
    registry.register_device("DEV-TEL-1", "environmental", "Room 101", "Building A")
    registry.register_device("DEV-TEL-2", "battery_monitor", "UPS Unit", "Substation")

    yield {
        "db_path": path,
        "bus": bus,
        "registry": registry,
        "telemetry_svc": telemetry_svc,
        "alert_svc": alert_svc
    }

    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_valid_telemetry_recording(isolated_env):
    """Verifies that valid telemetry updates history and device status."""
    tel_svc = isolated_env["telemetry_svc"]
    registry = isolated_env["registry"]

    payload = {
        "device_id": "DEV-TEL-1",
        "temperature": 23.5,
        "humidity": 45.2,
        "battery_level": 82.0,
        "signal_strength": -65.0,
        "uptime_seconds": 1200,
        "status": "NORMAL"
    }
    assert tel_svc.record_telemetry(payload) is True

    # Check device last_seen updated
    dev = registry.get_device("DEV-TEL-1")
    assert dev["last_seen"] is not None
    assert dev["battery_level"] == 82.0

    # Check history record
    history = tel_svc.get_device_history(device_id="DEV-TEL-1")
    assert len(history) == 1
    assert history[0]["temperature"] == 23.5
    assert history[0]["humidity"] == 45.2


def test_malformed_telemetry_handling(isolated_env):
    """Verifies that invalid payloads are safely rejected without throwing unhandled exceptions."""
    tel_svc = isolated_env["telemetry_svc"]

    # Missing device_id
    assert tel_svc.record_telemetry({"temperature": 22.0}) is False

    # Empty device_id
    assert tel_svc.record_telemetry({"device_id": "", "temperature": 22.0}) is False

    # Non-dictionary payload
    assert tel_svc.record_telemetry("invalid_string_payload") is False  # type: ignore


def test_aggregated_stats(isolated_env):
    """Verifies aggregate calculations (min, max, avg)."""
    tel_svc = isolated_env["telemetry_svc"]

    tel_svc.record_telemetry({"device_id": "DEV-TEL-1", "temperature": 20.0, "humidity": 40.0, "battery_level": 90.0})
    tel_svc.record_telemetry({"device_id": "DEV-TEL-1", "temperature": 30.0, "humidity": 60.0, "battery_level": 80.0})

    stats = tel_svc.get_aggregated_stats("DEV-TEL-1")
    assert stats["count"] == 2
    assert stats["min_temp"] == 20.0
    assert stats["max_temp"] == 30.0
    assert stats["avg_temp"] == 25.0
    assert stats["avg_hum"] == 50.0


def test_alert_generation_and_duplicate_prevention(isolated_env):
    """Verifies low battery alerts and offline alerts without creating duplicates."""
    alert_svc = isolated_env["alert_svc"]
    registry = isolated_env["registry"]

    # Record reading with low battery (10%)
    isolated_env["telemetry_svc"].record_telemetry({
        "device_id": "DEV-TEL-2",
        "battery_level": 10.0
    })

    # Run health evaluation
    res = alert_svc.evaluate_fleet_health(low_battery_threshold=20.0)
    assert res["new_alerts"] >= 1

    alerts = alert_svc.list_alerts(unresolved_only=True, device_id="DEV-TEL-2")
    assert any(a["alert_type"] == "LOW_BATTERY" for a in alerts)

    # Run evaluation again; ensure duplicate alert is NOT created
    res2 = alert_svc.evaluate_fleet_health(low_battery_threshold=20.0)
    alerts_after = alert_svc.list_alerts(unresolved_only=True, device_id="DEV-TEL-2")
    low_batt_count = sum(1 for a in alerts_after if a["alert_type"] == "LOW_BATTERY")
    assert low_batt_count == 1  # Still exactly 1 unresolved alert


def test_alert_resolution(isolated_env):
    """Verifies marking an alert as resolved."""
    alert_svc = isolated_env["alert_svc"]
    isolated_env["telemetry_svc"].record_telemetry({"device_id": "DEV-TEL-2", "battery_level": 5.0})
    alert_svc.evaluate_fleet_health(low_battery_threshold=20.0)

    alerts = alert_svc.list_alerts(unresolved_only=True, device_id="DEV-TEL-2")
    assert len(alerts) > 0
    target_alert_id = alerts[0]["id"]

    # Resolve
    assert alert_svc.resolve_alert(target_alert_id) is True
    # Should no longer appear in unresolved list
    assert not any(a["id"] == target_alert_id for a in alert_svc.list_alerts(unresolved_only=True))
