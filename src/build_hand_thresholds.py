"""
Recompute Bengaluru's flood hazard at 1, 2, 3, 5 and 10 m, not just 5 m.

The headline hazard is "share of the ward lying within 5 m above its nearest drainage".
Five metres is defensible - it is the usual first cut in the HAND literature - but it is a
judgement call, and a result that exists only at 5 m is an artefact of that call rather
than a finding. This produces the whole ladder so the claim can be tested rather than
asserted.

Reuses the cached Copernicus DEM tiles, so it costs minutes rather than a fresh download.
Bengaluru only: it is the city the headline rests on.
"""
import math
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np

# pysheds still calls np.in1d, removed in numpy 2.0 - must precede the import
if not hasattr(np, "in1d"):
    np.in1d = np.isin

import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.merge import merge as rio_merge

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DEM = ROOT / "data/raw/dem"
OUT = ROOT / "data/interim"
THRESHOLDS = [1, 2, 3, 5, 10]

if __name__ == "__main__":
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(4326)
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")

    minx, miny, maxx, maxy = g.total_bounds
    tiles = []
    for lat in range(math.floor(miny), math.ceil(maxy)):
        for lon in range(math.floor(minx), math.ceil(maxx)):
            t = DEM / (f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif")
            if t.exists():
                tiles.append(t)
    if not tiles:
        raise SystemExit("  no cached DEM tiles - run src/build_terrain.py first")
    print(f"  {len(tiles)} cached DEM tiles")

    srcs = [rasterio.open(t) for t in tiles]
    arr, transform = rio_merge(srcs)
    crs = srcs[0].crs
    for s in srcs:
        s.close()
    dem = arr[0].astype("float32")
    dem[dem < -1000] = np.nan

    from pysheds.grid import Grid
    tmp = DEM / "_thr_blr.tif"
    prof = {"driver": "GTiff", "height": dem.shape[0], "width": dem.shape[1], "count": 1,
            "dtype": "float32", "crs": crs, "transform": transform, "nodata": np.nan}
    with rasterio.open(tmp, "w", **prof) as dst:
        dst.write(np.nan_to_num(dem, nan=-9999), 1)

    grid = Grid.from_raster(str(tmp))
    elev = grid.read_raster(str(tmp))
    infl = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(elev)))
    fdir = grid.flowdir(infl)
    acc = grid.accumulation(fdir)
    hand = grid.compute_hand(fdir=fdir, dem=infl, mask=acc > 200)
    print("  HAND computed")

    hp = DEM / "_thr_hand.tif"
    with rasterio.open(hp, "w", **prof) as dst:
        dst.write(np.nan_to_num(np.asarray(hand, dtype="float32"), nan=-9999), 1)

    gm = g.to_crs(crs)
    rows = []
    with rasterio.open(hp) as src:
        for ward, geom in zip(gm.ward, gm.geometry):
            try:
                a, _ = rio_mask(src, [geom], crop=True, nodata=-9999)
                a = a[0].astype("float64")
                a = a[a > -9998]
            except Exception:
                a = np.array([])
            r = {"ward": ward}
            for t in THRESHOLDS:
                r[f"hand_lt{t}m_share"] = float((a < t).mean()) if a.size else np.nan
            rows.append(r)

    t = pd.DataFrame(rows)
    t.to_parquet(OUT / "hand_thresholds_bengaluru.parquet", index=False)
    print(f"\n  {'threshold':12s} {'mean share':>11s} {'sd':>7s} {'distinct':>9s}")
    for th in THRESHOLDS:
        c = t[f"hand_lt{th}m_share"]
        print(f"  {f'< {th} m':12s} {c.mean():11.3f} {c.std():7.3f} {c.round(4).nunique():9d}")
    tmp.unlink(missing_ok=True)
    hp.unlink(missing_ok=True)
    print(f"\n  -> {OUT/'hand_thresholds_bengaluru.parquet'}")
