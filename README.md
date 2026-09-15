# Does the drainage money follow the flood risk?

**Ward-level evidence on whether Indian municipal capital spending tracks measured climate hazard.**

**Live site: [climatequant.org](https://climatequant.org)**

> Within a city - where the budget, the politics and the accounting system are all held
> constant - do the wards with higher measured flood hazard actually get more money?

## The headline

**In Bengaluru, the wards most likely to flood get smaller capital budgets - about 12.8%
smaller per standard deviation of flood hazard.**

The value of the result is in *where* the gap sits, which a single regression hides. Decomposing
it (`src/analyse_budget_channel.py`) into the total budget, the drainage line inside it, and
the resulting share:

| step | estimate | p |
|---|---|---|
| flood hazard → **total ward budget** | **−12.8%** per SD | <0.0001 |
| flood hazard → stormwater spend | −9.0% | 0.016 |
| flood hazard → stormwater *given* the total budget | +4.2% | 0.155 |
| flood hazard → stormwater **share** | +1.61 pp | 0.047 |

Read together: **the misallocation is in the size of the envelope, not in the drainage line
item.** Engineers allocating a ward's budget tilt slightly toward drainage when the ward is
flood-prone - but they are tilting a budget that was already smaller. A study that looked
only at the drainage line would have found a mild positive and concluded the system works.

Two results make that reading hard to escape:

- **There is no drainage-*specific* targeting.** A coefficient-contrast test shows the
  drainage tilt (+1.73 pp) is statistically indistinguishable from roads (+2.63 pp) or parks
  (+2.13 pp) - 0 of 5 contrasts significant. High-hazard wards tilt toward *outdoor civil
  works generally*, which is what low-lying, less-built-up land needs. Not a flood response.
- **It is not partisan.** Ward councillor party is matched for all 198 wards; alignment with
  the state ruling party is worth +1.9% (p = 0.68), and the hazard effect survives party
  fixed effects at −8.1% (p = 0.009).

### It replicates in four cities of six

| city | units | β per SD | p |
|---|---|---|---|
| Chennai | 15 zones | −20.1% | 0.095 |
| Pune | 7 wards | −15.4% | 0.052 |
| Ahmedabad | 29 wards | −14.6% | 0.325 |
| **Bengaluru** | **198 wards** | **−11.7%** | **0.002** |
| Mumbai | 24 wards | +26.8% | 0.442 |
| Surat | 10 zones | +45.9% | 0.272 |
| **pooled, city × year FE** | **283 units** | **−8.4%** | **0.018** |

**Meta-analysis across all six cities: −12.2%, p = 0.0001**, with *zero* heterogeneity
(I² = 0%, Q p = 0.50) - the six estimates are consistent with a single common effect, so
Mumbai's and Surat's positives are noise around it rather than contradictions. Robust to
estimator: OLS −9.6%, PPML −9.6%, median regression −12.2%.

Negative in four, positive in two - and the cities differ enormously in what they *can*
detect. Minimum detectable effect: **Bengaluru 12%**, Pune 27%, Chennai 46%, Ahmedabad 57%,
Mumbai 137%, Surat 162%. So the result is **established in Bengaluru**, **directionally
supported** by Chennai (p=0.095) and Pune (p=0.052), and **untestable** in Mumbai and Surat,
whose data cannot see anything short of a doubling. Dropping Bengaluru leaves −1.6%
(p = 0.87).
Both are small-N panels on coarse units: Mumbai reports budget *estimates* rather than
actuals across 24 wards, and Surat's hazard is aggregated up from wards to 10 budget zones,
leaving it the most spatially smoothed of the six. The non-replications are reported rather
than dropped; see `PAPER_DRAFT.md`.

---

## Why this needed building at all

**The climate data everyone reaches for cannot answer the question.** The World Bank CCKP
grid is 0.25° (~25 km). Across Bengaluru's 198 wards its heat indicator takes **six distinct
values**, with a coefficient of variation of 2.5%. At ward scale it is not climate - it is a
dummy for which grid cell a ward sits in, and it will absorb any spatial gradient you put it
next to. The first version of the falsification test failed for exactly this reason; the test
was broken, not the finding.

So hazard here is **terrain-derived**: HAND (Height Above Nearest Drainage) at 30 m from the
Copernicus DEM, the standard free proxy for pluvial flood susceptibility. It varies at the
scale the question needs, and it is validated before use, not after: against **395 observed
BBMP/KSNDMC flood points**, high-hazard wards contain flood points at **1.81× the density**
of low-hazard wards (ρ = +0.26). That gate was stop-or-go - the study does not proceed if
the hazard variable cannot find known floods.

---

## Period covered

**FY2013–2026 across six cities.** Each city's window is set by what it publishes:
Ahmedabad FY2013–25 · Mumbai FY2016–26 · Chennai FY2020–26 · Pune FY2016–25 ·
Surat FY2018–24 · **Bengaluru FY2013–22**.

Bengaluru alone stops early, and not for lack of data: the city redrew its wards from 198 to
243 and then split into **five separate corporations** in 2025, so the unit of analysis stops
existing. Tested anyway - post-2022 gives −5.8% on the old ward map and +3.5% on the new one,
neither significant (`src/analyse_post2022.py`).

## What is built

- **82,219 BBMP work orders**, FY2011–2026, ward-tagged and classified into three drainage
  definitions
- **2,157 sub-city units across 22 boundary layers** with hazard, terrain and drainage-stock
  indicators
- **2,088 unit-years across six cities** on a common within-city hazard definition
- **Ward crosswalk** 243 → 198, areal-weighted, routed by published delimitation. 86.8% of post-2022 spend lands on a stable 198-ward base; the remaining 13.2% is 225-regime, for which **no boundary file is published**, and is excluded rather than mapped through the wrong geography
- **`data/final/wards.gpkg`** - 198 wards × 29 attributes; open it in QGIS and check the
  study against it

### Three findings about measurement

1. **The tagging elasticity is 35×.** The same ₹23,081 crore is 1.3% or 45.9% "drainage" depending
   on which of three defensible keyword definitions you use. Reported as a headline result,
   not a footnote - 300 independently adjudicated orders show the medium tier is 99.1%
   precise with 95.5% recall, but **81% of the money it catches is bundled road-and-drain
   work**. (Labelled by reading each description twice, independently, with arbitration;
   two passes agreed on 298/300. An earlier regex-based adjudicator was discarded - it
   shared keywords with the classifier it graded and so returned a meaningless 100%.)
2. **Drainage is the least ward-attributable category in BBMP's own data** - 27% cannot be
   assigned to any ward, against 3–5% for most categories. Trunk drains cross wards by
   construction, which biases the headline toward zero.
3. **Resilience money hides in the roads budget**, which is why the tagging choice moves the
   answer so much.

---

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py --list          # the 24 stages, in dependency order
python run_all.py                 # everything (~1 h cold, almost all downloading)
python run_all.py --skip-slow     # skip the three network-heavy stages
python run_all.py --from analyse_budget_channel
```

`data/final/` is committed (1.6 MB), so **the analysis stages run on a fresh clone without
downloading anything**:

```bash
python run_all.py --from verify_benchmarks
```

Everything else is re-fetchable from public URLs with **no accounts and no credentials**.

| component | source | licence |
|---|---|---|
| Ward capital spending | BBMP Works Bill Public View via [OpenCity](https://data.opencity.in) | open |
| Ward boundaries, 22 layers | [DataMeet](https://github.com/datameet/Municipal_Spatial_Data), bharatlas | CC BY-SA 2.5 IN |
| Elevation | Copernicus DEM GLO-30 (public S3) | open, attribution |
| Extreme rainfall, time-varying | [CHIRPS](https://data.chc.ucsb.edu) daily 0.05° | public domain |
| Climate indicators | World Bank CCKP (`s3://wbg-cckp`) | CC BY 4.0 |
| Existing drainage stock | OpenStreetMap via Overpass | ODbL |
| Landslide hazard | GFDRR / World Bank Data Catalog | open |

### Robustness

Significant at **every** HAND threshold (1/2/3/5/10 m, −6.4% to −11.2%) and **strongest with
no threshold at all** (mean HAND, −13.6%, p = 0.0007). Holds with population dropped (−8.0%),
with satellite built-up area substituted (−7.5%), and with no controls (−11.1%) - the
controls shrink the effect rather than create it. Three estimators agree (OLS −9.6%, PPML
−9.6%, median −12.2%). The headline survives Bonferroni and FDR correction; the **+1.61pp
share result does not survive FDR (0.063)** and is reported as suggestive.

See [`LICENSE`](LICENSE) - the MIT licence covers the **code only**; two of the data sources
are share-alike.

---

## Six bugs worth knowing about

Each silently corrupted results before being caught. All are documented at the point in the
code that handles them, and [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) collects them.

- **163 of 198 BBMP ward CSVs use a different schema** - the header sits under a two-line
  report title. An unguarded `read_csv` parses 8% of the data and reports success.
- **BBMP published ward 21 as a byte-identical copy of ward 22.** Taken at face value this
  double-counts one ward and invents a spending record for another. Caught by an independent
  fuzzy name-join that disagreed with the numeric join for exactly one ward.
- **The FY2025-26 release is four files, one per ward regime.** The published headline
  describes only the 198-regime file, so a correct parser looks 2× wrong against it.
- **Two published boundary files are geometrically wrong**: bharatlas's Surat and
  Bengaluru-GBA have **lat/lon transposed**; DataMeet's Kanpur is **Web Mercator labelled
  EPSG:4326**. Both return plausible-looking but meaningless zonal statistics - Kanpur
  reported `rain20 = 0.0` until it was caught.
- **`pysheds` calls `np.in1d`**, removed in numpy 2.x. Every city failed, and the real error
  was masked by a downstream "No objects to concatenate".
- **Do not deduplicate work orders row-wise** - one job number legitimately appears once per
  bill instalment. Row-level dedup deletes 3,240 real payment records.

---

## Layout

```
src/            24 pipeline stages; see run_all.py --list
data/final/     committed analysis-ready panels + wards.gpkg
output/
  tables/       every regression table as CSV
  figures/      F1-F7
  atlas.html    interactive ward atlas (open locally, no server)
PAPER_DRAFT.md      ~15 pp working paper
DATA_DICTIONARY.md  every file, every column, and the traps
```

Progress against the full plan: [`PROJECT_PLAN.md`](PROJECT_PLAN.md).
