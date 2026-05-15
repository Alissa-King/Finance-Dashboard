import hashlib

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

from src.db import get_session
from src.models import Deadline, Funder, Grant, ReportingRequirement

st.set_page_config(page_title="Calendar", page_icon="📅", layout="wide")
st.title("📅 Calendar")


def _funder_color(name: str) -> str:
    """Deterministic color from funder name."""
    colors = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261", "#6d6875", "#b5838d"]
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(colors)
    return colors[idx]


try:
    with get_session() as session:
        rows = (
            session.query(Deadline, Grant, Funder, ReportingRequirement)
            .join(Grant, Deadline.grant_id == Grant.id)
            .join(Funder, Grant.funder_id == Funder.id)
            .join(ReportingRequirement, Deadline.requirement_id == ReportingRequirement.id)
            .all()
        )
        events = []
        for d, g, f, r in rows:
            events.append({
                "id": str(d.id),
                "title": f"{f.name} — {r.name}",
                "start": d.due_date.isoformat(),
                "end": d.due_date.isoformat(),
                "color": _funder_color(f.name),
                "extendedProps": {
                    "grant": g.grant_name,
                    "status": d.status.value,
                    "fiscal_period": d.fiscal_period_covered or "",
                },
            })
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

cal_options = {
    "editable": False,
    "selectable": True,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,dayGridYear",
    },
    "initialView": "dayGridMonth",
}

result = calendar(events=events, options=cal_options, key="compliance_calendar")

if result and result.get("eventClick"):
    ev = result["eventClick"]["event"]
    props = ev.get("extendedProps", {})
    with st.expander(f"📌 {ev['title']}", expanded=True):
        st.write(f"**Grant:** {props.get('grant')}")
        st.write(f"**Period:** {props.get('fiscal_period')}")
        st.write(f"**Status:** {props.get('status')}")
        st.write(f"**Due:** {ev['start']}")
