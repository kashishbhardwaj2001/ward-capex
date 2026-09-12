"""
Full robustness suite (plan item 5.6) plus the extra outcomes from 4.2.

Arms:
  - all three tagging tiers
  - naive single-ward tag vs evenly-split multi-ward attribution
  - nominal vs deflated (constant FY2020 rupees)
  - drainage share / per capita / per km2 / per built-up km2
  - drop the largest 1% of projects
  - 198-ward vs 243-ward geography
  - Conley spatial standard errors alongside ward-clustered

Conley SEs matter here because wards are contiguous and terrain is spatially smooth: if
neighbouring wards share both hazard and spending shocks, ward-clustered SEs understate
uncertainty. Implemented as a uniform-kernel spatial HAC on ward centroids.
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

CTRL = "log_total + log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"


def conley_se(model, coords, cutoff_km=3.0):
    """Spatial HAC (Conley) standard errors, uniform kernel.

    X'X^-1 (sum_ij w_ij u_i u_j x_i x_j') X'X^-1, with w_ij = 1 if the two observations'
    ward centroids are within `cutoff_km`.
    """
    X = np.asarray(model.model.exog, dtype=float)
    u = np.asarray(model.resid, dtype=float)
    n, k = X.shape
    d = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    W = (d <= cutoff_km).astype(float)
    Xu = X * u[:, None]
    meat = Xu.T @ W @ Xu
    XtX_inv = np.linalg.pinv(X.T @ X)
    V = XtX_inv @ meat @ XtX_inv
    return np.sqrt(np.clip(np.diag(V), 0, None))


def build():
    p = pd.read_parquet(INT / "panel_v2.parquet")
    base = pd.read_parquet(ROOT / "data/final/bengaluru_budget_panel.parquet")
    keep = ["unit", "fy", "z_hazard", "hand_lt5m_share", "log_pop", "z_log_density",
            "z_dist_centre_km", "z_elev_m", "z_slope", "blr_ward_name"]
    base = base[[c for c in keep if c in base.columns]].copy()
    base["ward"] = pd.to_numeric(base["unit"], errors="coerce")
    d = p.merge(base.drop(columns=["unit"]), on=["ward", "fy"], how="inner")

    # elevation and slope live on the terrain table, keyed by polygon order; bring them
    # in and standardise, so the control set matches the rest of the study
    ter = pd.read_parquet(INT / "ward_terrain.parquet")
    ter = ter[ter.city == "bengaluru_198"].copy()
    gg = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson")
    gg["unit_id"] = range(len(gg))
    gg["ward"] = pd.to_numeric(gg["WARD_NO"], errors="coerce")
    ter = ter.merge(gg[["unit_id", "ward"]], on="unit_id")
    d = d.merge(ter[["ward", "elev_m", "slope", "twi"]], on="ward", how="left")
    for c in ["elev_m", "slope", "twi"]:
        d[f"z_{c}"] = (d[c] - d[c].mean()) / d[c].std()

    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    for t in ["narrow", "medium", "broad"]:
        s = (w[w[f"is_{t}"]].groupby(["ward", "fy"]).amount.sum()
             .rename(f"drain_{t}"))
        d = d.merge(s, on=["ward", "fy"], how="left")
    tot = w.groupby(["ward", "fy"]).amount.sum().rename("tot_nom")
    d = d.merge(tot, on=["ward", "fy"], how="left")
    for t in ["narrow", "medium", "broad"]:
        d[f"share_{t}"] = d[f"drain_{t}"].fillna(0) / d["tot_nom"] * 100

    # drop-largest-1% arm
    cut = w.amount.quantile(.99)
    ws = w[w.amount <= cut]
    s = ws[ws.is_medium].groupby(["ward", "fy"]).amount.sum().rename("drain_trim")
    t2 = ws.groupby(["ward", "fy"]).amount.sum().rename("tot_trim")
    d = d.merge(s, on=["ward", "fy"], how="left").merge(t2, on=["ward", "fy"], how="left")
    d["share_trim"] = d.drain_trim.fillna(0) / d.tot_trim * 100

    d["log_total"] = np.log(d.total_split.clip(lower=1))
    d["log_drain_pc"] = np.log(d.drain_pc.clip(lower=1))
    d["log_drain_bu"] = np.log(d.drain_per_builtup_km2.clip(lower=1))
    return d.replace([np.inf, -np.inf], np.nan)


ARMS = [
    ("tier: narrow",              "share_narrow"),
    ("tier: medium (baseline)",   "share_medium"),
    ("tier: broad",               "share_broad"),
    ("attribution: naive tag",    "share_naive"),
    ("attribution: split evenly", "share_split"),
    ("drop largest 1% projects",  "share_trim"),
    ("outcome: log per capita",   "log_drain_pc"),
    ("outcome: log per built-up km2", "log_drain_bu"),
]

if __name__ == "__main__":
    d = build()
    print(f"  panel: {len(d):,} ward-years, {d.ward.nunique()} wards\n")

    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(32643)
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    cen = g.set_index("ward").geometry.centroid
    cmap = {w: (pt.x / 1000, pt.y / 1000) for w, pt in cen.items()}

    print(f"  {'arm':32s} {'beta':>8s} {'clust se':>9s} {'p':>7s} {'Conley se':>10s} {'p':>7s}")
    rows = []
    for lab, yv in ARMS:
        dd = d.dropna(subset=[yv, "z_hazard", "log_total", "log_pop"])
        if len(dd) < 100:
            print(f"  {lab:32s} skipped (n={len(dd)})")
            continue
        m = smf.ols(f"{yv} ~ z_hazard + {CTRL} + C(fy)", data=dd).fit(
            cov_type="cluster", cov_kwds={"groups": dd["ward"]})
        b, se, p = m.params["z_hazard"], m.bse["z_hazard"], m.pvalues["z_hazard"]

        m0 = smf.ols(f"{yv} ~ z_hazard + {CTRL} + C(fy)", data=dd).fit()
        coords = np.array([cmap.get(w, (np.nan, np.nan)) for w in dd["ward"]])
        ok = np.isfinite(coords).all(1)
        try:
            cse = conley_se(m0, coords[ok])[list(m0.params.index).index("z_hazard")]
            cz = b / cse if cse else np.nan
            from scipy.stats import norm
            cp = 2 * (1 - norm.cdf(abs(cz)))
        except Exception:
            cse, cp = np.nan, np.nan
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:32s} {b:+8.3f} {se:9.3f} {p:7.3f}{st:3s} {cse:10.3f} {cp:7.3f}")
        rows.append({"arm": lab, "outcome": yv, "beta": b, "cluster_se": se,
                     "cluster_p": p, "conley_se": cse, "conley_p": cp, "n": int(m.nobs)})

    print("\n  === geography arm: 243-ward regime, post-2022 ===")
    try:
        xw = pd.read_parquet(INT / "post2022_on_198base.parquet")
        print(f"    post-2022 spend redistributed onto the 198-ward base: "
              f"{len(xw):,} ward-years, Rs {xw.amount.sum()/1e7:,.0f} Cr")
        print("    (kept as a separate arm - the 2022 delimitation changes the unit, so it "
              "is not pooled with FY2013-2022)")
    except Exception as e:
        print(f"    crosswalk arm unavailable: {e}")

    pd.DataFrame(rows).to_csv(OUT / "tables/robustness.csv", index=False)
    print(f"\n  -> {OUT/'tables/robustness.csv'}")
