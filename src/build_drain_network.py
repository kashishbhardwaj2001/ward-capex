"""
Existing drainage network density per ward (plan item 3.4).

WHY IT MATTERS. The study's headline is that high-hazard wards get SMALLER total budgets.
The obvious alternative explanation is a stock story: maybe high-hazard wards already have
more drainage infrastructure, so they rationally need less new capital spending. Without a
measure of the existing stock, that story cannot be ruled out and a referee will raise it.

This adds the stock control. OpenStreetMap is the only free, pan-Indian, ward-resolution
source for drainage line-work: BBMP's own rajakaluve GIS is not published as open data,
and the state SDMA layers are PDF maps.

WHAT IT DOES AND DOES NOT MEASURE - stated plainly, because OSM completeness is the
weakness here:
  * It counts MAPPED drain / ditch / canal / stream / culvert line-work. Where a ward's
    network is unmapped it scores low, which is indistinguishable from genuinely having
    no drains.
  * OSM mapping effort correlates with affluence and centrality, so measurement error is
    almost certainly correlated with the outcome. That biases the control TOWARD finding
    that rich central wards have more drains.
  * That direction is the useful one: if the hazard-budget result survives a control that
    is biased in favour of the rival explanation, the rival explanation is weakened rather
    than confirmed. If it did not survive, that would be reported.
  * `natural=water` / riverbank polygons are excluded - they are water BODIES, not
    drainage capacity.

Source: Overpass API, ODbL, no credentials.
"""
import json
import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import LineString

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
BOUND = ROOT / "data/raw/boundaries"
OUT = ROOT / "data/interim"
CACHE = ROOT / "data/raw/osm_drains"
CACHE.mkdir(parents=True, exist_ok=True)

# kumi.systems first: it is materially less loaded than the main instance, which returns
# 504 on a city-sized bbox at busy times. Both are tried before a city is given up on.
# kumi.systems first: it is materially less loaded than the main instance, which returns
# 504 on a city-sized bbox at busy times. overpass.osm.jp was in this list and is dropped -
# it refuses connections outright, so it only ever contributed a misleading last-error
# message ("ConnectionError") that masked why the other two had failed.
ENDPOINTS = ["https://overpass.kumi.systems/api/interpreter",
             "https://overpass-api.de/api/interpreter"]

# BOTH public Overpass mirrors refuse a request that does not identify itself, and they
# refuse it in ways that look like something else: overpass-api.de returns 406 Not
# Acceptable, kumi.systems returns 429 with the actual reason in the body ("Please include
# a meaningful User-Agent string"). requests' default UA is what triggers this. Without
# this header most cities fail, the failures look like rate-limiting, and backing off
# harder does not help because the request is never going to be accepted.
HEADERS = {"User-Agent": ("ward-capex/1.0 (municipal climate-finance research; "
                          "https://github.com/ward-capex) python-requests"),
           "Accept": "application/json"}

# waterway classes that carry stormwater. `river` is included as a separate class because
# in Indian cities the "river" is frequently the primary storm drain (Mithi, Cooum, Adyar),
# but it is reported separately so it can be excluded if a reader disagrees.
CLASSES = {"drain": ["drain"], "ditch": ["ditch"], "canal": ["canal"],
           "stream": ["stream"], "river": ["river"]}
ALL = [v for vs in CLASSES.values() for v in vs]


def _one(q, label):
    """POST a single Overpass query, returning its JSON or None."""
    last = ""
    for ep in ENDPOINTS:
        for attempt in range(2):
            try:
                r = requests.post(ep, data={"data": q}, headers=HEADERS,
                                  timeout=(15, 240))
                if r.status_code == 200:
                    return r.json()
                last = f"{ep.split('/')[2]} HTTP {r.status_code}"
                # 429 = slow down. 504 = the query was too expensive for a loaded
                # server; retrying the SAME query harder does not help, which is what
                # tiling below is for.
                time.sleep(20 if r.status_code == 429 else 5)
            except Exception as e:
                last = f"{ep.split('/')[2]} {type(e).__name__}"
                time.sleep(5)
    print(f"      {label}: {last}")
    return None


def tiles(bbox, n):
    """Split a bbox into an n x n grid."""
    minx, miny, maxx, maxy = bbox
    dx, dy = (maxx - minx) / n, (maxy - miny) / n
    return [(minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy)
            for i in range(n) for j in range(n)]


def query(bbox, city):
    """Fetch a city's drainage line-work, tiling if the whole-city query is too big.

    WHY TILING RATHER THAN BACKING OFF HARDER. A city-sized bbox over a dense OSM area
    makes Overpass do a lot of work, and a loaded public instance answers 504 rather than
    finishing. That is not rate-limiting: the same query will 504 again no matter how long
    you wait between attempts, which is why the first version of this crawled for an hour
    and gave up on half the cities. Splitting the bbox into a grid turns one expensive
    query into several cheap ones that each complete comfortably.

    Ways crossing a tile boundary are returned by every tile they touch, so results are
    de-duplicated on OSM way id before use.
    """
    cp = CACHE / f"{city}.json"
    if cp.exists():
        try:
            return json.loads(cp.read_text())
        except Exception:
            cp.unlink(missing_ok=True)

    def build_q(b):
        s_, w_, n_, e_ = b[1], b[0], b[3], b[2]
        return (f'[out:json][timeout:120];('
                f'way["waterway"~"^({"|".join(ALL)})$"]({s_},{w_},{n_},{e_});'
                f'way["tunnel"="culvert"]({s_},{w_},{n_},{e_});'
                f');out geom;')

    for grid in (1, 2, 3, 4):
        parts, ok = [], True
        boxes = [bbox] if grid == 1 else tiles(bbox, grid)
        if grid > 1:
            print(f"    {city}: retrying as {grid}x{grid} = {len(boxes)} tiles")
        for k, b in enumerate(boxes):
            j = _one(build_q(b), f"{city} tile {k+1}/{len(boxes)}")
            if j is None:
                ok = False
                break
            parts.extend(j.get("elements", []))
            if grid > 1:
                time.sleep(1)
        if ok:
            seen, els = set(), []
            for e in parts:                      # a way spanning tiles comes back twice
                i = e.get("id")
                if i in seen:
                    continue
                seen.add(i)
                els.append(e)
            out = {"elements": els}
            cp.write_text(json.dumps(out))
            return out

    print(f"  {city:16s} QUERY FAILED at every tiling up to 4x4")
    return None


def to_lines(j):
    rows = []
    for el in (j or {}).get("elements", []):
        g = el.get("geometry")
        if not g or len(g) < 2:
            continue
        tags = el.get("tags", {})
        wt = tags.get("waterway")
        cls = wt if wt in ALL else ("culvert" if tags.get("tunnel") == "culvert" else None)
        if cls is None:
            continue
        rows.append({"cls": cls,
                     "geometry": LineString([(p["lon"], p["lat"]) for p in g])})
    return gpd.GeoDataFrame(rows, crs=4326) if rows else None


if __name__ == "__main__":
    out = []
    files = sorted(BOUND.glob("*.geojson"))
    for f in files:
        city = f.stem
        try:
            g = gpd.read_file(f)
        except Exception:
            continue
        if g.crs is None:
            g = g.set_crs(4326)
        g = g.to_crs(4326)
        minx, miny, _, _ = g.total_bounds
        if abs(minx) > 180 or abs(miny) > 90:
            g = g.set_crs(3857, allow_override=True).to_crs(4326)
            minx, miny, _, _ = g.total_bounds
        if not (68 <= minx <= 98 and 6 <= miny <= 38) and (68 <= miny <= 98 and 6 <= minx <= 38):
            from shapely.ops import transform as st
            g["geometry"] = g.geometry.map(lambda gg: st(lambda x, y, z=None: (y, x), gg))
        g = g.reset_index(drop=True)
        g["unit_id"] = range(len(g))

        j = query(g.total_bounds, city)
        lines = to_lines(j)
        if lines is None or lines.empty:
            print(f"  {city:16s} no OSM drainage line-work found")
            continue

        # metric CRS: the UTM zone under the city centroid
        lon = float(g.total_bounds[[0, 2]].mean())
        epsg = 32600 + int((lon + 180) // 6) + 1
        gm, lm = g.to_crs(epsg), lines.to_crs(epsg)
        gm["area_km2"] = gm.geometry.area / 1e6

        cut = gpd.overlay(lm, gm[["unit_id", "geometry"]], how="intersection",
                          keep_geom_type=False)
        cut["len_m"] = cut.geometry.length
        wide = (cut.pivot_table(index="unit_id", columns="cls", values="len_m",
                                aggfunc="sum").fillna(0.0))
        wide.columns = [f"osm_{c}_m" for c in wide.columns]
        wide["osm_drain_total_m"] = wide.sum(axis=1)
        # the narrow definition: engineered stormwater only, no natural watercourse
        eng = [c for c in wide.columns
               if c in ("osm_drain_m", "osm_ditch_m", "osm_canal_m", "osm_culvert_m")]
        wide["osm_drain_engineered_m"] = wide[eng].sum(axis=1) if eng else 0.0

        d = gm[["unit_id", "area_km2"]].merge(wide, on="unit_id", how="left").fillna(0.0)
        d["drain_density_m_km2"] = d.osm_drain_total_m / d.area_km2.clip(lower=1e-6)
        d["drain_eng_density_m_km2"] = d.osm_drain_engineered_m / d.area_km2.clip(lower=1e-6)
        d.insert(0, "city", city)
        out.append(d)
        zero = (d.osm_drain_total_m == 0).mean() * 100
        print(f"  {city:16s} n={len(d):4d}  {d.osm_drain_total_m.sum()/1000:8,.0f} km "
              f"mapped   median density {d.drain_density_m_km2.median():7,.0f} m/km2   "
              f"{zero:4.0f}% of wards have none mapped")
        time.sleep(2)

    t = pd.concat(out, ignore_index=True)
    t.to_parquet(OUT / "ward_drain_network.parquet", index=False)
    print(f"\n  {len(t):,} units -> {OUT/'ward_drain_network.parquet'}")

    b = t[t.city == "bengaluru_198"]
    if len(b):
        print(f"\n  === Bengaluru sanity ===")
        print(f"    mapped drainage line-work: {b.osm_drain_total_m.sum()/1000:,.0f} km "
              f"across {len(b)} wards")
        print(f"    engineered only:           {b.osm_drain_engineered_m.sum()/1000:,.0f} km")
        print(f"    BBMP's published rajakaluve network is ~842 km - OSM captures "
              f"{b.osm_drain_engineered_m.sum()/1000/842*100:.0f}% of that scale")
        print(f"    wards with zero mapped drains: "
              f"{int((b.osm_drain_total_m == 0).sum())}/{len(b)}")
