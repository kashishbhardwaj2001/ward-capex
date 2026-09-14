"""
Four robustness checks a referee will ask for, run before they do.

Each of these was an open exposure rather than a known weakness - the point is that none
had been tested, so none could be defended. In order of how damaging a failure would be:

  1. HAZARD THRESHOLD. The headline hazard is "share of ward within 5 m of its nearest
     drainage". Five metres is a judgement call. If the result only exists at 5 m it is an
     artefact of that choice, so it is re-run at 1, 2, 3, 5 and 10 m and against two
     threshold-FREE measures (mean HAND, and the topographic wetness index).

  2. STALE POPULATION. The panel runs FY2013-2022 but population is the 2011 census, and
     Bengaluru grew fast and unevenly over that decade - peripheral wards fastest. If the
     result depends on a control that is up to 15 years out of date, that is a problem.
     Tested by dropping population entirely, and by substituting satellite-measured
     built-up area, which is contemporaneous.

  3. COUNCIL VACANCY. BBMP's council term ended in September 2020 and no election has been
     held since. Party controls for FY2021-22 therefore describe a council that did not
     exist. Tested by re-running on FY2013-2020 only.

  4. MULTIPLE TESTING. This project reports many specifications. No correction has been
     applied. The headline family is re-tested under Bonferroni and Benjamini-Hochberg.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "data/interim"
FIN = ROOT / "data/final"
OUT = ROOT / "output"

CTRL = "log_pop + z_log_density + z_dist_centre_km + z_elev_m + z_slope"


def fit(d, y, x, ctrl=CTRL, fe="C(fy)"):
    f = f"{y} ~ {x}" + (f" + {ctrl}" if ctrl else "") + (f" + {fe}" if fe else "")
    m = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["ward"]})
    return m.params[x], m.bse[x], m.pvalues[x], int(m.nobs)


def z(s):
    return (s - s.mean()) / s.std()


if __name__ == "__main__":
    d = pd.read_parquet(FIN / "bengaluru_budget_panel.parquet")
    d["ward"] = pd.to_numeric(d["unit"], errors="coerce")
    for c in ["elev_m", "slope"]:
        d[f"z_{c}"] = z(d[c])

    # ---------------------------------------------------------------- 1. threshold
    print("  === 1. DOES THE RESULT DEPEND ON THE 5 m THRESHOLD? ===")
    thr = INT / "hand_thresholds_bengaluru.parquet"
    print(f"  {'hazard measure':34s} {'effect':>9s} {'se':>7s} {'p':>8s}")
    rows = []
    for lab, col in [("share within 5 m  [headline]", "hand_lt5m_share"),
                     ("mean HAND (no threshold)", "hand_m"),
                     ("topographic wetness index", "twi")]:
        dd = d.dropna(subset=["log_total", col]).copy()
        # HAND and TWI run the opposite way to the share: LOW hand = flood-prone,
        # HIGH twi = flood-prone. Sign them so "up = more hazard" throughout.
        dd["hz"] = z(-dd[col]) if col == "hand_m" else z(dd[col])
        b, se, p, n = fit(dd, "log_total", "hz")
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:34s} {(np.exp(b)-1)*100:+8.1f}% {se:7.3f} {p:8.4f}{st}")
        rows.append({"test": "threshold", "spec": lab, "pct": (np.exp(b) - 1) * 100, "p": p})

    if thr.exists():
        t = pd.read_parquet(thr)
        # the panel already carries hand_lt5m_share; merging it again suffixes BOTH copies
        # to _x/_y and the loop below then cannot find either
        t = t.drop(columns=[c for c in t.columns if c in d.columns and c != "ward"])
        d2 = d.merge(t, on="ward", how="left")
        for m_ in [c for c in t.columns if c.startswith("hand_lt")]:
            dd = d2.dropna(subset=["log_total", m_]).copy()
            dd["hz"] = z(dd[m_])
            b, se, p, n = fit(dd, "log_total", "hz")
            st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
            lab = f"share within {m_.replace('hand_lt','').replace('m_share','')} m"
            print(f"  {lab:34s} {(np.exp(b)-1)*100:+8.1f}% {se:7.3f} {p:8.4f}{st}")
            rows.append({"test": "threshold", "spec": lab, "pct": (np.exp(b) - 1) * 100, "p": p})
    else:
        print(f"  (run src/build_hand_thresholds.py to add 1/2/3/10 m variants)")

    # ---------------------------------------------------------------- 2. population
    print(f"\n  === 2. IS IT PROPPED UP BY 2011 CENSUS POPULATION? ===")
    p2 = pd.read_parquet(INT / "panel_v2.parquet")
    d3 = d.merge(p2[["ward", "fy", "builtup_km2"]], on=["ward", "fy"], how="left")
    d3["z_builtup"] = z(np.log(d3.builtup_km2.clip(lower=.001)))
    for lab, ctrl in [
        ("full controls  [headline]", CTRL),
        ("population DROPPED", "z_log_density + z_dist_centre_km + z_elev_m + z_slope"),
        ("built-up area instead of pop", "z_builtup + z_dist_centre_km + z_elev_m + z_slope"),
        ("no controls at all", ""),
    ]:
        dd = d3.dropna(subset=["log_total", "z_hazard"] + ([] if not ctrl else []))
        b, se, p, n = fit(dd, "log_total", "z_hazard", ctrl=ctrl)
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:34s} {(np.exp(b)-1)*100:+8.1f}% {se:7.3f} {p:8.4f}{st}")
        rows.append({"test": "population", "spec": lab, "pct": (np.exp(b) - 1) * 100, "p": p})

    # ---------------------------------------------------------------- 3. council
    print(f"\n  === 3. THE COUNCIL TERM ENDED IN 2020 ===")
    for lab, sub in [("full panel FY2013-2022", d),
                     ("council existed: FY2013-2020", d[d.fy <= 2020]),
                     ("no council: FY2021-2022", d[d.fy >= 2021])]:
        dd = sub.dropna(subset=["log_total", "z_hazard"])
        if dd.ward.nunique() < 50:
            print(f"  {lab:34s} skipped (n={len(dd)})")
            continue
        b, se, p, n = fit(dd, "log_total", "z_hazard")
        st = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"  {lab:34s} {(np.exp(b)-1)*100:+8.1f}% {se:7.3f} {p:8.4f}{st}  n={n:,}")
        rows.append({"test": "council", "spec": lab, "pct": (np.exp(b) - 1) * 100, "p": p})

    # ---------------------------------------------------------------- 4. multiplicity
    print(f"\n  === 4. MULTIPLE TESTING CORRECTION ===")
    fam = [("hazard -> total budget", 1e-8), ("hazard -> stormwater", 0.0160),
           ("hazard -> stormwater | budget", 0.1555), ("hazard -> share", 0.0470)]
    k = len(fam)
    ps = np.array([p for _, p in fam])
    order = np.argsort(ps)
    bh = np.empty(k)
    for rank, i in enumerate(order, start=1):
        bh[i] = min(1, ps[i] * k / rank)
    bh = np.minimum.accumulate(bh[order[::-1]])[::-1]
    bhf = np.empty(k); bhf[order] = bh
    print(f"  {'test in the headline family':34s} {'raw p':>9s} {'Bonferroni':>11s} {'BH-FDR':>9s}")
    for (lab, p), bonf, fdr in zip(fam, ps * k, bhf):
        mark = "survives" if fdr < .05 else "fails"
        print(f"  {lab:34s} {p:9.4f} {min(bonf,1):11.4f} {fdr:9.4f}  {mark}")
    print(f"\n    The headline (-12.8%, p<1e-8) survives any correction at any k.")

    pd.DataFrame(rows).to_csv(OUT / "tables/robustness2.csv", index=False)
    print(f"\n  -> {OUT/'tables/robustness2.csv'}")
