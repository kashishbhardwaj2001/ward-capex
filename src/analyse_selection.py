"""
Selection into the sample (risk R11 in the plan).

THE RISK, AS THE PLAN STATED IT. "Cities that publish are better-governed, so results may
not generalise to cities that do not." The mitigation promised was to "state it explicitly;
compare publishing vs non-publishing cities on observables". Stating it is free; the
comparison is the part that can actually be wrong, so this script does it.

WHY IT MATTERS HERE SPECIFICALLY. The finding is that high-hazard wards get smaller budgets.
If the six cities that publish sub-city spending are systematically the LESS hazardous ones
- drier, higher, better drained - then the result is estimated on cities where the question
barely bites, and generalising it to Patna or Guwahati is unwarranted. If instead the
publishers are indistinguishable from, or MORE hazardous than, the non-publishers, the
external-validity worry is weaker.

WHAT CAN AND CANNOT BE COMPARED. Only hazard and physical geography, because those come from
global layers that cover every city equally (Copernicus DEM, CCKP, OSM). Governance quality
- the actual thing the risk is about - has no free pan-Indian ward-level measure, so it is
NOT tested here. This is a partial mitigation and is labelled as one: it can rule out the
crude version of the selection story (publishers are the dry cities), not the subtle one
(publishers are the competent cities).

Units: one row per boundary layer, aggregated from its wards. bengaluru_243 and chennai_ward
are dropped as duplicate geographies of layers already counted.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "output"

# the six cities whose sub-city spending is in the pooled panel
PUBLISHERS = {"bengaluru_198", "ahmedabad", "chennai_zone", "pune_admin", "mumbai", "surat"}
# duplicate geographies of a layer already counted - keeping both would double-weight a city
DUPES = {"bengaluru_243", "chennai_ward"}

METRICS = [
    ("hand_lt5m_share", "share of area with HAND < 5 m", "flood-prone land"),
    ("hand_m", "mean HAND (m)", "lower = more flood-prone"),
    ("rain20mm_days", "days > 20 mm / yr (CCKP)", "extreme rainfall"),
    ("rain50mm_days", "days > 50 mm / yr (CCKP)", "extreme rainfall"),
    ("precip_annual", "annual precipitation (mm)", "wetness"),
    ("slope", "mean slope", "lower = more ponding"),
    ("elev_m", "mean elevation (m)", "context"),
    ("area_km2", "mean ward area (km2)", "unit size"),
    ("drain_density_m_km2", "mapped drain density (m/km2)", "existing stock"),
]

if __name__ == "__main__":
    h = pd.read_parquet(INT / "ward_hazard.parquet")
    t = pd.read_parquet(INT / "ward_terrain.parquet")
    d = h.merge(t, on=["city", "unit_id"], how="left", suffixes=("", "_t"))
    dn = INT / "ward_drain_network.parquet"
    if dn.exists():
        n = pd.read_parquet(dn)
        keep = [c for c in ["city", "unit_id", "drain_density_m_km2"] if c in n.columns]
        d = d.merge(n[keep], on=["city", "unit_id"], how="left")

    d = d[~d.city.isin(DUPES)]
    city = d.groupby("city").agg(
        {m: "mean" for m, _, _ in METRICS if m in d.columns}).reset_index()
    city["n_units"] = d.groupby("city").size().values
    city["publishes"] = city.city.isin(PUBLISHERS)

    pub = city[city.publishes]
    non = city[~city.publishes]
    print(f"  {len(city)} cities with comparable hazard data: "
          f"{len(pub)} publish sub-city spending, {len(non)} do not\n")
    print(f"    publishers:     {', '.join(sorted(pub.city))}")
    print(f"    non-publishers: {', '.join(sorted(non.city))}\n")

    print("  === are the publishers systematically different? ===")
    print(f"  {'metric':30s} {'publishers':>12s} {'others':>12s} {'diff':>10s} "
          f"{'p (MW)':>8s}")
    rows = []
    for m, lab, _ in METRICS:
        if m not in city.columns:
            continue
        a, b = pub[m].dropna(), non[m].dropna()
        if len(a) < 3 or len(b) < 3:
            continue
        # Mann-Whitney rather than a t-test: n=6 vs n=14, and several of these
        # distributions are visibly skewed (drain density, area)
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        diff = a.mean() - b.mean()
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:30s} {a.mean():12,.2f} {b.mean():12,.2f} {diff:+10,.2f} "
              f"{p:8.3f}{st}")
        rows.append({"metric": m, "label": lab, "publishers": a.mean(),
                     "others": b.mean(), "diff": diff, "p": p, "n_pub": len(a),
                     "n_other": len(b)})

    sig = [r for r in rows if r["p"] < .05]
    haz = [r for r in rows if r["metric"] in
           ("hand_lt5m_share", "hand_m", "rain20mm_days", "rain50mm_days", "precip_annual")]
    haz_sig = [r for r in haz if r["p"] < .05]

    print(f"\n  === READING ===")
    print(f"    {len(sig)} of {len(rows)} observables differ at 5%; "
          f"{len(haz_sig)} of {len(haz)} HAZARD observables do.")
    print("")
    if not haz_sig:
        print("    On every hazard measure the publishing cities are statistically")
        print("    indistinguishable from the cities that do not publish. The crude version")
        print("    of the selection story - that sub-city disclosure comes from the dry,")
        print("    high, well-drained cities where this question barely bites - is not")
        print("    supported.")
    else:
        print("    Publishers DO differ on hazard:")
        for r in haz_sig:
            direction = "MORE" if (r["diff"] > 0) == (r["metric"] != "hand_m"
                                                      and r["metric"] != "slope") else "LESS"
            print(f"      {r['label']}: {r['diff']:+,.2f} (p={r['p']:.3f})")
        print("    The sample is not hazard-representative; the estimate should not be")
        print("    extrapolated to Indian cities generally without saying so.")
    # the one difference that does show up is about MY units, not about selection
    area = [r for r in rows if r["metric"] == "area_km2"]
    if area and area[0]["p"] < .05:
        a = area[0]
        print("")
        print(f"    The one observable that does differ is mean ward AREA "
              f"({a['publishers']:,.1f} vs {a['others']:,.1f} km2,")
        print(f"    p = {a['p']:.3f}) - and that is an artefact of this study, not a fact about")
        print("    the cities. Three of the six publishers report at ZONE level (Chennai,")
        print("    Pune, Surat), so their units are larger by construction. It is the same")
        print("    reporting-unit coarseness already flagged as the reason Mumbai and Surat")
        print("    cannot resolve the question, showing up again from a different angle.")
        print("    It says nothing about whether publishers are unusual cities.")
    print("")
    print("    WHAT THIS DOES NOT TEST: governance quality, which is what the risk is")
    print("    really about. No free pan-Indian measure of municipal capacity exists at")
    print("    this resolution, so the subtle version of the selection story - that")
    print("    publishers are the COMPETENT cities, and competent cities may allocate")
    print("    differently - remains open and is stated as a limitation rather than")
    print("    tested away.")

    city.to_csv(OUT / "tables/selection_city_observables.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "tables/selection_tests.csv", index=False)
    print(f"\n  -> {OUT/'tables/selection_tests.csv'}")
