"""
Classifier validation on 300 independently READ work orders (plan item 1.4).

HOW THIS WAS LABELLED, AND WHY THE FIRST VERSION WAS WORTHLESS. The original validation
adjudicated the 300-order sample with a regex. That regex shared almost all of its keywords
with the classifier it was supposed to be grading - its DEDICATED pattern was nearly
identical to the classifier's `narrow` tier - so the classifier was marking its own
homework. It returned exactly 100% precision, which should have been the tell.

The labels used here come from reading the 300 descriptions and judging what the work
actually is. Every order was labelled twice, independently, and the two passes agreed on
298 of 300 (99.3%); the 2 disagreements were settled by a third independent read.

Measured against those labels the old regex adjudicator agrees only 90% of the time, and
it fails in one systematic direction: it marked 19 orders 'bundled' that are genuinely
DEDICATED drainage. The cause is that Indian work-order descriptions name the street a
drain sits on - "Improvements to drain at 7th B Main Road" is a standalone drain job, not
a road job - and any rule keying on the token "road" will mistake location for scope.
That single error inflated the reported bundled share.

The adjudication rule:

  TRUE DEDICATED   the work IS a stormwater asset and essentially nothing else - SWD,
                   rajakaluve, nala, culvert, desilting, standalone drain construction.
                   A road named as the LOCATION does not make it bundled.
  TRUE BUNDLED     the work genuinely builds a drain, but as part of a larger non-drainage
                   job ("improvements to roads AND drains"). The drainage is real;
                   charging the full amount to drainage over-counts it.
  FALSE POSITIVE   no genuine stormwater content - including sewerage/UGD, which is a
                   different system, and "drain" appearing in a plumbing or place-name
                   context.

What each tier measures, stated honestly:
  narrow  = dedicated assets only        -> UNDER-counts (misses real bundled drainage)
  medium  = anything mentioning a drain  -> OVER-counts (charges road money to drainage)
  the truth lies between, which is why the tagging elasticity is reported as a result.
"""
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
OUT = ROOT / "output"

READ = INT / "label_sample_300_read.csv"


if __name__ == "__main__":
    if not READ.exists():
        raise SystemExit(f"  {READ.name} missing - the independently read labels are the "
                         f"input to this validation; regenerate them before running.")
    s = pd.read_csv(READ)

    print(f"  adjudicated sample: {len(s)} work orders, labelled by reading\n")
    n_arb = int((s.agreement == "arbitrated").sum())
    print(f"  inter-rater agreement: {(s.agreement == 'both').mean()*100:.1f}% "
          f"across two independent passes ({n_arb} arbitrated)\n")
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
                     "precision_dedicated_only": ded / n * 100,
                     "bundled_share_of_true": bun / max(ded + bun, 1) * 100})

    print("\n  * precision = share of flagged orders containing ANY genuine drainage work")

    print("\n  === RECALL: what does each tier MISS? ===")
    true_any = s[s.label != "false_positive"]
    for t in ["narrow", "medium", "broad"]:
        rec = s.loc[true_any.index, f"is_{t}"].mean() * 100
        miss = int((~s.loc[true_any.index, f"is_{t}"]).sum())
        print(f"    {t:8s} recall {rec:5.1f}%  (misses {miss} of {len(true_any)} "
              f"genuine drainage orders)")

    print("\n  === THE MONEY CONSEQUENCE ===")
    tot = s.amount.sum()
    ded_amt = s.loc[s.label == "true_dedicated", "amount"].sum()
    bun_amt = s.loc[s.label == "true_bundled", "amount"].sum()
    print(f"    dedicated drainage   Rs {ded_amt/1e7:7.1f} Cr  ({ded_amt/tot*100:5.1f}% of sample)")
    print(f"    bundled road+drain   Rs {bun_amt/1e7:7.1f} Cr  ({bun_amt/tot*100:5.1f}%)")
    print(f"    -> of the money the medium tier calls drainage, "
          f"{bun_amt/max(ded_amt+bun_amt,1)*100:.0f}% is bundled work whose")
    print(f"       drainage content is unobservable from the text. If that content were")
    print(f"       30%, the medium tier over-states drainage by "
          f"{bun_amt*0.7/max(ded_amt+bun_amt,1)*100:.0f}%.")

    pd.DataFrame(rows).to_csv(OUT / "tables/classifier_validation.csv", index=False)
    print(f"\n  -> {OUT/'tables/classifier_validation.csv'}")
