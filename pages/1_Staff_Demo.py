"""Local care-team view for the same fictional appointment and mock queue."""

import streamlit as st

from readiness import find_unresolved_items
from staff_tasks import list_mock_staff_tasks, mark_mock_task_seen
from tools import get_appointment
from ui_styles import apply_visitready_style, render_checklist, render_metric, render_sidebar


st.set_page_config(
    page_title="VisitReady · Care Team Demo",
    page_icon="✓",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_visitready_style()
render_sidebar()

appointment = get_appointment("DEMO-001")
st.markdown('<p class="vr-eyebrow">CARE TEAM VIEW · APPOINTMENT READINESS</p>', unsafe_allow_html=True)
st.title("Care team workspace")
st.markdown(
    '<p class="vr-lead">One shared view of the fictional visit and the local follow-up queue.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="vr-hero"><strong>Small steps make visits easier.</strong>'
    '<p>See the open preparation items, then inspect any mock task that needs a human decision.</p></div>',
    unsafe_allow_html=True,
)
st.markdown('<span class="vr-demo">● Local simulation · Not a hospital staff system</span>', unsafe_allow_html=True)

try:
    tasks = list_mock_staff_tasks()
except (OSError, ValueError):
    tasks = []
    st.error("The local mock queue could not be read.")

unresolved = find_unresolved_items(appointment)
waiting = sum(task.status == "awaiting_staff_review" for task in tasks)
for column, value, label in zip(
    st.columns(3),
    (1, len(unresolved), waiting),
    ("fictional appointment", "unresolved checklist items", "mock tasks awaiting acknowledgement"),
):
    with column:
        render_metric(value, label)

st.write("")
visit_column, queue_column = st.columns([1.2, 1], gap="large")
with visit_column:
    st.subheader("Visit preparation")
    render_checklist(appointment, title="Current checklist")
    st.markdown("**Still to clarify**")
    for item_name in unresolved:
        item = getattr(appointment, item_name)
        st.write(f"{item_name.title()}: {item.status.replace('_', ' ')}")
    st.caption(
        "These are fictional record states. An item marked confirmed reflects a report "
        "in the demo, not independent hospital verification."
    )

with queue_column:
    st.subheader("Team follow-up · mock")
    st.caption(
        "Fictional logistics reports can include an AI staff draft and supporting quotes. "
        "Verify the original report before acting. Explicitly submitted medical questions "
        "are shown verbatim, without an AI summary. "
        "Unrelated requests are denied and do not create new tasks."
    )
    if not tasks:
        st.info("No mock tasks yet. Submit a review case from the caregiver view.")
    for task in reversed(tasks):
        with st.container(border=True):
            st.markdown(f"**{task.task_id}** · {task.category.replace('_', ' ').title()}")
            st.caption(f"Appointment {task.appointment_id} · {task.status.replace('_', ' ')}")
            if task.assigned_team:
                st.caption(f"Assigned team: {task.assigned_team}")
            if task.staff_summary:
                st.markdown("**AI staff summary · draft**" if task.summary_source == "ai_draft" else "**Basic staff summary · fallback**")
                st.text(task.staff_summary.summary)
                for detail in task.staff_summary.reported_details:
                    st.markdown(f"**{detail.item.title()} · parent or guardian report**")
                    st.text(detail.statement)
                    st.caption("Supporting quote")
                    st.text(detail.source_quote)
                if task.staff_summary.review_items:
                    st.markdown("**Items for staff to review**")
                    st.write(", ".join(item.title() for item in task.staff_summary.review_items))
                with st.expander("Original fictional report"):
                    st.text(task.original_message or "No source report available.")
                st.caption("Internal draft only. Quote checks do not verify every interpretation. No assistance has been arranged or message sent to hospital staff.")
            elif task.category == "clinical_question" and task.original_message:
                st.markdown("**Original fictional question · caregiver submitted**")
                st.text(task.original_message)
                st.caption("Exact question; no AI medical interpretation. This is a local demo review request, not a completed clinical review.")
            else:
                st.caption("Metadata-only task. No AI staff summary or original question is stored here.")
            if task.status == "awaiting_staff_review":
                if st.button("Mark seen in demo", key=f"seen_{task.task_id}"):
                    try:
                        mark_mock_task_seen(task.task_id)
                    except (OSError, ValueError):
                        st.error("Could not update this local mock task.")
                    else:
                        st.rerun()

st.divider()
st.caption("No real hospital staff are contacted. Marking a task seen records only a demo acknowledgement.")
