from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.db import get_session
from src.models import Deadline, DeadlineStatus, Grant, Funder, ReportingRequirement

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg, #1a2035 0%, #0f1624 100%);
    border-radius: 12px;
    padding: 22px 20px 18px;
    border-left: 4px solid #4f8ef7;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5);
    text-align: center;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #6b7a99;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 2.8rem;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 4px;
}
.kpi-sub {
    font-size: 0.68rem;
    color: #4a5568;
}
section-header {
    font-size: 1rem;
    font-weight: 700;
    color: #c9d1d9;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}
</style>
""", unsafe_allow_html=True)

today = date.today()
next_7 = today + timedelta(days=7)
next_30 = today + timedelta(days=30)

STATUS_COLORS = {
    "Not Started": "#4a5568",
    "In Progress": "#00d4ff",
    "Submitted":   "#4f8ef7",
    "Accepted":    "#00e676",
    "Closed":      "#2d9e6b",
    "Overdue":     "#ff4757",
}


def _load():
    with get_session() as session:
        rows = (
            session.query(Deadline, Grant, Funder, ReportingRequirement)
            .join(Grant, Deadline.grant_id == Grant.id)
            .join(Funder, Grant.funder_id == Funder.id)
            .join(ReportingRequirement, Deadline.requirement_id == ReportingRequirement.id)
            .all()
        )
        return pd.DataFrame([{
            "id": d.id,
            "due_date": d.due_date,
            "status": d.status.value,
            "funder": f.name,
            "grant": g.grant_name,
            "requirement": r.name,
            "fiscal_period": d.fiscal_period_covered or "",
        } for d, g, f, r in rows])


try:
    df = _load()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

if df.empty:
    st.info("No deadlines found. Go to Settings to load sample data.")
    st.stop()

df["due_date"] = pd.to_datetime(df["due_date"]).dt.date

open_df = df[~df["status"].isin(["Submitted", "Accepted", "Closed"])]
overdue    = open_df[open_df["due_date"] < today]
due_7      = open_df[(open_df["due_date"] >= today) & (open_df["due_date"] <= next_7)]
due_30     = open_df[(open_df["due_date"] >= today) & (open_df["due_date"] <= next_30)]
upcoming   = open_df[open_df["due_date"] >= today].sort_values("due_date")
total      = len(df)
completed  = len(df[df["status"].isin(["Submitted", "Accepted", "Closed"])])
pct        = round(100 * completed / total) if total else 0

# ── Scrolling ticker ────────────────────────────────────────────────────────
items = []
for _, r in overdue.iterrows():
    items.append(f'<span style="color:#ff4757;font-weight:700">🔴 OVERDUE: {r["grant"]} — {r["requirement"]} was due {r["due_date"]}</span>')
for _, r in due_7.iterrows():
    d = (r["due_date"] - today).days
    items.append(f'<span style="color:#ffb300;font-weight:600">⚠️ DUE IN {d}d: {r["grant"]} — {r["requirement"]} ({r["fiscal_period"]})</span>')
for _, r in upcoming[~upcoming.index.isin(due_7.index)].head(12).iterrows():
    d = (r["due_date"] - today).days
    items.append(f'<span style="color:#00d4ff">📅 {d} days: {r["grant"]} — {r["requirement"]} ({r["fiscal_period"]})</span>')
if not items:
    items = ['<span style="color:#00e676">✅ All deadlines on track — great work!</span>']

sep = ' <span style="color:#21262d">&nbsp;◆&nbsp;</span> '
ticker_html = (sep.join(items) + sep) * 3

components.html(f"""
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: transparent; overflow: hidden; }}
.wrap {{
  display: flex; align-items: center; height: 44px;
  background: linear-gradient(90deg, #0d1117, #161b22, #0d1117);
  border: 1px solid #21262d; border-radius: 8px; overflow: hidden;
}}
.badge {{
  background: linear-gradient(180deg, #4f8ef7, #2563eb);
  color: #fff; font-family: 'Courier New', monospace;
  font-size: 10px; font-weight: 900; letter-spacing: 2.5px;
  padding: 0 16px; height: 100%;
  display: flex; align-items: center; flex-shrink: 0;
  border-right: 1px solid #21262d;
}}
.outer {{ overflow: hidden; flex: 1; height: 100%; display: flex; align-items: center; }}
.track {{
  display: inline-flex; align-items: center; white-space: nowrap;
  font-family: 'Courier New', monospace; font-size: 12.5px;
  animation: scroll 70s linear infinite; padding-left: 24px;
}}
@keyframes scroll {{
  0%   {{ transform: translateX(0); }}
  100% {{ transform: translateX(-33.333%); }}
}}
</style>
<div class="wrap">
  <div class="badge">LIVE&nbsp;DEADLINES</div>
  <div class="outer"><div class="track">{ticker_html}</div></div>
</div>
""", height=52)

st.markdown("<br>", unsafe_allow_html=True)

# ── KPI cards ───────────────────────────────────────────────────────────────
def kpi_card(col, label, value, sub, color, glow=False):
    shadow = f"0 0 22px {color}55, 0 4px 24px rgba(0,0,0,0.5)" if glow else "0 4px 24px rgba(0,0,0,0.5)"
    col.markdown(f"""
    <div class="kpi-card" style="border-left-color:{color};box-shadow:{shadow}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "🔴 Overdue",        len(overdue),  "require immediate action",  "#ff4757", glow=len(overdue) > 0)
kpi_card(c2, "⚠️ Due in 7 Days",  len(due_7),    "urgent attention needed",   "#ffb300", glow=len(due_7) > 0)
kpi_card(c3, "📅 Due in 30 Days", len(due_30),   "plan and prepare now",      "#00d4ff")
kpi_card(c4, "✅ Compliance",      f"{pct}%",     f"{completed} of {total} completed", "#00e676", glow=pct >= 80)

st.markdown("<br>", unsafe_allow_html=True)

# ── Countdown ring + compliance gauge ───────────────────────────────────────
col_ring, col_gauge = st.columns(2)

with col_ring:
    st.markdown("##### ⏳ Next Open Deadline")
    if not upcoming.empty:
        nxt = upcoming.iloc[0]
        days_left = (nxt["due_date"] - today).days
        ring_color = "#ff4757" if days_left <= 7 else "#ffb300" if days_left <= 14 else "#00d4ff"
        pct_ring = max(5, min(100, round(100 * days_left / 90)))

        fig = go.Figure(go.Pie(
            values=[pct_ring, 100 - pct_ring],
            hole=0.74,
            marker=dict(colors=[ring_color, "#141929"], line=dict(width=0)),
            textinfo="none", hoverinfo="skip",
            direction="clockwise", sort=False,
        ))
        fig.update_layout(
            showlegend=False, height=220,
            margin=dict(t=0, b=0, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(text=f"<b>{days_left}</b>", x=0.5, y=0.58,
                     font=dict(size=52, color=ring_color, family="Arial Black"),
                     showarrow=False),
                dict(text="days left", x=0.5, y=0.38,
                     font=dict(size=13, color="#6b7a99"), showarrow=False),
            ],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"**{nxt['requirement']}**  \n"
            f"{nxt['grant']} &nbsp;·&nbsp; {nxt['fiscal_period']}  \n"
            f"Due **{nxt['due_date'].strftime('%B %d, %Y')}**"
        )
    else:
        st.success("No upcoming open deadlines!")

with col_gauge:
    st.markdown("##### 📊 Overall Compliance")
    gauge_color = "#00e676" if pct >= 75 else "#ffb300" if pct >= 50 else "#ff4757"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix": "%", "font": {"size": 56, "color": "#e0e6f0", "family": "Arial Black"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1,
                     "tickcolor": "#30363d", "tickfont": {"color": "#6b7a99", "size": 10}},
            "bar": {"color": gauge_color, "thickness": 0.3},
            "bgcolor": "#0d1117",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 50],   "color": "#1f1418"},
                {"range": [50, 75],  "color": "#1f1e14"},
                {"range": [75, 100], "color": "#141f18"},
            ],
            "threshold": {"line": {"color": "#00e676", "width": 2},
                          "thickness": 0.8, "value": 75},
        },
    ))
    fig.update_layout(
        height=280, margin=dict(t=20, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e6f0"},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Status donuts by funder ─────────────────────────────────────────────────
st.markdown("##### 📁 Status by Funder")
funders = sorted(df["funder"].unique())
cols = st.columns(len(funders))

for col, funder in zip(cols, funders):
    counts = df[df["funder"] == funder]["status"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.65,
        marker=dict(
            colors=[STATUS_COLORS.get(s, "#4f8ef7") for s in counts.index],
            line=dict(color="#0d1117", width=2),
        ),
        textinfo="none",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"<b>{funder}</b>", font=dict(size=11, color="#c9d1d9"), x=0.5, y=0.97),
        showlegend=False,
        margin=dict(t=26, b=0, l=0, r=0),
        height=150,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    col.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Gantt timeline ──────────────────────────────────────────────────────────
st.markdown("##### 🗓️ Deadline Timeline")

gantt = df.copy()
gantt["x0"] = pd.to_datetime(gantt["due_date"]) - pd.Timedelta(days=1)
gantt["x1"] = pd.to_datetime(gantt["due_date"]) + pd.Timedelta(days=1)
gantt["hover"] = (
    gantt["grant"] + "<br>" +
    gantt["requirement"] + " (" + gantt["fiscal_period"] + ")<br>" +
    "Due: " + gantt["due_date"].astype(str) + "<br>Status: " + gantt["status"]
)

fig = px.timeline(
    gantt, x_start="x0", x_end="x1", y="funder",
    color="status", color_discrete_map=STATUS_COLORS,
    custom_data=["hover"],
)
fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
fig.update_yaxes(autorange="reversed")
fig.add_shape(
    type="line",
    x0=str(today), x1=str(today), y0=0, y1=1, yref="paper",
    line=dict(color="#00d4ff", width=1.5, dash="dash"),
)
fig.add_annotation(
    x=str(today), y=1.02, yref="paper",
    text="Today", showarrow=False,
    font=dict(color="#00d4ff", size=11), xanchor="left",
)
fig.update_layout(
    height=320,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
    font={"color": "#c9d1d9", "size": 12},
    xaxis=dict(gridcolor="#21262d", title=""),
    yaxis=dict(gridcolor="#21262d", title=""),
    legend=dict(orientation="h", y=-0.22, font=dict(color="#c9d1d9"), bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=16, b=60, l=10, r=10),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Monthly density heat map ─────────────────────────────────────────────────
st.markdown("##### 🔥 Monthly Deadline Density")

hm = df.copy()
hm["month"] = pd.to_datetime(hm["due_date"]).dt.to_period("M").astype(str)
pivot = hm.pivot_table(index="funder", columns="month", values="id", aggfunc="count", fill_value=0)

fig = go.Figure(go.Heatmap(
    z=pivot.values.tolist(),
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale=[[0, "#0d1117"], [0.25, "#162032"], [0.6, "#1668dc"], [1.0, "#00d4ff"]],
    hovertemplate="%{y}<br>%{x}: <b>%{z}</b> deadlines<extra></extra>",
    showscale=True,
    colorbar=dict(tickfont=dict(color="#c9d1d9"), outlinewidth=0,
                  title=dict(text="Count", font=dict(color="#8892a4"))),
    text=pivot.values.tolist(),
    texttemplate="%{text}",
    textfont=dict(color="#c9d1d9", size=13),
))
fig.update_layout(
    height=240,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
    font={"color": "#c9d1d9"},
    xaxis=dict(tickangle=-45, gridcolor="#21262d", title=""),
    yaxis=dict(gridcolor="#21262d", title=""),
    margin=dict(t=10, b=80, l=10, r=10),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── 3D Views ────────────────────────────────────────────────────────────────
st.markdown("##### 🌐 3D Interactive Views")
st.caption("Drag to rotate · Scroll to zoom · Double-click to reset")

tab_terrain, tab_space = st.tabs(["🏔️ Deadline Terrain", "🔮 Deadline Space"])

with tab_terrain:
    st.caption("Deadline density per funder per month — peaks show pileup months. Drag to spin.")
    hm3 = df.copy()
    hm3["month"] = pd.to_datetime(hm3["due_date"]).dt.to_period("M").astype(str)
    pivot3 = hm3.pivot_table(index="funder", columns="month", values="id",
                              aggfunc="count", fill_value=0)
    funder_labels = pivot3.index.tolist()
    month_labels  = pivot3.columns.tolist()
    z_data = pivot3.values.tolist()

    fig = go.Figure(go.Surface(
        z=z_data,
        x=list(range(len(month_labels))),
        y=list(range(len(funder_labels))),
        colorscale=[
            [0.0, "#0d1117"], [0.2, "#0d2137"],
            [0.5, "#1668dc"], [0.8, "#00aaff"], [1.0, "#00d4ff"],
        ],
        showscale=True,
        opacity=0.92,
        colorbar=dict(title=dict(text="Deadlines", font=dict(color="#8892a4")),
                      tickfont=dict(color="#c9d1d9"), outlinewidth=0),
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor="#ffffff",
                   project=dict(z=True)),
        ),
        hovertemplate=(
            "Funder: <b>%{customdata}</b><br>"
            "Month: <b>%{x}</b><br>"
            "Deadlines: <b>%{z}</b><extra></extra>"
        ),
        customdata=[[funder_labels[i]] * len(month_labels) for i in range(len(funder_labels))],
    ))
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                tickvals=list(range(len(month_labels))),
                ticktext=[m[-7:] for m in month_labels],
                title=dict(text="Month", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a",
                showbackground=True, tickfont=dict(color="#6b7a99", size=8),
            ),
            yaxis=dict(
                tickvals=list(range(len(funder_labels))),
                ticktext=funder_labels,
                title=dict(text="Funder", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a",
                showbackground=True, tickfont=dict(color="#6b7a99", size=9),
            ),
            zaxis=dict(
                title=dict(text="Deadlines", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a",
                showbackground=True, tickfont=dict(color="#6b7a99"),
            ),
            bgcolor="#0a0e1a",
            camera=dict(eye=dict(x=1.6, y=-1.8, z=1.3)),
            aspectmode="manual",
            aspectratio=dict(x=2.0, y=1.0, z=0.6),
        ),
        height=540,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_space:
    st.caption(
        "Every deadline as a bubble in 3D space — X = days from today, Y = funder, Z = status. "
        "Bigger bubbles = closer to due. Drag to explore."
    )
    status_order = list(STATUS_COLORS.keys())
    sc = df.copy()
    sc["due_dt"]      = pd.to_datetime(sc["due_date"])
    sc["days"]        = (sc["due_dt"] - pd.Timestamp(today)).dt.days
    sc["funder_idx"]  = sc["funder"].map({f: i for i, f in enumerate(sorted(sc["funder"].unique()))})
    sc["status_idx"]  = sc["status"].map({s: i for i, s in enumerate(status_order)})
    sc["bubble_size"] = sc["days"].abs().apply(lambda d: max(6, 28 - d * 0.08))
    funder_names = sorted(sc["funder"].unique())

    fig = go.Figure()
    for status, color in STATUS_COLORS.items():
        sub = sc[sc["status"] == status]
        if sub.empty:
            continue
        hover = (
            "<b>" + sub["grant"] + "</b><br>" +
            sub["requirement"] + "<br>" +
            sub["fiscal_period"] + "<br>" +
            "Due: " + sub["due_date"].astype(str) + "<br>" +
            "Status: <b>" + sub["status"] + "</b><br>" +
            sub["days"].apply(lambda d: f"In {d} days" if d >= 0 else f"{abs(d)} days ago")
        )
        fig.add_trace(go.Scatter3d(
            x=sub["days"], y=sub["funder_idx"], z=sub["status_idx"],
            mode="markers", name=status,
            marker=dict(size=sub["bubble_size"], color=color, opacity=0.88,
                        line=dict(width=0.5, color="#0d1117")),
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[-0.5, len(funder_names) - 0.5], z=[0, 0],
        mode="lines", line=dict(color="#00d4ff", width=5),
        name="Today", hoverinfo="skip",
    ))
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title=dict(text="Days from Today", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a", showbackground=True,
                tickfont=dict(color="#6b7a99"),
                zeroline=True, zerolinecolor="#00d4ff", zerolinewidth=2,
            ),
            yaxis=dict(
                tickvals=list(range(len(funder_names))), ticktext=funder_names,
                title=dict(text="Funder", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a", showbackground=True,
                tickfont=dict(color="#6b7a99", size=9),
            ),
            zaxis=dict(
                tickvals=list(range(len(status_order))), ticktext=status_order,
                title=dict(text="Status", font=dict(color="#c9d1d9")),
                gridcolor="#21262d", backgroundcolor="#0a0e1a", showbackground=True,
                tickfont=dict(color="#6b7a99", size=9),
            ),
            bgcolor="#0a0e1a",
            camera=dict(eye=dict(x=1.8, y=-2.0, z=1.1)),
            aspectmode="manual",
            aspectratio=dict(x=2.0, y=1.0, z=1.2),
        ),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="v", x=1.0, y=0.9, font=dict(color="#c9d1d9", size=11),
                    bgcolor="rgba(13,17,23,0.7)", bordercolor="#30363d", borderwidth=1),
        font=dict(color="#c9d1d9"),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)
