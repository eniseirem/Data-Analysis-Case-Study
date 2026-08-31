"""T11 Seat Frame Recall Dashboard - single-file Streamlit app.

Reads only the final processed dataset (SoSe26_Case_Study_finalData_Group_19.csv)
produced by the case study notebook. Palette was checked for colorblind-safety and
contrast against the light surface (#fcfcfb) - everything passes. A few colors
(orange, yellow, magenta) sit under 3:1 contrast on this background, so they're
only used as chart fills next to a visible legend or table, never as text on
their own.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------

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

LOGO_PATH = "assets/logo/logo.svg"


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
        st.image(LOGO_PATH, width=64)
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


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

DATA_PATH = Path(__file__).parent / ".." / "data" / "processed" / "case_study" / "SoSe26_Case_Study_finalData_Group_19.csv"


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, parse_dates=["production_date", "registration_date"])


def require_data() -> pd.DataFrame:
    """Loads the final dataset, or stops the app with a clear error if it's missing."""
    if not DATA_PATH.exists():
        st.error(
            f"Final dataset not found at `{DATA_PATH.resolve()}`. Run the case study "
            "notebook through the 'Final Dataset' section first."
        )
        st.stop()
    return load_data()


def select_filter(df: pd.DataFrame, column: str, label: str, key: str) -> tuple[str, pd.DataFrame]:
    """Renders an 'All'-or-one-value selectbox for `column` and returns (choice, filtered df)."""
    options = ["All"] + sorted(df[column].dropna().unique().tolist())
    choice = st.selectbox(label, options, key=key)
    filtered = df if choice == "All" else df[df[column] == choice]
    return choice, filtered


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------

def view_home(df: pd.DataFrame):
    show_header("Quality Science - Supply Chain Traceability")

    st.markdown(
        """
        ### Objective

        An ADAC safety inspection identified a defective seat frame batch (part **T11**,
        manufacturer 213, plant 2131, serial numbers 19000-30100). This dashboard traces
        that batch through production to the affected vehicles and their registered
        owners, so the relevant customers can be identified and notified.
        """
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_tile("Affected vehicles", f"{df['vehicle_id'].nunique():,}")
    with col2:
        stat_tile("Already flagged defective", f"{df['vehicle_flagged_defective'].sum():,}")
    with col3:
        stat_tile("Leather seats (K2LE1)", f"{(df['seat_type'] == 'K2LE1').sum():,}")
    with col4:
        stat_tile("Fabric seats (K2ST1)", f"{(df['seat_type'] == 'K2ST1').sum():,}")

    st.divider()

    st.markdown(
        """
        Roughly 1 in 10 affected vehicles is already flagged defective in production
        records - the other 90% haven't failed yet, which is exactly why this is a
        proactive recall rather than a reactive one. See **Map** for where owners are
        concentrated geographically, **Charts** for how the batch splits by seat type
        and production date, and **Table** for the full list to export.
        """
    )


def view_map(df: pd.DataFrame):
    show_header("Where affected vehicles are registered")

    mappable = df.dropna(subset=["latitude", "longitude"])

    filter_col, _ = st.columns([2, 5])
    with filter_col:
        seat_choice, filtered = select_filter(mappable, "seat_type", "Seat type", key="map_seat_type")

    st.caption(
        f"{len(filtered):,} of {len(mappable):,} affected vehicles with a known "
        f"registration location ({len(df) - len(mappable):,} have no geo match)."
    )

    by_town = (
        filtered
        .groupby(["registration_municipality", "latitude", "longitude"])
        .size()
        .reset_index(name="affected_vehicles")
    )

    center = dict(lat=by_town["latitude"].mean(), lon=by_town["longitude"].mean())

    fig = px.scatter_map(
        by_town,
        lat="latitude",
        lon="longitude",
        size="affected_vehicles",
        hover_name="registration_municipality",
        hover_data={"affected_vehicles": True, "latitude": False, "longitude": False},
        color_discrete_sequence=[BRAND_BLUE],
        center=center,
        zoom=5,
        height=600,
        map_style="open-street-map",
    )
    fig.update_layout(**PLOTLY_LAYOUT, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        by_town.sort_values("affected_vehicles", ascending=False).rename(
            columns={"registration_municipality": "Municipality", "affected_vehicles": "Affected vehicles"}
        )[["Municipality", "Affected vehicles"]],
        use_container_width=True,
        hide_index=True,
    )


def view_charts(df: pd.DataFrame):
    show_header("Breakdowns of the affected population")

    filter_col1, filter_col2, _ = st.columns([2, 2, 3])
    with filter_col1:
        vtype_choice, filtered = select_filter(df, "vehicle_type", "Vehicle type", key="charts_vehicle_type")
    with filter_col2:
        seat_choice, filtered = select_filter(filtered, "seat_type", "Seat type", key="charts_seat_type")

    st.caption(f"Showing {len(filtered):,} of {len(df):,} affected vehicles.")

    left, right = st.columns(2)

    with left:
        st.markdown("**Affected vehicles by seat type**")
        by_seat = filtered["seat_type"].value_counts().reset_index()
        by_seat.columns = ["seat_type", "count"]
        fig = px.bar(by_seat, x="seat_type", y="count", color="seat_type",
                     color_discrete_map=SEAT_TYPE_COLORS, text="count")
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                           xaxis_title="Seat type", yaxis_title="Affected vehicles")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Defect status by seat type**")
        # fillna so an unexpected flag value shows up as "Unknown" in the chart
        # instead of quietly disappearing from the groupby
        status = filtered.assign(
            status=filtered["vehicle_flagged_defective"]
            .map({0: "Not yet flagged", 1: "Already flagged"})
            .fillna("Unknown")
        )
        by_status = status.groupby(["seat_type", "status"]).size().reset_index(name="count")
        fig = px.bar(by_status, x="seat_type", y="count", color="status",
                     color_discrete_map=DEFECT_STATUS_COLORS, barmode="stack")
        fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Seat type", yaxis_title="Affected vehicles",
                           legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Production date of affected vehicles**")
    fig = px.histogram(filtered, x="production_date", color_discrete_sequence=[BRAND_BLUE])
    fig.update_layout(**PLOTLY_LAYOUT, xaxis_title="Production date", yaxis_title="Affected vehicles")
    st.plotly_chart(fig, use_container_width=True)


def view_table(df: pd.DataFrame):
    show_header("Full final dataset")

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        vtype_choice, filtered = select_filter(df, "vehicle_type", "Vehicle type", key="table_vehicle_type")
    with filter_col2:
        seat_choice, filtered = select_filter(filtered, "seat_type", "Seat type", key="table_seat_type")
    with filter_col3:
        search = st.text_input("Search vehicle ID")

    if search:
        filtered = filtered[filtered["vehicle_id"].str.contains(search, case=False, na=False, regex=False)]

    st.caption(f"{len(filtered):,} of {len(df):,} rows")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.download_button(
        "Download filtered data as CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="SoSe26_Case_Study_finalData_Group_19_filtered.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------

st.set_page_config(page_title="T11 Seat Frame Recall", page_icon=LOGO_PATH, layout="wide")
apply_page_style()

df = require_data()

with st.sidebar:
    st.image(LOGO_PATH, width=48)
    page = st.radio("Navigate", ["Home", "Map", "Charts", "Table"], label_visibility="collapsed")

if page == "Home":
    view_home(df)
elif page == "Map":
    view_map(df)
elif page == "Charts":
    view_charts(df)
elif page == "Table":
    view_table(df)
