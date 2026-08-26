import streamlit as st

from data import require_data
from theme import apply_page_style, show_header

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
col1.metric("Affected vehicles", f"{df['vehicle_id'].nunique():,}")
col2.metric("Already flagged defective", f"{df['vehicle_flagged_defective'].sum():,}")
col3.metric("Leather seats (K2LE1)", f"{(df['seat_type'] == 'K2LE1').sum():,}")
col4.metric("Fabric seats (K2ST1)", f"{(df['seat_type'] == 'K2ST1').sum():,}")

st.divider()

st.markdown(
    """
    Use the pages in the sidebar to explore:
    - **Map** - where affected vehicles are registered
    - **Charts** - breakdowns by seat type, vehicle type, and defect status
    - **Table** - the full final dataset, filterable
    """
)
