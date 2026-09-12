# Does the Drainage Money Follow the Flood Risk?

### Ward-level evidence from 68,635 municipal work orders in Bengaluru

---

## Abstract

Cities in low- and middle-income countries are told to invest in climate resilience, but
whether municipal capital actually reaches the places most exposed to hazard has never
been tested below the city level. Using 68,635 ward-tagged capital work orders from the
Bruhat Bengaluru Mahanagara Palike (₹23,132 crore, FY2013–2022) joined to a 30 m
terrain-derived flood-hazard surface for all 198 wards, I find **no statistically
significant relationship between a ward's flood hazard and its drainage capital
spending**. The point estimate is positive but small and never significant
(+1.1 to +1.5 pp per standard deviation of hazard; p = 0.19–0.30) across pooled, year-fixed
and zone-fixed specifications, and is a precise null in the extensive margin
(probability of any drainage spending: p = 0.98). Four placebo categories behave
correctly, supporting the hazard measure. Two secondary findings are of independent
interest: spending that *does* respond to flood hazard flows through the **roads** budget
line rather than the drainage line, and the measured "drainage share" of the municipal
budget varies **29-fold** (1.3% to 46.0%) across three defensible keyword definitions.

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

### 4.1 Headline: drainage spending does not track flood hazard

Outcome: drainage share of the ward works budget. Hazard standardised.

| Specification | β (pp per SD) | se | p | R² |
|---|---|---|---|---|
| Cross-section, bare | +2.31 | 1.36 | 0.089 | 0.057 |
| + size controls | +1.87 | 1.33 | 0.160 | 0.105 |
| + core/periphery | +1.67 | 1.33 | 0.208 | 0.147 |
| + terrain | +1.73 | 1.66 | 0.298 | 0.152 |
| Panel, year FE | +1.47 | 1.12 | 0.188 | 0.149 |
| **Panel, year + zone FE** | **+1.11** | **0.95** | **0.242** | **0.219** |

The bare cross-sectional correlation is r = +0.087. The relationship weakens as controls
are added and never reaches significance.

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
6. **Hazard validation is outstanding.** Against an official flood-hotspot inventory —
   the single most important remaining robustness check.

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
