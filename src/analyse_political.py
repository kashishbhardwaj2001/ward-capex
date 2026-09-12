"""
Political-economy control (plan item 5.5).

BBMP's last council election was 2015 (198 wards); the council's term ended September 2020
and no election has been held since, so the 2015 result is the relevant assignment for the
FY2013-2022 panel. Party split: BJP 100, INC 76, JDS 14, IND 7, SDPI 1 - matching the
published headline exactly.

Two questions:
  (a) Does a ward's councillor party predict its capital budget, once hazard and ward
      characteristics are controlled? If ruling-party wards get more, the budget gap this
      study documents may be political rather than technocratic.
  (b) Does adding party absorb the hazard->budget effect? If the -12.8% survives, the
      misallocation is not simply partisan targeting.

Karnataka state government during the panel: INC to May 2018, BJP/coalition 2018-2023.
A ward is coded ALIGNED if its corporator's party held the state government that year.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

# Karnataka ruling party by Indian fiscal year (FY beginning April)
STATE_RULER = {2013: "INC", 2014: "INC", 2015: "INC", 2016: "INC", 2017: "INC",
               2018: "JDS", 2019: "BJP", 2020: "BJP", 2021: "BJP", 2022: "BJP"}

CTRL = "log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"

if __name__ == "__main__":
    d = pd.read_parquet(ROOT / "data/final/bengaluru_budget_panel.parquet")
    d["ward"] = pd.to_numeric(d["unit"], errors="coerce")
    pol = pd.read_csv(ROOT / "data/raw/bbmp_councillors_2015.csv")
    pol["ward"] = pd.to_numeric(pol["ward"], errors="coerce")
    d = d.merge(pol[["ward", "party"]], on="ward", how="left")

    # elev_m / slope are already on this panel from the multi-city join - don't re-merge,
    # which would suffix them to elev_m_x / elev_m_y and silently drop the control
    for c in ["elev_m", "slope"]:
        d[f"z_{c}"] = (d[c] - d[c].mean()) / d[c].std()

    d["ruler"] = d["fy"].map(STATE_RULER)
    d["aligned"] = (d["party"] == d["ruler"]).astype(int)
    d["bjp"] = (d["party"] == "BJP").astype(int)
    d = d.dropna(subset=["party", "z_hazard", "log_total"])

    print(f"  panel: {len(d):,} ward-years, {d.ward.nunique()} wards, "
          f"party known for {d.party.notna().mean()*100:.0f}%")
    print("\n  party distribution (wards):")
    for k, v in pol.party.value_counts().items():
        print(f"    {k:6s} {v:4d}")
    print(f"\n  ward-years where corporator party == state ruling party: "
          f"{d.aligned.mean()*100:.0f}%")

    print("\n  === (a) does party predict the ward's TOTAL capital budget? ===")
    m = smf.ols(f"log_total ~ aligned + z_hazard + {CTRL} + C(fy)", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d["ward"]})
    for v, lab in [("aligned", "aligned with state ruling party"),
                   ("z_hazard", "flood hazard (per SD)")]:
        b, p = m.params[v], m.pvalues[v]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {lab:34s} {(np.exp(b)-1)*100:+6.1f}%  p={p:.4f}{st}")

    print("\n  === (b) does the hazard-budget effect survive party controls? ===")
    rows = []
    for lab, f in [
        ("no political control", f"log_total ~ z_hazard + {CTRL} + C(fy)"),
        ("+ aligned dummy",      f"log_total ~ z_hazard + aligned + {CTRL} + C(fy)"),
        ("+ party fixed effects", f"log_total ~ z_hazard + C(party) + {CTRL} + C(fy)"),
        ("+ party x year FE",    f"log_total ~ z_hazard + C(party):C(fy) + {CTRL}"),
    ]:
        r = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["ward"]})
        b, se, p = r.params["z_hazard"], r.bse["z_hazard"], r.pvalues["z_hazard"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {lab:24s} hazard {(np.exp(b)-1)*100:+6.1f}%  (se {se:.3f}) p={p:.4f}{st}")
        rows.append({"spec": lab, "beta": b, "se": se, "p": p,
                     "pct": (np.exp(b) - 1) * 100})

    print("\n  === is hazard itself politically distributed? ===")
    w = d.groupby(["ward", "party"]).z_hazard.first().reset_index()
    for k, gg in w.groupby("party"):
        if len(gg) >= 5:
            print(f"    {k:6s} n={len(gg):3d}  mean hazard z = {gg.z_hazard.mean():+.3f}")

    pd.DataFrame(rows).to_csv(OUT / "tables/political.csv", index=False)
    print(f"\n  -> {OUT/'tables/political.csv'}")
