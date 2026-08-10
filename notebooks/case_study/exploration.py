# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: title,-all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
# ---

# %%
# Scratch exploration to help pick the case study's analytical angle.
# Not part of the graded notebook. Delete before submission.

import csv
import re
from pathlib import Path

import pandas as pd

RAW = Path("../../data/raw/IDA SoSe26 - Data")

COLUMN_TRANSLATIONS = {
    "": "row_id",
    "X1": "seq_id",
    "X": "row_num",
    "Produktionsdatum": "production_date",
    "Produktionsdatum_Origin_01011970": "production_date_serial",
    "origin": "date_origin_reference",
    "Herstellernummer": "manufacturer_number",
    "Werksnummer": "plant_number",
    "Fehlerhaft": "defective",
    "Fehlerhaft_Datum": "defect_date",
    "Fehlerhaft_Fahrleistung": "defect_mileage",
    "IDNummer": "id_number",
    "Gemeinden": "municipality",
    "Gemeinde": "municipality",
    "Zulassung": "registration_date",
    "Postleitzahl": "postal_code",
    "PLZ": "postal_code",
    "ORT": "city",
    "Werk": "plant_code",
    "Laengengrad": "longitude",
    "Breitengrad": "latitude",
    "Lngengrad": "longitude",
    "Wareneingang": "goods_receipt_date",
    "ID_Fahrzeug": "vehicle_id",
    "ID_Karosserie": "body_id",
    "ID_Schaltung": "transmission_id",
    "ID_Sitze": "seat_id",
    "ID_Motor": "engine_id",
}
ID_PATTERN = re.compile(r"^ID_(.+)$")


def translate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort German -> English column rename, so the rest of the script
    (and its output) reads in English. Not authoritative — cross-check against
    the raw header before this naming goes into the real notebook."""
    renamed = {}
    for col in df.columns:
        col = col.strip()
        if col in COLUMN_TRANSLATIONS:
            renamed[col] = COLUMN_TRANSLATIONS[col]
            continue
        m = ID_PATTERN.match(col)
        if m:
            renamed[col] = f"{m.group(1).lower()}_id"
    return df.rename(columns=renamed)


def detect_sep(path: Path) -> str:
    # delimiters aren't consistent even within a category, e.g. Fahrzeuge_*.csv
    # is comma-delimited while Bestandteile_Fahrzeuge_*.csv is semicolon-delimited
    with open(path, "rb") as f:
        sample = f.read(65536).decode("latin-1", errors="ignore")
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        return ";"


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    kwargs.setdefault("sep", detect_sep(path))
    kwargs.setdefault("encoding", "latin-1")
    return translate_columns(pd.read_csv(path, **kwargs))


VEHICLE_TYPES = {
    ("OEM1", "Typ11"): "Fahrzeuge_OEM1_Typ11.csv",
    ("OEM1", "Typ12"): "Fahrzeuge_OEM1_Typ12.csv",
    ("OEM2", "Typ21"): "Fahrzeuge_OEM2_Typ21.csv",
    ("OEM2", "Typ22"): "Fahrzeuge_OEM2_Typ22.csv",
}
BESTANDTEILE = {
    ("OEM1", "Typ11"): "Bestandteile_Fahrzeuge_OEM1_Typ11.csv",
    ("OEM1", "Typ12"): "Bestandteile_Fahrzeuge_OEM1_Typ12.csv",
    ("OEM2", "Typ21"): "Bestandteile_Fahrzeuge_OEM2_Typ21.csv",
    ("OEM2", "Typ22"): "Bestandteile_Fahrzeuge_OEM2_Typ22.csv",
}


def read_fahrzeuge(fname):
    # usecols must match the raw (German) header - translation happens after read
    path = RAW / "Fahrzeug" / fname
    df = read_csv(path, usecols=["ID_Fahrzeug", "Werksnummer", "Fehlerhaft"])
    return df.astype({"vehicle_id": "string", "plant_number": "string", "defective": "int8"})


def read_bestandteile(fname):
    path = RAW / "Fahrzeug" / fname
    df = read_csv(path, usecols=["ID_Schaltung", "ID_Sitze", "ID_Motor", "ID_Fahrzeug"], dtype="string")
    for col, new in [("transmission_id", "transmission"), ("seat_id", "seats"), ("engine_id", "engine")]:
        df[new] = df[col].str.split("-").str[0].str.extract(r"^(K\d[A-Z]+)")[0]
    return df[["vehicle_id", "transmission", "seats", "engine"]]


# %% 1. Defect rate by OEM / vehicle type / plant
print("=" * 60)
print("1. Defect rate by OEM / type / plant")
print("=" * 60)

all_vehicles = []
for (oem, typ), fname in VEHICLE_TYPES.items():
    df = read_fahrzeuge(fname)
    df["oem"] = oem
    df["typ"] = typ
    all_vehicles.append(df)
    rate = df["defective"].mean()
    print(f"{oem} {typ}: {len(df):>10,} vehicles, defect rate = {rate:.2%}")

vehicles = pd.concat(all_vehicles, ignore_index=True)
print()
print("By plant, top 10 by vehicle count:")
by_plant = vehicles.groupby(["oem", "typ", "plant_number"])["defective"].agg(["mean", "count"])
print(by_plant.sort_values("count", ascending=False).head(10))

# %% 2. Defect rate by configuration (engine / transmission / seats)
print()
print("=" * 60)
print("2. Defect rate by configuration")
print("=" * 60)

all_config = []
for key, fname in BESTANDTEILE.items():
    bdf = read_bestandteile(fname)
    fdf = all_vehicles[list(VEHICLE_TYPES.keys()).index(key)][["vehicle_id", "defective"]]
    merged = bdf.merge(fdf, on="vehicle_id", how="inner")
    all_config.append(merged)

config = pd.concat(all_config, ignore_index=True)
for dim in ["engine", "transmission", "seats"]:
    print(f"\nDefect rate by {dim}:")
    print(config.groupby(dim)["defective"].agg(["mean", "count"]))

# %% 3. Are the geodata join keys usable?
print()
print("=" * 60)
print("3. Geodata joinability")
print("=" * 60)

zulassungen = read_csv(RAW / "Zulassungen" / "Zulassungen_alle_Fahrzeuge.csv", usecols=["Gemeinden"])
gemeinden = read_csv(RAW / "Geodaten" / "Geodaten_Gemeinden_v1.2_2017-08-22_TrR.csv")

zul_towns = set(zulassungen["municipality"].str.strip().str.upper().unique())
geo_towns = set(gemeinden["municipality"].str.strip().str.upper().unique())
overlap = zul_towns & geo_towns
print(f"Zulassungen distinct towns: {len(zul_towns)}")
print(f"Geodaten_Gemeinden distinct towns: {len(geo_towns)}")
print(f"Overlap: {len(overlap)} ({len(overlap) / len(zul_towns):.1%} of Zulassungen towns matched)")

tier1 = read_csv(RAW / "Geodaten" / "Tier1_Werke_2017-07-11_v1.2_TrR.csv")
werke_codes = set(tier1["plant_code"].astype(str).str.strip())
vehicle_werk_codes = set(vehicles["plant_number"].unique())
print(f"\nTier1 plant codes (sample): {list(werke_codes)[:10]}")
print(f"Vehicle plant_number values (sample): {list(vehicle_werk_codes)[:10]}")
print(f"Overlap: {len(werke_codes & vehicle_werk_codes)}")
