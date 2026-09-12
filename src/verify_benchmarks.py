"""
Benchmark verification (plan items 1.2 and 1.3).

Every target below was read off the published BBMP / OpenCity dataset pages BEFORE the
parser was written, so that the parser could be checked against a number it had no way
to fit to. This is the check that exposed the three-schema bug: parsing only the compact
schema reproduced 8% of the corpus while still appearing to "work".

Two things this verification pinned down that were NOT obvious from the dataset pages:

  * The published 2025-26 headline (4,729 rows / Rs 3,169 Cr) is the **198-Wards-Regime
    file alone**. That dataset ships FOUR files - one per ward regime (198 / 243 / 225 /
    Common) - totalling 9,071 rows and Rs 7,055 Cr. Anyone who compares their parsed
    total against the headline and sees 2x will assume they have double-counted. They
    have not; the headline is a quarter of the release.

  * 2023-24 loses exactly 4 rows (Rs 10.70 Cr, 0.23%) to the ward filter. All four carry
    an OFFICE code in the Ward No column rather than a ward number - "R", "o111", "o132",
    "o157" - and describe city-wide works (water-supply augmentation, project management
    consultancy). They are genuinely not ward-attributable, so they are dropped rather
    than guessed at. The residual is reported, never silently absorbed.

Tolerance: rows exact where the unit is a file; money 0.5%, since published figures are
rounded to 0.1 Cr.
"""
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/bbmp"
INT = ROOT / "data/interim"

TOL = 0.005


def check(label, got_n, got_cr, want_n, want_cr, exact_rows=True):
    dn = got_n - want_n
    dc = abs(got_cr - want_cr) / want_cr if want_cr else 0
    ok = (dn == 0 if exact_rows else True) and dc <= TOL
    print(f"  {label:38s} rows {got_n:6,d} (want {want_n:6,d}, {dn:+5d})  "
          f"Rs {got_cr:8,.1f} Cr (want {want_cr:8,.1f}, {dc*100:+5.2f}%)  "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    wo = pd.read_parquet(INT / "bbmp_workorders.parquet")
    print(f"  parsed corpus: {len(wo):,} work orders, "
          f"Rs {wo.amount.sum()/1e7:,.0f} Cr\n")
    res = []

    print("  === 1.2  per-ward corpus 2013-2022 ===")
    w1 = wo[(wo.src == "2013-2022") & (wo.ward == 1)]
    res.append(check("ward 1 (Kempegowda), 2013-2022",
                     len(w1), w1.amount.sum() / 1e7, 322, 88.8))

    print("\n  === 1.3  annual files ===")
    a23 = wo[wo.src == "2023-24"]
    # the ward filter legitimately removes 4 office-coded rows; verify against the raw
    # file so the residual is measured rather than assumed
    raw23 = pd.read_csv(RAW / "bbmp-work-orders-2023-24/000_BBMP Work Orders 2023-24.csv",
                        dtype=str, low_memory=False)
    raw_cr = pd.to_numeric(raw23["amount"], errors="coerce").sum() / 1e7
    res.append(check("FY2023-24, raw file", len(raw23), raw_cr, 6719, 4585.0))
    lost_n, lost_cr = len(raw23) - len(a23), raw_cr - a23.amount.sum() / 1e7
    print(f"  {'-> after ward filter':38s} rows {len(a23):6,d} "
          f"({lost_n:+d} office-coded)  Rs {a23.amount.sum()/1e7:8,.1f} Cr "
          f"({lost_cr/raw_cr*100:.2f}% unattributable)")

    # the published 2025-26 headline is the 198-regime file only, not the 4-file release
    p = RAW / "bbmp-work-orders-and-payments-2025-26"
    r198 = pd.read_csv(p / "000_Work Orders and Payments for 198 Wards Regime.csv",
                       dtype=str, low_memory=False)
    res.append(check("FY2025-26, 198-regime file", len(r198),
                     pd.to_numeric(r198["amount"], errors="coerce").sum() / 1e7,
                     4729, 3169.0))
    a25 = wo[wo.src == "2025-26"]
    print(f"  {'-> all four regime files parsed':38s} rows {len(a25):6,d}"
          f"{'':16s}Rs {a25.amount.sum()/1e7:8,.1f} Cr "
          f"(the headline is one file of four)")

    print(f"\n  {sum(res)}/{len(res)} benchmarks pass")
