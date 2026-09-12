"""
Ward x year panel with year and zone fixed effects, plus the zero-inflation treatment.

Why this beats the cross-section already run: cumulative FY2013-2022 spend collapses ten
years into one number, so a single large project in one ward drives its whole value. A
ward x year panel with year FE removes common time shocks (BBMP's budget cycle, the 2022
delimitation, COVID) and lets ward-level spending be modelled as the repeated, lumpy,
frequently-zero process it actually is.

Zone FE: BBMP's 8 administrative zones each hold their own works budget and engineering
staff, so zone is the within-city analogue of the city FE used in the pooled multi-city
model. Identification then comes from hazard differences BETWEEN WARDS INSIDE A ZONE.

Zero-inflation: drainage spend is zero in many ward-years. A share regression on a mass of
zeros is mis-specified, so we run (a) a linear model on the share, (b) a logit on whether
the ward spent anything on drainage at all, and (c) a log-linear model on the positive
amounts. Reporting all three is the honest treatment of a hurdle process.
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "output"

DRAIN = (r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
         r"\bdrain|\bkaluve\b|desilt|de-silt|culvert)")


def build():
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))].copy()
    w["is_drain"] = w["desc"].astype(str).str.lower().str.contains(DRAIN, regex=True, na=False)

    tot = w.groupby(["ward", "fy"]).amount.sum().rename("total")
    dr = w[w.is_drain].groupby(["ward", "fy"]).amount.sum().rename("drain")
    p = pd.concat([tot, dr], axis=1).reset_index()
    p["drain"] = p["drain"].fillna(0)

    # complete the panel: a ward-year with no work orders is a real zero, not missing
    full = pd.MultiIndex.from_product(
        [range(1, 199), range(2013, 2023)], names=["ward", "fy"]).to_frame(index=False)
    p = full.merge(p, on=["ward", "fy"], how="left").fillna({"total": 0, "drain": 0})

    p["share"] = np.where(p.total > 0, p.drain / p.total * 100, np.nan)
    p["any_drain"] = (p.drain > 0).astype(int)
    p["log_drain"] = np.log(p.drain.clip(lower=1))
    p["log_total"] = np.log(p.total.clip(lower=1))

    ward = pd.read_parquet(ROOT / "data/final/bengaluru_final.parquet")
    cols = ["ward", "z_flood_hazard", "flood_hazard", "log_pop", "z_log_density",
            "z_dist_centre_km", "z_elev_m", "z_slope", "z_sc_st_share", "blr_ward_name"]
    df = p.merge(ward[[c for c in cols if c in ward.columns]], on="ward", how="left")

    # BBMP zones: derive from the polygon file's assembly-constituency grouping as a
    # stand-in for the 8 administrative zones (the ward file carries no zone field)
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson")
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    g["zone"] = g["ASS_CONST1"].astype(str)
    df = df.merge(g[["ward", "zone"]], on="ward", how="left")
    return df.dropna(subset=["z_flood_hazard"])


CTRL = "log_total + log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"

if __name__ == "__main__":
    df = build()
    act = df[df.total > 0]
    print(f"  panel: {len(df):,} ward-years ({df.ward.nunique()} wards x {df.fy.nunique()} years)")
    print(f"  ward-years with ANY works spend : {len(act):,} ({len(act)/len(df)*100:.0f}%)")
    print(f"  ward-years with ANY drainage    : {int(df.any_drain.sum()):,} "
          f"({df.any_drain.mean()*100:.0f}%)")
    print(f"  zones (assembly constituencies) : {df.zone.nunique()}")

    print("\n  === (a) LINEAR on drainage share, adding fixed effects ===")
    specs = {
        "pooled":            f"share ~ z_flood_hazard + {CTRL}",
        "+ year FE":         f"share ~ z_flood_hazard + {CTRL} + C(fy)",
        "+ year & zone FE":  f"share ~ z_flood_hazard + {CTRL} + C(fy) + C(zone)",
    }
    rows = []
    for name, f in specs.items():
        m = smf.ols(f, data=act).fit(cov_type="cluster",
                                     cov_kwds={"groups": act["ward"]})
        b, se, p = (m.params["z_flood_hazard"], m.bse["z_flood_hazard"],
                    m.pvalues["z_flood_hazard"])
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {name:18s} beta {b:+6.2f} (se {se:4.2f}) p={p:.3f}{st:3s} "
              f"R2={m.rsquared:.3f} n={int(m.nobs):,}")
        rows.append({"model": "share", "spec": name, "beta": b, "se": se, "p": p})

    print("\n  === (b) LOGIT: does the ward spend ANYTHING on drainage that year? ===")
    m = smf.logit(f"any_drain ~ z_flood_hazard + {CTRL} + C(fy)", data=act).fit(disp=0)
    b, p = m.params["z_flood_hazard"], m.pvalues["z_flood_hazard"]
    mfx = b * df.any_drain.mean() * (1 - df.any_drain.mean())
    st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
    print(f"    coef {b:+.3f} (p={p:.3f}){st}  ~ marginal effect {mfx*100:+.1f} pp "
          f"per SD of hazard")
    rows.append({"model": "logit_any", "spec": "+year FE", "beta": b, "se": m.bse['z_flood_hazard'], "p": p})

    print("\n  === (c) LOG AMOUNT, conditional on spending anything ===")
    pos = act[act.drain > 0]
    m = smf.ols(f"log_drain ~ z_flood_hazard + {CTRL} + C(fy) + C(zone)", data=pos).fit(
        cov_type="cluster", cov_kwds={"groups": pos["ward"]})
    b, p = m.params["z_flood_hazard"], m.pvalues["z_flood_hazard"]
    st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
    print(f"    beta {b:+.3f} (p={p:.3f}){st}  => {(np.exp(b)-1)*100:+.1f}% more drainage "
          f"spend per SD of hazard, n={int(m.nobs):,}")
    rows.append({"model": "log_amount", "spec": "+year&zone FE", "beta": b,
                 "se": m.bse['z_flood_hazard'], "p": p})

    pd.DataFrame(rows).to_csv(OUT / "tables/panel_results.csv", index=False)
    df.to_parquet(ROOT / "data/final/bengaluru_ward_year_panel.parquet", index=False)
    print(f"\n  -> {OUT/'tables/panel_results.csv'}")
