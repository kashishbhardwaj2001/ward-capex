"""Pull ward/zone polygons for every Indian city in the study."""
import json, sys
from pathlib import Path
import geopandas as gpd, requests

RAW = Path(__file__).resolve().parent.parent / "data/raw/boundaries"
RAW.mkdir(parents=True, exist_ok=True)
DM = "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master"

SOURCES = {
    # city            file                                        unit    name field(s)
    "bengaluru_198": (f"{DM}/Bangalore/BBMP_oldWards.geojson",     "ward", ["WARD_NO","WARD_NAME"]),
    "bengaluru_243": (f"{DM}/Bangalore/BBMP.geojson",              "ward", ["KGISWardNo","KGISWardName"]),
    "mumbai":        (f"{DM}/Mumbai/BMC_Wards.geojson",            "ward", ["name"]),
    "chennai_ward":  (f"{DM}/Chennai/Wards.geojson",               "ward", ["Ward_No","Zone_No","Zone_Name"]),
    "chennai_zone":  (f"{DM}/Chennai/Zones.geojson",               "zone", None),
    "ahmedabad":     (f"{DM}/Ahmedabad/Wards.geojson",             "ward", ["Name"]),
    "pune_admin":    (f"{DM}/Pune/pune-admin-wards_2017.geojson",  "ward", None),
    "delhi":         (f"{DM}/Delhi/Delhi_Wards.geojson",           "ward", ["Ward_No","Ward_Name"]),
    "kolkata":       (f"{DM}/Kolkata/kolkata.geojson",             "ward", ["WARD"]),
    "hyderabad":     (f"{DM}/Hyderabad/ghmc-wards.geojson",        "ward", None),
    "jaipur":        (f"{DM}/Jaipur/Jaipur_Wards.geojson",           "ward", None),
    "lucknow":       (f"{DM}/Lucknow/Lucknow_ward_boundary.geojson", "ward", None),
    "bhopal":        (f"{DM}/Bhopal/Bhopal_wards.geojson",           "ward", None),
    "coimbatore":    (f"{DM}/Coimbatore/Cbe2011Wards.geojson",       "ward", None),
    "kanpur":        (f"{DM}/Kanpur/Kanpur_city_wards.geojson",      "ward", None),
    "vijayawada":    (f"{DM}/Vijayawada/Vijayawada_Wards.geojson",   "ward", None),
    "bhubaneswar":   (f"{DM}/Bhubaneswar/BMC_Wards.GeoJSON",         "ward", None),
    "faridabad":     (f"{DM}/Faridabad/Faridabad_Wards.geojson",     "ward", None),
    "vadodara":      (f"{DM}/Vadodara/vardodara_wards.geojson",      "ward", None),
    "pcmc":          (f"{DM}/PCMC/pcmc-electoral-wards.geojson",     "ward", None),
    "nmmc":          (f"{DM}/NMMC/NMC_ElectoralWards.geojson",       "ward", None),
    "surat":         ("https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/wards-surat/wards_surat.geojson", "zone", None),
}

if __name__ == "__main__":
    rows = []
    for city, (url, unit, _) in SOURCES.items():
        dest = RAW / f"{city}.geojson"
        try:
            if not dest.exists():
                r = requests.get(url, timeout=(15, 180)); r.raise_for_status()
                dest.write_bytes(r.content)
            g = gpd.read_file(dest)
            cols = [c for c in g.columns if c != "geometry"]
            rows.append((city, unit, len(g), ", ".join(cols[:4])))
            print(f"  {city:16s} {unit:5s} n={len(g):4d}  props: {cols[:4]}")
        except Exception as e:
            print(f"  {city:16s} FAILED: {type(e).__name__}: {str(e)[:90]}")
    print(f"\n  {len(rows)} layers, {sum(r[2] for r in rows)} total units")
