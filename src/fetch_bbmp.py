"""
Download BBMP (Bengaluru) ward-tagged work orders from OpenCity's CKAN portal.

Why work orders and not budget: BBMP publishes NO ward-wise capital budget. What it does
publish - via its own Works Bill Public View / IFMS, mirrored by the Oorvani Foundation on
data.opencity.in - is far better for this design: ward-tagged, project-level, dated ACTUAL
PAYMENTS with contractor names, ~5,000-7,000 orders a year, across 13 years.

NOTE: opendata.bbmp.gov.in does not resolve. data.opencity.in is the real route.
"""
import io
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://data.opencity.in/api/3/action/package_show"
RAW = Path(__file__).resolve().parent.parent / "data/raw/bbmp"
RAW.mkdir(parents=True, exist_ok=True)

DATASETS = [
    "bbmp-work-orders-by-ward-2013-2022",     # 198 resources, one per ward
    "bbmp-work-orders-2022-23",
    "bbmp-work-orders-2023-24",
    "bbmp-work-orders-and-payments-2024-25",
    "bbmp-work-orders-and-payments-2025-26",
    "bbmp-work-orders-categorised-2018-2023",  # cross-check only (27% untagged)
]


def resources(pkg):
    r = requests.get(API, params={"id": pkg}, timeout=(15, 120))
    r.raise_for_status()
    return r.json()["result"]["resources"]


def grab(url, dest, tries=3):
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for a in range(tries):
        try:
            r = requests.get(url, timeout=(15, 180))
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except Exception as e:
            if a == tries - 1:
                print(f"      fail {dest.name}: {type(e).__name__}")
            time.sleep(2)
    return False


if __name__ == "__main__":
    manifest = []
    for pkg in DATASETS:
        try:
            res = resources(pkg)
        except Exception as e:
            print(f"  {pkg}: FAILED {e}")
            continue
        d = RAW / pkg
        d.mkdir(exist_ok=True)
        got = 0
        for i, rs in enumerate(res):
            url = rs.get("url") or ""
            fmt = (rs.get("format") or "").lower()
            if fmt not in ("csv", "xlsx", "xls") or not url:
                continue
            name = (rs.get("name") or f"res{i}").replace("/", "-")[:80]
            ext = ".csv" if fmt == "csv" else ".xlsx"
            dest = d / f"{i:03d}_{name}{ext}"
            if grab(url, dest):
                got += 1
                manifest.append({"package": pkg, "idx": i, "name": rs.get("name"),
                                 "format": fmt, "url": url, "file": str(dest)})
        print(f"  {pkg:42s} {got:3d}/{len(res)} files")

    pd.DataFrame(manifest).to_csv(RAW / "manifest.csv", index=False)
    total = sum(f.stat().st_size for f in RAW.rglob("*") if f.is_file())
    print(f"\n  {len(manifest)} files, {total/1e6:.1f} MB -> {RAW}")
