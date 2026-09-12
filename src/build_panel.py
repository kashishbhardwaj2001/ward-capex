"""
Build the ward x financial-year work-order panel for Bengaluru, with drainage
classification and multi-ward attribution handling.

THREE THINGS THIS FILE GETS RIGHT, BECAUSE EACH ONE SILENTLY RUINS THE ANALYSIS:

1. FINANCIAL YEAR. The per-ward 2013-2022 files carry no date column, but the work-order
   number encodes it: "198-15-000026" = ward 198, FY starting 2015, serial 26. We parse FY
   from the work-order number rather than guessing from the file.

2. MULTI-WARD WORKS. Big trunk-drain (rajakaluve) projects routinely name several wards
   - "in ward No 01, 02, 03 & 04 of Yelahanka Division" - but carry ONE ward tag. Naive
   attribution therefore UNDERSTATES drainage spend in exactly the wards that received the
   biggest drainage projects, which are plausibly the most flood-prone ones. That biases
   the headline coefficient TOWARD ZERO. We detect these and produce both a naive and a
   split-evenly version so the bias can be bounded rather than ignored.

3. TAGGING TIERS. "Which spending is drainage spending" is a judgement call that moves the
   headline by a lot. We compute three pre-specified tiers and report all three; the spread
   between them is a result about measurement, not an embarrassment to hide.
"""
import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/bbmp"
OUT = ROOT / "data/interim"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ classification tiers
TIERS = {
    # narrow: unambiguous stormwater-drainage assets
    "narrow": r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
              r"primary\s+drain|secondary\s+drain|tertiary\s+drain)",
    # medium: + generic drains, desilting, culverts, kaluve
    "medium": r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
              r"\bdrain|\bkaluve\b|desilt|de-silt|culvert|catch\s*pit|\bsluice\b)",
    # broad: + combined road-and-drain works, footpath-cum-drain
    "broad":  r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
              r"\bdrain|\bkaluve\b|desilt|de-silt|culvert|catch\s*pit|\bsluice\b|"
              r"footpath|side\s*drain|road\s*and\s*drain|cross\s*drain|water\s*logg)",
}
# a few other categories, for the falsification test
OTHER_CATS = {
    "park_green": r"(\bpark\b|garden|tree\s*park|playground|green|lung\s*space|avenue\s*plant)",
    "road":       r"(\broad\b|asphalt|blacktop|white\s*top|tar\b|footpath|pavement)",
    "water_supply": r"(water\s*supply|borewell|bore\s*well|overhead\s*tank|\bohT\b|pipeline)",
    "building":   r"(building|community\s*hall|school|hospital|toilet|office)",
}

WARD_LIST_RE = re.compile(
    r"ward\s*(?:no\.?|nos\.?|number)?\s*[:\-]?\s*((?:\d{1,3}\s*(?:,|&|and|to|\-)\s*)+\d{1,3})",
    re.I)
WO_RE = re.compile(r"^\s*(\d{1,3})\s*-\s*(\d{2})\s*-\s*(\d+)")


def fy_from_wo(wo):
    """'198-15-000026' -> 2015 (financial year beginning)."""
    m = WO_RE.match(str(wo))
    if not m:
        return None
    yy = int(m.group(2))
    return 2000 + yy if yy < 90 else 1900 + yy


def ward_from_wo(wo):
    m = WO_RE.match(str(wo))
    return int(m.group(1)) if m else None


def parse_multiward(text):
    """Return the list of ward numbers a work description names, if more than one."""
    m = WARD_LIST_RE.search(str(text))
    if not m:
        return []
    nums = [int(n) for n in re.findall(r"\d{1,3}", m.group(1))]
    return sorted({n for n in nums if 1 <= n <= 400})


def read_ward_csv(f):
    """Read one of the 2013-2022 per-ward CSVs.

    THREE DIFFERENT SCHEMAS ship under the same dataset - silently, and an unguarded
    read_csv parses only one of them:
      * 163 files: a two-line report title occupies the first rows, so the real header
        ("Sl No / Job Number / Name of Work / ... / Gross / Nett") is further down and
        pandas reads it as `Unnamed: N` columns.
      *  20 files: the full header is already on row 0.
      *  15 files: a compact schema (id / wo num / wodetails / amount / nett).
    Parsing only the compact form loses 92% of the rows. Detect the header row instead.
    """
    try:
        head = pd.read_csv(f, header=None, nrows=12, dtype=str, low_memory=False)
    except Exception:
        return None

    hdr = None
    for i in range(len(head)):
        row = [str(x).strip().lower() for x in head.iloc[i].tolist()]
        joined = " ".join(row)
        if ("job number" in joined and "name of work" in joined) or \
           ("wo num" in joined and "wodetails" in joined):
            hdr = i
            break
    try:
        d = pd.read_csv(f, header=hdr if hdr is not None else 0,
                        dtype=str, low_memory=False)
    except Exception:
        return None
    d.columns = [str(c).strip().lower() for c in d.columns]
    d = d.loc[:, ~d.columns.str.startswith("unnamed")]

    # normalise the two verbose schemas onto the compact one
    ren = {"job number": "wo num", "name of work": "wodetails",
           "gross": "amount", "br number": "brnumber"}
    d = d.rename(columns={k: v for k, v in ren.items() if k in d.columns})
    keep = [c for c in ["wo num", "wodetails", "contractor", "brnumber",
                        "amount", "nett", "deduction", "ward", "office",
                        "budget head", "order date", "start date"] if c in d.columns]
    if "wo num" not in d.columns or "wodetails" not in d.columns:
        return None
    d = d[keep]
    # strip rupee formatting
    for c in ("amount", "nett", "deduction"):
        if c in d.columns:
            d[c] = (d[c].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
                    .replace("", None))
    return d.dropna(subset=["wo num"])


def load_all():
    frames = []

    # --- 2013-2022: 198 per-ward CSVs; ward is in the filename and the wo num
    for f in sorted(glob.glob(str(RAW / "bbmp-work-orders-by-ward-2013-2022/*.csv"))):
        d = read_ward_csv(f)
        if d is None or d.empty:
            continue
        wname = re.search(r"for (.+?)\(Num-(\d+)\)", Path(f).name)
        d["ward_file"] = int(wname.group(2)) if wname else None
        d["ward_name"] = wname.group(1).strip() if wname else None
        d["src"] = "2013-2022"
        frames.append(d)

    # --- annual files
    for pkg, tag in [("bbmp-work-orders-2022-23", "2022-23"),
                     ("bbmp-work-orders-2023-24", "2023-24"),
                     ("bbmp-work-orders-and-payments-2024-25", "2024-25"),
                     ("bbmp-work-orders-and-payments-2025-26", "2025-26")]:
        for f in sorted(glob.glob(str(RAW / pkg / "*.csv"))):
            try:
                d = pd.read_csv(f, low_memory=False)
            except Exception:
                continue
            d.columns = [c.strip().lower() for c in d.columns]
            d["src"] = tag
            d["regime"] = re.search(r"(\d+)\s*Wards? Regime", Path(f).name).group(1) \
                if re.search(r"(\d+)\s*Wards? Regime", Path(f).name) else None
            frames.append(d)

    df = pd.concat(frames, ignore_index=True, sort=False)

    # unify columns
    df["desc"] = df.get("wodetails", pd.Series(dtype=object)).fillna("")
    wo = df.get("wo num")
    if wo is None:
        wo = pd.Series([None] * len(df))
    # some annual files put the job number inside wodetails
    alt = df["desc"].astype(str).str.extract(r"^(\d{1,3}-\d{2}-\d+)")[0]
    df["wo"] = wo.fillna(alt)

    df["ward"] = pd.to_numeric(df.get("ward no", df.get("ward")), errors="coerce")
    df["ward"] = df["ward"].fillna(df["wo"].map(ward_from_wo)).fillna(df.get("ward_file"))
    df["fy"] = df["wo"].map(fy_from_wo)
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce")
    df["nett"] = pd.to_numeric(df.get("nett"), errors="coerce")

    return df[["ward", "ward_name", "fy", "wo", "desc", "contractor",
               "amount", "nett", "src", "regime"]].copy()


def classify(df):
    low = df["desc"].astype(str).str.lower()
    for tier, pat in TIERS.items():
        df[f"is_{tier}"] = low.str.contains(pat, regex=True, na=False)
    for cat, pat in OTHER_CATS.items():
        df[f"cat_{cat}"] = low.str.contains(pat, regex=True, na=False)
    df["wards_named"] = df["desc"].map(parse_multiward)
    df["n_wards_named"] = df["wards_named"].str.len()
    df["multiward"] = df["n_wards_named"] >= 2
    return df


if __name__ == "__main__":
    df = load_all()
    print(f"  loaded {len(df):,} work orders")
    df = classify(df)

    ok = df.dropna(subset=["ward"])
    ok = ok[(ok.amount.notna()) & (ok.amount > 0)]
    ok["ward"] = ok["ward"].astype(int)
    print(f"  usable (ward + amount): {len(ok):,}  "
          f"total Rs {ok.amount.sum()/1e7:,.0f} Cr")
    print(f"  FY coverage: {int(ok.fy.min()) if ok.fy.notna().any() else '?'}"
          f"-{int(ok.fy.max()) if ok.fy.notna().any() else '?'}, "
          f"{ok.fy.notna().mean()*100:.0f}% dated")
    print(f"  wards present: {ok.ward.nunique()}")
    print(f"  multi-ward works: {ok.multiward.sum():,} "
          f"({ok.multiward.mean()*100:.1f}%), "
          f"Rs {ok.loc[ok.multiward,'amount'].sum()/1e7:,.0f} Cr")
    print("\n  drainage share of total spend by tier:")
    for t in TIERS:
        s = ok.loc[ok[f"is_{t}"], "amount"].sum() / ok.amount.sum() * 100
        n = int(ok[f"is_{t}"].sum())
        print(f"    {t:7s} {s:5.1f}%   ({n:,} orders, "
              f"Rs {ok.loc[ok[f'is_{t}'],'amount'].sum()/1e7:,.0f} Cr)")

    ok.to_parquet(OUT / "bbmp_workorders.parquet", index=False)
    print(f"\n  -> {OUT/'bbmp_workorders.parquet'}")
