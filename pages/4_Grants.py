from datetime import date

import streamlit as st

from src.db import get_session
from src.models import Funder, FunderType, Grant, ReportingRequirement
from src.services.instance_generator import generate_deadlines

st.set_page_config(page_title="Grants", page_icon="🏛️", layout="wide")
st.title("🏛️ Grants")

tab_list, tab_add, tab_funders, tab_reqs = st.tabs(["Active Grants", "Add Grant", "Funders", "Requirements"])

# --- Active Grants ---
with tab_list:
    try:
        with get_session() as session:
            grants = (
                session.query(Grant, Funder)
                .join(Funder, Grant.funder_id == Funder.id)
                .all()
            )
        if not grants:
            st.info("No grants yet.")
        else:
            for g, f in grants:
                with st.expander(f"{g.grant_name} ({f.name})"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Award #:** {g.award_number or '—'}")
                    col1.write(f"**Program:** {g.program or '—'}")
                    col1.write(f"**Period:** {g.period_start} → {g.period_end}")
                    col2.write(f"**Amount:** ${g.award_amount:,.2f}" if g.award_amount else "**Amount:** —")
                    col2.write(f"**Program Officer:** {g.program_officer_name or '—'}")
                    col2.write(f"**PO Email:** {g.program_officer_email or '—'}")
                    if g.notes:
                        st.write(f"**Notes:** {g.notes}")
    except Exception as e:
        st.error(f"Database error: {e}")

# --- Add Grant ---
with tab_add:
    st.subheader("Add a new grant")
    try:
        with get_session() as session:
            funders = session.query(Funder).all()
            funder_map = {f.name: f.id for f in funders}
            reqs = session.query(ReportingRequirement).all()
            req_map = {r.name: r.id for r in reqs}
    except Exception as e:
        st.error(f"Database error: {e}")
        st.stop()

    if not funder_map:
        st.warning("Add funders first (Funders tab).")
    else:
        with st.form("add_grant"):
            funder_name = st.selectbox("Funder", list(funder_map.keys()))
            grant_name = st.text_input("Grant name *")
            award_number = st.text_input("Award / CFDA number")
            program = st.text_input("Program")
            col1, col2 = st.columns(2)
            period_start = col1.date_input("Period start", value=date.today().replace(month=1, day=1))
            period_end = col2.date_input("Period end", value=date.today().replace(month=12, day=31))
            award_amount = st.number_input("Award amount ($)", min_value=0.0, step=1000.0)
            po_name = st.text_input("Program officer name")
            po_email = st.text_input("Program officer email")
            notes = st.text_area("Notes")
            sel_reqs = st.multiselect("Auto-generate deadlines for requirements", list(req_map.keys()))
            submitted = st.form_submit_button("Add grant", type="primary")

        if submitted and grant_name:
            with get_session() as session:
                grant = Grant(
                    organization_id=1,
                    funder_id=funder_map[funder_name],
                    grant_name=grant_name,
                    award_number=award_number or None,
                    program=program or None,
                    period_start=period_start,
                    period_end=period_end,
                    award_amount=award_amount or None,
                    program_officer_name=po_name or None,
                    program_officer_email=po_email or None,
                    notes=notes or None,
                )
                session.add(grant)
                session.flush()

                deadline_count = 0
                for req_name in sel_reqs:
                    req = session.get(ReportingRequirement, req_map[req_name])
                    deadlines = generate_deadlines(grant, req)
                    for d in deadlines:
                        session.add(d)
                    deadline_count += len(deadlines)

            st.success(f"Grant added. {deadline_count} deadline(s) generated.")

# --- Funders ---
with tab_funders:
    st.subheader("Funders")
    try:
        with get_session() as session:
            funders = session.query(Funder).all()
            for f in funders:
                st.write(f"**{f.name}** ({f.type.value}) {f.parent_agency or ''}")
    except Exception as e:
        st.error(f"Database error: {e}")

    st.divider()
    st.subheader("Add funder")
    with st.form("add_funder"):
        fname = st.text_input("Name *")
        ftype = st.selectbox("Type", [t.value for t in FunderType])
        parent = st.text_input("Parent agency")
        website = st.text_input("Website")
        fnotes = st.text_area("Notes")
        add_funder = st.form_submit_button("Add funder")

    if add_funder and fname:
        with get_session() as session:
            session.add(Funder(name=fname, type=FunderType(ftype), parent_agency=parent or None,
                               website=website or None, notes=fnotes or None, organization_id=1))
        st.success(f"Funder '{fname}' added.")
        st.rerun()

# --- Requirements ---
with tab_reqs:
    st.subheader("Reporting requirements")
    try:
        with get_session() as session:
            reqs = session.query(ReportingRequirement).all()
            for r in reqs:
                st.write(f"**{r.name}** — {r.frequency.value}, due +{r.due_offset_days}d")
    except Exception as e:
        st.error(f"Database error: {e}")

    st.divider()
    st.subheader("Add requirement")
    with st.form("add_req"):
        rname = st.text_input("Name *")
        rfreq = st.selectbox("Frequency", ["quarterly", "semi_annual", "annual", "monthly", "one_time"])
        roffset = st.number_input("Days after period close due", min_value=0, value=30)
        rmethod = st.text_input("Submission method / portal")
        rlink = st.text_input("Form link")
        rdesc = st.text_area("Description")
        add_req = st.form_submit_button("Add requirement")

    if add_req and rname:
        with get_session() as session:
            from src.models import ReportFrequency
            session.add(ReportingRequirement(
                name=rname, frequency=ReportFrequency(rfreq),
                due_offset_days=int(roffset), submission_method=rmethod or None,
                form_link=rlink or None, description=rdesc or None,
            ))
        st.success(f"Requirement '{rname}' added.")
        st.rerun()
