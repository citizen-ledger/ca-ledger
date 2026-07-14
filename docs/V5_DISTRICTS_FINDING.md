# V5 finding: counties, school districts, and special districts

_Investigated 2026-07-13. No UI or pipeline was built; this document is
the deliverable._

## Recommendations, up front — three layers, three different answers

| Layer | Recommendation |
|---|---|
| **Counties** | **(a) SHIP with comparison** — the city treatment extends almost verbatim, including the hard reconciliation gate, with one new comparability footnote (unincorporated-population share). |
| **Special districts** | **(b) SHIP as individual records only — never compared** — and only with an explicit disclosure that the city-grade reconciliation gate cannot exist for this layer. |
| **School districts** | **(c) DON'T SHIP from this program** — they are not in the SCO portal at all; a future, separate investigation of CDE's SACS data could revisit them on their own terms. |

## Counties

**Source.** Same Socrata portal, same dataset family, same design:
County - Expenditures (`uctr-c2j8`), County - Revenues (`emxv-k8xv`),
and — critically — **County Expenditures Per Capita (`miui-wb29`)**,
the same style of independently published control total the city
pipeline gates on (verified: Alameda FY 2023-24, total_expenditures
$4,244,700,272, estimated_population 1,641,869). Years 2003→2024,
annual cadence, one year per filing cycle.

**Schema.** Near-identical to cities: `entity_name, fiscal_year,
category, subcategory_1, subcategory_2, line_description,
estimated_population` — the value column is named `values` instead of
`value`, and rows carry zip/area extras. Fund structure mirrors the
city pattern exactly: governmental function groups (county versions —
Public Protection, Public Assistance, Public Ways & Facilities/Health/
Sanitation, Education & Recreation, General Government, Debt Service &
Capital Outlay) plus the same ten enterprise-fund categories, Internal
Service Fund, and Conduit Financing. **The city pipeline reuses with a
column mapping and a county function crosswalk — including the
governmental/enterprise separation and the same hard gate.**

**Completeness, measured.** **57 of 57 expected filers, every year
2017→2024** (58 counties minus San Francisco, which files as a city
and is already in our data with its consolidation footnote). SCO's own
delinquency dataset for FY 2023-24 shows **11 counties "Filed Late"
and zero failures** — everything arrives.

**Comparability.** Counties share the resident denominator, and DOF
population estimates exist per county — per-capita comparison is as
legitimate as it is for cities, **with one structural confounder that
must be footnoted the way contract cities are**: counties provide
direct municipal-type services mainly to unincorporated areas, so a
county that is mostly incorporated (e.g. Orange) spends per resident
very differently from one that is mostly unincorporated — a fact about
responsibility, not efficiency. The unincorporated-population share is
computable from DOF E-1 (county total minus sum of its cities), so the
footnote can be data-derived per county, exactly in the house style.
Small-county scale caveats (Alpine, ~1,100 residents) ride along
naturally. Enterprise separation works as for cities (county
hospitals, airports, utilities shown apart).

## Special districts

**Source.** Special Districts - Expenditures (`m9u3-wdam`) and
Revenues (`nkv3-m73r`), years 2003→2024, plus per-year rosters of
independent districts and per-year delinquency lists. Schema differs
in naming (`entityname`, `fiscalyear`, `value`) and adds three
classification fields: **`activity`** (40+ types: Fire Protection 334,
Cemetery 233, County Water 159, Mosquito Abatement 46 …),
**`districttype2`** (Independent / Dependent / JPA / Nonprofit), and
`sd_type`. Fund structure preserves the enterprise/governmental
distinction (verified: Water Enterprise Fund is the single largest
category by rows; Governmental Funds, ISF, and Conduit all present).

**Completeness, measured — the delinquency is real.** ~4,662 distinct
districts filed for FY 2023-24 (stable 4,5–4,7k across years), but
SCO's FY 2023-24 delinquency dataset contains **836 districts that
filed late or failed to file — roughly one in six expected filers**,
against 11-late/0-failed for counties. Any given year of this layer is
materially incomplete in ways that shift year to year.

**Control total: none exists.** There is no per-capita or totals
dataset for special districts — nothing independently published to
reconcile an entity-year against. **This is a material downgrade from
the city standard and must be disclosed as such**: district records
would be presented *as filed, unreconciled*, a lower evidentiary tier
than every other number on the site. The gate that protects cities and
would protect counties cannot be built here.

**Comparability: no honest comparison exists, even within type.**
1. **No denominator.** The data carries no population — correctly,
   because residents are not what districts serve. A water district
   serves connections and acre-feet, a healthcare district serves a
   service area, a cemetery district serves the deceased; none of
   these denominators is in the data, and none is shared.
2. **The type field cannot rescue it.** The two largest activities are
   **Joint Powers Authority (1,191 entities)** and **County Service
   Area (647)** — legal forms, not functions; a JPA may be an
   insurance pool, a power agency, or a transit operator. Within even
   a clean type (Fire Protection), district boundaries, mutual-aid
   arrangements, and dependent-vs-independent governance make
   like-for-like framing an editorial act we cannot verify.
3. **~15% of the universe is missing or late in any year**, so a
   "comparison" would silently omit an unknowable sixth of the layer.
4. **Cross-layer double counting:** 3,867 row-entries belong to
   *dependent* districts governed by counties or cities; presenting
   district totals beside county totals invites adding overlapping
   money. Records-only presentation avoids the implication.

**Enterprise vs. governmental.** Preserved in the data and essential
here: most of this layer is ratepayer-funded business activity (water,
sewer, hospital enterprise funds dominate). Any presentation must keep
the blocks separate and must not place ratepayer revenue beside
tax-funded city/county spending as if commensurable — one more reason
comparison is off the table while individual records are fine.

**Recommendation (b), with conditions:** individual district records,
searchable, with the same enterprise/governmental separation the city
page uses; the record header must state (i) as-filed and unreconciled
(no control total exists), (ii) the filing-status caveat with SCO's
delinquency lists linked per year, (iii) no comparison feature of any
kind — no per-capita figures at all, since no honest denominator
exists. If a comparison is ever demanded, the answer is the finding
above, not a chart.

## School districts

**They are not on the SCO portal.** A full-text catalog search of
bythenumbers.sco.ca.gov returns nothing for K-12 or school-district
finance; SCO's local-government reporting covers counties, cities,
special districts, transit operators, and streets/roads. School
district finance lives with the **California Department of Education**
(SACS unaudited actuals, published annually per LEA, ~1,000 districts
plus county offices and charters, with the Ed-Data partnership as the
public face).

That is a different source, schema, filing regime, audit trail, and —
importantly — a different *legitimate* denominator (per-pupil/ADA is
standard in education finance in a way per-resident is not). None of
the city pipeline, gates, or comparability work transfers. Extending
the Ledger to schools would be a separate program with its own V-cycle
investigation of SACS: possible in principle, out of scope for the
By-the-Numbers family, and not something to bolt on by analogy.
**(c) for this program**; revisit as its own investigation if wanted.

## Reproducibility

- Entity counts: SODA `count(distinct entityname/entity_name)` grouped
  by fiscal year on `uctr-c2j8` (counties: 57 every year 2017-2024)
  and `m9u3-wdam` (districts: 4,491–4,722).
- Delinquency: `4gmi-6up5` (counties FY 2023-24: 11 rows, all "Filed
  Late") and `9whd-sig6` (special districts FY 2023-24: 836 rows).
- Control totals: `miui-wb29` (57 county rows for FY 2023-24; fields
  total_expenditures / estimated_population / expenditures_per_capita);
  no special-district equivalent exists on the portal.
- Schemas and category structures: single-row samples plus grouped
  category counts, FY 2023-24, both datasets.
