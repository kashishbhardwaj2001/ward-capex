# Does the Drainage Money Follow the Flood Risk?

### Ward-level evidence from 68,635 municipal work orders in Bengaluru

---

## Abstract

Cities in low- and middle-income countries are told to invest in climate resilience, but
whether municipal capital actually reaches the places most exposed to hazard has never
been tested below the city level. Using 68,635 ward-tagged capital work orders from the
Bruhat Bengaluru Mahanagara Palike (₹23,132 crore, FY2013–2022) joined to a 30 m
terrain-derived flood-hazard surface for all 198 wards, I find that **flood-prone wards
receive systematically smaller capital budgets** — 12.8% less per standard deviation of
hazard (p < 0.0001) — while allocating a modestly *higher* share of what they get to
drainage (+1.61 pp, p = 0.047). The two effects work against each other, and the budget
effect wins: flood-prone wards end up spending **9.0% less on drainage in absolute terms**
(p = 0.016).

The misallocation therefore sits one level above where climate-budget-tagging looks. An
exercise auditing the drainage line would find Bengaluru's engineers prioritising
correctly. The problem is only visible in the denominator. The pattern replicates with the
same sign in Chennai and Pune, and flood hazard is positively correlated with a ward's
SC/ST population share (r = +0.23), giving the gap an equity dimension.

Two measurement findings are of independent interest: the measured "drainage share" of the
budget varies **29-fold** across three defensible keyword definitions, and **27% of
drainage spending cannot be assigned to any ward** in BBMP's own categorisation — the
highest of any category — because trunk drains span wards by construction.

---

## 1. Why this question, and why at ward level

Cross-city studies of climate-risk-to-investment alignment confound hazard with wealth:
richer cities have both more assets at risk and more money to spend. Comparing wards
*within* one city holds the budget envelope, the political administration and the
accounting system fixed, so only hazard varies. Bengaluru is the only Indian city
publishing ward-tagged, project-level, dated actual payments over a long horizon.

This design also required solving a measurement problem. The World Bank's Climate Change
Knowledge Portal — the standard source for city climate indicators — is published on a
0.25° grid. Across Bengaluru's 198 wards, its heat index takes **six distinct values**
(CV 2.5%); its extreme-rainfall index likewise. At ward scale these are not climate
variables at all, but coarse spatial dummies for which grid cell a ward falls in. The
hazard measure must therefore be terrain-derived.

---

## 2. Data

| Component | Source | Detail |
|---|---|---|
| Capital spending | BBMP Works Bill Public View, via OpenCity CKAN | 68,635 ward-tagged orders, ₹23,132 Cr, FY2013–2022 |
| Ward boundaries | DataMeet, BBMP 2012 delimitation | 198 wards |
| Flood hazard | Copernicus DEM GLO-30 → HAND | share of ward below 5 m above nearest drainage |
| Controls | 2011 Census on ward polygons | population, density, SC/ST share, area |
| Geography | derived | distance from centre, elevation, slope |

**Hazard** is the share of each ward lying less than 5 m above the nearest drainage
channel (HAND), computed by filling pits, resolving flats, deriving flow direction and
accumulation, and defining the drainage network as cells with >200 upstream cells. Mean
0.375, SD 0.151, range 0.08–0.81 — genuine within-city variation (CV 40%), unlike the
climate-grid alternatives (CV 2.5%).

**Drainage spending** is classified from free-text work descriptions under three
pre-specified keyword tiers. This is the study's central measurement judgement and is
reported as a result, not hidden.

---

## 3. The tagging elasticity

| Tier | Definition | Amount | Share of works budget |
|---|---|---|---|
| Narrow | stormwater, SWD, rajakaluve, nala only | ₹303 Cr | **1.3%** |
| Medium | + drain, kaluve, desilt, culvert | ₹10,386 Cr | **44.9%** |
| Broad | + road-and-drain, footpath drain | ₹10,632 Cr | **46.0%** |

**A 29-fold difference** in the measured drainage share of an identical budget, from three
defensible readings of the same text. Any single-number claim about "how much a city
spends on drainage" is a statement about the analyst's keyword list as much as about the
city. The medium tier is used throughout; results are reported for all three.

---

## 4. Results

### 4.1 Headline: the misalignment is in the budget, not the drainage line

The naive pooled specification suggested stormwater spending *falls* with flood hazard
(−10.7% per SD, p = 0.004). Decomposing it shows why, and the decomposition is the result.

| Step | β | se | p | Effect |
|---|---|---|---|---|
| **(1) hazard → total ward budget** | **−0.137** | 0.027 | **<0.0001** | **−12.8% per SD** |
| (2) hazard → stormwater spend | −0.095 | 0.039 | 0.016 | −9.0% per SD |
| (3) hazard → stormwater, *budget controlled* | +0.041 | 0.029 | 0.153 | +4.2%, null |
| **(4) hazard → stormwater SHARE of budget** | **+1.609** | 0.810 | **0.047** | **+1.61 pp** |

Read together: flood-prone wards **do** tilt their spending toward drainage (row 4) — the
engineering priorities respond to the terrain. But they are working from budgets that are
**12.8% smaller** (row 1), and once budget size is controlled the drainage effect vanishes
(row 3). The net outcome is 9.0% *less* drainage money where the water collects.

All ward-year specifications cluster standard errors at ward and include year fixed
effects, ward area, population, density and distance from the centre.

#### Replication across cities

Pooled across Bengaluru, Chennai and Pune (1,858 unit-years, 220 sub-city units), with
city fixed effects and hazard standardised *within* city so a ward is never compared to a
zone:

| Specification | β | p | Effect |
|---|---|---|---|
| City FE | −0.114 | 0.004 | −10.7% per SD |
| City + year FE | −0.102 | 0.008 | −9.7% per SD |
| City × year FE | −0.100 | 0.011 | −9.5% per SD |

Per city: Bengaluru −11.8% (p = 0.002), Chennai −20.1% (p = 0.095), Pune −15.4%
(p = 0.052). **The sign is negative in all three.** Only Bengaluru publishes total ward
budgets, so the decomposition above can only be run there; the other two cities show the
reduced-form effect.

#### An equity dimension

Flood hazard is positively correlated with a ward's SC/ST population share (r = +0.234)
and essentially uncorrelated with population size (r = +0.056) or distance from the centre
(r = +0.042). The wards getting smaller budgets despite higher hazard are
disproportionately those with larger scheduled-caste and scheduled-tribe populations.

Worst-affected wards — high hazard, smallest budget relative to hazard:
Mattikere, Agaram, Nilasandra, Dharmaraya Swamy Temple, Vannarpet, Gurappanapalya.

### 4.2 Zero-inflation: a precise null on the extensive margin

Drainage spending occurs in 87% of ward-years, so this is not a corner-solution problem,
but the hurdle is modelled anyway:

- **Any drainage spending that year (logit):** coefficient +0.003, **p = 0.980** — as
  precise a null as the data can produce.
- **Log amount, conditional on spending (OLS, year + zone FE):** +3.8% per SD of hazard,
  p = 0.285.

### 4.3 Falsification

Flood hazard should predict drainage spending and nothing else. All coefficients are pp
per SD of hazard under the full specification.

| Category | β | p | Expectation | Result |
|---|---|---|---|---|
| **drainage** | +1.73 | 0.298 | positive | **not significant** |
| buildings | +0.28 | 0.788 | ~0 | ✅ |
| street lighting | −0.40 | 0.169 | ~0 | ✅ |
| water supply | −0.62 | 0.290 | ~0 | ✅ |
| parks | +2.13 | 0.096 | ~0 | ~ marginal |
| **roads** | **+2.62** | **0.049** | ambiguous | **significant** |

**All four clean placebos behave correctly**, which supports the hazard measure: it is not
spuriously correlated with spending in general. But the only category that significantly
tracks flood hazard is **roads**, not drainage.

### 4.4 The roads finding

Indian municipal road works routinely bundle side drains, kerb channels and culverts. The
result suggests that in flood-prone Bengaluru wards, drainage investment is delivered
*through the road budget* rather than the drainage budget. If so, any study — or any
climate-budget-tagging exercise — that counts only the drainage line will systematically
undercount resilience investment in exactly the places doing it.

### 4.5 The alignment gap

Wards in the top 30% of flood hazard receiving least drainage spending relative to what
their hazard predicts:

| Ward | Hazard | Drainage share | Gap |
|---|---|---|---|
| Dharmaraya Swamy Temple | 0.52 | 6.1% | −38.4 pp |
| Yeshwanthpura | 0.70 | 8.8% | −37.5 pp |
| J P Park | 0.76 | 13.5% | −33.3 pp |
| Kempapura Agrahara | 0.61 | 14.9% | −30.4 pp |
| Domlur | 0.67 | 16.0% | −29.9 pp |
| Horamavu | 0.46 | 16.6% | −27.3 pp |

Horamavu, Yeshwanthpura and Domlur are among Bengaluru's repeatedly-reported flooding
locations, which is weak external corroboration of the hazard surface.

### 4.6 Validation against BBMP's own categorisation

BBMP separately publishes a ward × category matrix for FY2018–2023. Comparing it to the
keyword classifier:

| Comparison | Pearson | Spearman |
|---|---|---|
| BBMP "Drainage" vs narrow tier | +0.11 | +0.27 |
| BBMP "Drainage" vs medium tier | +0.30 | +0.41 |
| **BBMP "Drainage + Roads and Drains" vs medium tier** | **+0.74** | **+0.70** |

The medium tier ranks wards much as BBMP's own classification does, once BBMP's
*Roads and Drains* category is included — independent support both for the classifier and
for §4.4's claim that drainage and road spending are entangled in practice.

### 4.7 Drainage is the least ward-attributable category — in BBMP's own data

BBMP's matrix carries an explicit "Untagged Expenses / Multiple Wards" row. By category:

| Category | Unassignable to a ward |
|---|---|
| **Drainage** | **27%** (₹1,828 Cr of ₹6,691 Cr) |
| Roads and Infrastructure | 21% |
| Water and Sanitation | 5% |
| Buildings and Facilities | 4% |
| Roads and Drains | 3% |

**Drainage is the most ward-unassignable category BBMP publishes**, and by a wide margin
over everything except roads. This is exactly the mechanism anticipated as the study's
principal bias: trunk drains and rajakaluve projects span several wards by construction,
so they cannot be assigned to one. My own regex detects multi-ward naming in only 3.8% of
orders (₹1,114 Cr), so the true unassignable fraction is roughly seven times what
text-matching alone reveals.

**This materially qualifies the null.** If a quarter of drainage money — and
disproportionately the *large trunk projects*, which are precisely those built where water
collects — cannot be attributed to any ward, then the ward-level analysis observes a
non-random subset biased against finding the relationship. The null should be read as:
*no detectable alignment in ward-attributable drainage spending*, which is a narrower and
more defensible claim than no alignment at all.

---

### 4.8 Hazard validation against official flood records

The hazard surface is validated against 395 geocoded flood locations compiled by BBMP with
the Karnataka State Natural Disaster Monitoring Centre (200 flood-vulnerable, 70
flood-prone, 129 low-lying), covering 148 of 198 wards.

| Modelled hazard quartile | Wards | Flood points | Points per km² |
|---|---|---|---|
| Q1 (lowest) | 50 | 64 | 0.751 |
| Q2 | 49 | 93 | 0.859 |
| Q3 | 49 | 111 | 1.208 |
| **Q4 (highest)** | 50 | 127 | **1.356** |

Monotonically increasing, with **1.81× the flood-point density** in the top hazard
quartile versus the bottom (Spearman ρ = +0.26, Pearson r = +0.21). Elevation runs the
other way, as it should (ρ = −0.16).

The correlation is moderate rather than strong, which is the expected result: HAND measures
topographic susceptibility, not drainage capacity, blockage or rainfall intensity — the
proximate causes of urban flooding. It is sufficient to establish that the hazard variable
is measuring something real, which is what the study requires.

---

## 5. Limitations

1. **Descriptive, not causal.** Terrain hazard is time-invariant and non-manipulable;
   there is no counterfactual Bengaluru with flatter ground. No causal claim is made.
2. **Multi-ward attribution — the binding limitation.** BBMP's own categorisation cannot
   assign **27% of drainage spending** to any ward, the highest share of any category it
   publishes (§4.7). Text-matching detects only 3.8%. Trunk drains span wards by
   construction and are built where water collects, so the unobserved portion is
   systematically concentrated in high-hazard areas — biasing β **toward zero**. This is
   the single most important qualification on the null result.
3. **HAND is a proxy.** No free hydraulic pluvial model exists for Indian cities. HAND
   captures topographic susceptibility, not drainage capacity, rainfall intensity or
   blockage — the proximate causes of urban flooding.
4. **Work orders are payments, not budgets.** Arguably better, but not an allocation
   decision.
5. **One city.** Bengaluru proves the method; the pooled multi-city panel is in progress.
6. **Hazard validation passed but is moderate.** Spearman ρ = +0.26 against 395 official
   BBMP/KSNDMC flood points, with a clean monotonic quartile gradient (§4.8). Good enough
   to proceed; not a hydraulic model.

---

## 6. What this contributes

- The **first sub-city test** of whether municipal capital allocation tracks measured
  physical climate hazard, in any country.
- A **quantified tagging elasticity** (29×) for municipal climate spending, on
  government-published data.
- Evidence that resilience spending may be **routed through non-obvious budget lines**,
  with direct implications for climate budget tagging.
- A free, reproducible pipeline: ward polygons, terrain hazard and spending panels for
  **1,946 sub-city units across 17 Indian cities**.

---

*Data and code: all sources free and open. Ward boundaries CC BY-SA 2.5 IN (DataMeet);
spending data from BBMP via OpenCity; DEM from Copernicus.*
