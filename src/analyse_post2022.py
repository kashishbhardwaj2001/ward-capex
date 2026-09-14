"""
Does the finding still hold after the study window closes? (out-of-sample check)

THE OBJECTION THIS ANSWERS. The panel ends at FY2022 because Bengaluru redrew its ward map
after that, and in 2025 split into five corporations. A reader in 2026 is entitled to ask
whether a result estimated on FY2013-2022 is a historical curiosity.

It can be partly tested. BBMP publishes post-2022 work orders as separate files per ward
regime, and the 198-REGIME file is still on the same delimitation the study uses - so those
rows need no crosswalk and are directly comparable. That is Rs 4,616 Cr across 156 wards in
FY2023, held out of the estimation entirely.

WHAT THIS IS AND IS NOT. It is a one-year cross-section, not a panel: no year fixed effects,
much less power, and 42 of 198 wards have no FY2023 orders on this base. The average order
is also far larger than in the study window (Rs 2.1 Cr vs Rs 0.34 Cr), because by FY2023 the
198-regime file is carrying mostly large legacy projects while routine work moved to the new
delimitation. So a null here would be weak evidence, and the point estimate matters more
than the p-value.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
FIN = ROOT / "data/final"
OUT = ROOT / "output"

CTRL = "log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"

if __name__ == "__main__":
    base = pd.read_parquet(FIN / "bengaluru_budget_panel.parquet")
    base["ward"] = pd.to_numeric(base["unit"], errors="coerce")
    ward = base.drop_duplicates("ward")[
        ["ward", "z_hazard", "log_pop", "z_log_density", "z_dist_centre_km",
         "elev_m", "slope"]].copy()
    for c in ["elev_m", "slope"]:
        ward[f"z_{c}"] = (ward[c] - ward[c].mean()) / ward[c].std()

    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    post = wo[(wo.fy >= 2023) & (wo.ward.between(1, 198))].copy()
    post["regime"] = post["regime"].fillna("198")
    out = post[post.regime == "198"]          # same map as the study; no crosswalk needed

    tot = out.groupby("ward").amount.sum().rename("total_23")
    drn = out[out.is_medium].groupby("ward").amount.sum().rename("drain_23")
    d = ward.merge(tot, on="ward", how="inner").merge(drn, on="ward", how="left")
    d["drain_23"] = d["drain_23"].fillna(0)
    d["log_total"] = np.log(d.total_23.clip(lower=1))
    d["share"] = d.drain_23 / d.total_23 * 100
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["log_total", "z_hazard"])

    print(f"  HELD-OUT SAMPLE: FY2023, {len(d)} wards, "
          f"Rs {d.total_23.sum()/1e7:,.0f} Cr\n")

    print("  === does flood hazard still predict a smaller ward budget? ===")
    rows = []
    for lab, f in [("raw (no controls)", "log_total ~ z_hazard"),
                   ("with full controls", f"log_total ~ z_hazard + {CTRL}")]:
        m = smf.ols(f, data=d).fit(cov_type="HC1")
        b, se, p = m.params["z_hazard"], m.bse["z_hazard"], m.pvalues["z_hazard"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {lab:22s} {(np.exp(b)-1)*100:+7.1f}%  (se {se:.3f})  p={p:.4f}{st}")
        rows.append({"window": "FY2023 held out", "spec": lab, "beta": b, "se": se,
                     "p": p, "pct": (np.exp(b) - 1) * 100, "n": int(m.nobs)})

    print("\n  === and the drainage share, as in the study window? ===")
    m = smf.ols(f"share ~ z_hazard + log_total + {CTRL}", data=d).fit(cov_type="HC1")
    b, p = m.params["z_hazard"], m.pvalues["z_hazard"]
    print(f"    share of budget to drainage  {b:+.2f} pp  p={p:.4f}")

    print("\n  === side by side with the estimation window ===")
    print(f"    {'window':26s} {'hazard -> total budget':>24s}")
    print(f"    {'FY2013-2022 (estimated on)':26s} {'-12.8%  p<0.0001':>24s}")
    print(f"    {'FY2023 (held out)':26s} "
          f"{f'{rows[1][chr(34)+chr(34)] if False else rows[1][chr(112)+chr(99)+chr(116)]:+.1f}%  p={rows[1][chr(112)]:.4f}':>24s}")

    old_map = rows[1]          # FY2023 on the 198 map, with full controls

    # ---------------------------------------------------------------- the NEW map
    # A second, fully independent test. The 243-regime rows are on the post-2022
    # delimitation, for which a boundary file exists - so hazard can be measured natively on
    # the new wards and the analysis re-run there, with no crosswalk anywhere in it. It is
    # not a re-weighting of the old result; it is the same question asked of different
    # polygons and different money.
    #
    # The cost: the 243 boundary file carries no census attributes, so there is no
    # population, density or SC/ST control - only terrain and geography. The equity part of
    # the study cannot be reproduced here at all.
    import geopandas as gpd
    h = pd.read_parquet(INT / "ward_hazard.parquet")
    t = pd.read_parquet(INT / "ward_terrain.parquet")
    n = (h[h.city == "bengaluru_243"]
         .merge(t[t.city == "bengaluru_243"], on=["city", "unit_id"], suffixes=("", "_t")))
    g243 = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_243.geojson").reset_index(drop=True)
    g243["unit_id"] = range(len(g243))
    g243["ward"] = pd.to_numeric(g243["KGISWardNo"], errors="coerce")
    cen = g243.to_crs(32643).geometry.centroid
    mid = cen.union_all().centroid
    g243["dist_km"] = cen.distance(mid) / 1000
    n = n.merge(g243[["unit_id", "ward", "dist_km"]], on="unit_id", how="left")

    new = post[post.regime == "243"]
    tot2 = new.groupby("ward").amount.sum().rename("total")
    d2 = n.merge(tot2, on="ward", how="inner")
    for c in ["hand_lt5m_share", "elev_m", "slope", "dist_km", "area_km2"]:
        d2[f"z_{c}"] = (d2[c] - d2[c].mean()) / d2[c].std()
    d2["log_total"] = np.log(d2.total.clip(lower=1))
    d2 = d2.replace([np.inf, -np.inf], np.nan).dropna(subset=["log_total", "z_hand_lt5m_share"])

    print(f"\n  === SECOND TEST: the NEW 243-ward map, measured natively ===")
    print(f"    {len(d2)} wards, Rs {d2.total.sum()/1e7:,.0f} Cr, no crosswalk used")
    for lab, f in [("raw (no controls)", "log_total ~ z_hand_lt5m_share"),
                   ("+ terrain & geography",
                    "log_total ~ z_hand_lt5m_share + z_elev_m + z_slope + z_dist_km + z_area_km2")]:
        m2 = smf.ols(f, data=d2).fit(cov_type="HC1")
        b, se, pv = (m2.params["z_hand_lt5m_share"], m2.bse["z_hand_lt5m_share"],
                     m2.pvalues["z_hand_lt5m_share"])
        st = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
        print(f"    {lab:24s} {(np.exp(b)-1)*100:+7.1f}%  (se {se:.3f})  p={pv:.4f}{st}")
        rows.append({"window": "FY2023+ on the 243 map", "spec": lab, "beta": b, "se": se,
                     "p": pv, "pct": (np.exp(b) - 1) * 100, "n": int(m2.nobs)})
    print("    (no population or equity controls exist for this boundary file)")

    # ---------------------------------------------------------------- verdict
    new_map = rows[-1]
    agree = (old_map["pct"] < 0) == (new_map["pct"] < 0)
    sig = [r for r in (old_map, new_map) if r["p"] < .10]
    print("\n  === READING ===")
    print(f"    old 198-ward map, FY2023   {old_map['pct']:+6.1f}%  p={old_map['p']:.3f}")
    print(f"    new 243-ward map, FY2023+  {new_map['pct']:+6.1f}%  p={new_map['p']:.3f}")
    print("")
    if not agree and not sig:
        print("    THE TWO TESTS DISAGREE IN SIGN, and neither is close to significant.")
        print("    The honest conclusion is that post-2022 data can neither confirm nor")
        print("    refute the FY2013-2022 finding. It is not evidence the result has gone")
        print("    away, and it is not evidence it persists.")
        print("")
        print("    That is a property of the data, not bad luck. Post-2022 spending is split")
        print("    across three ward maps at once; the 225 regime has no published boundary")
        print("    at all; FY2024-26 carry a fraction of the money of a normal year because")
        print("    municipal payments lag by years and those books are still being written;")
        print("    and neither post-2022 test has a population control, because the new")
        print("    boundary file ships without census attributes.")
        print("")
        print("    The right response is to re-run this once BBMP publishes a full panel on")
        print("    a single stable map - which is one command - rather than to read either")
        print("    of these two numbers as an answer.")
    elif agree and sig:
        print("    Both tests point the same way and at least one is significant. That is")
        print("    real out-of-sample support for the FY2013-2022 finding.")
    elif agree:
        print("    Both tests point the same way; neither is significant. Weak confirmatory")
        print("    evidence - the point estimates agree, the power does not exist to prove")
        print("    it with one year on a fragmented ward map.")
    else:
        print("    The tests disagree AND one is significant. Read the significant one, and")
        print("    treat the post-2022 period as genuinely unresolved.")

    pd.DataFrame(rows).to_csv(OUT / "tables/post2022_holdout.csv", index=False)
    print(f"\n  -> {OUT/'tables/post2022_holdout.csv'}")
