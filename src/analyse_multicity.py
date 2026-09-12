"""
Pooled multi-city test with city fixed effects.

Identification: hazard is standardised WITHIN each city and city FE are included, so the
coefficient is driven entirely by differences between sub-city units inside the same city.
A Bengaluru ward is never compared to a Chennai zone.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

if __name__ == "__main__":
    m = pd.read_parquet(ROOT / "data/final/multicity_panel.parquet")
    m["log_spend"] = np.log(m.storm_spend.clip(lower=1))
    m["log_area"] = np.log(m.area_km2.clip(lower=.01))

    print(f"  pooled panel: {len(m):,} unit-years, {m.city.nunique()} cities, "
          f"{m.groupby('city').unit.nunique().sum()} units")
    print(f"  total stormwater spend: Rs {m.storm_spend.sum()/1e7:,.0f} Cr\n")

    print("  === POOLED: log stormwater spend ~ within-city hazard ===")
    specs = {
        "city FE":              "log_spend ~ z_hazard + log_area + C(city)",
        "city + year FE":       "log_spend ~ z_hazard + log_area + C(city) + C(fy)",
        "city x year FE":       "log_spend ~ z_hazard + log_area + C(city):C(fy)",
    }
    rows = []
    for name, f in specs.items():
        r = smf.ols(f, data=m).fit(cov_type="cluster",
                                   cov_kwds={"groups": m["city"] + "_" + m["unit"]})
        b, se, p = r.params["z_hazard"], r.bse["z_hazard"], r.pvalues["z_hazard"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {name:16s} beta {b:+6.3f} (se {se:5.3f}) p={p:.3f}{st:3s} "
              f"=> {(np.exp(b)-1)*100:+5.1f}% per SD   n={int(r.nobs):,}  R2={r.rsquared:.3f}")
        rows.append({"spec": name, "beta": b, "se": se, "p": p, "n": int(r.nobs)})

    print("\n  === PER CITY (is the null universal, or Bengaluru-specific?) ===")
    for c, g in m.groupby("city"):
        if g.unit.nunique() < 5:
            print(f"    {c:10s} skipped ({g.unit.nunique()} units, too few)")
            continue
        r = smf.ols("log_spend ~ z_hazard + log_area", data=g).fit(
            cov_type="cluster", cov_kwds={"groups": g["unit"]})
        b, p = r.params["z_hazard"], r.pvalues["z_hazard"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {c:10s} beta {b:+6.3f} p={p:.3f}{st:3s} "
              f"=> {(np.exp(b)-1)*100:+6.1f}% per SD of hazard  "
              f"({g.unit.nunique()} units, {len(g)} unit-years)")
        rows.append({"spec": f"city:{c}", "beta": b, "se": r.bse["z_hazard"],
                     "p": p, "n": int(r.nobs)})

    pd.DataFrame(rows).to_csv(OUT / "tables/multicity_results.csv", index=False)
    print(f"\n  -> {OUT/'tables/multicity_results.csv'}")
