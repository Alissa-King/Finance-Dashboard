import streamlit as st

from src.db import get_session
from src.models import Funder

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

st.subheader("Organization")
st.text_input("Organization name", value="HIV Alliance", key="org_name")
st.text_input("Primary contact email", key="contact_email")

st.subheader("Fiscal year")
fy_start = st.selectbox(
    "Fiscal year start month",
    options=list(range(1, 13)),
    format_func=lambda m: __import__("calendar").month_name[m],
    index=6,  # default July
)

st.subheader("Database")
st.info("Database connection is configured via `DATABASE_URL` environment variable / Streamlit secrets.")

st.subheader("Authentication")
st.info(
    "App password is set via `st.secrets['password']` in `.streamlit/secrets.toml` "
    "(local) or Streamlit Community Cloud secrets manager (deployed)."
)

st.divider()
st.subheader("Sample Data")
with get_session() as _s:
    _seeded = _s.query(Funder).count() > 0

if _seeded:
    st.success("Sample data already loaded.")
else:
    st.warning("No data found. Load sample data to explore the dashboard.")
    if st.button("Load sample data", type="primary"):
        from seed import seed
        try:
            seed()
            st.success("Sample data loaded! Navigate to the Dashboard to explore.")
            st.rerun()
        except Exception as e:
            st.error(f"Seed failed: {e}")

st.divider()
st.caption("Settings persistence coming in Phase 2 (multi-user / org config table).")
