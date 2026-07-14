# Data status

_Last updated: 2026-07-08_

## Dataset used

**Enacted state budgets from the California Department of Finance**, via
the JSON API that powers the official eBudget site:

```
https://ebudget.ca.gov/api/publication/e/{fiscal-year}/appInfo
https://ebudget.ca.gov/api/publication/e/{fiscal-year}/statistics            # agencies
https://ebudget.ca.gov/api/publication/e/{fiscal-year}/statistics/{agencyCd} # departments
https://ebudget.ca.gov/api/publication/e/{fiscal-year}/rwaCntl/support/{orgCd}    # funds detail
https://ebudget.ca.gov/api/publication/e/{fiscal-year}/rwaCntl/capOutlay/{orgCd}
```

Dollar values in the API are thousands. Fund classes: G = General Fund,
S = Special, B = Bond, F = Federal, N = Nongovernmental-cost,
R = Reimbursements. The site's General/Special/Bond figures come from
`/statistics`; Federal is the sum of F-class rows in the two `rwaCntl`
tables. N and R are excluded, matching budget-document presentation.

This was not the first choice — see "How the source was chosen" below.

## Fiscal years loaded

2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26 — the six most
recent enacted Budget Acts (2025-26 signed June 27, 2025). A stub
2026-27 "Enacted" publication exists in the API with no data
(publication date "January 01, 9999"); the pipeline skips publications
whose `/statistics` is empty.

## Accounting basis

**Enacted appropriations under California's Budgetary-Legal basis of
accounting** — the spending plan fixed when each year's Budget Act is
signed. Not actual cash expenditures, not GAAP/ACFR audited figures.
Expenditures on this basis are recognized when funds are committed
(encumbered), so figures differ from both actual spending and audited
financial statements. Enacted figures never change after publication.

## Cross-check against ebudget.ca.gov

Most recent fiscal year (2025-26 Budget Act, signed June 27, 2025),
`data.js` vs. the published enacted figures¹:

| | data.js | Published | Difference |
|---|---|---|---|
| General Fund | $228.366B | $228.4B | −0.01% |
| Special Funds | $88.799B | ~$89B | −0.2% |
| Bond Funds | $3.886B | ~$4B | −2.9% (rounding: published to nearest $1B) |
| **Total state funds** | **$321.051B** | **$321.1B** | **−0.02%** |

Prior year (2024-25 Budget Act), against the printed Summary Charts²:

| | data.js | Published Summary Charts | Difference |
|---|---|---|---|
| General Fund | $211.504B | $211,504M | 0.000% |
| Special Funds | $83.985B | $83,985M | 0.000% |
| Bond Funds | $2.373B | $2,373M | 0.000% |
| **Total state funds** | **$297.862B** | **$297,862M** | **0.000%** |

¹ 2025-26 enacted totals as published in the California State Budget
2025-26 (ebudget.ca.gov Full Budget Summary) and reported identically by
the Legislative Analyst's Office ("The 2025-26 Budget: Overview of the
Spending Plan", lao.ca.gov/Publications/Report/5079) and the Senate
budget committee's Summary of the Budget Act of 2025: $321.1B total
state spending, $228.4B General Fund, ~$89B special funds, ~$4B bond
funds. (Published secondary sources round special/bond funds to the
nearest billion; the sub-0.1% total difference is that rounding.)

² "2024-25 Total State Expenditures by Agency", California State Budget
2024-25 Summary Charts (ebudget.ca.gov, enacted edition), p. 9.

Every loaded year also reconciles against the API's own
`stateGrandTotal` field with at most $2k drift (rounding). One caveat:
two agencies (Transportation, Legislative/Judicial/Executive) differ
from the *printed* 2024-25 chart by ±$2-3B because the API reflects
DOF's current agency mapping rather than the org structure printed at
enactment; the statewide total is identical.

## How the source was chosen

1. **Open FiscalCal on data.ca.gov** (the source the original pipeline
   assumed): does not exist. data.ca.gov's CKAN catalog has no state
   expenditure dataset; its "fiscal" organization is empty.
2. **Open FI$Cal** (open.fiscal.ca.gov, "Monthly Spending Transaction
   Files", ~1.5 GB CSV per month on Azure blob storage): real actual
   expenditures (modified accrual for FI$Cal departments, cash basis
   for the rest), but covers only **~79% of budgetary expenditures**
   (per its own About page) — and the gap is concentrated: CDCR,
   Caltrans, DOJ, and the Department of Water Resources run their own
   accounting systems ("deferred" departments) and are absent entirely;
   UC and CalPERS/CalSTRS are exempt. Aggregated FY 2024-25 actuals:
   state funds **$257.6B vs. $297.9B enacted (−13.5%)** overall, but
   Corrections showed **$0.29B vs. $18.2B enacted (−98%)** — an
   agency-proportional display would have been materially misleading,
   so this source was flagged and rejected for the site's primary view
   (2026-07-08). The working FI$Cal pipeline is preserved in git
   history (first commit).
3. **eBudget enacted publications** (chosen): full coverage of every
   agency and department, department-level fund detail, and totals that
   reproduce the published enacted Summary Charts exactly.

## Pipeline changes

- `pipeline/fetch_state_data.py` was rewritten twice: the original CKAN
  datastore fetcher (unverified placeholder `RESOURCE_ID`) → an Open
  FI$Cal blob-streaming aggregator → the current eBudget API client.
- Added a permanent per-year cache (`pipeline/cache/enacted_*.json`,
  gitignored) — enacted figures never change, so years are fetched once.
- Null fund fields in some API department rows are coerced to 0.
- Population constants updated to DOF report E-4 (2026 vintage, revised
  Jan-1 estimates: 39.38M → 39.59M across the loaded years); the
  sample data's figures were stale.
- `index.html`: two data-robustness fixes for values real data contains
  but the sample did not — negative amounts (e.g. Government Operations
  special funds in 2022-23 is officially **−$563M**; now rendered with
  a proper minus sign, and department bar widths clamped at 0) — plus
  copy updates: the dek says "enacted state budget", and the footer
  states the accounting basis. No visual-design or interactivity
  changes.

## Verification pass (2026-07-08, follow-up session)

A second session re-verified the pipeline and site before publishing.

- **Live API re-run blocked by the session environment, not the script.**
  `fetch_state_data.py --inspect` and a full `--refresh` run could not
  execute from this container: its egress policy denies
  `ebudget.ca.gov` (proxy answers 403 to CONNECT; lao.ca.gov and other
  ca.gov hosts are likewise blocked). No code change fixes this — the
  pipeline is unchanged, and should be re-run with `--refresh` once from
  a network that can reach ebudget.ca.gov to independently reproduce
  `data.js`. `RESOURCE_ID` no longer exists in the script; the CKAN
  fetcher it belonged to was replaced entirely (see "Pipeline changes").
- **data.js internal consistency verified** (script-independent, run
  locally): six fiscal years present; `meta.source` is
  `ebudget.ca.gov`, not `SAMPLE`; per-year agency sums match the
  `trend` block for all years; no agency exceeds 60% of its year's
  state-funds total (max: Health and Human Services, 41.4% in
  2025-26, 54.6% with the federal toggle on); adjacent year totals are
  all within 1.3x of each other.
- **Cross-check against published totals** (table above): 2025-26 total
  state funds differ from the published $321.1B by 0.02%; General Fund
  by 0.01%. Published figures were taken from LAO and Senate budget
  committee summaries because ebudget.ca.gov itself was unreachable
  from this environment.
- **Rendering verified in headless Chromium** (localhost, real
  `data.js`): the yellow sample-data banner is gone (replaced by the
  neutral source line "Data: Enacted state budgets, Budgetary-Legal
  basis…"); the appropriation bar renders all 12 agency segments;
  clicking a segment opens the department drilldown (HHS → 25
  departments, Health Care Services $74.3B at top); the trend chart
  shows the six real years ($202B → $263B → $308B → $311B → $298B →
  $321B); the federal-funds toggle recomputes every figure (adds the
  $176B federal row); the fund-source panel and footer render. The only
  console errors are the Google Fonts stylesheet (blocked by this
  sandbox's network) and a missing favicon — neither is a data issue.
- **Known negative amounts, kept on purpose:** the enacted data
  legitimately contains negative appropriations, all small and all
  official — e.g. Statewide General Admin Expenditures (Pro Rata)
  around −$0.7B to −$1.0B GF each year, Public School System
  Stabilization Account −$2.6B to −$0.9B special funds in 2021-22
  through 2024-25, Office of Emergency Services −$3.9B special funds
  in 2022-23, and at agency level Government Operations −$563M special
  funds in 2022-23. These match the published budget documents (they
  are offsets/transfers, not errors) and render with a proper minus
  sign; they are flagged here rather than silently altered.

## Follow-up pass (2026-07-08, merged to main)

- **Reproducibility run still pending.** This environment also cannot
  reach ebudget.ca.gov, so the independent `--refresh` re-run of the
  pipeline (regenerate `data.js` from the live API and diff against
  the committed file) remains deferred until someone runs it from an
  unrestricted network. The pipeline script is unchanged.
- **Hero dek accuracy: already fixed.** The dek reads "Every dollar of
  California's enacted state budget, drawn to scale" (changed from the
  original "spends" phrasing in the real-data commit); no occurrence
  of the expenditure wording remains in the repo. No copy change was
  needed this pass.
- **Negative-appropriation rendering verified headlessly** (Chromium,
  FY 2022-23, committed `data.js`): opened the three affected
  drilldowns — General Government (Pro Rata −$47M net, Public School
  System Stabilization Acct), Legislative/Judicial/Executive (OES
  special funds −$3.9B), Government Operations (special funds −$563M
  at agency level). Every department bar's rendered width is ≥ 0
  (negative net amounts get a zero-width bar and a minus-signed
  figure, e.g. "−$47M"); no bar overflows its track; no console
  errors. The drilldown fund strip omits a fund class whose total is
  ≤ 0 (so Government Operations 2022-23 shows only General Fund and
  Bond Funds in the strip while the header total reflects the −$563M
  special funds); the remaining segments' declared widths can exceed
  100% but the strip is `display:flex` with `overflow:hidden`, so they
  compress to fit the container — measured 972px of segments in a
  974px track, no visual overflow. Nothing was broken, so no rendering
  code was changed.

## Citizen-tools release (2026-07-08)

Five features added to `index.html` (no frameworks, no dependencies, no
build step; the site still works from a double-click on `index.html`):

1. **Permalinks** — full view state (fiscal year, federal toggle,
   selected agency, both table sorts, filter query) is encoded in the
   URL hash and restored on load; plain `#anchor` links are ignored by
   the state parser.
2. **CSV export** — "Download this data" generates a CSV of the current
   table view client-side, with `#`-comment header lines naming the
   source dataset, accounting basis, generation and export dates, the
   displayed fund scope, and any active filter; the raw `data.js` is
   linked beside it.
3. **Change from the prior year** — a per-agency table of year-over-year
   change in dollars and percent, sortable, increases and decreases
   always rendered together in one view; the earliest loaded year
   states that no prior year exists.
4. **Cite** — the agency detail panel copies a plain-text citation to
   the clipboard: figure, agency, fiscal year, source dataset,
   accounting basis (enacted appropriations, Budgetary-Legal basis),
   permalink, and access date, with a `document.execCommand` fallback
   where the async clipboard API is unavailable.
5. **Methodology section** — what the figures are and are not, the
   exact source and annual late-June cadence, and the known caveats:
   the negative-appropriation inventory above, the fund-mix strip's
   omission of net-negative fund classes (its segments show shares of
   the positive-fund subtotal), department rows not always summing to
   agency totals, and the source's current-organizational-structure
   agency mapping. Linked from the top banner and the footer.

Both data tables' sort headers are now real buttons with `aria-sort`,
so sorting is keyboard- and screen-reader-accessible. Direction color
uses only the palette already in the stylesheet (the same two classes
the header's vs.-prior-year figure has used since V1), applied
symmetrically to increases and decreases.

**Tests (headless Chromium, 55 assertions, all passing):** hash-state
restore on load (year, toggle, agency, sort, query, and the filtered
table it implies); every interaction writing the hash plus a
round-trip reload of a produced URL; CSV contents byte-for-byte
(comment header lines, column header, first data row against data.js
values to three decimals, quoted comma-containing agency names, totals
row present unfiltered and absent when filtered); change-view
arithmetic against data.js, presence of both directions in one view,
sort behavior, and the earliest-year notice; citation text (figure,
basis, source, permalink, access date) via the real clipboard; the
methodology section's presence and links; and a `file://` load with
hash restore, hash sync, and CSV download working. A banned-term scan
(surge/slash/ballooning/soar/plunge/skyrocket) over the whole page
comes back clean.

## Public-hosting preparation (2026-07-08)

- `.github/workflows/deploy-pages.yml` deploys the repo root to GitHub
  Pages on every push to main (official actions: configure-pages,
  upload-pages-artifact, deploy-pages; no build step). Requires the
  repository's Pages source to be set to "GitHub Actions" by hand.
- Permalinks and the Cite feature already derive their base URL from
  `window.location` — verified under a simulated project-pages subpath
  (`/ca-ledger/`) that hash restore, hash sync, and the citation
  permalink all carry the deployed URL, and that `file://` use still
  works.
- SEO/social metadata added to `index.html`: description, canonical,
  Open Graph, and Twitter-card tags, all using the same neutral
  sentence ("A nonpartisan public record of California's enacted state
  budget, by agency, department, and fund source"); the canonical and
  og:url point at the default project-pages URL and should be updated
  if a custom domain is attached.
- `robots.txt` (plain allow-all) and `favicon.svg` (ledger ruling on
  the site's green with the gold accent, palette colors only) added.
  Note: on a project-pages subpath, crawlers consult the domain root's
  robots.txt (github.io's), not this file; it becomes authoritative
  under a custom domain.
- Headless tests: 18 assertions (metadata completeness, robots/favicon
  served, subpath permalink/cite behavior, file:// intact), all
  passing.

## V2 city view — preview on sample data (2026-07-08)

- `cities.html` added, sharing the V1 design system, self-contained
  like V1 (no frameworks, no dependencies, works from a double-click).
  Features: searchable city picker; city detail with a proportional
  expenditure bar by function, per-resident figures, and a function
  table; and a comparison view where 2-4 cities show per-resident
  spending by function side by side — bars in each row share one
  scale, column order is the user's selection order, and no
  highest/lowest labeling of any kind. Permalinks (`y`, `c`, `cmp`,
  `q`), CSV export (city and comparison), and Cite all work on the
  city views.
- `city-data.js` is **SAMPLE data**: 18 California cities × 3 fiscal
  years × 10 expenditure functions, deterministic illustrative figures
  sized from real 2023 populations, in a schema modeled on the SCO
  city annual financial reports. `meta.source` is `SAMPLE`, which
  drives the same yellow banner V1 used; CSV exports and citations
  from this page carry an explicit "SAMPLE DATA … do not cite" line.
- `pipeline/fetch_city_data.py` targets the SCO "By the Numbers"
  Socrata API (bythenumbers.sco.ca.gov). **Endpoints unverified** — it
  was written in this network-restricted environment (sco.ca.gov and
  socrata.com are egress-blocked, verified at write time). The script
  documents exactly what to verify on first unrestricted run (catalog
  search, dataset id, column map, function-category map), refuses to
  guess, and never overwrites city-data.js unless a fetch validates.
  Note the basis difference from V1: city reports are **actual
  revenues and expenditures**, not enacted budgets; the page footer
  says so.
- Headless tests: 54 assertions on the city page (sample banner and
  color, picker search, detail figures and shares recomputed from
  city-data.js, comparison per-capita values and per-row shared
  scaling, duplicate-selection dedupe, permalink restore, both CSVs
  byte-checked including SAMPLE lines, citation content, keyboard/ARIA
  spot checks, banned-term scan, file:// load) — all passing. V1
  regression suites re-run: 55 + 18 assertions, all passing.

## Network-dependent tasks attempted again (2026-07-08, later session)

All three planned network tasks were attempted from a fresh session;
the environment's egress policy still blocks the data hosts, so the
data tasks remain pending. Exact findings:

- **V1 reproducibility run: still blocked.** `fetch_state_data.py
  --refresh` cannot reach ebudget.ca.gov (proxy answers 403 to
  CONNECT; the sandboxed web-fetch channel also gets 403). The
  regenerate-and-diff check remains pending on an unrestricted
  network. No change to data.js.
- **V2 real data: still blocked, and deliberately not faked.**
  bythenumbers.sco.ca.gov and api.us.socrata.com are both denied on
  every available channel, so the Socrata endpoints stay unverified
  and no aggregation was implemented — the script's policy is to
  refuse to write from guesses, and that held. What did move forward:
  the comparability investigation was completed from published
  research and encoded as blocking requirements in the script's
  docstring — contract cities (county-provided police/fire; measured
  as systematically lower per-capita police spending with demographic
  confounds), enterprise funds (ratepayer-funded utilities that only
  some cities operate; the schema must keep governmental and
  enterprise activity separate and compare governmental by default),
  the San Francisco city-county consolidation, single-year
  capital/debt spikes, and same-vintage population denominators. The
  stated rule: if these cannot be resolved from the data plus a
  maintained flag list, ship city detail only and keep the comparison
  feature off real data. The V2 page remains on labeled sample data.
- **GitHub Pages: workflow verified, deployment awaiting a settings
  change.** Both runs of "Deploy to GitHub Pages" failed in
  `actions/configure-pages` with "Get Pages site failed … Not Found",
  which means Pages is not yet enabled for the repository. The
  workflow itself checked out and ran correctly up to that step. Two
  settings facts matter: (1) Settings → Pages → Build and deployment
  → Source must be set to "GitHub Actions"; (2) the repository is
  currently **private** — GitHub Pages on a private repository
  requires a paid plan (and the published site is public regardless),
  so the repo may need to be made public first. Once enabled, re-run
  the workflow from the Actions tab; permalinks and citations already
  derive their URLs from `window.location`, verified earlier under a
  simulated `/ca-ledger/` subpath, so they will emit the public URL
  as soon as the page is served from it.

## Reproducibility verified from an unrestricted network (2026-07-13)

The pending V1 reproducibility check ran from a machine with normal
egress (ebudget.ca.gov reachable, HTTP 200):

- `python3 pipeline/fetch_state_data.py --refresh` refetched all six
  enacted years live (~3,000 API requests). Every year reconciled
  against the API's `stateGrandTotal` as before; the same two known
  plausibility notices printed (the official negative special-fund
  totals in 2022-23).
- The regenerated `data.js` differed from the committed one in exactly
  two lines: the generated-on date in the header comment and
  `meta.generated` (2026-07-08 → 2026-07-13). **Every data byte was
  identical.** The committed file was left in place; there is nothing
  substantive to update.
- The 2026-27 "Enacted" publication was re-checked and is still the
  empty stub (publication date "January 01, 9999"); the pipeline
  correctly excludes it.

## V2 city data loaded from the live SCO API (2026-07-13)

Both hosts the earlier sessions could not reach were reachable from
this machine (HTTP 200), so the pending network tasks ran.

**Datasets verified on bythenumbers.sco.ca.gov (Socrata):**
`ju3w-4gxp` City - Expenditures, `rrtv-rsj9` City - Revenues,
`ykhf-vfsr` City Expenditures Per Capita (official totals, used as the
reconciliation target), `tsz3-29gc` Check List of Services Provided
(FY 2015-16 vintage; provision codes A-K decoded from the dataset's
"City Service Codes.docx" attachment). `fiscal_year` is the ending
year ("2024" = FY 2023-24); values are dollars; population is
`estimated_population` from the same filing.

**Structure found and encoded:** `category` distinguishes governmental
activity (function groups in `subcategory_1`, lines like
"Police_Current Expenditures" in `subcategory_2`) from ten
"… Enterprise Fund" categories, Internal Service Fund, and Conduit
Financing. The load keeps governmental and enterprise blocks separate,
excludes internal service and conduit from both, and maps whole SCO
lines to 15 display functions (police, fire, other public safety,
streets & transportation, community development & housing, sewer &
solid waste, health & welfare, parks, libraries, other culture &
leisure, governmental public utilities, general government, other,
debt service, capital outlay) — nothing dropped, nothing counted
twice: the identity gov + enterprise + internal service + conduit =
official SCO total was verified for Los Angeles by hand
($21,517,484,103 exactly) and is enforced by the pipeline for every
city-year; a load that fails it will not write city-data.js.

**Loaded:** 482 cities × 8 fiscal years (2016-17 … 2023-24), all
3,856 city-years reconciled, zero sanity-check failures.
city-data.js is 1.4 MB (compact JSON).

**Comparability requirements, as implemented:**
- Contract cities: checklist codes (e.g. Lakewood police = "contract
  with the county", fire = "special district without city contract" —
  calibration: Lakewood $103/resident police vs Los Angeles $855)
  plus a current-year flag when a line is under $5/resident. Footnoted
  in city detail, comparison, CSVs, and citations.
- Enterprise funds: comparison view and function figures are
  governmental-only (stated in the UI); each city's enterprise
  activities render as their own block.
- San Francisco: flagged consolidated (confirmed from the data — it is
  the only city reporting county lines such as Assessor and District
  Attorney).
- Capital/debt spikes: capital outlay and debt service are visible
  functions, and a >±40% year-over-year swing in governmental
  expenditures footnotes the year.
- Population: same-filing figure, never a mixed vintage.

The comparison view therefore ships with real data (the documented
fallback — detail-only — was not needed). The services-checklist
vintage (FY 2015-16, the most recent the SCO publishes) is stated
wherever its codes appear.

## Pre-deploy pass (2026-07-13): committed tests, checklist caveats, deploy check

- **Headless test suite rebuilt and committed** at `tests/run_tests.py`
  (the earlier sessions' suites were run but never committed). One
  command — `python3 tests/run_tests.py` — runs 104 assertions with
  Playwright + Chrome against the real data files, recomputing every
  expected figure independently in Python: V1/V2 rendering, permalink
  hash round-trips (both directions), CSV export contents (headers,
  scope lines, data rows, totals), citation output via the clipboard,
  change-view arithmetic (per-agency and totals-row dollar/percent
  deltas), a banned-adjective scan on both pages' rendered text, the
  city comparability footnotes (checklist vintage, contract-city and
  fire-district notes, San Francisco consolidation), and the
  enterprise-fund block. All 104 pass.
- **Methodology caveats stated on both pages:** the service-provision
  flags derive from the SCO services checklist whose most recent
  published vintage is FY 2015-16; arrangements may have changed since;
  and the under-$5/resident flag is a heuristic backstop, not a
  current-year survey. (index.html Methodology → "The city view";
  cities.html Sources & method.) The stale "planned for V2" line in
  the V1 footer now links to the live city view.
- **Deploy check:** `.github/workflows/deploy-pages.yml` uploads the
  repository root as the Pages artifact, so both `index.html` and
  `cities.html` (plus `data.js`, `city-data.js`, favicon, robots.txt)
  deploy together. Permalinks and citations derive from
  `window.location`; the test suite serves the site under a
  `/ca-ledger/` subpath — the GitHub Pages layout — and asserts that
  citations emit that served URL, so they will emit the public URL in
  production. Deployment itself still awaits the repository settings
  change documented earlier (repo is private; Pages must be enabled
  with Source = GitHub Actions).

## Redesign: the Ledger design system (2026-07-13)

Both pages were rebuilt to the design-handoff bundle ("Ledger /
accounting ledger" direction) — still dependency-free vanilla
HTML/CSS/JS that works from a file double-click; the data layer,
pipelines, and test entry point are unchanged. Deviations from the
handoff, per instruction:

- **Revisions view and source-trace panels dropped.** The eBudget
  pipeline fetches neither Governor's-proposal figures nor document
  page references, and the Ledger does not stub records with
  placeholder data. Allocation, Change, and Trend shipped.
- **City accounting labels corrected.** The handoff described the city
  data as "general fund only, enterprise funds excluded"; the actual
  data is **governmental activities** (broader than the general fund),
  with enterprise activity shown separately. Every label, hero
  substat, schedule heading, and method note was rewritten
  accordingly, and the test suite asserts the corrected language
  (including that "general fund only" appears nowhere).
- **8-city chip picker replaced** with the search-based picker over
  all 482 cities; selection capped at 4, comparison requires 2–4.
- **Preserved features the handoff omitted:** the federal-funds
  toggle, the comparability footnotes (contract cities with the
  FY 2015-16 checklist vintage caveat, San Francisco consolidation,
  ±40% single-year swings), and the per-city enterprise-fund block.
- **RECORD INTEGRITY is real.** Both pipelines now stamp
  `meta.integrity` with the SHA-256 of the canonical JSON payload
  (sorted keys, compact separators, digest field excluded so the
  digest can live inside the file it certifies).
  `pipeline/verify_digest.py` recomputes and compares; both pages
  display the live digest with verification instructions, and the
  test suite runs the verifier.
- **Georgia serif** (Untitled Serif is licensed and not licensed here).

Neutrality rules from the handoff are implemented and tested:
direction renders as ▲▼ in ink (the legacy green/red delta classes are
gone and a test asserts grayscale), the Change view uses a mirrored
center-axis chart on a symmetric scale with both gross totals always
shown, comparison cities are always alphabetical regardless of
selection order, and the one blue is reserved for interactive
affordances. The caption "▲▼ SHOW DIRECTION ONLY; THE LEDGER DOES NOT
CHARACTERIZE CHANGES" ships as-is.

The test suite was reworked for the new UI: every prior assertion has
a meaningful equivalent, plus new coverage for the corrected city
labels, integrity digests, unit-switch arithmetic, drill-down, and
saved views — **135 assertions, all passing** on the real data files.

## Map view added to the city page (2026-07-13)

A navigational map alongside the search picker (Search / Map toggle —
the search picker is unchanged). Dependency-free: the California
outline is a single inline SVG path generated by
`pipeline/make_ca_outline.py` from the U.S. Census Bureau cartographic
boundary file `cb_2023_us_state_20m` (public domain, 1:20M
simplified, 6 rings / 468 points), parsed with a stdlib-only
.shp/.dbf reader; the page fetches nothing at runtime.

- **Coordinates**: `pipeline/fetch_city_data.py` now attaches lat/lng
  to every city from the Census 2024 place gazetteer (public domain),
  matched on normalized name against California's 482 incorporated
  places (LSAD city/town — an exact one-to-one with the SCO's 482
  reporting cities). Two names needed explicit aliases, recorded in
  the script: SCO "Amador" = Census "Amador City city", SCO
  "Mt. Shasta" = "Mount Shasta city" (plus UTF-8 handling for La
  Cañada Flintridge). An unmatched city fails the write with a report
  — never guessed, never silently dropped. 482/482 matched; the
  integrity digest was regenerated and verifies.
- **Neutrality (hard rule)**: dots are uniform ink — a single computed
  fill and opacity for every unselected dot, asserted by the test
  suite. Dot area scales with population (a fact about the place);
  the map encodes position and population only, never spending. The
  on-page caption says so. Selected cities take the comparison view's
  swatch shades in the same alphabetical order.
- **Density**: solved with six neutral geographic region zooms
  (Statewide / North / Bay Area / Central Valley / Los Angeles Basin /
  South) as pill controls — chosen over pan/zoom or hover-only
  disambiguation because preset regions are deterministic,
  keyboard-accessible, shareable in the permalink (`r=`), and printable;
  free pan/zoom is fiddly without a library and hard to encode in a
  citation. Dot screen size stays constant across zooms, so metro
  dots separate cleanly at regional scale.
- **Interaction**: dots are focusable buttons (role=button,
  tabindex=0, aria-labels with name, population, county); click or
  Enter toggles selection through the same code path as the search
  picker — same state, same hash, same record below (asserted
  identical by the tests). Hover/focus shows name · population ·
  county in a readout line; the map prints in grayscale by
  construction.
- **Permalink**: `p=map` encodes the active picker view, `r=` the
  region; both restore on load.
- Tests: 24 new assertions (coordinate coverage and bounds, uniform
  fills, swatch order, selection parity, hash round-trip, a11y) —
  **159 total, all passing**; the 135 prior assertions are intact.

## V3 built: actuals beside enacted (2026-07-13)

Per the approved finding (docs/V3_ACTUALS_FINDING.md, option (a)).

**Extraction.** `pipeline/schedule9.py` extracts prior-year actuals
from DOF Schedule 9 ("Comparative Statement of Expenditures") PDFs —
the authoritative source; the eBudget API's prior-year columns were
used only as the cross-check, never as figures. Two hard gates run
before anything is written:

- **Gate 1** — the sum of Schedule 9's agency groups must reconcile
  with the same publication's Schedule 6 statewide row, on BOTH the
  General Fund and the total, within Schedule 6's $1M rounding.
- **Gate 2** — department rows must sum exactly to their group total,
  or department-level actuals for that group are withheld (the gate-1-
  proven group total still publishes).

**Shipped: four fiscal years, all gate-exact.**
2021-22 $270.694B (2023-24 Enacted), 2022-23 $274.039B (2024-25
Enacted), 2023-24 $303.246B (2025-26 Enacted), 2024-25 $319.151B
(2026-27 Governor's Budget) — each equal to its Schedule 6 control.

**Not shipped: FY 2020-21 — reported, not worked around.** Both PDFs
carrying those actuals (2022-23 Governor's Budget and Enacted) emit
scrambled text at page-spanning agency groups under both pypdf
extraction modes; recovery attempts failed Gate 1 and were discarded.
Per instruction there was no fallback to the API. The view shows an
explanatory empty state for 2020-21 (as it does for 2025-26, whose
actuals first publish in January 2027).

**Education mapping.** Schedule 9 groups K-12 and Higher Education as
one "EDUCATION" agency; department rows are assigned to our split
using each display year's own org-code map, with named overrides for
codes absent from the web lists (community-college retirement and the
GO-bond lines). Cross-group movers are deliberate and correct — e.g.
ScholarShare sits under LJE in Schedule 9 but under K-12 in our
enacted structure ($184M in 2023-24), so mapping by OUR structure is
what makes the actual comparable to the enacted column. Statewide
conservation is gated exactly; the tests assert CDE→K-12, UC and
Community Colleges→Higher Education, and a ±0.5% bound on the split
vs. the source group.

**Known dept-level limitation (gated, disclosed).** In every vintage,
the HEALTH AND HUMAN SERVICES and GENERAL GOVERNMENT groups' department
rows do not extract in a form that sums to their group totals, so
Gate 2 withholds department actuals there; drilled views say so and
point at the gate-verified agency total. All other groups carry full
department detail.

**API cross-check (2023-24, report only):** agency-level API
prior-year sums vs. shipped Schedule 9 actuals — seven agencies within
0.1%; Corrections 80.1%, Transportation 90.6%, Natural Resources 90.3%
(the API's web department lists omit e.g. CDCR's realignment funds) —
confirming the finding's instruction that the API must never be the
source of the difference column.

**The view.** A fourth view (Allocation / Change / Trend / Actuals):
enacted and actual columns with a signed difference per agency,
drillable to departments where gate 2 allows. On its face, not buried:
both columns Budgetary-Legal; the vintage; and the statement that the
difference reflects mid-year legislation, re-appropriations, carryover,
reversions, and fund reclassifications — not a judgment of any kind.
Direction is ▲▼ grayscale ink (asserted); gross below- and
above-enactment totals always shown together; default sort is by
enacted size, never by gap; sorting is the reader's (asort permalink
param). CSV and Cite carry the basis, vintage, and
non-characterization lines. The banned-term scan now also rejects
"waste", "overrun", "savings", "underspend", "mismanage" (with a
carve-out for the SCO category "solid waste" on the city page).

Tests: 214 assertions, all passing (all 159 prior kept; 55 added —
reconciliation gates re-asserted against hardcoded Schedule 6
controls, education mapping, difference arithmetic recomputed
independently, grayscale direction, empty states with reasons,
permalink round-trips, CSV/citation content).

## Map upgraded to real city boundaries (2026-07-13)

The city map's population-scaled dots are replaced by every city's
true incorporated boundary.

- **Source:** Census cartographic boundary file cb_2023_06_place_500k
  (public domain), filtered to incorporated places — exactly 482,
  one-to-one with the SCO cities, matched by the same normalization +
  alias rules as the gazetteer (including the UTF-8 repair for La
  Cañada Flintridge). The generator
  (`pipeline/make_city_boundaries.py`, stdlib-only with a hand-rolled
  Douglas-Peucker) fails with a named report unless all 482 match;
  nothing is guessed or dropped.
- **Payload:** simplification at 0.2 viewBox units (≈275 m ground)
  keeps full ring structure (enclaves and exclaves included) at
  15,121 points — **city-geo.js is 202 KB** (options measured: 102 KB
  at 0.5, 134 KB at 0.35, 202 KB at 0.2; chosen for fidelity at the
  regional zooms, and nowhere near the multi-megabyte threshold that
  would have required a decision). The file carries its own SHA-256
  integrity digest, verified by pipeline/verify_digest.py and the
  test suite.
- **Rendering:** real polygons at every zoom, all 482 — no dot
  fallback, no representation swap. A city that is a few pixels at
  statewide zoom is shown at its true size; the regional presets make
  small cities workable. Uniform ink fill with a uniform parchment
  hairline between adjacent boundaries (structural, encodes nothing);
  selected cities take the comparison swatches in alphabetical order;
  hover/focus highlights in the interactive blue only.
- **Clickability:** an invisible circle above each polygon provides a
  minimum hit-target (screen-constant across zooms; the tests assert
  ≥6 px radius for the smallest at statewide) and doubles as the
  keyboard button (role=button, tabindex, full aria-labels). Small
  cities' targets stack above larger ones so overlaps resolve in
  their favor; the polygon itself is also clickable.
- **Neutrality unchanged and asserted:** all 482 unselected shapes
  share one computed fill and one fill-opacity; the caption reads
  "TRUE INCORPORATED BOUNDARIES (CENSUS, SIMPLIFIED) · THE MAP SHOWS
  WHERE, NEVER HOW MUCH."

Tests: 219 assertions, all passing — the 214 prior kept (map dot
assertions translated to polygons), plus boundary coverage (482/482),
hit-anchor validity, minimum hit-target size, hover affordance, and
the geo file's integrity digest.

## Map rebuilt on MapLibre GL JS (2026-07-13)

The dependency rule was re-scoped by instruction: **the record stays
pure** — index.html, the cities.html schedules/tables/exports/
citations, and both pipelines remain dependency-free and work from a
file double-click — while **the map is allowed a dependency.**

- **Dependency added:** MapLibre GL JS **v5.24.0** (3-Clause BSD),
  **vendored** into the repo at `vendor/maplibre-gl.js` (1.03 MB) and
  `vendor/maplibre-gl.css` (68 KB), fetched from the npm registry
  (`maplibre-gl@5.24.0` via unpkg) at commit time — no CDN at runtime,
  no third-party JS execution beyond the vendored file. Chosen over
  Leaflet because the "must not look like a generic embed" requirement
  needs vector tiles plus a custom style JSON; raster-tile basemaps
  can't be restyled to the Ledger's parchment/ink.
- **Basemap tiles:** OpenFreeMap (`tiles.openfreemap.org`, OSM data,
  free, keyless, CORS-open, OpenMapTiles schema — swappable for any
  compatible tile source, so no vendor lock-in). The style is the
  Ledger's own, defined inline: parchment land, muted water, ash
  county lines (dashed) and state lines, smoke city labels. Nothing in
  the basemap is shaded by any data. Attribution: © OpenStreetMap
  contributors / OpenFreeMap, shown in the map's compact control.
- **Loading and degradation:** the library loads lazily, only when the
  reader opens the Map view — the record pages never touch it. If
  `vendor/maplibre-gl.js` cannot load, the map shows a clear message
  and the search picker keeps working (test-asserted). If only the
  basemap tiles are unreachable (e.g. offline from a double-click),
  the map still renders every city boundary on parchment with a
  notice. The record pages are confirmed independent: no network, no
  map, everything else works.
- **Continuous zoom and pan** replace the six regional presets; a
  "Reset to statewide" control remains. Permalinks now carry the view
  as `m=zoom/lat/lng` (zoom to 0.1, coordinates to 0.01° ≈ 1 km),
  restored on load; reset clears it.
- **Overlay:** the same Census-derived geometry, regenerated by
  `pipeline/make_city_boundaries.py` as GeoJSON (lon/lat, 5 decimals,
  proper hole nesting; 482 features; **city-geo.js is now 410 KB**,
  digest-stamped). Feature properties are exactly {slug, name, clng,
  clat} — no financial fields exist for a style to encode.
- **Neutrality, adapted to WebGL and still CI-fatal:** a canvas has no
  per-shape DOM, so the uniform-fill assertion became two stronger
  ones — (1) the fill paint property must be a single ink literal when
  nothing is selected, and a slug-keyed match with an ink default when
  cities are selected (any data-driven fill changes this JSON and
  fails); (2) the geometry file must contain no financial properties.
  Selected cities take the comparison swatches alphabetically at full
  opacity; hover/focus highlights in interactive blue only.
- **Keyboard:** a visually-hidden, fully focusable per-city button
  list — focus pans the map to the city, highlights its boundary, and
  announces name/population/county in the aria-live readout; Enter
  selects through the identical code path as the search picker
  (parity test-asserted).
- **Print:** the map cannot print meaningfully from WebGL, so it is
  hidden in print CSS and the search-selected record prints instead
  (test-asserted).

Tests: **216 assertions, all passing.** The SVG-era map assertions
(DOM fills, hit-circle radius, hover class) were replaced by their
MapLibre equivalents (paint-spec neutrality, property-absence, canvas
click parity, keyboard parity, m= round-trip, degradation, print) —
three fewer in count, none weaker in coverage; the map tests now
require network for basemap tiles.

## 2026-07-13 — V5 build: the Counties layer

Built per the approved V5 finding, option (a) for counties only —
special districts and school districts were not built (see
docs/V5_DISTRICTS_FINDING.md for why).

- **Source:** the same SCO "By the Numbers" Socrata portal as cities —
  County Expenditures (`uctr-c2j8`), County Revenues (`emxv-k8xv`),
  and the independently published control totals in County
  Expenditures Per Capita (`miui-wb29`).
- **Coverage:** all **57 filing counties × 8 fiscal years (2016-17
  through 2023-24)** — 456 county-years. San Francisco files as a
  consolidated city and county: it stays in `city-data.js` with its
  existing footnote, is **absent from `county-data.js`** (asserted),
  and its polygon in `county-geo.js` carries `"pointer": "city"` so
  the map routes it to the city record. It is counted exactly once.
- **Hard gate, same as cities:** `pipeline/fetch_county_data.py`
  refuses to write unless, for every county-year, governmental +
  enterprise + internal service + conduit financing reproduces the
  SCO's published total ($1,000 or 0.1% tolerance on totals that run
  to tens of billions). Each county-year also stores the control total
  (`scoTotal`) so the test suite re-asserts the reconciliation on
  every run.
- **Governmental/enterprise separation preserved exactly:** county
  function figures and comparison cover governmental activities only;
  enterprise funds (county hospitals, airports, utilities…) are the
  same separate block; ISF and conduit are excluded from both.
- **The unincorporated-share footnote** (the county equivalent of the
  Lakewood problem): each county-year carries the share of its
  residents living in unincorporated areas, surfaced as a data-derived
  neutral note in the detail view, comparison, CSV, and citations.
  **Documented deviation:** the instruction suggested DOF report E-1
  as the source; the share is instead computed as
  (county population − sum of the county's cities' populations) ÷
  county population **from the same SCO filings** already in the
  record. Reason: the populations are then the same vintage and same
  source as every other number on the page (the SCO figures are
  themselves DOF estimates as reported in the filings), and the note
  stays reproducible from the committed pipeline without a second
  source. Values sanity-checked against known cases (Los Angeles
  ≈ 10%, Alpine = 100% — no incorporated cities).
- **Layer separation is structural, not copy:** the page has a
  Cities / Counties switch; switching clears the selection; slugs from
  one layer are invalid in the other; comparison, CSV, and citation
  operate within one layer; the methodology states plainly that
  cities and counties are never compared to each other (their
  responsibilities overlap in population but not in kind).
- **Map:** the county layer swaps the boundary source to
  `county-geo.js` (58 features: 57 counties + the SF pointer, 172 KB,
  Census `cb_2023_us_county_500k`, digest-stamped). Same neutrality
  rule, same assertions: uniform ink fill, selection keyed only by
  identity, no financial fields in the geometry. The keyboard list
  excludes the SF pointer; clicking SF's polygon shows a routing
  notice and never selects a county.
- **Integrity:** `county-data.js` (219 KB) and `county-geo.js` are
  SHA-256 digest-stamped; `pipeline/verify_digest.py` now checks all
  five data files by default, and the page's RECORD INTEGRITY panel
  shows the digest of whichever layer is active.

Tests: **244 assertions, all passing** — the 216 existing plus 28 new
county assertions (per-county-year gate re-assertion, unincorporated
footnote presence and arithmetic, SF single-counting on both sides,
layer-separation behavior, county map neutrality and pointer routing,
county CSV/citation wording).

## 2026-07-13 — V5 build, part two: the special districts layer

Built per the V5 finding, option (b), as re-scoped: FINDING FIRST,
DIRECTORY SECOND, NUMBERS LAST AND HEDGED. This layer is deliberately
NOT the evidentiary tier of the rest of the Ledger, and the page says
so on every surface.

- **Sources:** Special Districts Expenditures (`m9u3-wdam`) and
  Revenues (`nkv3-m73r`), plus the Controller's "filed late or failed
  to file" list for each year one exists — FY 2018-19 (`uiun-snc7`),
  2019-20 (`rbwh-942r`), 2020-21 (`fbdc-d5ib`), 2021-22 (`udxr-rcgh`),
  2022-23 (`en47-vkkk`), 2023-24 (`9whd-sig6`). No list was published
  for FY 2016-17 or 2017-18; the page prints "no list published" for
  those years rather than guessing.
- **The finding is the product, and it is computed, not copied.**
  Every figure the finding states — expected filers, filed, filed
  late, did not file (per year), district counts by legal type, the
  largest activity types, the enterprise share of as-filed dollars —
  is recomputed from the live API by `pipeline/fetch_district_data.py`
  on every run and stored in `meta.finding`; districts.html renders
  those values and hardcodes none of them (test-asserted: the
  formatted figures appear in the DOM and are absent from the page
  source). Current run: 4,817 expected filers for FY 2023-24, 785
  filed late, 51 did not file, 1,572 dependent districts among the
  4,750 that filed, 76.7% of as-filed expenditure dollars in
  enterprise funds. The live counts supersede the V5 doc's
  measurements where methods differ (the doc counted row-entries for
  dependent districts; the finding counts districts, per year, and
  states its method).
- **No reconciliation gate exists for this layer — structurally.**
  No control-total dataset is published for special districts, so
  nothing here can be verified against an independent total. The page
  states this in a persistent tier band, in the finding, in
  methodology note D-1, and on the face of every record: "As filed
  with the State Controller. Not reconciled against any published
  control total. The Ledger cannot verify this figure." The caveat
  travels into every CSV header and citation (test-asserted).
- **What IS gated (structurally, in the pipeline):** slug uniqueness;
  full year coverage; every late/failed list row either matched
  (normalized prefix + county — SCO's lists truncate names at ~40
  characters) or carried into the directory exactly as printed, never
  guessed. Match accounting this run: 5,123 late rows matched, 227
  did-not-file rows matched, 105 rows with no line items in either
  dataset shown as printed, 0 ambiguous, 1 re-spelling merged
  (identical after punctuation normalization + same county +
  disjoint years — the only merge rule permitted, per the V4
  entity-resolution finding).
- **The directory is the union of both datasets** — measured: ~60
  districts file only revenue line items, ~16 only expenditures.
  5,239 districts on record. Each row links to the district's own
  page on the Controller's explorer
  (`districts.bythenumbers.sco.ca.gov`, deep-link verified from a
  cold load).
- **No per-resident figures, no comparison, no totals.** The data
  file carries no population field at all, so the per-resident
  ingredient is refused at the source (test-asserted on the records).
  No comparison UI exists; selection is single-district and a second
  choice replaces the first. The finding section contains no dollar
  figure — counts and shares, never a layer total — because dependent
  districts (and JPAs) mean the same dollars can appear in more than
  one government's books.
- **Tier made visible in the design system's vocabulary:** dashed
  hairlines where gated layers use solid (test-asserted:
  border-style dashed here, solid on cities.html); an open square
  (▢) where the gated tier uses a filled mark, with the legend in the
  tier band; no schedule number ("AS-FILED RECORD — NOT A LEDGER
  SCHEDULE"); the caveat is part of the record face, not a footnote;
  the as-filed tables are plain text with no proportional bars.
- **No map, stated:** special districts are not a Census geography
  and no statewide boundary file exists on data.ca.gov or
  gis.data.ca.gov (searched 2026-07-13). The layer ships without a
  map rather than approximating boundaries.
- **Payload:** district-data.js is 2.17 MB (the largest data file;
  reported, not silent). It is loaded only by districts.html — the
  state, city, and county pages are unaffected.
- **Neutrality note:** district NAMES from the source legitimately
  contain words the Ledger bans in its own copy (districts named
  "…Wastewater Agency", even two "…Delinquent Tax Financing
  Authority" entities), so the banned-term scan for this page runs on
  the authored page source, where characterization could actually
  live; "delinquent" is additionally banned in the page's own copy —
  the page says "filed late or failed to file," as the Controller's
  lists do.

Tests: **305 assertions, all passing** — the 244 existing plus 61 for
this layer (caveat on record/CSV/citation, no per-resident figure
anywhere, no comparison or aggregate reachable, finding rendered from
data and absent from source, dashed-tier visuals vs. solid gated
surfaces, SCO deep links, filing-status table, authored-copy
neutrality scan, and the city/county picker never growing a district
layer).

## Update cadence

State: one new fiscal year per annual Budget Act (late June). Run
`python3 pipeline/fetch_state_data.py` after enactment; update the
population constant annually from DOF E-4.

Cities: one new fiscal year per SCO filing cycle (reports for a fiscal
year appear on By the Numbers roughly a year later). Run
`python3 pipeline/fetch_city_data.py --write`; extend `SOURCE_YEARS`
when a new year appears.

Counties: same cadence and portal as cities. Run
`python3 pipeline/fetch_county_data.py --write`; the write fails
unless every county-year reconciles against `miui-wb29`.

Special districts: same portal. Run
`python3 pipeline/fetch_district_data.py --write`; the finding's
figures recompute from the live data on every run. When SCO publishes
a new fiscal year, extend the window in YEARS and add the year's
late/failed list id to DELINQUENCY.
