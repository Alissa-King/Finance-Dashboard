import streamlit as st

st.set_page_config(
    page_title="Grants Compliance Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Password gate — required for public Streamlit Community Cloud deploys
def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    with st.form("login"):
        st.title("Grants Compliance Dashboard")
        st.caption("HIV Alliance — Finance Team")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        expected = st.secrets.get("password", "")
        if password == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


if not _check_password():
    st.stop()

# Sidebar navigation (Streamlit handles multipage routing automatically via /pages)
st.sidebar.title("📋 Grants Compliance")
st.sidebar.caption("HIV Alliance")

# Home page content when landing on app.py directly
st.title("Welcome")
st.info("Use the sidebar to navigate to the Dashboard, Calendar, Deadlines, Grants, Settings, or Import pages.")
