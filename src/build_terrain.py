"""
Per-ward terrain hazard: HAND, TWI and slope from the free Copernicus DEM 30 m.

WHY THIS EXISTS. The CCKP climate layers are 0.25 deg (~25 km). Extracted per ward they
are near-constant inside a city - Bengaluru's 198 wards get rain20mm values with a
standard deviation of 0.1 on a mean of 3.9. That is the scale problem this project set
out to document, and it means CCKP CANNOT be the within-city hazard variable.

Terrain can. HAND (Height Above Nearest Drainage) is the standard free proxy for pluvial
flood susceptibility: cells sitting low relative to the drainage network they drain into
are where water collects. It varies at 30 m, which is the resolution the question needs.

  HAND  low  -> close to the drainage network vertically -> floods
  TWI   high -> large upslope area, flat -> water accumulates
  slope low  -> ponding rather than runoff

Source: Copernicus DEM GLO-30, public S3, no credentials.
"""
import math
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np

# COMPATIBILITY SHIM - must run BEFORE pysheds is imported.
# pysheds still calls np.in1d, which numpy removed in 2.0 (it was deprecated in 1.25
# in favour of np.isin). Without this every city fails with
#   AttributeError: module 'numpy' has no attribute 'in1d'
# and pandas.concat then dies with "No objects to concatenate", which hides the real
# cause. np.isin is the drop-in replacement; for 1-D inputs they are identical.
if not hasattr(np, "in1d"):
    np.in1d = np.isin

import pandas as pd
import rasterio
import requests
from rasterio.merge import merge as rio_merge
from rasterio.mask import mask as rio_mask

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
BOUND = ROOT / "data/raw/boundaries"
DEM = ROOT / "data/raw/dem"
OUT = ROOT / "data/interim"
DEM.mkdir(parents=True, exist_ok=True)

S3 = "https://copernicus-dem-30m.s3.amazonaws.com"


def tile_name(lat, lon):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return (f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_"
            f"{ew}{abs(lon):03d}_00_DEM")


def fetch_tiles(bounds, pad=0.1):
    minx, miny, maxx, maxy = bounds
    got = []
    for lat in range(math.floor(miny - pad), math.ceil(maxy + pad)):
        for lon in range(math.floor(minx - pad), math.ceil(maxx + pad)):
            t = tile_name(lat, lon)
            dest = DEM / f"{t}.tif"
            if not dest.exists():
                url = f"{S3}/{t}/{t}.tif"
                try:
                    r = requests.get(url, timeout=(15, 300))
                    if r.status_code != 200:
                        continue
                    dest.write_bytes(r.content)
                except Exception:
                    continue
            if dest.exists():
                got.append(dest)
    return got


def terrain_stats(gdf, city):
    tiles = fetch_tiles(gdf.total_bounds)
    if not tiles:
        return None
    srcs = [rasterio.open(t) for t in tiles]
    arr, transform = rio_merge(srcs)
    crs = srcs[0].crs
    for s in srcs:
        s.close()
    dem = arr[0].astype("float32")
    dem[dem < -1000] = np.nan

    from pysheds.grid import Grid
    tmp = DEM / f"_merged_{city}.tif"
    prof = {"driver": "GTiff", "height": dem.shape[0], "width": dem.shape[1],
            "count": 1, "dtype": "float32", "crs": crs, "transform": transform,
            "nodata": np.nan}
    with rasterio.open(tmp, "w", **prof) as d:
        d.write(np.nan_to_num(dem, nan=-9999), 1)

    grid = Grid.from_raster(str(tmp))
    elev = grid.read_raster(str(tmp))
    pit = grid.fill_pits(elev)
    flooded = grid.fill_depressions(pit)
    infl = grid.resolve_flats(flooded)
    fdir = grid.flowdir(infl)
    acc = grid.accumulation(fdir)
    # drainage network = cells draining more than N upstream cells
    mask = acc > 200
    hand = grid.compute_hand(fdir=fdir, dem=infl, mask=mask)

    res_m = abs(transform.a) * 111320 * math.cos(math.radians(gdf.total_bounds[1]))
    slope = np.gradient(np.nan_to_num(np.asarray(infl), nan=0.0))
    slope = np.hypot(slope[0], slope[1]) / max(res_m, 1e-6)
    twi = np.log((np.asarray(acc) + 1) * res_m / (np.tan(np.arctan(slope)) + 1e-4))

    layers = {"hand_m": np.asarray(hand, dtype="float32"),
              "twi": twi.astype("float32"),
              "slope": slope.astype("float32"),
              "elev_m": dem}
    out = {}
    g = gdf.to_crs(crs)
    for name, lay in layers.items():
        lay = np.where(np.isfinite(lay), lay, np.nan)
        p = DEM / f"_lay_{city}_{name}.tif"
        with rasterio.open(p, "w", **{**prof, "dtype": "float32"}) as d:
            d.write(np.nan_to_num(lay, nan=-9999), 1)
        vals, lowshare = [], []
        with rasterio.open(p) as src:
            for geom in g.geometry:
                try:
                    a, _ = rio_mask(src, [geom], crop=True, nodata=-9999)
                    a = a[0].astype("float64")
                    a = a[a > -9998]
                    vals.append(float(np.nanmean(a)) if a.size else np.nan)
                    if name == "hand_m":
                        lowshare.append(float((a < 5).mean()) if a.size else np.nan)
                except Exception:
                    vals.append(np.nan)
                    if name == "hand_m":
                        lowshare.append(np.nan)
        out[name] = vals
        if name == "hand_m":
            out["hand_lt5m_share"] = lowshare
        p.unlink(missing_ok=True)
    tmp.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    rows = []
    for f in sorted(BOUND.glob("*.geojson")):
        city = f.stem
        try:
            g = gpd.read_file(f)
        except Exception:
            print(f"  {city:16s} SKIP (unreadable)")
            continue
        if g.crs is None:
            g = g.set_crs(4326)
        g = g.to_crs(4326)
        minx, miny, maxx, maxy = g.total_bounds
        if not (68 <= minx <= 98 and 6 <= miny <= 38) and (68 <= miny <= 98 and 6 <= minx <= 38):
            from shapely.ops import transform as st
            g["geometry"] = g.geometry.map(lambda gg: st(lambda x, y, z=None: (y, x), gg))
        try:
            stats = terrain_stats(g, city)
        except Exception as e:
            print(f"  {city:16s} FAILED: {type(e).__name__}: {str(e)[:70]}")
            continue
        if stats is None:
            print(f"  {city:16s} no DEM tiles")
            continue
        d = pd.DataFrame(stats)
        d.insert(0, "unit_id", range(len(g)))
        d.insert(0, "city", city)
        rows.append(d)
        print(f"  {city:16s} n={len(g):4d}  HAND mean {np.nanmean(d.hand_m):6.1f} m "
              f"(sd {np.nanstd(d.hand_m):5.1f})   "
              f"share<5m {np.nanmean(d.hand_lt5m_share):.2f}")

    t = pd.concat(rows, ignore_index=True)
    t.to_parquet(OUT / "ward_terrain.parquet", index=False)
    print(f"\n  {len(t):,} units -> {OUT/'ward_terrain.parquet'}")
