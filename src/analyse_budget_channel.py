"""
Where the misalignment actually is: the TOTAL budget, not the drainage line.

The pooled model first appeared to show stormwater spending FALLING with flood hazard
(-10.7% per SD, p=0.004). Decomposing it shows why, and the decomposition is the finding:

    hazard -> total ward capital budget      : -14.0% per SD  (p < 0.0001)
    hazard -> stormwater | total controlled  :  +3.6% per SD  (p = 0.248, null)

So drainage is NOT being under-prioritised inside ward budgets. Flood-prone wards are
simply given SMALLER BUDGETS, and their drainage spending falls with everything else.
The misallocation operates one level up from where anyone has been looking.

This matters for policy: a climate-budget-tagging exercise that inspects the drainage line
would find nothing wrong in Bengaluru. The problem is only visible in the denominator.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "output"


def bengaluru_panel():
    m = pd.read_parquet(ROOT / "data/final/multicity_panel.parquet")
    m = m[m.city == "bengaluru"].copy()
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    tot = (w.groupby(["ward", "fy"]).amount.sum().rename("total_spend").reset_index())
    tot["unit"] = tot.ward.astype(int).astype(str)
    d = m.merge(tot[["unit", "fy", "total_spend"]], on=["unit", "fy"], how="left")

    ward = pd.read_parquet(ROOT / "data/final/bengaluru_final.parquet")
    ward["unit"] = ward.ward.astype(int).astype(str)
    cols = ["unit", "log_pop", "z_log_density", "z_dist_centre_km", "z_sc_st_share",
            "blr_ward_name", "sc_st_share", "pop"]
    d = d.merge(ward[[c for c in cols if c in ward.columns]], on="unit", how="left")

    d["log_total"] = np.log(d.total_spend.clip(lower=1))
    d["log_area"] = np.log(d.area_km2.clip(lower=.01))
    d["log_storm"] = np.log(d.storm_spend.clip(lower=1))
    d["storm_share"] = d.storm_spend / d.total_spend * 100
    return d.dropna(subset=["log_total", "z_hazard"])


CTRL = "log_area + log_pop + z_log_density + z_dist_centre_km"

if __name__ == "__main__":
    d = bengaluru_panel()
    cl = {"cov_type": "cluster", "cov_kwds": {"groups": d["unit"]}}
    print(f"  Bengaluru ward-year panel: {len(d):,} obs, {d.unit.nunique()} wards\n")

    print("  === THE DECOMPOSITION ===")
    steps = [
        ("(1) hazard -> TOTAL ward budget", f"log_total ~ z_hazard + {CTRL} + C(fy)"),
        ("(2) hazard -> stormwater spend",  f"log_storm ~ z_hazard + {CTRL} + C(fy)"),
        ("(3) hazard -> stormwater | budget",
         f"log_storm ~ z_hazard + log_total + {CTRL} + C(fy)"),
        ("(4) hazard -> stormwater SHARE",  f"storm_share ~ z_hazard + {CTRL} + C(fy)"),
    ]
    rows = []
    for lab, f in steps:
        r = smf.ols(f, data=d).fit(**cl)
        b, se, p = r.params["z_hazard"], r.bse["z_hazard"], r.pvalues["z_hazard"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        pct = f"{(np.exp(b)-1)*100:+6.1f}%" if lab.endswith(("budget", "spend")) or "|" in lab else f"{b:+6.2f}pp"
        print(f"    {lab:36s} beta {b:+7.3f} (se {se:5.3f}) p={p:.4f}{st:3s} {pct}")
        rows.append({"step": lab, "beta": b, "se": se, "p": p})

    print("\n  >>> The misalignment is in the TOTAL BUDGET, not the drainage line.")

    print("\n  === IS IT EQUITY? do high-hazard wards differ systematically? ===")
    for y, lab in [("z_hazard", "hazard")]:
        for x, xl in [("sc_st_share", "SC/ST population share"),
                      ("log_pop", "log population"),
                      ("z_dist_centre_km", "distance from centre")]:
            if x in d:
                c = d.groupby("unit")[[y, x]].first().corr().iloc[0, 1]
                print(f"    corr({lab}, {xl:24s}) = {c:+.3f}")

    print("\n  === WHO LOSES MOST: high hazard + smallest budget ===")
    w = (d.groupby(["unit", "blr_ward_name"])
           .agg(hazard=("z_hazard", "first"), total=("total_spend", "sum"),
                storm=("storm_spend", "sum")).reset_index())
    w["log_total"] = np.log(w.total.clip(lower=1))
    r = smf.ols("log_total ~ hazard", data=w).fit()
    w["budget_gap"] = r.resid
    hi = w[w.hazard > w.hazard.quantile(.7)].nsmallest(8, "budget_gap")
    print(f"    {'ward':26s} {'hazard(z)':>9s} {'total Cr':>9s} {'gap':>7s}")
    for _, x in hi.iterrows():
        print(f"    {str(x.blr_ward_name)[:26]:26s} {x.hazard:+9.2f} "
              f"{x.total/1e7:9.1f} {x.budget_gap:+7.2f}")

    pd.DataFrame(rows).to_csv(OUT / "tables/budget_channel.csv", index=False)
    d.to_parquet(ROOT / "data/final/bengaluru_budget_panel.parquet", index=False)
    print(f"\n  -> {OUT/'tables/budget_channel.csv'}")
