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
# (e.g. `Einzelteil/`, `Komponente/`). The extension alone doesn't tell you the
# real format, so before writing any import code we opened a byte-level sample
# of at least one file per category. This surfaced three issues that a plain
# `pd.read_csv` call would not survive:
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
# 2. **`Komponente_K7.txt` looked similarly broken at first** (no `\n`
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
# Because of this, files need to be read format-by-format rather than with
# one blanket call — see the loader below.

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
    quirks from 1.2 applies. Covers the two broken patterns found so far;
    extend this if a new pattern turns up in a file we haven't sampled yet."""
    with open(path, "rb") as f:
        sample = f.read(65536)

    if b"\n" in sample:
        sample_text = sample.decode("latin-1", errors="ignore")
        try:
            sep = csv.Sniffer().sniff(sample_text, delimiters=";,\t|").delimiter
        except csv.Error:
            sep = ";"
        return pd.read_csv(path, sep=sep)
    if b"\r" in sample:
        return pd.read_csv(path, sep="\t", lineterminator="\r")
    delim = " | | " if b" | | " in sample else "\t"
    return read_glued_export(path, delim)

# %% [markdown]
# ### 1.3 Verifying the loader
#
# We check `load_raw_file` against one representative file per format found
# in 1.2 before relying on it more broadly.

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
