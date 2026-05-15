import tempfile

import streamlit as st

from src.services.csv_importer import import_csv

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")
st.title("📥 Import")

st.markdown("""
Upload a CSV exported from your existing Excel compliance calendar.

**Required columns:**
- `grant_name`
- `funder_name`
- `requirement_name`
- `due_date` (YYYY-MM-DD)

**Optional columns:**
- `funder_type` (federal / state / local / private_foundation / other)
- `frequency` (quarterly / semi-annual / annual / monthly / one-time)
- `fiscal_period_covered`
- `status` (Not Started / In Progress / Submitted / Accepted / Closed)
- `notes`
""")

uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    if st.button("Import", type="primary"):
        with st.spinner("Importing..."):
            try:
                stats = import_csv(tmp_path)
                st.success(
                    f"Import complete! "
                    f"Funders: {stats['funders']} | "
                    f"Grants: {stats['grants']} | "
                    f"Requirements: {stats['requirements']} | "
                    f"Deadlines: {stats['deadlines']}"
                )
                if stats["errors"]:
                    st.warning(f"{len(stats['errors'])} row(s) had errors:")
                    for err in stats["errors"][:20]:
                        st.text(err)
            except Exception as e:
                st.error(f"Import failed: {e}")
