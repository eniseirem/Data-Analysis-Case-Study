# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
# ---

# %% [markdown]
# # Case Study — Data Analysis and Web App
#
# **Group number:** TBD
#
# **Members:** TBD

# %% [markdown]
# # Objective
#
# As a part of the safety inspection by the ADAC, defected seat frame "T11" was identified. The internal investigation revealed that products with ID numbers “11-213-2131-19000” to “11-213-2131-30100” were manufactured with incorrect production parameters. To ensure that the impact of the impaired T11 frame is identified,we analyze the data to trace the critical parts through production, determine which high-level components and vehicles contain them and identify the registrations associated with those vehicles as well as the related geographical information.
#
# Therefore, the main objective of the case study is to isolate the affected products and communicate it with relevant customers.
#
#
# # Analysis Strategy
#
# The analysis follows a forward traceability approach including:
#
# - Identifying all T11  parts belonging to the critical production range.
# - Determining which components contain the identified T11 parts.
# - Determining which vehicles contain the affected components.
# - Linking affected vehicles to registration records.
# - TODO: fill in with all the steps later
# -
# - Creation of one cleaned final dataset that serves as the sole input to the web application.

# %% [markdown]
# ## 1. Data Import
#
# Raw data was downloaded from tubCloud and extracted into `data/raw/` at the
# project root (kept out of version control — see `data/raw/README.md`). We
# reach it via a relative path so the notebook keeps running if someone else
# drops their own copy in the same place.

# %%
import csv
from pathlib import Path

import pandas as pd

RAW_DIR = Path("../../data/raw/IDA SoSe26 - Data")
assert RAW_DIR.exists(), f"Raw data not found at {RAW_DIR.resolve()} — see data/raw/README.md"


# %% [markdown]
# ### 1.1 Listing available files
#
# Before importing anything, we catalogue every file the group database
# provides, grouped by category, so we can see the full scope and spot
# irregularities before touching the data.

# %%
def list_raw_files(root: Path) -> pd.DataFrame:
    """Catalogue every file under `root`, one row per file, category = subfolder name
    (or '(root)' for files sitting directly under root, outside any category folder)."""
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            category = path.parent.name if path.parent != root else "(root)"
            rows.append({
                "category": category,
                "file": path.name,
                "extension": path.suffix,
                "size_mb": round(path.stat().st_size / 1e6, 1),
            })
    return pd.DataFrame(rows)


file_catalog = list_raw_files(RAW_DIR)
print(f"{len(file_catalog)} files across {file_catalog['category'].nunique()} categories")
file_catalog.groupby(["category", "extension"]).size()


# %% [markdown]
# ### 1.2 Manual inspection findings
#
# The catalogue above shows several categories mixing `.txt` and `.csv` files
# (e.g. `Einzelteil/`, `Komponente/`). The extension alone does not indicate information regarding the
# real format, so before writing any code we opened a byte-level sample
# of at least one file per category. This surfaced three issues that a standard
# `pd.read_csv`  would not have been able to parse correctly:
#
# 1. **`Einzelteil_T01.txt` has no row separator at all.** The whole file is a
#    single line: fields *within* a row are separated by `" | | "`, but there
#    is no character marking the end of one row and the start of the next —
#    the last field of row *n* is simply followed by one bare space and then
#    the (quoted) row index of row *n+1*. The header also contains three
#    copies of every real column, suffixed `.x`, `.y`, and unsuffixed —
#    evidence of a botched merge upstream on the source side; in the rows we
#    sampled only the `.x`-suffixed columns carried real values, `.y` and the
#    unsuffixed columns were all `NA`. We handle this with a dedicated parser
#    (`read_glued_export` below) instead of `pd.read_csv`.
# 2. **`Komponente_K7.txt` looked similarly broken (unstructured might be better word for this) at first** (no `\n`
#    anywhere in the file) but turned out to just use old-Mac-style
#    `\r`-only line endings with tab as the field separator.
#    `pd.read_csv(..., sep="\t", lineterminator="\r")` reads it directly —
#    confirmed on the real file (306,490 rows x 9 columns).
# 3. **A duplicate file:** `Einzelteil_T23.csv` exists both directly under
#    the data root and inside `Einzelteil/`. We byte-compared the two (`cmp`)
#    and confirmed they are identical (172,075,946 bytes each) — a stray
#    copy, not a distinct dataset. We treat the copy inside `Einzelteil/` as
#    canonical and exclude the root-level one from import.
#
# # August 12: findings
#
# To identify further inconsistencies after the initial manual inspectoin, we inspected the relevant file from the dataset (T11) and identified a way to parse it, which is provided below in details.
#
# 1. The text files inside Einzelteil do not follow an identical structure. For instance, T01 and T11 have different formatting, namely for T11:
# -  columns separated by tab, while rows are form-feed separated: \x0c, rather than a general newline character, therefore it can be read with:
# *pd.read_csv(..., sep="\t", lineterminator="\x0c")*
#
# 2. Fahrzeuge_OEM1_Typ11.csv (contains information regarding where the items were produced and when) contains two redundant counter columns with names "" and "X1". To ensure removing this would indeed be harmless, we verify that it is indeed just a counter (df["Unnamed: 0"].head()
# df["Unnamed: 0"].nunique()
# len(df)) and  remove it by running df = df.drop(columns=["Unnamed: 0"]) in cell below.
#
# As a result, we conclude that supplied dataset uses different conventions for separating the rows, therefore the single method cannot be reliably applied to read the files.  The loader detecs the identified format and applies parsing accordingly.
#
#

# %%
def read_glued_export(path: Path, delim: str, encoding: str = "latin-1") -> pd.DataFrame:
    """Parser for exports with no row separator at all: fields within a row are
    joined by `delim`, and consecutive rows are joined by a bare space with no
    delimiter of their own (see finding #1 above). Relies on two properties that
    hold for this dataset: no real field value contains a space, and every row's
    first field is a quoted row index, with row 1 always literally '"1"'."""
    text = path.read_text(encoding=encoding)
    tokens = text.split(delim)

    unglued = []
    for tok in tokens:
        if " " in tok:
            i = tok.rindex(" ")
            unglued.append(tok[:i])
            unglued.append(tok[i + 1:])
        else:
            unglued.append(tok)

    ncols = unglued.index('"1"')
    header = [h.strip('"') for h in unglued[:ncols]]
    data = unglued[ncols:]
    data = data[: len(data) - (len(data) % ncols)]  # drop a trailing partial row, if any

    rows = [data[i : i + ncols] for i in range(0, len(data), ncols)]
    df = pd.DataFrame(rows, columns=header)
    return df.apply(lambda c: c.str.strip('"') if c.dtype == "object" else c)


def load_raw_file(path: Path) -> pd.DataFrame:
    """Reads any raw file into a DataFrame, auto-detecting which of the format
    quirks from 1.2 applies (clean CSV, form-feed-separated, \\r-only line
    endings, or fully glued/no-separator). Extend this if a new pattern turns
    up in a file we haven't sampled yet. Everything is read as latin-1 since
    the dataset is German-locale and not reliably valid UTF-8."""
    with open(path, "rb") as f:
        sample = f.read(65536)

    if b"\n" in sample:
        sample_text = sample.decode("latin-1", errors="ignore")
        try:
            sep = csv.Sniffer().sniff(sample_text, delimiters=";,\t|").delimiter
        except csv.Error:
            sep = ";"
        return pd.read_csv(path, sep=sep, encoding="latin-1")

    if b"\x0c" in sample:
        return pd.read_csv(
            path,
            sep="\t",
            lineterminator="\x0c",
            encoding="latin-1",
            na_values=["NA"],
        )

    if b"\r" in sample:
        return pd.read_csv(path, sep="\t", lineterminator="\r", encoding="latin-1")

    delim = " | | " if b" | | " in sample else "\t"
    return read_glued_export(path, delim)


# %% [markdown]
# TODO: in 1.2 parser contains a fairly strong assumption:
#
# “no real field value contains a space”
#
# So I would not treat it as universally safe for every dataset unless your group has verified that carefully.

# %% [markdown]
# ### 1.3 Verifying the loader
#
# We check `load_raw_file` against one representative file per format found
# in 1.2 before relying on it more broadly.
#
# We use *load_raw_file(path)* as adapter around several different file formats.

# %%
samples = {
    "Einzelteil — clean csv": RAW_DIR / "Einzelteil" / "Einzelteil_T04.csv",
    "Einzelteil — glued, no row separator": RAW_DIR / "Einzelteil" / "Einzelteil_T01.txt",
    "Komponente — \\r line endings": RAW_DIR / "Komponente" / "Komponente_K7.txt",
    "Zulassungen — clean csv": RAW_DIR / "Zulassungen" / "Zulassungen_alle_Fahrzeuge.csv",
}

for label, path in samples.items():
    df = load_raw_file(path)
    print(f"{label}: {df.shape}")
    display(df.head(3))

# %% [markdown]
# # Initial EDA
#
# Since T11 is the starting point of the traceability analysis, we start by inspecting Einzelteil_T11.txt in the Einzelteil folder. Unrelated individual-part datasets are therefore not imported at this stage.
#
# Before transoforming anything, we conduct EDA to indeitfy types, missing values, defect distribution, etc.

# %%
t11_path = RAW_DIR/"Einzelteil"/"Einzelteil_T11.txt"

t11 = load_raw_file(t11_path)

print(f"Rows: {t11.shape[0]:,}")
print(f"Columns: {t11.shape[1]}")

#display the first and last 5 rows for getting the overview of entries.
print(t11.head())
print(t11.tail())

#brief summary of data
t11.info()

# %% [markdown]
# - After initial inspection, we can see that out of  2,385,260 entires, 2147106, i.e. 90% of entries in column  Fehlerhaft_Datum do not contain a value, indicating that they passed the Quality Check.

# %%
missing_values = (
    t11.isna()
    .sum()
    .sort_values(ascending=False)
    .to_frame("missing_values")
)

missing_values["percentage"] = (
    missing_values["missing_values"] / len(t11) * 100
).round(2)

display(missing_values)

# %% [markdown]
# A cross-check with the Fehlerhaft indicator shows that these missing dates correspond to parts for which no defect was recorded, while defective parts contain a defect date.

# %%
pd.crosstab(
    t11["Fehlerhaft"],
    t11["Fehlerhaft_Datum"].isna(),
    margins=True
)

#Fehlerhaft = 0 → mileage = 0
#Fehlerhaft = 1 → mileage > 0

# %% [markdown]
#  - To check if dataset contains duplicated entires, we also run the following cell

# %%
print(f"Duplicated rows: {t11.duplicated().sum():,}")

# %% [markdown]
# After checking duplicates, we check how many distinct values we have in each rows for *Herstellernummer*, **Werksnummer* and *Fehlerhaft*

# %%
display(t11["Herstellernummer"].value_counts(dropna=False)) #manufacturers 213, 212 and 215 produced T11
display(t11["Werksnummer"].value_counts(dropna=False)) #werksnummer = serial number
display(t11["Fehlerhaft"].value_counts(dropna=False))

#manufacturer values, n number produced by manufacturer


# %% [markdown]
# We pay particular attention to the variables Fehlerhaft, Fehlerhaft_Datum, and Fehlerhaft_Fahrleistung. Fehlerhaft indicates whether a defect was recorded for the part, Fehlerhaft_Datum records the corresponding defect date, and Fehlerhaft_Fahrleistung represents the distance travelled when the defect was recorded.
#
# since we know that 11-213-2131-19000 through 11-213-2131-30100 were produced using incorrect parameters, we can identify critical batch by filtering through ID range

# %%
print(
    t11.groupby("Fehlerhaft")[
        ["Fehlerhaft_Datum", "Fehlerhaft_Fahrleistung"]
    ].agg(["count", "min", "max"])
)

# %% [markdown]
# T11 export has an unusual extra row-index value, and X1 also appears to be a row counter. First we verify this assumption, and then we drop the column containing the duplicated information

# %%
print(t11.index[:10])
print(t11["X1"].head(10).tolist())

print("Rows:", len(t11))
print("Unique X1:", t11["X1"].nunique())
print("Duplicate X1:", t11["X1"].duplicated().sum())

# %% [markdown]
# X1 was verified to contain a unique sequential number for every observation (2,385,260 unique values across 2,385,260 rows), matching the source row index. It therefore represents an export-generated row counter rather than a production attribute and is removed from the analysis. (this is data cleaning step)

# %%
t11 = t11.reset_index(drop=True) #ensures that dataframe behaves like ordinary pandas row index
t11 = t11.drop(columns=["X1"])

# %% [markdown]
# We can conclude that X1 is an export-generated row counter with no production meaning.

# %% [markdown]
# Important column for the objectie is Fehlerhaft_Datum. To correctly analyze the values, we need to convert them to datetime type, as When pandas reads a CSV/text file, these may initially be stored as generic strings/objects rather than actual dates. This could help us further inspect earliest and latest dates of the defect by using .min() and .max() methods if necessary or extract month, year or other relevant information that is not as straightforward using strings.
#
# "coerce" ensures that in case pandas encounters something that cannot be interpreted as a valid date, will get converted to NaT (Not a Time). The motivation for using this is presence of NA for non-defective records.
#
# overview: : inspect raw type → convert to appropriate datetime type → verify that no valid non-missing records were lost during conversion.

# %%
t11["Fehlerhaft_Datum"] = pd.to_datetime(
    t11["Fehlerhaft_Datum"],
    errors="coerce"
)

#converts the column into a real pandas datetime type.

# %% [markdown]
# # Overview of production-date encoding:
#
# Production date is stored as number of days since 01-01-1970, i.e.
#  origin = 1970-01-01 + 14190 days = actual production date.
#
# we will need to inspect the production date for the following reasons:
# - checking when the critical batch was produced,
# - detecting impossible dates,
# - potentially showing the affected production period in your final analysis.

# %%
print(
    t11[
        ["Produktionsdatum_Origin_01011970", "origin"]
    ].head()
)

# %% [markdown]
# Check for ensuring that conversion did not introduce any accidental errors

# %%
original_dates = t11["Fehlerhaft_Datum"].copy()
#convert
parsed_dates = pd.to_datetime(
    original_dates,
    format="%Y-%m-%d",
    errors="coerce"
)

failed_conversion = (
    original_dates.notna()
    & parsed_dates.isna()
)

print("Non-missing dates before:", original_dates.notna().sum())
print("Dates that failed conversion:", failed_conversion.sum())

t11["Fehlerhaft_Datum"] = parsed_dates

# %%
#confirm datatype
print(t11["Fehlerhaft_Datum"].dtype)

# %% [markdown]
# To identify whih Manufacturing companies and Production sites produced T11, and how many T11 parts came from each, we group the records that have the same manufacturer and serial numbers
#

# %%
manufacturer_and_serialnumbers_grouped = t11.groupby(
        ["Herstellernummer", "Werksnummer"]
    ).size().reset_index(name="count")

print(manufacturer_and_serialnumbers_grouped)

# %% [markdown]
# From the criticla ID (*11-213-2131-19000*) itself, we know that:
#
# - 11   = T11
# - 213  = manufacturer
# - 2131 = manufacturing plant
# - 19000 = serial number
#
# T11 was produced by multiple manufacturers. For the case study, however, manufacturer 213 and plant 2131 are of particular importance because the specified critical ID range 11-213-2131-19000 to 11-213-2131-30100 originates from this manufacturer–plant combination.
#
#
# Therefore, the critical production batch specifically means:
# T11 parts manufactured by manufacturer 213 at plant 2131 whose serial number is between 19000 and 30100.

# %% [markdown]
# # next steps:
#
# 1. clean T11
#         ↓
# 2. extract serial number from ID_T11
#         ↓
# 3. filter manufacturer 213
#         ↓
# 4. filter plant 2131
#         ↓
# 5. filter only serial 19000–30100 and store into critical_t11
#
# And after critical_t11 exists, we can start exploring which components contain one of these critical T11 IDs.
#
# 11-213-2131-19000
#         ↓
# 11-213-2131-30100
#
# before doing that, we need to identify the structure of ID column to ensure looking for the values above is consistent with the format
#
#

# %%
t11_clean = t11.copy()  # keep t11 as the untouched original
print(t11_clean.shape)
print(t11_clean.columns.tolist())

# %% [markdown]
#

# %%
#extract the serial number from ID_T11.
t11_clean["serial_number"] = pd.to_numeric(
    t11_clean["ID_T11"].str.rsplit("-", n=1).str[-1],
    errors="coerce"
) #creates serial number by taking serial_number = 19000 from 11-213-2131-19000

# Instead of comparing entire strings, we can compare the new derived field: serial_number
print(t11_clean[["ID_T11", "serial_number"]].head(10))

print(
    "Failed serial number extractions:",
    t11_clean["serial_number"].isna().sum()
)

# %% [markdown]
# Now that we validated the serial number extraction, we can create the critical batchc with serial numbers from 1900ß through 20100 by filtering manufacturer 213, plant 2131 and serial number range.

# %%
critical_t11 = t11_clean[
    (t11_clean["Herstellernummer"].astype(str) == "213")
    & (t11_clean["Werksnummer"].astype(str) == "2131")
    & (t11_clean["serial_number"].between(19000, 30100))
].copy()

print(f"Critical T11 records: {len(critical_t11):,}")

print(
    "Serial range:",
    critical_t11["serial_number"].min(),
    "to",
    critical_t11["serial_number"].max()
)

print(
    "Manufacturers:",
    critical_t11["Herstellernummer"].unique()
)

print(
    "Plants:",
    critical_t11["Werksnummer"].unique()
)

print(
    "Duplicate critical IDs:",
    critical_t11["ID_T11"].duplicated().sum()
)

print(critical_t11.head()) #30100 - 19000 + 1 = 11,101

expected_serials = set(range(19000, 30101))

actual_serials = set(
    critical_t11["serial_number"].dropna().astype(int)
)

missing_serials = expected_serials - actual_serials

print("Expected possible serials:", len(expected_serials))
print("Present serials:", len(actual_serials))
print("Missing serials:", len(missing_serials))

display(
    critical_t11["Fehlerhaft"]
    .value_counts(dropna=False)
    .rename("count")
)

# %%
#The production-date conversion and some extra descriptive plots can still be added # later if useful, but they do not block the core business analysis.

# %% [markdown]
# #  Next, we will search for the Components that contain T11
#
# - For tackling this business problem, we inspect the Bestandteile_Komponente_*  files and trace T11 IDs through production hierarchy. These files describe which components are installed in higher-level components. For T11, we need to check which component types contain T11 and then match with critical T11 IDs. (what is exactly matching here define more concretely)
# - To do this, we inspect the schemas of the Bestandteile_Komponente_* files, that describe individual parts used in assembling a component

# %%
print("Missing T11 IDs:", t11_clean["ID_T11"].isna().sum())
print("Duplicate T11 IDs:", t11_clean["ID_T11"].duplicated().sum())
print("Failed serial extraction:", t11_clean["serial_number"].isna().sum())

# %%
component_path = RAW_DIR/"Komponente"

component_bom_files = sorted(
    component_path.glob("Bestandteile_Komponente_*")
)

print(f"files that contain relevant parts (T11): {len(component_bom_files)}")

for path in component_bom_files:
    print(path.name)

# %%
for path in component_bom_files:
    df_header = pd.read_csv(
        path,
        nrows=0,
        sep=None,
        engine="python"  # for automatic delimiter detection
    )

    print(f"\n{path.name}")
    print(df_header.columns.tolist())

    if "ID_T11" in df_header.columns:
        print(f"  -> T11 found in {path.name}")

# %% [markdown]
# The results of running the cell above indicates that Bestandteile_Komponente_K2LE1.csv contains specific ID_T11 parts and Bestandteile_Komponente_K2ST1 as well.
#
# T11
# ├── can be part of K2LE1
# └── can be part of K2ST1

# %%
k2le1_bom = load_raw_file(
    RAW_DIR / "Komponente" / "Bestandteile_Komponente_K2LE1.csv"
)

k2st1_bom = load_raw_file(
    RAW_DIR / "Komponente" / "Bestandteile_Komponente_K2ST1.csv"
)

print("K2LE1:", k2le1_bom.shape)
display(k2le1_bom.head())

print("K2ST1:", k2st1_bom.shape)
display(k2st1_bom.head())

# %% [markdown]
# we select teh relevant columns, since from preview above we see that ID_T11 and ID_K2LE1 amd ST! are relevant ones
#
# This indicates that T11 parts can be installed in components of type K2LE1 or K2ST1. The corresponding ID_K2LE1 and ID_K2ST1 columns identify the higher-level components containing each individual T11 part..
#
# To further trace the hierarchy, only those 2 component files need to be analyzed.

# %%
k2le1_trace = k2le1_bom[
    ["ID_T11", "ID_K2LE1"]
].copy()

k2st1_trace = k2st1_bom[
    ["ID_T11", "ID_K2ST1"]
].copy()

critical_ids = set(critical_t11["ID_T11"])

affected_k2le1 = k2le1_trace[
    k2le1_trace["ID_T11"].isin(critical_ids)
].copy()

affected_k2st1 = k2st1_trace[
    k2st1_trace["ID_T11"].isin(critical_ids)
].copy()

print("Affected K2LE1 rows:", len(affected_k2le1))
print("Affected K2LE1 components:", affected_k2le1["ID_K2LE1"].nunique())

print("Affected K2ST1 rows:", len(affected_k2st1))
print("Affected K2ST1 components:", affected_k2st1["ID_K2ST1"].nunique())

display(affected_k2le1.head())
display(affected_k2st1.head())

# %% [markdown]
# Because the component IDs have different column names, standardize them first:
#

# %%
affected_k2le1 = affected_k2le1.rename(
    columns={"ID_K2LE1": "component_id"}
)
affected_k2le1["component_type"] = "K2LE1"

affected_k2st1 = affected_k2st1.rename(
    columns={"ID_K2ST1": "component_id"}
)
affected_k2st1["component_type"] = "K2ST1"

#and then combine them

affected_components = pd.concat(
    [
        affected_k2le1[["ID_T11", "component_id", "component_type"]],
        affected_k2st1[["ID_T11", "component_id", "component_type"]],
    ],
    ignore_index=True
)

print("Affected component relationships:", len(affected_components))
print("Unique critical T11 IDs matched:", affected_components["ID_T11"].nunique())
print("Unique affected components:", affected_components["component_id"].nunique())

display(affected_components.head())

# %% [markdown]
# Check whether every critical T11 was actually found in one of these component parts lists:

# %%
matched_t11_ids = set(affected_components["ID_T11"])

unmatched_t11_ids = critical_ids - matched_t11_ids

print("Critical T11 IDs:", len(critical_ids))
print("Matched to a component:", len(matched_t11_ids))
print("Not matched to a component:", len(unmatched_t11_ids))

# %% [markdown]
# All 11,101 T11 parts belonging to the critical production batch were successfully
# matched to a higher-level component: 2,201 installed in K2LE1 components and
# 8,900 in K2ST1 components, with no critical T11 IDs left unmatched. The number
# of unique T11 IDs, component relationships, and unique component IDs is
# identical (11,101), indicating a one-to-one T11-to-component relationship in
# the observed parts-list data.

# %% [markdown]
# # Next Step: Identify Affected Vehicles based on affected componenets
#
# Previous cells identified the relevant componens we need to files that contain information regarding which components are installed in OEM1 vehicles  :
# - Bestandteile_Fahrzeuge_OEM1_Typ11.csv
# - Bestandteile_Fahrzeuge_OEM1_Typ12.csv
#
# Now we want to check which vehicles contain K2LE1 and K2ST1 components.

# %%
vehicle_files = [
    RAW_DIR/"Fahrzeug"/"Bestandteile_Fahrzeuge_OEM1_Typ11.csv",
    RAW_DIR/"Fahrzeug"/"Bestandteile_Fahrzeuge_OEM1_Typ12.csv",
]

#we check only headers to explore the schema of the file
for path in vehicle_files:
    header = pd.read_csv(path, nrows=0,  sep=None, engine="python")
    print(f"\n{path.name}")
    print(header.columns.tolist())


# %% [markdown]
# Since T11 is a seat-related part, we look into ID_Sitze as this is where the seat-related components would appear.
#
# Hypothesis:
# component_id
# (K2LE1 / K2ST1)
#        ↓
# ID_Sitze
#        ↓
# ID_Fahrzeug
#
# To verify this assumption, we preview a few samples.

# %%
for path in vehicle_files:
    sample = pd.read_csv(
        path,
        nrows=10,
        sep=None,
        engine="python"
    )

    print(f"\n{path.name}")
    display(sample[["ID_Sitze", "ID_Fahrzeug"]])

# %% [markdown]
# The results above confirm that ID_Sitze is indeed the column where the affected components appear. After this, we load the relevant columns.

# %%
affected_seat_ids = set(
    affected_components["component_id"]
)

print("Affected seat component IDs:", len(affected_seat_ids))

# %% [markdown]
# It means you have 11,101 unique affected seat-component IDs that you now want to search for inside ID_Sitze of the vehicle parts-list files.
#
# Next we need to search ID_Sitze in OEM1 vehicle parts lists to get the information regarding which vehicles are affected.
#

# %%
vehicle_boms = []

for path in vehicle_files:
    df = pd.read_csv(
        path,
        sep=None,
        engine="python",
        usecols=["ID_Sitze", "ID_Fahrzeug"]
    )

    if "Typ11" in path.name:
        df["vehicle_type"] = "Typ11"
    elif "Typ12" in path.name:
        df["vehicle_type"] = "Typ12"

    vehicle_boms.append(df)

vehicle_bom = pd.concat(
    vehicle_boms,
    ignore_index=True
)

print(vehicle_bom.shape)
display(vehicle_bom.head())

# %% [markdown]
# Now we need to filter to vehicles whose seat component is one of your affected components.

# %%
affected_vehicle_rows = vehicle_bom[
    vehicle_bom["ID_Sitze"].isin(affected_seat_ids)
].copy()

print("Matched component-to-vehicle rows:", len(affected_vehicle_rows))
print("Unique affected vehicles:",
      affected_vehicle_rows["ID_Fahrzeug"].nunique())

display(affected_vehicle_rows.head())

# %% [markdown]
# also we want to preserve the enitre trace from T11 to vehicle, so we need to merge the results back to affected_components
#

# %%
affected_vehicles = affected_components.merge(
    affected_vehicle_rows,
    left_on="component_id",
    right_on="ID_Sitze",
    how="left",
    validate="one_to_one"
)

display(affected_vehicles.head())

print("Trace rows:", len(affected_vehicles))
print("Unique T11 IDs:", affected_vehicles["ID_T11"].nunique())
print("Unique components:", affected_vehicles["component_id"].nunique())
print("Unique vehicles:", affected_vehicles["ID_Fahrzeug"].nunique())
print("Components not matched to a vehicle:",
      affected_vehicles["ID_Fahrzeug"].isna().sum())

# %% [markdown]
# All 11,101 affected seat components were successfully matched to an OEM1 vehicle. No affected component remained unmatched. The number of traceability records, unique T11 IDs, unique component IDs, and unique vehicle IDs is identical at 11,101. This indicates a one-to-one relationship in the observed data: each critical T11 part belongs to one affected component, and each of these affected components is installed in one distinct vehicle.
#
# Therefore, the critical production batch of 11,101 T11 parts ultimately corresponds to 11,101 affected OEM1 vehicles.
#
# After establishing the component-to-vehicle relationship using the `Bestandteile_Fahrzeuge_*`
# datasets, we now need vehicle-level attributes - production date, manufacturer, plant, and
# recorded defect information - so we load the vehicle production files and merge them into
# `affected_vehicles` on `ID_Fahrzeug` and `vehicle_type`.

# %%
vehicle_production_files = [
    (RAW_DIR / "Fahrzeug" / "Fahrzeuge_OEM1_Typ11.csv", "Typ11"),
    (RAW_DIR / "Fahrzeug" / "Fahrzeuge_OEM1_Typ12.csv", "Typ12"),
]

for path, vehicle_type in vehicle_production_files:
    header = pd.read_csv(
        path,
        nrows=0,
        sep=None,
        engine="python"
    )

    print(f"\n{path.name}")
    print(header.columns.tolist())

# %%
vehicle_production_frames = []

for path, vehicle_type in vehicle_production_files:
    df = load_raw_file(path)
    df["vehicle_type"] = vehicle_type

    vehicle_production_frames.append(df)

vehicle_production = pd.concat(
    vehicle_production_frames,
    ignore_index=True
)

print("Vehicle production rows:", len(vehicle_production))
print("Unique vehicle IDs:",
      vehicle_production["ID_Fahrzeug"].nunique())

display(vehicle_production.head())

# %% [markdown]
# To check a one-record-per-vehicle production table, we check for duplicates

# %%
print(
    "Duplicate vehicle IDs:",
    vehicle_production["ID_Fahrzeug"].duplicated().sum()
)


# %%
affected_vehicles_enriched = affected_vehicles.merge(
    vehicle_production,
    on=["ID_Fahrzeug", "vehicle_type"],
    how="left",
    validate="one_to_one"
)

# %% [markdown]
# Then validate the merge to ensure that all 11101 vehicles recieved the production information

# %%
print("Rows after merge:", len(affected_vehicles_enriched))

print(
    "Unique affected vehicles:",
    affected_vehicles_enriched["ID_Fahrzeug"].nunique()
)

# %% [markdown]
# Next steps:
# Vehicle production information
#  ↓
# Registration information
#  ↓
# Geographic information
#  ↓
# Final processed CSV
#  ↓

# %% [markdown]
# # Next Step: Add Registration Information
#
# Each vehicle's registration record (owner's municipality, registration date)
# lives in `Zulassungen_alle_Fahrzeuge.csv`, keyed by `IDNummer`, which uses the
# same ID format as `ID_Fahrzeug`. We check the schema first, then join.

# %%
zulassungen_path = RAW_DIR / "Zulassungen" / "Zulassungen_alle_Fahrzeuge.csv"
zulassungen_header = pd.read_csv(zulassungen_path, nrows=0, sep=None, engine="python")
print(zulassungen_header.columns.tolist())

zulassungen = pd.read_csv(
    zulassungen_path,
    sep=None,
    engine="python",
    usecols=["IDNummer", "Gemeinden", "Zulassung"]
)
print("Zulassungen rows:", len(zulassungen))
print("Duplicate IDNummer:", zulassungen["IDNummer"].duplicated().sum())
display(zulassungen.head())

# %% [markdown]
# `IDNummer` has duplicates because a vehicle can be re-registered (ownership
# change, new municipality). We keep the **most recent** registration per
# vehicle, since that is the one relevant for notifying the current owner.
# `Zulassung` is parsed to an actual date first - sorting the raw strings
# happens to work for this file since the format is already ISO (`YYYY-MM-DD`),
# but relying on that would silently break if the format ever changed.

# %%
zulassungen["Zulassung"] = pd.to_datetime(zulassungen["Zulassung"], errors="coerce")
print("Unparseable Zulassung values:", zulassungen["Zulassung"].isna().sum())

zulassungen_latest = (
    zulassungen
    .sort_values("Zulassung")
    .drop_duplicates(subset="IDNummer", keep="last")
)
print("Vehicles with a registration record:", len(zulassungen_latest))

# %%
affected_vehicles_registered = affected_vehicles_enriched.merge(
    zulassungen_latest,
    left_on="ID_Fahrzeug",
    right_on="IDNummer",
    how="left",
    validate="one_to_one"
)

print("Rows after merge:", len(affected_vehicles_registered))
print(
    "Affected vehicles with no registration record:",
    affected_vehicles_registered["Gemeinden"].isna().sum()
)

# %% [markdown]
# # Next Step: Add Geographic Information
#
# `Geodaten_Gemeinden` gives latitude/longitude per municipality name, so we can
# place each affected vehicle on a map via its registration town.

# %%
geodaten_path = RAW_DIR / "Geodaten" / "Geodaten_Gemeinden_v1.2_2017-08-22_TrR.csv"
geodaten = pd.read_csv(geodaten_path, sep=None, engine="python")
print(geodaten.columns.tolist())
display(geodaten.head())

# %% [markdown]
# Town names aren't guaranteed to match exactly on casing/whitespace, so we
# normalize both sides before joining. Coordinates also use German
# comma-decimal formatting (e.g. `"11,801372"`) and need converting to floats
# before they're usable as latitude/longitude.

# %%
affected_vehicles_registered["_town_key"] = (
    affected_vehicles_registered["Gemeinden"].str.strip().str.upper()
)
geodaten["_town_key"] = geodaten["Gemeinde"].str.strip().str.upper()
geodaten["Laengengrad"] = geodaten["Laengengrad"].astype(str).str.replace(",", ".").astype(float)
geodaten["Breitengrad"] = geodaten["Breitengrad"].astype(str).str.replace(",", ".").astype(float)

geodaten_unique = geodaten.drop_duplicates(subset="_town_key")

affected_vehicles_geo = affected_vehicles_registered.merge(
    geodaten_unique[["_town_key", "Laengengrad", "Breitengrad"]],
    on="_town_key",
    how="left",
    validate="many_to_one"
)

print("Rows after merge:", len(affected_vehicles_geo))
print(
    "Affected vehicles with no geo match:",
    affected_vehicles_geo["Laengengrad"].isna().sum()
)

# %% [markdown]
# # Final Dataset
#
# One row per affected vehicle: the critical T11 part, the seat component it
# went into, the vehicle it was installed in, that vehicle's production info,
# its current registration, and the coordinates to map it. This is the only
# dataset the web app reads.

# %%
final_columns = {
    "ID_T11": "part_id",
    "component_id": "seat_component_id",
    "component_type": "seat_type",
    "ID_Fahrzeug": "vehicle_id",
    "vehicle_type": "vehicle_type",
    "Produktionsdatum": "production_date",
    "Fehlerhaft": "vehicle_flagged_defective",
    "Fehlerhaft_Datum": "defect_date",
    "Fehlerhaft_Fahrleistung": "defect_mileage",
    "Gemeinden": "registration_municipality",
    "Zulassung": "registration_date",
    "Laengengrad": "longitude",
    "Breitengrad": "latitude",
}

final_dataset = (
    affected_vehicles_geo
    .rename(columns=final_columns)
    [list(final_columns.values())]
)

print("Final dataset shape:", final_dataset.shape)
display(final_dataset.head())

# %%
output_dir = Path("../../data/processed/case_study")
output_dir.mkdir(parents=True, exist_ok=True)
final_dataset.to_csv(output_dir / "t11_recall_affected_vehicles.csv", index=False)
print(f"Saved to {output_dir / 't11_recall_affected_vehicles.csv'}")

