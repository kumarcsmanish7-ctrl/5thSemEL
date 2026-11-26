"""Live SOC dashboard for video and network integration data."""
import json
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_webrtc import webrtc_streamer

from src.config import ROUTING_WEIGHTS
from src.rag_engine import RAGSecurityEngine

st.set_page_config(
    page_title="Cyber-Resilient CCTV SOC",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 18rem !important;
        min-width: 18rem !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 18rem !important;
    }
    .block-container {
        max-width: 1700px;
        padding: 2rem 1.6rem 3rem;
    }
    .stApp h1 {
        font-size: clamp(1.7rem, 3vw, 2.35rem);
        line-height: 1.15;
    }
    .metric-card {
        border-radius: 8px;
        min-height: 118px;
        padding: 14px 16px;
        color: white;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-crit { background: linear-gradient(135deg, #e53e3e, #9b2c2c); }
    .metric-high { background: linear-gradient(135deg, #dd6b20, #9c4221); }
    .metric-med  { background: linear-gradient(135deg, #d69e2e, #744210); }
    .metric-low  { background: linear-gradient(135deg, #38a169, #22543d); }
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        opacity: 0.9;
        line-height: 1.2;
        min-height: 1.1rem;
    }
    .metric-value {
        font-size: clamp(1.6rem, 2.5vw, 2.2rem);
        font-weight: 700;
        line-height: 1.1;
        margin: 6px 0;
        white-space: nowrap;
    }
    .metric-card small {
        font-size: 0.76rem;
        opacity: 0.9;
        white-space: nowrap;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 12px;
        border-left: 4px solid #3182ce;
        padding-left: 10px;
    }
    @media (max-width: 900px) {
        section[data-testid="stSidebar"] {
            width: 16rem !important;
            min-width: 16rem !important;
        }
        section[data-testid="stSidebar"] > div {
            width: 16rem !important;
        }
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_rag_engine():
    return RAGSecurityEngine()


def display_value(value, suffix=""):
    if value is None or value == "":
        return "—"
    return f"{value}{suffix}"


def alert_severity_counts(alerts):
    severity_names = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    return {
        severity: sum(
            str(alert.get("severity") or "").upper() == severity
            for alert in alerts
        )
        for severity in severity_names
    }


def severity_label(value):
    severity = str(value or "").upper()
    markers = {
        "CRITICAL": "🔴 CRITICAL",
        "HIGH": "🟠 HIGH",
        "MEDIUM": "🟡 MEDIUM",
        "LOW": "🟢 LOW",
    }
    return markers.get(severity, "⚪ UNSPECIFIED")


if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = get_rag_engine()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.sidebar.title("SOC Control Panel")
st.sidebar.markdown("---")
api_base_url = st.sidebar.text_input(
    "Integration API URL",
    value=os.getenv("INTEGRATION_API_URL", "http://127.0.0.1:8000"),
    help="Video and network detection systems POST event data to this integration API.",
).strip().rstrip("/")

api_connected = False
api_error = None
health_data = {}
video_event = None
network_event = None
live_alerts = []
routing_weights = dict(ROUTING_WEIGHTS)
try:
    if not api_base_url:
        raise ValueError("Enter the integration API URL.")
    health_response = requests.get(f"{api_base_url}/api/health", timeout=3)
    health_response.raise_for_status()
    health_data = health_response.json()
    if not isinstance(health_data, dict) or health_data.get("status") != "online":
        raise ValueError("The integration API returned an invalid health response.")

    state_response = requests.get(f"{api_base_url}/api/state", timeout=3)
    state_response.raise_for_status()
    live_state = state_response.json()
    if not isinstance(live_state, dict):
        raise ValueError("The integration API returned an invalid state payload.")
    video_event = live_state.get("video_event")
    network_event = live_state.get("network_event")
    live_alerts = live_state.get("alerts_history")
    routing_weights = live_state.get("routing_weights", dict(ROUTING_WEIGHTS))
    if video_event is not None and not isinstance(video_event, dict):
        raise ValueError("video_event must be an object or null.")
    if network_event is not None and not isinstance(network_event, dict):
        raise ValueError("network_event must be an object or null.")
    if not isinstance(live_alerts, list) or not all(
        isinstance(alert, dict) for alert in live_alerts
    ):
        raise ValueError("alerts_history must be a list of alert objects.")
    if not isinstance(routing_weights, dict) or set(routing_weights) != set(ROUTING_WEIGHTS):
        raise ValueError(
            "routing_weights must include distance, latency, congestion, and security_risk."
        )
    api_connected = True
except (requests.RequestException, ValueError, TypeError) as exc:
    api_error = str(exc)

if api_connected:
    st.sidebar.success("Integration API connected")
    st.sidebar.caption(health_data.get("role", "Integration hub"))
else:
    st.sidebar.error("Integration API disconnected")
    st.sidebar.caption(api_error)
    st.sidebar.code("uvicorn src.integration_api:app --host 0.0.0.0 --port 8000")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Modified Dijkstra Weights")
st.sidebar.caption(
    "Cost = w1 × distance + w2 × latency + w3 × congestion + w4 × risk"
)
if api_connected:
    with st.sidebar.form("routing_weights_form"):
        w1 = st.slider(
            "w1 (Distance)", 0.0, 1.0, float(routing_weights["distance"]), 0.05
        )
        w2 = st.slider(
            "w2 (Latency)", 0.0, 1.0, float(routing_weights["latency"]), 0.05
        )
        w3 = st.slider(
            "w3 (Congestion)", 0.0, 1.0, float(routing_weights["congestion"]), 0.05
        )
        w4 = st.slider(
            "w4 (Security Risk)", 0.0, 1.0,
            float(routing_weights["security_risk"]), 0.05
        )
        weight_total = round(w1 + w2 + w3 + w4, 2)
        st.caption(f"Weight total: {weight_total:.2f} (should equal 1.00)")
        apply_weights = st.form_submit_button("Apply routing weights")
    if apply_weights:
        if weight_total != 1.0:
            st.sidebar.error("Routing weights must sum to 1.00.")
        else:
            try:
                response = requests.put(
                    f"{api_base_url}/api/network/routing-weights",
                    json={
                        "distance": w1,
                        "latency": w2,
                        "congestion": w3,
                        "security_risk": w4,
                    },
                    timeout=3,
                )
                response.raise_for_status()
                st.sidebar.success("Routing weights saved")
            except requests.RequestException as exc:
                st.sidebar.error(f"Could not save routing weights: {exc}")
else:
    st.sidebar.caption("Connect the integration API to configure routing weights.")

st.title("🛡️ Cyber-Resilient CCTV Monitoring & Response System")
st.markdown("*Video anomaly alerts, network monitoring, and security response guidance.*")

severity_counts = alert_severity_counts(live_alerts)
metric_values = (
    [severity_counts["CRITICAL"], severity_counts["HIGH"],
     severity_counts["MEDIUM"], severity_counts["LOW"]]
    if api_connected else ["—"] * 4
)
metric_subtitles = (
    ["API received"] * 4
    if api_connected else ["Waiting for API"] * 4
)
metric_classes = ["crit", "high", "med", "low"]
metric_labels = ["Critical Alerts", "High Alerts", "Medium Alerts", "Low Alerts"]
metric_cols = st.columns(4)
for col, css_class, label, value, subtitle in zip(
    metric_cols, metric_classes, metric_labels, metric_values, metric_subtitles
):
    with col:
        st.markdown(
            f"""
            <div class="metric-card metric-{css_class}">
                <div class="metric-title">{label}</div>
                <div class="metric-value">{value}</div>
                <small>{subtitle}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")
tab_overview, tab_video, tab_network, tab_rag = st.tabs([
    "📊 SOC Overview & Active Alerts",
    "📹 Video Anomaly Feed",
    "🌐 Adaptive Network Routing",
    "🤖 Security Copilot",
])

with tab_overview:
    row1_col1, row1_col2 = st.columns([1.5, 1])
    with row1_col1:
        st.markdown(
            '<div class="section-title">Security Alert Feed</div>',
            unsafe_allow_html=True,
        )
        st.caption("Recent alert history received from the integration API.")
        if live_alerts:
            filters_col, search_col = st.columns([1, 2])
            with filters_col:
                severity_filter = st.selectbox(
                    "Filter by severity",
                    ["All severities", "CRITICAL", "HIGH", "MEDIUM", "LOW", "UNSPECIFIED"],
                    key="alert_severity_filter",
                )
            with search_col:
                alert_search = st.text_input(
                    "Search alerts",
                    placeholder="Search incident, source, or status",
                    key="alert_search",
                ).strip().lower()

            filtered_alerts = []
            for alert in live_alerts[:100]:
                severity = str(alert.get("severity") or "UNSPECIFIED").upper()
                searchable = " ".join(
                    str(alert.get(key) or "")
                    for key in ("type", "source", "status", "time", "timestamp")
                ).lower()
                if severity_filter != "All severities" and severity != severity_filter:
                    continue
                if alert_search and alert_search not in searchable:
                    continue
                filtered_alerts.append(alert)

            alert_rows = [{
                "Time": alert.get("time") or alert.get("timestamp"),
                "Severity": severity_label(alert.get("severity")),
                "Incident": alert.get("type", "Security alert"),
                "Source": alert.get("source") or "—",
                "Status": alert.get("status") or "Received",
            } for alert in filtered_alerts]
            if alert_rows:
                st.dataframe(
                    pd.DataFrame(alert_rows),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No alerts match the selected filters.")
            unclassified_alerts = sum(
                not alert.get("severity")
                or str(alert["severity"]).upper() not in severity_counts
                for alert in live_alerts
            )
            if unclassified_alerts:
                st.caption(
                    f"{unclassified_alerts} received alert(s) have no recognized severity."
                )
        elif api_connected:
            st.info("No alerts have been received yet.")
        else:
            st.warning("Alerts will appear here when the integration API connects.")

    with row1_col2:
        st.markdown(
            '<div class="section-title">Alerts Over Time</div>',
            unsafe_allow_html=True,
        )
        trend_rows = []
        for alert in live_alerts:
            timestamp = pd.to_datetime(
                alert.get("time") or alert.get("timestamp"), errors="coerce"
            )
            if pd.isna(timestamp):
                continue
            if timestamp.tzinfo is not None:
                timestamp = timestamp.tz_convert(None)
            event_type = str(alert.get("type") or "Security alert")
            trend_rows.append({
                "Time": timestamp.floor("h"),
                "Alert Stream": (
                    "Video Anomaly Alerts"
                    if "video" in event_type.lower()
                    else "Network Threat Alerts"
                ),
            })
        if trend_rows:
            trend_data = (
                pd.DataFrame(trend_rows)
                .groupby(["Time", "Alert Stream"], as_index=False)
                .size()
                .rename(columns={"size": "Incidents"})
            )
            trend_chart = alt.Chart(trend_data).mark_line(
                point=True,
                interpolate="monotone",
            ).encode(
                x=alt.X("Time:T", title="Event time"),
                y=alt.Y("Incidents:Q", title="Alert volume"),
                color=alt.Color("Alert Stream:N", scale=alt.Scale(
                    domain=["Network Threat Alerts", "Video Anomaly Alerts"],
                    range=["#dd6b20", "#38a169"],
                )),
                tooltip=["Time:T", "Alert Stream:N", "Incidents:Q"],
            ).properties(height=180)
            st.altair_chart(trend_chart, use_container_width=True)
        else:
            st.caption("Trend chart will populate from timestamped alerts.")

        st.markdown(
            '<div class="section-title">Alert Severity Distribution</div>',
            unsafe_allow_html=True,
        )
        chart_data = pd.DataFrame([
            {"Severity": name.title(), "Count": severity_counts[name]}
            for name in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            if severity_counts[name] > 0
        ])
        if not chart_data.empty:
            severity_chart = alt.Chart(chart_data).mark_arc(
                innerRadius=45
            ).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Severity", type="nominal", scale=alt.Scale(
                    domain=["Critical", "High", "Medium", "Low"],
                    range=["#e53e3e", "#dd6b20", "#d69e2e", "#38a169"],
                )),
                tooltip=["Severity", "Count"],
            ).properties(height=180)
            st.altair_chart(severity_chart, use_container_width=True)
        else:
            st.caption("No severity distribution until alerts are received.")

    st.markdown(
        '<div class="section-title">Integrated Telemetry Stream</div>',
        unsafe_allow_html=True,
    )
    telemetry_cols = st.columns(4)
    telemetry_cols[0].metric(
        "Video Anomaly Score",
        display_value((video_event or {}).get("anomaly_score"))
        if api_connected else "—",
    )
    telemetry_cols[1].metric(
        "Network Traffic Rate",
        display_value((network_event or {}).get("traffic_rate"), " pps")
        if api_connected else "—",
    )
    telemetry_cols[2].metric(
        "Network Latency",
        display_value((network_event or {}).get("latency"), " ms")
        if api_connected else "—",
    )
    telemetry_cols[3].metric(
        "Active Routing State",
        display_value((network_event or {}).get("routing_status"))
        if api_connected else "—",
    )
    feed_status_cols = st.columns(3)
    feed_status_cols[0].metric(
        "Video integration",
        "Event received" if video_event else ("Waiting" if api_connected else "Offline"),
    )
    feed_status_cols[1].metric(
        "Network integration",
        "Event received" if network_event else ("Waiting" if api_connected else "Offline"),
    )
    feed_status_cols[2].metric(
        "Alert history",
        f"{len(live_alerts)} / 100" if api_connected else "Unavailable",
    )
    if video_event or network_event:
        valid_update_times = []
        for event in (video_event, network_event):
            if not event or not event.get("timestamp"):
                continue
            timestamp = pd.to_datetime(event["timestamp"], errors="coerce")
            if pd.isna(timestamp):
                continue
            if timestamp.tzinfo is not None:
                timestamp = timestamp.tz_convert(None)
            valid_update_times.append(timestamp)
        if valid_update_times:
            latest_update = max(valid_update_times)
            st.caption(
                f"Latest source timestamp: {latest_update.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    st.markdown(
        '<div class="section-title">Security Operations Triage</div>',
        unsafe_allow_html=True,
    )
    triage_col1, triage_col2, triage_col3 = st.columns([1, 1, 1.8])
    with triage_col1:
        st.markdown("##### 📌 Top Threat Offenses")
        offense_counts = {}
        for alert in live_alerts:
            alert_type = str(alert.get("type") or "Security alert")
            offense_counts[alert_type] = offense_counts.get(alert_type, 0) + 1
        if offense_counts:
            for alert_type, count in sorted(
                offense_counts.items(), key=lambda item: item[1], reverse=True
            )[:5]:
                st.write(f"{count} × {alert_type}")
        else:
            st.caption("Threat categories will appear as alerts arrive.")

    with triage_col2:
        st.markdown("##### 🚨 Recent Incidents")
        if live_alerts:
            for alert in live_alerts[:4]:
                st.write(
                    f"{alert.get('severity', 'UNSPECIFIED')} — "
                    f"{alert.get('type', 'Security alert')}: "
                    f"{alert.get('status', 'Received')}"
                )
        else:
            st.caption("No recent incidents received.")

    with triage_col3:
        st.markdown("##### 📜 Audit & Event Log Timeline")
        audit_rows = [{
            "Event Time": alert.get("time") or alert.get("timestamp"),
            "Event Type": alert.get("type"),
            "Entity": alert.get("source"),
            "Source IP": alert.get("source_ip") or "Not provided",
            "Outcome": alert.get("status"),
        } for alert in live_alerts[:6]]
        if audit_rows:
            st.dataframe(
                pd.DataFrame(audit_rows),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("Audit events will appear when alerts are received.")

with tab_video:
    st.markdown(
        '<div class="section-title">CCTV Video Anomaly Detection</div>',
        unsafe_allow_html=True,
    )
    input_col1, input_col2 = st.columns(2)
    with input_col1:
        uploaded_video = st.file_uploader(
            "Upload a video for preview",
            type=["mp4", "mov", "webm"],
            key="video_preview_upload",
        )
        if uploaded_video is not None:
            st.video(uploaded_video)
    with input_col2:
        st.markdown("##### Live webcam")
        webrtc_streamer(
            key="live_webcam",
            media_stream_constraints={"video": True, "audio": False},
        )
    st.caption(
        "Uploaded video and the local webcam are preview-only and are not sent "
        "to the video analysis system. Its analyzed alert metadata is sent through the integration API."
    )
    st.markdown("---")
    video_col, score_col = st.columns([3, 2])
    with video_col:
        st.subheader("Live Video Alert Metadata")
        if video_event:
            status = display_value(video_event.get("status"))
            video_severity = str(video_event.get("severity") or "").upper()
            status_upper = str(video_event.get("status") or "").upper()
            status_message = (
                f"Camera: {display_value(video_event.get('camera_id'))} | "
                f"Status: {status} | "
                f"Class: {display_value(video_event.get('event_type') or video_event.get('class_name'))}"
            )
            if status_upper in {"ANOMALY", "ANOMALY_DETECTED", "ALERT"} or video_severity in {
                "CRITICAL", "HIGH"
            }:
                st.error(status_message)
            elif video_severity == "MEDIUM":
                st.warning(status_message)
            elif status_upper in {"NORMAL", "OK", "CLEAR", "NO_ANOMALY"}:
                st.success(status_message)
            else:
                st.info(status_message)
            st.caption(
                f"Severity: {severity_label(video_event.get('severity'))} · "
                f"Confidence: {display_value(video_event.get('confidence'))} · "
                f"Updated: {display_value(video_event.get('timestamp'))}"
            )
        elif api_connected:
            st.info("Waiting for video alert metadata.")
        else:
            st.warning("Video alert metadata is unavailable while the API is disconnected.")

    with score_col:
        st.subheader("Reconstruction Error & Score History")
        if video_event and video_event.get("anomaly_score") is not None:
            st.metric("Latest reported anomaly score", video_event["anomaly_score"])
            st.caption(
                "The integration currently provides the latest score only. "
                "A score-history chart requires a time-series API field."
            )
        else:
            st.caption("Waiting for an anomaly score.")

with tab_network:
    st.markdown(
        '<div class="section-title">DDoS Detection & Adaptive Network Routing</div>',
        unsafe_allow_html=True,
    )
    network_col, routing_col = st.columns([3, 2])
    with network_col:
        st.subheader("CCTV Network Topology & Forwarding Path")
        if network_event:
            attack_status = str(network_event.get("attack_status") or "Unspecified")
            network_severity = str(network_event.get("severity") or "").upper()
            if (
                any(word in attack_status.upper() for word in ("ATTACK", "DDOS", "FLOOD"))
                or network_severity in {"CRITICAL", "HIGH"}
            ):
                st.error(f"🚨 **Reported network status:** {attack_status}")
            elif network_severity == "MEDIUM":
                st.warning(f"**Reported network status:** {attack_status}")
            elif attack_status.upper() in {"NORMAL", "OK", "CLEAR"}:
                st.success(f"**Reported network status:** {attack_status}")
            else:
                st.info(f"**Reported network status:** {attack_status}")
            st.caption(f"Severity: {severity_label(network_event.get('severity'))}")
            active_path = network_event.get("active_path")
            st.markdown(
                f"**Reported active path:** "
                f"`{display_value(active_path)}`"
            )
            route_details = [{
                "Field": "Traffic rate",
                "Value": display_value(network_event.get("traffic_rate"), " pps"),
            }, {
                "Field": "Latency",
                "Value": display_value(network_event.get("latency"), " ms"),
            }, {
                "Field": "Packet loss",
                "Value": display_value(network_event.get("packet_loss_pct"), "%"),
            }, {
                "Field": "Routing status",
                "Value": display_value(network_event.get("routing_status")),
            }, {
                "Field": "Updated",
                "Value": display_value(network_event.get("timestamp")),
            }]
            st.dataframe(
                pd.DataFrame(route_details),
                hide_index=True,
                use_container_width=True,
            )
        elif api_connected:
            st.info("Waiting for network and routing telemetry.")
        else:
            st.warning("Network telemetry is unavailable while the API is disconnected.")

    with routing_col:
        st.subheader("Modified Dijkstra Cost Formula")
        st.latex(
            r"\text{Cost}(e)=w_1\cdot\text{Dist}+w_2\cdot\text{Lat}"
            r"+w_3\cdot\text{Cong}+w_4\cdot\text{Risk}"
        )
        for weight_name, value in ROUTING_WEIGHTS.items():
            st.write(
                f"- {weight_name.replace('_', ' ').title()}: "
                f"`{float(routing_weights[weight_name]):.2f}`"
            )
        st.info(
            "Weights are saved in the integration API for the routing system to consume from "
            "`/api/state`. The dashboard displays the reported path and does not "
            "calculate routes or send SDN commands."
        )

with tab_rag:
    st.markdown(
        '<div class="section-title">RAG-Based Security Assistant & Incident Response</div>',
        unsafe_allow_html=True,
    )
    rag_engine = st.session_state.rag_engine
    st.caption(
        f"Retrieval index: {rag_engine.retrieval_backend} "
        f"({len(rag_engine.chunks)} knowledge chunks)"
    )
    rag_col, chat_col = st.columns([1, 1])
    latest_alert = live_alerts[0] if live_alerts else None
    incident_context = None
    recommendation = None
    if latest_alert:
        alert_type = latest_alert.get("type") or "Security alert"
        incident_context = {
            "alert_type": alert_type,
            "severity": latest_alert.get("severity") or "Unspecified",
            "source": latest_alert.get("source") or "Unspecified",
            "details": json.dumps(latest_alert, ensure_ascii=True),
        }
        recommendation = rag_engine.generate_mitigation_response(incident_context)

    with rag_col:
        st.subheader("Automated Incident Triage & SOP Retrieval")
        if recommendation:
            st.markdown(f"**Identified Incident:** `{recommendation['incident_type']}`")
            st.markdown(f"**Threat Classification:** `{recommendation['threat_category']}`")
            st.markdown(f"**Target Origin:** `{recommendation['source_node']}`")
            st.markdown("#### 📋 Immediate Action Checklist (from Retrieved SOPs)")
            for step in recommendation["immediate_actions"]:
                st.markdown(f"- [ ] {step}")
            st.markdown("#### 🔄 SDN Routing Guidance")
            st.info(recommendation["sdn_routing_guidance"])
            st.markdown("#### 📚 Grounded Knowledge Base Sources")
            for source in recommendation["retrieved_sources"]:
                st.markdown(f"- 📄 `{source}`")
        elif api_connected:
            st.info("No incident has been received. Recommendations will appear with real alert data.")
        else:
            st.warning("Connect the integration API to receive incident-based recommendations.")

    with chat_col:
        st.subheader("💬 Security Operator Copilot Chat")
        chat_container = st.container(height=380)
        for message in st.session_state.chat_history:
            with chat_container:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        user_prompt = st.chat_input("Ask about mitigation, SOPs, or routing policies...")
        if user_prompt:
            st.session_state.chat_history.append(
                {"role": "user", "content": user_prompt}
            )
            if incident_context:
                response = rag_engine.generate_mitigation_response(
                    incident_context,
                    user_query=user_prompt,
                )
                answer = (
                    f"**Grounded Assessment:** Based on "
                    f"`{', '.join(response['retrieved_sources'])}`:\n\n"
                    "**Key Recommendations:**\n"
                    + "\n".join(f"- {action}" for action in response["immediate_actions"])
                    + f"\n\n**SDN Forwarding Action:** {response['sdn_routing_guidance']}"
                )
            else:
                retrieved = rag_engine.retrieve_context(user_prompt, top_k=3)
                answer = "\n\n".join(
                    f"**{item['chunk']['source_file']} · {item['chunk']['section']}**\n\n"
                    f"{item['chunk']['content']}"
                    for item in retrieved
                ) or "No matching guidance was found in the indexed knowledge base."
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )
            st.rerun()

st.markdown("---")
st.caption(
    "Video alerts: POST /api/video/alert · Network alerts: POST /api/network/alert · "
    "Dashboard state: GET /api/state"
)
st_autorefresh(interval=5000, key="soc_dashboard_refresh")
