"""A caregiver-only presentation of the fictional VisitReady appointment."""

from html import escape
from hashlib import sha256

import streamlit as st
from openai import APIConnectionError, APIError, AuthenticationError, RateLimitError

from caregiver_response import compose_caregiver_response
from coordinator import VisitPlan, coordinate_visit, submit_clinical_review
from patient_profile import load_patient_profile
from parking_tools import lookup_appointment_parking
from parking_view import render_parking_help
from readiness import find_unresolved_items
from resource_tools import get_public_guidance
from run_history import record_run
from storage import save_approved_update
from tools import get_appointment
from ui_styles import (
    apply_visitready_style,
)


def _apply_caregiver_style() -> None:
    """Keep the single-page family view focused on the checklist and assistant."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none !important;}
        [data-testid="stToolbar"] {visibility:hidden;}
        [data-testid="stAppViewContainer"] {background:#FCFEFF;}
        .block-container {max-width:1120px; padding-top:1.15rem;}
        .vr-family-header {display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.15rem 0 1.1rem; border-bottom:1px solid #D7E7F0; margin-bottom:1.4rem;}
        .vr-family-brand {font-size:1.5rem; line-height:1.1; font-weight:850; color:#00619E; letter-spacing:-.04em;}
        .vr-family-intro {display:flex; justify-content:space-between; align-items:end; gap:1rem; margin-bottom:1.25rem;}
        .vr-family-intro h1 {font-size:2.2rem; line-height:1.1; margin:.2rem 0 .45rem;}
        .vr-family-intro h1, .vr-check-head h2, .vr-chat-head h2 {color:#36576E !important;}
        .vr-family-intro p {font-size:.93rem; color:#647487; margin:0;}
        .vr-patient-card {display:flex; gap:.7rem; align-items:start; min-width:260px; max-width:300px; border:1px solid #D7E7F0; background:#F4F9FC; color:#36576E; padding:.85rem; border-radius:14px;}
        .vr-patient-avatar {width:36px; height:36px; flex:0 0 36px; display:grid; place-items:center; border-radius:11px; background:#DDEEF8; color:#00619E; font-size:.76rem; font-weight:850;}
        .vr-patient-copy span {display:block; font-size:.65rem; color:#647487; letter-spacing:.1em; font-weight:800;}
        .vr-patient-copy strong {display:block; color:#36576E; font-size:.94rem; margin:.12rem 0;}
        .vr-patient-copy small {display:block; color:#647487; font-size:.73rem;}
        .vr-patient-reason {color:#36576E; font-size:.77rem; line-height:1.35; margin-top:.5rem; padding-top:.5rem; border-top:1px solid #D7E7F0;}
        .vr-family-card {background:#fff; border:1px solid #D7E7F0; border-radius:18px; box-shadow:0 8px 24px rgba(0,97,158,.045); padding:1.3rem;}
        .vr-check-head {display:flex; justify-content:space-between; align-items:baseline; gap:.6rem;}
        .vr-check-head h2, .vr-chat-head h2 {font-size:1.18rem; margin:0; letter-spacing:-.025em;}
        .vr-check-head > span {font-size:.76rem; color:#647487;}
        .vr-check-track {height:7px; border-radius:999px; background:#E7F1F7; overflow:hidden; margin:1rem 0 1.15rem;}
        .vr-check-fill {height:100%; background:#0D74B4; border-radius:999px;}
        .vr-check-row {display:flex; align-items:center; gap:.85rem; padding:.88rem 0; border-top:1px solid #E6EFF4;}
        .vr-check-icon {width:32px; height:32px; flex:0 0 32px; display:grid; place-items:center; border-radius:10px; background:#E9F3F8; color:#00619E; font-weight:800;}
        .vr-check-row.confirmed .vr-check-icon {background:#DDF3E8; color:#137158;}
        .vr-check-row.unconfirmed .vr-check-icon {background:#FFF0D9; color:#9C681D;}
        .vr-check-copy {min-width:0; flex:1;}
        .vr-check-copy strong {display:block; color:#36576E; font-size:.88rem;}
        .vr-check-copy small {display:block; color:#647487; font-size:.74rem; line-height:1.4;}
        .vr-check-badge {white-space:nowrap; font-size:.7rem; font-weight:780; color:#00619E; background:#EAF4FB; padding:.3rem .55rem; border-radius:999px;}
        .vr-check-row.confirmed .vr-check-badge {color:#146E52; background:#E2F5EA;}
        .vr-check-row.unconfirmed .vr-check-badge {color:#95611A; background:#FFF1DA;}
        .vr-check-foot {font-size:.74rem; line-height:1.45; color:#647487; margin:.9rem 0 0;}
        .vr-chat-head {display:flex; align-items:center; justify-content:space-between; gap:.6rem; margin-bottom:1rem;}
        .vr-chat-head > span {font-size:.68rem; font-weight:780; color:#00619E; background:#EAF4FB; padding:.32rem .58rem; border-radius:999px;}
        .vr-chat-greeting {display:flex; gap:.65rem; align-items:start; margin-bottom:1rem;}
        .vr-chat-avatar {width:32px; height:32px; flex:0 0 32px; display:grid; place-items:center; color:#00619E; background:#DDEEF8; border-radius:11px; font-weight:800;}
        .vr-chat-bubble {background:#F1F8FC; border:1px solid #D7E7F0; color:#36576E; border-radius:4px 14px 14px 14px; padding:.7rem .85rem; font-size:.84rem; line-height:1.5;}
        .vr-chat-you {max-width:85%; margin:.8rem 0 .8rem auto; padding:.68rem .85rem; border-radius:14px 14px 4px 14px; background:#00619E; color:white; font-size:.84rem; line-height:1.5; white-space:pre-wrap;}
        .vr-chat-answer {display:flex; gap:.65rem; align-items:start; margin-bottom:1rem;}
        .vr-chat-answer .vr-chat-bubble {background:#F1F8FC;}
        .vr-chat-hint {color:#647487; font-size:.73rem; margin:.4rem 0 .6rem;}
        [data-testid="stTextArea"] textarea {border:1px solid #B9D4E4; background:#fff; min-height:105px;}
        [data-testid="stTextArea"] textarea:focus {border-color:#0D74B4; box-shadow:0 0 0 2px #DDEEF8;}
        [data-testid="stTextArea"] label {font-size:.8rem; color:#36576E; font-weight:700;}
        button[data-testid="stBaseButton-secondary"] {border-color:#B9D4E4; color:#00619E;}
        @media(max-width:760px) {.vr-family-intro {display:block;} .vr-family-intro h1 {font-size:1.8rem;} .vr-patient-card {margin-top:.85rem; max-width:none;} .vr-family-card {padding:1rem;} .vr-check-badge {font-size:.65rem;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_caregiver_checklist(appointment) -> None:
    items = (
        ("Transportation", appointment.transportation),
        ("Registration", appointment.registration),
        ("Paperwork", appointment.paperwork),
    )
    descriptions = {
        "confirmed": ("✓", "Reported complete."),
        "unconfirmed": ("~", "A plan has been reported; it still needs confirmation."),
        "unknown": ("?", "No information has been added yet."),
        "incomplete": ("!", "This step may need attention."),
        "unavailable": ("–", "No option is currently available."),
    }
    confirmed = sum(item.status == "confirmed" for _, item in items)
    rows = "".join(
        f'<div class="vr-check-row {item.status}">'
        f'<span class="vr-check-icon">{descriptions[item.status][0]}</span>'
        f'<span class="vr-check-copy"><strong>{label}</strong><small>{descriptions[item.status][1]}</small></span>'
        f'<span class="vr-check-badge">{item.status.title()}</span></div>'
        for label, item in items
    )
    st.markdown(
        '<div class="vr-family-card"><div class="vr-check-head"><h2>Visit checklist</h2>'
        f'<span>{confirmed} of {len(items)} confirmed</span></div>'
        f'<div class="vr-check-track"><div class="vr-check-fill" style="width:{confirmed / len(items) * 100:.0f}%"></div></div>'
        + rows
        + '<p class="vr-check-foot">Only your care team can verify appointment requirements.</p></div>',
        unsafe_allow_html=True,
    )


def _remember_plan(plan: VisitPlan, message: str, appointment_snapshot: str) -> None:
    st.session_state["caregiver_plan"] = {
        "plan": plan,
        "message": message.strip(),
        "appointment_snapshot": appointment_snapshot,
    }


def _run_visit_plan(appointment, message: str) -> bool:
    st.session_state.pop("caregiver_plan", None)
    try:
        with st.spinner("Checking your visit details..."):
            plan = coordinate_visit(appointment, message)
    except RateLimitError:
        st.error("I'm sorry, VisitReady is temporarily unavailable. Please try again in a little while.")
    except AuthenticationError:
        st.error("VisitReady is temporarily unavailable. Please contact support for help.")
    except APIConnectionError:
        st.error("I'm sorry, VisitReady couldn't connect just now. Please try again in a moment.")
    except APIError:
        st.error("I'm sorry, VisitReady couldn't complete that request. Please try again in a moment.")
    except (ValueError, KeyError):
        st.error("I'm sorry, I couldn't prepare a safe next step from that message.")
    else:
        scope_denied = bool(plan.case_state and plan.case_state.pre_model_denial_reason)
        if not scope_denied and (plan.policy_result == "block" or plan.readiness_proposal is None):
            st.error("I couldn't safely prepare a next step. Please contact your care team for help.")
            return False
        try:
            record_run(plan, "live")
        except (OSError, ValueError):
            st.warning("Your next step is ready, but its activity record could not be saved.")
        _remember_plan(plan, message, appointment.model_dump_json())
        # Clear on the next render, before the text-area widget is created.
        # The submitted message stays in caregiver_plan, independent of the draft.
        st.session_state["clear_caregiver_message"] = True
        return True
    return False


def _show_result(appointment) -> None:
    result = st.session_state.get("caregiver_plan")
    if not result:
        return
    if result["appointment_snapshot"] != appointment.model_dump_json():
        return

    plan: VisitPlan = result["plan"]
    message = result["message"]
    response = compose_caregiver_response(plan)
    st.markdown(
        f'<div class="vr-chat-you">{escape(message.strip())}</div>'
        '<div class="vr-chat-answer"><span class="vr-chat-avatar">✦</span>'
        f'<div class="vr-chat-bubble">{escape(response.next_step)}</div></div>',
        unsafe_allow_html=True,
    )
    if plan.case_state and plan.case_state.clinical_gate_triggered:
        task = plan.case_state.staff_task
        if task:
            with st.container(border=True):
                st.success("Submitted for care team review.")
                st.markdown(f"**Ticket:** {task.task_id} · **Status:** Awaiting review")
                team_label = (task.assigned_team or "Appointment care team").removesuffix(" (demo)")
                st.caption(f"Appointment {task.appointment_id} · {team_label}")
        else:
            if st.button("Care team review", key="request_clinical_review", use_container_width=True):
                try:
                    submitted = submit_clinical_review(plan, confirmed=True)
                except ValueError:
                    st.error("This question could not be submitted. Please ask it again.")
                else:
                    _remember_plan(submitted, message, result["appointment_snapshot"])
                    try:
                        record_run(submitted, "live")
                    except (OSError, ValueError):
                        st.warning("The review request was processed, but its activity record could not be saved.")
                    st.rerun()
    if response.parking_help:
        message_key = sha256(message.strip().encode("utf-8")).hexdigest()[:12]
        render_parking_help(response.parking_help, key=f"chat_{message_key}", show_intro=False)
    elif response.public_guidance:
        st.caption("General visit guidance")
        st.write(response.public_guidance)
        st.markdown(f"[Read the public source: {response.source_title}]({response.source_url})")
    update = plan.readiness_proposal.proposed_update if plan.readiness_proposal else None
    if update and plan.case_state and not plan.case_state.pre_model_review_reason:
        st.markdown("**Update your checklist?**")
        st.write(
            f"Your report suggests **{update.item.title()} → {update.status.replace('_', ' ').title()}**. "
            "This hasn't been saved yet."
        )
        st.caption("Saving records what you reported; it doesn't verify the information with the hospital.")
        if st.button("Save my reported change", key="save_caregiver_update"):
            try:
                save_approved_update(appointment, plan.readiness_proposal, message, approved=True)
            except (PermissionError, ValueError, OSError):
                st.error("We couldn't save your update, so nothing has changed. Please try again.")
            else:
                st.session_state.pop("caregiver_plan", None)
                st.session_state["saved_notice"] = f"Thanks, your {update.item} update is saved in your checklist."
                st.rerun()


def render_caregiver_app() -> None:
    st.set_page_config(
        page_title="VisitReady · Your Visit",
        page_icon="✓",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_visitready_style()
    _apply_caregiver_style()
    if st.session_state.pop("clear_caregiver_message", False):
        st.session_state["caregiver_message"] = ""
    appointment = get_appointment("DEMO-001")
    patient_profile = load_patient_profile(appointment.appointment_id)
    unresolved = find_unresolved_items(appointment)
    st.markdown(
        '<div class="vr-family-header"><span class="vr-family-brand">◈ VisitReady</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="vr-family-intro"><div><span class="vr-eyebrow">YOUR VISIT</span>'
        '<h1>Feel ready for what comes next.</h1>'
        f'<p>{len(unresolved)} preparation item{"s" if len(unresolved) != 1 else ""} to check. Ask a question or share what changed.</p>'
        '</div><div class="vr-patient-card"><span class="vr-patient-avatar">SO</span>'
        '<div class="vr-patient-copy"><span>PATIENT</span>'
        f'<strong>{escape(appointment.patient_name.removesuffix(" (fictional)"))}</strong>'
        f'<small>{patient_profile.age_years} years old · {escape(appointment.appointment_id)}</small>'
        '<div class="vr-patient-reason"><span>REASON FOR VISIT</span>'
        f'{escape(patient_profile.visit_reason)}</div>'
        '</div></div></div>',
        unsafe_allow_html=True,
    )
    if appointment.location:
        st.caption(f"Appointment location: {appointment.location.name} · {appointment.location.address}")
    if saved_notice := st.session_state.pop("saved_notice", None):
        st.success(saved_notice)

    details_column, help_column = st.columns([.9, 1.3], gap="large")
    with details_column:
        _render_caregiver_checklist(appointment)
        with st.expander("What should I bring?"):
            guidance = get_public_guidance("what_to_bring")
            st.write(guidance.summary)
            st.markdown(f"[Read the Lurie Children's source]({guidance.source_url})")
            st.caption("General public guidance, not instructions for this specific appointment.")
        with st.expander("Parking & directions"):
            render_parking_help(lookup_appointment_parking("", appointment.location), key="visit")

    with help_column:
        with st.container(border=True):
            st.markdown(
                '<div class="vr-chat-head"><h2>Ask VisitReady</h2><span>HERE TO HELP</span></div>'
                '<div class="vr-chat-greeting"><span class="vr-chat-avatar">✦</span>'
                '<div class="vr-chat-bubble">Hi! I can help with your visit checklist, talk through a preparation concern, '
                'or point you to general visit guidance. What would you like help with today?</div></div>',
                unsafe_allow_html=True,
            )
            _show_result(appointment)
            message = st.text_area(
                "Your question or update",
                placeholder="Type a question about getting ready for this visit...",
                max_chars=2000,
                key="caregiver_message",
            )
            if st.button("Ask VisitReady", type="primary", disabled=not message.strip(), use_container_width=True):
                if _run_visit_plan(appointment, message):
                    st.rerun()
            st.caption("VisitReady can't provide medical advice.")

