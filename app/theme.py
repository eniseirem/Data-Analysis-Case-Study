"""Shared theme constants and page setup for the app.

Palette was checked for colorblind-safety and contrast against the light
surface (#fcfcfb) - everything passes. A few colors (orange, yellow, magenta)
sit under 3:1 contrast on this background, so they're only used as chart
fills next to a visible legend or table, never as text on their own.
"""

import streamlit as st

BRAND_BLUE = "#2a78d6"

CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"

# fixed per-category colors so the same value is always the same color,
# regardless of which order it happens to appear in a given chart's data
SEAT_TYPE_COLORS = {
    "K2LE1": CATEGORICAL[0],
    "K2ST1": CATEGORICAL[1],
}
DEFECT_STATUS_COLORS = {
    "Already flagged": CATEGORICAL[7],
    "Not yet flagged": CATEGORICAL[0],
    "Unknown": TEXT_MUTED,
}

FONT_FAMILY = "'Source Sans Pro', system-ui, -apple-system, 'Segoe UI', sans-serif"

PLOTLY_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY),
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    colorway=CATEGORICAL,
    xaxis=dict(gridcolor=GRIDLINE, linecolor=GRIDLINE),
    yaxis=dict(gridcolor=GRIDLINE, linecolor=GRIDLINE),
)


def apply_page_style():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: {FONT_FAMILY};
        }}
        .stApp {{
            background-color: {PAGE_PLANE};
        }}
        h1, h2, h3 {{
            color: {TEXT_PRIMARY};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {SURFACE};
            border-right: 1px solid {GRIDLINE};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_header(subtitle: str = ""):
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image("assets/logo/logo.svg", width=64)
    with col_title:
        st.markdown("### T11 Seat Frame Recall Dashboard")
        if subtitle:
            st.caption(subtitle)


def stat_tile(label: str, value: str):
    st.markdown(
        f"""
        <div style="
            background: #eef5fc;
            border-left: 3px solid {BRAND_BLUE};
            border-radius: 2px;
            padding: 0.75rem 1rem;
        ">
            <div style="color: {TEXT_SECONDARY}; font-size: 0.85rem;">{label}</div>
            <div style="color: {TEXT_PRIMARY}; font-size: 1.75rem; font-weight: 600;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
