"""
Unit tests for Device Registry and Database Initialization.
Uses isolated temporary SQLite databases for each test run.
"""

import os
import tempfile
import pytest
from src.database import init_db, seed_initial_data, get_connection
from src.device_registry import DeviceRegistry


@pytest.fixture
def test_db():
    """Provides a fresh, isolated temporary database path for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_init_db_and_idempotence(test_db):
    """Verifies that init_db executes cleanly multiple times without error."""
    init_db(test_db)
    with get_connection(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        assert "devices" in tables
        assert "telemetry" in tables
        assert "commands" in tables
        assert "alerts" in tables
        assert "event_logs" in tables
        assert "device_configurations" in tables


def test_register_device_success(test_db):
    """Verifies successful registration of a virtual IoT device."""
    registry = DeviceRegistry(db_path=test_db)
    dev = registry.register_device(
        device_id="TEST-DEV-001",
        device_type="temperature",
        name="Test Sensor",
        location="Lab 101",
        reporting_interval=15
    )
    assert dev is not None
    assert dev["device_id"] == "TEST-DEV-001"
    assert dev["device_type"] == "temperature"
    assert dev["name"] == "Test Sensor"
    assert dev["location"] == "Lab 101"
    assert dev["reporting_interval"] == 15
    assert dev["is_active"] == 1


def test_register_duplicate_device_fails(test_db):
    """Verifies duplicate device ID registration raises a ValueError."""
    registry = DeviceRegistry(db_path=test_db)
    registry.register_device("DEV-DUP-01", "temperature", "Sensor A", "Room 1")

    with pytest.raises(ValueError, match="already exists"):
        registry.register_device("DEV-DUP-01", "humidity", "Sensor B", "Room 2")


def test_register_invalid_device_id_fails(test_db):
    """Verifies illegal characters in device ID are rejected."""
    registry = DeviceRegistry(db_path=test_db)
    with pytest.raises(ValueError, match="alphanumeric"):
        registry.register_device("DEV@#$!!", "temperature", "Sensor", "Room 1")


def test_device_activation_and_deactivation(test_db):
    """Verifies activating and deactivating devices."""
    registry = DeviceRegistry(db_path=test_db)
    registry.register_device("DEV-ACTIVE-01", "environmental", "Sensor Active", "Hallway")

    # Deactivate
    assert registry.set_active_state("DEV-ACTIVE-01", False) is True
    dev = registry.get_device("DEV-ACTIVE-01")
    assert dev["is_active"] == 0
    assert dev["connection_status"] == "offline"

    # Reactivate
    assert registry.set_active_state("DEV-ACTIVE-01", True) is True
    dev = registry.get_device("DEV-ACTIVE-01")
    assert dev["is_active"] == 1


def test_device_filtering(test_db):
    """Verifies search and filter operations."""
    registry = DeviceRegistry(db_path=test_db)
    registry.register_device("DEV-TEMP-A", "temperature", "North Sensor", "Building A")
    registry.register_device("DEV-TEMP-B", "temperature", "South Sensor", "Building B")
    registry.register_device("DEV-HUM-A", "humidity", "East Sensor", "Building A")

    # Filter by type
    temps = registry.list_devices(device_type="temperature")
    assert len(temps) == 2

    # Filter by location
    bldg_a = registry.list_devices(location="Building A")
    assert len(bldg_a) == 2

    # Search query
    found = registry.list_devices(search="South")
    assert len(found) == 1
    assert found[0]["device_id"] == "DEV-TEMP-B"


def test_empty_registry_handling(test_db):
    """Verifies safe handling of empty registry queries."""
    registry = DeviceRegistry(db_path=test_db)
    assert registry.list_devices() == []
    assert registry.get_device("NON-EXISTENT") is None
    stats = registry.get_summary_stats()
    assert stats["total"] == 0
    assert stats["online"] == 0
