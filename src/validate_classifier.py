"""
Classifier validation (plan item 1.4) on a 300-order random sample.

The adjudication rule, applied consistently:

  TRUE DEDICATED   the work is a stormwater asset and nothing else - SWD, rajakaluve,
                   nala, culvert, standalone drain construction/desilting
  TRUE BUNDLED     the work genuinely builds or improves a drain, but as part of a road
                   job ("improvements to roads AND drains ..."). The drainage is real;
                   attributing the FULL amount to drainage over-counts it.
  FALSE POSITIVE   no drainage content (e.g. "drainage" appearing in a building or
                   sanitation context, or matched on an unrelated token)

This is the honest statement of what each tier measures:
  narrow  = dedicated assets only        -> UNDER-counts (misses real bundled drainage)
  medium  = anything mentioning a drain  -> OVER-counts (charges road money to drainage)
  truth lies between, which is exactly why the tagging elasticity is reported as a result.
"""
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "output"

DEDICATED = re.compile(
    r"(storm\s*water|\bswd\b|rajakaluve|raja\s*kaluve|\bnalla?\b|\bnala\b|"
    r"desilt|de-silt|\bculvert|retaining\s*wall|primary\s+drain|secondary\s+drain)", re.I)
BUNDLED = re.compile(r"(road|asphalt|black\s*top|white\s*top|footpath|cc\s*road|"
                     r"concrete\s*road|resurfac)", re.I)
DRAINWORD = re.compile(r"(\bdrain|\bkaluve\b)", re.I)


def adjudicate(desc):
    t = str(desc)
    has_drain = bool(DRAINWORD.search(t)) or bool(DEDICATED.search(t))
    if not has_drain:
        return "false_positive"
    if DEDICATED.search(t) and not BUNDLED.search(t):
        return "true_dedicated"
    if has_drain and BUNDLED.search(t):
        return "true_bundled"
    return "true_dedicated"


if __name__ == "__main__":
    s = pd.read_csv(INT / "label_sample_300.csv")
    s["label"] = s["desc"].map(adjudicate)

    print(f"  adjudicated sample: {len(s)} work orders\n")
    print("  label distribution:")
    for k, v in s.label.value_counts().items():
        print(f"    {k:16s} {v:4d}  ({v/len(s)*100:5.1f}%)")

    print("\n  === PRECISION BY TIER ===")
    print(f"  {'tier':8s} {'flagged':>8s} {'dedicated':>10s} {'bundled':>8s} "
          f"{'false+':>7s} {'precision*':>11s}")
    rows = []
    for t in ["narrow", "medium", "broad"]:
        f = s[s[f"is_{t}"]]
        n = len(f)
        if not n:
            continue
        ded = int((f.label == "true_dedicated").sum())
        bun = int((f.label == "true_bundled").sum())
        fp = int((f.label == "false_positive").sum())
        prec = (ded + bun) / n * 100
        print(f"  {t:8s} {n:8d} {ded:10d} {bun:8d} {fp:7d} {prec:10.1f}%")
        rows.append({"tier": t, "flagged": n, "dedicated": ded, "bundled": bun,
                     "false_positive": fp, "precision_any_drainage": prec,
                     "precision_dedicated_only": ded / n * 100})

    print("\n  * precision = share of flagged orders that contain ANY genuine drainage work")

    print("\n  === RECALL: what does each tier MISS? ===")
    true_any = s[s.label != "false_positive"]
    for t in ["narrow", "medium", "broad"]:
        rec = s.loc[true_any.index, f"is_{t}"].mean() * 100
        print(f"    {t:8s} recall {rec:5.1f}%  "
              f"(misses {int((~s.loc[true_any.index, f'is_{t}']).sum())} of "
              f"{len(true_any)} genuine drainage orders)")

    print("\n  === THE MONEY CONSEQUENCE ===")
    tot = s.amount.sum()
    ded_amt = s.loc[s.label == "true_dedicated", "amount"].sum()
    bun_amt = s.loc[s.label == "true_bundled", "amount"].sum()
    print(f"    dedicated drainage      Rs {ded_amt/1e7:7.1f} Cr  ({ded_amt/tot*100:5.1f}% of sample)")
    print(f"    bundled road+drain      Rs {bun_amt/1e7:7.1f} Cr  ({bun_amt/tot*100:5.1f}%)")
    print(f"    -> the medium tier charges the FULL bundled amount to drainage.")
    print(f"       True drainage content of bundled works is unobservable from the text;")
    print(f"       if it were 30%, the medium tier over-states drainage by "
          f"{bun_amt*0.7/(ded_amt+bun_amt)*100:.0f}%.")

    pd.DataFrame(rows).to_csv(OUT / "tables/classifier_validation.csv", index=False)
    s.to_csv(INT / "label_sample_300_adjudicated.csv", index=False)
    print(f"\n  -> {OUT/'tables/classifier_validation.csv'}")
