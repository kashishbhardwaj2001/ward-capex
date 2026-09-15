# Data dictionary

Every file the pipeline writes, what its rows mean, and the traps in it.

Units throughout: **money in rupees** (not lakh, not crore) unless a column name ends
`_cr` or `_lakh`; **area in km²**; **length in metres**; **fiscal years as the calendar
year in which the year BEGINS** - `fy = 2013` is April 2013 – March 2014, written
"FY2013-14" in Indian usage. Getting that convention wrong shifts every series by one year.

---

## The analysis files - `data/final/`

### `wards.gpkg` - layer `wards_198`
**The canonical ward layer. One row per ward, 198 rows.** Open it in QGIS and the whole
study is checkable against it. Geometry EPSG:4326.

| column | meaning |
|---|---|
| `ward` | BBMP ward number, 1–198, 2012 delimitation. The join key everywhere. |
| `ward_name` | Ward name as published on the polygon file |
| `assembly_const` | Karnataka assembly constituency containing the ward |
| `pop_2011`, `pop_sc`, `pop_st`, `pop_m`, `pop_f` | 2011 Census, from the polygon attributes |
| `area_sq_km` | Area as published; `area_km2` is recomputed from the geometry in UTM 43N |
| `reservation` | Seat reservation category for the 2015 council election |
| `rain20mm_days`, `rain50mm_days`, `hot_days_35c`, `consec_dry_days`, `precip_annual` | CCKP polygon means. **⚠ Near-constant within the city** - see the warning below. |
| `landslide` | GFDRR global landslide hazard, polygon mean |
| `hand_m` | **The hazard variable.** Height Above Nearest Drainage, metres, Copernicus DEM 30 m. LOW = flood-prone. |
| `hand_lt5m_share` | Share of the ward's cells with HAND < 5 m. This is what `z_hazard` standardises. |
| `twi`, `slope`, `elev_m` | Topographic wetness index, slope, elevation - all DEM-derived |
| `n_years`, `total_capex_cr`, `drain_cr`, `drain_share_pct` | Panel aggregates over FY2013–2022, crore |
| `pop_panel`, `sc_st_share`, `z_hazard_panel` | The values the regressions actually used |

> **⚠ The CCKP columns are in this file for auditing, not for analysis.** At 0.25° (~25 km)
> they take about six distinct values across the whole city - `hot_days_35c` has a
> coefficient of variation of 2.5%. Used as a ward-level regressor they behave as a coarse
> spatial dummy, not as climate. This is the project's central methodological finding, and
> `src/analyse_falsification.py` demonstrates it rather than asserting it.

### `bengaluru_budget_panel.parquet` - **the headline estimation sample**
**One row per ward-year, 1,722 rows** (198 wards × FY2013–2022, minus empty cells).

| column | meaning |
|---|---|
| `unit` | Ward number as a string |
| `fy` | Fiscal year, beginning-year convention |
| `storm_spend`, `total_spend` | Stormwater and total capital spend, rupees, medium tier |
| `log_storm`, `log_total`, `storm_share` | Logs and the share in percentage points |
| `z_hazard` | Standardised `hand_lt5m_share`. **Higher = more flood-prone.** |
| `log_pop`, `z_log_density`, `z_dist_centre_km`, `z_sc_st_share` | Controls |
| `hand_m`, `twi`, `slope`, `elev_m`, `area_km2` | Terrain |

### `multicity_panel.parquet`
**One row per unit-year across six cities, 2,088 rows.** The `unit` is a **ward** in
Bengaluru (198) and Mumbai (24), and a **zone/ward-office** elsewhere - Chennai (15),
Ahmedabad (29), Pune (7), Surat (10). `z_hazard` is standardised **within city**, so a
coefficient is always a within-city comparison. Do not read across cities on the raw value.

> Surat's budget reports by zone while its polygons are wards; ward hazard is aggregated
> **up** to the zone via `data/raw/surat_ward_zone_weights.csv`. Its within-unit hazard
> variation is consequently the most smoothed of the six (sd 0.050).

### `bengaluru_final.parquet` / `bengaluru_panel*.parquet`
Ward-level cross-sections, 198 rows, carrying the category shares used by the
falsification test (`share_narrow/medium/broad`, `share_park`, `spend_road`, …) and both
hazard variables (`z_flood_hazard` from terrain, `z_heat_hazard` from CCKP - the latter
kept **only** to demonstrate it is unusable).

---

## Intermediate files - `data/interim/`

| file | rows | meaning |
|---|---|---|
| `bbmp_workorders.parquet` | 82,287 | One row per work order. `ward`, `fy`, `desc`, `amount`, `is_narrow/medium/broad`, `multiward`, `src`. **`src` identifies the source release, which matters - see the benchmark note below.** |
| `ward_hazard.parquet` | 2,157 | CCKP + GFDRR per polygon, 22 boundary layers. Keyed `(city, unit_id)` where `unit_id` is **polygon order in the source file**. |
| `ward_terrain.parquet` | 2,157 | HAND / TWI / slope / elevation, same key |
| `ward_chirps.parquet` | unit × FY | **Time-varying** extreme-rain days from CHIRPS daily 0.05°: `chirps_r20_days`, `chirps_r50_days`, `chirps_annual_mm`, `chirps_max_1day_mm` |
| `ward_drain_network.parquet` | 2,157 | OSM drainage line-work per ward: `osm_drain_total_m`, `osm_drain_engineered_m`, `drain_density_m_km2` |
| `ward_crosswalk_243_to_198.parquet` | - | Areal weights mapping the 2022 delimitation onto the 2012 base. Weights sum to 1.0 per new ward - **so "money preserved" through a merge is an arithmetic identity and is NOT a validation**; an earlier version reported 100% on exactly that basis and thereby hid a real routing bug. Apply these weights **only** to rows whose `regime` is 243. |
| `ward_join_manual.csv` | 0 | Every disagreement between the numeric and fuzzy ward joins, with the adjudication. **Empty is the correct state** - it was non-empty until the ward-21/22 bug below was fixed. |
| `label_sample_300_read.csv` | 300 | Classifier validation sample, labelled by **reading** each description twice independently (298/300 agreement) plus arbitration. `label_sample_300_adjudicated.csv` is the superseded regex-labelled version, kept only for the comparison in `validate_classifier.py` - it agrees with the read labels just 90% of the time. |

---

## Traps that cost real debugging time

**1. `unit_id` is positional.** It is the row order of the source GeoJSON, not a ward
number. Any join that reorders polygons silently mis-assigns hazard to wards. Bengaluru is
the exception: `WARD_NO` is on the polygons and is used directly.

**2. The pooled hazard/terrain tables carry every source layer's own attributes.** Twenty-two
cities' boundary files contribute columns like `ward_no`, `zone`, `Name`, `objectid`. A
merge on a generic key name gets suffixed away without error. Rename your key to something
unique first - `blr_ward`, `srt_ward`, `srt_zone` in this codebase exist for that reason.

**3. Published headline totals may describe one file of several.** The BBMP FY2025-26
release ships **four** files, one per ward regime (198 / 243 / 225 / Common). The published
headline of 4,729 rows / ₹3,169 Cr is the **198-regime file alone**; all four total 9,071
rows / ₹7,055 Cr. Compare against the wrong one and your parser looks 2× wrong when it is
right. `src/verify_benchmarks.py` pins this down.

**4. BBMP published ward 21 as a byte-identical copy of ward 22.** Taken at face value this
double-counts ward 22 and invents a spending record for ward 21. `build_panel.py` hashes
each ward file and drops the duplicate, keeping the copy whose filename agrees with the job
numbers inside it. Ward 21 has no FY2013-2022 data because none was ever published.

**5. Do not deduplicate work orders row-wise.** One job number legitimately appears on
several rows - one per bill instalment, with distinct SBR/BR/CBR numbers. Row-level dedup
on `(wo, amount, desc)` deletes 3,240 real payment records. The duplication problem was at
**file** level, not row level.

**6. Two published boundary files are geometrically wrong as shipped.** bharatlas's Surat
and Bengaluru-GBA files have **lat/lon transposed**; DataMeet's Kanpur file is **Web
Mercator labelled EPSG:4326**. Both defects produce plausible-looking but meaningless
zonal statistics (Kanpur returned rain20 = 0.0 before the fix). The pipeline detects and
corrects both on read.

**7. Four FY2023-24 rows carry an office code in the ward column** (`R`, `o111`, `o132`,
`o157`) and describe city-wide works. They are dropped, not guessed at - 0.23% of that
year's money, reported rather than absorbed.
