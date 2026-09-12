"""
Boundary-vintage cross-check (plan item 2.1).

The study fixes its analysis unit as the 198-ward (2012) BBMP delimitation. That choice is
only defensible if the alternatives have actually been looked at, so this script pulls
every published Bengaluru ward vintage it can reach and compares them.

THREE VINTAGES EXIST, not two:
  198  BBMP 2012   DataMeet BBMP_oldWards.geojson  - richest attributes, longest panel
  243  BBMP 2022   DataMeet BBMP.geojson           - the 2022 re-delimitation
  369  GBA  2025   bharatlas wards_bengaluru_gba   - the Greater Bengaluru Authority split
                                                     BBMP into FIVE corporations

The 369-ward GBA file is the one the plan flagged as "cross-check against the bharatlas
R2 bucket", and it materially changes how the panel's end date has to be justified: after
2025 "Bengaluru" is no longer one municipal budget at all, it is five. That is a hard stop
on extending the panel forward, and it is a better reason than "data ends here".

IT ALSO CONFIRMS A SYSTEMATIC DEFECT. The bharatlas Surat file ships with lat/lon
transposed; this script finds the Bengaluru-GBA file has the SAME defect
(bounds 12.8,77.5 -> 13.1,77.8 - latitude sitting in the longitude slot). Two of two
bharatlas files checked are transposed, so the coordinate guard in build_hazard.py /
build_terrain.py is not defensive coding against a one-off, it is handling this
publisher's normal output.
"""
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
BOUND = ROOT / "data/raw/boundaries"
REF = ROOT / "data/raw/boundaries_ref_gba.geojson"
GBA_URL = ("https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/"
           "admin/wards-bengaluru-gba/wards_bengaluru_gba.geojson")


def fix_coords(g, label):
    """The same guard the hazard pipeline applies, reported rather than silent."""
    note = "as published"
    if g.crs is None:
        g = g.set_crs(4326)
    g = g.to_crs(4326)
    minx, miny, maxx, maxy = g.total_bounds
    if abs(minx) > 180 or abs(miny) > 90:
        g = g.set_crs(3857, allow_override=True).to_crs(4326)
        note = "CRS MISLABELLED (Web Mercator as EPSG:4326) - reprojected"
        minx, miny, maxx, maxy = g.total_bounds
    if not (68 <= minx <= 98 and 6 <= miny <= 38) and (68 <= miny <= 98 and 6 <= minx <= 38):
        from shapely.ops import transform as st
        g["geometry"] = g.geometry.map(lambda gg: st(lambda x, y, z=None: (y, x), gg))
        note = "lat/lon TRANSPOSED - flipped"
    print(f"    {label:28s} {note}")
    return g


if __name__ == "__main__":
    if not REF.exists():
        print("  fetching the GBA vintage from the bharatlas bucket ...")
        REF.write_bytes(requests.get(GBA_URL, timeout=(15, 300)).content)

    print("  === coordinate integrity of each published vintage ===")
    layers = {}
    for label, path in [("198 BBMP 2012 (DataMeet)", BOUND / "bengaluru_198.geojson"),
                        ("243 BBMP 2022 (DataMeet)", BOUND / "bengaluru_243.geojson"),
                        ("369 GBA 2025 (bharatlas)", REF)]:
        if not path.exists():
            print(f"    {label:28s} MISSING")
            continue
        layers[label] = fix_coords(gpd.read_file(path), label)

    print("\n  === vintage comparison ===")
    print(f"  {'vintage':28s} {'n':>5s} {'area km2':>9s} {'median ward km2':>16s}")
    for label, g in layers.items():
        lon = float(g.total_bounds[[0, 2]].mean())
        gm = g.to_crs(32600 + int((lon + 180) // 6) + 1)
        a = gm.geometry.area / 1e6
        print(f"  {label:28s} {len(g):5d} {a.sum():9,.0f} {a.median():16.2f}")

    gba = layers.get("369 GBA 2025 (bharatlas)")
    if gba is not None and "Corporation" in gba.columns:
        print("\n  === what the GBA reorganisation actually did ===")
        # TOT_P ships as text in this file - summing it without coercion concatenates
        gba["pop_n"] = pd.to_numeric(gba["TOT_P"], errors="coerce")
        c = gba.groupby("Corporation").agg(wards=("ward_id", "size"),
                                           pop=("pop_n", "sum"))
        for k, r in c.iterrows():
            print(f"    {k:10s} {int(r.wards):4d} wards   pop {int(r['pop']):,}")
        print(f"    -> after 2025 there is no single 'Bengaluru' municipal budget;")
        print(f"       there are {len(c)}. The FY2013-2022 panel therefore ends at a real")
        print(f"       institutional boundary, not merely where the files stop.")

    print("\n  === does this change the choice of analysis unit? ===")
    print("    No - and now for a stated reason rather than by default:")
    print("      * 198 (2012) is the only vintage carrying ward-level 2011 census")
    print("        attributes, which the equity analysis needs.")
    print("      * It spans the full FY2013-2022 work-order corpus with one geography.")
    print("      * 243 (2022) is handled by the areal crosswalk as a robustness arm.")
    print("      * 369 (2025) post-dates the panel entirely and splits the city into five")
    print("        budget-issuing bodies, so it cannot be pooled with the earlier years.")
