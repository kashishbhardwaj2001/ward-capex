"""
Generate output/atlas.html from the actual analysis outputs (all six cities).

WHY THIS EXISTS. The atlas used to be a hand-maintained HTML file with 261 KB of Bengaluru
geometry and every headline number pasted in by hand. Two things followed, and both bit:

  * Its numbers went stale silently. Every time the panel grew - Ahmedabad, then Mumbai,
    then Surat - the prose and the embedded constants had to be edited by hand, and more
    than once they were not. The page claimed four cities and 1,946 units long after the
    project had six and 2,157.
  * It showed only Bengaluru. The replication section listed six cities as bars, but the
    map - the thing a reader actually looks at - had one city in it.

Generating the file fixes both by construction: the numbers come from output/tables/*.csv
and data/final/*.parquet, and the map carries every city that has a spending panel.

WHAT EACH CITY CAN SHOW, which is not the same everywhere and the page says so. Bengaluru
is the only city with ward-level TOTAL capital spending, census population and an official
flood-point inventory, so it alone gets a drainage share, an alignment gap and an equity
read-out. The other five have stormwater spending and terrain hazard, and the read-out
shows only what exists for them rather than rendering empty rows.

Geometry is simplified to ~40 m and coordinates rounded to 5 decimals (~1 m). That is far
below ward resolution and keeps the whole six-city page near half a megabyte, which matters
because this is a local file a reader opens directly with no server.
"""
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import numpy as np
import pandas as pd

from atlas_client import APP_JS, CHART_JS
from atlas_template import BODY, EXTRA_CSS, build_sections

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
FIN = ROOT / "data/final"
TAB = ROOT / "output/tables"
OUT = ROOT / "output/atlas.html"
STYLE = Path("/tmp/atlas_style.html")

LAYER = {"bengaluru": "bengaluru_198", "chennai": "chennai_zone", "pune": "pune_admin",
         "ahmedabad": "ahmedabad", "mumbai": "mumbai", "surat": "surat"}
LABEL = {"bengaluru": "Bengaluru", "chennai": "Chennai", "pune": "Pune",
         "ahmedabad": "Ahmedabad", "mumbai": "Mumbai", "surat": "Surat"}
UNIT_WORD = {"bengaluru": "ward", "mumbai": "ward", "ahmedabad": "ward",
             "chennai": "zone", "pune": "ward office", "surat": "zone"}

SIMPLIFY = 0.0004     # ~40 m, far below ward resolution
PREC = 5              # ~1 m


def fix_crs(g):
    """The two published-boundary defects this project keeps meeting."""
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
    return g


def dissolve_surat(g):
    """Surat publishes 30 election WARDS as polygons but budgets by 10 ZONES, so the map
    unit has to be built, not read. Each ward is assigned to the zone holding most of its
    area (from the ward->zone crosswalk) and the wards are dissolved into zone polygons.

    Two zones need care. The pre-split "South" is the union of South-A/B/East/West, which
    SMC's older budget books still report as one unit, so it is emitted as its own overlapping
    polygon rather than dropped - a reader looking at an early Surat year should see the unit
    that year's budget actually used. "HQ" is a cost centre with no geography and never
    appears here.
    """
    w = pd.read_csv(ROOT / "data/raw/surat_ward_zone_weights.csv")
    dom = (w.sort_values("area_weight", ascending=False)
           .drop_duplicates("ward_no")[["ward_no", "zone"]])
    g["ward_no"] = pd.to_numeric(g["wardcode"], errors="coerce")
    g = g.merge(dom, on="ward_no", how="left")
    g = g[g.zone.notna()]
    z = g.dissolve(by="zone").reset_index()[["zone", "geometry"]]

    south_parts = ["South-A", "South-B", "South-East", "South-West"]
    if set(south_parts).issubset(set(z.zone)):
        merged = z[z.zone.isin(south_parts)].union_all()
        z = pd.concat([z, gpd.GeoDataFrame({"zone": ["South"], "geometry": [merged]},
                                           crs=z.crs)], ignore_index=True)
    z["unit"] = z["zone"]
    z["nm"] = z["zone"].str.replace("-", " ") + " zone"
    return z


def unit_key(g, city):
    """Reproduce build_multicity.py's per-city unit id, so the join is the same one the
    regressions used rather than a second, subtly different one."""
    if city == "bengaluru" and "WARD_NO" in g.columns:
        return g["WARD_NO"].astype(str).str.replace(r"\.0$", "", regex=True)
    if city == "chennai" and "Zone_No" in g.columns:
        return g["Zone_No"].astype(str).str.strip()
    if city == "mumbai" and "name" in g.columns:
        return g["name"].astype(str).str.strip().str.upper()
    if city == "ahmedabad" and "Name" in g.columns:
        return (g["Name"].astype(str).str.replace(r"^\d+\s*", "", regex=True)
                .str.replace(r"[^A-Za-z ]", " ", regex=True)
                .str.replace(r"\s+", " ", regex=True).str.upper().str.strip())
    if city == "pune" and "name" in g.columns:
        return g["name"].astype(str).str.replace(r"^Admin Ward \d+\s*", "",
                                                 regex=True).str.strip()
    return pd.Series((g.index + 1).astype(str), index=g.index)


def pretty_name(g, city, unit):
    for c in ["WARD_NAME", "Name", "name", "Zone_Name", "zone_name", "wardname"]:
        if c in g.columns and g[c].notna().any():
            return (g[c].astype(str).str.replace(r"^\d+\s*", "", regex=True)
                    .str.strip().str.title())
    return unit


def round_geom(obj):
    if isinstance(obj, list):
        return [round_geom(x) for x in obj]
    if isinstance(obj, float):
        return round(obj, PREC)
    return obj


def build_cities():
    mc = pd.read_parquet(FIN / "multicity_panel.parquet")
    blr = pd.read_parquet(FIN / "bengaluru_final.parquet")
    blr["unit"] = blr["ward"].astype("Int64").astype(str)

    # THE ALIGNMENT GAP is computed in analyse_bengaluru.py and make_figures.py but never
    # written to a table, so reading one produced an all-empty column on the page. Compute
    # it here with the same definition make_figures uses: the residual from the line
    # relating drainage share to flood hazard. Negative = more hazard than money.
    gap = None
    if {"flood_hazard", "share_medium"}.issubset(blr.columns):
        g0 = blr.dropna(subset=["flood_hazard", "share_medium"]).copy()
        b1, b0 = np.polyfit(g0.flood_hazard, g0.share_medium, 1)
        g0["gap"] = g0.share_medium - (b0 + b1 * g0.flood_hazard)
        gap = g0[["unit", "gap"]]

    cities = {}
    for city, layer in LAYER.items():
        g = fix_crs(gpd.read_file(ROOT / f"data/raw/boundaries/{layer}.geojson"))
        g = g.reset_index(drop=True)
        if city == "surat":
            g = dissolve_surat(g)
        else:
            g["unit"] = unit_key(g, city)
            g["nm"] = pretty_name(g, city, g["unit"])

        p = mc[mc.city == city]
        agg = p.groupby("unit").agg(
            storm=("storm_spend", "sum"), hz=("z_hazard", "first"),
            hand=("hand_m", "first"), area=("area_km2", "first"),
            uy=("fy", "size"), fy0=("fy", "min"), fy1=("fy", "max")).reset_index()
        d = g.merge(agg, on="unit", how="inner")
        if d.empty:
            print(f"  {city:10s} SKIPPED - no unit matched the panel")
            continue

        if city == "bengaluru":
            d = d.merge(blr[["unit", "share_medium", "total", "drain_medium",
                             "POP_TOTAL", "POP_SC", "POP_ST"]], on="unit", how="left")
            if gap is not None:
                d = d.merge(gap[["unit", "gap"]], on="unit", how="left")

        d["geometry"] = d.geometry.simplify(SIMPLIFY).buffer(0)
        feats = []
        for _, r in d.iterrows():
            props = {"u": r.unit, "nm": str(r.nm)[:34],
                     "hz": None if pd.isna(r.hz) else round(float(r.hz), 3),
                     "storm_cr": round(float(r.storm) / 1e7, 2),
                     "hand": None if pd.isna(r.hand) else round(float(r.hand), 1),
                     "area": None if pd.isna(r.area) else round(float(r.area), 2),
                     "uy": int(r.uy)}
            props["spk"] = (round(props["storm_cr"] / props["area"], 2)
                            if props["area"] else None)
            if city == "bengaluru":
                for k, src in [("share", "share_medium"), ("gap", "gap")]:
                    v = r.get(src)
                    props[k] = None if pd.isna(v) else round(float(v), 2)
                tot = r.get("total")
                props["total_cr"] = None if pd.isna(tot) else round(float(tot) / 1e7, 1)
                pop = r.get("POP_TOTAL")
                props["pop"] = None if pd.isna(pop) else int(pop)
                sc, st_ = r.get("POP_SC"), r.get("POP_ST")
                props["scst"] = (round((float(sc) + float(st_)) / float(pop) * 100, 1)
                                 if pop and not pd.isna(sc) and not pd.isna(st_) else None)
            geo = json.loads(gpd.GeoSeries([r.geometry], crs=4326).to_json())
            feats.append({"type": "Feature",
                          "geometry": round_geom(geo["features"][0]["geometry"]),
                          "properties": props})

        b = d.total_bounds
        cities[city] = {
            "label": LABEL[city], "unitWord": UNIT_WORD[city], "n": len(d),
            "bounds": [round(float(x), 4) for x in b],
            "fy": [int(d.fy0.min()), int(d.fy1.max())],
            "storm_cr": round(float(d.storm.sum()) / 1e7, 0),
            "rich": city == "bengaluru",
            "features": feats}
        print(f"  {city:10s} {len(d):4d} units  FY{int(d.fy0.min())}-{int(d.fy1.max())}  "
              f"Rs {d.storm.sum()/1e7:7,.0f} Cr")
    return cities


def read_tables():
    """Every headline number, read from the CSV the analysis wrote."""
    R = {}

    def csv(n):
        p = TAB / n
        return pd.read_csv(p) if p.exists() else None

    bc = csv("budget_channel.csv")
    if bc is not None and "pct" in bc.columns:
        R["budget"] = bc.to_dict("records")

    mcr = csv("multicity_results.csv")
    if mcr is not None:
        per = mcr[mcr.get("scope", mcr.columns[0]).astype(str).str.contains("city|per", case=False, na=False)] \
            if "scope" in mcr.columns else mcr
        R["multicity_raw"] = mcr.to_dict("records")

    pol = ROOT / "data/raw/bbmp_councillors_2015.csv"
    blrf = FIN / "bengaluru_final.parquet"
    if pol.exists() and blrf.exists():
        pp = pd.read_csv(pol)
        pp["ward"] = pd.to_numeric(pp["ward"], errors="coerce")
        bb = pd.read_parquet(blrf)[["ward", "z_flood_hazard"]]
        j = pp.merge(bb, on="ward", how="inner")
        agg = (j.groupby("party").agg(n=("ward", "size"),
                                      hz=("z_flood_hazard", "mean")).reset_index())
        R["parties"] = [{"p": r.party, "n": int(r.n), "hz": round(float(r.hz), 3)}
                        for r in agg.itertuples() if r.n >= 5]

    # hazard_validation.csv is the PER-WARD table (198 rows), not the quartile summary the
    # ladder chart needs. Reading it straight through rendered 198 ward rows where four
    # quartiles belong - caught by an interaction test asserting the chart's row count, not
    # by looking at the page, because 198 thin bars still look like a chart.
    hv = csv("hazard_validation.csv")
    if hv is not None and "hand_lt5m_share" in hv.columns:
        hv = hv.copy()
        hv["q"] = pd.qcut(hv.hand_lt5m_share, 4,
                          labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"])
        g = (hv.groupby("q", observed=True)
             .agg(wards=("ward", "size"), pts=("n_flood_pts", "sum"),
                  density=("pts_per_km2", "mean")).reset_index())
        R["validation"] = [{"quartile": str(r.q), "wards": int(r.wards),
                            "pts": int(r.pts), "density": round(float(r.density), 3)}
                           for r in g.itertuples()]

    for key, fn in [("robust", "robustness.csv"), ("political", "political.csv"),
                    ("classifier", "classifier_validation.csv"),
                    ("falsification", "falsification_outcome_side.csv"),
                    ("contrasts", "falsification_contrasts.csv"),
                    ("stock", "stock_control.csv"),
                    ("wardfe", "ward_fe_rainfall.csv"),
                    ("throughput", "ward_fe_throughput.csv"),
                    ("selection", "selection_tests.csv")]:
        t = csv(fn)
        if t is not None:
            R[key] = t.to_dict("records")
    return R




def emit(cities, R):
    """Write the page to output/atlas.html and to site/index.html.

    Two copies deliberately: output/ is where the rest of the pipeline puts its artefacts
    and where a reader opening the repo will look, while site/ is the directory a static
    host is pointed at. Data is INLINED rather than fetched, so the identical file works
    opened from disk (file://, where fetch would be blocked) and served over HTTP.
    """
    style = STYLE.read_text() if STYLE.exists() else "<title>Ward Capital Atlas</title>"
    meta = R.get("meta", {})
    eyebrow = (f'{meta.get("n_cities", 6)} CITIES &middot; {meta.get("n_units", 283)} '
               f'SUB-CITY UNITS &middot; {meta.get("n_unit_years", 2088):,} UNIT-YEARS '
               f'&middot; {meta.get("n_orders", 68415):,} BBMP WORK ORDERS')
    body = BODY.replace("__EYEBROW__", eyebrow).replace("__SECTIONS__", build_sections(R))
    data = json.dumps({"cities": cities, "R": R}, separators=(",", ":"))
    js = APP_JS.replace("__DATA__", data).replace("__CHARTS__", CHART_JS)
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="description" content="Do Indian municipal capital budgets reach the '
            'wards most exposed to flooding? Ward-level evidence from six cities.">'
            + style + EXTRA_CSS + "</head><body>" + body + js + "</body></html>")
    OUT.write_text(html)
    # docs/ rather than site/: GitHub Pages will only serve a repository root or a folder
    # literally named docs, and serving straight from the repo means no build step and no
    # second deploy target to keep in sync.
    site = ROOT / "docs/index.html"
    site.parent.mkdir(exist_ok=True)
    site.write_text(html)
    return html


if __name__ == "__main__":
    print("  building six-city atlas from the analysis outputs\n")
    cities = build_cities()
    R = read_tables()

    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    mc = pd.read_parquet(FIN / "multicity_panel.parquet")
    R["meta"] = {
        "n_orders": int(len(w)), "total_cr": round(float(w.amount.sum()) / 1e7),
        "n_units": int(mc.groupby(["city", "unit"]).ngroups),
        "n_unit_years": int(len(mc)), "n_cities": int(mc.city.nunique()),
        "pool_cr": round(float(mc.storm_spend.sum()) / 1e7),
        "tiers": [{"t": t,
                   "cr": round(float(w.loc[w[f"is_{t}"], "amount"].sum()) / 1e7),
                   "pct": round(float(w.loc[w[f"is_{t}"], "amount"].sum()
                                      / w.amount.sum() * 100), 1)}
                  for t in ["narrow", "medium", "broad"]],
    }
    R["meta"]["elasticity"] = round(R["meta"]["tiers"][2]["cr"]
                                    / max(R["meta"]["tiers"][0]["cr"], 1), 1)

    payload = {"cities": cities, "R": R}
    html = emit(cities, R)
    print(f"\n  {len(cities)} cities, {sum(c['n'] for c in cities.values())} mapped units")
    print(f"  page: {len(html)/1024:,.0f} KB")
    print(f"    -> {OUT}")
    print(f"    -> {ROOT/'docs/index.html'}  (GitHub Pages root)")
