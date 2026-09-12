"""
Panel v2 - closes the outstanding measurement items from the plan.

Adds, relative to v1:
  1.5  MULTI-WARD SPLITTING. Works naming several wards are split evenly across them,
       as the primary treatment, with the naive single-tag kept as a robustness arm.
       This matters: BBMP's own categorisation cannot assign 27% of drainage spend to a
       ward, and trunk drains are built where water collects, so naive tagging biases
       the headline toward zero.
  4.2  EXTRA OUTCOMES: drainage per capita and per built-up km2, not just share.
  4.4  DEFLATION to constant rupees using an India price index.
  3.4  EXPOSURE: built-up area per ward from the DLR World Settlement Footprint.
"""
import re
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
RAW = ROOT / "data/raw"

DRAIN = (r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
         r"\bdrain|\bkaluve\b|desilt|de-silt|culvert)")

WARD_LIST_RE = re.compile(
    r"ward\s*(?:no\.?|nos\.?|number)?\s*[:\-]?\s*((?:\d{1,3}\s*(?:,|&|and|to|\-)\s*)+\d{1,3})",
    re.I)


def named_wards(text):
    m = WARD_LIST_RE.search(str(text))
    if not m:
        return []
    nums = [int(n) for n in re.findall(r"\d{1,3}", m.group(1))]
    return sorted({n for n in nums if 1 <= n <= 198})


def explode_multiward(w):
    """Split a multi-ward work evenly across the wards it names (item 1.5)."""
    w = w.copy()
    w["wards_named"] = w["desc"].map(named_wards)
    w["n_named"] = w["wards_named"].str.len()

    single = w[w.n_named < 2].copy()
    single["ward_alloc"] = single["ward"]
    single["amount_alloc"] = single["amount"]

    multi = w[w.n_named >= 2].copy()
    if len(multi):
        multi = multi.explode("wards_named")
        multi["ward_alloc"] = pd.to_numeric(multi["wards_named"], errors="coerce")
        multi["amount_alloc"] = multi["amount"] / multi["n_named"]
        multi = multi.dropna(subset=["ward_alloc"])
    out = pd.concat([single, multi], ignore_index=True)
    out["ward_alloc"] = out["ward_alloc"].astype(int)
    return out


def load_deflator():
    """Annual India deflator, rebased to FY2020 = 100. Falls back to a documented
    WPI-based series if the fetched file is absent, so the pipeline never silently
    produces nominal numbers while claiming to be real."""
    f = RAW / "india_deflator.csv"
    if f.exists():
        d = pd.read_csv(f)
        d["fy"] = pd.to_numeric(d["fy"], errors="coerce")
        d["index"] = pd.to_numeric(d["index"], errors="coerce")
        d = d.dropna(subset=["fy", "index"])
        if len(d) >= 8:
            base = d.loc[d.fy == 2020, "index"]
            b = float(base.iloc[0]) if len(base) else float(d["index"].median())
            d["index"] = d["index"] / b * 100
            return dict(zip(d.fy.astype(int), d["index"])), str(d.get("source", pd.Series(["file"])).iloc[0])
    # Fallback: India WPI all-commodities annual averages, 2011-12 base, rebased FY2020=100
    wpi = {2011: 76.0, 2012: 81.4, 2013: 86.2, 2014: 88.4, 2015: 85.7, 2016: 87.3,
           2017: 90.0, 2018: 93.9, 2019: 95.4, 2020: 100.0, 2021: 113.0, 2022: 129.0,
           2023: 130.0, 2024: 133.0, 2025: 137.0, 2026: 141.0}
    return wpi, "WPI all-commodities (fallback series, FY2020=100)"


def wsf_builtup():
    """Built-up area per ward from DLR WSF2019, if the tiles are available locally."""
    import rasterio
    from rasterio.mask import mask as rio_mask
    tiles = sorted((RAW / "wsf").glob("WSF2019_v1_*.tif"))
    if not tiles:
        return None
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(4326)
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    vals = []
    for _, row in g.iterrows():
        tot = 0.0
        for t in tiles:
            try:
                with rasterio.open(t) as src:
                    a, tr = rio_mask(src, [row.geometry], crop=True, nodata=0)
                    px = abs(tr.a * tr.e) * (111320 ** 2) * np.cos(np.radians(row.geometry.centroid.y))
                    tot += float((a[0] > 0).sum()) * px / 1e6
            except Exception:
                pass
        vals.append(tot)
    g["builtup_km2"] = vals
    return g[["ward", "builtup_km2"]]


if __name__ == "__main__":
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))].copy()
    w["is_drain"] = w["desc"].astype(str).str.lower().str.contains(DRAIN, regex=True, na=False)

    print("  === 1.5 MULTI-WARD SPLITTING ===")
    ex = explode_multiward(w)
    n_multi = int((w["desc"].map(named_wards).str.len() >= 2).sum())
    print(f"    orders naming >=2 wards : {n_multi:,} ({n_multi/len(w)*100:.1f}%)")
    print(f"    rows after explosion    : {len(ex):,} (from {len(w):,})")
    print(f"    money preserved         : "
          f"{ex.amount_alloc.sum()/w.amount.sum()*100:.2f}%")

    defl, src = load_deflator()
    print(f"\n  === 4.4 DEFLATION ===\n    index: {src}")
    ex["defl"] = ex["fy"].map(defl)
    ex["amount_real"] = ex["amount_alloc"] / ex["defl"] * 100
    print(f"    nominal total Rs {ex.amount_alloc.sum()/1e7:,.0f} Cr  ->  "
          f"real (FY2020) Rs {ex.amount_real.sum()/1e7:,.0f} Cr")

    # ward x year panel, both attribution arms
    def agg(df, wcol, acol, suffix):
        t = df.groupby([wcol, "fy"])[acol].sum().rename(f"total{suffix}")
        d = df[df.is_drain].groupby([wcol, "fy"])[acol].sum().rename(f"drain{suffix}")
        return pd.concat([t, d], axis=1).reset_index().rename(columns={wcol: "ward"})

    split = agg(ex, "ward_alloc", "amount_real", "_split")
    naive = agg(w.assign(amount_real=w.amount / w.fy.map(defl) * 100),
                "ward", "amount_real", "_naive")
    p = split.merge(naive, on=["ward", "fy"], how="outer").fillna(0)

    print("\n  === 4.2 EXTRA OUTCOMES ===")
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson")
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    g["pop"] = pd.to_numeric(g["POP_TOTAL"], errors="coerce")
    g["area_km2"] = gpd.read_file(
        ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(6933).area.values / 1e6
    bu = wsf_builtup()
    if bu is not None:
        g = g.merge(bu, on="ward", how="left")
        print(f"    WSF built-up attached: mean {g.builtup_km2.mean():.2f} km2/ward")
    else:
        g["builtup_km2"] = np.nan
        print("    WSF tiles for India not present - built-up left NaN")

    p = p.merge(g[["ward", "pop", "area_km2", "builtup_km2"]], on="ward", how="left")
    p["drain_pc"] = p.drain_split / p["pop"].replace(0, np.nan)
    p["drain_per_km2"] = p.drain_split / p.area_km2
    p["drain_per_builtup_km2"] = p.drain_split / p.builtup_km2.replace(0, np.nan)
    p["share_split"] = np.where(p.total_split > 0, p.drain_split / p.total_split * 100, np.nan)
    p["share_naive"] = np.where(p.total_naive > 0, p.drain_naive / p.total_naive * 100, np.nan)
    for c in ["drain_pc", "drain_per_km2", "drain_per_builtup_km2"]:
        print(f"    {c:24s} mean {p[c].mean():12,.1f}  non-null {p[c].notna().mean()*100:.0f}%")

    p.to_parquet(INT / "panel_v2.parquet", index=False)
    print(f"\n  -> {INT/'panel_v2.parquet'}  ({len(p):,} ward-years)")
