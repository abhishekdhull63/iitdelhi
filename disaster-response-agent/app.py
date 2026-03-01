"""
NEXUS Command Center v3.0 — Claw & Shield 2026
Glassmorphism + st.components.v1.html() for GUARANTEED HTML rendering
"""
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# Import the main agent orchestrator (BACKEND UNCHANGED)
from agent_core import TriageCommander
from enforcement_middleware import IntentModel, ActionType, check_high_volume, _SQLITE_DB_PATH

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NEXUS Command Center",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS  (injected once via st.markdown)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Deep navy gradient background */
.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2a 50%, #0a1428 100%);
    color: #e5e7eb;
}

/* Glassmorphism containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
}

/* Headers */
h1, h2, h3 {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: #f3f4f6 !important;
}

/* Transparent top header bar */
[data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(10, 10, 26, 0.8) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Neon green primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(45deg, #10b981, #059669) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 16px 32px !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.4) !important;
    transition: all 0.3s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 40px rgba(16, 185, 129, 0.8) !important;
    transform: translateY(-2px) !important;
}

/* Text area */
.stTextArea textarea {
    background-color: rgba(0, 0, 0, 0.4) !important;
    color: #e5e7eb !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
}
.stTextArea textarea:focus {
    border-color: #06b6d4 !important;
    box-shadow: 0 0 0 1px #06b6d4 !important;
}

/* ═══════════ DRONE / CCTV FEED OVERLAY ═══════════ */
div[data-testid="stImage"] {
    position: relative;
    border: 1px solid rgba(0, 255, 204, 0.25) !important;
    border-radius: 8px !important;
    overflow: hidden;
    box-shadow: 0 0 20px rgba(0, 255, 204, 0.08);
}
/* Scanlines */
div[data-testid="stImage"]::before {
    content: "";
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px
    );
    pointer-events: none;
    z-index: 2;
}
/* Blinking REC dot */
div[data-testid="stImage"]::after {
    content: "● REC";
    position: absolute;
    top: 10px; right: 12px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #ff3b3b;
    letter-spacing: 1.5px;
    text-shadow: 0 0 6px rgba(255,59,59,0.6);
    z-index: 3;
    animation: recBlink 1.2s ease-in-out infinite;
}
@keyframes recBlink {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.15; }
}
/* Desaturate image for surveillance look */
div[data-testid="stImage"] img {
    filter: saturate(0.65) brightness(0.85) contrast(1.15) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
# Ensure script clears pending events and starts completely fresh on cold boot
if "app_initialized" not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.commander = TriageCommander()
    st.session_state.shield_log = []
    st.session_state.latest_result = None
    st.session_state.mission_counter = 0
    st.session_state.pending_high_volume_mission = None
    st.session_state.pending_mission_image = None
    st.session_state.pending_mission_mime = None

# Ensure keys exist for warm reloads
if "commander" not in st.session_state:
    st.session_state.commander = TriageCommander()
if "shield_log" not in st.session_state:
    st.session_state.shield_log = []
if "latest_result" not in st.session_state:
    st.session_state.latest_result = None
if "mission_counter" not in st.session_state:
    st.session_state.mission_counter = 0
if "pending_high_volume_mission" not in st.session_state:
    st.session_state.pending_high_volume_mission = None
if "pending_mission_image" not in st.session_state:
    st.session_state.pending_mission_image = None
if "pending_mission_mime" not in st.session_state:
    st.session_state.pending_mission_mime = None


def add_log_entry(msg_type: str, message: str) -> None:
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    st.session_state.shield_log.append({
        "time": ist_now.strftime("%H:%M:%S"),
        "type": msg_type,
        "message": message,
    })


def process_mission(briefing: str, image_bytes: Optional[bytes] = None, image_mime: Optional[str] = None) -> None:
    """Run the TriageCommander and update the UI state."""
    add_log_entry("INFO", f"▶ INITIATING MISSION [{len(briefing)} chars]")

    try:
        result = st.session_state.commander.run_mission(
            mission_briefing=briefing,
            image_bytes=image_bytes,
            image_mime=image_mime
        )
        st.session_state.latest_result = result
        status = result.get("status", "UNKNOWN")

        if status == "SUCCESS":
            add_log_entry("SUCCESS", f"✅ CLEARED: {result.get('result', 'Dispatch written.')}")
        elif status == "SUCCESS_AFTER_REFLECTION":
            n = result.get("reflection_attempts", 1)
            add_log_entry("HEALED", f"🔄 HEALED: Auto-corrected after {n} pass(es).")
            add_log_entry("SUCCESS", f"✅ CLEARED: {result.get('result', 'Dispatch written.')}")
        elif status == "ROUTED_TO_MEDICAL":
            add_log_entry("ROUTED", "⚠️ MEDICAL DETECTED: Intercepted by Shield.")
            add_log_entry("ROUTED", "🏥 ROUTED → MedicalTriageAgent.")
            add_log_entry("SUCCESS", f"✅ WRITTEN: {result.get('result', 'Medical log written.')}")
        elif status == "BLOCKED_BY_SHIELD":
            n = result.get("reflection_attempts", 0)
            if n > 0:
                add_log_entry("BLOCKED", f"🛑 FAILED: Self-healing exhausted after {n} retries.")
            add_log_entry("BLOCKED", f"🛑 BLOCKED: {result.get('error', 'Policy violation.')} ({result.get('rule_id')})")
        elif status == "BLOCKED_BY_SUB_AGENT":
            add_log_entry("BLOCKED", f"🚫 SUB-AGENT REJECT: {result.get('error', 'Authority exceeded.')} ({result.get('rule_id')})")
        else:
            add_log_entry("ERROR", f"❌ ERROR: {result.get('error', 'Unknown error.')}")

    except Exception as e:
        add_log_entry("ERROR", f"💥 CRITICAL: {e}")
        st.session_state.latest_result = {"status": "CRITICAL_ERROR", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# LOG RENDERER  — uses st.components.v1.html() (renders in an iframe,
#                  guaranteeing HTML/CSS is never escaped)
# ─────────────────────────────────────────────────────────────────────────────
def render_shield_log(height: int = 400) -> None:
    """Build a self-contained HTML document and render it via components.html."""

    # Colour map
    COLOR_MAP = {
        "SUCCESS": "#10b981",
        "HEALED":  "#06b6d4",
        "ROUTED":  "#f59e0b",
        "BLOCKED": "#ef4444",
        "ERROR":   "#ef4444",
        "INFO":    "#9ca3af",
    }

    rows = ""
    if not st.session_state.shield_log:
        rows = '<div style="color:#484f58;padding:8px;">System standing by…</div>'
    else:
        for entry in reversed(st.session_state.shield_log):
            color = COLOR_MAP.get(entry.get("type", "INFO"), "#9ca3af")
            rows += (
                f'<div style="margin-bottom:6px;padding-bottom:4px;'
                f'border-bottom:1px dashed rgba(255,255,255,0.05);">'
                f'<span style="color:#6b7280;font-size:0.85em;margin-right:8px;">'
                f'[{entry["time"]}]</span>'
                f'<span style="color:{color};font-weight:bold;">'
                f'{entry["message"]}</span></div>'
            )

    full_html = f"""
    <html>
    <body style="
        margin:0; padding:12px;
        font-family:'Courier New',monospace;
        font-size:14px; line-height:1.6;
        background:rgba(0,0,0,0.6);
        color:#e5e7eb;
        border-radius:8px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
    ">
    {rows}
    </body>
    </html>
    """
    components.html(full_html, height=height, scrolling=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 🚨🔥 **NEXUS** Command Center 🔥🚨")
st.markdown("**_AI-Powered Disaster Triage & Secure Delegation_**")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ **System Status**")
    c1, c2 = st.columns(2)
    c1.metric("System Health", "Optimal", "100%")
    c2.metric("Shield Active", "🟢 LIVE", "0 vulns")
    st.markdown("---")
    st.markdown("*Claw & Shield 2026*")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT (Glass-Box Dashboard)
# ─────────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

# ── LEFT: Mission Input ─────────────────────────────────────────────────────
with col1:
    with st.container(border=True):
        st.markdown("### 📤 **Mission Input**")

        uploaded_file = st.file_uploader(
            "Upload Field Image (Optional)",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
        )

        image_context = ""
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption="UAV-LINK-ACTIVE // NEXUS-SAT-7", use_container_width=True)
                image_context = f"\n[ATTACHMENT: '{uploaded_file.name}']"
                add_log_entry("INFO", f"📎 Attachment loaded: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Failed to load image: {e}")

        mission_briefing = st.text_area(
            "Emergency Report",
            value="",
            placeholder=(
                "Flooding at coordinates 23.4,72.6. Multiple affected. "
                "Need 500 water purifiers and 4 rescue boats immediately."
            ),
            height=180,
            label_visibility="collapsed",
            key=f"mission_input_{st.session_state.mission_counter}",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚀 **DEPLOY MISSION**", type="primary", use_container_width=True):
            if not mission_briefing.strip():
                st.warning("Provide a mission briefing first.")
            else:
                full_briefing = mission_briefing + image_context
                
                image_bytes = None
                image_mime = None
                if uploaded_file is not None:
                    image_bytes = uploaded_file.getvalue()
                    image_mime = uploaded_file.type

                # HUMAN-IN-THE-LOOP (HITL) CHECK
                dummy_intent = IntentModel(action_type=ActionType.UNKNOWN, raw_text=full_briefing)
                if check_high_volume(dummy_intent):
                    st.session_state.pending_high_volume_mission = full_briefing
                    st.session_state.pending_mission_image = image_bytes
                    st.session_state.pending_mission_mime = image_mime
                    st.rerun()
                else:
                    with st.spinner("🧠 Triage + Shield Analysis..."):
                        process_mission(full_briefing, image_bytes, image_mime)
                    # Auto-clear the input field for the next demo run
                    st.session_state.mission_counter += 1
                    st.rerun()

        # Render HITL Confirmation UI if pending
        if st.session_state.pending_high_volume_mission:
            st.warning("⚠️ **HITL ALERT**: High volume dispatch (>1,000 units) detected. Human confirmation required.")
            confirm = st.checkbox("Confirm High-Volume Dispatch", key=f"hitl_{st.session_state.mission_counter}")
            
            c1, c2 = st.columns(2)
            with c1:
                if confirm:
                    with st.spinner("🧠 Triage + Shield Analysis..."):
                        process_mission(
                            st.session_state.pending_high_volume_mission,
                            st.session_state.pending_mission_image,
                            st.session_state.pending_mission_mime
                        )
                    st.session_state.pending_high_volume_mission = None
                    st.session_state.pending_mission_image = None
                    st.session_state.pending_mission_mime = None
                    st.session_state.mission_counter += 1
                    st.rerun()
            with c2:
                if st.button("Cancel", key="cancel_hitl"):
                    st.session_state.pending_high_volume_mission = None
                    st.session_state.pending_mission_image = None
                    st.session_state.pending_mission_mime = None
                    st.rerun()

# ── RIGHT: Core Systems Log ────────────────────────────────────────────────
with col2:
    with st.container(border=True):
        hdr_a, hdr_b = st.columns([0.8, 0.2])
        with hdr_a:
            st.markdown("### 🖥️ **Core Systems Log**")
        with hdr_b:
            if st.button("Clear Log", type="secondary"):
                st.session_state.shield_log = []
                st.session_state.latest_result = None
                st.rerun()

        # ★ THE FIX: render via components.html — never escapes HTML
        render_shield_log(height=200)
        
        st.markdown("---")
        st.markdown("### 🛡️ **Security Guard (Audit Logs)**")
        
        try:
            conn = sqlite3.connect(str(_SQLITE_DB_PATH))
            df = pd.read_sql_query("SELECT timestamp, severity, action, status FROM audit_logs ORDER BY id DESC LIMIT 5", conn)
            conn.close()
            
            if not df.empty:
                # Convert UTC timestamps to IST for display
                df['timestamp'] = (pd.to_datetime(df['timestamp']) + timedelta(hours=5, minutes=30)).dt.strftime('%H:%M:%S IST')
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs available yet.")
        except Exception as e:
            st.error(f"Audit DB Offline: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# RESULTS (Bottom)
# ─────────────────────────────────────────────────────────────────────────────
res = st.session_state.latest_result
if res:
    st.markdown("---")
    status = res.get("status", "")

    if status in ("SUCCESS", "SUCCESS_AFTER_REFLECTION"):
        st.success("✅ **MISSION DEPLOYED**: Logistics Sub-Agent Dispatch Complete")
        with st.expander("View Payload Data", expanded=True):
            st.json(res.get("triage", {}))
    elif status == "ROUTED_TO_MEDICAL":
        st.warning("🏥 **MEDICAL MISSION**: Handled by MedicalTriageAgent")
        with st.expander("View Symptom Analysis", expanded=True):
            st.json(res.get("analysis", {}))
    elif status.startswith("BLOCKED"):
        st.error(f"🛑 **MISSION ABORTED**: {res.get('rule_id', 'Shield')}")
        with st.expander("View Violation Details", expanded=True):
            st.info(res.get("error", "Unknown violation"))

    # ── Token Cost Tracker ──
    triage_data = res.get("triage", res.get("analysis", {}))
    if isinstance(triage_data, dict) and triage_data.get("total_mission_cost") is not None:
        cost = triage_data["total_mission_cost"]
        tokens = triage_data.get("total_tokens", 0)
        st.caption(f"💸 **Mission Cost:** ${cost:.6f}  ·  **Tokens:** {tokens}")

# ─────────────────────────────────────────────────────────────────────────────
# GPS INJECTION + PDF EXPORT (Browser-side via HTML component)
# ─────────────────────────────────────────────────────────────────────────────
gps_pdf_html = """
<div style="display:flex;gap:10px;margin:12px 0;flex-wrap:wrap;">
    <button onclick="getLocation()" style="
        padding:8px 18px; background:rgba(0,255,204,0.08); color:#00ffcc;
        border:1px solid rgba(0,255,204,0.25); border-radius:100px;
        font-family:'Courier New',monospace; font-size:12px; font-weight:700;
        cursor:pointer; letter-spacing:0.5px;
    ">📍 Inject Live GPS</button>
    <button onclick="window.top.print()" style="
        padding:8px 18px; background:rgba(0,204,106,0.08); color:#00ff88;
        border:1px solid rgba(0,204,106,0.25); border-radius:100px;
        font-family:'Courier New',monospace; font-size:12px; font-weight:700;
        cursor:pointer; letter-spacing:0.5px;
    ">🖨️ Export Secure Brief</button>
    <span id="gps-status" style="
        font-family:'Courier New',monospace; font-size:11px; color:#6b7280;
        display:flex; align-items:center;
    "></span>
</div>
<script>
function getLocation() {
    var s = document.getElementById('gps-status');
    s.textContent = '📍 Locating...';
    if (!navigator.geolocation) {
        appendToTextarea('[Live Telemetry: OFFLINE - Manual Entry Required]');
        s.textContent = '⚠️ GPS Offline';
        return;
    }
    navigator.geolocation.getCurrentPosition(function(pos) {
        var lat = pos.coords.latitude.toFixed(4);
        var lon = pos.coords.longitude.toFixed(4);
        appendToTextarea('[Live Telemetry: ' + lat + '° N, ' + lon + '° E]');
        s.textContent = '✅ GPS Injected';
        setTimeout(function(){ s.textContent = ''; }, 2500);
    }, function() {
        appendToTextarea('[Live Telemetry: OFFLINE - Manual Entry Required]');
        s.textContent = '⚠️ GPS Offline';
        setTimeout(function(){ s.textContent = ''; }, 2500);
    }, { enableHighAccuracy: true, timeout: 10000 });
}
function appendToTextarea(text) {
    var ta = window.parent.document.querySelector('.stTextArea textarea');
    if (ta) {
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value').set;
        nativeInputValueSetter.call(ta, ta.value + '\\n' + text);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
}
</script>
"""
components.html(gps_pdf_html, height=55)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#6b7280;font-size:0.9em;'>"
    "*Powered by OpenClaw + Gemini AI | Shield Middleware Active | ArmorIQ Enforced*"
    "</div>",
    unsafe_allow_html=True,
)
