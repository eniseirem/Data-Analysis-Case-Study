import plotly.express as px
import streamlit as st

from data import require_data, select_filter
from theme import (
    BRAND_BLUE,
    DEFECT_STATUS_COLORS,
    PLOTLY_LAYOUT,
    SEAT_TYPE_COLORS,
    apply_page_style,
    show_header,
)

st.set_page_config(page_title="Charts - T11 Recall", page_icon="assets/logo/logo.svg", layout="wide")
apply_page_style()
show_header("Breakdowns of the affected population")

df = require_data()

filter_col1, filter_col2, _ = st.columns([2, 2, 3])
with filter_col1:
    vtype_choice, filtered = select_filter(df, "vehicle_type", "Vehicle type")
with filter_col2:
    seat_choice, filtered = select_filter(filtered, "seat_type", "Seat type")

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
