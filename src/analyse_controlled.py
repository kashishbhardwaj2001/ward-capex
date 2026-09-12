"""
Bengaluru, with controls - fixing the falsification failure.

THE PROBLEM THE FIRST CUT EXPOSED. With no controls, drainage spending responded MORE
strongly to heat (beta -3.16, p=0.010) than to flood (beta +2.31, p=0.089). Drainage does
not respond to heat. That pattern is the signature of an omitted variable correlated with
both: in Bengaluru, hot wards are the outer, newer, lower-density, later-annexed ones,
which also have different budgets and different drainage stock. The falsification test did
its job - it caught a specification that was measuring urban form, not hazard-matching.

WHAT THIS FILE ADDS.
  * ward population, area, density (2011 census, carried on the 198-ward polygon file)
  * SC/ST population share - an equity control and a plausible allocation confound
  * distance from the city centre - a single proxy for the core/periphery gradient that
    drives the heat correlation
  * elevation and slope - terrain confounds that are NOT the flood channel
  * zone fixed effects - BBMP's 8 administrative zones have their own budgets and
    engineers, so this is the within-city analogue of city FE in the pooled model

Re-run the falsification test after each addition. If drainage still tracks heat more than
flood once core/periphery is absorbed, the design is measuring urban form and must be said
so plainly.
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
(OUT / "tables").mkdir(parents=True, exist_ok=True)


def add_controls(df):
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(4326)
    g["unit_id"] = range(len(g))
    cen = g.to_crs(32643).geometry.centroid          # UTM 43N for Bengaluru
    city_centre = cen.union_all().centroid
    g["dist_centre_km"] = cen.distance(city_centre) / 1000
    g["ward_area_km2"] = g.to_crs(6933).area / 1e6

    keep = g[["unit_id", "dist_centre_km", "ward_area_km2",
              "POP_TOTAL", "POP_SC", "POP_ST", "RESERVATIO"]].copy()
    for c in ["POP_TOTAL", "POP_SC", "POP_ST"]:
        keep[c] = pd.to_numeric(keep[c], errors="coerce")
    df = df.merge(keep, on="unit_id", how="left", suffixes=("", "_g"))

    df["pop"] = df["POP_TOTAL"].replace(0, np.nan)
    df["density"] = df["pop"] / df["ward_area_km2"]
    df["sc_st_share"] = (df["POP_SC"].fillna(0) + df["POP_ST"].fillna(0)) / df["pop"]
    df["log_pop"] = np.log(df["pop"].clip(lower=1))
    df["log_density"] = np.log(df["density"].clip(lower=1))
    for c in ["dist_centre_km", "log_density", "sc_st_share", "elev_m", "slope", "twi"]:
        if c in df:
            df[f"z_{c}"] = (df[c] - df[c].mean()) / df[c].std()
    return df


SPECS = {
    "1 bare":          "z_flood_hazard + log_total",
    "2 +size":         "z_flood_hazard + log_total + log_pop + z_log_density",
    "3 +core/periph":  "z_flood_hazard + log_total + log_pop + z_log_density + z_dist_centre_km",
    "4 +terrain":      "z_flood_hazard + log_total + log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope",
    "5 +equity":       "z_flood_hazard + log_total + log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope + z_sc_st_share",
}

if __name__ == "__main__":
    df = pd.read_parquet(ROOT / "data/final/bengaluru_panel.parquet")
    df = add_controls(df)
    print(f"  {len(df)} wards | pop coverage {df['pop'].notna().mean()*100:.0f}%")
    print(f"  dist from centre: {df.dist_centre_km.min():.1f}-{df.dist_centre_km.max():.1f} km")

    print("\n  === HEAT vs DISTANCE: is heat just the core/periphery gradient? ===")
    c = df[["heat_hazard", "dist_centre_km", "flood_hazard", "log_density"]].corr()
    print(f"    corr(heat, dist_from_centre)   = {c.loc['heat_hazard','dist_centre_km']:+.3f}")
    print(f"    corr(heat, density)            = {c.loc['heat_hazard','log_density']:+.3f}")
    print(f"    corr(flood, heat)              = {c.loc['flood_hazard','heat_hazard']:+.3f}")

    print("\n  === HEADLINE, adding controls one at a time (outcome: drainage share, medium tier) ===")
    rows = []
    for name, rhs in SPECS.items():
        m = smf.ols(f"share_medium ~ {rhs}", data=df).fit(cov_type="HC1")
        b, se, p = (m.params["z_flood_hazard"], m.bse["z_flood_hazard"],
                    m.pvalues["z_flood_hazard"])
        stars = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {name:16s} beta {b:+6.2f} (se {se:4.2f}) p={p:.3f}{stars:3s}  "
              f"R2={m.rsquared:.3f}  n={int(m.nobs)}")
        rows.append({"spec": name, "beta": b, "se": se, "p": p, "r2": m.rsquared})

    print("\n  === FALSIFICATION, re-run under the FULL specification ===")
    full = SPECS["5 +equity"]
    fals = []
    for outcome, lab in [("share_medium", "drainage"), ("share_park", "parks/green")]:
        for hz, hlab in [("z_flood_hazard", "flood"), ("z_heat_hazard", "heat")]:
            rhs = full.replace("z_flood_hazard", hz)
            m = smf.ols(f"{outcome} ~ {rhs}", data=df).fit(cov_type="HC1")
            b, p = m.params[hz], m.pvalues[hz]
            fals.append({"outcome": lab, "hazard": hlab, "beta": b, "p": p})
            note = ("EXPECTED" if (lab == "drainage" and hlab == "flood")
                    else "should be ~0")
            print(f"    {lab:12s} ~ {hlab:5s}  beta {b:+6.2f}  p={p:.3f}   ({note})")

    d_f = [r for r in fals if r["outcome"] == "drainage" and r["hazard"] == "flood"][0]
    d_h = [r for r in fals if r["outcome"] == "drainage" and r["hazard"] == "heat"][0]
    passed = abs(d_f["beta"]) > abs(d_h["beta"]) and d_f["beta"] > 0
    print(f"\n    >>> FALSIFICATION {'PASSES' if passed else 'STILL FAILS'}: "
          f"|flood|={abs(d_f['beta']):.2f} vs |heat|={abs(d_h['beta']):.2f}")

    pd.DataFrame(rows).to_csv(OUT / "tables/controlled_specs.csv", index=False)
    pd.DataFrame(fals).to_csv(OUT / "tables/falsification_controlled.csv", index=False)
    df.to_parquet(ROOT / "data/final/bengaluru_panel_controlled.parquet", index=False)
    print(f"\n  -> {OUT/'tables/controlled_specs.csv'}")
