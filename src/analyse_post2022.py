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

    same = rows[1]["pct"] < 0
    print(f"\n  === READING ===")
    if same and rows[1]["p"] < .10:
        print("    The gap is still there, a year after the estimation window closes, on")
        print("    data the model never saw. The finding is not an artefact of the years")
        print("    it was fitted to.")
    elif same:
        print("    Same direction, not significant at 10%. With one year, 156 wards and no")
        print("    year fixed effects that is expected - the point estimate is the evidence")
        print("    here, and it points the same way.")
    else:
        print("    The sign REVERSES out of sample. That is a real warning and is reported")
        print("    as such: the FY2013-2022 result should not be projected forward without")
        print("    re-estimating once BBMP publishes a full panel on a stable map.")
    print("\n    Either way this is a weak test by construction - see the module docstring.")
    pd.DataFrame(rows).to_csv(OUT / "tables/post2022_holdout.csv", index=False)
    print(f"\n  -> {OUT/'tables/post2022_holdout.csv'}")
