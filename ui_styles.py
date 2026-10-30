"""Shared visual language for the two local VisitReady demo views."""

from html import escape

import streamlit as st

from models import Appointment


def apply_visitready_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width:1200px; padding:1.5rem 1.25rem 3rem;}
        h1, h2, h3 {color:#36576E !important; letter-spacing:-.035em;}
        h1 {font-size:2.5rem; margin-bottom:.25rem;}
        [data-testid="stSidebar"] {background:#F1F8FC; border-right:1px solid #D7E7F0; width:230px !important; min-width:230px !important; max-width:230px !important;}
        [data-testid="stSidebar"] > div {width:230px !important;}
        [data-testid="stSidebarNavLink"][aria-current="page"] {background:#DDEEF8 !important;}
        [data-testid="stSidebarNavLink"][aria-current="page"] p {color:#00619E !important;}
        div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px; border-color:#D7E7F0;}
        div.stButton > button {border-radius:11px; font-weight:700;}
        button[data-testid="stBaseButton-primary"] {background:#FDB813 !important; border-color:#FDB813 !important; color:#2D2D2D !important;}
        button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {background:#E9A708 !important; border-color:#E9A708 !important;}
        button[data-testid="stBaseButton-primary"]:disabled {background:#F7E6BB !important; border-color:#F7E6BB !important; color:#756C56 !important;}
        div[data-testid="stTextArea"] textarea {border-radius:12px;}
        .vr-eyebrow {font-size:.7rem; letter-spacing:.15em; font-weight:800; color:#0D74B4; margin-bottom:.1rem;}
        .vr-lead {color:#647487; font-size:.98rem; margin:.1rem 0 1.2rem; max-width:660px;}
        .vr-hero {background:linear-gradient(115deg,#E4F2FA,#F3F9FC 63%,#FFF8E8); border:1px solid #D7E7F0; border-radius:20px; padding:1.25rem 1.5rem; margin:0 0 1.4rem;}
        .vr-hero strong {display:block; color:#00619E; font-size:1.45rem; line-height:1.25; letter-spacing:-.025em;}
        .vr-hero p {color:#576170; margin:.45rem 0 0; max-width:620px; font-size:.92rem;}
        .vr-demo {display:inline-block; border-radius:999px; background:#EAF4FB; color:#00619E; padding:.28rem .7rem; font-size:.73rem; font-weight:750; margin-bottom:1rem;}
        .vr-card {background:#fff; border:1px solid #D7E7F0; border-radius:18px; padding:1.2rem 1.35rem; box-shadow:0 8px 22px rgba(0,97,158,.045); margin-bottom:.5rem;}
        .vr-card-head {display:flex; justify-content:space-between; align-items:center; gap:.6rem; margin-bottom:.9rem;}
        .vr-card-title {font-weight:780; font-size:1.04rem; color:#36576E;}
        .vr-muted {font-size:.78rem; color:#647487;}
        .vr-status-grid {display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem;}
        .vr-status {border:1px solid #E6EDE8; background:#FBFCFA; border-radius:12px; padding:.7rem .8rem; min-height:80px;}
        .vr-label {display:block; color:#647487; font-size:.77rem; margin-bottom:.35rem;}
        .vr-value {display:inline-block; font-size:.82rem; font-weight:750; border-radius:999px; padding:.2rem .55rem;}
        .vr-confirmed {color:#17664D; background:#DFF4E9;}
        .vr-unconfirmed, .vr-unknown {color:#8A5D1B; background:#FFF1D3;}
        .vr-incomplete, .vr-unavailable {color:#A04439; background:#FBE5E1;}
        .vr-note {font-size:.76rem; color:#647487; margin:.8rem 0 0;}
        .vr-metric {background:#fff; border:1px solid #D7E7F0; border-radius:14px; padding:1rem 1.1rem;}
        .vr-metric-number {font-size:1.55rem; font-weight:800; color:#00619E; line-height:1.1;}
        .vr-metric-label {font-size:.77rem; color:#647487; margin-top:.2rem;}
        .vr-client-topbar {display:flex; justify-content:space-between; align-items:center; gap:1rem; color:#698077; font-size:.78rem; margin:.1rem 0 1.25rem;}
        .vr-client-topbar strong {color:#285B51;}
        .vr-client-hero {display:grid; grid-template-columns:1.4fr .75fr; gap:1.4rem; align-items:center; background:linear-gradient(120deg,#E5F1E9,#F1F6EE 70%,#EAF4F0); border:1px solid #D8E8DD; border-radius:21px; padding:1.6rem 1.8rem; margin-bottom:1.1rem;}
        .vr-client-hero h2 {font-size:1.95rem; line-height:1.13; margin:.3rem 0 .55rem; color:#28594E;}
        .vr-client-hero p {color:#5B776B; font-size:.92rem; margin:0;}
        .vr-hero-note {background:rgba(255,255,255,.78); border:1px solid #E4EEE6; border-radius:15px; padding:1rem 1.05rem;}
        .vr-hero-note span {display:block; font-size:.68rem; letter-spacing:.1em; color:#719083; font-weight:750; margin-bottom:.35rem;}
        .vr-hero-note strong {display:block; color:#2D6657; font-size:1rem; line-height:1.2;}
        .vr-hero-note p {font-size:.76rem; color:#71877A; margin:.45rem 0 0;}
        .vr-status-grid.vr-vertical {grid-template-columns:1fr;}
        .vr-status-grid.vr-vertical .vr-status {min-height:0; display:flex; align-items:center; justify-content:space-between; gap:.75rem;}
        .vr-status-grid.vr-vertical .vr-label {margin:0; font-size:.88rem; color:#355E52; font-weight:650;}
        .vr-client-detail {background:#fff; border:1px solid #DEE9E2; border-radius:16px; padding:1rem 1.15rem; margin-bottom:1.2rem;}
        .vr-client-detail span {display:block; color:#71877A; font-size:.72rem; margin-bottom:.28rem;}
        .vr-client-detail strong {display:block; color:#2A5148; font-size:1rem;}
        .vr-client-detail small {color:#768A7F; font-size:.75rem;}
        @media (max-width:650px) {.vr-status-grid {grid-template-columns:1fr;} .vr-status {min-height:0;} .vr-card-head {display:block;} .vr-hero {padding:1rem;}}
        @media (max-width:800px) {.vr-client-hero {grid-template-columns:1fr; padding:1.2rem;} .vr-client-hero h2 {font-size:1.6rem;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### ◈ VisitReady")
        st.caption("CARE COORDINATION · LOCAL DEMO")
        st.write("Use the page menu above to switch between the caregiver, care-team, and activity views.")
        st.divider()
        st.caption("Fictional data. No connection to a hospital or its staff.")


def render_checklist(
    appointment: Appointment, title: str = "Your visit checklist", *, vertical: bool = False
) -> None:
    appointment_label = (
        "" if vertical else
        f'<span class="vr-muted">{escape(appointment.patient_name)} · {escape(appointment.appointment_id)}</span>'
    )
    cards = "".join(
        f'<div class="vr-status"><span class="vr-label">{label}</span>'
        f'<span class="vr-value vr-{item.status}">{item.status.replace("_", " ").title()}</span></div>'
        for label, item in (("Transportation", appointment.transportation), ("Registration", appointment.registration), ("Paperwork", appointment.paperwork))
    )
    checklist_html = (
        '<div class="vr-card"><div class="vr-card-head">'
        f'<span class="vr-card-title">{escape(title)}</span>'
        + appointment_label
        + f'</div><div class="vr-status-grid{" vr-vertical" if vertical else ""}">'
        + cards
        + '</div><p class="vr-note">Unknown = no information yet. Unconfirmed = a plan exists but is not settled.</p></div>'
    )
    st.markdown(checklist_html, unsafe_allow_html=True)


def render_client_sidebar(appointment: Appointment) -> None:
    """Show visit context; Streamlit's demo-page menu is hidden visually."""
    st.markdown(
        '<style>div[data-testid="stSidebarNav"] {display:none !important;}</style>',
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown("### ◈ VisitReady")
        st.caption("YOUR VISIT · FICTIONAL DEMO")
        st.divider()
        st.markdown(f"**{escape(appointment.patient_name)}**")
        st.caption(f"Appointment reference · {escape(appointment.appointment_id)}")
        st.divider()
        st.caption("This demo cannot contact a care team or provide medical advice.")


def render_metric(value: int, label: str) -> None:
    st.markdown(
        '<div class="vr-metric">'
        f'<div class="vr-metric-number">{value}</div>'
        f'<div class="vr-metric-label">{escape(label)}</div>'
        '</div>', unsafe_allow_html=True,
    )
