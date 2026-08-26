"""Shared data access for every page: one path, one cached load, one filter helper."""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / ".." / "data" / "processed" / "case_study" / "t11_recall_affected_vehicles.csv"


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, parse_dates=["production_date", "registration_date"])


def require_data() -> pd.DataFrame:
    """Loads the final dataset, or stops the page with a clear error if it's missing."""
    if not DATA_PATH.exists():
        st.error(
            f"Final dataset not found at `{DATA_PATH.resolve()}`. Run the case study "
            "notebook through the 'Final Dataset' section first."
        )
        st.stop()
    return load_data()


def select_filter(df: pd.DataFrame, column: str, label: str) -> tuple[str, pd.DataFrame]:
    """Renders an 'All'-or-one-value selectbox for `column` and returns (choice, filtered df)."""
    options = ["All"] + sorted(df[column].dropna().unique().tolist())
    choice = st.selectbox(label, options)
    filtered = df if choice == "All" else df[df[column] == choice]
    return choice, filtered
