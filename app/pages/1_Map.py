import plotly.express as px
import streamlit as st

from data import require_data, select_filter
from theme import BRAND_BLUE, PLOTLY_LAYOUT, apply_page_style, show_header

st.set_page_config(page_title="Map - T11 Recall", page_icon="assets/logo/logo.svg", layout="wide")
apply_page_style()
show_header("Where affected vehicles are registered")

df = require_data()
mappable = df.dropna(subset=["latitude", "longitude"])

filter_col, _ = st.columns([2, 5])
with filter_col:
    seat_choice, filtered = select_filter(mappable, "seat_type", "Seat type")

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
