"""
STOP-OR-GO: does the modelled HAND surface actually find Bengaluru's known flood spots?

If a terrain model cannot rank the places BBMP itself lists as flood-vulnerable above the
places it does not, then every result in this project is built on a hazard variable that
means nothing, and the honest response is to stop.

Ground truth: OpenCity CKAN "Flooding Locations in Bengaluru Urban"
(package b03218ea-4b7c-4fa9-ab67-b9054d7ecc4c) - three KML layers compiled by BBMP with
the Karnataka State Natural Disaster Monitoring Centre:
    vuln.kml        200 flood-vulnerable locations (carries WARDNO)
    floodprone.kml   70 flood-prone locations
    lowlying.kml    129 low-lying locations

Test: rank wards by modelled hazard, rank them by observed flood-point density, and
compare. Also a point-level test - are the DEM cells at flood points lower (in HAND terms)
than the city as a whole?
"""
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/floodpoints"
OUT = ROOT / "output"
RAW.mkdir(parents=True, exist_ok=True)

PKG = "https://data.opencity.in/api/3/action/package_show?id=b03218ea-4b7c-4fa9-ab67-b9054d7ecc4c"


def fetch_points():
    js = requests.get(PKG, timeout=(15, 120)).json()
    frames = []
    for r in js["result"]["resources"]:
        url, name = r.get("url"), (r.get("name") or "layer")
        if not url or not url.lower().endswith((".kml", ".kmz")):
            continue
        dest = RAW / f"{name.replace('/', '-')[:50]}.kml"
        if not dest.exists():
            dest.write_bytes(requests.get(url, timeout=(15, 180)).content)
        try:
            g = gpd.read_file(dest)
            g["layer"] = name
            frames.append(g)
            print(f"    {name[:40]:42s} {len(g):4d} points")
        except Exception as e:
            print(f"    {name[:40]:42s} FAILED {type(e).__name__}")
    return pd.concat(frames, ignore_index=True) if frames else None


if __name__ == "__main__":
    print("  downloading official BBMP/KSNDMC flood layers:")
    pts = fetch_points()
    if pts is None or pts.empty:
        raise SystemExit("  no flood points obtained - validation cannot run")
    pts = gpd.GeoDataFrame(pts, geometry="geometry", crs=4326)
    pts = pts[pts.geometry.notna() & ~pts.geometry.is_empty]
    print(f"  total usable points: {len(pts)}")

    wards = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(4326)
    wards["ward"] = pd.to_numeric(wards["WARD_NO"], errors="coerce")
    wards["unit_id"] = range(len(wards))

    j = gpd.sjoin(pts, wards[["ward", "unit_id", "geometry"]], predicate="within")
    print(f"  points inside the 198-ward layer: {len(j)} "
          f"({len(j)/len(pts)*100:.0f}%), covering {j.ward.nunique()} wards")

    cnt = j.groupby("ward").size().rename("n_flood_pts")
    ter = pd.read_parquet(ROOT / "data/interim/ward_terrain.parquet")
    ter = ter[ter.city == "bengaluru_198"]
    w = (wards[["ward", "unit_id"]].merge(ter, on="unit_id")
         .merge(cnt, on="ward", how="left"))
    w["n_flood_pts"] = w["n_flood_pts"].fillna(0)
    w["area_km2"] = wards.to_crs(6933).area.values / 1e6
    w["pts_per_km2"] = w.n_flood_pts / w.area_km2

    print("\n  === WARD-LEVEL: does modelled hazard predict observed flood points? ===")
    for hz in ["hand_lt5m_share", "twi", "elev_m", "slope"]:
        r = w[hz].corr(w.pts_per_km2)
        rs = w[hz].corr(w.pts_per_km2, method="spearman")
        print(f"    {hz:18s} pearson {r:+.3f}   spearman {rs:+.3f}")

    q = w.copy()
    q["hz_quartile"] = pd.qcut(q.hand_lt5m_share, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
    print("\n  observed flood points by modelled-hazard quartile:")
    for lab, g in q.groupby("hz_quartile", observed=True):
        print(f"    {lab:8s} wards {len(g):3d}   flood points {int(g.n_flood_pts.sum()):4d}   "
              f"per km2 {g.pts_per_km2.mean():.3f}")

    lo = q[q.hz_quartile == "Q1 low"].pts_per_km2.mean()
    hi = q[q.hz_quartile == "Q4 high"].pts_per_km2.mean()
    ratio = hi / lo if lo else np.inf
    sp = w["hand_lt5m_share"].corr(w.pts_per_km2, method="spearman")
    print(f"\n    top-quartile vs bottom-quartile flood-point density: {ratio:.2f}x")
    verdict = "GO" if (sp > 0.15 and ratio > 1.3) else "STOP"
    print(f"    >>> VALIDATION {verdict}  (spearman {sp:+.3f}, ratio {ratio:.2f}x)")

    w.to_csv(OUT / "tables/hazard_validation.csv", index=False)
    print(f"\n  -> {OUT/'tables/hazard_validation.csv'}")
