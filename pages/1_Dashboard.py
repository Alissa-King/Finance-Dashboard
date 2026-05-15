from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.db import get_session
from src.models import Deadline, DeadlineStatus, Grant, Funder, ReportingRequirement

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

today = date.today()
next_7 = today + timedelta(days=7)
next_30 = today + timedelta(days=30)


def _load_deadlines():
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
                "due_date": d.due_date,
                "status": d.status.value,
                "funder": f.name,
                "grant": g.grant_name,
                "requirement": r.name,
                "fiscal_period": d.fiscal_period_covered,
            })
        return pd.DataFrame(data)


try:
    df = _load_deadlines()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

if df.empty:
    st.info("No deadlines found. Add grants and generate deadlines to get started.")
    st.stop()

df["due_date"] = pd.to_datetime(df["due_date"]).dt.date

overdue = df[(df["due_date"] < today) & (~df["status"].isin(["Submitted", "Accepted", "Closed"]))]
due_7 = df[(df["due_date"] >= today) & (df["due_date"] <= next_7) & (~df["status"].isin(["Submitted", "Accepted", "Closed"]))]
due_30 = df[(df["due_date"] >= today) & (df["due_date"] <= next_30) & (~df["status"].isin(["Submitted", "Accepted", "Closed"]))]
recent = df[df["status"].isin(["Submitted", "Accepted"])].sort_values("due_date", ascending=False).head(5)

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("🔴 Overdue", len(overdue))
col2.metric("⚠️ Due in 7 days", len(due_7))
col3.metric("📅 Due in 30 days", len(due_30))

total = len(df)
completed = len(df[df["status"].isin(["Submitted", "Accepted", "Closed"])])
pct = round(100 * completed / total) if total else 0
col4.metric("✅ Compliance %", f"{pct}%")

st.divider()

# Overdue
if not overdue.empty:
    st.subheader("🔴 Overdue")
    st.dataframe(
        overdue[["funder", "grant", "requirement", "fiscal_period", "due_date", "status"]],
        use_container_width=True, hide_index=True,
    )

# Due in 7 days
if not due_7.empty:
    st.subheader("⚠️ Due in the next 7 days")
    st.dataframe(
        due_7[["funder", "grant", "requirement", "fiscal_period", "due_date", "status"]],
        use_container_width=True, hide_index=True,
    )

# Due in 30 days
st.subheader("📅 Due in the next 30 days")
if not due_30.empty:
    st.dataframe(
        due_30[["funder", "grant", "requirement", "fiscal_period", "due_date", "status"]],
        use_container_width=True, hide_index=True,
    )
else:
    st.success("Nothing due in the next 30 days.")

# Recently submitted
st.subheader("✅ Recently submitted")
if not recent.empty:
    st.dataframe(
        recent[["funder", "grant", "requirement", "fiscal_period", "due_date", "status"]],
        use_container_width=True, hide_index=True,
    )

st.divider()

# Cross-funder period view — the differentiator
st.subheader("🗓️ Cross-funder period view")
st.caption("See every deadline converging in a given month — the pileup view.")

months = sorted(df["due_date"].apply(lambda d: d.replace(day=1)).unique())
month_options = [m.strftime("%B %Y") for m in months]

if month_options:
    selected_month_str = st.selectbox("Select month", month_options)
    selected_month = date(
        int(selected_month_str.split()[-1]),
        pd.to_datetime(selected_month_str, format="%B %Y").month,
        1,
    )
    next_month = (selected_month + timedelta(days=32)).replace(day=1)
    month_df = df[(df["due_date"] >= selected_month) & (df["due_date"] < next_month)]

    if month_df.empty:
        st.info("No deadlines in this month.")
    else:
        st.dataframe(
            month_df[["funder", "grant", "requirement", "fiscal_period", "due_date", "status"]].sort_values("due_date"),
            use_container_width=True, hide_index=True,
        )
        fig = px.timeline(
            month_df.assign(start=month_df["due_date"], finish=month_df["due_date"]),
            x_start="start", x_end="finish",
            y="funder", color="funder",
            hover_data=["grant", "requirement", "fiscal_period", "status"],
            title=f"Deadlines in {selected_month_str}",
        )
        st.plotly_chart(fig, use_container_width=True)
