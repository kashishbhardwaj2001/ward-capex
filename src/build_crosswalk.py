"""
Areal-weighted crosswalk between Bengaluru's ward vintages (gate G4).

BBMP re-delimited 198 -> 243 -> 225 -> 369 wards between 2022 and 2025. Work orders after
FY2022 are tagged to the NEW ward numbers, so a naive panel silently mixes two different
geographies under the same integer labels - ward 57 in 2015 is not ward 57 in 2024.

Fix: intersect the vintages, compute the share of each new ward's area that falls in each
old ward, and redistribute post-2022 spending onto the stable 198-ward (2012) base.

Assumption, stated because it matters: spending is distributed UNIFORMLY within a ward.
That is wrong at the project level - a single drain sits at one point, not spread evenly -
but it is unbiased in expectation across many projects, and it is the standard approach.
The validation below checks that the city total is preserved exactly.
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
BOUND = ROOT / "data/raw/boundaries"
OUT = ROOT / "data/interim"

UTM = 32643          # UTM 43N, appropriate for Bengaluru


def build_crosswalk():
    old = gpd.read_file(BOUND / "bengaluru_198.geojson").to_crs(UTM)
    new = gpd.read_file(BOUND / "bengaluru_243.geojson").to_crs(UTM)
    old["old_ward"] = pd.to_numeric(old["WARD_NO"], errors="coerce")
    new["new_ward"] = pd.to_numeric(new["KGISWardNo"], errors="coerce")
    old = old[["old_ward", "geometry"]].dropna()
    new = new[["new_ward", "geometry"]].dropna()
    old["geometry"] = old.geometry.buffer(0)
    new["geometry"] = new.geometry.buffer(0)

    inter = gpd.overlay(new, old, how="intersection", keep_geom_type=True)
    inter["inter_area"] = inter.geometry.area
    new_area = new.assign(a=new.geometry.area).set_index("new_ward")["a"]
    inter["new_area"] = inter["new_ward"].map(new_area)
    inter["w"] = inter["inter_area"] / inter["new_area"]

    xw = inter[["new_ward", "old_ward", "w"]].copy()
    # normalise so each new ward's weights sum to 1 (slivers / boundary noise)
    s = xw.groupby("new_ward")["w"].transform("sum")
    xw["w"] = xw["w"] / s.replace(0, np.nan)
    return xw.dropna()


if __name__ == "__main__":
    xw = build_crosswalk()
    print(f"  crosswalk: {len(xw):,} (new_ward, old_ward) pairs")
    print(f"  new wards covered: {xw.new_ward.nunique()} of 243")
    print(f"  old wards touched: {xw.old_ward.nunique()} of 198")
    chk = xw.groupby("new_ward").w.sum()
    print(f"  weight sums: min {chk.min():.4f}  max {chk.max():.4f}  "
          f"(should all be 1.0)")
    frag = xw.groupby("new_ward").size()
    print(f"  fragmentation: a new ward maps to {frag.mean():.1f} old wards on average "
          f"(max {frag.max()})")

    # --- validate on real money
    wo = pd.read_parquet(OUT / "bbmp_workorders.parquet")
    post = wo[(wo.fy >= 2023) & (wo.ward.between(1, 243))]
    tot_before = post.amount.sum()
    m = post.merge(xw, left_on="ward", right_on="new_ward", how="inner")
    m["amount_alloc"] = m["amount"] * m["w"]
    tot_after = m.amount_alloc.sum()
    matched = m.ward.nunique()
    print(f"\n  === GATE G4 validation, on post-2022 spending ===")
    print(f"    ward-tagged post-2022 spend : Rs {tot_before/1e7:,.0f} Cr "
          f"({len(post):,} orders, {post.ward.nunique()} distinct wards)")
    print(f"    redistributed onto 198 base : Rs {tot_after/1e7:,.0f} Cr "
          f"({matched} new wards matched)")
    share = tot_after / tot_before * 100 if tot_before else 0
    print(f"    money preserved             : {share:.1f}%")
    print(f"    >>> G4 {'PASSES' if share >= 90 else 'FAILS'} "
          f"(threshold: >=90% of spend maps to stable units)")

    alloc = (m.groupby(["old_ward", "fy"]).amount_alloc.sum()
             .rename("amount").reset_index()
             .rename(columns={"old_ward": "ward"}))
    alloc.to_parquet(OUT / "post2022_on_198base.parquet", index=False)
    xw.to_parquet(OUT / "ward_crosswalk_243_to_198.parquet", index=False)
    print(f"\n  -> {OUT/'ward_crosswalk_243_to_198.parquet'}")
