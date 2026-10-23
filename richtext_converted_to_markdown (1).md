DSS Project: Distributed IoT Device Management Architecture
===========================================================

For your DSS subject, I recommend a Distributed IoT Device Management Dashboard that lets you monitor virtual IoT devices, check their health, send commands, update configurations, and detect offline devices.

We'll keep it suitable for your Windows 11 laptop with 8 GB RAM and no GPU. The project will work locally without paid APIs, cloud hosting, or physical IoT hardware.

The key is to build something that demonstrates an actual device-management architecture, rather than just a dashboard with dummy charts.

1\. What the project will do
----------------------------

[wetatronics.com](https://www.wetatronics.com/products/conx-portal/?utm_source=chatgpt.com)

Device Monitoring

Connected devices, offline devices, last-seen time and health status.

Live Telemetry

Temperature, humidity, battery level and signal strength.

Device Control

Send simulated commands and change device configuration.

Alerts and Logs

Detect low battery, abnormal readings, offline devices and command failures.

The image is a visual reference, not a screenshot of a finished application.

### Example scenario

Imagine you manage 30 smart sensors in a college building.

The dashboard shows 26 online devices, 3 offline devices, and 1 device reporting low battery. You select a sensor, inspect its telemetry, send a simulated restart command, and check whether the command succeeded.

This creates a useful end-to-end demonstration without buying sensors or microcontrollers.

2\. Complete system architecture
--------------------------------

The project will have logically separate device, communication, management, storage, and presentation layers. MQTT is a good fit for the optional broker-based communication mode because it uses a lightweight publish/subscribe messaging model for IoT systems.

The Standard for IoT Messaging+1

1\. IoT Device Layer

Virtual sensors · Device IDs · Telemetry · Heartbeats · Command responses

2\. Communication Layer

Default: local message simulator

Optional: MQTT broker such as Eclipse Mosquitto

3\. Device Management Service

Device registry · Telemetry ingestion · Health checks · Command handling · Configuration management

4\. Storage Layer

SQLite · Device metadata · Telemetry history · Command logs · Alerts

5\. Management Dashboard

Streamlit · Plotly · Device inventory · Controls · Reports

Local-first demonstration architecture with a replaceable messaging layer.

### How the communication works

*   Telemetry: Devices publish readings, and the management service records them.
    
*   Heartbeat: Each device periodically signals that it is active. The service marks a device offline when its heartbeat becomes stale.
    
*   Commands: An operator submits a command, which is routed to the selected device. The simulator returns a success or failure response.
    
*   Configuration: The operator changes settings such as reporting intervals. The service records the new configuration and the device's acknowledgement.
    
*   Persistence: Device information, historical readings and command results remain stored after the application restarts.
    

SQLite is a good starting point because it is an embedded, serverless database and doesn't require running a separate database server.

SQLite+1

Important distinction: the default simulator demonstrates the architecture without external services. The optional MQTT mode provides a more realistic broker-mediated communication path. The application should label simulated operations honestly and should not claim physical devices are connected.

3\. Technology stack
--------------------

Technology

Purpose

Python 3.12

Main application and device simulator

Streamlit

Web-based management dashboard

Pandas

Telemetry processing and tabular analysis

Plotly

Interactive charts

SQLite

Persistent device and event records

MQTT / Paho MQTT

Optional broker-based device communication

Pytest

Testing device management logic

Git and GitHub

Version control and submission

Mosquitto is an optional lightweight MQTT broker; it should not be required for the first-run experience.

Eclipse Mosquitto+1

Avoid React, Kubernetes, Docker, cloud IoT subscriptions, machine-learning models, and complex distributed databases. None is needed to demonstrate this project's core requirements.

4\. Main application pages
--------------------------

Page 1 — Overview

*   Total registered and online devices.
    
*   Offline and unhealthy device counts.
    
*   Average battery level.
    
*   Recent telemetry and alert summary.
    

Page 2 — Device Registry

*   Device ID, type, group and location.
    
*   Online/offline status.
    
*   Last-seen timestamp.
    
*   Search, filter and device details.
    
*   Register and deactivate virtual devices.
    

Page 3 — Telemetry and Analytics

*   Temperature and humidity trends.
    
*   Battery and signal readings.
    
*   Device-wise comparisons.
    
*   Time range and device filters.
    

Page 4 — Control Center

*   Simulated restart command.
    
*   Change telemetry reporting interval.
    
*   Configuration acknowledgement.
    
*   Command history and failure status.
    

These images are UI inspiration only. Antigravity should implement the actual controls and charts using the project's data, not insert screenshots into the application.

5\. Suggested folder structure
------------------------------

Ask Antigravity to build the following project from scratch:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   distributed-iot-management/  │  ├── app.py  ├── requirements.txt  ├── README.md  ├── .gitignore  │  ├── data/  │   └── sample_devices.csv  │  ├── src/  │   ├── device_simulator.py  │   ├── device_registry.py  │   ├── message_bus.py  │   ├── mqtt_adapter.py  │   ├── telemetry_service.py  │   ├── command_service.py  │   ├── alert_service.py  │   ├── database.py  │   └── charts.py  │  ├── tests/  │   ├── test_registry.py  │   ├── test_telemetry.py  │   └── test_commands.py  │  └── docs/      └── architecture.md   `

The application should start with app.py. SQLite tables can be initialized automatically on the first run, so you do not have to create a database manually.

The message\_bus.py module should provide a simple local simulator interface. The optional mqtt\_adapter.py should implement the same interface using MQTT, keeping the rest of the application independent of the communication method.

6\. Master prompt for Antigravity
---------------------------------

Copy this entire prompt into Antigravity. It instructs the coding agent to implement the project, test it, and deliver a working application rather than merely generating a plan.

MASTER PROMPT — DISTRIBUTED IoT DEVICE MANAGEMENT ARCHITECTURE
==============================================================

1\. Your role
-------------

Act as a practical Python developer, distributed-systems engineer, IoT developer, UI/UX designer, and software tester.

Build a complete, working college project titled **Distributed IoT Device Management Architecture**. Do not just generate a plan, mockup, static dashboard, or screenshots. Create the actual code, execute tests, run the application, and fix problems.

The result must be suitable for a DSS subject demonstration and viva.

2\. Hardware constraints
------------------------

The application must run on my Windows 11 laptop with:

*   8 GB RAM
    
*   Entry-level CPU
    
*   No dedicated GPU
    
*   No paid API keys
    
*   No cloud subscriptions
    
*   No physical IoT devices required
    

Use Python 3.12, Streamlit, Pandas, Plotly, SQLite, Pytest, and Paho MQTT for optional MQTT support.

Keep dependencies minimal. The core application must work offline after the packages have been installed.

Do not require Docker, Kubernetes, React, Node.js, a cloud database, machine-learning models, or external IoT services.

3\. Project goal
----------------

Create an IoT device management system capable of monitoring a fleet of virtual devices, collecting telemetry, detecting offline devices, managing device configurations, processing commands, maintaining event logs, and presenting operational information through a dashboard.

The architecture must separate device simulation, message transport, device management, persistence, and presentation.

Clearly distinguish simulated devices from real connected hardware.

4\. Architecture
----------------

Implement these logical layers:

1.  **Device layer:** Independent virtual IoT device agents that generate telemetry and heartbeat messages.
    
2.  **Communication layer:** A local message-bus simulator enabled by default, with optional MQTT-based messaging.
    
3.  **Management layer:** Device registration, message ingestion, health evaluation, command handling, configuration management, and alert generation.
    
4.  **Storage layer:** SQLite database containing device metadata, telemetry history, configurations, commands, and events.
    
5.  **Presentation layer:** Streamlit dashboard with device monitoring, analytics, control actions, and logs.
    

The communication interface must be replaceable. Device-management logic must not depend directly on a particular message-bus implementation.

The default simulator must function without an MQTT broker. The optional MQTT mode must use an actual MQTT client and broker when configured. Document how to install and launch Eclipse Mosquitto and how to enable MQTT mode.

Do not describe the internal simulator as a real distributed deployment. Document the difference between logical simulation and actual broker-mediated communication.

5\. Required project structure
------------------------------

Create these files:

*   app.py
    
*   requirements.txt
    
*   README.md
    
*   .gitignore
    
*   data/sample\_devices.csv
    
*   src/device\_simulator.py
    
*   src/device\_registry.py
    
*   src/message\_bus.py
    
*   src/mqtt\_adapter.py
    
*   src/telemetry\_service.py
    
*   src/command\_service.py
    
*   src/alert\_service.py
    
*   src/database.py
    
*   src/charts.py
    
*   tests/test\_registry.py
    
*   tests/test\_telemetry.py
    
*   tests/test\_commands.py
    
*   docs/architecture.md
    

Create additional files only when they improve maintainability or are genuinely necessary.

Initialize the SQLite database automatically on startup. Create all required tables and indexes safely and idempotently.

6\. Device simulator
--------------------

Generate approximately 20–50 virtual devices by default.

Use fictional device IDs such as:

*   SENSOR-001
    
*   SENSOR-002
    
*   SENSOR-003
    

Give devices different types, such as temperature sensors, humidity sensors, battery monitors, and environmental sensors.

Each device record should include:

*   Device ID
    
*   Device type
    
*   Name
    
*   Location or group
    
*   Registration timestamp
    
*   Connection status
    
*   Last-seen timestamp
    
*   Firmware version
    
*   Configuration version
    
*   Battery level where applicable
    

Generate timestamped telemetry fields such as:

*   Temperature
    
*   Humidity
    
*   Battery percentage
    
*   Signal strength
    
*   Device uptime
    
*   Device operating status
    

Not every device must support every sensor field. Handle unsupported or missing metrics properly.

Use realistic ranges and controlled variation. Give the simulator a reproducible initial seed. Generate sensor-specific readings rather than arbitrary values that change without any meaningful relationship.

Implement heartbeats and a configurable offline timeout. Include a demonstration control to simulate disconnection or reconnect a virtual device.

Keep the number of devices and stored telemetry records bounded. The application must not consume increasing amounts of memory indefinitely.

Clearly show that these readings are generated demonstration data.

7\. Device registry
-------------------

Implement functions to:

*   List all registered devices.
    
*   Retrieve a device by ID.
    
*   Register a virtual device.
    
*   Deactivate or reactivate a device.
    
*   Group devices by location or type.
    
*   Search and filter devices.
    
*   Display the latest telemetry and last-seen time.
    
*   Show firmware and configuration versions.
    

Use SQLite as the persistent source of device metadata.

Prevent duplicate device IDs and validate device attributes before writing to the database. Handle nonexistent devices gracefully.

8\. Communication layer
-----------------------

Create a simple message-bus interface with methods to publish messages and register or dispatch handlers.

### Default simulator mode

The local mode must:

*   Work without an external broker.
    
*   Generate telemetry and heartbeat events.
    
*   Deliver simulated command requests to virtual devices.
    
*   Produce acknowledgements or failure responses.
    
*   Expose recent message activity for debugging.
    

Do not create one uncontrolled background thread per device. Use a bounded, manageable simulation mechanism with safe state handling.

### Optional MQTT mode

Implement actual MQTT publish/subscribe communication using Paho MQTT and a configurable broker address and port.

Use documented topic conventions, for example:

*   iot/devices/{device\_id}/telemetry
    
*   iot/devices/{device\_id}/heartbeat
    
*   iot/devices/{device\_id}/commands
    
*   iot/devices/{device\_id}/ack
    

Validate incoming payload structure and device identifiers. Handle connection failures and missing brokers without crashing the dashboard.

Provide clear MQTT connection status and understandable troubleshooting instructions.

Do not silently pretend MQTT is active when the application is using simulated messaging.

9\. Device management services
------------------------------

Implement independent service modules.

### Telemetry service

*   Validate incoming telemetry.
    
*   Normalize timestamps and numeric fields.
    
*   Reject malformed messages.
    
*   Store valid records.
    
*   Maintain the most recent reading for each device.
    
*   Support historical queries and aggregated statistics.
    

### Health service

*   Evaluate heartbeats and last-seen time.
    
*   Identify online and offline devices.
    
*   Detect low battery and abnormal sensor readings.
    
*   Use configurable thresholds.
    
*   Avoid duplicate alert creation for the same unresolved condition.
    

Define device status consistently and document the offline timeout and threshold values.

### Command service

Provide safe, simulated device commands:

*   Restart device.
    
*   Request immediate telemetry.
    
*   Change reporting interval.
    
*   Update device configuration.
    
*   Request device status.
    

Record each command with a unique command ID, device ID, timestamp, requested action, status, and response.

Use a lifecycle such as pending, sent, acknowledged, failed, or timed\_out, with valid state transitions.

A command must target the selected device and must not merely change a success label in the UI.

The simulator must respond through the same command-handling path used by the application. In MQTT mode, route the command to the device topic and process an acknowledgement.

Never claim that physical hardware has been restarted or reconfigured when only simulation is active.

### Configuration service

Allow operators to modify supported configuration fields, such as reporting interval.

Validate configuration values, store configuration revisions, and record simulated device acknowledgement. Display the active configuration and revision in the interface.

10\. Database
-------------

Use SQLite with sensible schemas for:

*   devices
    
*   telemetry
    
*   device\_configurations
    
*   commands
    
*   alerts
    
*   event\_logs
    

Use primary keys, foreign keys where appropriate, indexes on device IDs and timestamps, and parameterized queries.

Use transactions for operations that modify related records. Avoid loading the complete telemetry history into memory when a filtered SQL query will suffice.

Use Python's standard sqlite3 module unless another dependency is clearly justified.

Ensure the data survives application restarts. Include a safe database initialization and sample-data seeding process that does not duplicate seed records on every launch.

11\. Dashboard pages
--------------------

Build four complete navigation sections.

### Page A: Overview

Display:

*   Total registered devices
    
*   Online devices
    
*   Offline devices
    
*   Devices requiring attention
    
*   Recent alerts
    
*   Telemetry activity
    
*   A chart showing device status distribution
    
*   A historical telemetry chart
    

All KPI values must be computed from database records.

### Page B: Device Registry

Include:

*   Search and filter controls
    
*   Device ID and type
    
*   Location and group
    
*   Online/offline status
    
*   Last-seen timestamp
    
*   Battery level
    
*   Firmware and configuration versions
    
*   Device detail view
    
*   Register and deactivate/reactivate controls
    

Use clear status labels. Do not use color as the only indicator of a device's status.

### Page C: Telemetry and Analytics

Include:

*   Temperature and humidity history where supported
    
*   Battery and signal trends
    
*   Device comparison
    
*   Latest readings
    
*   Time-range filtering
    
*   Device and device-type filters
    
*   Summary statistics
    
*   Data export to CSV
    

Show units and timestamps clearly. Handle missing readings and empty result sets gracefully.

### Page D: Control Center

Include:

*   Device selection
    
*   Supported simulated command selection
    
*   Configuration update form
    
*   Confirmation before executing a command
    
*   Command submission result
    
*   Acknowledgement or failure status
    
*   Recent command history
    
*   Alert and event logs
    
*   A device disconnect/reconnect demonstration control
    

Every visible action must be functional and must update actual application state or database records.

12\. User interface
-------------------

Create a professional, clean device-operations dashboard suitable for a college engineering demonstration.

Use:

*   A restrained navy, charcoal, white, and blue palette
    
*   Consistent typography and spacing
    
*   Compact status cards
    
*   Readable data tables
    
*   Clear headings and section labels
    
*   Consistent chart formatting
    
*   Useful empty states
    
*   Responsive columns and sidebar controls
    
*   Clear success, warning, and error messages
    

Avoid generic AI-looking design, huge decorative headers, excessive gradients, unnecessary animations, emoji-heavy interfaces, huge rounded cards, and fake functionality.

Make the most important device status information immediately visible.

Use Streamlit-native components first. Add custom CSS only where it materially improves readability.

13\. Refresh and application state
----------------------------------

Provide a manual refresh button and an optional automatic refresh mechanism with a configurable interval.

The automatic refresh must be optional, disabled by default, and safe to enable or disable.

Avoid endless rerun loops, repeated database initialization, duplicated event listeners, competing timers, and unbounded background threads.

Use Streamlit state and database persistence appropriately. Ensure that refreshing the page does not unexpectedly repeat a command or create duplicate devices.

If a simulation loop is needed, it must be bounded, predictable, and safe to stop.

14\. Security and reliability
-----------------------------

Demonstrate practical security-conscious design:

*   Validate device IDs and incoming payloads.
    
*   Use parameterized database operations.
    
*   Avoid hard-coded secrets.
    
*   Do not log authentication tokens or credentials.
    
*   Restrict MQTT configuration to supported connection settings.
    
*   Keep local demo operations clearly separated from production device controls.
    
*   Document the need for MQTT authentication, TLS, authorization rules, secure device identity, and network restrictions in a real deployment.
    

Do not claim production-grade security without implementing and testing it.

Never provide controls that unexpectedly access local hardware, execute shell commands, or perform real firmware flashing.

15\. Testing requirements
-------------------------

Create and execute tests for:

*   Database initialization and persistence
    
*   Device registration and duplicate IDs
    
*   Device status and heartbeat expiration
    
*   Valid and invalid telemetry
    
*   Telemetry history queries
    
*   Low-battery and abnormal-reading alerts
    
*   Command creation and state transitions
    
*   Command acknowledgements and failures
    
*   Configuration validation
    
*   Empty device lists and missing records
    
*   Malformed message payloads
    

Use isolated test databases so tests cannot damage actual application data.

Fix test failures before reporting completion. Do not mark unexecuted tests as passed.

Perform a manual smoke test of the dashboard and important user actions.

16\. Performance constraints
----------------------------

Use simple, efficient data structures and bounded telemetry retention.

Do not generate thousands of records on every Streamlit rerun. Use caching carefully without serving stale device status or command results.

Avoid unnecessary database polling, excessive refreshes, and expensive chart updates.

The standard simulation should run comfortably on an 8 GB RAM Windows laptop without a GPU. Explain that performance depends on the selected history size and refresh frequency.

17\. Documentation
------------------

Create a complete README with:

1.  Project abstract and problem statement.
    
2.  Objectives and use case.
    
3.  Architecture explanation.
    
4.  Component responsibilities.
    
5.  Device message flow.
    
6.  Database schema overview.
    
7.  Installation instructions for Windows.
    
8.  One-command application startup.
    
9.  Dashboard usage guide.
    
10.  How to demonstrate commands and offline detection.
    
11.  How to enable optional MQTT mode.
    
12.  How to run the tests.
    
13.  Security considerations.
    
14.  Limitations of simulation.
    
15.  Future enhancements.
    
16.  Viva questions and answers.
    

In docs/architecture.md, explain the difference between device agents, the message broker, management services, persistence, and the dashboard. Include a Mermaid component diagram and sequence diagrams for telemetry ingestion and command acknowledgement.

18\. Acceptance criteria
------------------------

The project is complete only when:

*   The required source files and documentation exist.
    
*   The application works in simulator mode without an external MQTT broker.
    
*   Sample virtual devices appear on first launch.
    
*   Device status changes according to heartbeat and offline rules.
    
*   Telemetry is validated and persisted.
    
*   Charts use actual stored readings.
    
*   Search and filters work.
    
*   Commands have recorded results and valid state transitions.
    
*   Configuration updates persist.
    
*   Alerts and event logs work.
    
*   Refreshing the app does not create duplicates.
    
*   CSV export works.
    
*   Optional MQTT mode is separated from simulator mode and has useful error handling.
    
*   Automated tests have actually been run.
    
*   There are no obvious broken buttons, placeholder pages, or unresolved runtime exceptions.
    

19\. Final execution instructions
---------------------------------

Inspect the existing project directory before making changes. Build the implementation incrementally and verify each layer.

First implement and test database operations, device simulation, and message handling. Next implement device management services, then the dashboard, tests, and documentation.

After implementation:

1.  Install only the required dependencies.
    
2.  Initialize sample data.
    
3.  Run all automated tests.
    
4.  Start the dashboard.
    
5.  Test each major interaction.
    
6.  Fix discovered errors.
    
7.  Verify the exact commands needed to run it from Windows PowerShell.
    

Do not stop after writing the plan. Create the project files and run the implementation.

At the end, report the files created, implemented features, actual test results, the exact launch commands, any remaining limitations, and a brief demonstration plan for the college evaluator.

7\. How to run it on your laptop
--------------------------------

Open PowerShell inside the folder containing app.py and requirements.txt.

Step 1 — Create environment

Copy

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   py -3.12 -m venv .venv   `

Step 2 — Activate environment

Copy

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   .\.venv\Scripts\Activate.ps1   `

Step 3 — Install packages

Copy

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python -m pip install -r requirements.txt   `

Step 4 — Start the application

Copy

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python -m streamlit run app.py   `

Step 5 — Run the tests

Copy

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python -m pytest tests -v   `

You only need the optional MQTT broker when testing broker-based communication. The initial simulator mode should run without it.

8\. How to demonstrate the project to your lecturer
---------------------------------------------------

Use this five-minute demonstration sequence:

1.  Show the device registry. Explain how each device has a unique ID, type, configuration and status.
    
2.  Show telemetry. Open a sensor and demonstrate how new readings enter the system and appear in historical charts.
    
3.  Simulate a failure. Disconnect a virtual device, show its last-seen time and demonstrate offline detection.
    
4.  Send a command. Change a reporting interval or send a simulated restart. Show the command record and acknowledgement.
    
5.  Explain the distributed architecture. Show how the optional MQTT broker separates publishers and subscribers, and explain how SQLite preserves device and event history.
    

9\. What to explain in the viva
-------------------------------

Question

Main point

Why is the architecture distributed?

Device agents, communication, management and the user interface are separated into logical components; MQTT mode demonstrates broker-mediated communication.

Why MQTT?

It supports lightweight publish/subscribe messaging suitable for IoT devices.

The Standard for IoT Messaging+1

What is a heartbeat?

A periodic signal used to assess whether a device is still communicating.

How is an offline device detected?

Its last-seen time exceeds a configured heartbeat timeout.

Why SQLite?

It provides persistent relational storage without requiring a separate database server.

SQLite+1

Is this a production-scale IoT deployment?

No. The initial version is a local demonstration with virtual devices; MQTT adds a more realistic communication mode.

My recommendation: Start with the default simulator and get all four dashboard sections working before enabling MQTT. This gives you a complete project that is easier to run, explain, test and demonstrate on your laptop.