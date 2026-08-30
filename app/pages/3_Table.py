import streamlit as st

from data import require_data, select_filter
from theme import apply_page_style, show_header

st.set_page_config(page_title="Table - T11 Recall", page_icon="assets/logo/logo.svg", layout="wide")
apply_page_style()
show_header("Full final dataset")

df = require_data()

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    vtype_choice, filtered = select_filter(df, "vehicle_type", "Vehicle type")
with filter_col2:
    seat_choice, filtered = select_filter(filtered, "seat_type", "Seat type")
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
