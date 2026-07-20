# Citizen Ledger

_A nonpartisan record of California government spending._

A nonpartisan, static, interactive record of California state spending.
No frameworks, no build step, no server for the record: open `index.html`
in a browser and it works, including offline. (One scoped exception: the
city page's optional Map view uses vendored MapLibre GL JS and networked
basemap tiles — see STATUS.md; everything else stays dependency-free.)

## What's in the box

| File | What it is |
|---|---|
| `index.html` | The state-budget page on the Ledger design system: record surface with dollar ruler, proportional bar with drill-down, Allocation / Change / Trend / Actuals views, unit switching, cite + saved views. Zero runtime dependencies. |
| `data.js` | The dataset the state view renders: six years of enacted state budgets (2020-21 through 2025-26), generated from official data. |
| `pipeline/fetch_state_data.py` | Regenerates `data.js` from the Department of Finance's eBudget API, including prior-year actuals extracted from DOF Schedule 9 (`pipeline/schedule9.py`; needs `pypdf` only when refreshing actuals). |
| `cities.html` | The V2 local-government view, with a Cities / Counties layer switch: entity picker with search, governmental expenditures by function with per-resident figures, a separate enterprise-activities block, comparability footnotes, and a 2-4 entity side-by-side comparison (always within one layer — cities and counties are never compared to each other). |
| `city-data.js` | The city dataset: all 482 reporting cities × 8 fiscal years (2016-17 through 2023-24) of reported actual revenues and expenditures, generated from official SCO data. |
| `pipeline/fetch_city_data.py` | Regenerates `city-data.js` from the SCO "By the Numbers" Socrata API. Refuses to write unless every city-year total reconciles against the SCO's own published totals. |
| `county-data.js` | The county dataset: all 57 filing counties × 8 fiscal years (San Francisco files as a consolidated city and county and lives in the city data — counted exactly once). |
| `pipeline/fetch_county_data.py` | Regenerates `county-data.js` from the same SCO portal, with the same hard gate: refuses to write unless every county-year reconciles against the SCO's published control totals (`miui-wb29`). |
| `pipeline/make_county_boundaries.py` | Regenerates `county-geo.js` — 57 county boundaries plus a San Francisco polygon that routes to the Cities layer (Census, public domain). |
| `about.html` | About & method: sources per layer with accounting basis and cadence, the reconciliation gate stated plainly, the refusals and their reasons, the standing architecture rule, known limits, and the SHA-256 verification anyone can run. |
| `address.html` | The address view: enter a California address (or drop a pin) and see the governments that spend in your name — city or unincorporated county, county, school district(s) of residence, state — as stacked records that are never summed, plus the county's special-district count. Census-geocoded via JSONP; the address never leaves the browser except to census.gov and never enters permalinks, citations, or CSVs. |
| `schools.html` | The K-12 layer: 934 school districts compared per ADA — every district figure reproduces CDE's published Current Expense of Education to the cent before publication — with data-derived notes for basic-aid, small-district, and charter-sponsor distortions; county offices and charters as records only; and a live-computed statement of how this layer overlaps the state budget (they are never added). |
| `school-data.js` | Three fiscal years of gated district figures (with CDE's published total stored beside each recomputed one), county-office and charter records, and the pipeline-computed overlap block (1.9 MB). |
| `pipeline/fetch_school_data.py` | Regenerates `school-data.js` from CDE's SACS archives. Refuses to write unless every district-year reproduces CDE's published figure (in practice to the cent) and the ledger reproduces CDE's own rollups cell-by-cell. Needs mdbtools + openpyxl. |
| `districts.html` | The special districts layer, deliberately a different evidentiary tier: the finding first (the measured condition of the layer, recomputed live), the directory second (every district on record, with per-year filing status and a link to its own SCO filing), the as-filed numbers last — caveat on the face, no per-resident figures, no comparison, no totals. |
| `district-data.js` | ~5,200 districts × 8 years of as-filed figures, filing statuses, and the computed finding (2.2 MB — the largest data file, loaded only by districts.html). |
| `pipeline/fetch_district_data.py` | Regenerates `district-data.js` from the SCO portal. There is no reconciliation gate for this layer because no control-total dataset exists — that absence is the finding, and the pipeline computes every figure the finding states. |
| `pipeline/verify_digest.py` | Recomputes each data file's SHA-256 integrity digest (also shown on both pages under RECORD INTEGRITY). |
| `pipeline/make_ca_outline.py` | Regenerates the California outline embedded in `cities.html` from the Census cartographic boundary file (public domain), with the map's shared projection constants. |
| `pipeline/make_city_boundaries.py` | Regenerates `city-geo.js` — all 482 incorporated-place boundaries (Census, public domain), stdlib-only with hand-rolled Douglas-Peucker; fails with a named report unless every city matches. |
| `tests/run_tests.py` | Headless test suite — one command, 940 assertions on the real data. |
| `tests/mutation_test.py` | Mutation testing: tampers with one figure per layer (digest re-stamped) and requires the suite to catch it. A surviving mutation means the tests are reading the pipeline's claims, not the data. |
| `vendor/fonts/` | IBM Plex Mono (weights 400/500/600, latin and latin-ext), self-hosted under the SIL Open Font License 1.1 with `OFL.txt` alongside. Self-hosted so the pages load no third-party subresource and disclose nothing to a font CDN. |
| `deflator-data.js` | The price index behind the nominal/real toggle: DOF's published fiscal-year deflator, with its vintage, source digest, forecast years and the sentences that state the adjustment is the Ledger's own (5 KB). |
| `pipeline/fetch_deflator.py` | Rebuilds `deflator-data.js` from DOF's published file. Adopts DOF's fiscal-year averaging rather than deriving one; refuses to write if the sheet, column or vintage stamp changes shape. |
| `search.html` | Cross-layer search: one box over every layer at once. Results are **grouped by layer**, each group stating its own accounting basis, and carry **no figures at all** — a city, its county, its school district and its community-college district are never placed side by side as numbers. Entities with comparability notes in their own layer say so rather than showing a bare name. |
| `search-index.js` | The prebuilt index: 8,068 entities, names and identifiers only, built from the data files already shipped (466 KB raw, 86 KB gzipped). Loaded only by `search.html`. |
| `pipeline/build_search_index.py` | Rebuilds `search-index.js` from the shipped data. Adds no data. Refuses to ship an identifier it cannot prove resolves. |
| `revisions.html` | The record of changes: every figure that has moved since the record began, per layer, with a "check a citation" box that reads the generated date out of a pasted citation and reports whether that layer has changed since. Mechanical — it reports THAT a figure moved and by how much, never why. |
| `*-revisions.js` | One change record per layer (a few hundred bytes each when nothing has moved). Only `revisions.html` loads them, so no data page pays for the feature. |
| `pipeline/revisions.py` | Builds the change records. Every pipeline calls it before overwriting its data file, so a refresh records what moved without anyone being asked anything. Also carries the one backfilled historical event, whose cause is known rather than inferred. |
| `docs/SCOPE.md` | Standing scope decisions and the architectural rule: no server, no API keys, no per-use costs, no runtime third-party services — features requiring one are out of scope by default. Read it before proposing features. |
| `STATUS.md` | Data provenance: source, accounting basis, validation against published totals, and the history of how the source was chosen. |

## Run it

Double-click `index.html`, or:

```
cd ca-ledger
python3 -m http.server 8000     # then open http://localhost:8000
```

## Features

- **Appropriation bar with drill-down** — one proportional bar over a dollar ruler, grayscale ramp by size, ghost strip showing prior-year shares; click a segment or row to open that agency's departments.
- **Four views** — Allocation (sortable table with data-derived † method notes), Change (mirrored center-axis chart on a symmetric scale, gross decreases and increases always shown together), Trend (six-year columns plus per-agency small multiples), and Actuals — enacted beside published actual expenditures with a signed difference, both on the Budgetary-Legal basis (DOF Schedule 9, reconciled against Schedule 6 statewide controls before publication; the difference reflects mid-year legislation, re-appropriations, carryover, and reversions, and is never characterized).
- **Unit switching** — dollars, per resident, or % of total; every figure recomputes.
- **Federal funds toggle** — state funds only vs. state + federal pass-through.
- **Fund-source schedule** — General / Special / Bond / Federal.
- **Permalinks** — the full view state (year, view, unit, federal toggle, drill, sort, filter) lives in the URL hash; citations reproduce the exact view.
- **Cite + Download CSV** — a plain-text citation to the clipboard, and a CSV whose header names the source, basis, generation date, and permalink.
- **Saved views** — stored in localStorage on the reader's device only.
- **Record integrity** — each data file carries a SHA-256 digest, displayed on the page with instructions to verify it independently.
- **Nominal / real dollars** — the state, city/county and K-12 pages can restate a multi-year trend into constant dollars. **Nominal is the default and the record; real is a view over it.** Unlike every other figure on this site, this one is not reproduction: DOF, CDE and the State Controller all publish nominal figures and deflate nothing, so the adjustment is the Ledger's own methodological choice and every real figure says so — naming the index, its statutory basis (Education Code 42238.1), the base year and DOF's file vintage, in the view, in the citation and in the CSV. Fiscal years DOF flags as forecasts are never adjusted. The sensitivity to the choice of index is stated per layer on that layer's own face: over K-12's three-year window two defensible indices differ by 2.68 points (~42% of measured inflation) and can change a trend's sign; over the eight-year city/county window they differ by 0.6 points and disagree about one city in 482. The toggle is disabled where deflation is arithmetically inert (percent-of-total, and the enacted-vs-actual difference).
- **Cross-layer search** — nobody thinks "I want the county layer"; they think "Fresno". One box finds every government filing under a name — city, county, school district, county office, charter, special districts, community college, CSU, UC, and state agencies. Results are grouped by layer with each layer's accounting basis stated, and the index deliberately carries **no figures**, so nothing in the results view can be added or ranked across layers.
- **A record of changes** — each refresh diffs the figures it is about to publish against the ones already published and records what moved, keyed on stable identifiers. Figures that appear and disappear are recorded as well as figures that change, because a reclassification moves money between keys that did not previously exist. Detection compares figures, not file digests: a rebuild that only changes the build date is not a revision. The record says THAT a figure moved and by how much — never why, because a source restating a figure and a source redefining it are indistinguishable from the outside, and on the Controller's layers the prior figure cannot be reproduced by anyone.
- **Stable identifiers** — an entity's slug is a function of the source's published name and its own stable code (CDS, county, charter number), never of the order a build happened to iterate. The same source data always produces the same identifiers and the same digest. Where several entities share a published name, *every* one of them carries a qualified identifier: none holds the unqualified form, because that form names all of them. A link using a retired unqualified identifier is not silently resolved to a guess — the page says which entities it could have meant and lets the reader choose.
- **Map view (city page)** — a Search/Map toggle beside the search picker: every city's real incorporated boundary (Census, 410 KB GeoJSON) over a neutral Ledger-styled basemap — MapLibre GL JS (vendored, BSD) with OpenFreeMap vector tiles (keyless, swappable). Continuous zoom/pan with a Reset-to-statewide control and `m=` view permalinks; keyboard-accessible city buttons; selection identical to the search picker; graceful degradation (no library → message + search still works; no tiles → boundaries on parchment). Boundaries are uniform ink, selection keyed only by identity — the map shows where, never how much. The map is the ONE permitted dependency; the record pages remain dependency-free and work from a file double-click.
- **No third-party subresources** — every asset the pages load is served from this repository. The only runtime services are the map's keyless OpenFreeMap tiles and the address view's Census geocoder, both non-load-bearing and both named in `docs/SCOPE.md`; `test_runtime_origins` fails the build if a third appears.
- **Neutrality by construction** — direction is ▲▼ in ink, never red/green; the single blue is reserved for interactive controls; cities are always alphabetical; map dots never encode spending.
- Keyboard-navigable, print-ready (a citation header prints with the page).

## The data

- **Source:** the JSON API behind the Department of Finance's official
  eBudget site — `https://ebudget.ca.gov/api/publication/e/{year}/…` —
  the same data that renders ebudget.ca.gov's Enacted Budget pages.
- **Accounting basis:** enacted-budget expenditures, i.e. appropriations
  under California's Budgetary-Legal basis of accounting, fixed when each
  year's Budget Act is signed. These are spending plans, not audited
  actuals. (The state's actual-expenditure dataset, Open FI$Cal, covers
  only ~79% of budgetary spending and omits entire departments — see
  `STATUS.md` for why it was rejected as the primary source.)
- **What counts:** General, special, and bond funds make up the state
  total, matching the enacted Summary Charts exactly (2024-25 validates
  to the published $297,862M to the million). Federal funds are a
  user-controlled toggle. Reimbursements and nongovernmental-cost funds
  are excluded, as in the budget documents.
- **Update cadence:** one new fiscal year per annual Budget Act, signed
  each June. Enacted figures never change after publication, so the
  per-year cache in `pipeline/cache/` is permanent.

### Refreshing

```
python3 pipeline/fetch_state_data.py --inspect   # see available years
python3 pipeline/fetch_state_data.py             # fetch, rebuild data.js
python3 pipeline/fetch_state_data.py --years 2026-27   # when next year's act is signed
```

Population figures for the per-resident numbers come from DOF report
E-4 (statewide January 1 estimates) and are a constant in the script —
update once a year.

## Tests

```
python3 tests/run_tests.py
```

One command, 940 assertions against the real data files (the map assertions need network for basemap tiles): the actuals reconciliation gates (re-asserted against Schedule 6 control totals) and difference arithmetic, V1 and V2
rendering on the Ledger design system, drill-down and view/unit
controls, permalink hash round-trips, CSV export contents, citation
output, Change-view arithmetic, a banned-adjective scan, neutrality
checks (direction always in ink, never judgment colors), the corrected
city accounting labels (governmental activities — never "general fund
only"), the city comparability footnotes, the enterprise-fund block,
the county layer (its reconciliation gate re-asserted per county-year,
the unincorporated-share footnote, San Francisco's single-counting,
and the structural city/county layer separation), the special
districts layer (the caveat on every record, CSV, and citation; no
per-resident figure anywhere; no comparison or aggregate reachable;
finding figures rendered from the data file and absent from the page
source; the dashed unreconciled-tier surface vs. the gated layers'
solid one),
and the RECORD INTEGRITY digests (verified live with
`pipeline/verify_digest.py`). The suite serves the repo under a
`/ca-ledger/` subpath (the GitHub Pages layout), so it also proves
permalinks and citations emit the served public URL. Requires Python
3.9+, `pip install playwright`, and system Chrome (or `playwright
install chromium`).

### Mutation testing — do the tests verify the data, or the pipeline?

```
python3 tests/mutation_test.py            # every layer
python3 tests/mutation_test.py --list
```

A test can look rigorous and verify nothing. Before the UC layer
shipped, a review changed one campus figure by $1,000, re-stamped the
SHA-256 digest so the integrity check still passed, and ran the suite:
every assertion passed. The gate assertions were reading values the
pipeline itself had written instead of recomputing the reconciliation
from the shipped rows.

This harness makes that failure mode impossible to reintroduce. For
each of 24 targets it creates a throwaway git worktree, changes one
figure in a shipped data file, re-stamps the digest so the integrity
check cannot be what catches it, and runs the full suite. **Every
mutation must fail the suite; a surviving mutation is a hole in the
gates, not a bug in the script.** It deliberately includes *coordinated*
tampers that move a figure and every stored parent that would expose it —
those keep every in-file identity true, so nothing inside the file can
catch them. Only an anchor held outside it can: the source's published
control where one exists (community colleges, UC, CSU, state actuals),
and otherwise a recorded snapshot of the statewide totals currently
shipped (state budget, cities, counties, K-12, special districts) — which
detects the edit without claiming the source has re-confirmed the total.
A legitimate data refresh will fail those snapshot pins by design; the
constants are re-derived and reviewed, never updated silently. Use
`--ref` to test any commit.

## Licensing: open code, public-domain data, protected name

- **Code:** Apache License 2.0 (see [LICENSE](LICENSE)). Fork it,
  adapt it, build another state's ledger on it.
- **Data:** the generated data files are **CC0 1.0** — public domain.
  Cite freely; no permission needed.
- **Name:** "Citizen Ledger" is **not licensed for reuse** — the
  Apache license's trademark exclusion (Section 6), restated in
  [NOTICE](NOTICE). A fork may use the code and the data but may not
  present itself as Citizen Ledger or imply its figures are this
  project's verified record. Authentic figures are the ones whose
  SHA-256 digests match those published here (the Chromium/Chrome
  model: open code, protected name).

Security posture and how to report a problem: [docs/SECURITY.md](docs/SECURITY.md).

## Neutrality choices, on purpose

- No adjectives attached to numbers. No "only," no "ballooning."
- Every view shows shares and per-resident figures so scale is visible
  without editorializing.
- Federal pass-through is a user-controlled toggle, not an editorial
  decision baked into the total.
- Sources, method, and accounting basis are stated on the page itself.

## V2 (cities) — real data

`cities.html` runs on official data: all **482 reporting cities**,
fiscal years **2016-17 through 2023-24**, from the standardized annual
financial reports cities file with the State Controller's Office
(bythenumbers.sco.ca.gov, Socrata API). These are **reported actual
revenues and expenditures** — retrospective figures, not budgets —
a different basis from the state view, and the page says so.

Comparability is handled structurally, not with disclaimers alone:

- **Governmental vs. enterprise.** Function figures and the comparison
  view cover governmental activities only; ratepayer-funded enterprise
  operations (water, power, airports, harbors, hospitals, transit) are
  a separate block per city, because cities differ in which they run.
  Internal service funds and conduit financing are excluded from both.
- **Contract cities.** Police/fire service-provision codes from the
  SCO services checklist (most recent vintage FY 2015-16) plus a
  data-derived flag (under $5/resident) produce neutral footnotes in
  the detail view, the comparison, CSV exports, and citations.
- **San Francisco** is footnoted as the state's only consolidated
  city-county; its filings include county functions.
- **Single-year swings** (>±40% year over year) are footnoted so
  capital/debt spikes aren't read as trends.
- **Population** is the figure reported in the same SCO filing.
- **Reconciliation gate:** the pipeline refuses to write unless every
  city-year (482 × 8 = 3,856) reproduces the SCO's own published
  total-expenditures figure.

### Counties layer

The same page carries California's **57 filing counties** (fiscal years
2016-17 through 2023-24) as a separate layer, on the same basis, from
the same SCO portal, behind the same kind of hard gate: every
county-year (57 × 8 = 456) must reproduce the SCO's independently
published control total (`miui-wb29`) or nothing is written.

- **San Francisco is counted exactly once.** It files as the state's
  only consolidated city and county and appears in the Cities layer;
  it is absent from the county figures, and its polygon on the county
  map routes to the city record.
- **The unincorporated-share footnote** is the county equivalent of
  the contract-city problem: counties act as the direct local
  government mainly for residents of unincorporated areas, so each
  county's record carries a data-derived note stating what share of
  its residents live outside any city — per-resident differences
  partly reflect that responsibility share, not spending choices.
- **Cities and counties are never compared to each other.** The layers
  are structurally separate: switching layers clears the selection,
  slugs from one layer are invalid in the other, and the comparison
  view, CSV, and citations operate within a single layer.

## Special districts — a different tier, and it says so

`districts.html` is built finding-first, per the V5 investigation:
no control-total dataset exists for special districts, so the
reconciliation gate that protects every other figure on the site is
structurally impossible for this layer. The page leads with that
finding (every figure in it recomputed from the live data by the
pipeline), then a directory of every district on record — name, type,
county, per-year filing status, and a deep link to the district's own
filing on the Controller's site — and only then the as-filed numbers:
caveat on the face of every record, CSV, and citation; enterprise and
governmental funds kept apart; **no per-resident figures** (districts
have no resident denominator — the data file carries no population
field at all); **no comparison between districts**; **no totals**
(dependent districts' money also appears in city and county books).
The tier is visible at a glance: dashed hairlines, an open square
mark, no schedule number. No map: no statewide district boundary file
exists from Census or state sources, and the Ledger ships without one
rather than approximating.
