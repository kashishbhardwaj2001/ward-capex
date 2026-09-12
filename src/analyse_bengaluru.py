"""
First real test: does Bengaluru's drainage money go to the wards that flood?

Joins the BBMP ward-tagged work-order panel to the per-ward terrain hazard surface and
runs the headline specification plus the falsification test.

Design notes that matter:
  * Unit = the stable 198-ward (2012) geography. Post-2022 regimes are dropped here
    rather than crosswalked, so this is the honest first cut, not the final panel.
  * Hazard = HAND-derived (share of ward below 5 m above nearest drainage). CCKP climate
    layers are 0.25 deg and are near-constant inside a city (SD 0.1 on mean 3.9 across
    198 wards) so they CANNOT identify anything within-city. That negative is reported.
  * DESCRIPTIVE. Hazard is time-invariant and non-manipulable; there is no counterfactual
    Bengaluru with flatter terrain. No causal claim is made.
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
(OUT / "tables").mkdir(parents=True, exist_ok=True)

TIERS = ["narrow", "medium", "broad"]


def load():
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    haz = pd.read_parquet(INT / "ward_hazard.parquet")
    ter = pd.read_parquet(INT / "ward_terrain.parquet")

    # hazard/terrain are keyed on unit_id = row order of the boundary file
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson")
    g["unit_id"] = range(len(g))
    # NB: the pooled hazard table carries attribute columns from EVERY city, and one of
    # them (Vadodara) already has a lowercase 'ward_no'. Merging on that name silently
    # produces ward_no_x / ward_no_y and the key vanishes. Use a unique name.
    g["blr_ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    g["blr_ward_name"] = g["WARD_NAME"]

    hz = haz[haz.city == "bengaluru_198"][
        ["city", "unit_id", "area_km2", "rain20mm_days", "rain50mm_days",
         "hot_days_35c", "consec_dry_days", "precip_annual", "landslide"]]
    h = (hz.merge(ter[ter.city == "bengaluru_198"], on=["city", "unit_id"])
           .merge(g[["unit_id", "blr_ward", "blr_ward_name",
                     "POP_TOTAL", "POP_SC", "POP_ST", "AREA_SQ_KM"]], on="unit_id"))
    return wo, h


def build_panel(wo, h):
    # keep the 198-ward regime only: wards 1..198 and FYs before the 2022 re-delimitation
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))].copy()

    agg = {"total": ("amount", "sum"), "n_orders": ("amount", "size")}
    base = w.groupby("ward").agg(**agg).reset_index()
    for t in TIERS:
        s = (w[w[f"is_{t}"]].groupby("ward").amount.sum()
             .rename(f"drain_{t}"))
        base = base.merge(s, on="ward", how="left")
    base[[f"drain_{t}" for t in TIERS]] = base[[f"drain_{t}" for t in TIERS]].fillna(0)
    for cat in ["park_green", "road", "water_supply"]:
        s = w[w[f"cat_{cat}"]].groupby("ward").amount.sum().rename(f"spend_{cat}")
        base = base.merge(s, on="ward", how="left")
    base = base.fillna(0)

    df = base.merge(h, left_on="ward", right_on="blr_ward", how="inner")
    for t in TIERS:
        df[f"share_{t}"] = df[f"drain_{t}"] / df["total"] * 100
    df["share_park"] = df["spend_park_green"] / df["total"] * 100
    df["log_total"] = np.log(df["total"].clip(lower=1))
    df["flood_hazard"] = df["hand_lt5m_share"]          # 0-1, share of ward low-lying
    df["heat_hazard"] = df["hot_days_35c"]
    # standardise for readable coefficients
    for c in ["flood_hazard", "heat_hazard", "twi", "slope", "landslide"]:
        if c in df:
            df[f"z_{c}"] = (df[c] - df[c].mean()) / df[c].std()
    return df


if __name__ == "__main__":
    wo, h = load()
    df = build_panel(wo, h)
    print(f"  panel: {len(df)} wards (198-ward regime, FY2013-2022)")
    print(f"  total works spend: Rs {df.total.sum()/1e7:,.0f} Cr")
    print(f"  hazard (share of ward <5m above drainage): "
          f"mean {df.flood_hazard.mean():.3f}  sd {df.flood_hazard.std():.3f}  "
          f"range {df.flood_hazard.min():.2f}-{df.flood_hazard.max():.2f}")

    print("\n  === GATE G1: is there variation in drainage spend to explain? ===")
    for t in TIERS:
        s = df[f"share_{t}"]
        print(f"    {t:7s} share of works spend: mean {s.mean():5.1f}%  sd {s.std():5.1f}  "
              f"zeros {(s == 0).sum():3d}/{len(s)}")

    print("\n  === HEADLINE: does drainage spend track flood hazard? ===")
    rows = []
    for t in TIERS:
        m = smf.ols(f"share_{t} ~ z_flood_hazard + log_total", data=df).fit(
            cov_type="HC1")
        b, p = m.params["z_flood_hazard"], m.pvalues["z_flood_hazard"]
        rows.append({"tier": t, "beta": b, "se": m.bse["z_flood_hazard"],
                     "p": p, "r2": m.rsquared, "n": int(m.nobs)})
        stars = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {t:7s}  beta = {b:+6.2f} pp per SD of hazard "
              f"(se {m.bse['z_flood_hazard']:.2f}, p={p:.3f}){stars}   R2={m.rsquared:.3f}")

    print("\n  === FALSIFICATION: hazard-matching ===")
    print("     (drainage should respond to FLOOD; parks should respond to HEAT, not flood)")
    fals = []
    for out_v, lab in [("share_medium", "drainage"), ("share_park", "parks/green")]:
        for hz, hlab in [("z_flood_hazard", "flood"), ("z_heat_hazard", "heat")]:
            m = smf.ols(f"{out_v} ~ {hz} + log_total", data=df).fit(cov_type="HC1")
            b, p = m.params[hz], m.pvalues[hz]
            fals.append({"outcome": lab, "hazard": hlab, "beta": b, "p": p})
            flag = "<-- expected" if (lab == "drainage" and hlab == "flood") else ""
            print(f"    {lab:12s} ~ {hlab:5s}  beta {b:+6.2f}  p={p:.3f}  {flag}")

    print("\n  === THE ALIGNMENT GAP: high hazard, low drainage spend ===")
    m = smf.ols("share_medium ~ z_flood_hazard + log_total", data=df).fit()
    df["resid"] = m.resid
    hi = df[df.flood_hazard > df.flood_hazard.quantile(.75)]
    worst = hi.nsmallest(8, "resid")[["blr_ward_name", "ward", "flood_hazard",
                                      "share_medium", "resid"]]
    print(worst.to_string(index=False,
                          float_format=lambda x: f"{x:7.2f}"))

    pd.DataFrame(rows).to_csv(OUT / "tables/headline.csv", index=False)
    pd.DataFrame(fals).to_csv(OUT / "tables/falsification.csv", index=False)
    df.to_parquet(ROOT / "data/final/bengaluru_panel.parquet", index=False)
    print(f"\n  -> {ROOT/'data/final/bengaluru_panel.parquet'}")
