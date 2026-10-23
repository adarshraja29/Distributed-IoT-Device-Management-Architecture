"""
Distributed IoT Device Management Architecture - Master Dashboard
A professional, local-first Streamlit operations dashboard for monitoring, controlling,
and analyzing distributed IoT devices for academic DSS demonstration.
"""

import os
import sys
import time
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import init_db, seed_initial_data, prune_old_telemetry, DEFAULT_DB_PATH
from src.message_bus import get_default_message_bus, LocalMessageBus
from src.mqtt_adapter import MQTTAdapter, PAHO_AVAILABLE
from src.device_simulator import get_fleet_simulator
from src.device_registry import get_device_registry
from src.telemetry_service import get_telemetry_service
from src.command_service import get_command_service
from src.alert_service import get_alert_service
from src import charts

# Page Configuration
st.set_page_config(
    page_title="Distributed IoT Management Architecture",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling: Restrained navy, slate, charcoal, and crisp white theme
st.markdown("""
<style>
    /* Base typography and clean headers */
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: inherit;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: inherit;
        opacity: 0.8;
        margin-bottom: 1.2rem;
    }
    .card-metric {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px 16px;
    }
    .status-badge-online {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-badge-offline {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    /* Compact buttons & forms */
    .stButton>button {
        border-radius: 4px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


def initialize_app_state():
    """Initializes database, fleet simulator agents, and session state variables idempotently."""
    if "app_initialized" not in st.session_state:
        # 1. Initialize SQLite schema & seed sample devices
        init_db()
        seed_initial_data()

        # 2. Wire simulator with database devices
        registry = get_device_registry()
        devices = registry.list_devices()
        simulator = get_fleet_simulator()
        simulator.load_from_db_records(devices)

        # 3. Session state flags
        st.session_state.app_initialized = True
        st.session_state.bus_mode = "local"  # 'local' or 'mqtt'
        st.session_state.mqtt_adapter = None
        st.session_state.offline_timeout_seconds = 60


initialize_app_state()

# Services
registry = get_device_registry()
telemetry_service = get_telemetry_service()
command_service = get_command_service()
alert_service = get_alert_service()
simulator = get_fleet_simulator()
local_bus = get_default_message_bus()

# Sidebar: Controls & Navigation
with st.sidebar:
    st.markdown("### 🏢 IoT Architecture Console")
    st.caption("College DSS Demonstration System")

    page_options = ["Overview", "Device Registry", "Telemetry & Analytics", "Control Center"]
    query_page = st.query_params.get("page")
    default_index = page_options.index(query_page) if query_page in page_options else 0

    nav_page = st.radio(
        "Navigation",
        page_options,
        index=default_index
    )

    st.markdown("---")
    st.markdown("#### ⚙️ Fleet Simulation Control")

    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        if st.button("▶ Step Tick", help="Trigger 1 immediate simulation cycle for connected devices", use_container_width=True):
            emitted = simulator.step()
            st.toast(f"Generated telemetry & heartbeats ({emitted} messages)", icon="📡")
            st.rerun()

    with col_sim2:
        if st.button("🔍 Scan Health", help="Run offline heartbeat timeout & threshold check", use_container_width=True):
            res = alert_service.evaluate_fleet_health(offline_timeout_seconds=st.session_state.offline_timeout_seconds)
            command_service.check_and_update_timeouts()
            st.toast(f"Evaluated: {res['marked_offline']} marked offline, {res['new_alerts']} alerts", icon="🛡️")
            st.rerun()

    # Communication Mode Display
    st.markdown("---")
    st.markdown("#### 🔌 Communication Bus")
    if st.session_state.bus_mode == "local":
        st.info("Mode: **Local Simulator Bus** (In-Memory)")
    else:
        st.success(f"Mode: **MQTT Broker** ({st.session_state.mqtt_adapter.broker_host})")

    # Refresh Options
    st.markdown("---")
    st.markdown("#### 🔄 Refresh Controls")
    if st.button("Manual Refresh", use_container_width=True):
        st.rerun()

    auto_refresh = st.checkbox("Auto-refresh page", value=False)
    if auto_refresh:
        refresh_rate = st.slider("Interval (seconds)", min_value=5, max_value=60, value=15, step=5)
        # Sleep briefly then rerun safely
        time.sleep(refresh_rate)
        simulator.step()
        alert_service.evaluate_fleet_health(offline_timeout_seconds=st.session_state.offline_timeout_seconds)
        st.rerun()


# ==============================================================================
# PAGE 1: OVERVIEW
# ==============================================================================
if nav_page == "Overview":
    st.markdown('<div class="main-header">Fleet Operational Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">System-wide operational metrics, connection health, and real-time alert summary.</div>', unsafe_allow_html=True)

    stats = registry.get_summary_stats()

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.metric(label="Total Devices", value=stats["total"])
    with kpi2:
        st.metric(label="Online Devices", value=stats["online"], delta=f"{stats['online']}/{stats['total']} Active")
    with kpi3:
        st.metric(label="Offline Devices", value=stats["offline"], delta=f"-{stats['offline']}" if stats['offline'] > 0 else "0", delta_color="inverse")
    with kpi4:
        st.metric(label="Low Battery (<20%)", value=stats["low_battery"], delta="Requires Charge" if stats["low_battery"] > 0 else "Normal", delta_color="inverse")
    with kpi5:
        st.metric(label="Active Alerts", value=stats["active_alerts"], delta="Attention" if stats["active_alerts"] > 0 else "Clear", delta_color="inverse")

    st.markdown("---")

    # Visualizations Row
    col_chart1, col_chart2 = st.columns([1, 1])
    with col_chart1:
        status_counts = {"online": stats["online"], "offline": stats["offline"], "inactive": stats["inactive"]}
        fig_donut = charts.create_status_donut_chart(status_counts)
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_chart2:
        all_devices = registry.list_devices()
        fig_types = charts.create_device_type_bar_chart(all_devices)
        st.plotly_chart(fig_types, use_container_width=True)

    # Alerts and Recent Telemetry Pulse
    st.markdown("---")
    col_alerts, col_telemetry = st.columns([1, 1])

    with col_alerts:
        st.markdown("#### ⚠️ Active Alerts & System Incidents")
        unresolved_alerts = alert_service.list_alerts(unresolved_only=True, limit=6)
        if unresolved_alerts:
            for alert in unresolved_alerts:
                sev_icon = "🔴" if alert["severity"] == "critical" else "🟡"
                with st.expander(f"{sev_icon} [{alert['alert_type']}] Device: {alert['device_id']} - {alert['created_at']}"):
                    st.write(f"**Message:** {alert['message']}")
                    st.caption(f"Logged at: {alert['created_at']} | Severity: {alert['severity'].upper()}")
                    if st.button("Acknowledge & Resolve", key=f"res_{alert['id']}"):
                        alert_service.resolve_alert(alert["id"])
                        st.toast("Alert marked as resolved.", icon="✅")
                        st.rerun()
        else:
            st.success("No active critical or warning alerts in the system.")

    with col_telemetry:
        st.markdown("#### 📡 Latest Telemetry Activity")
        latest_readings = telemetry_service.get_latest_readings_all()
        if latest_readings:
            df_tel = pd.DataFrame(latest_readings)[["device_id", "name", "temperature", "humidity", "battery_level", "timestamp"]].head(6)
            st.dataframe(df_tel, use_container_width=True, hide_index=True)
        else:
            st.info("No telemetry recorded yet. Click 'Step Tick' in the sidebar to simulate readings.")


# ==============================================================================
# PAGE 2: DEVICE REGISTRY
# ==============================================================================
elif nav_page == "Device Registry":
    st.markdown('<div class="main-header">IoT Device Registry</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage virtual device inventory, metadata, location groupings, and active states.</div>', unsafe_allow_html=True)

    # Search & Filter Controls
    col_search, col_filter_type, col_filter_loc, col_filter_status = st.columns([2, 1, 1, 1])
    with col_search:
        search_query = st.text_input("🔍 Search by ID, Name, or Location", value="")
    with col_filter_type:
        types_list = ["All"] + registry.get_all_types()
        sel_type = st.selectbox("Device Type", types_list, index=0)
    with col_filter_loc:
        locs_list = ["All"] + registry.get_all_locations()
        sel_loc = st.selectbox("Location", locs_list, index=0)
    with col_filter_status:
        sel_status = st.selectbox("Connection Status", ["All", "online", "offline"], index=0)

    # Query filtered devices
    filtered_devices = registry.list_devices(
        search=search_query if search_query else None,
        device_type=sel_type,
        location=sel_loc,
        connection_status=sel_status
    )

    st.markdown(f"**Showing {len(filtered_devices)} registered devices**")

    if filtered_devices:
        df_dev = pd.DataFrame(filtered_devices)[[
            "device_id", "device_type", "name", "location", "connection_status",
            "battery_level", "last_seen", "firmware_version", "config_version", "is_active"
        ]]
        st.dataframe(df_dev, use_container_width=True, hide_index=True)
    else:
        st.warning("No devices matching your filter criteria were found.")

    st.markdown("---")

    # Two columns: Inspector & Device Registration
    col_inspect, col_register = st.columns([1, 1])

    with col_inspect:
        st.markdown("#### 🔬 Device Detail Inspector")
        if filtered_devices:
            dev_options = [d["device_id"] for d in filtered_devices]
            sel_inspect_id = st.selectbox("Select Device to Inspect", dev_options)
            inspect_dev = registry.get_device(sel_inspect_id)

            if inspect_dev:
                st.write(f"**Device ID:** `{inspect_dev['device_id']}`")
                st.write(f"**Name:** {inspect_dev['name']}")
                st.write(f"**Location:** {inspect_dev['location']}")
                st.write(f"**Type:** {inspect_dev['device_type']}")
                st.write(f"**Connection Status:** `{inspect_dev['connection_status'].upper()}`")
                st.write(f"**Battery Level:** {inspect_dev['battery_level']}%")
                st.write(f"**Last Seen:** {inspect_dev['last_seen']}")
                st.write(f"**Reporting Interval:** {inspect_dev['reporting_interval']}s")
                st.write(f"**Firmware:** `{inspect_dev['firmware_version']}` | **Config Rev:** `v{inspect_dev['config_version']}`")

                # Activate / Deactivate Toggle
                is_active = bool(inspect_dev["is_active"])
                btn_label = "Deactivate Device" if is_active else "Reactivate Device"
                if st.button(btn_label, key=f"toggle_{inspect_dev['device_id']}"):
                    registry.set_active_state(inspect_dev["device_id"], not is_active)
                    st.toast(f"Device {inspect_dev['device_id']} updated.", icon="🔄")
                    st.rerun()

    with col_register:
        st.markdown("#### ➕ Register New Virtual Device")
        with st.form("form_register_device"):
            new_id = st.text_input("Device ID (e.g. SENSOR-031)", value="").strip()
            new_type = st.selectbox("Device Type", ["environmental", "temperature", "humidity", "battery_monitor"])
            new_name = st.text_input("Device Name", value="").strip()
            new_loc = st.text_input("Location / Campus Zone", value="Building A - Lab 102").strip()
            new_interval = st.number_input("Reporting Interval (seconds)", min_value=1, max_value=3600, value=10)
            new_firmware = st.text_input("Firmware Version", value="v1.0.0").strip()

            submit_reg = st.form_submit_button("Register Device")
            if submit_reg:
                try:
                    reg_dev = registry.register_device(
                        device_id=new_id,
                        device_type=new_type,
                        name=new_name,
                        location=new_loc,
                        reporting_interval=new_interval,
                        firmware_version=new_firmware
                    )
                    # Also register with virtual fleet simulator
                    from src.device_simulator import VirtualDeviceAgent
                    agent = VirtualDeviceAgent(
                        device_id=new_id,
                        device_type=new_type,
                        name=new_name,
                        location=new_loc,
                        reporting_interval=new_interval,
                        firmware_version=new_firmware
                    )
                    simulator.register_device(agent)
                    st.success(f"Device {new_id} successfully registered into inventory and simulation fleet!")
                    st.rerun()
                except ValueError as err:
                    st.error(f"Registration Error: {str(err)}")


# ==============================================================================
# PAGE 3: TELEMETRY AND ANALYTICS
# ==============================================================================
elif nav_page == "Telemetry & Analytics":
    st.markdown('<div class="main-header">Telemetry Analytics & Historical Trends</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Inspect time-series telemetry streams, cross-device comparisons, and export audit datasets.</div>', unsafe_allow_html=True)

    all_devs = registry.list_devices()
    dev_ids = ["All"] + [d["device_id"] for d in all_devs]

    col_dev, col_metric, col_limit = st.columns([2, 1, 1])
    with col_dev:
        sel_analytics_dev = st.selectbox("Filter Device", dev_ids, index=0)
    with col_metric:
        sel_metric = st.selectbox("Primary Metric", ["temperature", "humidity", "battery_level", "signal_strength"], index=0)
    with col_limit:
        sel_limit = st.select_slider("Sample Size (records)", options=[50, 100, 200, 500], value=100)

    # Fetch History
    history = telemetry_service.get_device_history(
        device_id=sel_analytics_dev,
        limit=sel_limit
    )

    # Aggregated KPI Summary
    stats_data = telemetry_service.get_aggregated_stats(device_id=sel_analytics_dev)
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Data Points", stats_data["count"])
    with s2:
        st.metric("Avg Temperature", f"{stats_data['avg_temp']}°C" if stats_data['avg_temp'] is not None else "N/A")
    with s3:
        st.metric("Avg Humidity", f"{stats_data['avg_hum']}%" if stats_data['avg_hum'] is not None else "N/A")
    with s4:
        st.metric("Avg Battery", f"{stats_data['avg_battery']}%" if stats_data['avg_battery'] is not None else "N/A")

    st.markdown("---")

    # Time-series line chart
    fig_trend = charts.create_telemetry_trend_chart(
        telemetry_records=history,
        metric=sel_metric,
        title=f"Time Series Trend: {sel_metric.replace('_', ' ').capitalize()} ({sel_analytics_dev})"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Comparative Bar Chart
    latest_readings = telemetry_service.get_latest_readings_all()
    if latest_readings:
        fig_comp = charts.create_device_comparison_bar(latest_readings, metric=sel_metric)
        st.plotly_chart(fig_comp, use_container_width=True)

    # Tabular View & CSV Export
    st.markdown("---")
    st.markdown("#### 📋 Telemetry Records & Export")
    if history:
        df_hist = pd.DataFrame(history)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        csv_data = df_hist.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Telemetry as CSV",
            data=csv_data,
            file_name=f"telemetry_export_{sel_analytics_dev}_{int(time.time())}.csv",
            mime="text/csv"
        )
    else:
        st.info("No historical records matching the filter criteria.")


# ==============================================================================
# PAGE 4: CONTROL CENTER
# ==============================================================================
elif nav_page == "Control Center":
    st.markdown('<div class="main-header">Device Control Center & Remote Operations</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Dispatch simulated remote commands, reconfigure devices, test failure modes, and view event logs.</div>', unsafe_allow_html=True)

    all_devs = registry.list_devices()
    if not all_devs:
        st.error("No registered devices available for control.")
        st.stop()

    dev_options = [d["device_id"] for d in all_devs]

    col_cmd, col_cfg = st.columns([1, 1])

    with col_cmd:
        st.markdown("#### 🎯 Dispatch Remote Command")
        target_dev_id = st.selectbox("Select Target Device", dev_options, key="cmd_target_dev")
        target_dev = registry.get_device(target_dev_id)

        cmd_action = st.selectbox(
            "Select Command Action",
            ["restart", "request_telemetry", "status_poll"],
            format_func=lambda x: {
                "restart": "Restart Device (Reboot & Reset Uptime)",
                "request_telemetry": "Request Immediate Telemetry",
                "status_poll": "Poll Operational Status"
            }.get(x, x)
        )

        confirm_cmd = st.checkbox("Confirm command execution before dispatch", value=True)

        if st.button("🚀 Execute Remote Command", key="btn_exec_cmd"):
            if not confirm_cmd:
                st.warning("Please confirm the command checkbox before submitting.")
            else:
                with st.spinner(f"Routing command to {target_dev_id}..."):
                    result = command_service.dispatch_command(
                        device_id=target_dev_id,
                        command_type=cmd_action
                    )
                    # If using local bus, acknowledgement occurs synchronously
                    ack_info = command_service.get_command(result["command_id"])
                    if ack_info and ack_info["status"] == "acknowledged":
                        st.success(f"Command `{ack_info['command_id']}` Acknowledged: {ack_info['response']}")
                    elif ack_info and ack_info["status"] == "failed":
                        st.error(f"Command Failed: {ack_info['response']}")
                    else:
                        st.info(f"Command Dispatched with ID: {result['command_id']}")

    with col_cfg:
        st.markdown("#### 🛠️ Update Device Configuration")
        cfg_dev_id = st.selectbox("Select Device to Configure", dev_options, key="cfg_target_dev")
        cfg_dev = registry.get_device(cfg_dev_id)

        current_interval = cfg_dev.get("reporting_interval", 10) if cfg_dev else 10
        current_version = cfg_dev.get("config_version", 1) if cfg_dev else 1

        st.caption(f"Active Configuration: **v{current_version}** | Current Interval: **{current_interval}s**")

        new_reporting_interval = st.number_input(
            "New Telemetry Interval (seconds)",
            min_value=1,
            max_value=3600,
            value=current_interval,
            step=5
        )

        if st.button("💾 Apply Configuration Revision", key="btn_apply_cfg"):
            try:
                res = command_service.update_configuration(
                    device_id=cfg_dev_id,
                    reporting_interval=new_reporting_interval
                )
                st.success(f"Configuration updated to v{current_version + 1}! Acknowledgement: {res.get('status', 'sent')}")
                st.rerun()
            except ValueError as err:
                st.error(f"Configuration Error: {str(err)}")

    # Failure Demonstration & Disconnect Testing
    st.markdown("---")
    st.markdown("#### 🧪 Failure Simulation & Offline Detection Demo")
    st.write(
        "For college demonstration, disconnect a virtual device to stop its heartbeats, "
        "then run the health evaluation to observe how the architecture flags offline devices and triggers alerts."
    )

    col_fail1, col_fail2, col_fail3 = st.columns([2, 1, 1])
    with col_fail1:
        fail_dev_id = st.selectbox("Select Device for Connectivity Testing", dev_options, key="fail_dev")
        fail_dev_record = registry.get_device(fail_dev_id)
        current_conn = fail_dev_record["connection_status"] if fail_dev_record else "unknown"
        st.write(f"Current Status: **`{current_conn.upper()}`**")

    with col_fail2:
        if st.button("🔌 Simulate Disconnect", help="Cuts virtual connection; stops device from responding to heartbeats or commands"):
            simulator.set_device_connection(fail_dev_id, False)
            registry.update_connection_status(fail_dev_id, "offline")
            alert_service.evaluate_fleet_health(offline_timeout_seconds=0)
            st.toast(f"Device {fail_dev_id} disconnected.", icon="⚠️")
            st.rerun()

    with col_fail3:
        if st.button("⚡ Reconnect Device", help="Restores virtual network link and resumes heartbeats"):
            simulator.set_device_connection(fail_dev_id, True)
            registry.update_connection_status(fail_dev_id, "online")
            st.toast(f"Device {fail_dev_id} reconnected.", icon="✅")
            st.rerun()

    # Communication Bus Switcher (Local Simulator vs MQTT Mode)
    st.markdown("---")
    st.markdown("#### 🌐 Message Bus & MQTT Configuration")
    st.write("Demonstrates pluggable communication architecture: switch between in-memory message bus and an actual MQTT broker.")

    col_bus1, col_bus2 = st.columns([1, 1])
    with col_bus1:
        st.write(f"**Current Active Mode:** `{st.session_state.bus_mode.upper()}`")
        if st.session_state.bus_mode == "local":
            if st.button("Switch to MQTT Broker Mode"):
                if not PAHO_AVAILABLE:
                    st.error("paho-mqtt is not installed in Python environment.")
                else:
                    adapter = MQTTAdapter(broker_host="localhost", broker_port=1883)
                    if adapter.connect(timeout=2.0):
                        st.session_state.mqtt_adapter = adapter
                        st.session_state.bus_mode = "mqtt"
                        st.success("Connected to Eclipse Mosquitto broker!")
                        st.rerun()
                    else:
                        st.error(f"MQTT Connection Failed: {adapter.get_last_error()}")
                        st.info("Tip: Ensure Eclipse Mosquitto is running on localhost:1883, or stay in Local Simulator mode.")
        else:
            if st.button("Switch back to Local Simulator Bus"):
                if st.session_state.mqtt_adapter:
                    st.session_state.mqtt_adapter.disconnect()
                st.session_state.bus_mode = "local"
                st.success("Reverted to Local Simulator mode.")
                st.rerun()

    with col_bus2:
        st.markdown("**Recent Bus Activity (Raw Wire Frames)**")
        active_bus = st.session_state.mqtt_adapter if st.session_state.bus_mode == "mqtt" and st.session_state.mqtt_adapter else local_bus
        recent_frames = active_bus.get_recent_messages(limit=6)
        if recent_frames:
            for frame in recent_frames:
                st.caption(f"**Topic:** `{frame['topic']}` [{frame['timestamp']}]")
        else:
            st.caption("No messages published on bus yet.")

    # Recent Commands Table & Event Audit Log
    st.markdown("---")
    col_hist_cmd, col_event_log = st.columns([1, 1])

    with col_hist_cmd:
        st.markdown("#### 📜 Recent Command History")
        cmds = command_service.list_commands(limit=10)
        if cmds:
            df_cmds = pd.DataFrame(cmds)[["command_id", "device_id", "command_type", "status", "response", "created_at"]]
            st.dataframe(df_cmds, use_container_width=True, hide_index=True)
        else:
            st.caption("No commands have been dispatched yet.")

    with col_event_log:
        st.markdown("#### 📋 System & Device Audit Logs")
        events = alert_service.list_event_logs(limit=10)
        if events:
            df_events = pd.DataFrame(events)[["device_id", "event_type", "description", "timestamp"]]
            st.dataframe(df_events, use_container_width=True, hide_index=True)
        else:
            st.caption("No event logs recorded.")
