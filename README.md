# Distributed IoT Device Management Architecture
### College DSS (Distributed Systems) Course Project & Viva Demonstration

---

## 1. Project Abstract & Problem Statement

Internet of Things (IoT) deployments in enterprise, industrial, and campus environments frequently involve dozens to thousands of distributed sensor nodes and actuators. Managing such fleets poses fundamental distributed systems challenges:
* Detecting node or network communication failures without physical presence.
* Ingesting high-velocity time-series telemetry while preserving data integrity.
* Dispatching remote control commands and tracking asynchronous execution state transitions.
* Providing persistent operational visibility and anomaly alerting through centralized dashboards.

**Problem Statement:** Setting up physical IoT hardware (microcontrollers, sensors, gateways) and cloud IoT subscriptions is cost-prohibitive and impractical for academic evaluation. Furthermore, typical student projects often resort to static, mock dashboards with fake charts that lack an underlying distributed architecture.

**Solution:** This project implements an authentic, local-first **Distributed IoT Device Management Architecture**. It simulates a fleet of 30 autonomous virtual IoT devices, exposes an interchangeable communication layer (supporting an in-memory message bus and an actual Eclipse Mosquitto MQTT broker), processes telemetry and health heartbeats, coordinates remote commands with full lifecycle tracking (`pending` $\rightarrow$ `sent` $\rightarrow$ `acknowledged`/`failed`), persists state in SQLite, and visualizes operations through a Streamlit & Plotly management console.

---

## 2. Objectives and Use Case

### Core Objectives:
1. **Decoupled Architecture:** Logically separate the virtual device fleet, communication bus, management services, database, and presentation dashboard.
2. **Health Monitoring & Fault Detection:** Implement periodic heartbeat signals to automatically detect offline devices when heartbeat timeouts elapse.
3. **Remote Actuation & Control:** Dispatch simulated commands (reboot, status poll, telemetry cycle) and dynamic reporting interval configuration updates.
4. **Time-Series Analytics:** Visualize sensor history (temperature, humidity, battery levels, signal strength) with filtering and CSV export.
5. **Zero-Cost & Low-Spec Execution:** Run natively on a standard Windows 11 laptop (8 GB RAM, no GPU, no paid cloud subscriptions).

### Example College Scenario:
Imagine monitoring 30 smart environmental sensors across campus buildings (auditorium, server rooms, chemistry labs, rooftop solar banks, and libraries). The dashboard flags an offline sensor in the server room, sounds a warning alert for low battery on a solar monitor, allows the operator to reconfigure reporting intervals from 10s to 30s, and tests device failure recovery by simulating network disconnects and reconnects.

---

## 3. Architecture & Component Responsibilities

The system is organized into 5 logical tiers:

```
[IoT Device Layer]  <--->  [Communication Layer]  <--->  [Management Layer]  <--->  [Storage Layer]
 (Virtual Sensors)          (Local Bus / MQTT)           (Services)               (SQLite DB)
                                                                 ^
                                                                 |
                                                     [Presentation Layer]
                                                     (Streamlit Dashboard)
```

1. **Virtual Device Layer (`src/device_simulator.py`):**
   * Emulates autonomous sensor nodes with unique IDs, firmware versions, battery discharge, and physical baseline variations.
   * Generates periodic telemetry and heartbeat payloads.
   * Handles incoming command payloads and emits acknowledgement packets.
2. **Communication Layer (`src/message_bus.py`, `src/mqtt_adapter.py`):**
   * Implements a unified publish/subscribe interface (`MessageBusInterface`).
   * **Default:** `LocalMessageBus` in-memory bus with pattern topic matching and wireframe activity log.
   * **Optional:** `MQTTAdapter` utilizing `paho-mqtt` to connect with an Eclipse Mosquitto broker on `localhost:1883`.
3. **Device Management Services:**
   * **Registry (`src/device_registry.py`):** Inventory lookups, device registration, and active/inactive states.
   * **Telemetry Service (`src/telemetry_service.py`):** Payload validation, normalization, and time-series queries.
   * **Alert Service (`src/alert_service.py`):** Evaluates heartbeats, flags offline nodes, triggers non-duplicated alerts.
   * **Command Service (`src/command_service.py`):** Command dispatch, timeout detection, and configuration revisions.
4. **Storage Layer (`src/database.py`):**
   * Embedded SQLite database (`iot_management.db`) initialized idempotently with tables for devices, telemetry, configurations, commands, alerts, and event logs.
5. **Presentation Layer (`app.py`, `src/charts.py`):**
   * Streamlit dashboard with Plotly charts styled in a restrained navy/charcoal palette.

---

## 4. Device Message Flow & Topic Conventions

The communication bus uses clean topic conventions:

| Topic Pattern | Payload Contents | Purpose |
| :--- | :--- | :--- |
| `iot/devices/{id}/telemetry` | `temperature`, `humidity`, `battery_level`, `uptime`, `signal_strength` | Regular sensor telemetry stream |
| `iot/devices/{id}/heartbeat` | `device_id`, `timestamp`, `status: ALIVE`, `uptime` | Periodic keep-alive pulse |
| `iot/devices/{id}/commands` | `command_id`, `command_type`, `payload`, `timestamp` | Remote command dispatch |
| `iot/devices/{id}/ack` | `command_id`, `status: acknowledged|failed`, `response` | Execution acknowledgement |

---

## 5. Database Schema Overview

* **`devices`**: `device_id` (PK), `device_type`, `name`, `location`, `registration_time`, `connection_status`, `last_seen`, `firmware_version`, `config_version`, `battery_level`, `reporting_interval`, `is_active`.
* **`telemetry`**: `id` (PK AUTOINCREMENT), `device_id` (FK), `timestamp`, `temperature`, `humidity`, `battery_level`, `signal_strength`, `uptime_seconds`, `status`.
* **`device_configurations`**: `id` (PK), `device_id` (FK), `version`, `reporting_interval`, `target_temp_min`, `target_temp_max`, `alert_threshold_battery`, `applied_at`, `status`.
* **`commands`**: `command_id` (PK), `device_id` (FK), `command_type`, `payload`, `status` (`pending`, `sent`, `acknowledged`, `failed`, `timed_out`), `response`, `created_at`, `updated_at`.
* **`alerts`**: `id` (PK), `device_id` (FK), `alert_type`, `severity`, `message`, `resolved`, `created_at`, `resolved_at`.
* **`event_logs`**: `id` (PK), `device_id`, `event_type`, `description`, `timestamp`.

---

## 6. Installation & Quick Start (Windows 11)

### Prerequisites:
* Python 3.12 (or 3.10+) installed.
* Windows PowerShell.

### Step-by-Step Launch:

1. **Open PowerShell** in the project directory:
   ```powershell
   cd "c:\Users\Adarsh\My Projects\Distributed IoT Device Management Architecture"
   ```

2. **(Optional) Create and activate a Virtual Environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies:**
   ```powershell
   python -m pip install -r requirements.txt
   ```

4. **Run the Dashboard (One-Command Startup):**
   ```powershell
   python -m streamlit run app.py
   ```
   *The Streamlit web interface will automatically launch at `http://localhost:8501`.*

5. **Run the Automated Pytest Suite:**
   ```powershell
   python -m pytest tests -v
   ```

---

## 7. Dashboard Walkthrough & Usage Guide

### Page 1 — Overview
* Displays high-level fleet metrics: Total Devices, Online Count, Offline Count, Low Battery Count, and Active Alerts.
* Interactive Plotly Donut Chart showing fleet operational distribution.
* Horizontal bar chart summarizing devices by sensor type.
* Active Alerts feed with one-click "Acknowledge & Resolve" buttons.
* Real-time telemetry pulse table.

### Page 2 — Device Registry
* Dynamic search query bar (searches device ID, name, or room location).
* Multi-attribute filters: Device Type, Campus Location, Connection Status.
* Detailed Device Inspector showing configuration revisions, battery, and firmware.
* Activation/Deactivation toggle button.
* Virtual Device Registration Form to add new sensors to both the database and simulation fleet.

### Page 3 — Telemetry & Analytics
* Time-series interactive line chart for Temperature, Humidity, Battery, and Signal Strength.
* Device-to-device comparative bar chart.
* Key aggregated statistics (Average, Minimum, Maximum).
* Downloadable CSV export button (`telemetry_export.csv`).

### Page 4 — Control Center
* Remote command dispatch (Restart, Request Telemetry, Status Poll) with safety confirmation.
* Live command acknowledgement response inspector.
* Configuration revision form (updates reporting intervals and increments configuration version).
* **Failure Simulation:** Disconnect and Reconnect virtual nodes to demonstrate offline detection.
* Raw message bus wireframe traffic inspector.
* Command execution audit log and system event history.

---

## 8. How to Demonstrate Offline Detection & Remote Commands

Use this quick demonstration sequence for college evaluators:
1. **Show Fleet Normal State:** Navigate to **Overview** and show that 27 devices are online.
2. **Simulate Node Failure:**
   * Go to **Control Center** $\rightarrow$ **Failure Simulation & Offline Detection Demo**.
   * Pick `SENSOR-001` (Ambient Room Monitor 1) and click **"Simulate Disconnect"**.
   * Click **"Scan Health"** in the sidebar.
3. **Verify Offline Detection:**
   * Return to **Overview**: Notice the offline count increases, and a critical `DEVICE_OFFLINE` alert appears with an alert timestamp.
4. **Dispatch Remote Command to Offline Device:**
   * In **Control Center**, try dispatching a **Restart** command to `SENSOR-001`.
   * Observe the command status: it reports `failed` with `"Device unreachable: simulated connection is offline."`
5. **Restore Node Connection:**
   * Click **"Reconnect Device"** and click **"Step Tick"** in the sidebar.
   * Device `SENSOR-001` transitions back to `online`, and future commands succeed.

---

## 9. How to Enable Optional MQTT Mode

The application operates out-of-the-box using the in-memory `LocalMessageBus`. To demonstrate broker-mediated communication with Eclipse Mosquitto:

1. **Install Mosquitto on Windows:**
   * Download and run the Mosquitto installer from [mosquitto.org](https://mosquitto.org/download/).
   * Start the Mosquitto broker service in a terminal:
     ```powershell
     mosquitto -v -p 1883
     ```
2. **Switch to MQTT Mode in the Dashboard:**
   * Open the dashboard $\rightarrow$ **Control Center** $\rightarrow$ **Message Bus & MQTT Configuration**.
   * Click **"Switch to MQTT Broker Mode"**.
   * The dashboard connects to `localhost:1883` and publishes/subscribes over actual MQTT network sockets.
   * If Mosquitto is not running, the application displays a friendly connection timeout and remains safely in local mode without crashing.

---

## 10. Automated Testing

All core modules are verified using isolated temporary databases:
```powershell
python -m pytest tests -v
```
**Test Coverage Includes:**
* `test_registry.py`: Table creation, duplicate ID prevention, regex validation, activation states, and filtering.
* `test_telemetry.py`: Telemetry ingestion, malformed payload rejection, aggregated math, low-battery alert creation, and duplicate alert suppression.
* `test_commands.py`: Command dispatch lifecycle, acknowledgement verification, unreachable device failure handling, configuration versions, and command timeout transitions.

---

## 11. Security Considerations for Production Deployments

In a local academic demonstration, simplicity is prioritized. For real-world IoT deployments, the following security controls are documented and recommended:
1. **Transport Layer Security (TLS):** MQTT port 8883 with X.509 client certificates to prevent eavesdropping and man-in-the-middle attacks.
2. **Mutual Authentication (mTLS):** Enforce unique cryptographic private keys stored on hardware secure elements (e.g., ATECC608A) rather than hardcoded credentials.
3. **Access Control Lists (ACLs):** Restrict devices so they can only publish to their designated topic prefix (`iot/devices/{device_id}/...`) and cannot snoop on peer nodes.
4. **Input Sanitization & Parameterized Queries:** Strictly implemented in this codebase to prevent SQL injection vulnerabilities.

---

## 12. Limitations & Future Enhancements

* **Simulation vs Real Hardware:** Virtual nodes simulate physical drift through mathematical distribution rather than analog sensor measurement.
* **Network Latency:** Local sockets have negligible packet loss compared to cellular (NB-IoT/LTE-M) or LoRaWAN deployments.
* **Future Enhancements:**
  * Add firmware over-the-air (FOTA) binary streaming simulation.
  * Integrate role-based access control (RBAC) for operators vs administrators.
  * Support geospatial mapping using GPS coordinates on an interactive campus map.

---

## 13. Viva Questions & Model Answers

**Q1: Why is this architecture considered "distributed"?**  
*Answer:* The virtual sensor agents, communication bus, management services, database, and presentation dashboard are decoupled into discrete logical components. In MQTT mode, devices and management services operate as independent publishers and subscribers coordinated entirely by a network message broker.

**Q2: What is the purpose of the heartbeat mechanism?**  
*Answer:* IoT devices often experience sudden power loss or network disconnection without sending a graceful departure notice. A periodic heartbeat signal lets the central manager detect when the elapsed time since `last_seen` exceeds an offline timeout threshold and trigger failure alerts.

**Q3: Why choose SQLite over a client-server database like PostgreSQL for this project?**  
*Answer:* SQLite is a serverless, embedded relational database that requires zero external configuration, stores data in a single portable file, supports standard SQL with foreign keys and indexes, and runs effortlessly on low-spec laptops with 8 GB RAM.

**Q4: How does the command lifecycle work?**  
*Answer:* When a command is dispatched, it transitions through well-defined states: `pending` $\rightarrow$ `sent` (published to device topic) $\rightarrow$ `acknowledged` (or `failed` if the device is unreachable). A watchdog query marks stale sent commands as `timed_out` if no response arrives within a timeout window.

**Q5: What makes MQTT ideal for IoT systems compared to HTTP?**  
*Answer:* MQTT is a lightweight, binary-based publish/subscribe protocol with tiny 2-byte header overhead, persistent keep-alive connections, and QoS levels. Unlike HTTP request-response, MQTT allows the server to push commands to devices without devices needing to run open HTTP web servers or poll continuously.
