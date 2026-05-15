import streamlit as st

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
st.caption("Settings persistence coming in Phase 2 (multi-user / org config table).")
