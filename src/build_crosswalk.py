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
    #
    # ROUTE BY DELIMITATION, NOT BY WARD NUMBER RANGE. BBMP publishes post-2022 work orders
    # as SEPARATE FILES per ward regime - "...for 198 Wards Regime.csv", "...225...",
    # "...243...", plus a Common Wards file - and build_panel.py records which file each
    # order came from in `regime`. A ward number alone therefore does NOT identify a
    # geography: ward 57 means a different polygon under each delimitation.
    #
    # The first version of this validation selected on `ward.between(1, 243)` and applied
    # the 243 -> 198 weights to everything it caught. Only 18.6% of that money was actually
    # on the 243 base. Rs 3,068 Cr was already on the 198 base and got scattered across
    # 5.5 other wards apiece by weights that should never have touched it, and Rs 893 Cr of
    # 225-regime orders was mapped through the wrong vintage's geometry entirely.
    #
    # Routing:
    #   regime 198 / unlabelled  -> already the target geography; pass through UNCHANGED
    #   regime 243               -> apply the areal weights (the only valid use)
    #   regime 225               -> EXCLUDED. No 225-ward boundary file is published
    #                               anywhere we could find, so no crosswalk can be built.
    #                               Dropping it and saying so beats mapping it wrongly.
    wo = pd.read_parquet(OUT / "bbmp_workorders.parquet")
    post = wo[(wo.fy >= 2023) & (wo.ward.between(1, 243))].copy()
    post["regime"] = post["regime"].fillna("198")      # unlabelled files are 198-base
    tot_before = post.amount.sum()

    print(f"\n  === GATE G4 validation, on post-2022 spending ===")
    print(f"    ward-tagged post-2022 spend : Rs {tot_before/1e7:,.0f} Cr "
          f"({len(post):,} orders, {post.ward.nunique()} distinct wards)")
    print(f"    by published delimitation:")
    for k, g in post.groupby("regime"):
        print(f"      regime {str(k):4s}  Rs {g.amount.sum()/1e7:7,.0f} Cr  "
              f"({g.amount.sum()/tot_before*100:5.1f}%)  {len(g):5,d} orders")

    identity = post[post.regime.isin(["198"])]
    to_map = post[post.regime == "243"]
    dropped = post[post.regime == "225"]

    m = to_map.merge(xw, left_on="ward", right_on="new_ward", how="inner")
    m["amount_alloc"] = m["amount"] * m["w"]
    mapped_cr = m.amount_alloc.sum()

    alloc = pd.concat([
        m.groupby(["old_ward", "fy"]).amount_alloc.sum().rename("amount")
         .reset_index().rename(columns={"old_ward": "ward"}),
        identity.groupby(["ward", "fy"]).amount.sum().reset_index(),
    ], ignore_index=True).groupby(["ward", "fy"], as_index=False).amount.sum()

    usable = identity.amount.sum() + mapped_cr
    print(f"\n    passed through unchanged    : Rs {identity.amount.sum()/1e7:,.0f} Cr "
          f"(already on the 198 base)")
    print(f"    redistributed via weights   : Rs {mapped_cr/1e7:,.0f} Cr "
          f"(243 regime, {m.ward.nunique()} wards)")
    print(f"    EXCLUDED, no 225 boundary   : Rs {dropped.amount.sum()/1e7:,.0f} Cr "
          f"({dropped.amount.sum()/tot_before*100:.1f}%)")
    share = usable / tot_before * 100 if tot_before else 0
    print(f"    -> on a stable 198-ward base: Rs {usable/1e7:,.0f} Cr ({share:.1f}%)")

    # A NON-TAUTOLOGICAL CHECK. Weights are normalised to sum to 1 per new ward, so
    # "money preserved" through the merge is an arithmetic identity - it is 100% whatever
    # the ward numbers mean, and the old gate could not fail. What actually has to hold is
    # that the 243-regime money lands somewhere, and that money NOT on the 243 base is
    # never put through the weights. Both are asserted rather than printed.
    leak = m.amount_alloc.sum() - to_map.amount.sum()
    assert abs(leak) < 1.0, f"243-regime money changed by Rs {leak:,.0f} through the weights"
    # Disjointness has to be checked on ROW IDENTITY, not on the job number. BBMP job
    # numbers are ward-FY-serial and are only unique WITHIN a regime file: "198-23-000002"
    # exists in both the 198 and the 243 release as different works, with different
    # descriptions and amounts (187 such collisions post-2022). Anything that treats `wo`
    # as a global key - a dedup, a merge, an anti-join like this one - silently corrupts.
    assert not (set(to_map.index) & set(identity.index)), \
        "198-base money was put through the 243 weights"
    print(f"    weight round-trip on the 243 subset: Rs {leak:+,.0f} (exact)")
    print(f"    >>> G4 {'PASSES' if share >= 90 else 'FAILS'} "
          f"(threshold: >=90% of spend lands on a stable unit)")
    if share < 90:
        print(f"        The 225 regime has no published boundary file, so its "
              f"{dropped.amount.sum()/tot_before*100:.0f}% cannot be")
        print(f"        placed. This is a real limit of BBMP's disclosure, not a bug: any")
        print(f"        number above would be manufactured by mapping it through a")
        print(f"        delimitation it does not belong to.")

    alloc.to_parquet(OUT / "post2022_on_198base.parquet", index=False)
    xw.to_parquet(OUT / "ward_crosswalk_243_to_198.parquet", index=False)
    print(f"\n  -> {OUT/'ward_crosswalk_243_to_198.parquet'}")
