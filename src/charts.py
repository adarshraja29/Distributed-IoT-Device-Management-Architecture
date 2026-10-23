"""
Distributed IoT Device Management Architecture - Charts & Visualizations
Generates clean, professional Plotly charts styled with a restrained navy/charcoal palette.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Design Palette: restrained professional engineering theme
COLOR_ONLINE = "#10B981"    # Emerald
COLOR_OFFLINE = "#EF4444"   # Crimson
COLOR_INACTIVE = "#94A3B8"  # Slate Gray
COLOR_PRIMARY = "#1E40AF"   # Deep Navy
COLOR_SECONDARY = "#3B82F6" # Electric Blue
COLOR_WARNING = "#F59E0B"   # Amber
COLOR_BG = "#FFFFFF"

LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", size=12, color="#1E293B"),
    plot_bgcolor=COLOR_BG,
    paper_bgcolor=COLOR_BG,
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)


def create_status_donut_chart(status_counts: Dict[str, int]) -> go.Figure:
    """Creates a donut chart representing fleet online, offline, and inactive distribution."""
    labels = ["Online", "Offline", "Inactive"]
    values = [
        status_counts.get("online", 0),
        status_counts.get("offline", 0),
        status_counts.get("inactive", 0)
    ]
    colors = [COLOR_ONLINE, COLOR_OFFLINE, COLOR_INACTIVE]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+value",
        hoverinfo="label+value+percent",
        textposition="inside"
    )])

    fig.update_layout(
        title="Fleet Operational Status",
        **LAYOUT_DEFAULTS
    )
    return fig


def create_device_type_bar_chart(devices: List[Dict[str, Any]]) -> go.Figure:
    """Creates a bar chart displaying count of devices by type."""
    if not devices:
        fig = go.Figure()
        fig.update_layout(title="No devices registered", **LAYOUT_DEFAULTS)
        return fig

    df = pd.DataFrame(devices)
    type_counts = df["device_type"].value_counts().reset_index()
    type_counts.columns = ["Device Type", "Count"]

    fig = px.bar(
        type_counts,
        x="Count",
        y="Device Type",
        orientation="h",
        color_discrete_sequence=[COLOR_PRIMARY],
        text="Count"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Device Fleet by Type",
        xaxis_title="Registered Units",
        yaxis_title="",
        **LAYOUT_DEFAULTS
    )
    return fig


def create_telemetry_trend_chart(
    telemetry_records: List[Dict[str, Any]],
    metric: str = "temperature",
    title: Optional[str] = None
) -> go.Figure:
    """
    Creates a time-series line chart for a specific metric (temperature, humidity, battery_level).
    Supports multi-device overlays if multiple devices are present in records.
    """
    if not telemetry_records:
        fig = go.Figure()
        fig.update_layout(
            title=title or f"No historical {metric} data available",
            **LAYOUT_DEFAULTS
        )
        return fig

    df = pd.DataFrame(telemetry_records)
    if metric not in df.columns or df[metric].dropna().empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Metric '{metric}' not reported by selected device(s)",
            **LAYOUT_DEFAULTS
        )
        return fig

    # Ensure timestamp sorting
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp")

    units = {
        "temperature": "°C",
        "humidity": "% RH",
        "battery_level": "%",
        "signal_strength": "dBm"
    }
    unit_str = units.get(metric, "")

    fig = px.line(
        df,
        x="timestamp",
        y=metric,
        color="device_id",
        markers=True,
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, "#0D9488", "#7C3AED", "#D97706"]
    )

    fig.update_layout(
        title=title or f"Historical Trend: {metric.replace('_', ' ').capitalize()} ({unit_str})",
        xaxis_title="Timestamp (UTC)",
        yaxis_title=f"{metric.replace('_', ' ').capitalize()} ({unit_str})",
        **LAYOUT_DEFAULTS
    )
    return fig


def create_device_comparison_bar(latest_readings: List[Dict[str, Any]], metric: str = "battery_level") -> go.Figure:
    """Compares the latest reading for a given metric across selected devices."""
    if not latest_readings:
        fig = go.Figure()
        fig.update_layout(title="No telemetry records to compare", **LAYOUT_DEFAULTS)
        return fig

    df = pd.DataFrame(latest_readings)
    if metric not in df.columns or df[metric].dropna().empty:
        fig = go.Figure()
        fig.update_layout(title=f"No readings found for {metric}", **LAYOUT_DEFAULTS)
        return fig

    df = df.dropna(subset=[metric]).head(15)  # top 15 devices for readability

    color_seq = COLOR_PRIMARY if metric != "battery_level" else COLOR_SECONDARY
    fig = px.bar(
        df,
        x="device_id",
        y=metric,
        hover_data=["name", "location"],
        color_discrete_sequence=[color_seq],
        text=metric
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        title=f"Comparative Latest {metric.replace('_', ' ').capitalize()} Across Devices",
        xaxis_title="Device ID",
        yaxis_title=metric.replace('_', ' ').capitalize(),
        **LAYOUT_DEFAULTS
    )
    return fig
