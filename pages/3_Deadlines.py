from datetime import date

import pandas as pd
import streamlit as st

from src.db import get_session
from src.models import AuditLog, Deadline, DeadlineStatus, Funder, Grant, ReportingRequirement

st.set_page_config(page_title="Deadlines", page_icon="📋", layout="wide")
st.title("📋 Deadlines")


def _load():
    with get_session() as session:
        rows = (
            session.query(Deadline, Grant, Funder, ReportingRequirement)
            .join(Grant, Deadline.grant_id == Grant.id)
            .join(Funder, Grant.funder_id == Funder.id)
            .join(ReportingRequirement, Deadline.requirement_id == ReportingRequirement.id)
            .all()
        )
        data = []
        for d, g, f, r in rows:
            data.append({
                "id": d.id,
                "funder": f.name,
                "grant": g.grant_name,
                "requirement": r.name,
                "fiscal_period": d.fiscal_period_covered or "",
                "due_date": d.due_date,
                "status": d.status.value,
                "submitted_date": d.submitted_date,
                "notes": d.notes or "",
            })
        return pd.DataFrame(data)


try:
    df = _load()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("No deadlines yet.")
    st.stop()

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    funders = ["All"] + sorted(df["funder"].unique().tolist())
    sel_funder = st.selectbox("Funder", funders)
with col2:
    statuses = ["All"] + [s.value for s in DeadlineStatus]
    sel_status = st.selectbox("Status", statuses)
with col3:
    sort_col = st.selectbox("Sort by", ["due_date", "funder", "status", "grant"])

filtered = df.copy()
if sel_funder != "All":
    filtered = filtered[filtered["funder"] == sel_funder]
if sel_status != "All":
    filtered = filtered[filtered["status"] == sel_status]
filtered = filtered.sort_values(sort_col)

st.dataframe(
    filtered[["funder", "grant", "requirement", "fiscal_period", "due_date", "status", "submitted_date"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Update deadline status")

deadline_options = {
    f"{row['grant']} — {row['requirement']} ({row['fiscal_period']}) due {row['due_date']}": row["id"]
    for _, row in filtered.iterrows()
}

if deadline_options:
    selected_label = st.selectbox("Select deadline", list(deadline_options.keys()))
    selected_id = deadline_options[selected_label]

    new_status = st.selectbox("New status", [s.value for s in DeadlineStatus])
    submitted_date = st.date_input("Submitted date (if applicable)", value=None)
    submission_link = st.text_input("Submission link (optional)")
    notes = st.text_area("Notes (optional)")

    if st.button("Update", type="primary"):
        with get_session() as session:
            d = session.get(Deadline, selected_id)
            old_status = d.status.value
            d.status = DeadlineStatus(new_status)
            if submitted_date:
                d.submitted_date = submitted_date
            if submission_link:
                d.submission_link = submission_link
            if notes:
                d.notes = notes
            session.add(AuditLog(
                deadline_id=d.id,
                user_id=None,
                action=f"Status changed from {old_status} to {new_status}",
                timestamp=__import__("datetime").datetime.utcnow(),
            ))
        st.success(f"Updated to {new_status}")
        st.rerun()
