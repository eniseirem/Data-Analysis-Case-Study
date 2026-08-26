"""Shared theme constants and page setup for the app.

Palette validated with the dataviz skill's validate_palette.js (light mode,
surface #fcfcfb): all hard gates pass. Slots 2/4/5 fall below 3:1 contrast on
the light surface (WARN, not a fail) - kept out of text, only used as fills
with a visible legend/table view alongside, per the skill's relief rule.
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
        [data-testid="stMetricValue"] {{
            color: {BRAND_BLUE};
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
        st.markdown(f"### T11 Seat Frame Recall Dashboard")
        if subtitle:
            st.caption(subtitle)
