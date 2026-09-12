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
    d["fy"] = d["fy"].map(fy_to_int)
    d["storm_spend"] = pd.to_numeric(d["rs_lakh"], errors="coerce") * 1e5
    g = (d.dropna(subset=["unit", "fy"])
           .groupby(["unit", "fy"]).storm_spend.sum().reset_index())
    g["city"] = "surat"
    return g


def bengaluru():
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    g = (w[w.is_medium].groupby(["ward", "fy"]).amount.sum()
         .rename("storm_spend").reset_index().rename(columns={"ward": "unit"}))
    g["unit"] = g["unit"].astype(int).astype(str)
    g["city"] = "bengaluru"
    return g


# Surat is deliberately excluded: its published polygons are 30 WARDS while its budget
# reports by 9 ZONES, and no ward->zone crosswalk is published. Joining them would be a
# guess, so the Surat spending panel is retained but left unjoined.
HAZ_LAYER = {"bengaluru": "bengaluru_198", "chennai": "chennai_zone",
             "pune": "pune_admin"}


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
    return panel.merge(hz, on=["city", "unit"], how="inner")


if __name__ == "__main__":
    parts = [p for p in [bengaluru(), pune(), chennai(), surat()] if p is not None]
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
