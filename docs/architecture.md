# Distributed IoT Device Management Architecture
## College DSS Subject Architectural Specification

---

## 1. System Overview & Architectural Paradigm

The **Distributed IoT Device Management Architecture** is designed to demonstrate a robust, modular, and loosely-coupled IoT management system. Rather than creating a static dashboard with dummy charts, this system implements an end-to-end distributed systems pattern comprising:

1. **Autonomous Virtual Device Agents:** Emulating physical sensor nodes that generate periodic telemetry and heartbeat pulses, and handle remote actuator/management commands.
2. **Pluggable Communication Bus:** An abstract messaging layer with interchangeable implementations:
   * **In-Memory Local Simulator Bus:** Zero-configuration default mode for standalone laptop execution.
   * **MQTT Broker Adapter:** Broker-mediated publish/subscribe transport adhering to standard IoT communication patterns (using Eclipse Mosquitto and Paho MQTT).
3. **Core Management Services:** Specialized micro-services for device inventory registration, telemetry normalization, health and offline evaluation, command lifecycle tracking, and configuration management.
4. **Relational Persistence Layer:** Serverless SQLite database with parameterized transactions, foreign key constraints, indexes, and bounded telemetry pruning.
5. **Operational Presentation Layer:** Clean, responsive Streamlit dashboard providing fleet overview, device registry, time-series telemetry analytics, remote command center, and failure testing controls.

---

## 2. Component Architecture Diagram

```mermaid
graph TD
    subgraph Device_Layer [1. IoT Device Layer]
        D1[Virtual Sensor Node 1]
        D2[Virtual Sensor Node 2]
        Dn[Virtual Sensor Node N]
    end

    subgraph Communication_Layer [2. Communication Layer]
        BusSwitch{Pluggable Bus Interface}
        LocalBus[Local Simulator In-Memory Bus]
        MQTTBroker[Eclipse Mosquitto MQTT Broker]
        BusSwitch -->|Default| LocalBus
        BusSwitch -->|Optional| MQTTBroker
    end

    subgraph Management_Layer [3. Management Services]
        RegSvc[Device Registry Service]
        TelSvc[Telemetry Ingestion Service]
        AlertSvc[Health & Offline Detection Service]
        CmdSvc[Command & Config Service]
    end

    subgraph Storage_Layer [4. Persistence Layer - SQLite]
        DB[(iot_management.db)]
        T_Dev[devices]
        T_Tel[telemetry]
        T_Cmd[commands]
        T_Cfg[device_configurations]
        T_Alert[alerts]
        T_Log[event_logs]
        DB --- T_Dev
        DB --- T_Tel
        DB --- T_Cmd
        DB --- T_Cfg
        DB --- T_Alert
        DB --- T_Log
    end

    subgraph Presentation_Layer [5. Presentation Layer - Streamlit]
        P1[Overview Dashboard]
        P2[Device Registry]
        P3[Telemetry & Analytics]
        P4[Control Center]
    end

    D1 -->|Publish: Telemetry & Heartbeats| BusSwitch
    D2 -->|Publish: Telemetry & Heartbeats| BusSwitch
    Dn -->|Publish: Telemetry & Heartbeats| BusSwitch

    BusSwitch -->|Dispatch| TelSvc
    BusSwitch -->|Dispatch| AlertSvc

    CmdSvc -->|Publish: Remote Commands| BusSwitch
    BusSwitch -->|Receive: Remote Commands| D1
    D1 -->|Publish: Acknowledgement| BusSwitch
    BusSwitch -->|Dispatch: Acknowledgement| CmdSvc

    TelSvc --> DB
    AlertSvc --> DB
    CmdSvc --> DB
    RegSvc --> DB

    DB --> P1
    DB --> P2
    DB --> P3
    DB --> P4
    P4 -->|Trigger Commands & Disconnects| CmdSvc
```

---

## 3. Communication Topic Conventions

The communication bus uses clean, standardized topic hierarchy compatible with standard MQTT systems:

| Topic Pattern | Direction | Description |
| :--- | :--- | :--- |
| `iot/devices/{device_id}/telemetry` | Device $\rightarrow$ Management | Periodic sensor readings (temp, humidity, battery, signal, uptime) |
| `iot/devices/{device_id}/heartbeat` | Device $\rightarrow$ Management | Lightweight health and availability heartbeat pulse |
| `iot/devices/{device_id}/commands` | Management $\rightarrow$ Device | Remote commands (restart, update interval, status poll) |
| `iot/devices/{device_id}/ack` | Device $\rightarrow$ Management | Command execution acknowledgement or failure response |

---

## 4. Sequence Diagrams

### 4.1. Telemetry Ingestion Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Virtual Device Agent
    participant Bus as Message Bus (Local / MQTT)
    participant TelSvc as Telemetry Service
    participant DB as SQLite Database
    participant UI as Streamlit UI

    Dev->>Bus: publish("iot/devices/SENSOR-001/telemetry", payload)
    Bus->>TelSvc: dispatch(topic, payload)
    TelSvc->>TelSvc: validate_and_normalize(payload)
    alt Payload Valid
        TelSvc->>DB: INSERT INTO telemetry (...)
        TelSvc->>DB: UPDATE devices SET last_seen = NOW, battery_level = val
        UI->>DB: Query latest metrics & time-series
        UI-->>UI: Render updated charts & tables
    else Payload Malformed
        TelSvc-->>TelSvc: Reject payload & log warning
    end
```

### 4.2. Command Dispatch & Acknowledgement Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Operator
    participant UI as Control Center (Streamlit)
    participant CmdSvc as Command Service
    participant Bus as Message Bus (Local / MQTT)
    participant Dev as Virtual Device Agent
    participant DB as SQLite Database

    Admin->>UI: Select Device & Action ("restart")
    UI->>CmdSvc: dispatch_command("SENSOR-001", "restart")
    CmdSvc->>DB: INSERT INTO commands (id, status='pending')
    CmdSvc->>DB: UPDATE commands (status='sent')
    CmdSvc->>Bus: publish("iot/devices/SENSOR-001/commands", payload)
    Bus->>Dev: Deliver command payload
    alt Device Connected
        Dev->>Dev: Execute restart (reset uptime)
        Dev->>Bus: publish("iot/devices/SENSOR-001/ack", {status:'acknowledged'})
        Bus->>CmdSvc: Receive acknowledgement
        CmdSvc->>DB: UPDATE commands SET status='acknowledged', response=msg
        UI-->>Admin: Display success message & command ID
    else Device Disconnected (Offline Simulation)
        Dev-->>Bus: [Unreachable] (or returns status='failed')
        CmdSvc->>DB: UPDATE commands SET status='failed' / 'timed_out'
        UI-->>Admin: Display failure error notification
    end
```

---

## 5. Persistence Schema Details

* **`devices`**:
  * `device_id` (VARCHAR PK)
  * `device_type` (`temperature`, `humidity`, `environmental`, `battery_monitor`)
  * `name`, `location`
  * `connection_status` (`online`, `offline`)
  * `last_seen` (ISO 8601 UTC)
  * `firmware_version`, `config_version`
  * `battery_level`, `reporting_interval`, `is_active`
* **`telemetry`**:
  * `id` (INTEGER AUTOINCREMENT PK)
  * `device_id` (FK $\rightarrow$ `devices.device_id`)
  * `timestamp`, `temperature`, `humidity`, `battery_level`, `signal_strength`, `uptime_seconds`, `status`
  * Indexes on `(device_id, timestamp)` and `timestamp`.
* **`device_configurations`**:
  * `id` (PK), `device_id`, `version`, `reporting_interval`, `target_temp_min`, `target_temp_max`, `alert_threshold_battery`, `applied_at`, `status`
* **`commands`**:
  * `command_id` (TEXT PK), `device_id`, `command_type`, `payload`, `status` (`pending`, `sent`, `acknowledged`, `failed`, `timed_out`), `response`, `created_at`, `updated_at`
* **`alerts`**:
  * `id` (PK), `device_id`, `alert_type`, `severity` (`info`, `warning`, `critical`), `message`, `resolved`, `created_at`, `resolved_at`
* **`event_logs`**:
  * `id` (PK), `device_id`, `event_type`, `description`, `timestamp`

---

## 6. Lightweight Performance & Offline Architecture

1. **Zero Cloud Requirement:** The system operates 100% locally on Windows 11 with 8 GB RAM without requiring GPUs, cloud subscriptions, or external network connectivity.
2. **Bounded Resource Footprint:** Telemetry records can be pruned via `prune_old_telemetry()`, maintaining bounded database size and memory usage.
3. **Thread Safety:** Database operations utilize parameterized queries with WAL/timeout configurations, preventing concurrency locks between background simulation ticks and UI reads.
