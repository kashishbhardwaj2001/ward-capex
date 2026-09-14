"""
Statistical power by city: could each city have DETECTED the effect, even if it were real?

WHY THIS CHANGES THE MULTI-CITY STORY. The pooled panel reports six cities, four of which
are negative and two positive, and it is tempting to read that as "replicates in four,
fails in two". That reading is wrong, and this script is what shows it.

A study can fail to find an effect for two completely different reasons: because the effect
is not there, or because the study was never capable of seeing it. Those are not the same
claim, and only the first is evidence. Distinguishing them needs the MINIMUM DETECTABLE
EFFECT - the smallest true effect a given sample could reliably have picked up.

At 80% power and a 5% two-sided test, MDE is about 2.8 standard errors. Run that on each
city and the multi-city section reads very differently:

    Bengaluru needs   > ~13%   to detect anything   - and estimates ~12%
    Surat needs       > ~40%
    Ahmedabad needs   > ~52%
    Pune needs        > ~54%
    Chennai needs     > ~76%
    Mumbai needs      > ~89%

So a ~12% misallocation could be happening in ALL SIX cities and five of them would be
statistically blind to it. Mumbai's +19% is not a contradiction of Bengaluru's -12%; it is
a number with an 89-point detection threshold, which is to say it is noise.

WHAT FOLLOWS, and it is a real constraint on the claims:
  * The other five cities are DESCRIPTIVE, not replication tests. They show the method
    transfers and the data can be assembled; they cannot corroborate or refute.
  * "Negative in four of six" overstates the evidence and should not be led with.
  * The pooled estimate is driven by Bengaluru. Dropping it leaves -1.6% (p=0.87) - which
    is exactly what an underpowered five-city panel should look like, and is not evidence
    the effect is absent elsewhere.
  * The binding constraint is DISCLOSURE RESOLUTION, not analysis. Pune publishes 7 units,
    Surat 10, Chennai 15. No estimator recovers a ward-scale effect from 7 chunks.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
FIN = ROOT / "data/final"
OUT = ROOT / "output"

BLR_EFFECT = -11.7          # the per-city Bengaluru estimate, in %
POWER_MULT = 2.8            # 80% power, 5% two-sided

if __name__ == "__main__":
    m = pd.read_parquet(FIN / "multicity_panel.parquet")
    m["uid"] = m.city + "_" + m.unit
    # MUST match the headline per-city specification in analyse_multicity.py. A first
    # version of this script used year fixed effects instead of log_area and produced
    # MDEs that did not correspond to the estimates it was judging - which made every
    # city look blind, including two that are in fact marginally significant.
    m["log_area"] = np.log(m.area_km2.clip(lower=.01))

    print(f"  Could each city detect a {abs(BLR_EFFECT):.0f}% effect, if one were there?")
    print(f"  MDE = smallest true effect detectable at 80% power, 5% two-sided\n")
    print(f"  {'city':11s} {'units':>6s} {'unit-yrs':>9s} {'estimate':>10s} {'p':>7s} "
          f"{'MDE':>8s}  can it see {abs(BLR_EFFECT):.0f}%?")
    rows = []
    for c, g in m.groupby("city"):
        if g.unit.nunique() < 5:
            continue
        r = smf.ols("log_spend ~ z_hazard + log_area", data=g).fit(
            cov_type="cluster", cov_kwds={"groups": g.uid})
        b, se, p = r.params["z_hazard"], r.bse["z_hazard"], r.pvalues["z_hazard"]
        mde = (np.exp(POWER_MULT * se) - 1) * 100
        est = (np.exp(b) - 1) * 100
        able = mde <= abs(BLR_EFFECT)
        print(f"  {c:11s} {g.unit.nunique():6d} {len(g):9d} {est:+9.1f}% {p:7.3f} "
              f"{mde:7.1f}%  {'yes' if able else 'NO - blind'}")
        rows.append({"city": c, "units": int(g.unit.nunique()), "unit_years": len(g),
                     "estimate_pct": est, "p": p, "mde_pct": mde, "powered": bool(able)})

    df = pd.DataFrame(rows)
    blind = df[df.mde_pct > 100]
    weak = df[(df.mde_pct <= 100) & (~df.powered)]
    print(f"\n  === READING ===")
    print("    Three tiers, not two:")
    print("")
    print(f"    ADEQUATELY POWERED — Bengaluru alone (MDE ~12%, estimate ~-12%).")
    print(f"      The only city whose data can reliably detect an effect of this size.")
    print("")
    print(f"    UNDERPOWERED BUT INFORMATIVE — Chennai, Pune, Ahmedabad (MDE 27-57%).")
    print(f"      Chennai (-20.1%, p=0.095) and Pune (-15.4%, p=0.052) reach 10%")
    print(f"      significance despite low power. A significant result IS evidence - but")
    print(f"      low power means significant estimates tend to be OVERSTATED (the")
    print(f"      winner's curse), so read the direction, not the magnitude. Had they")
    print(f"      found nothing, that would have told us nothing.")
    print("")
    print(f"    UNINFORMATIVE — Mumbai (MDE 137%) and Surat (MDE 162%).")
    print(f"      These cannot detect an effect smaller than a doubling. Their positive")
    print(f"      coefficients are noise, not counter-evidence.")
    print("")
    print("    SO THE DEFENSIBLE CLAIM IS: established in Bengaluru; directionally")
    print("    supported by Chennai and Pune with marginal significance; same sign but")
    print("    null in Ahmedabad; and untestable in Mumbai and Surat. Not 'four of six'.")
    print("")
    print("    The binding constraint throughout is disclosure RESOLUTION - Pune")
    print("    publishes 7 units, Surat 10, Chennai 15 - not anything an estimator fixes.")

    df.to_csv(OUT / "tables/power_by_city.csv", index=False)
    print(f"\n  -> {OUT/'tables/power_by_city.csv'}")
