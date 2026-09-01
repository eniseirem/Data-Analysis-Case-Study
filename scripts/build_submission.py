"""Assemble the flat SoSe26_Case_Study_Group_19 submission package from the repo.

Run from the repo root:
    /opt/anaconda3/envs/QW/bin/python scripts/build_submission.py

Output goes to submission/SoSe26_Case_Study_Group_19/ (gitignored) and is not
part of the git repo layout - the submission ZIP structure the course requires
is flat and differs from how this repo is organized for development.
"""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUP = "19"
OUT = ROOT / "submission" / f"SoSe26_Case_Study_Group_{GROUP}"
NBCONVERT = "/opt/anaconda3/envs/QW/bin/jupyter"


def reset_out():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def copy_with_logo_path_fix(src: Path, dest: Path):
    text = src.read_text()
    dest.write_text(text.replace('"assets/logo/logo.svg"', '"www/logo.svg"'))


def build_app():
    app_src = ROOT / "app"
    copy_with_logo_path_fix(
        app_src / f"SoSe26_Case_Study_App_Group_{GROUP}.py", OUT / f"SoSe26_Case_Study_App_Group_{GROUP}.py"
    )

    (OUT / "pages").mkdir()
    for page in (app_src / "pages").glob("*.py"):
        copy_with_logo_path_fix(page, OUT / "pages" / page.name)

    copy_with_logo_path_fix(app_src / "theme.py", OUT / "theme.py")

    data_py = (app_src / "data.py").read_text()
    old = (
        'DATA_PATH = Path(__file__).parent / ".." / "data" / "processed" '
        '/ "case_study" / "SoSe26_Case_Study_finalData_Group_19.csv"'
    )
    new = f'DATA_PATH = Path(__file__).parent / "SoSe26_Case_Study_finalData_Group_{GROUP}.csv"'
    assert old in data_py, "data.py DATA_PATH line not found as expected"
    (OUT / "data.py").write_text(data_py.replace(old, new))

    shutil.copytree(app_src / ".streamlit", OUT / ".streamlit")


def patch_and_export_notebook(src_ipynb: Path, dest_stem: str, replacements: list[tuple[str, str]]):
    nb = json.loads(src_ipynb.read_text())
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell.get("source", []))
        changed = False
        for old, new in replacements:
            if old in src:
                src = src.replace(old, new)
                changed = True
        if changed:
            cell["source"] = src.splitlines(keepends=True)

    dest_ipynb = OUT / f"{dest_stem}.ipynb"
    dest_ipynb.write_text(json.dumps(nb, indent=1))

    subprocess.run(
        [NBCONVERT, "nbconvert", "--to", "html", "--embed-images", str(dest_ipynb)],
        check=True,
    )


def build_case_study():
    patch_and_export_notebook(
        ROOT / "notebooks" / "case_study" / f"SoSe26_Case_Study_Group_{GROUP}.ipynb",
        f"SoSe26_Case_Study_Group_{GROUP}",
        [
            ('RAW_DIR = Path("../../data/raw/IDA SoSe26 - Data")', 'RAW_DIR = Path("data/raw/IDA SoSe26 - Data")'),
            ('output_dir = Path("../../data/processed/case_study")', 'output_dir = Path(".")'),
        ],
    )
    shutil.copy(
        ROOT / "data" / "processed" / "case_study" / f"SoSe26_Case_Study_finalData_Group_{GROUP}.csv",
        OUT / f"SoSe26_Case_Study_finalData_Group_{GROUP}.csv",
    )


def build_general_tasks():
    patch_and_export_notebook(
        ROOT / "notebooks" / "general_tasks" / "General_Task_AF.ipynb",
        f"SoSe26_General_Tasks_Group_{GROUP}",
        [('DATA_DIR = Path("../../data")', 'DATA_DIR = Path("data")')],
    )


def build_additional_files():
    dest = OUT / "additional_files"
    dest.mkdir()
    shots = ROOT / "notebooks" / "case_study" / "screenshots"
    for f in sorted(shots.iterdir()):
        shutil.copy(f, dest / f.name)


def build_data_placeholder():
    (OUT / "data" / "raw").mkdir(parents=True)
    (OUT / "data" / "raw" / "README.txt").write_text(
        "Place the original 'IDA SoSe26 - Data' folder here before re-running "
        "the notebooks: data/raw/IDA SoSe26 - Data/...\n"
    )


def build_www():
    www = OUT / "www"
    www.mkdir()
    shutil.copy(ROOT / "app" / "assets" / "logo" / "logo.svg", www / "logo.svg")


def main():
    reset_out()
    build_app()
    build_case_study()
    build_general_tasks()
    build_additional_files()
    build_data_placeholder()
    build_www()
    print(f"Built {OUT}")


if __name__ == "__main__":
    main()
