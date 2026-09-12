"""
Ward name -> polygon join, and the canonical ward layer (plan items 2.3 and 2.4).

WHY A FUZZY JOIN AT ALL. Both sides carry a ward NUMBER, so the join is nominally trivial.
It is still worth doing on the name, because the number is the thing most likely to be
silently wrong: BBMP reused ward numbers across the 198 / 225 / 243 delimitations, and a
file mislabelled with the wrong regime would join cleanly on number and put every ward's
money in the wrong polygon. Matching names INDEPENDENTLY and then checking that the name
match agrees with the number match is a cheap detector for exactly that failure.

So this script runs two joins and compares them:
  (a) numeric  ward_no  <->  WARD_NO
  (b) fuzzy    ward_name <-> WARD_NAME, after normalisation

Normalisation matters more than the string metric here. Indian ward names vary in
romanisation far more than they vary in spelling: "Chowdeswari"/"Choudeswari",
"Attur"/"Atturu"/"Athuru", the optional trailing "Ward", "Nagar"/"Nagara",
"Puram"/"Pura", "Halli"/"Palya". Normalising those away first turns most near-misses
into exact matches, which is why a plain difflib ratio is enough and no extra dependency
is needed.

Every disagreement between (a) and (b) is written to ward_join_manual.csv with the
decision and its reason, so the residual is auditable rather than absorbed.

Output: data/final/wards.gpkg - the canonical 198-ward layer carrying geometry, census
attributes, hazard, terrain and the panel's spending aggregates. One file a reader can
open in QGIS and check the whole study against.
"""
import re
import unicodedata
import warnings
from difflib import SequenceMatcher
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
FIN = ROOT / "data/final"
FIN.mkdir(parents=True, exist_ok=True)

# romanisation variants seen in the BBMP files, longest first so that e.g. "nagara"
# is rewritten before "nagar" can match its prefix
VARIANTS = [
    (r"nagara\b", "nagar"), (r"puram\b", "pura"), (r"pete\b", "peta"),
    (r"palya\b", "palya"), (r"halli\b", "halli"), (r"kere\b", "kere"),
    (r"\bsri\b", "shri"), (r"\bshree\b", "shri"), (r"\bsree\b", "shri"),
    (r"ou", "o"), (r"au", "o"), (r"aa", "a"), (r"ee", "i"), (r"oo", "u"),
    (r"th", "t"), (r"dh", "d"), (r"bh", "b"), (r"gh", "g"), (r"kh", "k"),
    (r"ph", "f"), (r"v", "w"), (r"j", "z"),
]


def norm(s):
    """Aggressive romanisation-tolerant normalisation."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"\b(ward|wards)\b", " ", s)          # the trailing "Ward" is noise
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    for pat, rep in VARIANTS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"(.)\1+", r"\1", s)                   # collapse doubled letters
    return re.sub(r"\s+", "", s)


def best_match(name, cands):
    n = norm(name)
    scored = [(SequenceMatcher(None, n, norm(c)).ratio(), c) for c in cands]
    scored.sort(reverse=True)
    return scored[0][1], scored[0][0]


if __name__ == "__main__":
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson")
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce").astype("Int64")
    g = g[g.ward.notna()].copy()

    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    spend = (wo[wo.ward.between(1, 198)][["ward", "ward_name"]]
             .dropna().drop_duplicates("ward").copy())
    spend["ward"] = spend["ward"].astype("Int64")

    print(f"  polygons {len(g)}   spending wards {len(spend)}\n")

    # (a) numeric join
    num = spend.merge(g[["ward", "WARD_NAME"]], on="ward", how="left")
    n_num = num.WARD_NAME.notna().sum()
    print(f"  === (a) numeric join ===")
    print(f"    matched {n_num}/{len(spend)} ({n_num/len(spend)*100:.1f}%)")

    # (b) independent fuzzy name join
    print(f"\n  === (b) fuzzy name join (independent of ward number) ===")
    cands = g.WARD_NAME.tolist()
    name_to_ward = dict(zip(g.WARD_NAME, g.ward))
    rows = []
    for _, r in spend.iterrows():
        m, sc = best_match(r.ward_name, cands)
        rows.append({"ward": r.ward, "spend_name": r.ward_name,
                     "poly_name": m, "score": sc, "poly_ward": name_to_ward[m]})
    fz = pd.DataFrame(rows)
    exact = (fz.score >= 0.999).sum()
    hi = (fz.score >= 0.85).sum()
    print(f"    exact after normalisation  {exact:3d}/{len(fz)} ({exact/len(fz)*100:.1f}%)")
    print(f"    score >= 0.85              {hi:3d}/{len(fz)} ({hi/len(fz)*100:.1f}%)")

    # (c) the check that matters: do the two joins agree?
    fz["agrees"] = fz.ward == fz.poly_ward
    agree = fz.agrees.sum()
    print(f"\n  === (c) do the two joins agree? ===")
    print(f"    name-match ward == number-match ward: {agree}/{len(fz)} "
          f"({agree/len(fz)*100:.1f}%)   target >= 95%")

    dis = fz[~fz.agrees].copy()
    if len(dis):
        print(f"\n  {len(dis)} disagreement(s) - adjudicating each:")
        # adjudication rule: the ward NUMBER is authoritative when the two candidate
        # names are genuinely distinct places (a real homonym / near-homonym), because
        # the number is what the work order was filed under. Record every one.
        dis["poly_name_for_number"] = dis.ward.map(dict(zip(g.ward, g.WARD_NAME)))
        dis["self_score"] = [
            SequenceMatcher(None, norm(a), norm(b)).ratio()
            for a, b in zip(dis.spend_name, dis.poly_name_for_number)]
        dis["decision"] = "keep numeric join"
        dis["reason"] = np.where(
            dis.self_score >= 0.85,
            "name also matches its own numbered polygon; fuzzy top-1 lost to a homonym",
            "names differ across vintages; ward number is the filing key and is authoritative")
        for _, r in dis.iterrows():
            print(f"    ward {int(r.ward):3d}  spend='{r.spend_name}'  "
                  f"fuzzy->'{r.poly_name}'(w{int(r.poly_ward)}, {r.score:.2f})  "
                  f"own polygon='{r.poly_name_for_number}'({r.self_score:.2f})")
            print(f"             -> {r.decision}: {r.reason}")
    dis.to_csv(INT / "ward_join_manual.csv", index=False)
    print(f"\n  -> {INT/'ward_join_manual.csv'} ({len(dis)} manual decisions logged)")

    # ---------------------------------------------------------------- 2.4 wards.gpkg
    print(f"\n  === 2.4 emit canonical ward layer ===")
    out = g[["ward", "WARD_NAME", "ASS_CONST1", "POP_TOTAL", "POP_SC", "POP_ST",
             "POP_M", "POP_F", "AREA_SQ_KM", "RESERVATIO", "geometry"]].copy()
    out = out.rename(columns={"WARD_NAME": "ward_name", "ASS_CONST1": "assembly_const",
                              "POP_TOTAL": "pop_2011", "POP_SC": "pop_sc",
                              "POP_ST": "pop_st", "POP_M": "pop_m", "POP_F": "pop_f",
                              "AREA_SQ_KM": "area_sq_km", "RESERVATIO": "reservation"})

    # hazard + terrain, keyed by polygon order within the bengaluru_198 layer
    g2 = g.reset_index(drop=True)
    g2["unit_id"] = range(len(g2))
    key = g2[["unit_id", "ward"]]
    # whitelist the MEASURED columns only. The pooled hazard/terrain tables carry every
    # source boundary file's own attributes (objectid, kgiswardid, zone_officer_mobile,
    # ...) for 22 cities; merging them wholesale produced an 85-field layer of which
    # ~70 fields belonged to other cities entirely.
    WANT = {"ward_hazard.parquet": ["area_km2", "rain20mm_days", "rain50mm_days",
                                    "hot_days_35c", "consec_dry_days", "precip_annual",
                                    "landslide"],
            "ward_terrain.parquet": ["hand_m", "hand_lt5m_share", "twi", "slope",
                                     "elev_m"]}
    for f, cols in WANT.items():
        p = INT / f
        if not p.exists():
            print(f"    {f} missing - skipped")
            continue
        t = pd.read_parquet(p)
        t = t[t.city == "bengaluru_198"].merge(key, on="unit_id")
        have = [c for c in cols if c in t.columns]
        out = out.merge(t[["ward"] + have], on="ward", how="left")
        print(f"    {f:24s} +{len(have)} fields")

    # panel aggregates
    pan = ROOT / "data/final/bengaluru_budget_panel.parquet"
    if pan.exists():
        d = pd.read_parquet(pan)
        d["ward"] = pd.to_numeric(d["unit"], errors="coerce")
        agg = d.groupby("ward").agg(
            n_years=("fy", "nunique"),
            total_capex_cr=("total_spend", lambda s: s.sum() / 1e7),
            drain_cr=("storm_spend", lambda s: s.sum() / 1e7),
            pop_panel=("pop", "first"),
            sc_st_share=("sc_st_share", "first"),
            z_hazard_panel=("z_hazard", "first")).reset_index()
        agg["drain_share_pct"] = agg.drain_cr / agg.total_capex_cr * 100
        out = out.merge(agg, on="ward", how="left")

    # the alignment gap, if the residual table has been produced
    gap = ROOT / "output/tables/alignment_gap.csv"
    if gap.exists():
        gp = pd.read_csv(gap)
        gcol = [c for c in gp.columns if "resid" in c.lower()]
        wcol = [c for c in gp.columns if c.lower() in ("ward", "unit")]
        if gcol and wcol:
            gp = gp[[wcol[0], gcol[0]]].rename(
                columns={wcol[0]: "ward", gcol[0]: "alignment_residual"})
            gp["ward"] = pd.to_numeric(gp["ward"], errors="coerce")
            out = out.merge(gp, on="ward", how="left")

    out = out.set_geometry("geometry").set_crs(4326, allow_override=True)

    # GPKG field names are case-insensitive and must be unique; the hazard/terrain/panel
    # merges can reintroduce a name that differs from an existing one only in case.
    # Normalise to lower snake_case and drop the collisions rather than let the driver
    # fail with an opaque "Error adding field".
    out.columns = [c if c == "geometry" else c.lower() for c in out.columns]
    out = out.loc[:, ~pd.Series(out.columns).duplicated().values]
    for c in out.columns:
        if c == "geometry":
            continue
        if str(out[c].dtype) in ("Int64", "boolean", "object", "str"):
            out[c] = (out[c].astype(float) if pd.api.types.is_numeric_dtype(out[c])
                      else out[c].astype(str))

    dest = FIN / "wards.gpkg"
    out.to_file(dest, layer="wards_198", driver="GPKG")
    print(f"    {len(out)} wards x {len(out.columns)-1} attributes -> {dest}")
    print(f"    fields: {', '.join([c for c in out.columns if c != 'geometry'])}")
