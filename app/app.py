import streamlit as st

from data import require_data
from theme import apply_page_style, show_header, stat_tile

st.set_page_config(
    page_title="T11 Seat Frame Recall",
    page_icon="assets/logo/logo.svg",
    layout="wide",
)
apply_page_style()
show_header("Quality Science - Supply Chain Traceability")

df = require_data()

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
