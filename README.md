# QWIDA — Quality Science Data Analysis Case Study

Group number: 
Members: 

## What this repo contains

Two graded deliverables, kept in separate branches after the shared structure below is in place:

- **`general` branch** — `notebooks/general_tasks/` — standalone Jupyter Notebook covering the 6 General Tasks 

- **`case` branch** — `notebooks/case_study/` + `app/` — the Case Study notebook (data import, cleaning, tidy-data prep, final merged dataset) and the Streamlit web app built on top of that final dataset only.

`main` holds the shared scaffolding both branches build on: folder layout and `data/`. There's no shared code module — each notebook is self-contained; General Tasks is a single notebook with mostly independent sub-questions, and the case study's prep logic is only ever used by the case study notebook itself, so nothing is genuinely shared between the two.

## Structure

```
data/
  raw/                    # original CSVs from the group's tubCloud/DB export — gitignored, not submitted
  processed/
    case_study/           # the final merged dataset — committed, required for submission, feeds app/
    general_tasks/        # optional derived data (e.g. the "Logistics delay" dataset), local scratch
notebooks/
  general_tasks/           # one self-contained notebook, no separate EDA step — inline per sub-task
  case_study/              # EDA is the notebook's own early section, before any cleaning/merging
exports/       # HTML exports of the final, fully-run notebooks — required for submission
app/           # Streamlit app, must run standalone from this folder with relative paths only
  assets/
    logo/      # own logo or Department of Quality Science logo
    fonts/     # Source Sans Pro
  pages/
```

## Data

## Conventions

- Relative paths only, everywhere (notebooks and app must run unmodified on another machine).
- Raw data lives in `data/raw/` and is **not** committed 
- Only `data/processed/case_study/` (the final dataset) is committed; `data/processed/general_tasks/` is local scratch.
- Light blue as the app's main colour, Source Sans Pro font, department/own logo.
- The app only reads `data/processed/case_study/`'s output file — it never imports notebook code. Anything the app needs to display must already be a column in that final dataset; if it's missing, extend the notebook's Step 2 output, don't recompute it in the app.

## Submission deadline

1 September 2026, 23:59.
