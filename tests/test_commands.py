"""
Unit tests for Command Service, Virtual Device Agent Command Handling,
Configuration Revisions, and Timeouts.
"""

import os
import tempfile
import pytest
from src.database import init_db
from src.device_registry import DeviceRegistry
from src.command_service import CommandService
from src.device_simulator import VirtualDeviceAgent, FleetSimulator
from src.message_bus import LocalMessageBus


@pytest.fixture
def isolated_cmd_env():
    """Provides isolated test environment for commands."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)

    bus = LocalMessageBus()
    registry = DeviceRegistry(db_path=path)
    cmd_svc = CommandService(db_path=path, bus=bus)
    simulator = FleetSimulator(message_bus=bus)

    # Register virtual device in registry
    registry.register_device("DEV-CMD-1", "environmental", "Demo Room", "Building C", reporting_interval=10)

    # Register agent in simulator
    agent = VirtualDeviceAgent("DEV-CMD-1", "environmental", "Demo Room", "Building C", reporting_interval=10)
    simulator.register_device(agent)

    yield {
        "db_path": path,
        "bus": bus,
        "registry": registry,
        "cmd_svc": cmd_svc,
        "simulator": simulator,
        "agent": agent
    }

    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_command_dispatch_and_acknowledgement(isolated_cmd_env):
    """Verifies complete command dispatch -> agent execution -> acknowledgement lifecycle."""
    cmd_svc = isolated_cmd_env["cmd_svc"]

    # Dispatch restart command
    cmd = cmd_svc.dispatch_command("DEV-CMD-1", "restart")
    assert cmd is not None
    assert cmd["command_id"].startswith("CMD-")

    # In local bus, synchronous dispatch delivers command and ack immediately
    updated_cmd = cmd_svc.get_command(cmd["command_id"])
    assert updated_cmd["status"] == "acknowledged"
    assert "rebooted successfully" in updated_cmd["response"]


def test_command_on_disconnected_device_fails(isolated_cmd_env):
    """Verifies that an offline/disconnected device fails the command gracefully."""
    cmd_svc = isolated_cmd_env["cmd_svc"]
    simulator = isolated_cmd_env["simulator"]

    # Disconnect simulated device
    simulator.set_device_connection("DEV-CMD-1", False)

    cmd = cmd_svc.dispatch_command("DEV-CMD-1", "restart")
    updated_cmd = cmd_svc.get_command(cmd["command_id"])
    assert updated_cmd["status"] == "failed"
    assert "unreachable" in updated_cmd["response"]


def test_configuration_update_lifecycle(isolated_cmd_env):
    """Verifies configuration update creates new version and updates reporting interval."""
    cmd_svc = isolated_cmd_env["cmd_svc"]
    registry = isolated_cmd_env["registry"]

    cmd = cmd_svc.update_configuration("DEV-CMD-1", reporting_interval=25)
    assert cmd is not None

    # Verify device record updated in database
    dev = registry.get_device("DEV-CMD-1")
    assert dev["reporting_interval"] == 25
    assert dev["config_version"] == 2

    # Verify agent updated
    assert isolated_cmd_env["agent"].reporting_interval == 25


def test_configuration_validation_rejection(isolated_cmd_env):
    """Verifies invalid reporting intervals are rejected."""
    cmd_svc = isolated_cmd_env["cmd_svc"]

    with pytest.raises(ValueError, match="between 1 and 3600"):
        cmd_svc.update_configuration("DEV-CMD-1", reporting_interval=0)

    with pytest.raises(ValueError, match="between 1 and 3600"):
        cmd_svc.update_configuration("DEV-CMD-1", reporting_interval=99999)


def test_command_timeout_updating(isolated_cmd_env):
    """Verifies check_and_update_timeouts marks stale sent commands as timed_out."""
    cmd_svc = isolated_cmd_env["cmd_svc"]
    # Manually insert a stale sent command
    from src.database import get_connection
    with get_connection(isolated_cmd_env["db_path"]) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO commands (command_id, device_id, command_type, status, created_at, updated_at)
            VALUES ('CMD-STALE-99', 'DEV-CMD-1', 'status_poll', 'sent', '2020-01-01 00:00:00', '2020-01-01 00:00:00');
        """)
        conn.commit()

    timed_out_count = cmd_svc.check_and_update_timeouts(timeout_seconds=30)
    assert timed_out_count == 1

    cmd = cmd_svc.get_command("CMD-STALE-99")
    assert cmd["status"] == "timed_out"
