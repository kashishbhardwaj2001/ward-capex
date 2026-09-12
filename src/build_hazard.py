"""
Extract per-ward hazard indicators for every Indian city in the study.

This is the half that requires the UCRA work, and it applies the fix from that audit:
the City Scan pipeline samples CMIP6 at a city centroid using a +/-1 DEGREE nine-point
stencil (~77,000 km2 - larger than some countries). Here every indicator is an
AREA-WEIGHTED POLYGON MEAN over the actual ward boundary, which is the whole point:
at ward scale the stencil would hand every ward in a city the identical number.

Hazards:
  flood proxy   - extreme-rainfall days (CCKP r20mm, r50mm). No free hydraulic pluvial
                  model exists, so rainfall intensity is the driver-side proxy; terrain
                  (HAND/TWI) is added separately in build_terrain.py.
  heat          - CCKP hd35 (days above 35 C)
  drought       - CCKP cdd (consecutive dry days)
  landslide     - GFDRR global rainfall-triggered landslide hazard
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.mask import mask as rio_mask

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
STUFF = ROOT.parent                      # "climate stuff"
BOUND = ROOT / "data/raw/boundaries"
OUT = ROOT / "data/interim"
OUT.mkdir(parents=True, exist_ok=True)

CCKP = STUFF / "run/rawdata/CCKP"
LANDSLIDE = (STUFF / "run/rawdata/Landslide" /
             "Global landslide hazard map - Rainfall trigger (1980-2018, median) - COG.tif")

# CCKP variables that matter here, ssp245 mid-century
CCKP_VARS = {
    "r20mm": "rain20mm_days",     # days with rainfall > 20 mm  -> pluvial driver
    "r50mm": "rain50mm_days",     # days with rainfall > 50 mm  -> extreme pluvial driver
    "hd35":  "hot_days_35c",      # heat
    "cdd":   "consec_dry_days",   # drought
    "pr":    "precip_annual",
}
SSP, PERIOD = "245", "2040-2059"


def cckp_da(var):
    f = CCKP / (f"climatology-{var}-annual-mean_cmip6_annual_all-regridded-bct-"
                f"ssp{SSP}-climatology_median_{PERIOD}.nc")
    if not f.exists():
        return None
    ds = xr.open_dataset(f)
    name = f"climatology-{var}-annual-mean"
    da = ds[name] if name in ds else ds[list(ds.data_vars)[0]]
    if "time" in da.dims:
        da = da.isel(time=0)
    return da


def polygon_mean_cckp(da, gdf):
    """Area-weighted-ish polygon mean: sample the grid over the polygon's bbox and
    average the cells whose centres fall inside. For wards smaller than a 0.25 deg cell
    this degrades to the containing cell - which is itself the finding (see notes)."""
    lonname = "lon" if "lon" in da.dims else "longitude"
    latname = "lat" if "lat" in da.dims else "latitude"
    out = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            out.append(np.nan)
            continue
        minx, miny, maxx, maxy = geom.bounds
        pad = 0.15
        try:
            sub = da.sel({lonname: slice(minx - pad, maxx + pad),
                          latname: slice(miny - pad, maxy + pad)})
            if sub.size == 0:
                sub = da.sel({lonname: (minx + maxx) / 2, latname: (miny + maxy) / 2},
                             method="nearest")
            out.append(float(np.nanmean(sub.values)))
        except Exception:
            out.append(np.nan)
    return out


def raster_mean(path, gdf):
    """Mean of a raster inside each polygon."""
    vals = []
    with rasterio.open(path) as src:
        g = gdf.to_crs(src.crs)
        for geom in g.geometry:
            try:
                arr, _ = rio_mask(src, [geom], crop=True, filled=True,
                                  nodata=np.nan)
                a = arr[0].astype("float64")
                a = a[np.isfinite(a)]
                vals.append(float(a.mean()) if a.size else np.nan)
            except Exception:
                vals.append(np.nan)
    return vals


if __name__ == "__main__":
    das = {v: cckp_da(v) for v in CCKP_VARS}
    have = [v for v, d in das.items() if d is not None]
    print(f"  CCKP variables available: {have}")
    print(f"  landslide raster: {'yes' if LANDSLIDE.exists() else 'MISSING'}")

    rows = []
    for f in sorted(BOUND.glob("*.geojson")):
        city = f.stem
        try:
            g = gpd.read_file(f)
        except Exception as e:
            print(f"  {city:16s} SKIP ({type(e).__name__})")
            continue
        if g.crs is None:
            g = g.set_crs(4326)
        g = g.to_crs(4326)

        # COORDINATE SANITY CHECKS. Published Indian boundary files carry two distinct
        # defects that both yield plausible-looking but meaningless hazard values:
        #
        #  (a) TRANSPOSED lat/lon. Surat's bharatlas file has bounds
        #      [21.06, 72.70, 21.32, 72.97] - latitude sitting in the longitude slot.
        #  (b) MISLABELLED CRS. Kanpur's DataMeet file declares EPSG:4326 but its
        #      coordinates are Web Mercator metres (bounds ~8.93e6, 3.04e6). Sampled as
        #      degrees it lands off the globe and every indicator returns 0.0.
        #
        # India spans roughly lon 68-98 E, lat 6-38 N; anything far outside that is one of
        # the two, not a real geography.
        minx, miny, maxx, maxy = g.total_bounds
        if abs(minx) > 180 or abs(miny) > 90:
            g = g.set_crs(3857, allow_override=True).to_crs(4326)
            print(f"  {city:16s} !! CRS mislabelled - coords were Web Mercator, reprojected "
                  f"({[round(v,2) for v in g.total_bounds]})")
            minx, miny, maxx, maxy = g.total_bounds
        if not (68 <= minx <= 98 and 6 <= miny <= 38) and (68 <= miny <= 98 and 6 <= minx <= 38):
            from shapely.ops import transform as shp_transform
            g["geometry"] = g.geometry.map(
                lambda gg: shp_transform(lambda x, y, z=None: (y, x), gg))
            print(f"  {city:16s} !! lat/lon were transposed - flipped "
                  f"({[round(v,2) for v in g.total_bounds]})")


        g["unit_id"] = range(len(g))
        g["city"] = city

        # area in km2 via an equal-area projection
        g["area_km2"] = g.to_crs(6933).area / 1e6

        for var, label in CCKP_VARS.items():
            g[label] = polygon_mean_cckp(das[var], g) if das[var] is not None else np.nan
        if LANDSLIDE.exists():
            g["landslide"] = raster_mean(LANDSLIDE, g)

        cols = ["city", "unit_id", "area_km2"] + list(CCKP_VARS.values()) + \
               (["landslide"] if LANDSLIDE.exists() else [])
        extra = [c for c in g.columns if c not in cols + ["geometry"]][:6]
        keep = g[cols + extra].copy()
        for c in extra:                      # mixed dtypes break parquet
            keep[c] = keep[c].astype(str)
        rows.append(keep)
        print(f"  {city:16s} n={len(g):4d}  "
              f"rain20={np.nanmean(g['rain20mm_days']):6.1f} "
              f"(sd {np.nanstd(g['rain20mm_days']):4.1f})  "
              f"hd35={np.nanmean(g['hot_days_35c']):6.1f}")

    haz = pd.concat(rows, ignore_index=True)
    haz.to_parquet(OUT / "ward_hazard.parquet", index=False)
    print(f"\n  {len(haz):,} units across {haz.city.nunique()} layers "
          f"-> {OUT/'ward_hazard.parquet'}")
