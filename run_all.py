#!/usr/bin/env python3
"""
Reproduce the whole study, end to end.

    python run_all.py                 # everything, in order
    python run_all.py --list          # show the stages and stop
    python run_all.py --from build_panel
    python run_all.py --only analyse_budget_channel analyse_falsification
    python run_all.py --skip-slow     # skip the three network-heavy download stages

The stage order below is a real dependency order, not a filename sort. Three stages are
slow because they download from the open internet rather than because they compute much:

    build_terrain       ~1.5 GB of Copernicus DEM tiles      (cached in data/raw/dem)
    build_chirps        3,653 daily CHIRPS grids, ~2 MB each (cached in data/raw/chirps)
    build_drain_network 22 Overpass queries, rate-limited    (cached in data/raw/osm_drains)

All three cache to disk and are cheap on a second run. A cold, complete run takes roughly
an hour on a home connection, almost all of it downloading.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT.parent / ".venv/bin/python")
if not Path(PY).exists():
    PY = sys.executable

SLOW = {"build_terrain", "build_chirps", "build_drain_network"}

STAGES = [
    # -- acquisition -------------------------------------------------------------
    ("fetch_bbmp",               "BBMP work orders from the OpenCity CKAN API"),
    ("fetch_boundaries",         "22 ward boundary layers"),
    # -- construction ------------------------------------------------------------
    ("build_panel",              "parse 82k work orders; classify drainage; 3 schemas"),
    ("build_hazard",             "CCKP + GFDRR zonal stats for 2,157 units"),
    ("build_terrain",            "HAND / TWI / slope from Copernicus DEM 30 m"),
    ("build_chirps",             "time-varying extreme-rain days, CHIRPS daily 0.05 deg"),
    ("build_drain_network",      "existing drainage stock from OpenStreetMap"),
    ("build_crosswalk",          "243-ward -> 198-ward areal crosswalk"),
    ("build_panel_v2",           "deflate, per-capita / per-built-up outcomes"),
    ("build_multicity",          "pool six cities onto a common hazard definition"),
    ("build_wards_gpkg",         "ward name join + canonical wards.gpkg"),
    # -- validation (run BEFORE the analysis, so a failure stops the study) -------
    ("verify_benchmarks",        "parser vs published row/rupee benchmarks"),
    ("verify_boundary_vintages", "198 / 243 / 369 vintages; coordinate integrity"),
    ("validate_hazard",          "GATE: hazard vs 395 observed flood points"),
    ("validate_classifier",      "GATE: 300 hand-adjudicated work orders"),
    # -- analysis ----------------------------------------------------------------
    ("analyse_panel",            "descriptives"),
    ("analyse_bengaluru",        "headline cross-section"),
    ("analyse_controlled",       "controlled specification"),
    ("analyse_budget_channel",   "THE DECOMPOSITION: total vs line vs share"),
    ("analyse_falsification",    "outcome-side falsification + coefficient contrasts"),
    ("analyse_wardfe",           "ward FE arm on time-varying CHIRPS rainfall"),
    ("analyse_stock_control",    "existing drainage stock as a rival explanation"),
    ("analyse_political",        "councillor party controls"),
    ("analyse_robustness",       "8 arms, Conley spatial SEs"),
    ("analyse_multicity",        "pooled and per-city"),
    ("analyse_selection",        "R11: do publishing cities differ from the rest?"),
    ("make_figures",             "F1-F7"),
]


def run(name, desc):
    p = ROOT / "src" / f"{name}.py"
    if not p.exists():
        print(f"  SKIP {name} (missing)")
        return True
    print(f"\n{'='*78}\n  {name}  --  {desc}\n{'='*78}", flush=True)
    t0 = time.time()
    r = subprocess.run([PY, str(p)], cwd=ROOT)
    dt = time.time() - t0
    if r.returncode != 0:
        print(f"\n  !! {name} FAILED after {dt:.0f}s (exit {r.returncode})")
        return False
    print(f"  -- {name} ok ({dt:.0f}s)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--skip-slow", action="store_true")
    ap.add_argument("--keep-going", action="store_true",
                    help="continue past a failing stage instead of stopping")
    a = ap.parse_args()

    if a.list:
        for n, d in STAGES:
            print(f"  {'[slow] ' if n in SLOW else '       '}{n:26s} {d}")
        sys.exit(0)

    todo = list(STAGES)
    if a.only:
        todo = [s for s in todo if s[0] in set(a.only)]
    elif a.start:
        names = [n for n, _ in todo]
        if a.start not in names:
            sys.exit(f"unknown stage: {a.start}")
        todo = todo[names.index(a.start):]
    if a.skip_slow:
        todo = [s for s in todo if s[0] not in SLOW]

    print(f"  running {len(todo)} stage(s) with {PY}")
    failed = []
    for n, d in todo:
        if not run(n, d):
            failed.append(n)
            if not a.keep_going:
                sys.exit(f"\n  stopped at {n}. Re-run with --from {n} after fixing, "
                         f"or --keep-going to push past it.")
    print(f"\n{'='*78}")
    if failed:
        print(f"  COMPLETE WITH {len(failed)} FAILURE(S): {', '.join(failed)}")
        sys.exit(1)
    print(f"  all {len(todo)} stages completed")
