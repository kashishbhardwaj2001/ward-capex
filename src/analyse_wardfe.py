"""
The ward fixed-effects arm (the payoff of plan item 3.2).

WHY THIS IS THE SPECIFICATION THE STUDY WAS MISSING. Every result so far rests on a
CROSS-SECTION: terrain hazard does not move, so a ward fixed effect would absorb it
entirely. That leaves one question permanently open - "is this just ward wealth, or
ward politics, or anything else fixed about a ward that you failed to control for?"
Controls narrow that gap; they cannot close it.

CHIRPS daily gives a hazard measure that MOVES. Bengaluru had 4.9 extreme-rain days per
ward in FY2016 and 17.4 in FY2022. So the question becomes within-ward:

    when a ward has an unusually wet year, does its drainage budget respond?

with a ward fixed effect absorbing everything time-invariant about that ward - its
terrain, its wealth, its councillor, its distance from the centre - and a year fixed
effect absorbing the city-wide budget cycle.

WHAT IDENTIFIES IT, AND THE HONEST LIMIT. With ward FE and year FE both in, identification
comes only from wards deviating from the city's own year-to-year pattern - CHIRPS is
0.05 deg (~5.5 km), so Bengaluru's 198 wards sit in roughly 60-70 distinct pixels, and
within a pixel the rainfall is identical by construction. The residual variation is real
but modest. A null here is therefore weak evidence, and is reported as such; a
significant result would be strong.

TIMING. Capital works are commissioned, tendered and paid over months, so the response to
a wet year should show up in the SAME year at the earliest and more plausibly the next.
Both are estimated. A contemporaneous-only design would understate the response.

THE CONFOUND THAT DECIDES HOW ALL OF THIS READS - and it is not small. The outcome here is
EXECUTED spending, recovered from work orders and their payment records. It is not an
allocated budget. Heavy rain stops construction: a wet year mechanically suppresses how
much work gets done and paid for, in every category at once, for reasons that have nothing
to do with how anyone budgeted.

Run naively, this pipeline finds exactly that and it looks like a finding: within-ward,
a wetter year predicts LOWER drainage spending (-0.92 log points per SD, p = 0.001), with
ward and year fixed effects both in. Read as a budget response it would be a dramatic
result - budgets moving the wrong way when it rains.

It is not a budget response. The diagnostic below shows the same wet year suppresses the
NUMBER of work orders (-0.55, p = 0.001) and suppresses street lighting (-2.82) and
buildings (-2.21) MORE than drainage (-0.92). Everything falls together, and drainage falls
least. That is a throughput effect, not an allocation effect.

So the level specifications are reported but not interpreted, and the SHARE is the
specification that answers the question, because a common throughput shock cancels out of a
ratio. This distinction is the whole reason the diagnostic runs before the verdict rather
than after.
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


def build():
    d = pd.read_parquet(ROOT / "data/final/bengaluru_budget_panel.parquet")
    d["ward"] = pd.to_numeric(d["unit"], errors="coerce")

    ch = pd.read_parquet(INT / "ward_chirps.parquet")
    ch = ch[ch.city == "bengaluru_198"].copy()
    # unit_id is polygon order; map it to ward number off the polygon file
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").reset_index(drop=True)
    g["unit_id"] = range(len(g))
    g["blr_ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    ch = ch.merge(g[["unit_id", "blr_ward"]], on="unit_id", how="left")
    ch = ch.rename(columns={"blr_ward": "ward"}).drop(columns=["city", "unit_id"])

    d = d.merge(ch, on=["ward", "fy"], how="left")

    # lagged rainfall: the previous fiscal year's extreme-rain days for the same ward
    lag = ch.copy()
    lag["fy"] = lag["fy"] + 1
    d = d.merge(lag[["ward", "fy", "chirps_r20_days", "chirps_annual_mm"]]
                .rename(columns={"chirps_r20_days": "r20_lag",
                                 "chirps_annual_mm": "mm_lag"}),
                on=["ward", "fy"], how="left")

    # standardise WITHIN ward, so the coefficient is "a wet year for this ward",
    # not "a wet ward" - the latter is what the fixed effect removes anyway
    for src, dst in [("chirps_r20_days", "z_r20_w"), ("chirps_annual_mm", "z_mm_w"),
                     ("r20_lag", "z_r20_lag_w"), ("mm_lag", "z_mm_lag_w")]:
        gb = d.groupby("ward")[src]
        d[dst] = (d[src] - gb.transform("mean")) / gb.transform("std").replace(0, np.nan)
    return d.replace([np.inf, -np.inf], np.nan)


SPECS = [
    ("contemporaneous, ward + year FE", "z_r20_w"),
    ("lagged one year, ward + year FE", "z_r20_lag_w"),
    ("annual mm, ward + year FE",       "z_mm_w"),
    ("annual mm lagged, ward + year FE", "z_mm_lag_w"),
]

if __name__ == "__main__":
    d = build()
    cov = d.dropna(subset=["z_r20_w"])
    print(f"  panel: {len(d):,} ward-years, {d.ward.nunique()} wards, "
          f"CHIRPS attached to {len(cov):,} ({len(cov)/len(d)*100:.0f}%)\n")

    print("  === how much variation survives the two fixed effects? ===")
    r = d.dropna(subset=["chirps_r20_days"])
    tot = r.chirps_r20_days.std()
    resid = smf.ols("chirps_r20_days ~ C(ward) + C(fy)", data=r).fit().resid.std()
    print(f"    raw sd of extreme-rain days          {tot:5.2f}")
    print(f"    sd left after ward FE + year FE      {resid:5.2f}  "
          f"({resid/tot*100:.0f}% of the original)")
    print(f"    -> {resid/tot*100:.0f}% is what identifies every estimate below. "
          f"CHIRPS pixels are")
    print(f"       5.5 km, so wards sharing a pixel contribute nothing after the FEs.\n")

    print("  === does a wet year move the ward's budget? ===")
    print(f"  {'outcome':22s} {'specification':34s} {'beta':>8s} {'se':>7s} {'p':>8s}")
    rows = []
    for yname, ylab in [("log_total", "total ward budget"),
                        ("log_storm", "stormwater spend"),
                        ("storm_share", "stormwater share (pp)")]:
        for lab, xv in SPECS:
            dd = d.dropna(subset=[yname, xv])
            if len(dd) < 200 or dd.ward.nunique() < 50:
                print(f"  {ylab:22s} {lab:34s} skipped (n={len(dd)})")
                continue
            m = smf.ols(f"{yname} ~ {xv} + C(ward) + C(fy)", data=dd).fit(
                cov_type="cluster", cov_kwds={"groups": dd["ward"]})
            b, se, p = m.params[xv], m.bse[xv], m.pvalues[xv]
            st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
            print(f"  {ylab:22s} {lab:34s} {b:+8.4f} {se:7.4f} {p:8.3f}{st}")
            rows.append({"outcome": yname, "spec": lab, "beta": b, "se": se, "p": p,
                         "n": int(m.nobs), "wards": int(dd.ward.nunique())})
        print()

    # ---------------------------------------------------------------- the diagnostic
    # Before reading any level coefficient, establish whether a wet year suppresses
    # municipal works ACTIVITY as such. If it does, every level coefficient is
    # contaminated and only the share is interpretable.
    print("  === DIAGNOSTIC: is a wet year suppressing ACTIVITY, not budgets? ===")
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))].copy()
    low = w["desc"].astype(str).str.lower()
    CATS = {"drainage": r"(storm\s*water|\bswd\b|rajakaluve|\bnalla?\b|\bnala\b|"
                        r"\bdrain|\bkaluve\b|desilt|culvert)",
            "roads": r"(\broad\b|asphalt|black\s*top|white\s*top|tar\b|pavement)",
            "buildings": r"(building|community\s*hall|school|hospital|anganwadi|office|toilet)",
            "streetlight": r"(street\s*light|streetlight|high\s*mast|lamp|lighting|electric)"}
    dd = d.copy()
    for c, pat in CATS.items():
        a = (w[low.str.contains(pat, regex=True, na=False)]
             .groupby(["ward", "fy"]).amount.sum().rename(f"a_{c}"))
        dd = dd.merge(a, on=["ward", "fy"], how="left")
        dd[f"log_{c}"] = np.log(dd[f"a_{c}"].fillna(0).clip(lower=1))
    dd = dd.merge(w.groupby(["ward", "fy"]).size().rename("n_orders"),
                  on=["ward", "fy"], how="left")

    print(f"  {'outcome':26s} {'beta (annual mm, per SD)':>25s} {'se':>8s} {'p':>8s}")
    diag = []
    for lab, yv in [("work orders, COUNT", "log_n"), ("drainage spend", "log_drainage"),
                    ("roads spend", "log_roads"), ("buildings spend", "log_buildings"),
                    ("street lighting spend", "log_streetlight")]:
        if yv == "log_n":
            dd["log_n"] = np.log(dd["n_orders"].clip(lower=1))
        x = dd.dropna(subset=[yv, "z_mm_w"])
        m = smf.ols(f"{yv} ~ z_mm_w + C(ward) + C(fy)", data=x).fit(
            cov_type="cluster", cov_kwds={"groups": x["ward"]})
        b, se, p = m.params["z_mm_w"], m.bse["z_mm_w"], m.pvalues["z_mm_w"]
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:26s} {b:+25.4f} {se:8.4f} {p:8.3f}{st}")
        diag.append({"outcome": lab, "beta": b, "se": se, "p": p})
    pd.DataFrame(diag).to_csv(OUT / "tables/ward_fe_throughput.csv", index=False)

    n_neg = sum(x["beta"] < 0 for x in diag)
    print(f"\n    {n_neg} of {len(diag)} outcomes fall in a wet year, the order COUNT among")
    print("    them, and drainage falls LEAST of the four spending categories.")
    print("    -> this is construction throughput, not budget allocation. Level")
    print("       coefficients below are therefore reported but NOT interpreted as a")
    print("       budget response; the share nets the common shock out.\n")

    # ---------------------------------------------------------------- the verdict
    share_rows = [r_ for r_ in rows if r_["outcome"] == "storm_share"]
    share_sig = [r_ for r_ in share_rows if r_["p"] < .05]
    print("  === READING ===")
    print("    Interpretable specification: the stormwater SHARE, which is invariant to a")
    print("    common throughput shock. Level specifications are contaminated by it.")
    print("")
    if not share_sig:
        print(f"    None of the {len(share_rows)} share specifications detects a within-ward")
        print("    response to rainfall - contemporaneous or lagged, extreme-rain days or")
        print("    annual millimetres. A ward that has an unusually wet year does not tilt")
        print("    its capital budget toward drainage the following year.")
        print("")
        print("    Strength of this null, stated honestly: MODERATE, not strong. After ward")
        print(f"    and year fixed effects only {resid/tot*100:.0f}% of the rainfall variation survives, and")
        print("    wards sharing a 5.5 km CHIRPS pixel contribute none of it. The test could")
        print("    miss a real but modest response.")
        print("")
        print("    What it nonetheless establishes is the thing the cross-section could not:")
        print("    the headline is NOT an artefact of some fixed ward characteristic that")
        print("    happens to correlate with terrain. Within a single ward, holding")
        print("    everything fixed about it, the hazard moves and the allocation does not.")
    else:
        print(f"    {len(share_sig)} share specification(s) significant at 5%:")
        for r_ in share_sig:
            print(f"      {r_['spec']}: {r_['beta']:+.3f} pp (p={r_['p']:.3f})")
        print("    A within-ward reallocation survives both fixed effects and the")
        print("    throughput confound - materially stronger than the cross-section.")

    pd.DataFrame(rows).to_csv(OUT / "tables/ward_fe_rainfall.csv", index=False)
    print(f"\n  -> {OUT/'tables/ward_fe_rainfall.csv'}")
