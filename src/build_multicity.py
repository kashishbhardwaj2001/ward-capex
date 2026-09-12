"""
Pool the sub-city stormwater spending panels across Indian cities and join to hazard.

Each city publishes at a different unit and in a different language, so this file does the
harmonisation:

  Bengaluru  ward   198   work orders, keyword-classified        FY2011-2026
  Pune       prabhag/zone project list, account code CE20E101    FY2016-2026
  Chennai    zone    15   D.P. code 412-40-11-00 / 230-54-*      FY2011-2026
  Surat      zone     9   account code 5682                      FY2018-2026
  Mumbai     division 3   functionary code 33                    FY2024-2026

A DELIBERATE CONSTRAINT: units are NOT comparable across cities - a Bengaluru ward is
~3.5 km2, a Chennai zone ~30 km2, a Mumbai division ~150 km2. Pooling them raw would mix
spatial supports. The pooled model therefore uses CITY FIXED EFFECTS and standardises
hazard WITHIN city, so identification is always from within-city variation and never from
comparing a ward to a zone.
"""
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "data/final"
OUT.mkdir(parents=True, exist_ok=True)


def fy_to_int(s):
    m = re.search(r"(\d{4})", str(s))
    return int(m.group(1)) if m else np.nan


def pune():
    """Pune stormwater projects are tagged to PRABHAG (electoral ward, 41-76 of them),
    but the only Pune polygons available are the 15 ADMIN ward offices. The ward-office
    budget sheet carries a `prabhag_list` column naming the constituent prabhags, which
    is exactly the crosswalk needed - so build it from there."""
    f = ROOT / "pune/pmc_swd_projects.csv"
    wf = ROOT / "pune/pmc_wardoffice.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d["prabhag"] = (d["prabhag_from_text"].fillna(d["ward_col"])
                    .astype(str).str.extract(r"(\d+)")[0])
    d = d.dropna(subset=["prabhag"])
    d["fy"] = d["year"].map(fy_to_int)

    xw = None
    if wf.exists():
        w = pd.read_csv(wf)
        rows = []
        for _, r in w.dropna(subset=["prabhag_list"]).iterrows():
            office = str(r["ward_office"])
            for n in re.findall(r"\d+", str(r["prabhag_list"])):
                rows.append({"prabhag": n, "ward_office": office})
        if rows:
            xw = pd.DataFrame(rows).drop_duplicates("prabhag")

    # Marathi ward-office name -> the English place name used on the polygons
    MR2EN = {
        "औंध": "Aundh", "कोथरूड": "Kothrud", "घोले": "Ghole Road", "वारजे": "Warje",
        "ढोले": "Dhole Patil", "नगररोड": "Nagar Road", "नगर रोड": "Nagar Road",
        "येरवडा": "Yerwada", "भवानी": "Bhavani Peth", "कसबा": "Kasba",
        "विश्रामबाग": "Vishrambaug", "बिबवेवाडी": "Bibwewadi",
        "सहकारनगर": "Sahakarnagar", "धनकवडी": "Dhankawadi",
        "हडपसर": "Hadapsar", "कोंढवा": "Kondhwa", "मुंढवा": "Hadapsar",
        "वानवडी": "Hadapsar", "टिळक": "Bibwewadi",
    }

    def to_en(x):
        for mr, en in MR2EN.items():
            if mr in str(x):
                return en
        return None

    if xw is not None and len(xw):
        d = d.merge(xw, on="prabhag", how="left")
        d["unit"] = d["ward_office"].map(to_en)
        d = d.dropna(subset=["unit"])
    else:
        d["unit"] = d["prabhag"]

    g = (d.groupby(["unit", "fy"]).provision_rs.sum().rename("storm_spend")
         .reset_index())
    g["city"] = "pune"
    return g


def chennai():
    for f in [ROOT / "out/chennai_gcc_stormwater_by_zone_2018-2025.csv",
              ROOT / "chennai/chennai_swd_zone_panel.csv"]:
        if not f.exists():
            continue
        d = pd.read_csv(f)
        if "zone" in d.columns and "v1" in d.columns:          # the out/ format
            # "Zone-VI THIRU-VI-KA NAGAR" -> "VI"; the polygon file's Zone_No is the
            # same Roman numeral, so this is the join key.
            d["unit"] = d["zone"].astype(str).str.extract(r"Zone-([IVX]+)\b")[0]
            d["fy"] = d["edition"].map(fy_to_int)
            d["storm_spend"] = pd.to_numeric(d["v1"], errors="coerce") * 1000
        else:                                                   # the panel format
            d = d[d.get("measure", "ACTUAL").astype(str).str.upper().str.contains("ACTUAL")]
            d["unit"] = d["zone_no"].astype(str)
            d["fy"] = d["fiscal_year"].map(fy_to_int)
            d["storm_spend"] = pd.to_numeric(d["amount_rs_lakh"], errors="coerce") * 1e5
        g = (d.dropna(subset=["unit", "fy"])
               .groupby(["unit", "fy"]).storm_spend.sum().reset_index())
        g["city"] = "chennai"
        return g
    return None


def surat():
    f = ROOT / "surat/surat_5682_zone_year_panel.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d = d[d["measure"].astype(str).str.contains("actual", case=False, na=False)]
    d["unit"] = d["zone"].astype(str)
    d = d[~d["unit"].isin(SURAT_DROP)]        # HQ is a cost centre, not a geography
    d["fy"] = d["fy"].map(fy_to_int)
    d["storm_spend"] = pd.to_numeric(d["rs_lakh"], errors="coerce") * 1e5
    g = (d.dropna(subset=["unit", "fy"])
           .groupby(["unit", "fy"]).storm_spend.sum().reset_index())
    g["city"] = "surat"
    return g


def ahmedabad():
    """AMC publishes a ward-tagged drainage project list (Gujarati budget books, parsed
    to ward + rupees). Ward names match the polygon layer's `Name` field once the leading
    ward number and case are normalised."""
    f = ROOT / "ahmedabad/amc_ward_drainage_projects.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d["unit"] = (d["ward"].astype(str).str.upper()
                 .str.replace(r"[^A-Z ]", " ", regex=True)
                 .str.replace(r"\s+", " ", regex=True).str.strip())
    d["fy"] = d["fy"].map(fy_to_int)
    d["storm_spend"] = pd.to_numeric(d["rs_crore"], errors="coerce") * 1e7
    g = (d.dropna(subset=["unit", "fy", "storm_spend"])
           .groupby(["unit", "fy"]).storm_spend.sum().reset_index())
    g["city"] = "ahmedabad"
    return g


def mumbai():
    """MCGM Ward Wise Books, recovered from an unlinked WebDAV folder tree on
    portal.mcgm.gov.in. Budget ESTIMATES (not audited actuals) but they carry BOTH the
    Storm Water Drains capital line AND ward total capital, which makes Mumbai the second
    city where the budget decomposition can be run."""
    f = ROOT / "data/raw/mumbai_ward_swd.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d = d[d["measure"] == "swd_capital_be"].copy()
    d["unit"] = d["ward"].astype(str).str.strip().str.upper()
    d["fy"] = d["fy"].map(fy_to_int)
    d["storm_spend"] = pd.to_numeric(d["amount_rs"], errors="coerce")
    g = (d.dropna(subset=["unit", "fy", "storm_spend"])
           .groupby(["unit", "fy"]).storm_spend.sum().reset_index())
    g["city"] = "mumbai"
    return g


def bengaluru():
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    g = (w[w.is_medium].groupby(["ward", "fy"]).amount.sum()
         .rename("storm_spend").reset_index().rename(columns={"ward": "unit"}))
    g["unit"] = g["unit"].astype(int).astype(str)
    g["city"] = "bengaluru"
    return g


# Surat's published polygons are 30 WARDS while its budget reports by 9 ZONES. It was
# excluded until a ward->zone crosswalk could be constructed; one now exists
# (data/raw/surat_ward_zone_weights.csv, built by sampling points inside each ward
# polygon against SMC's published zone boundaries, area weights summing to 1 per ward),
# so Surat is joined by aggregating ward hazard UP to the budget's zone unit.
#
# Direction matters: the budget unit is the zone, so the hazard must be coarsened to the
# zone, never the budget disaggregated to wards. A zone's hazard is the area-weighted
# mean of its constituent wards, weight = ward_area x (ward's area share in that zone).
HAZ_LAYER = {"bengaluru": "bengaluru_198", "chennai": "chennai_zone",
             "pune": "pune_admin", "ahmedabad": "ahmedabad",
             "mumbai": "mumbai"}

# SMC split its old "South" zone into South-A / South-B / South-East / South-West. Early
# budget books still report the undivided "South"; it is reconstructed as the union of
# the four. "HQ" is a headquarters cost centre, not a geography, and is dropped.
SURAT_LEGACY = {"South": ["South-A", "South-B", "South-East", "South-West"]}
SURAT_DROP = {"HQ"}


def surat_zone_hazard():
    """Area-weighted aggregation of Surat's 30 ward polygons onto its 9 budget zones."""
    wf = ROOT / "data/raw/surat_ward_zone_weights.csv"
    if not wf.exists():
        return None
    w = pd.read_csv(wf)
    haz = pd.read_parquet(INT / "ward_hazard.parquet")
    ter = pd.read_parquet(INT / "ward_terrain.parquet")
    h = haz.merge(ter, on=["city", "unit_id"], suffixes=("", "_t"))
    sub = h[h.city == "surat"].copy()
    if sub.empty:
        return None
    # ward_no is not carried on the pooled hazard table (it keeps only the attributes
    # shared across all 22 source layers), so read it back off the polygon file. unit_id
    # is polygon order, which is how build_hazard.py assigns it.
    import geopandas as gpd
    g = gpd.read_file(ROOT / "data/raw/boundaries/surat.geojson").reset_index(drop=True)
    g["unit_id"] = range(len(g))
    g["srt_ward"] = pd.to_numeric(g["wardcode"], errors="coerce")
    sub = sub.merge(g[["unit_id", "srt_ward"]], on="unit_id", how="left")
    if sub["srt_ward"].isna().all():
        return None
    # "zone" also collides - several boundary layers ship their own zone column - so
    # rename BOTH crosswalk keys to srt_* before touching the pooled table.
    w = w.rename(columns={"ward_no": "srt_ward", "zone": "srt_zone"})
    m = w.merge(sub, on="srt_ward", how="inner", suffixes=("", "_haz"))
    if m.empty:
        return None
    m["wt"] = m["area_km2"] * m["area_weight"]

    COLS = ["hand_lt5m_share", "hand_m", "twi", "slope", "elev_m"]
    def agg(gr):
        out = {c: np.average(gr[c], weights=gr.wt) for c in COLS
               if gr[c].notna().all() and gr.wt.sum() > 0}
        out["area_km2"] = gr.wt.sum()
        return pd.Series(out)
    z = m.groupby("srt_zone").apply(agg).reset_index()

    # reconstruct the pre-split "South"
    for legacy, parts in SURAT_LEGACY.items():
        pz = z[z.srt_zone.isin(parts)]
        if len(pz) == len(parts):
            row = {c: np.average(pz[c], weights=pz.area_km2) for c in COLS if c in pz}
            row["srt_zone"] = legacy
            row["area_km2"] = pz.area_km2.sum()
            z = pd.concat([z, pd.DataFrame([row])], ignore_index=True)

    z = z.rename(columns={"srt_zone": "unit"})
    z["city"] = "surat"
    print(f"    surat: 30 wards -> {len(z)} budget zones "
          f"(incl. reconstructed {list(SURAT_LEGACY)})")
    return z[["city", "unit"] + COLS + ["area_km2"]]


def attach_hazard(panel):
    haz = pd.read_parquet(INT / "ward_hazard.parquet")
    ter = pd.read_parquet(INT / "ward_terrain.parquet")
    h = haz.merge(ter, on=["city", "unit_id"], suffixes=("", "_t"))
    rows = []
    for city, layer in HAZ_LAYER.items():
        sub = h[h.city == layer].copy()
        if sub.empty:
            continue
        sub = sub.sort_values("unit_id").reset_index(drop=True)
        sub["city_key"] = city
        # positional join: unit_id order == polygon order. For Bengaluru we can do better
        # because ward numbers are on the polygons.
        if city == "bengaluru" and "WARD_NO" in sub.columns:
            sub["unit"] = sub["WARD_NO"].astype(str).str.replace(r"\.0$", "", regex=True)
        elif city == "chennai" and "Zone_No" in sub.columns:
            sub["unit"] = sub["Zone_No"].astype(str).str.strip()
        elif city == "mumbai" and "name" in sub.columns:
            sub["unit"] = sub["name"].astype(str).str.strip().str.upper()
        elif city == "ahmedabad" and "Name" in sub.columns:
            # "48 RAMOL HATHIJAN" -> "RAMOL HATHIJAN"
            sub["unit"] = (sub["Name"].astype(str)
                           .str.replace(r"^\d+\s*", "", regex=True)
                           .str.replace(r"[^A-Za-z ]", " ", regex=True)
                           .str.replace(r"\s+", " ", regex=True).str.upper().str.strip())
        elif city == "pune" and "name" in sub.columns:
            # Polygons are English ("Admin Ward 01 Aundh"); the budget sheet names its
            # ward offices in Marathi. Map on the Devanagari place name.
            sub["unit"] = sub["name"].astype(str).str.replace(
                r"^Admin Ward \d+\s*", "", regex=True).str.strip()
        else:
            sub["unit"] = (sub.index + 1).astype(str)
        rows.append(sub[["city_key", "unit", "hand_lt5m_share", "hand_m",
                         "twi", "slope", "elev_m", "area_km2"]])
    hz = pd.concat(rows, ignore_index=True).rename(columns={"city_key": "city"})
    sz = surat_zone_hazard()
    if sz is not None:
        hz = pd.concat([hz, sz], ignore_index=True)
    return panel.merge(hz, on=["city", "unit"], how="inner")


if __name__ == "__main__":
    parts = [p for p in [bengaluru(), pune(), chennai(), surat(), ahmedabad(),
                         mumbai()]
             if p is not None]
    panel = pd.concat(parts, ignore_index=True)
    panel = panel[panel.storm_spend > 0]
    print("  RAW sub-city stormwater spending panels:")
    for c, g in panel.groupby("city"):
        print(f"    {c:10s} {len(g):5,} unit-years | {g.unit.nunique():3d} units | "
              f"FY{int(g.fy.min())}-{int(g.fy.max())} | Rs {g.storm_spend.sum()/1e7:8,.0f} Cr")

    m = attach_hazard(panel)
    print(f"\n  joined to hazard: {len(m):,} unit-years across {m.city.nunique()} cities")
    for c, g in m.groupby("city"):
        print(f"    {c:10s} {len(g):5,} unit-years | {g.unit.nunique():3d} units matched | "
              f"hazard {g.hand_lt5m_share.mean():.3f} (sd {g.hand_lt5m_share.std():.3f})")

    # standardise hazard WITHIN city - never across
    m["z_hazard"] = m.groupby("city").hand_lt5m_share.transform(
        lambda s: (s - s.mean()) / s.std() if s.std() else 0)
    m["log_spend"] = np.log(m.storm_spend.clip(lower=1))
    m.to_parquet(OUT / "multicity_panel.parquet", index=False)
    print(f"\n  -> {OUT/'multicity_panel.parquet'}")
