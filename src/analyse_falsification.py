"""
A VALID falsification test - and why the first one was not.

WHAT WENT WRONG FIRST TIME. The original design was hazard-side: drainage should respond
to flood hazard, parks to heat hazard, and each should ignore the other's hazard. It
appeared to fail - drainage tracked "heat" more strongly than flood. The test was broken,
not the finding.

  CCKP hd35 across Bengaluru's 198 wards: mean 23.0, sd 0.58, CV 2.5%, and only SIX
  DISTINCT VALUES. The 0.25 deg grid covers the whole city in about six cells, so the
  variable is not heat at ward scale - it is a coarse spatial dummy for which grid cell a
  ward happens to sit in. Z-scoring it turns a step function into apparent signal, and it
  will absorb ANY spatial gradient in spending. It cannot falsify anything.

  This is the same scale problem the wider project documents, showing up inside the
  analysis rather than in the audit.

THE FIX: falsify on the OUTCOME side instead, where every variable comes from the same
ward-tagged work-order text and varies properly.

  Flood hazard should predict DRAINAGE spending.
  It should NOT predict spending on buildings, street lighting, or water supply, none of
  which are flood-protective.
  Roads are deliberately ambiguous and reported as such: Indian road works routinely bundle
  side drains, so a positive road coefficient is expected and is not evidence of failure.
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

# outcome categories built from the work-order description text
CATS = {
    "drainage":     r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
                    r"\bdrain|\bkaluve\b|desilt|de-silt|culvert)",
    "building":     r"(building|community\s*hall|school|hospital|anganwadi|office|toilet)",
    "streetlight":  r"(street\s*light|streetlight|\bhigh\s*mast|lamp|lighting|electric)",
    "water_supply": r"(water\s*supply|borewell|bore\s*well|overhead\s*tank|cauvery|pipeline)",
    "roads":        r"(\broad\b|asphalt|black\s*top|white\s*top|tar\b|pavement)",
    "parks":        r"(\bpark\b|garden|playground|tree|green|lung\s*space)",
}
EXPECT = {"drainage": "POSITIVE - the hypothesis",
          "building": "~zero", "streetlight": "~zero", "water_supply": "~zero",
          "roads": "ambiguous - road works bundle side drains",
          "parks": "~zero"}

CONTROLS = "log_total + log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"


def rebuild_outcomes(df):
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))].copy()
    low = w["desc"].astype(str).str.lower()
    tot = w.groupby("ward").amount.sum().rename("tot")
    out = tot.to_frame()
    for cat, pat in CATS.items():
        s = w[low.str.contains(pat, regex=True, na=False)].groupby("ward").amount.sum()
        out[f"sh_{cat}"] = (s / tot * 100).fillna(0)
    out = out.reset_index()
    return df.merge(out.drop(columns="tot"), left_on="ward", right_on="ward", how="left")


if __name__ == "__main__":
    df = pd.read_parquet(ROOT / "data/final/bengaluru_panel_controlled.parquet")
    df = rebuild_outcomes(df)

    print("  === WHY THE HAZARD-SIDE TEST WAS INVALID ===")
    for c, lab in [("flood_hazard", "HAND (terrain, 30 m)"),
                   ("hot_days_35c", "CCKP hd35 (0.25 deg)")]:
        s = df[c].dropna()
        print(f"    {lab:24s} CV {s.std()/abs(s.mean())*100:5.2f}%   "
              f"distinct values across 198 wards: {s.round(4).nunique()}")
    print("    -> a 6-valued variable cannot falsify anything at ward scale.\n")

    print("  === OUTCOME-SIDE FALSIFICATION: flood hazard vs each spending category ===")
    print(f"  {'category':14s} {'beta':>8s} {'se':>6s} {'p':>7s}   expectation")
    rows = []
    for cat in CATS:
        m = smf.ols(f"sh_{cat} ~ z_flood_hazard + {CONTROLS}", data=df).fit(cov_type="HC1")
        b, se, p = (m.params["z_flood_hazard"], m.bse["z_flood_hazard"],
                    m.pvalues["z_flood_hazard"])
        stars = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        rows.append({"category": cat, "beta": b, "se": se, "p": p,
                     "expectation": EXPECT[cat], "mean_share": df[f"sh_{cat}"].mean()})
        print(f"  {cat:14s} {b:+8.2f} {se:6.2f} {p:7.3f}{stars:3s}  {EXPECT[cat]}")

    r = {x["category"]: x for x in rows}
    placebos = ["building", "streetlight", "water_supply", "parks"]
    n_sig = sum(r[c]["p"] < .05 for c in placebos)
    drain_sig = r["drainage"]["p"] < .10 and r["drainage"]["beta"] > 0
    print(f"\n    drainage positive & signif at 10%: {'YES' if drain_sig else 'NO'} "
          f"(beta {r['drainage']['beta']:+.2f}, p={r['drainage']['p']:.3f})")
    print(f"    placebo categories significant at 5%: {n_sig} of {len(placebos)}")
    verdict = ("PASSES" if drain_sig and n_sig == 0 else
               "PARTIAL" if drain_sig else "FAILS")
    print(f"    >>> FALSIFICATION {verdict}")

    pd.DataFrame(rows).to_csv(OUT / "tables/falsification_outcome_side.csv", index=False)
    df.to_parquet(ROOT / "data/final/bengaluru_final.parquet", index=False)
    print(f"\n  -> {OUT/'tables/falsification_outcome_side.csv'}")
