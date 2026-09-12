# Does the Drainage Money Follow the Flood Risk?

**Ward-level evidence on whether Indian municipal capital spending tracks measured climate hazard.**

> Within a city — where the budget, politics and administration are held constant — do
> wards with higher measured flood hazard actually receive more drainage capital spending?

**Headline result: in Bengaluru, no.** Across 68,635 ward-tagged capital work orders
(₹23,132 crore, FY2013–2022) and all 198 wards, the relationship between terrain-derived
flood hazard and drainage spending is positive but never statistically significant
(β = +1.1 to +1.5 pp per SD, p = 0.19–0.30). See [PAPER_DRAFT.md](PAPER_DRAFT.md).

---

## Why wards, not cities

Comparing cities confounds hazard with wealth: richer cities have both more assets at
risk and more money to spend. Comparing wards *inside* one city fixes the budget envelope,
the politics and the accounting system, so only hazard varies.

## Three findings beyond the headline

1. **The tagging elasticity is 29×.** The same budget is 1.3% or 46.0% "drainage" depending
   on which of three defensible keyword definitions you use.
2. **Resilience money hides in the roads budget.** Roads is the only category that
   significantly tracks flood hazard (β = +2.62, p = 0.049) — drainage does not.
3. **Drainage is the least ward-attributable category in BBMP's own data** — 27% of it
   cannot be assigned to any ward, versus 3–5% for most categories. Trunk drains span
   wards by construction, which biases the headline toward zero.

## A measurement prerequisite

The World Bank CCKP climate grid (0.25°) takes **six distinct values** across Bengaluru's
198 wards — it is a spatial dummy at this scale, not a climate variable. Hazard must be
terrain-derived. Figure `F6` documents this.

---

## Data — all free, no accounts

| Component | Source | Licence |
|---|---|---|
| Ward capital spending | BBMP Works Bill Public View via [OpenCity](https://data.opencity.in) | open |
| Ward boundaries, 17 cities | [DataMeet](https://github.com/datameet/Municipal_Spatial_Data) | CC BY-SA 2.5 IN |
| Elevation | Copernicus DEM GLO-30 (public S3) | open |
| Climate indicators | World Bank CCKP (`s3://wbg-cckp`) | open |
| Landslide hazard | GFDRR / World Bank Data Catalog | open |

## What is built

- **1,946 sub-city units across 17 Indian cities** with hazard and terrain indicators
- **82,443 BBMP work orders**, FY2011–2026, ward-tagged and classified
- **Ward crosswalk** 243 → 198 (areal-weighted, 100% of money preserved)

## Reproduce

```bash
python src/fetch_boundaries.py     # ward polygons, 17 cities
python src/fetch_bbmp.py           # 211 BBMP files (~37 MB)
python src/build_panel.py          # parse + classify work orders
python src/build_hazard.py         # CCKP indicators per ward
python src/build_terrain.py        # HAND / TWI / slope from Copernicus DEM
python src/build_crosswalk.py      # ward vintage crosswalk (gate G4)
python src/analyse_bengaluru.py    # first cut
python src/analyse_controlled.py   # with controls
python src/analyse_falsification.py# outcome-side falsification
python src/analyse_panel.py        # ward-year panel, FE, zero-inflation
python src/make_figures.py         # six figures
```

## Three bugs worth knowing about

Each silently corrupted results before being caught — they are documented in the code:

- **163 of 198 BBMP CSVs use a different schema** (header buried under a report title).
  An unguarded `read_csv` parses 8% of the data and reports success.
- **Surat's published boundaries have lat/lon transposed** — hazard values come back
  plausible but meaningless. `build_hazard.py` now sanity-checks every layer's bounds.
- **`pysheds` calls `np.in1d`**, removed in numpy 2.x. The real error was masked by a
  downstream "No objects to concatenate".

## Status

All four kill gates resolved. Bengaluru complete. Multi-city spending ingestion and
hazard validation against an official flood inventory are outstanding — see
[../PROJECT_PLAN.md](../PROJECT_PLAN.md).
