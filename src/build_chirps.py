"""
Time-varying extreme-rainfall hazard from CHIRPS daily (plan item 3.2).

WHY THIS EXISTS. Everything else in the hazard block is time-INVARIANT: terrain does not
move, and the CCKP climate layers are 0.25 deg (~25 km), which inside a single city is one
number repeated across every ward. That forces the whole study into a cross-section - you
can never put in a ward fixed effect, because the hazard variable would be collinear with
it. A reviewer's first question is therefore "is this just ward wealth?", and with a
cross-section the only answer is a controls argument.

CHIRPS daily is 0.05 deg (~5.5 km) and runs 1981-present. Two things follow:

  * TIME variation. Extreme-rain days differ year to year, so the panel supports
    ward FE + year FE and asks whether a ward that gets an unusually wet year sees its
    drainage budget respond. That is a materially stronger design than the cross-section.

  * SOME space variation. Bengaluru spans ~50 km, so ~9x9 CHIRPS cells. The 198 wards
    land in roughly 60-70 distinct cells. That is real within-city variation, but it is
    NOT ward-resolution: wards smaller than 5.5 km share a pixel, and the mean BBMP ward
    is 3.5 km2. The honest statement is that CHIRPS resolves neighbourhood-scale rainfall,
    terrain resolves ward-scale susceptibility, and the two are complements. This script
    does not pretend otherwise - it reports how many wards share a pixel.

Extraction: each ward is burned onto the CHIRPS grid (all_touched, so a sub-pixel ward
still picks up the cell it sits in) and the day's value is the mean of its cells. Wards
that still capture no cell fall back to centroid sampling; the count is printed.

Source: data.chc.ucsb.edu, public HTTP, no credentials.
"""
import gzip
import io
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.features import rasterize
from rasterio.windows import from_bounds

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
BOUND = ROOT / "data/raw/boundaries"
OUT = ROOT / "data/interim"
CACHE = ROOT / "data/raw/chirps"
CACHE.mkdir(parents=True, exist_ok=True)

BASE = ("https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/"
        "{y}/chirps-v2.0.{y}.{m:02d}.{d:02d}.tif.gz")
INDIA = (68.0, 6.0, 98.0, 38.0)
FY_FIRST, FY_LAST = 2013, 2022           # Indian FY: Apr y -> Mar y+1


def load_units():
    """Every ward polygon, in the same order build_hazard.py assigns unit_id."""
    frames = []
    for f in sorted(BOUND.glob("*.geojson")):
        try:
            g = gpd.read_file(f)
        except Exception:
            continue
        if g.crs is None:
            g = g.set_crs(4326)
        g = g.to_crs(4326)
        minx, miny, _, _ = g.total_bounds
        if abs(minx) > 180 or abs(miny) > 90:            # Web Mercator mislabelled 4326
            g = g.set_crs(3857, allow_override=True).to_crs(4326)
            minx, miny, _, _ = g.total_bounds
        if not (68 <= minx <= 98 and 6 <= miny <= 38) and (68 <= miny <= 98 and 6 <= minx <= 38):
            from shapely.ops import transform as st
            g["geometry"] = g.geometry.map(lambda gg: st(lambda x, y, z=None: (y, x), gg))
        g = g.reset_index(drop=True)
        g["city"] = f.stem
        g["unit_id"] = range(len(g))
        frames.append(g[["city", "unit_id", "geometry"]])
    return pd.concat(frames, ignore_index=True)


def grid_geometry():
    """Fetch one day to learn the India window's transform and shape."""
    b = gzip.decompress(requests.get(BASE.format(y=2020, m=7, d=15), timeout=120).content)
    with rasterio.open(io.BytesIO(b)) as src:
        w = from_bounds(*INDIA, src.transform)
        return src.window_transform(w), src.read(1, window=w).shape, w


def fetch_day(dt):
    """Return the India window for one date, or None. Cached on disk as a small .npy."""
    cp = CACHE / f"{dt:%Y%m%d}.npy"
    if cp.exists():
        try:
            return np.load(cp)
        except Exception:
            cp.unlink(missing_ok=True)
    url = BASE.format(y=dt.year, m=dt.month, d=dt.day)
    for _ in range(3):
        try:
            r = requests.get(url, timeout=(15, 180))
            if r.status_code != 200:
                return None
            with rasterio.open(io.BytesIO(gzip.decompress(r.content))) as src:
                w = from_bounds(*INDIA, src.transform)
                a = src.read(1, window=w).astype("float32")
            a[a < 0] = np.nan                       # CHIRPS nodata is -9999
            np.save(cp, a)
            return a
        except Exception:
            continue
    return None


if __name__ == "__main__":
    units = load_units()
    print(f"  {len(units):,} ward polygons across {units.city.nunique()} layers")

    transform, shape, _ = grid_geometry()
    print(f"  CHIRPS India window {shape} at 0.05 deg (~5.5 km)")

    # burn each ward onto the grid; id 0 is reserved for "no ward"
    shapes = [(geom, i + 1) for i, geom in enumerate(units.geometry)]
    idx = rasterize(shapes, out_shape=shape, transform=transform, fill=0,
                    all_touched=True, dtype="int32")
    counts = np.bincount(idx.ravel(), minlength=len(units) + 1)

    # wards that captured no cell -> centroid fallback
    missing = np.where(counts[1:] == 0)[0]
    cen_rc = {}
    if len(missing):
        inv = ~transform
        for i in missing:
            c = units.geometry.iloc[i].centroid
            col, row = inv * (c.x, c.y)
            r, cc = int(row), int(col)
            if 0 <= r < shape[0] and 0 <= cc < shape[1]:
                cen_rc[i] = (r, cc)
    print(f"  burned: {int((counts[1:] > 0).sum()):,} wards captured >=1 cell; "
          f"{len(cen_rc):,} fall back to centroid; "
          f"{len(missing)-len(cen_rc)} outside the India window")

    # how many wards share a pixel - the resolution caveat, measured not asserted
    blr = units.index[units.city == "bengaluru_198"].tolist()
    if blr:
        cells = {}
        for i in blr:
            key = tuple(sorted(np.flatnonzero(idx.ravel() == i + 1)[:50].tolist()))
            cells.setdefault(key, []).append(i)
        print(f"  Bengaluru: {len(blr)} wards occupy {len(cells)} distinct cell "
              f"footprints ({len(cells)/len(blr)*100:.0f}% distinct)")

    flat = idx.ravel()
    order = np.argsort(flat, kind="stable")
    sorted_ids = flat[order]
    starts = np.searchsorted(sorted_ids, np.arange(len(units) + 2))

    days = []
    d0, d1 = date(FY_FIRST, 4, 1), date(FY_LAST + 1, 3, 31)
    d = d0
    while d <= d1:
        days.append(d)
        d += timedelta(days=1)
    print(f"  {len(days):,} days, {d0} -> {d1}\n")

    n = len(units)
    acc = {k: np.zeros((FY_LAST - FY_FIRST + 1, n), dtype="float64")
           for k in ["r20", "r50", "total", "maxday", "wet"]}
    ndays = np.zeros(FY_LAST - FY_FIRST + 1)

    def fy_of(dt):
        return (dt.year if dt.month >= 4 else dt.year - 1) - FY_FIRST

    done = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for dt, a in zip(days, ex.map(fetch_day, days)):
            done += 1
            if done % 250 == 0:
                print(f"    {done:,}/{len(days):,} days", flush=True)
            if a is None:
                continue
            f = fy_of(dt)
            ndays[f] += 1
            av = a.ravel()[order]
            vals = np.full(n, np.nan)
            for i in range(n):
                s, e = starts[i + 1], starts[i + 2]
                if e > s:
                    seg = av[s:e]
                    seg = seg[np.isfinite(seg)]
                    if seg.size:
                        vals[i] = seg.mean()
                elif i in cen_rc:
                    r, c = cen_rc[i]
                    v = a[r, c]
                    if np.isfinite(v):
                        vals[i] = v
            ok = np.isfinite(vals)
            acc["r20"][f][ok] += (vals[ok] > 20)
            acc["r50"][f][ok] += (vals[ok] > 50)
            acc["total"][f][ok] += vals[ok]
            acc["wet"][f][ok] += (vals[ok] > 1)
            acc["maxday"][f][ok] = np.maximum(acc["maxday"][f][ok], vals[ok])

    rows = []
    for fi, fy in enumerate(range(FY_FIRST, FY_LAST + 1)):
        rows.append(pd.DataFrame({
            "city": units.city.values, "unit_id": units.unit_id.values, "fy": fy,
            "chirps_r20_days": acc["r20"][fi], "chirps_r50_days": acc["r50"][fi],
            "chirps_annual_mm": acc["total"][fi], "chirps_wet_days": acc["wet"][fi],
            "chirps_max_1day_mm": acc["maxday"][fi], "chirps_days_covered": ndays[fi]}))
    t = pd.concat(rows, ignore_index=True)
    t.loc[t.chirps_annual_mm == 0, [c for c in t.columns if c.startswith("chirps_")]] = np.nan
    t.to_parquet(OUT / "ward_chirps.parquet", index=False)

    b = t[t.city == "bengaluru_198"]
    print(f"\n  === Bengaluru, the variation this unlocks ===")
    yr = b.groupby("fy").agg(r20=("chirps_r20_days", "mean"),
                             mm=("chirps_annual_mm", "mean"),
                             sd=("chirps_r20_days", "std"))
    for fy, r in yr.iterrows():
        print(f"    FY{fy}  mean {r.r20:5.1f} days >20mm  (between-ward sd {r.sd:4.2f})  "
              f"{r.mm:6.0f} mm")
    wsd = b.groupby("unit_id").chirps_r20_days.mean().std()
    ysd = yr.r20.std()
    print(f"\n    between-ward sd (time-averaged): {wsd:.2f} days")
    print(f"    between-year sd (ward-averaged):  {ysd:.2f} days")
    print(f"    -> the YEAR dimension carries {ysd/(wsd+1e-9):.1f}x the variation of the "
          f"ward dimension, which is exactly why this is the ward-FE instrument and "
          f"terrain stays the cross-sectional one.")
    print(f"\n  {len(t):,} unit-years -> {OUT/'ward_chirps.parquet'}")
