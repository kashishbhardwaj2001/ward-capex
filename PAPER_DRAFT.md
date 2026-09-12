# Does the Drainage Money Follow the Flood Risk?

### Ward-level evidence from 68,415 municipal work orders in Bengaluru

---

## Abstract

Cities in low- and middle-income countries are told to invest in climate resilience, but
whether municipal capital actually reaches the places most exposed to hazard has never
been tested below the city level. Using 68,415 ward-tagged capital work orders from the
Bruhat Bengaluru Mahanagara Palike (₹23,081 crore, FY2013–2022) joined to a 30 m
terrain-derived flood-hazard surface for all 198 wards, I find that **flood-prone wards
receive systematically smaller capital budgets** — 12.8% less per standard deviation of
hazard (p < 0.0001) — while allocating a modestly *higher* share of what they get to
drainage (+1.61 pp, p = 0.047). The two effects work against each other, and the budget
effect wins: flood-prone wards end up spending **9.0% less on drainage in absolute terms**
(p = 0.016).

The misallocation therefore sits one level above where climate-budget-tagging looks. An
exercise auditing the drainage line would find Bengaluru's engineers prioritising
correctly. The problem is only visible in the denominator. The pattern repeats with the
same sign in Chennai, Pune and Ahmedabad but **not in Mumbai or Surat**, both of which are
too coarsely reported to resolve within-city hazard, and flood hazard is positively
correlated with a ward's SC/ST population share (r = +0.23), giving the gap an equity
dimension.

Three tests narrow what else could produce it. A **coefficient-contrast test** shows the
within-budget tilt toward drainage is statistically indistinguishable from the tilt toward
roads or parks (0 of 5 contrasts significant) — high-hazard wards favour outdoor civil works
generally, not flood protection, which closes the reading that wards protect themselves with
whatever money they have. A **ward fixed-effects arm** on time-varying CHIRPS rainfall finds
no within-ward reallocation when a ward has an unusually wet year, ruling out a fixed ward
characteristic correlated with terrain; it also shows why levels cannot be read here at all,
since a wet year suppresses the *number* of work orders (−0.55, p = 0.001) and cuts street
lighting and buildings harder than drainage — construction throughput, not budgeting.
Finally, controlling for the **existing drainage stock** (660 km of mapped line-work) leaves
87% of the effect intact; the p-value weakens only because the control is collinear with
hazard by construction.

Two measurement findings are of independent interest: the measured "drainage share" of the
budget varies **35-fold** across three defensible keyword definitions, and **27% of
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
| Capital spending | BBMP Works Bill Public View, via OpenCity CKAN | 68,415 ward-tagged orders, ₹23,081 Cr, FY2013–2022 |
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
| Narrow | stormwater, SWD, rajakaluve, nala only | ₹301 Cr | **1.3%** |
| Medium | + drain, kaluve, desilt, culvert | ₹10,355 Cr | **44.9%** |
| Broad | + road-and-drain, footpath drain | ₹10,600 Cr | **45.9%** |

**A 35-fold difference** in the measured drainage share of an identical budget, from three
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

Pooled across **six cities — Bengaluru, Ahmedabad, Chennai, Pune, Mumbai and Surat**
(2,088 unit-years, 283 sub-city units, ₹16,792 crore), with city fixed effects and hazard
standardised *within* city so a ward is never compared to a zone:

| Specification | β | p | Effect |
|---|---|---|---|
| City FE | −0.101 | 0.007 | −9.6% per SD |
| City + year FE | −0.090 | 0.014 | −8.6% per SD |
| City × year FE | −0.088 | 0.018 | −8.4% per SD |

Per city:

| City | Units | Unit-years | β | p | Effect |
|---|---|---|---|---|---|
| Chennai | 15 zones | 90 | −0.225 | 0.095 | −20.1% |
| Pune | 7 wards | 46 | −0.167 | 0.052 | −15.4% |
| Ahmedabad | 29 wards | 107 | −0.158 | 0.325 | −14.6% |
| Bengaluru | 198 wards | 1,722 | −0.125 | 0.002 | −11.7% |
| **Mumbai** | 24 wards | 64 | **+0.237** | 0.442 | **+26.8%** |
| **Surat** | 10 zones | 59 | **+0.377** | 0.272 | **+45.9%** |

**Negative in four of six cities**, significant in three. The two positive cities run the
other way but **neither is statistically distinguishable from zero** — Mumbai's standard
error is three times the pooled effect and Surat's is larger still.

The two non-replications share a structural feature that is worth stating plainly rather
than treating as coincidence: **both are the coarsest and smallest panels in the set.**
Bengaluru contributes 198 wards with a within-city hazard SD of 0.149; Surat contributes
10 zones with an SD of 0.050, the most spatially smoothed of the six, because its budget
reports by zone and its hazard has to be aggregated *up* from 30 ward polygons through an
areal crosswalk. Mumbai contributes 24 wards of budget *estimates* rather than audited
actuals. Where the unit is coarse enough, within-city hazard variation is largely averaged
away before it can be related to anything, and the estimate is uninformative in either
direction. That is a limitation of the available disclosure, not a finding about those two
cities.

#### Mumbai does not replicate, and the paper says so

Mumbai is the only city besides Bengaluru publishing *both* stormwater and total ward
capital, so it is the one independent test of the full decomposition. It fails:

| Step | β | p |
|---|---|---|
| hazard → total ward capital | +0.042 | 0.713 |
| hazard → SWD capital | +0.223 | 0.748 |
| hazard → SWD, total controlled | +0.046 | 0.957 |
| hazard → SWD share | +0.337 | 0.826 |

Every coefficient is null with large standard errors. Three reasons not to over-read either
direction: Mumbai has **24 wards to Bengaluru's 198**, so power is low; its figures are
**budget estimates, not audited actuals** (recovered from an unlinked WebDAV folder tree on
MCGM's portal — they are not published through any navigable index); and its SWD share is
extremely noisy (mean 5.4%, SD 16.1). Mumbai is best read as uninformative rather than as
contradicting Bengaluru — but it is not supporting evidence, and it is reported here rather
than dropped.

The honest summary of the multi-city evidence is therefore narrower than "it replicates":
the result is **established in Bengaluru**, where the data are ward-level, audited and
long-running; it is **directionally consistent in three further cities**, two of them at
conventional significance; and it is **untestable at present in two**, whose disclosure is
too coarse to resolve within-city hazard at all. The pooled estimate should be read as a
summary of the first four, not as evidence about the last two.

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

The original design was **hazard-side**: drainage should respond to flood hazard, parks to
heat hazard, and each should ignore the other's. It appeared to fail — drainage tracked
"heat" more strongly than flood. **The test was broken, not the finding.** CCKP's `hd35`
takes six distinct values across 198 wards (CV 2.5%); at ward scale it is a dummy for which
0.25° cell a ward sits in, and z-scoring a step function manufactures apparent signal. It
cannot falsify anything. This is the paper's own scale critique surfacing inside its
analysis, and it is the reason the test was rebuilt on the **outcome side**, where every
variable comes from the same ward-tagged work-order text and varies properly.

All coefficients are pp per SD of hazard under the full specification.

| Category | β | p | Expectation | Result |
|---|---|---|---|---|
| **drainage** | +1.73 | 0.298 | positive | not significant |
| buildings | +0.28 | 0.788 | ~0 | ✅ |
| street lighting | −0.40 | 0.169 | ~0 | ✅ |
| water supply | −0.62 | 0.290 | ~0 | ✅ |
| parks | +2.13 | 0.096 | ~0 | ~ marginal |
| roads | +2.62 | 0.049 | ambiguous | significant |

**All four clean placebos behave correctly**, which supports the hazard measure: it is not
spuriously correlated with spending in general.

#### 4.3.1 The test that discriminates

Reading that table row by row invites the wrong question. Once the decomposition has located
the effect in the *total budget*, what matters is not whether drainage is positive but
whether the within-budget tilt is **drainage-specific**. Two stories predict different
things:

- *flood-targeting* — drainage's coefficient is significantly **larger** than the placebos':
  wards protect themselves within whatever budget they get;
- *generic civil works* — drainage moves with roads and parks and is **not distinguishable**
  from them: the tilt reflects what kind of land a low-lying ward has, not a flood response.

Estimated as a Wald test on the coefficient difference, stacking each pair of shares on the
same ward sample so the covariance is available (`src/analyse_falsification.py`):

| drainage vs | difference | se | p |
|---|---|---|---|
| buildings | +2.47 | 1.85 | 0.182 |
| street lighting | +1.40 | 1.38 | 0.309 |
| water supply | +1.37 | 1.47 | 0.350 |
| parks | −0.29 | 1.89 | 0.876 |
| roads | −0.92 | 1.32 | 0.485 |

**Zero of five contrasts are significant.** There is no drainage-specific targeting: the
composition tilt in high-hazard wards runs toward **outdoor civil works generally** — roads
+2.6 pp, parks +2.1 pp, drainage +1.7 pp — and away from buildings, lighting and water
supply. That is the pattern one expects of low-lying, less-built-up land, not of a flood
response.

This sharpens the headline rather than contradicting it. The headline is that flood hazard
predicts a **smaller total budget** (−12.8%); this test adds that there is **no
drainage-specific compensation inside that smaller budget**. Both halves point the same way.

It also closes the most damaging alternative reading of the +1.61 pp share result in §4.1.
On its own, that coefficient can be told as *"wards do protect themselves, they just have
less money to do it with."* They do not. The share moves because the whole outdoor-works
basket moves.

### 4.4 The roads finding, stated at the strength the evidence supports

Indian municipal road works routinely bundle side drains, kerb channels and culverts, and
roads is the only category significant on its own (+2.62 pp, p = 0.049). The natural story
is that in flood-prone wards drainage investment is delivered *through the road budget*.

The contrast test in §4.3.1 does not support the strong version of that claim: roads is not
significantly different from drainage (p = 0.485), so the data cannot distinguish "drainage
hides in roads" from "low-lying wards get more outdoor civil works of every kind". What
survives is the weaker and still consequential point, which the classifier validation
reaches independently: **80% of the money the medium tier tags as drainage is bundled
road-and-drain work**. Whatever the mechanism, any study — or any climate-budget-tagging
exercise — that counts only the drainage line will mis-measure resilience investment,
because the line item and the physical asset do not correspond.

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

### 4.9 A ward fixed-effects arm, and the confound it uncovers

Every result so far is cross-sectional. Terrain hazard does not move, so a ward fixed
effect would absorb it entirely, leaving one objection permanently open: *is this just
ward wealth, or ward politics, or anything else fixed about a ward that the controls miss?*

CHIRPS daily (0.05°, ~5.5 km) supplies a hazard measure that **moves**. Bengaluru wards
averaged 4.9 extreme-rain days in FY2016 and 17.4 in FY2022. The question becomes
within-ward: *when a ward has an unusually wet year, does its drainage budget respond?* —
with a ward fixed effect absorbing terrain, wealth, councillor and location, and a year
fixed effect absorbing the city-wide budget cycle. After both, **39% of the rainfall
variation survives** to identify the estimates.

**Run naively this produces a dramatic and wrong result.** Within-ward, a wetter year
predicts *lower* drainage spending — β = −0.92 log points per SD, p = 0.001. Read as a
budget response, budgets move the wrong way when it rains.

They do not. The outcome here is *executed* spending recovered from work orders and their
payment records, not an allocated budget, and **heavy rain stops construction**:

| outcome, per SD of annual rainfall | β | p |
|---|---|---|
| **number of work orders** | **−0.55** | **0.001** |
| drainage spend | −0.92 | 0.001 |
| roads spend | −1.57 | 0.264 |
| buildings spend | −2.21 | 0.238 |
| street lighting spend | −2.82 | 0.085 |

All five fall, the **order count** among them, and **drainage falls least of the four
categories**. This is construction throughput, not allocation. Level specifications are
therefore reported but not interpreted; the **share** is the specification that answers the
question, because a shock common to all categories cancels out of a ratio.

On the share, **no specification detects a within-ward response** — contemporaneous or
lagged one year, extreme-rain days or annual millimetres. A ward that has an unusually wet
year does not tilt its capital budget toward drainage the year after.

The null is **moderate, not strong**: 39% residual variation, and wards sharing a 5.5 km
CHIRPS pixel contribute none of it, so a modest real response could be missed. What it does
establish is what the cross-section could not — the headline is not an artefact of a fixed
ward characteristic correlated with terrain. Within a single ward, with everything fixed
about it held constant, the hazard moves and the allocation does not follow.

### 4.10 The existing-stock explanation, tested and rejected

The most serious innocent reading of the headline is a **stock** story: perhaps flood-prone
wards were already given their drainage, so they rationally need less new capital now. If
true, the misallocation is a well-functioning system that finished early.

Testing it needs a measure of the drainage that already exists. BBMP's rajakaluve GIS is not
open data and the state SDMA layers are PDF maps, so OpenStreetMap is the only free
ward-resolution source: **660 km of mapped drainage line-work across Bengaluru's 198 wards**
(568 km engineered), against BBMP's published ~842 km rajakaluve network. Nine wards have
nothing mapped.

Existing drainage is indeed concentrated where hazard is (Spearman ρ = +0.47 on engineered
line-work) — which is what the stock story needs. Part of that correlation is *mechanical*
and must be named: HAND is computed from the drainage network implied by the terrain, and
OSM's `stream`/`river` ways follow the same topography, so the engineered-only measure is
the one used as the control.

| specification | β | se | p | effect |
|---|---|---|---|---|
| baseline, no stock control | −0.0814 | 0.0339 | 0.016 | −7.8% |
| + drain density (linear) | −0.0704 | 0.0409 | 0.085 | −6.8% |
| + engineered-only density | −0.0713 | 0.0401 | 0.075 | −6.9% |
| + log density | −0.0623 | 0.0365 | 0.087 | −6.0% |
| + density × hazard interaction | −0.0751 | 0.0411 | 0.068 | −7.2% |

**The effect survives in magnitude — 87% of it — while the standard error widens 1.21×.**
Reading the p-value alone (0.016 → 0.085) would mistake multicollinearity for the effect
disappearing: the control correlates with hazard by construction, so it inflates the
standard error while barely moving the coefficient.

The stock story therefore does not account for the result, and the test was **biased in its
favour**: OSM completeness tracks affluence and centrality, overstating the stock in exactly
the wards the stock story needs it overstated in.

Where the stock story earns partial credit is the split sample:

| sample | effect | p |
|---|---|---|
| wards with below-median existing drainage | **−10.5%** | 0.045 |
| wards with above-median existing drainage | −5.1% | 0.310 |

The hazard penalty is roughly **twice as large where little drainage exists**. Existing
infrastructure absorbs some of the gap; it does not close it. The penalty stays negative on
both sides.

### 4.11 It is not partisan targeting

BBMP's last council election was 2015 (BJP 100, INC 76, JDS 14, IND 7, SDPI 1 — matching
the published headline exactly); the council's term ended in September 2020 with no
election since, so the 2015 assignment covers the panel. A ward is coded *aligned* when its
corporator's party held the Karnataka state government that year (39% of ward-years).

| Test | Result |
|---|---|
| Aligned with state ruling party → total budget | **+1.9%, p = 0.68** — no effect |
| Flood hazard → total budget, no political control | −8.0%, p = 0.013 |
| + aligned dummy | −8.1%, p = 0.013 |
| + party fixed effects | −8.1%, **p = 0.009** |
| + party × year fixed effects | −8.0%, p = 0.012 |

**Alignment with the ruling party buys a ward nothing**, and the hazard penalty is
completely unmoved by party controls. Whatever produces the budget gap, it is not partisan
targeting of the governing party's own wards.

Hazard is nonetheless politically distributed: opposition-held INC wards are more
flood-prone (mean hazard z = +0.27) than BJP wards (−0.17), and the seven independents are
the most exposed of all (+0.89).

**An attenuation to state plainly.** The headline −12.8% is estimated controlling for ward
area, population, density and distance from the centre. Adding **elevation and slope** —
which are mechanically related to HAND, since all three derive from the same DEM — pulls
the coefficient to **−8.0%**, still significant at 1–5%. The honest range for the budget
penalty is therefore **−8% to −13% per standard deviation of hazard**, depending on how
much terrain is absorbed into the controls. Every specification is negative and
significant; the magnitude is what moves.

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
4. **Work orders are payments, not budgets.** Arguably better — they are what was actually
   spent — but not an allocation decision. §4.9 shows this is not a theoretical worry: a
   wet year suppresses the *number* of work orders (−0.55, p = 0.001), so rainfall shocks
   move executed spending through construction throughput regardless of any budget
   response. Level specifications on time-varying rainfall are uninterpretable for that
   reason, and only the share is used.
4b. **Classifier measures bundled work.** Hand-adjudicating 300 orders: the medium tier has
   100% precision and 98.1% recall, but **80% of what it flags is bundled "roads and
   drains"** where the full amount is charged to drainage. The narrow tier is clean but
   recovers only 6.5% of genuine drainage orders. Under the narrow definition the hazard
   effect on drainage share is **significantly positive** (+0.445 pp, p = 0.013 with Conley
   spatial SEs) — dedicated stormwater assets do track hazard; bundled road money does not.
5. **Depth varies by city, and the two non-replications are the coarsest panels.**
   Bengaluru carries the decomposition with 198 wards and a within-city hazard SD of 0.149.
   Chennai, Pune and Ahmedabad contribute the reduced form at coarser units (zones, ward
   offices) over shorter panels. Surat is joined via a purpose-built ward→zone crosswalk,
   but its budget reports only 10 zones, leaving a hazard SD of 0.050 — the most spatially
   smoothed of the six; Mumbai publishes budget *estimates* across 24 wards. Both run
   positive and neither is distinguishable from zero. Where the reporting unit is coarse
   enough, within-city hazard variation is averaged away before it can be related to
   anything, so these are uninformative rather than contradicting. The pooled estimate
   should be read as summarising the four cities that can resolve the question.
5b. **The stock control is OpenStreetMap, with the measurement error that implies.** OSM
   mapping effort tracks affluence and centrality, so mapped drain density overstates the
   stock in rich central wards. That bias runs *toward* the rival explanation, which is why
   the control is usable — but a purpose-built municipal drainage GIS would be better, and
   none is published. Part of the hazard–stock correlation is also mechanical, since HAND
   is derived from terrain-implied drainage and OSM's natural watercourses follow the same
   topography; the control therefore uses engineered line-work only (§4.10).
5c. **CHIRPS resolves neighbourhoods, not wards.** At 0.05° (~5.5 km) Bengaluru's 198 wards
   occupy roughly 60–70 distinct pixels, and wards sharing a pixel have identical rainfall
   by construction. After ward and year fixed effects only 39% of the rainfall variation
   survives, so the within-ward null in §4.9 is **moderate evidence, not strong** — a real
   but modest reallocation could be missed.
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
