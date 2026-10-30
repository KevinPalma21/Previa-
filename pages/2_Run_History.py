"""Read-only timeline for coordinated VisitReady demo runs."""

import streamlit as st

from run_history import list_run_history
from ui_styles import apply_visitready_style, render_sidebar


st.set_page_config(page_title="VisitReady · Activity Trail", page_icon="✓", layout="wide", initial_sidebar_state="expanded")
apply_visitready_style()
render_sidebar()
st.markdown('<p class="vr-eyebrow">LOCAL DEMO · ACTIVITY TRAIL</p>', unsafe_allow_html=True)
st.title("What happened, step by step")
st.caption(
    "Local demo trace of which steps ran or were skipped. It does not save caregiver "
    "messages, model-written text, or API keys. This is not a hospital audit log."
)

try:
    records = list_run_history()
except (OSError, ValueError):
    st.error("The local run history could not be read.")
else:
    if not records:
        st.info("No coordinated runs yet. Ask VisitReady or run the sample on the main page.")
    for record in reversed(records[-20:]):
        timestamp = record.created_at.astimezone().strftime("%b %d, %Y · %I:%M %p")
        with st.expander(f"{record.run_id} · {timestamp} · {record.policy_result.replace('_', ' ')}"):
            st.write("Appointment:", record.appointment_id)
            st.write("Mode:", "Live AI run" if record.mode == "live" else "Simulated sample")
            for event in record.events:
                st.write(f"{event.step.replace('_', ' ').title()}: **{event.outcome.replace('_', ' ').title()}**")
