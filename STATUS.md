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
- **GitHub Pages: workflow verified, deployment then awaiting a
  settings change.** Both runs of "Deploy to GitHub Pages" failed in
  `actions/configure-pages` with "Get Pages site failed … Not Found",
  which meant Pages was not yet enabled for the repository. The
  workflow itself checked out and ran correctly up to that step. Two
  settings facts mattered: (1) Settings → Pages → Build and deployment
  → Source must be set to "GitHub Actions"; (2) the repository was
  at the time **private** — GitHub Pages on a private repository
  requires a paid plan (and the published site is public regardless),
  so the repo needed to be made public first. Permalinks and citations
  already derive their URLs from `window.location`, verified earlier
  under a simulated `/ca-ledger/` subpath, so they emit the public URL
  as soon as the page is served from it. _(Resolved 2026-07-16: the
  repository is public and the site is live on GitHub Pages.)_

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
  citations emit that served URL, so they emit the public URL in
  production. Deployment at the time still awaited the repository
  settings change documented earlier (the repo was then private;
  Pages had to be enabled with Source = GitHub Actions). _(Resolved
  2026-07-16: the repository is public and the site is live.)_

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

## 2026-07-14 — V6 build: the address view (address.html)

Built per docs/V6_ADDRESS_FINDING.md, option (b) SHIP NARROWED.

- **Geocoding:** U.S. Census Bureau geocoder via its supported JSONP
  interface (its CORS allow-list blocks browser fetch(), as the
  finding verified). The geographies endpoint assigns county,
  incorporated place, and CDP from full-resolution TIGER — the
  Ledger's simplified map shapes are never used for assignment. City
  matching is by Census GEOID: `pipeline/make_city_boundaries.py` now
  carries `geoid` on every feature (regenerated, 418 KB, digest
  restamped), so no name matching happens at runtime.
- **No sum, structurally:** the three records (city or
  unincorporated-county, county, state) stack with per-record basis
  labels; a bordered does-not-add statement carries the live
  intergovernmental figures, which now ship in county-data.js as
  `meta.intergovernmental` — computed by the county pipeline from
  the Controller's revenue data on every run (FY 2023-24: 53.8% of
  county governmental revenues intergovernmental; $37.6B state,
  $17.8B federal of $104.5B). Tests assert the arithmetic sum of the
  three rendered per-resident figures appears nowhere in the DOM and
  that the share is absent from the page source.
- **No district assignment:** the districts panel states the county's
  filer count from district-data.js and that the Ledger cannot
  determine which districts serve an address, linking to the
  county-filtered directory. The TRA path stays retired per the
  finding.
- **Unincorporated addresses are first-class:** no incorporated place
  → the county renders as THE local government, with the
  unincorporated share made concrete and any CDP labeled "a
  statistical designation, not a government." Verified live against
  the real geocoder for East Los Angeles. San Francisco resolves to
  one consolidated record, counted once.
- **Comparability survives the synthesis:** city mini-records carry
  the same service-provision notes as the full record (a Lakewood
  lookup shows the county-contract note beside its low per-resident
  figure), and the county record on incorporated addresses explains
  the countywide-vs-unincorporated split.
- **Privacy, as guaranteed in the finding:** the address goes only to
  census.gov (disclosed on the page, including the load-balancer
  cookie); permalinks are resolved slugs only (`c=` / `uc=`);
  citations and CSVs are generated from slugs and say so; nothing is
  persisted. Tests inject a distinctive address through a mocked
  geocoder and assert it appears in neither hash, citation, CSV, nor
  localStorage.
- **Degradation:** geocoder unreachable → plain failure message plus
  direct links to the search pickers (test-asserted, via aborted
  requests); no-match → stated, never guessed. Pin-drop (coordinates
  endpoint, no address) and an on-device point-in-polygon fallback
  against the shipped simplified boundaries (its city-limit accuracy
  caveat printed with every result) cover the rural and
  maximum-privacy cases.
- **Page weight:** address.html loads all five data files plus
  city/county geometry (~4.8 MB raw, ~1 MB compressed on Pages) —
  the heaviest page on the site, stated here rather than silent; the
  record pages are unaffected.

Tests: **338 assertions, all passing** — 305 existing (one adapted:
city-geo properties now include `geoid`) plus 33 for this page (no
summed figure in the DOM; live intergovernmental share rendered from
data and absent from source; the in-your-name copy rule with its
banned phrasings; East-LA-class unincorporated correctness through a
mocked geocoder; SF consolidation; address absent from
hash/citation/CSV/localStorage; failure degradation; district-count
substitute).

## 2026-07-14 — Renamed: The California Ledger → Citizen Ledger

Full rename across every user-facing and maintainer-facing surface:
page titles, wordmarks, OG/Twitter metadata, citation lead-ins, CSV
headers, print citations, README, the landscape finding, all seven
pipeline docstrings, the favicon comment, and the test-suite
docstring. The tagline — "A nonpartisan record of California
government spending" — now carries the state, appearing under the
wordmark on every page and leading every meta description, since the
name no longer says California.

Citations across all four pages now share one format, and the site's
name travels in every one of them:
`Citizen Ledger, "[view title], FY 20XX-XX." …figures… Source… Permalink…`
(the districts view keeps its tier in the title: "Special Districts —
As Filed: …, FY … (unreconciled)").

Deliberately unchanged, per the project owner: the repository name,
the GitHub Pages URL, and every canonical/OG URL — they keep pointing
at the current address until that decision is made separately
(test-asserted so the rename cannot drift them).

VISION.md and FOUNDATIONS.md were listed for updating but do not
exist in this repository; nothing was invented to fill them.

Tests: **374 assertions, all passing** — 338 existing plus 36 rename
locks (per-page title/site-name/tagline/wordmark/footer, old name
absent from source AND rendered DOM on every page, canonical URLs
unchanged, and the citation format verified rendered on all four
pages). An independent three-auditor verification pass (residual
scan, rendered surfaces, citation/CSV format conformance) ran on top
of the suite.

## 2026-07-14 — V7 build: the K-12 schools layer (schools.html)

Built per docs/V7_SCHOOLS_FINDING.md, option (a): GATED AND COMPARABLE,
comparison scoped to school districts only.

- **The gate is the strictest on the site.**
  `pipeline/fetch_school_data.py` recomputes every district's Current
  Expense of Education (CDE's EDP 365 formula: Fund 01; objects
  1000-5999, 6500, 7300-7399; minus non-agency and community-service
  goals, food-service and facilities functions, retiree-benefit
  objects; district-entity rows only) from the raw SACS general ledger
  and refuses to write unless every district-year matches CDE's
  published per-district figure within $0.05 — in practice, to the
  cent: **934/934 (FY 2022-23), 933/933 (FY 2023-24), 932/932
  (FY 2024-25)**. Two further gates: summing the raw ledger must
  reproduce CDE's own in-database county/state rollups cell-by-cell,
  and the charter Alternative Form data must reproduce its totals
  table. Each record stores `cePublished` beside the recomputed
  figure, so the suite re-asserts the gate on every run and readers
  can re-check it from the data file.
- **Scope:** FY 2022-23 through 2024-25 (the pipeline extends the
  window by adding a year to YEARS; archives exist back to 2003-04).
  934 school districts (comparable), 58 county offices (records
  only), 980 separately-filing charter records, 318 dependent-charter
  pointers. ROPs/SELPAs/JPAs are inside the rollup gates but not
  records in this version.
- **Comparison is districts only, per ADA** — the ADA CDE itself
  publishes beside its per-ADA statistic (identical to the cent).
  County offices are structurally outside comparison and the page
  states why before any selection; they carry no per-ADA figure at
  all. Charters are records only, with the filing mode on each
  record's face.
- **Three data-derived daggers, in the contract-city pattern:** basic
  aid (local tax above LCFF entitlement — the count and share render
  live from the LCFF data, 127 districts in FY 2024-25); fewer than
  250 ADA (necessary-small-school funding floors); sponsored charters
  (fires when separately-reporting charter ADA is at least a quarter
  of the district's own — New Jerusalem's record states 5,445
  sponsored against 17.8 own). Districts with charters commingled in
  Fund 01 (45 districts; 149 charters statewide) state on their face
  that those charters cannot be separated and that CDE's published
  figure includes them; dependent-charter pointer rows in the search
  name the authorizer and never select.
- **The overlap statement is computed by the pipeline on every run**
  (`meta.overlap`): FY 2024-25, 50.7% of the $153.3B LEAs reported
  receiving is state-sourced — against the state layer's $81.6B K-12
  agency (agreement 0.952; the page says "roughly 1–3.5% and never to
  the dollar"). Property tax inside LCFF: 19.6%; federal: 7.6%. The
  named traps render with live values: EPA $13.1B (continuously
  appropriated outside the Budget Act, inside the GF display), STRS
  on-behalf $3.6B (object 8590 within resource 7690 only — a bare
  8590 sum is the whole other-state bucket and wrong), inter-LEA
  pass-throughs $3.3B, and Prop 98 being K-14. index.html's
  methodology gained a static pointer note (M-8); the computed
  statement lives on schools.html. Tests assert the share renders
  from the data file and appears nowhere in the page source.
- **Cross-layer rule:** K-12 entities are never compared to or summed
  with cities, counties, special districts, or the state — stated in
  methodology and enforced by page structure (the city/county picker
  has no school layer, test-asserted).
- **Pipeline dependencies:** mdbtools (mdb-export) and openpyxl —
  pipeline-only, like pypdf for the state actuals. The SACS archives
  (~45 MB/yr, extracting to ~470 MB Access databases) cache under
  pipeline/cache/schools/ (gitignored); CDE's HTML pages are
  bot-gated but the file URLs download cleanly. school-data.js is
  1.88 MB, digest-stamped, checked by verify_digest.py defaults.
- **One correctness catch during the build:** the Charters table's
  FundUsed values are words, not fund codes ("General" = Fund 01,
  "CharterSpecRevenue" = 09, "CharterEnterprise" = 62) and SBE's
  ReportLevel is "StateBoardOfEducation" — the word-based mapping
  reproduces the finding's counts exactly (149 commingled, 318
  dependent).

Tests: **429 assertions, all passing** — 374 existing plus 55 for
this layer (the gate re-asserted for every district-year from the
shipped data; function rows summing exactly to the gated figure; all
three daggers rendered with live counts absent from source; the
commingled limit on an affected record's face; COE exclusion
structural checks; dependent pointers that never select; the overlap
statement's live values, named traps, and bounded precision; the
cross-layer statement; citation/CSV format with the published figure
re-checkable from exports; authored-copy neutrality scan).

## 2026-07-14 — School districts on the address view

The address view now resolves the school district(s) of residence,
because — unlike special districts — school districts ARE a Census
TIGER geography.

- **Assignment is the Census Bureau's, by identifier.** The
  geographies endpoint returns the Unified / Elementary / Secondary
  School District layers directly (verified live), so no boundary
  files ship and no point-in-polygon runs. The returned GEOID equals
  the NCES LEA id; matching to SACS districts uses a crosswalk built
  by the pipeline from CDE's own directory (NCESDist ↔ CDS code) —
  never names. All 934 districts carry ids; an unmatched GEOID fails
  loudly on the face of the panel ("no identifier-matched record …
  nothing is shown rather than a guess"), test-asserted.
- **Unified vs. elementary + secondary handled, never assumed:** a
  unified district renders one record; a pair renders two, labeled
  YOUR ELEMENTARY / YOUR HIGH SCHOOL DISTRICT (verified live:
  Lancaster Elementary + Antelope Valley Union High). The five
  common-administration filers carry both constituents' NCES ids —
  a documented administrative structure from CDE's readme, encoded
  as a verified constant, not name matching — so Modesto's two legal
  districts dedupe to the single Modesto City Schools record.
- **The record keeps the layer's discipline:** gated Current Expense
  per ADA ("RECONCILED TO CDE'S PUBLISHED FIGURE"), top functions per
  ADA, and the daggers carry through (a Palo Alto address shows the
  basic-aid note with the live count). Every school record states:
  the district shown is the **district of residence** —
  charter-school students may attend schools their district does not
  run.
- **The does-not-add statement extends to schools** with the live
  share from school-data.js meta ("about 50.7% of what school
  districts report receiving is state money the state record already
  contains — the layers agree to roughly 1–3.5% and never to the
  dollar"); the share is absent from the page source, test-asserted.
  CSV exports gain a per-ADA school table (never per-resident) with
  the residence and no-add notes; citations carry both.
- **Privacy unchanged:** the same single JSONP request to census.gov
  now also names the school-district layers — the address goes
  nowhere new; permalinks carry `sd=` slugs only. The on-device
  fallback does not resolve schools and says so. Where the geocoder
  response has no school layers, the panel states "not determined"
  rather than guessing.
- address.html now also loads school-data.js (~8.6 MB raw total for
  the page, ~1.5 MB compressed — the heaviest page on the site,
  stated here as always).

Tests: **443 assertions, all passing** — 429 existing plus 14
(identifier coverage incl. the five dual-id filers; unified and
elem+high mocked flows; common-admin dedupe; unmatched-GEOID loud
failure; the extended does-not-add with live share absent from
source; per-ADA CSV and citation; the not-determined strip on
school-less responses).

## 2026-07-14 — Scope decision: "Ask the Ledger" permanently out; the no-server rule made standing

The project owner ruled a natural-language query interface
permanently out of scope, and made the underlying rule standing:
**no server, no API keys, no per-use costs, no runtime third-party
services — any feature requiring one is out of scope by default.**
The reasoning (an LLM call per question needs a key, a key needs a
server, and a server is the failure mode the landscape finding's
graveyard documents; the Ledger is already queryable via search,
filters, comparison, and permalinks; survivability is the scarce
resource) is recorded normatively in **docs/SCOPE.md**, which also
states precisely how the two existing keyless, non-load-bearing
runtime enhancements (map tiles, Census geocoder) relate to the rule.
A repo-wide search confirmed no reference to the feature existed
anywhere before this decision — the record exists to keep it that way.

## 2026-07-14 — Address autocomplete, native autofill, pin-map labels, explicit actuals empty state

- **Autocomplete against the Census address database only.** The
  geocoder returns up to 50 TIGER-matched candidates for ambiguous
  input and corrects misspelled cities (verified empirically), so the
  address input now offers debounced as-you-type candidates (house
  number required, 450 ms debounce, top 6 shown) with the disclosure
  caption "candidates from the Census Bureau's address database" on
  the list itself. No property records, voter files, residency
  datasets, or keyed services — per docs/SCOPE.md. Privacy model
  unchanged and re-tested: partial addresses reach census.gov only
  (request-level test asserts the typed string appears in no other
  host's requests), nothing persists, permalinks stay slugs-only. The
  privacy note now says as-you-type lookups happen. Honest limit: the
  known rural gaps are TIGER coverage, not format — suggestions fix
  format-guessing; pin-drop remains the answer where no range exists.
- **Native browser autofill enabled** (`autocomplete="street-address"`)
  — the browser may offer the user's own saved address; the page never
  auto-populates or geolocates on load.
- **Pin-drop map now carries the Ledger basemap with place labels**
  (parchment, muted water, state line, smoke city/town labels from
  OpenFreeMap — the same style vocabulary as the cities map), so a
  person placing a pin can see where they are. Labels are geography,
  never a data encoding: label color is a single neutral literal and
  the county overlay stays uniform ink (both test-asserted). Tile
  failure degrades to boundaries on parchment, as elsewhere.
- **The state Actuals view's current-year empty state is explicit:**
  "No actuals exist yet for FY 2025-26. Actual expenditures for a
  fiscal year are published roughly six and a half months after it
  ends, in the following January's Governor's Budget — for FY
  2025-26, the January 2027 edition." Year and edition are computed,
  not hardcoded; the FY 2020-21 extraction-gate explanation keeps its
  own distinct copy.

Tests: **454 assertions, all passing** — 443 existing (one adapted to
the new empty-state copy) plus 11 new (autofill attribute; candidates
render with the disclosure caption; the typed address reaches
census.gov only; pick-resolves flow with slugs-only hash; nothing
persisted; pin-map label layer present with neutral literal color and
uniform county fill; current-year empty state names the year and the
January edition).

## 2026-07-14 — INCIDENT: FY 2016-17 city functions shipped misclassified; fixed, and a new gate class added

**The bug.** Every city's FY 2016-17 `byFunction` was wrong from the
first city-data publication until today: the SCO source's FY2017
vintage puts the function group in `category` (line in
`subcategory_1`), while 2017-18+ puts paired super-groups in
`category` and the group in `subcategory_1`. The classifier read
`subcategory_1` as the group and silently fell through to "other" for
anything unrecognized — so Los Angeles shipped FY 2016-17 as
`{other: $6,716M, debt, capital}` with no police or fire line, and
statewide "other" was 83.2% of city governmental spending that year
(clean years measure ≤0.6%). Found by the V8 depth investigation;
re-verified before fixing.

**Why the gate missed it.** The reconciliation gate proves
conservation — every city-year total reproduced the Controller's
published figure exactly, including the broken year. Totals cannot
see classification: the money was all there, in the wrong buckets.

**The fix.** `classify_expenditure()` is now shape-driven, not
year-driven: it detects the function group by value wherever it sits
(handling both vintage layouts, including FY2017's combined
"Debt Service and Capital Outlay" splitting in `subcategory_1`), and
**refuses to classify unrecognized shapes** — the silent
fall-through to "other" is gone, as is the county classifier's
equivalent silent catch-all to "admin". city-data.js regenerated
(all totals gates still pass; digest restamped). Verified: LA FY
2016-17 now shows police $2,494.2M / fire $624.0M, consistent with
the series ($2,610M police in 2017-18); statewide 2016-17 "other" is
0.04%; functions still sum exactly to the gated totals.

**The new gate class — classification-shape gates, hard, in every
pipeline** (no write on failure), alongside the totals gates:
- cities: statewide police/fire/admin/streets/parks nonzero every
  year; statewide "other" ≤10% of governmental spending; per city,
  police/fire above $1M in both adjacent years cannot be zero in
  between (unless the whole filing is zero at source);
- counties: all 14 functions nonzero statewide, every year;
- schools: ADA>0 implies instruction dollars >0 per district; core
  function groups nonzero statewide;
- special districts: governmental and enterprise buckets both
  nonzero statewide, every year.
All four pipelines ran clean under the new gates across every year;
the same rules are re-asserted from the shipped files by the test
suite so a regression cannot pass CI.

**What else the sweep found** — the honest answer to "how much don't
we know about what we've shipped":
- **Counties, schools, special districts: clean.** Every year of
  every other layer passes every shape rule; county vintage
  differences are punctuation-only (hyphen vs en-dash), already
  normalized. The FY 2016-17 city year was the only classification
  casualty.
- **Three all-zero source filings surfaced:** Hollister and Novato
  FY 2021-22 and Woodland FY 2022-23 are zero-filled governmental
  forms at the SCO source (non-timely filings published as zeros) —
  source facts, not our error, and the sandwich rule exempts
  zero-total years for exactly this reason.
- **One materiality lesson:** Mendota's fire line is genuinely $16k →
  $0 → $1.5k at source — tiny incidental lines legitimately touch
  zero, which is why the sandwich gate carries a $1M floor. A real
  department cannot flicker to zero; a bookkeeping line can.

Tests: **489 assertions, all passing** — 454 existing (all green
against the regenerated data) plus 35 shape assertions (statewide
function presence per layer-year, the other-share bound, the LA
2016-17 regression lock, the material-sandwich rule, ADA-implies-
instruction, and district bucket liveness).

## 2026-07-14 — V8 build: the approved depth layers

Built per docs/V8_DEPTH_FINDING.md with the owner's approvals and
refusals, under all six cross-cutting rules.

**Shipped depths, each behind a hard parent-sum gate (pipeline: no
write on failure; suite: re-asserted from the shipped files):**

- **State fund drill** (index.html, department rows in the Allocation
  drill): every department's fund rows — legal fund titles, class
  G/S/B/F, integer thousands — sum exactly to the gated gf/sp/bd/fed
  parents, all 6 years. The data was already being fetched to compute
  the federal toggle and thrown away; now it ships.
- **State programs as a LABELED ALL-FUNDS VIEW with the explicit
  bridge**: programs render under "ALL FUNDS · A DIFFERENT SCOPE
  FROM THE DEPARTMENT FIGURE ABOVE," followed by the exact bridge —
  state funds + federal + nongovernmental-cost funds + reimbursements
  − capital outlay not allocated to programs = programs total, in
  real numbers, ending "nothing is missing and nothing is
  double-counted… Both totals are correct — they answer different
  questions." The gate anchors on the API's own program totals rows;
  the build surfaced one more source subtlety: departments vary in
  whether capital outlay is allocated to programs, so the unallocated
  remainder is computed per department (Corrections 2020-21: $471M
  unallocated; Wildlife Conservation Board: $0 — and WCB's own "All
  Expenditures" API row double-counts, which our identity ignores).
  A department whose displays cannot be reconciled would ship
  fund-detail-only with a programsOmitted marker — measured result:
  **zero departments need it**; every program view reconciles
  exactly. Program prior-year columns are NOT carried (refused — they
  undercount the gated actuals).
- **Schools function × object-family + restricted/unrestricted**
  (schools.html, expandable function rows): both partitions sum to
  the gated Current Expense **to the cent for every district-year**
  (pipeline gate + suite). LAUSD's negative General-administration
  object cell renders with its minus sign and the cost-transfer
  explanation; the restricted/unrestricted line sits under the
  headline and "sums exactly" is stated on the face. Full 4-digit
  object depth refused (payload).
- **City and county line-level state forms** (cities.html, expandable
  function rows, governmental activities only): official FTR line
  names from a shipped dictionary, whole dollars, children gated to
  the unrounded function totals (±$1) for every entity-year-function.
  County lines split activity from fund type (District Attorney ·
  GENERAL); "Other …" slots are marked "not itemized in the state
  form"; Santa Clara County's Auditor-Controller line renders
  negative every year with the netted-cost-allocation note — shown,
  not hidden. Special-district depth refused (the record keeps its
  SCO deep link as the drill).

**Payload, measured (the double-click budget):**

| File | before | after |
|---|---|---|
| data.js | 355 KB (indent-2) | **580 KB** (compact, incl. funds + programs + bridge + fund-name dictionary) |
| school-data.js | 1.90 MB | **4.05 MB** |
| city-data.js | 1.48 MB | **2.85 MB** |
| county-data.js | 220 KB | **743 KB** |

All digests restamped; verify_digest checks all files. The six
cross-cutting rules hold by construction: unrounded-parent gates
everywhere; integer source units (thousands for state, dollars for
SCO lines, cents-exact for SACS); honest negatives with one-line
explanations; exclusions preserved (ISF/conduit and EDP deductions
stay out; N/R appear only as labeled bridge rows); the
classification-shape gates run unchanged; and every label at every
depth is an official source name — no crosswalk was invented.

Tests: **509 assertions, all passing** — 489 existing plus 20 depth
assertions (fund children vs every department parent; the program/
bridge identity from the shipped integer fund rows; cent-exact school
partitions; line children vs every city/county function; refusals
locked — no program prior-year columns, object families only, no
district lines; and the rendered bridge, negative lines, and
restricted split verified in the UI).

## 2026-07-14 — Year-reachability report and guard

A report that FY 2016-17 was unreachable in the cities page's year
selector **did not reproduce**: empirically, every page's selector
offers exactly its data file's years (cities and counties: all 8
including 2016-17; state: 6; schools: 3), the earliest year is
reachable by dropdown, stepper, and permalink (verified rendering
LA's police row), and the districts page's tables carry all 8 years.
No layer has data the UI hides — with one by-design exception already
documented: the address view's stacked records show the latest fiscal
year only, linking through to the full multi-year records.

Likely causes of the report: a stale cached page (identical symptom
seen during the county build) or the GitHub Pages deployment, which
was unavailable while the repository was private (noted at Pages
setup; the owner's settings decision, since made — the repository
went public and Pages went live on 2026-07-16).

The guard requested was added regardless: the suite now asserts, per
layer, that the year set offered in the UI exactly equals the year
set in that layer's data file, that the earliest city year renders,
and that the districts tables carry every data year — so a future
selector regression cannot ship silently.

Tests: **515 assertions, all passing** (509 + 6 year-coverage).

## 2026-07-15 — Three state-page legibility fixes (presentation only)

Each confirmed cosmetic before touching (no figure changed, no data
regenerated, digests untouched):

- **Sub-$0.5M fund tail collapsed** in the fund-detail drill: long
  lists no longer end in $0M rows; a single expandable line ("7 funds
  under $0.5M · combined") carries the exact combined figure, expands
  to every member fund at whole-dollar precision, and the footer
  still sums all funds including the tail (test-asserted against the
  data file). Every fund remains in data.js.
- **Department-actuals dashes explained inline**: the drilled Actuals
  view now states that — means no department figure exists, not zero
  (DOF publishes Schedule 9 actuals at agency level only), and names
  the agency's own actual beside its enacted figure so the
  relationship is explicit. (Verified first: department nodes carry
  no actual field — the dashes are the record, not a bug.)
- **No direction glyph at 0.0%**: a ▲/▼ beside a change that rounds
  to 0.0% was contradictory; the formatter now suppresses the glyph
  exactly when the rounded value is 0.0%, and tests scan rendered
  views for any arrow-adjacent 0.0%.

Tests: **525 assertions, all passing** (515 + 10).

## 2026-07-15 — Contract-service zeros explained on the face; near-zero fund sections collapse

Both presentation/notes only — no figure changed, no data regenerated.

- **Every zero police/fire cell now explains itself, pinned open.**
  Audited first: 1,162 city-year cells show $0 police or fire in a
  nonzero filing — 1,102 of them checklist-confirmed as externally
  provided (fire: 675 special-district/other-agency, 325 code I, 64
  county-contract; police: 5 county-contract), and 60 where the
  FY 2015-16 checklist claims city provision yet the filing shows
  zero. The dagger note previously existed but sat behind a click —
  a $0 read as "spends nothing." Now: the note renders open under
  the zero row (detail view), travels into comparison footnotes and
  the address-view mini-record, and says where the money actually
  is — county contracts name the county ("that spending appears in
  Los Angeles County's record, not the city's"); other providers get
  "the provider's record"; and the 60 checklist-contradicted zeros
  get the honest fallback: "not reported in this city's filing — the
  Ledger cannot confirm from the services checklist how the service
  is provided," never implying zero spending. Boundary: the checklist
  covers police and fire only; zeros in other functions (library,
  parks) carry no provider data and stay unannotated rather than
  guessed at.
- **All-near-zero fund sections collapse to one line**: a department
  whose whole state-funds side rounds under $0.5M (e.g. Community
  Services & Development, essentially all-federal) now shows "State
  funds: under $0.5M combined — this department is almost entirely
  federally funded" instead of a $0M row list — still expandable to
  the exact whole-dollar rows, still summing into the panel.

One test-infrastructure fix while verifying: the V1 drill-readout
assertion read a hover-driven readout while Chromium synthesized a
hover over the re-rendered bar under the stationary pointer; the test
now reads the readout at rest.

Tests: **534 assertions, all passing** (525 + 9).

## 2026-07-15 — The front door and the About & method page

- **Front door:** a masthead above the state view on index.html — not
  a separate landing, because moving the state page would break every
  citation permalink already pointing at index.html, and the citation
  contract outranks a splash. Under one screen: the tagline as the
  statement, one sentence saying what the data is and that it is
  reconciled to the sources' own published totals, five plain doors
  (address lookup, state budget, city/county, schools, special
  districts), and the discipline line — "It never ranks, never
  characterizes, and never concludes" — linking to the method page.
  No imagery, no slogans.
- **about.html — About & method**, drawn from SCOPE.md, the finding
  docs, and STATUS, in public-facing language: what the Ledger is and
  who it is for; the sources named per layer with accounting basis
  and update cadence; **the reconciliation gate** stated plainly and
  concretely (recompute from the raw source, reproduce the source's
  own published total, or nothing is written — with the schools
  to-the-cent case named, plus the depth parent-sum gates and the
  shape gates), and the special-districts as-filed exception stated
  where the claim is made; SHA-256 verification anyone can run; the
  refusals (no ranking, no characterizing, no conclusions, no vendor
  data — linking the V4 finding — no sums across layers); the
  standing no-server/no-keys/no-per-use-cost rule and why the site is
  built to outlast its maker (linking SCOPE.md and the landscape
  finding); the known limits (as-filed tier, basis differences,
  actuals lag, never-sum, checklist vintage, display-only map
  boundaries); and the open/reproducible statement. Every factual
  claim checked against the current build; the as-filed carve-out is
  attached directly to the verification claim so nothing overstates.
- Navs on all pages gain "About & method"; per-page Methodology
  anchors remain. (FOUNDATIONS.md was cited as source material but
  does not exist in this repository — noted before, still true;
  SCOPE.md and the findings supplied the substance.)

Tests: **597 assertions, all passing** (534 + 63: the five doors
reach every layer and the state door scrolls; the method page states
all four accounting bases, names the gate with its refusal-to-write,
states the as-filed exception, the SHA-256 check, all five refusals
with the V4 link, the architectural rule, limits, cadences; and an
archive-voice scan bans marketing language on both new surfaces).

## 2026-07-15 — Licensing, authenticity, and the documented security posture

No data or pipeline code changed.

- **License:** Apache-2.0 for the code (chosen over MIT because its
  Section 6 explicitly excludes trademark rights — the Chromium/Chrome
  model in the license text itself), full text in LICENSE. The
  generated data files are CC0, as the about page already stated. The
  NOTICE file — which Apache 4(d) obliges redistributors to carry —
  states the name restriction: a fork may use the code and data but
  may not present itself as Citizen Ledger. README and about.html
  state the three-way split plainly.
- **Authenticity:** about.html gains "Verifying authenticity" — the
  authentic figures are the ones whose SHA-256 digests match those
  published here and reproduce from the official sources; a copy that
  cannot reproduce them is not the authentic record.
- **docs/SECURITY.md:** an honest threat model. What the static
  architecture eliminates by construction (no server, database,
  auth, secrets, or collected user data — the surfaces do not
  exist); the residual risks named without inflation: the GitHub
  account as the crown jewel (2FA a hard requirement), push/merge
  integrity (branch protection + signed commits — stated as policy,
  not enforcement, until the owner enables them), the deploy
  pipeline (actions now **pinned to full commit SHAs**; permissions
  already minimal; no build step), the three keyless runtime
  services (tiles, geocoder, fonts — fonts added honestly as the
  third), post-deploy tampering with the digest defense's honest
  limit stated (an attacker controlling the whole site could alter
  digests and data together; the digests defend copies/forks and
  data-file tampering, and full verification is re-running the
  pipelines), the vendored-library and pipeline-dependency supply
  chain, and the stated boundary that gates verify fidelity TO the
  official sources, not the sources themselves. Plus how to report a
  data error or a security issue.

Tests: **602 assertions, all passing** (597 + 5: authenticity and
licensing statements on the about page, LICENSE/NOTICE contents,
SECURITY.md's honest-limits language, workflow SHA pinning).

## 2026-07-16 — The repository is public and the site is live

Four settings milestones, all the owner's, landed: the repository
moved to the `citizen-ledger` organization
(github.com/citizen-ledger/ca-ledger — every hardcoded reference
retargeted in PR #1, merged), branch protection went active on
`main` (all changes by pull request now), the repository was made
**public**, and the site deployed to GitHub Pages at
https://citizen-ledger.github.io/ca-ledger/.

Wording followed the facts, in both directions. When the repo was
still private, the about page's claim was softened to "one
repository, which will be public" rather than overstate; now that it
is public, the same discipline restores present tense: "all in one
public repository" (about.html, with its test assertion updated to
match). The three status-log passages above that described the repo
as private in present tense were corrected to past tense with dated
resolution notes — the history stands, but no sentence in this
repository now asserts the repo is private or that publication is
pending. A full sweep (literal phrases plus an agent pass over every
page, doc, and code comment for anything *implying* private status
or an undeployed site) caught one more: the test suite's docstring
said permalinks "will emit the public URL when deployed" — now "in
production they emit the public URL." Two forward-looking notes in
docs/LANDSCAPE_FINDING.md ("seek [Coleman's] review … before wide
release"; "re-run this investigation before any public launch") were
left as written: they are dated investigation guidance about
promotion and shelf-life, not claims about the repository's status.

No data, pipeline, or figure changed.

## 2026-07-17 — V11 community-college layer built (ccc.html)

The California Community College district layer shipped (per
docs/V11_CCC_FINDING.md, option (a), gated at whole-dollar resolution).
New page `ccc.html`, new pipeline `pipeline/fetch_ccc_data.py`, new data
file `ccc-data.js`. Nav extended to eight items across every page and
the 404.

**The gate, proven on real data — whole dollars, exact.** The 73
districts' Current Expense of Education (ECS 84362, the community-college
analog of K-12's) sum **exactly, to the dollar**, to the Chancellor's
Office's own printed statewide total in Table VI: $8,469,851,699 =
$8,469,851,699, no write on failure. Independently validated off the
portal by each district's mandatory CPA audit (Ed Code 84040). This is a
third, accurately-named resolution tier — exact to the dollar, finer than
CSU's thousand, coarser than K-12's cent.

**Auto-reproducible — the contrast with CSU.** Every source is a public
endpoint the pipeline fetches without credentials: the CCFS-311 reporting
portal (a public POST; the statewide Run button is disabled until a
fiscal-year autopostback fires, which the pipeline scripts), the MIS
District & College Codes PDF, and the SCFF 2022-23 Recalculation Exhibit
C PDF. `python3 pipeline/fetch_ccc_data.py --refresh` re-fetches all
three live and reproduces the data file **byte-for-byte** — confirmed.
All 73 districts fetch via a single Table VI report; zero fetch failures.
There is **no** manual-cache exception here — that remains CSU's alone.

**A finding figure corrected in the build.** The finding drafted LA's
Current Expense of Education as $774,683,675; that is the 50-Percent-Law
worksheet's "Total Expenditures Prior to Exclusions," a pre-exclusion
line. The published ECS 84362 (Table VI, after exclusions) is
$716,533,122. The docstring, the finding's build-correction note, and
this entry all record it — the "prove it on real data" discipline
catching a number before it shipped.

**Denominator and daggers, data-derived and reconciled.** Per-FTES uses
the apportionment funded FTES from Exhibit C (not the Data Mart derived
count); Calbright, not apportionment-funded, carries no per-FTES.
Comparability daggers: multi-college (23 districts, verified against the
MIS codes — reconciling to the official 116 accredited colleges),
community-supported/basic-aid (8 districts, derived from SCFF
property-tax excess — matching the Chancellor's Office's own "8 Fully
Community Supported Districts"), and noncredit-heavy (≥ 2× the statewide
share). The multi-college **and** community-supported intersection — the
cell where per-FTES is most misleading — is San Mateo, South Orange
County, West Valley-Mission, and San Jose-Evergreen; the roster the
finding listed by hand had missed San Mateo, a three-college basic-aid
district. Districts are never ranked. The state-overlap "these figures
do not add" box carries the LAO systemwide structure (~$19B total, ~half
state General Fund) computed live.

Tests: +45 assertions (836 total, all passing), including the whole-dollar
gate, the roster reconciliations, the dangerous-cell verification, the
auto-reproducible/basis/denominator wording, and the integrity digest.
about.html gained a sources row; docs/SCOPE.md now lists the layer as
auto-fetchable and corrects the stale "community colleges not built"
note; verify_digest.py includes ccc-data.js.

## 2026-07-18 — V12 UC layer built (uc.html)

The University of California layer shipped (per docs/V12_UC_FINDING.md,
option (a): SHIP stripped and gated). New page `uc.html`, pipeline
`pipeline/fetch_uc_data.py`, data file `uc-data.js`. Nav extended to
nine items across every page and the 404.

**The gate — exact to the thousand, BOTH years, plus the column-sum
check.** Ten campuses plus UC's own PRINTED Systemwide column equal the
audited total operating expenses exactly: FY2024-25 $58,074,198K +
(−$306,871K) = $57,767,327K, residual $0K; FY2023-24 $52,003,294K +
$2,700,134K = $54,703,428K, residual $0K. Thousands is the finest
resolution UC publishes (the CSU tier; never called "to the cent").
Every campus column's function lines must sum exactly to that column's
printed total, with the sparse rows' assignment proven UNIQUE by
exhaustion — the build-time gate the V12 finding prescribed after a
verification pass mis-mapped a sparse row exactly as a naive build
would. No write on any failure.

**The strip — UC's own lines only, shown, never deleted.** Medical
centers $22,304,432K (38.6%), auxiliary enterprises $1,819,469K (3.1%),
Department of Energy laboratories $1,194,419K (2.1%) → core
$32,449,007K (56.2%). The DOE line is LBNL, inside UC's statements per
its own Note 1; Los Alamos and Livermore are equity-method LLCs already
outside, their equity income undisclosed by UC (stated, so no one reads
absence as zero). **The limit is on the face, non-negotiable: hospitals
are stripped, medical schools are NOT** — health-sciences instruction
and research remain in core, so per-student figures are not comparable
across campuses with and without medical schools. Stated in the limit
box, the record caps, the per-FTE view, the cite text, and the CSV
header; UCSF (health-sciences-only, no general campus — core ≈ $1.5M
per student FTE) carries the structural dagger, data-derived.

**Audit status quoted verbatim.** The per-campus table is UC's "Campus
Facts in Brief (Unaudited)" — the auditor's "other information," on
which PwC "do[es] not express an opinion." Quoted on the page and in
the method note; the audited figure is the systemwide total the
campuses reconcile to.

**Denominator and access.** Per-student uses student FTE from UCOP's
stable-URL actual-FTE PDFs; medical residents are on UC's own labeled
line and EXCLUDED from the denominator, with the resident counts
carried in the data so the choice is auditable. Both sources are public
ucop.edu URLs — `--refresh` re-fetches live and reproduces uc-data.js
byte-for-byte (confirmed). No manual-cache exception; CSU remains the
lone one. Overlap live: state educational appropriations 8.3% of
operating expenses / 9.3% of operating revenues, never summed with the
enacted budget line. Campuses never ranked.

Tests: +62 assertions (898 total, all passing), including both years'
gates RECOMPUTED from the shipped campus rows (not just the pipeline's
own gate metadata), the column-sum check re-asserted from the data,
the campus-rows-to-systemwide bridges, unit tests of the sparse-row
assignment prover (ambiguous or non-tying rows are gate failures), the
strip identity, the five-campus medical roster, the residents-excluded
FTE math, the verbatim unaudited status, the limit wording pinned in
the per-FTE view itself, the alphabetical (never value-ranked) default
order, and the integrity digest. An adversarial three-lens review ran
before the PR; its two mutation-proven blocking findings (gate
assertions that only echoed pipeline metadata; the per-FTE view able
to drop the limit silently) and its pipeline finding (campus column
order was positional, unverified against the printed header) are all
fixed — the header order is now a hard gate.
about.html gained a UC sources row and gate sentence; docs/SCOPE.md
now records all three higher-education systems as built (CSU thousand
manual-cache · CCC dollar auto · UC thousand auto stripped);
verify_digest.py includes uc-data.js.

## 2026-07-18 — Mutation testing applied to every layer

The UC pre-PR review found a weakness that had nothing to do with UC: a
+$1,000 edit to one campus figure, with the SHA-256 digest re-stamped to
hide it, passed all 898 assertions. The gate assertions were reading
`meta.gateHistory` — values the pipeline itself had written — instead of
recomputing the reconciliation from the shipped rows. **The tests were
verifying the pipeline's claims about the data, not the data.** That was
fixed for UC in the same PR; this pass applies the lesson to every layer
built before it, and proves the result by mutation rather than by
inspection.

**The harness ships with the repo:** `python3 tests/mutation_test.py`
mutates one figure per layer in a throwaway git worktree, re-stamps the
digest so the integrity check cannot be what catches it, and runs the full
suite. Every mutation must fail the suite; a surviving mutation is a hole
in the gates. It exercises two classes deliberately — a *single* figure
(caught by a children-sum-to-parent identity) and a *coordinated* edit that
moves a figure and its stored parent/control together, so the in-file
identity still holds and only an external anchor can catch it.

**Before/after, proven by mutation.** Each row: one figure changed in the
shipped data file, digest re-stamped, full suite run.

| Layer / view | Mutation | Before | After |
|---|---|---|---|
| State enacted | one agency's General Fund +$0.05B | **SURVIVED** | caught |
| State enacted (depth) | one department fund line +$1B | caught | caught |
| State actuals | one agency's actual GF +$0.05B | caught | caught |
| Cities | one city-function figure +$0.05M | caught | caught |
| Cities (headline) | the governmental total alone +$0.05M | **SURVIVED** | caught |
| Cities (fully consistent) | line + function + total together | **SURVIVED** | caught |
| Counties | one county-function figure +$0.05M | caught | caught |
| Counties (coordinated) | function + stored control | caught | caught |
| Counties (fully consistent) | line + function + control together | **SURVIVED** | caught |
| Special districts | one district's expenditure +$1,000 | **SURVIVED** | caught |
| K-12 Current Expense | one district's instruction +$0.10 | caught | caught |
| K-12 (coordinated) | instruction + currentExpense + cePublished | caught | caught |
| K-12 (fully consistent) | gate + published + function + fn×obj + split + source | **SURVIVED** | caught |
| K-12 function × object (V8) | one cell +$0.10 | caught | caught |
| K-12 funding source (V9) | one resource group +$0.10 | caught | caught |
| K-12 resource × object (V10a) | one object cell +$1 | caught | caught |
| K-12 county offices | one function figure +$0.10 | not tested | caught |
| K-12 charters | one object figure +$0.10 | not tested | caught |
| CSU | one campus operating expense +$1k | caught | caught |
| CSU (coordinated) | campus + University total | caught | caught |
| CCC | one district's Current Expense +$1 | caught | caught |
| CCC (coordinated) | district + statewide control together | **SURVIVED** | caught |
| UC | one campus total +$1k | caught | caught |
| UC (coordinated) | campus + core + audited total + gateHistory | caught | caught |
| Cities (enterprise) | one enterprise fund figure +$0.05M | not tested | caught |
| UC (prior-year shift) | $250M moved between the printed FY2023-24 campus and Systemwide components, sum unchanged | **SURVIVED** (verified) | caught |

Eight mutations survived the suite before this pass (the last found by the adversarial review of the fix itself, which is why the UC pin now covers the printed components and not just the audited total). The four "fully
consistent" and "coordinated" cases are the instructive ones: they move a
figure *and* every stored parent that would otherwise expose it, so every
in-file identity still holds — the reconciliation passes while the numbers
are wrong. No sum-check can catch that; only an anchor the data file cannot
carry along can, which is what the control pins are.


**The audit, honestly.** Most layers were already stronger than the UC
precedent suggested: K-12 (all four views — Current Expense, function ×
object, V9 funding source, V10a resource × object cross-tab), counties,
state actuals (pinned against Schedule 6 constants), CSU, CCC and the V8
depth identities all recompute from the shipped rows and caught a single
tampered figure. Two hypotheses of mine were corrected by the evidence:
cities were *not* weak in the way expected — every nonzero city-function
cell carries line detail, so the existing line-children check covers them
all — but the headline `expenditures` field was never tied to its own
functions; and the state-enacted agency↔department bridge turns out to be
structurally impossible to assert (agencies carry department-less items,
drifting up to $7.9B), so that layer needed a pinned control rather than a
child-sum identity.

**What changed in the tests.** New ANCHORS tie each layer to a figure the
data file cannot carry along — and they are of two kinds, which the code,
the tests and the about page now distinguish rather than blur:

*Published controls*, which a reader can look up: CCC's printed Table VI
statewide Current Expense, UC's audited totals for both years, CSU's
audited University total, and Schedule 6 for the state actuals. A
mismatch means our data disagrees with the source.

*Tamper pins*, which are snapshots of the statewide aggregate we
currently ship: state enacted, cities, counties, K-12 and special
districts. **No published statewide control exists for any of these**, so
a mismatch means the file changed — it says nothing about whether the
file is right. Stating what actually sits behind each: the state enacted
layer has **no build-time reconciliation gate at all** (the pipeline
prints its drift against the API's own grand total and writes
regardless), and its pin is provably not the published figure — DOF
publishes $297,862M for 2024-25 where the pin is $297,860M, the $2M being
the rounding of shipped agency values. Cities do have a real per-city
build gate, but over all funds, whereas the pin is the governmental-only
subtotal the site displays. K-12's addends are each gated to the cent
against CDE's published EDP 365, but CDE publishes no statewide total, so
the aggregate is ours. Special districts have nothing by design — that
absence is the finding.

A legitimate data refresh will fail the tamper pins. That is intended:
the constants are re-derived and the delta reviewed, never updated
silently, and a companion assertion requires every shipped year to be
pinned so a new fiscal year cannot slip through unpinned. Each per-layer
entry under "Update cadence" below now says so, since that is where a
maintainer looks before a rebuild.

**One residual gap, stated rather than implied away.** A statewide pin
catches any change to the total, but not a *transfer between* two
entities that leaves the total unchanged — moving $5B of General Fund
from one state agency to another survives every check, and the agency
bars are the largest figures on the front page. Closing it would mean
pinning per-agency totals for every year, which multiplies the refresh
burden; it is recorded here instead. The equivalent transfer inside the
city, county and K-12 layers is caught, because those layers' per-entity
figures are each anchored by a build-time gate against a published
per-entity control. Pin tolerances are set two or more orders
of magnitude above the measured float-summation noise floor (city/county
~7e-11 $M, schools ~2e-4 $) and below the smallest mutation, so accumulated
float error can never trip them and a tampered figure always does. Added
alongside: cities' functions-sum-to-total and enterprise-byFund-sum-to-total
identities, and children-sum assertions for county offices and charter
schools, which had verifiable identities that nothing asserted.

**Classification-shape and neutrality gates were checked for the same
weakness and are sound**: the shape gates recompute statewide function
sums, the sandwich rule and the LA FY2016-17 regression from shipped rows,
and the neutrality assertions read computed styles off the rendered page.
Neither reads pipeline metadata.

The about page now states the discipline plainly, because it is part of how
a reader is invited to check the record.

## Update cadence

State: one new fiscal year per annual Budget Act (late June). Run
`python3 pipeline/fetch_state_data.py` after enactment; update the
population constant annually from DOF E-4.
After the rebuild, re-derive `ENACTED_PIN` in `tests/run_tests.py`
from the new data file and review the delta — the suite fails until
it is updated, by design.

Cities: one new fiscal year per SCO filing cycle (reports for a fiscal
year appear on By the Numbers roughly a year later). Run
`python3 pipeline/fetch_city_data.py --write`; extend `SOURCE_YEARS`
when a new year appears.
After the rebuild, re-derive `CITY_PIN` in `tests/run_tests.py`
from the new data file and review the delta — the suite fails until
it is updated, by design.

Counties: same cadence and portal as cities. Run
`python3 pipeline/fetch_county_data.py --write`; the write fails
unless every county-year reconciles against `miui-wb29`.
After the rebuild, re-derive `COUNTY_PIN` in `tests/run_tests.py`
from the new data file and review the delta — the suite fails until
it is updated, by design.

K-12 schools: one new fiscal year per SACS publication (~7 months
after the June 30 close). Add the year to YEARS in
`pipeline/fetch_school_data.py` and run with --write; the write fails
unless every district-year reproduces CDE's published figure.
After the rebuild, re-derive `SCHOOL_CE_PIN` in `tests/run_tests.py`
from the new data file and review the delta — the suite fails until
it is updated, by design.

Special districts: same portal. Run
`python3 pipeline/fetch_district_data.py --write`; the finding's
figures recompute from the live data on every run. When SCO publishes
a new fiscal year, extend the window in YEARS and add the year's
late/failed list id to DELINQUENCY.
After the rebuild, re-derive `DIST_PIN` in `tests/run_tests.py`
from the new data file and review the delta — the suite fails until
it is updated, by design.

Community colleges: one new fiscal year once the CCFS-311 filings, the
district audits, and the SCFF apportionment recalculation are all final
(the recalculation lands well after the June 30 close). Run
`python3 pipeline/fetch_ccc_data.py --write --refresh`; update `FY`,
`FY_PORTAL` (the CCFS-311 FiscalYearDropdown value), and the SCFF
Exhibit C URL for the new year. The write fails unless the districts'
Current Expense of Education sum exactly to the printed statewide Table
VI total. Auto-fetchable — no manual cache. Update `CCC_STATEWIDE_CE` and
`CCC_PIN_YEAR` in `tests/run_tests.py` to the new year's printed Table VI
total — a published control, so it is looked up, not re-derived.

UC: one new fiscal year per Annual Financial Report (~five months after
the June 30 close; the UCOP actual-FTE PDF appears alongside). Run
`python3 pipeline/fetch_uc_data.py --write --refresh`; update the AFR
and FTE URLs in `AFR`/`FTE_PDF` and `FY_DISPLAY` for the new year (the
prior year stays in `AFR` so both years' gates always run). The write
fails unless ten campuses + UC's printed Systemwide column equal the
audited total exactly, both years, and every campus column passes the
column-sum check. Auto-fetchable — no manual cache. Update `UC_AUDITED` in
`tests/run_tests.py` with the new year's audited total and printed campus/
Systemwide components, from the AFR.

## 2026-07-19 — Identifier stability: slugs no longer depend on PYTHONHASHSEED

**The defect.** `pipeline/fetch_school_data.py` sorted a *set* of CDS
code tuples with a key function that returned the district **name
alone**. For the names California duplicates, the sort was a pure tie,
so the winner of the unqualified slug was decided by set-iteration
order — that is, by `PYTHONHASHSEED`, which Python randomizes per
process. Reproduced across five seeds: the same source data produced
five different identifier assignments. All three real districts named
"Jefferson Elementary" win the bare slug under some seed, and all three
appear in this repository's own git history in exactly that
flip-flopping pattern.

Two consequences, both serious:

1. **Digest reproducibility.** Re-running the pipeline on unchanged
   source produced a different `school-data.js` and therefore a
   different published SHA-256. Under this project's own authenticity
   doctrine, an honest rebuild read as a tampered copy.
2. **Permalink stability.** `schools.html#c=jefferson-elementary`
   silently pointed at a different district after a rebuild — the
   reader saw one district's figures under another's cited name, with
   no signal that anything had changed. Found while investigating the
   V13 change feed, where a slug-keyed diff of the existing history
   emitted **2,149 phantom restatements** across four commits that
   changed not one figure.

**The fix.** A shared `assign_slugs()` helper, used by districts,
county offices and charters. It sorts on the source's own stable code
(never on the name), and it qualifies **every** holder of a shared
name rather than letting one of them win the unqualified form — a
slug that names three districts is a claim we cannot support. It
raises rather than guessing if a qualifier fails to disambiguate;
`countyOffices` previously had no collision guard at all and would
have silently overwritten a record.

**Identifiers that changed** — 14, every one of them a previously
unqualified slug that several entities shared. All already-qualified
slugs are unchanged, and **no figure moved**: 202,976 numeric cells,
CDS-keyed, identical before and after.

    11 districts   hope-elementary -> hope-elementary-tulare, and the
                   Jefferson / Junction / Lakeside Union / Liberty /
                   Mountain View / Ocean View / Pacific Union / Pioneer
                   Union / South Bay Union / Washington equivalents
     3 charters    discovery-charter -> discovery-charter-0355,
                   excel-academy-charter -> -2073, journey -> -1974

**Old links.** A retired identifier is never silently resolved to a
guess — earlier builds handed it to an arbitrary one of the entities
sharing it, so resolving it now would restate the original defect in a
quieter form. `meta.ambiguousSlugs` records what each retired slug
could have meant; `schools.html` explains the ambiguity and offers the
candidates, and `address.html` says the same for a stale `sd=`.

**Assertion.** `test_identifier_stability` runs the real assignment
function in subprocesses under five `PYTHONHASHSEED` values over the
real shipped roster and requires byte-identical output; it also
requires every shared name to be disambiguated for every holder and
recorded in `meta.ambiguousSlugs`. Proven to fail on the pre-fix code
(five seeds, five distinct results) and pass on the fixed code (five
seeds, one result). Verified end-to-end as well: two full pipeline
runs under different seeds produce a byte-identical `school-data.js`.

**Refresh note.** The charter number is **not** unique — 0756 is shared
by the nine High Tech schools — so it qualifies a shared *name* and
never identifies a charter. If CDE ever publishes two same-named
charters sharing a number, the build fails rather than merging them.

## 2026-07-19 — Fonts self-hosted; the architectural rule is now asserted

**The mismatch.** `docs/SCOPE.md` is normative and names exactly two
runtime third-party services — OpenFreeMap tiles on the map view, the
Census geocoder on the address view — both keyless, unmetered, and
non-load-bearing. But all ten pages also loaded IBM Plex Mono from
`fonts.googleapis.com` and `fonts.gstatic.com`, undocumented. The
document that decides which features are allowed had stopped describing
the site.

Two costs, beyond the inaccuracy. Every page view disclosed the
reader's IP and user-agent to a third party for no functional reason —
on a site whose address view is careful to say the typed address never
leaves the browser except to census.gov. And a page could not render
as designed without a network round-trip to Google, which is precisely
the class of dependency `docs/SCOPE.md` exists to prevent.

**Resolved by removal, not by amendment.** IBM Plex Mono is licensed
under the SIL Open Font License 1.1, which permits redistribution and
self-hosting provided the license travels with the files. The three
weights the site uses (400/500/600) are now vendored at
`vendor/fonts/`, in both the latin and latin-ext subsets, with
`OFL.txt` alongside as that license requires; `NOTICE` records the
component and its terms.

The files are the same ones the browser was already fetching, so
rendering is unchanged. `unicode-range` is preserved, so the subsets
stay lazy: a page load fetches four of the six files (three latin plus
one latin-ext), 40,292 bytes measured, and the two unused files are
never requested. Codepoints in neither range — the ▲▼ ✕ ✓ marks — fall
through to the platform mono stack exactly as they did before.
Measured after the change: **zero external subresource requests.**

**The rule is now a test, not a sentence.** `test_runtime_origins`
fails the build if any page loads a subresource from a host other than
the two SCOPE.md names. It distinguishes what the browser *fetches*
from what the record *cites*: `<a href>` links out to source agencies
and `<link rel="canonical">` are not dependencies and do not trip it.
Proven against six regression forms — a Google Fonts stylesheet, a
preconnect hint, a CDN script, a remote image, a font pulled in
through CSS `url()`, and a remote favicon — all caught, with no false
positive on the four legitimate patterns.

A normative rule that is not asserted decays into a preference. This
one drifted for the whole life of the project; it cannot drift again
silently.

## 2026-07-19 — The record of changes (V13 option (b), mechanical only)

**What shipped.** `revisions.html`, eight per-layer record files, and
`pipeline/revisions.py`. Every pipeline now compares the figures it is
about to publish against the ones already published, and appends what
moved. The record reports **that** a figure changed and by how much. It
never reports why.

**Why it never reports why.** A changed figure has at least five
possible causes: the source restated its own published data; the source
redefined it; we fixed an extraction bug; we changed method
deliberately; or an upstream Ledger layer we consume was refreshed. Two
of those are observationally identical — a restatement and a
redefinition both look like "old code, new source, different number" —
and separating them means reading the source's release notes, which no
engineering removes. On the three State Controller layers it is worse:
those pipelines push aggregation into the portal (`$select=sum(value)`),
so the rows never reach this machine and, once the portal revises, the
prior figure cannot be reproduced by anyone, including us.

Option (a) in the finding would have accepted a per-refresh human
labelling step. That was rejected here: refreshing the data is the one
process that must stay frictionless, because friction there is how a
project like this quietly stops being updated. A feed that guessed at
cause would also be exactly the class of unearned claim the rest of the
site exists to avoid.

**Three event kinds, all first-class.** Changed, appeared, disappeared.
The last two carry most of the weight: when the FY 2016-17 city
classifier was fixed, money moved between category keys that did not
previously exist, so counting only changed values reports 31 events out
of a 482-city correction and misses most of its magnitude.

**Detection compares figures, not digests.** Proven on live data during
the build: a rebuild of `school-data.js` moved `meta.generated` from
2026-07-18 to 2026-07-19, which changed the published SHA-256 —
`0df9b43e…` to `b1e9e5bf…` — while the figures-only digest stayed
`e09190c1…` and not one figure moved. The record correctly stayed
silent. That is the case docs/V13_CHANGEFEED_FINDING.md §6 warned
about, reproduced by accident and handled correctly.

**Identity, not name.** Figures are keyed on the source's own stable
code — CDS, MIS district code, agency id and department code, charter
number with name and county. Renaming an entity is not a changed
figure, and is asserted as such.

**The one attributed event.** The FY 2016-17 city classifier fix, 31
figures, $3,061.8M of movement, re-derived from git (491218c..342a042)
and labelled as **our own correction**. Its cause is known rather than
inferred because it is our own commit. It is the only entry in the
whole system that carries a cause, and the refresh path cannot write
one — the note is a module constant, not a field any pipeline can set.

**The backfill does not backdate coverage.** `meta.begins` is the first
batch written by a real refresh (2026-07-19), never the backfilled
batch's own date (2026-07-14). An earlier version took the latter and
made a 2026-07-14 citation look fully covered; the finding is explicit
that backfill yields one event and the record otherwise starts empty,
and the file now says so.

**Same-day citations are answered honestly.** A citation carries a
date, not a time. If a build landed on the day a reader cited, the
checker returns "cannot be determined for that date" rather than
guessing in either direction.

**Payload discipline.** Records are per-layer, so a light page never
pays for a heavy one, and each stores a display name only for entities
it actually mentions. A first version stored one per entity and made
the special-district record 426 KB to describe zero events; pruned, the
whole eight-layer record is 4.4 KB raw / 891 B gzipped, and no existing
page loads any of it — only `revisions.html` does.

**Provenance recorded, automatically.** Each batch carries the
figures-only digest, the pipeline commit it was built from (which
excludes "we changed the method" mechanically, without asking anyone),
and, where the source publishes one, its own rows-updated stamp. The
baseline batches record `+dirty` commits because they were written from
a working tree mid-change; that is accurate and left as-is.

**Assertions.** `test_revisions` proves the record is derived rather
than echoed — each layer's figures digest must recompute from the
shipped data — and that no batch except the backfilled one claims a
cause. 1136 assertions pass.

## 2026-07-19 — Cross-layer search (search.html)

**What shipped.** `search.html`, `search-index.js`, and
`pipeline/build_search_index.py`. One box over 8,068 entities in ten
layers: state agencies and departments, cities, counties, K-12
districts, county offices, charter schools, special districts,
community-college districts, CSU and UC campuses. Typing "Fresno"
returns 64 results in 7 layers — the city, the county, the unified
district, the county office, the CSU campus, a charter, and 58 special
districts.

**The index adds no data.** Every name, identifier and flag is copied
from a file the site already publishes, and the index is rebuilt from
those files rather than maintained by hand.

**It carries no figures, deliberately.** This is the whole design
problem. A city, the county containing it, its school district and its
community-college district spend on overlapping populations, with
different responsibilities, on different accounting bases. Putting four
numbers next to each other in one list invites exactly the arithmetic
the rest of the site refuses. So a result names an entity, names its
layer, names that layer's basis, and says whether the entity carries
comparability notes — and to see a number you follow the link into the
layer, where the figure appears with its own caveats attached. The
entry shape is fixed at five fields with no room for a figure, and the
test suite asserts that not one dollar sign appears in the results view.

**Grouped, never ranked across layers.** Groups are ordered by how well
the query matched inside them, which ranks the query's relevance and
never the layers against each other. Each group states its basis in the
layer's own words.

**Names match their own pages.** Community-college districts are
title-cased exactly as ccc.html renders them (the portal publishes
upper case); CSU and UC campuses use the source names their pages show,
rather than a constructed "California State University, San Francisco
State University". Where a system's own published name differs from its
campus names, that system name is searchable as a layer term taken from
the layer's `meta.sourceLabel` — so "University of California" finds
campuses filed as "Berkeley" without inventing an alias.

**Identifier discipline.** 7,626 of 8,068 identifiers are just the
slugified name and are stored empty to save 52 KB gzipped. That is a
derived identifier, which is the exact fragility removed from the K-12
pipeline earlier today — so the builder proves the round-trip for every
entity against the real data files before shipping, and the suite
re-proves that every indexed identifier resolves to a real record.

**Payload.** 476 KB raw, 86 KB gzipped, loaded only by `search.html`.
No existing page pays for it.

**A regression this caused, and the honest fix.** Adding Search made
eleven primary-nav destinations, which wrap to six rows in the phone
nav's two-column grid and pushed the front door's statement to 374px —
outside the top 40% of an 844px screen, and past an existing assertion.
Rather than relax that threshold, the change record moved out of the
primary nav: it is a provenance surface like About & method, and stays
reachable from every footer and from about.html's own section on it.
Ten destinations, five rows, assertion passes on its original terms.

**Assertions.** 1176 pass. The new ones cover layer grouping, the
absence of any cross-layer total (no dollar figure may appear, and the
page may not say "combined", "in total", "sum of"), dagger surfacing on
UCSF and basic-aid districts, identifier resolution, the permalink
round-trip, keyboard navigation into and out of the results, and no
horizontal overflow at 360, 390 and desktop.

## 2026-07-19 — Inflation adjustment on the state page (V14)

**What shipped.** `pipeline/fetch_deflator.py`, `deflator-data.js`, and a
Nominal/Real toggle on `index.html`, per docs/V14_INFLATION_FINDING.md.

**This is the first figure on the site that is not reproduction, and it
says so.** DOF publishes a fifty-year spending series and never deflates
it; CDE's Current Expense workbook has no constant-dollar column; the
State Controller is an explicit pass-through. There is no official
practice to adopt, so the adjustment is the Ledger's own methodological
choice — and the words "this adjustment is the Ledger's, not the
source's" appear in the view, in the citation and in the CSV, not in a
footnote.

**The index** is the one California statute names for government
spending: Education Code 42238.1(a)(2)'s Implicit Price Deflator for
State and Local Government Purchases, published by DOF — the department
that statute designates as its reporter. Two limits travel with it in
the data and on the page: it is national, not Californian, and the LAO,
which used it explicitly from 1999 to 2008, called it "not a
particularly good indicator of increases in school costs."

**No fiscal-year averaging of our own.** DOF publishes the index already
averaged to California fiscal years, so the pipeline adopts that file
wholesale. The most arbitrary of the four decisions became no decision.

**Forecast years are never adjusted.** DOF flags FY2025-26 onward as
forecast, and FY2025-26 is the state layer's newest year. In the trend
view a forecast year is **omitted from the real line entirely** rather
than plotted at its nominal value — a nominal point on a real line would
make the trend appear to jump for a reason that is an artefact of the
deflator, not of spending. In single-year views it shows nominal with a
loud warning. Found while driving the real page logic against the real
data, not by inspection.

**Disabled where deflation is arithmetically inert.** Percent-of-total
is a ratio of two same-year figures, and the enacted-versus-actual
difference is too; deflating both sides changes nothing. Rather than
render a control that provably does nothing, the toggle is disabled
there and says why on hover. Verified: shares are identical to 1e-12
under real.

**Vintage recorded with the data.** A fixed base year does not mean
fixed values — BEA revises annually and DOF republishes each May and
November. `deflator-data.js` carries DOF's own "Updated:" stamp, the
source URL, and the SHA-256 of the exact bytes parsed, and the deflator
is registered as a layer in the V13 change record so a republication
surfaces as moved figures like anything else.

**A source anomaly, named rather than absorbed.** DOF's May 2026 file
lists fiscal year 2029-30 **twice with different values** (153.61942 and
158.43815). The parser detects duplicate fiscal years: a duplicated
ACTUAL year blocks the build outright, and a duplicated FORECAST year —
which this site never uses to adjust anything — is dropped and recorded
in `meta.sourceAnomalies` rather than silently resolved by taking
whichever row came last. Same discipline as the state layer's named
SOURCE_RESIDUAL.

**Scope shipped: the state page only.** Cities/counties and K-12 are in
the finding's scope and are NOT yet built. The state page is the
reference implementation, and it is the layer that contains the forecast
blocker.

**Assertions.** 1220 pass. The new ones are mostly about honesty rather
than arithmetic: that a real view names the index, statute, base year
and vintage; that the citation and CSV carry the basis and never stay
silent about it; that nominal is the default and always one interaction
away; that the toggle is disabled where inert; that the base year is an
actual and never a forecast; and that the forecast warning lists only
years the page shows.

## 2026-07-19 — Inflation adjustment extended to cities/counties and K-12

Completes the V14 finding's scope. `cities.html` and `schools.html` now
carry the same Nominal/Real toggle as `index.html`, built to the same
contract.

**Every discipline carried forward.** The sentences the pages render
live in `deflator-data.js` beside the data, never in page markup, so a
page cannot say something the data does not. "This adjustment is the
Ledger's, not the source's" renders in the view, the citation and the
CSV header on all three layers, each naming the source that publishes
nominal only — the Controller for cities and counties, CDE for K-12.
Both limits ride along. Nominal is the default and always one
interaction away. The duplicate-fiscal-year guard is unchanged. The
toggle is disabled wherever deflating both sides of a ratio provably
changes nothing.

**Sensitivity is stated per layer, on the right face.** A single shared
sentence would understate the risk on K-12 and overstate it on the local
layers, so `meta.windowNotes` carries one per layer and each page renders
its own:

- **K-12** — rendered as a warning, not a footnote: the window is three
  years, this deflator and DOF's California CPI differ by **2.68
  percentage points, roughly 42% of the whole measured inflation**, and
  that is enough to change the sign of a real trend. The page tells the
  reader to treat a small real change as indistinguishable from no
  change, and the citation and CSV repeat it.
- **Cities and counties** — the less sensitive case: 0.6 points over
  eight years, disagreeing about the direction of exactly one city in
  482. The same note carries the result the feature exists for.

Asserted both ways: the K-12 face must contain the 2.68-point figure and
the word "sign", and the cities face must NOT — a page may not claim a
sensitivity that is not its own.

**The headline result reproduces in the shipped build.** Recomputed from
the shipped `city-data.js` through the shipped `deflator-data.js`, using
the pages' own adjustment: **71 of 482 cities rise in nominal dollars and
fall in real ones** over FY2016-17 → FY2023-24, and **none go the other
way**. Statewide city spending is +60.9% nominal against +22.8% real in
FY2024-25 dollars. That check is now an assertion, not a one-off.

**Forecast years.** Neither new layer's window contains one — the local
window ends FY2023-24 and K-12 ends FY2024-25, both actuals — but the
guard is present on both pages so a future year cannot slip through
unadjusted-but-unmarked.

**Assertions.** 1265 pass.

## 2026-07-20 — The print record sheet control

The record sheets shipped on every layer but were reachable only by
pressing Cmd+P, so the feature was effectively invisible. There is now a
"Print record sheet" button beside Cite and Download CSV on all nine
layers, in the same outlined-pill vocabulary as the demoted CSV control.

**Disabled with a reason, not hidden.** Four layers need a record
selected first. The control stays present and explains itself rather
than vanishing: a control that disappears is invisible to exactly the
reader who has not selected anything yet, and an element that appears
and disappears is more disorienting under a screen reader than one that
is present and disabled. This matches the inflation toggle, which is
already disabled-with-reason where deflation is arithmetically inert.

| Layer | Gate |
|---|---|
| state, CSU, CCC, UC | always enabled |
| cities/counties | a city or county selected |
| K-12 | a district, county office or charter selected |
| special districts | a district record open |
| address | a lookup performed |

**It throws on no layer.** The gate is computed inside each page's
closure and synced at the top of every render, so it cannot drift from
what is on screen, and every gate call is wrapped. A print-path throw
has blanked a page's on-screen record before (districts, `money0`), and
a throw here would leave the button enabled over an empty sheet.

**The control does not print itself.** This is measured, not grepped:
csu/ccc/uc put their action row in `.actions` while their print CSS
hides `.hd-actions`, so a grep would have passed while the button leaked
onto the paper.

**Assertions.** 1429 → 1518 (+89). Also fixed a 2px horizontal overflow
at 360px that the extra button introduced — the action row could not
wrap.

## 2026-07-20 — The inflation toggle says what it is

The nominal/real control shipped as two pills reading "Nominal" and "Real"
with no visible label. Its only name was `aria-label="Dollar basis"` —
screen-reader-only, and itself accounting vocabulary. A reader with no
finance background had no way to know the control was an inflation
adjustment. In the default nominal state the word "inflation" did not
appear anywhere on screen on any of the three layers.

The precise terms are kept. "Nominal" and "Real" still read exactly that.
What is added is a plain-language name for what the control does:

- A visible **Inflation** label bound to the group, with the accounting
  `aria-label` removed and `aria-labelledby` pointing at the visible word,
  so the announced name and the rendered name cannot drift apart.
- Each pill states its operation: "Dollars as filed, with no adjustment for
  inflation" / "Adjusted for inflation into FY 2024-25 dollars. This
  adjustment is the Ledger's, not the source's."
- The real-dollar lead now reads **ADJUSTED FOR INFLATION — INTO FY 2024-25
  DOLLARS, BY THE LEDGER, NOT THE SOURCE**, carrying all three facts the
  reader needs in one line, at the point of use.
- The nominal chip says "NOT ADJUSTED FOR INFLATION" rather than only
  naming the basis.
- The inert reasons drop "deflating" for plain words, and are mirrored into
  the accessibility tree — a disabled button is not focusable, so a reason
  carried only in `title` reached nobody.

**Two defects were caught by adversarial verification and fixed before
this shipped.** The label was first placed as a bare sibling in a
space-between wrapping row; measured, it detached from its group at 16 of
18 widths, and on the state page at 1024/900/414/390 it came to rest beside
the *unit* group — labelling the wrong control, which is worse than
labelling none. It is now structurally bound in one inline-flex box, and
adjacency is asserted at twelve widths on three layers rather than at one
convenient size.

The second was a copy defect of exactly the kind this change was meant to
prevent. `realOn()` excludes percent units but **not** the actuals view, so
figures there are adjusted — while the first draft of the reason read "No
inflation adjustment applies here" beside a note reading "ADJUSTED FOR
INFLATION". Plain language that is false is worse than jargon that is true.
It now says the basis cannot change the gap, which is what is actually the
case.

**No figure changed.** 1,162 rendered figures across 16 views compared
against main: byte-identical.

**Assertions.** 1518 → 1687 (+169).

## 2026-07-20 — The refusal guard now establishes position, not value

`classify_expenditure()` was made shape-driven after the FY 2016-17
misclassification, with an explicit refusal for unrecognised layouts. It
did not refuse the layout that matters.

SCO has shipped three layouts of the same table. Pre-FY 2016-17 the
function group is repeated in `category`, `subcategory_1` **and**
`subcategory_2`. The guard tested only whether `subcategory_1` held a
known group name — in that layout it does — so the row was accepted,
routed down the FY 2017-18+ branch, and every police and fire dollar was
filed under `safetyOther`. Measured live against FY 2009-10: 8 of 8 row
shapes accepted, $15.2B misfiled, police and fire reading exactly $0,
every totals gate passing. Conservation cannot see classification.

**The fix is positional.** The line slot must be proven to carry a line.
If the value in the line position is the group itself, nothing
establishes which field it came from, and the row is refused. Verified
across all 22 published years: refuses all 14 pre-2017 years (112 of 112
row shapes), accepts all 8 shipped years (1,842 of 1,842). Zero false
refusals, zero false accepts. Regenerating `city-data.js` produces a
byte-identical file.

**A second, independent defence.** Shape-gate rules 1-3 all reduce to "is
this named line zero", which a group-echoing layout defeats in one step:
every dollar lands in the residual bucket, so nothing named looks
missing. New rule 4 bounds the residual: `safetyOther` and `cultureOther`
cannot exceed 35% of their group. Clean shipped years measure 9.5-10.6%
and 11.7-14.3%; the misclassification measures 100%. Either rule alone
now stops the build.

**The class, audited across every pipeline.** Forty candidate sites were
examined and adversarially re-checked; seven were confirmed sound. Six
survived as live instances of the same class. The most serious is in
`revisions.py`: the change feed keys city, county and state figures on
their RANK in an amount-sorted array, and emits the label index itself as
a value. `lineLabels` is `sorted()` over the observed label set, so a
single new label renumbers up to 90 labels across 76,112 line entries —
and the change record, whose whole premise is mechanical trustworthiness,
would publish tens of thousands of phantom changes. Not fixed here;
recorded as the next priority.

**Assertions.** 1687 → 1715 (+28), including the FY 2009-10 case
reproduced verbatim from the source.

## 2026-07-20 — The change feed is keyed on identity, not rank

The slug-instability lesson reappearing in a second subsystem. Several
payloads ship a figure as a row in an array **sorted by amount** — city
and county `lines`, state `funds` and `programs`, K-12 `byResource.n`.
`_leaves` walks a list by enumeration index, so the key a figure got was
its RANK. Measured: 576,953 of 825,331 keys (69.9%) were rank-derived;
the districts layer was 100%.

Two consequences, both reproduced against the shipped data:

- `lineLabels` is `sorted()` over the observed label set, so one new
  label anywhere in California renumbers up to 90 labels and shifts every
  index below it. **The feed reported 76,114 events for a single real
  change.** It now reports 1.
- Two lines swapping order, with neither value altered, were reported as
  each other's change — 4 phantom events. Now 0.
- City rows are `[labelIndex, dollars]`, and the index is numeric, so the
  walker emitted it as though it were a figure. A pure re-indexing read
  as a changed value. The index is no longer emitted at all.

Every figure is now keyed on something intrinsic: the line label, the
fund code, the program code, the resource code, or a NAMED fixed slot
(`exp.gov`, `nr.N`). A duplicate intrinsic key refuses rather than
letting one figure silently overwrite another.

**Nothing historical was rewritten.** Zero of the 31 published events
were rank-derived — they are all `byFunction` paths from the FY2016-17
backfill. Re-deriving the backfill under the new keying produces the
identical 31 events and the identical cell count. `--verify` passes on
all nine layers.

**The class, audited across every subsystem.** 32 sites examined, each
adversarially re-checked; 10 confirmed sound and 9 more confirmed as the
*sound* side of the distinction (an index into a constant declared in
code is meaning, not rank). Five unstable identifiers survived, of which
one is **already shipping wrong**: `fetch_district_data.py` groups
districts on `(name, county)` but writes them to `ents[name]`, so two
same-named districts in different counties collide and the second
overwrites the first. Verified in the shipped file — Rural North
Vacaville Water District appears twice, and one copy carries **Sutter**
county for a district in Solano. Not fixed here; recorded as the next
priority.

**Assertions.** 1687 → 1705 (+18), all 18 executed.

## 2026-07-20 — Districts: grouped on (name, county), stored on the name

A published figure was wrong. The special-district pipeline grouped
filings on `(norm(name), county.lower())` — correctly — and then wrote
both the directory and the amounts keyed on the **display name alone**.
Three pairs of same-named districts in different counties collided, and
each pair shipped as one entity.

The grouping being right is what made it invisible. Anyone reading the
aggregation concluded the code was correct, and no totals gate could see
it either: the money was all present, attributed to one entity instead of
two. The defect was at write time, not at aggregation time.

What was published wrong, and what the source actually says:

| record | was | is |
|---|---|---|
| Rural North Vacaville Water District | Sutter, "Levee" | **Solano, "Community Services"** |
| — its FY 2017-18 expenditure | $1,268,460 | **$1,101,223** |
| Hamilton City Fire Protection District | Sonoma, JPA | **Glenn, "Fire Protection"** |
| California Risk Management Authority (CRMA) | Fresno+Madera merged | **split, Fresno and Madera** |

The $1,268,460 was the arithmetic sum of two independent agencies —
$1,101,223 filed in Solano and $167,237 filed by a Sutter levee district
that merely shares the name. `fetch_amounts()` grouped by name and year
with no county at all, so the two were added together; worse, they landed
in different buckets, so one district appeared to run both governmental
and enterprise activity.

**The fix** keys `ents` and both amount tables on the same `(name,
county)` pair the grouping already uses, and refuses on a duplicate rather
than overwriting. Six records now match the source's county, activity and
filing years exactly, verified row by row against SCO.

A phantom disappeared as a side effect. `rural-north-vacaville-water-district-solano-list-only`
existed because the Solano delinquency row could not match a directory
keyed under Sutter, so it fabricated a second entity. With the identity
fixed the row matches the real district, and its late-filing marker now
appears in that district's own filing string.

**Recorded as our own correction** — the feed's one attributed event type,
130 events, marked `OUR CORRECTION` on the record page. The invariant that
keeps this honest is unchanged and now asserted: a note can only come from
a constant declared in the pipeline. The refresh path may apply a declared
correction; it can never invent one.

**The class, audited.** 37 sites across five areas, adversarially
re-checked; 19 confirmed sound. Ten are structurally vulnerable with no
live collision. Two more **live** collisions were confirmed and are not
fixed here: `fetch_state_data.dept_depth()` keys funds on `fundCd` alone
where DOF distinguishes by `(fundCd, fundLglTitl, fundClassCd)`, and
`meta.fundNames` is one global dict merged across six years and ~190
departments, so a fund renamed between budget acts loses one of its names.

**Assertions.** 1733 → 1774 (+41).

## 2026-07-20 — A fund is (code, title, class), not a code

Two identity collisions in the state layer, both confirmed in the audit
attached to the district fix, both enumerated against DOF rather than
inspected.

**Fund rows were keyed on the fund code alone.** DOF distinguishes a fund
by code, legal title and class together. Where it publishes two titles
under one code, the pipeline added them and kept whichever class arrived
first. Probing all 1,155 department-years across the six loaded budgets:
**43 collisions, every one fund 0001**, where DOF emits "General Fund" and
"General Fund, Proposition 98" as separate rows. The Proposition 98
education guarantee was being folded into the general fund line.

**The fund-name legend was one global dictionary** merged across six
budget acts and ~190 departments per year, so a fund renamed between acts
kept only its latest name. **23 codes drift** across the window:

| code | was shown as | actually |
|---|---|---|
| 3085 | Behavioral Health Services Fund, in every year | Mental Health Services until FY 2025-26 (Prop 1 renamed it) |
| 3246 | Civil Rights Enforcement and Litigation, in every year | Fair Employment and Housing until FY 2023-24 |
| 3209 | Health Plan Improvement Trust, in every year | Office of Patient Advocate until FY 2023-24 |

Reading our FY 2020-21 page, a fund appeared under a name it would not
carry for five more years. Names are now scoped per year — the same shape
the school resource titles already use, for the same reason.

**No gated total moved.** Every agency and department figure is identical,
and the V8 parent-sum gate passes unchanged: splitting a row into two of
the same class preserves the class sum. What changed is which rows the
fund drill shows and what they are called. A row now carries its own legal
title only where one code carries more than one, so the payload cost is
the 43 real cases rather than a title on every row.

**Recorded as our own correction** — 129 events: 43 disappeared and 86
appeared, and none merely changed, because none was. That is the event
class the V13 finding warned a value-only feed would under-report, and it
is exactly what a re-keying looks like.

The duplicate-key guard added with the change-feed fix earned its keep
here: it refused the build the moment fund codes stopped being unique,
rather than letting one figure overwrite another.

**One of my own assertions was wrong and is now corrected.** The
rank-detection check written with the change-feed fix treated any numeric
path segment as a rank, but a fund code is legitimately numeric
("funds.0001"). It now matches the specific rank signatures — a bare
ordinal where a name belongs, or the two-ordinal pair a list-of-lists
produced — verified against ten cases separating codes from ranks.

**Assertions.** 1774 → 1888 (+114).

## 2026-07-21 — Three identity defects: a leaked key, a positional year, a name-derived id

The remainder of the identity audit. None changed a published figure, so
the change record is silent — correctly.

**1. A retired identity rendered its raw internal key as a name.**
`record_revision` stored the key AS the label whenever an event mentioned
an identity it had no name for, and the page rendered labels verbatim, so
a reader would have been shown `campus:Cal Poly Humboldt` where a campus
name belongs. Labels already carry forward for retired identities — that
is the point of labelling separately from keying — so the fallback was
never needed. The pipeline no longer writes it, and an identity with no
known name now renders as a marked identifier rather than as a name.
Checked every layer: no shipped label is merely its own key.

**2. The district SCO link derived its fiscal year from array position.**
`yyyy = 2017 + i` reproduced the right answer only because the window
happens to begin at FY 2016-17. Prepending a year would have silently
repointed every district's outbound "filing at the State Controller" link
to the wrong year. It now reads the ending year out of the year LABEL —
the same rank-as-identifier lesson as the change-feed keying.

**3. The state agency id was `slugify(name)[:24]`.** Enumerated across all
12 agencies in the six loaded budgets: **zero truncation collisions
today**, though truncation is load-bearing for five of the twelve (the
longest full slug is 38 characters). The live hazard was the rename: a DOF
rename moving no money would change the id, and the change record keys on
it — **4,821 keys for the largest agency, 22,931 across all twelve**, each
republished as disappeared and then appeared. Naively re-keying onto the
code would itself have produced ~4.9 MB of events against a 64 KB budget,
so the id is instead **pinned to DOF's own webAgencyCd through a declared
mapping**: the published ids keep the exact values they have today, and
the display name no longer feeds the identity. An unknown code refuses the
build rather than minting an id from a name.

Verified: every agency id is unchanged across all 72 agency-years, no
permalink moved, and `data.js` differs from its predecessor only in the
generated date and the digest that follows from it.

**Assertions.** 1888 → 1916 (+28).

## 2026-07-21 — Historical depth, part 1: the state record reaches its floor

Per docs/V15_HISTORICAL_FINDING.md. Six fiscal years become **nine** —
FY 2017-18 through FY 2025-26. The floor is the source's, not a choice:
DOF's structured budget API returns 12 populated agency rows for
FY 2017-18, FY 2018-19 and FY 2019-20, and an **empty array** for every
earlier year. It does not 404, so an availability check written against
status codes would have claimed coverage back to 2007-08.

**Every added year passes every gate**, recomputed from the shipped file:

| FY | agencies | depts | fund rows | programs | V8 class-sum | position guard | actuals |
|---|---|---|---|---|---|---|---|
| 2017-18 | 12 | 190 | 1,700 | 695 | PASS | PASS | gated |
| 2018-19 | 12 | 192 | 1,715 | 661 | PASS | PASS | gated |
| 2019-20 | 12 | 192 | 1,712 | 676 | PASS | PASS | gated |

Actuals for the three years gate clean off Schedule 9 against Schedule 6
(138/138/139 department rows), so the enacted-vs-actual view deepens too.
FY 2020-21 actuals remain honestly absent, as before.

**FY 2019-20 does not reconcile inside DOF's own data**, and the second
source settles it. The API's `stateGrandTotal` exceeds the sum of its own
twelve agency rows by 2,353k. DOF's *printed* Schedule 9 for that year
gives General Fund 147,780,666 + Special 61,092,907 + Bond 5,904,388 =
**214,777,961** — exactly our agency rows. Two DOF publications disagree
with each other; the Ledger reports the agency rows as published and
records the difference as an exact reviewed constant, never a tolerance
band.

**Per-resident stops at FY 2020-21, and says so.** The population series
rests on the 2020 census benchmark; DOF's estimates for the three added
years rest on the 2010 benchmark, and splicing them would put a
denominator break inside a per-resident line. Dollar and percent figures
cover all nine years.

**Structural breaks are stated where the series crosses them** (M-9): COVID
federal relief as a one-off inside the window, SB 1 stepping transportation
up at its start — and, equally important, that the record stops *above*
redevelopment dissolution, realignment, LCFF, the ACA expansion and
GASB 68, so a reader is not left to assume none exist.

**Cities and counties refused, visibly** (cities.html M-8). The source
offers twenty-two years and the Ledger loads eight. The page now states
why: the eight governmental categories carry 100% of the statewide total in
FY 2013–16 and 50.6% in FY 2017; six of eight functions change meaning at
the break (public utilities −99.5%, transportation −73.3%, health −70.2%)
while the grand total moves 1.3%; and before FY 2016-17 police and fire are
a single undifferentiated value, so the per-resident police figure the page
is built on does not exist. Named as a choice, not left as a gap.

**A new concept: coverage changes are not figure changes.** Extending the
window made every figure in three years "appear" — 12,646 events and a
1.1 MB record against a 64 KB budget. Nothing had moved; the Ledger looked
further back. A declared COVERAGE entry now records one stated fact —
**12,517 figures entered the record with FY 2017-18, FY 2018-19 and
FY 2019-20** — and suppresses those appearances, while changes in years
already covered are still reported one by one. **Zero** such changes
occurred, so the extension moved nothing. The record is 17 KB.

The note-attribution invariant is unchanged and still asserted: a note may
come only from a constant declared in the pipeline. There are now two
kinds — a correction and a coverage change — and the refresh path can apply
either and invent neither.

**Assertions.** 1916 → 2046 (+130).

## 2026-07-21 — A check that cannot fail is not a check

The dormant-assertion lesson, moved from the test suite into the pipeline.
A gate whose comparison target is empty passes vacuously: it loops over
nothing, accumulates no failures, and reports success.

**This was shipping.** `fetch_ccc_data.build()` reconciled funded FTES and
state General Fund with `if appn_statewide.get("fundedFtes") and ...`, and
`fetch_apportionment()` returned `statewide == {}` for FY 2022-23 — its
page-identity regex required a heading ending in "CCD" or "District", and
the statewide summary page is headed "Statewide Totals", so the target was
excluded by construction. The `and` short-circuited and both comparisons
were skipped while the build printed its success banner.

**Was that year ever verified? No.** Forensic proof: the shipped
`statewide.fundedFtes` is 1,100,664.62 — the pipeline's own fallback
self-sum — while the Chancellor's Office control prints 1,100,664.61. The
published figure was never the published control. Reconciled properly now,
funded FTES lands within +0.01 and state General Fund at **exactly $0**, so
no figure was wrong; only the assurance was false. That is its own defect:
`meta.daggers.basicAid` publishes the claim that the community-supported
count "matches the Chancellor's Office's own figure", and that comparison
had never run.

**The guard.** New `pipeline/gates.py` — `require_target()` refuses an
empty comparison target, `require_rows()` refuses a row count below the
floor a source must produce, and a minimum of zero is itself rejected
because "at least none" is not a check. Both raise `VacuousGate`, a
`SystemExit` subclass, so a build stops the way every other gate failure
stops it. Applied to CCC (Table VI and apportionment), K-12 (the Current
Expense header and district count, plus the classification-shape gate),
cities (city-years to shape-check) and state (a department reporting funds
must have parsed fund rows).

**A second live case, and an embarrassing one.** `verify_digest.py` carried
a hardcoded list of ten files while **twelve** shipped payloads carry a
digest: `deflator-data.js` and `search-index.js` had never been verified,
and the run still printed a clean sweep. Every recent PR of mine cited
"10 files VERIFIED" as evidence. The list is now discovered from the files
themselves, the run refuses if any digest-bearing file would be skipped,
and all twelve verify.

**A third.** The cities reconciliation guarded itself with
`if key in official and official[key] > 0`, so any city-year whose
published control is zero was never compared. Three of 3,856 shipped
city-years carry a published total of zero. They are now counted as
unreconciled rather than silently passed, and a build must reconcile at
least 3,800 of them.

**Also closed:** CCC's community-supported count used a truthiness test, so
a legitimately-zero published control would have disabled the check. It now
tests `is None`, because zero is a real published value.

**Assertions.** 1916 → 1945 (+29), including a mutation proof: emptying a
gate's target now refuses where it previously produced a clean build.

## 2026-07-21 — The UC strip: a gate that could not fail, and a write that never ran

Two of the four gates left open by the vacuous-gate sweep. The other two
(the state program gate and schedule9's Gate 2) remain.

**The strip identity was a tautology.** `core_k` was defined as
`auditedTotal − med − aux − doe` and then asserted to sum back to
`auditedTotal`. Substituting the definition gives `auditedTotal ==
auditedTotal`. Measured over 2,000 randomised trials — including
components exceeding the total and negative components — it fired **zero
times**. It is replaced by checks that constrain something: each stripped
component must have been found, the residual must be non-negative, and it
must fall in a 30–90% band (the real figure is 56.2%).

**No published provenance claim rested on it.** `meta.gate` names exactly
two identities — campuses + Systemwide == audited total, and the
column-sum check — and both are real. The tautology was dead weight, not
a load-bearing falsehood.

**The "unguarded aux" is guarded, one layer up.** The audit's mutation
popped the auxiliary row from the grid *after* `_prove_assignment` had
validated it — a state a parse failure cannot produce. A row that fails to
parse leaves the columns short of their printed totals, no assignment
ties, and the build refuses (verified: removing the row yields "0
sparse-row assignments tie"). A row the table omits entirely is caught by
Gate 1. The coupling is now pinned by a test, because it is not obvious
from the strip code.

**What the strip does NOT verify is now stated.** The three stripped lines
are UC's own and their values are proven; the remainder shown as "core" is
**not a figure UC publishes** — it is the Ledger's arithmetic residual and
inherits any error in the three lines subtracted from it. `meta.strip`
says so.

**A second defect, and it was blocking the first.** `fetch_uc_data` and
`fetch_ccc_data` both assigned `prev` inside `build()` and used it in
`main()` — a different scope — so **every `--write` raised NameError**
after writing the payload but before recording anything. Neither layer's
change record had ever been written by a real refresh.

That is why the CCC parser fix of 2026-07-21 never reached the published
file: it was verified in a dry run, and `--write` crashed. **A published
figure changes now.** Statewide funded FTES moves from **1,100,664.62** —
the pipeline's own sum of the 72 district pages — to **1,100,664.61**, the
Chancellor's Office's printed control. Recorded as our own correction, one
event. Nothing else moved: all 72 districts and every Table VI figure are
unchanged.

**Digest coverage, measured:** `verify_digest.py` discovers its file list
from the payloads; **12 of 12** files carrying a digest verify.

**Assertions.** 2075 → 2099 (+24).

## 2026-07-21 — Silence is not a check, and disk state is not an input

The last three defects from the vacuous-gate audit.

**1. The state program gate skipped itself.** `if depth["programs"]:` wrapped
a hard gate, so a department arriving with no program lines simply passed.
"No programs" was ambiguous between "DOF publishes none here" and "we did
not check", and the second reading is the dangerous one.

Two departments legitimately have no program structure, and both are now
DECLARED with a reason: **9860** Capital Outlay Planning and Studies, a bare
appropriation at $1-2M; and **9889** the Public School System Stabilization
Account, a reserve DOF publishes as deposits and withdrawals. Any other
department that moves money with no program lines now stops the build.

The declaration is asserted to be EARNED — every declared code must actually
occur, so it is a record rather than a blanket exemption.

**Two measurement errors of my own, both caught by the work itself.** I first
declared only 9860, because I scanned the cache summing SIGNED fund values —
and 9889's deposits and withdrawals net to exactly zero while moving up to
**$5.2B** in a single year. The gate now tests absolute movement. And I first
put the gate in `fetch_year`, which runs only on `--refresh`: a gate that
fires only when the cache is cold is a gate most builds skip. It now lives in
`build_payload`, which runs on every build.

**2. Schedule 9's Gate 2 conflated two outcomes.** `if rows and <reconciles>`
made "parsed nothing" — our defect — indistinguishable from "parsed rows that
do not reconcile", a property of DOF's document. They are separated:
`deptDetailUnparsed` and `deptDetailUnreconciled` are recorded distinctly, and
parsing nothing in ANY group now fails outright.

Re-running every actuals year: all seven report **unreconciled**, none
unparsed. So HHS and General Government are withheld because DOF's own
department rows do not reconcile to their group totals — not because our
extraction failed. Their group totals are gated by Gate 1 throughout.

**No published claim overstates this.** `meta.actuals.basis` claims
reconciliation against Schedule 6 *statewide* control totals, which is Gate 1
and is true; nothing claims department detail is reconciled where it was
withheld.

**3. The build window is the requested years, not the disk.** `build_payload`
consumed every FY file in the cache, so a checkout with `DEFAULT_YEARS = 6`
silently built nine years because another branch had left three caches behind.
The build now takes exactly the requested window, refuses if a requested year
is missing, and reports any cached year it ignores. Verified: an extra cache
file no longer changes the output, and `--years 2023-24 2024-25 2025-26`
builds exactly three years and reports six ignored.

**Also fixed:** a coverage declaration was re-applied on every build, so
running the pipeline twice in one day declared the same extension twice. It is
a one-time fact and is now recorded once.

**No figure moved.** 14 `programsNone` declarations were added; every figure
in all nine years is unchanged. Digest coverage measured: 12 discovered, 12
verified.

**Assertions.** 2099 → 2118 (+19).

## 2026-07-21 — V15 corrected: CSU is unreachable, CCC is deeper than claimed

Before building on docs/V15_HISTORICAL_FINDING.md, each layer's
recommendation was re-probed by running the real parser against the real
source. Two of the finding's claims were wrong. They are corrected in the
document itself rather than left for the next reader.

**CSU cannot be extended at all** — the finding recommended +5 years. That
rested on a report that older CSU PDFs carry a uniform −29 character shift,
"readable once known". It could not be verified, for a reason that
supersedes it: `calstate.edu` returns **HTTP 403** with an Imperva
interstitial to every scripted request, and `extract_from_pdfs()` is a
documented stub that returns nothing. The control total for every proposed
year is **uncomputable, not merely unreconciled**. CSU stays at its single
gated year. The FY2012-13 structural floor is not refuted — it is
unreachable, which is stronger.

**CCC is deeper than the finding claimed.** It stated FY2015-16 through
FY2017-18 were "unretrievable and must be shown as absent". All three fetch
real, year-labelled data and reconcile at whole-dollar resolution with a
residual of exactly $0, using the shipped parser unchanged. The in-scope
Table VI core is **FY2009-10 through FY2022-23 — 14 years, every one
gate-verified at $0**.

One new limit found in the same pass: **FY2018-19 apportionment has no
published control** — "Funded FTES" appears nowhere in that year's R1
document. That year ships its Table VI core with the apportionment fields
absent, never interpolated.

Both errors ran in the direction of the agent that produced them: the CSU
report was optimistic about a document it never held, the CCC report
pessimistic about documents it failed to fetch once. The finding's own
evidence standard — VERIFIED means *I fetched it* — was right; it was
applied unevenly.

## 2026-07-21 — K-12 groundwork: CDE's vocabulary, declared per vintage

Prerequisite for the K-12 historical extension, landed on its own because
it closes a live silent-failure mode whether or not the extension follows.

CDE renames sheets and columns between vintages. **FY2018-19** names its
Current Expense sheet `District (by CDS)` and heads its first two columns
`CO Code` / `District Code`, where FY2017-18 and FY2019-20 both use `CDS` /
`CO` / `CDS`. The shipped detector tested `str(row[0]).strip() == "CO"`
exactly, so on that vintage the header was never found, the published
control table stayed **empty**, and every downstream gate iterated nothing
— passing on zero districts.

The fix is a **declaration, not a looser detector**. A detector widened to
accept several spellings would also accept a vintage nobody has read, which
is the same failure with more steps. Every entry was read off the real
published file:

| FY | sheet | county col | district col | name col |
|---|---|---|---|---|
| 2016-17, 2017-18 | `CDS` | CO | CDS | DISTRICT |
| **2018-19** | **`District (by CDS)`** | **CO Code** | **District Code** | **District** |
| 2019-20 | `CDS` | CO | CDS | DISTRICT |
| 2020-21, 2021-22 | `District` | CO | CDS | DISTRICT |
| 2022-23 → | `District` | CO | CDS | District |

SACS changes two names at the FY2021-22 / FY2022-23 boundary: the charter
school column (`SchoolID` → `SchoolCode`) and the county-office type
spelling (`CO OFFICE` → `County Office of Education`). The older side was
verified by inspecting all six databases; the current side is proven by the
running gate, which reads `SchoolCode` and counts 58 county offices.

**An undeclared year now refuses the build** rather than being parsed on
assumption.

Behaviour-preserving: the three loaded years rebuild with identical
districts, county offices and charters, and the same 934 / 933 / 932
gate counts.

**Assertions.** 2118 → 2131 (+13).

## 2026-07-21 — CCC: absence marks absence

Four live defects in what ships today. No figure moved: every Current
Expense, instructional-salary and 50-Percent-Law value is unchanged, and
the statewide totals are identical.

**1. A missing fact was published as a negative.** A district whose
apportionment record is absent shipped `basicAid: false` — the claim that
its property-tax position had been checked against the SCFF schedule and
it is not community-supported. It had not been checked. The four sibling
fields (`fundedFtes`, `stateGf`, `perFtes`, `noncreditShare`) already used
`null`; `basicAid` was the outlier, and `noncreditHeavy`, derived as
`bool(x and x >= t)`, collapsed a `None` share to `False` the same way.
Calbright is the live case: it is not apportionment-funded at all, so the
fact does not exist for it.

**2. Two fallbacks removed.** `noncreditShare` fell back to `0.0` when the
denominator was missing — "we measured zero noncredit" from a division we
could not do. And the statewide `fundedFtes` / `stateGf` fell back to the
pipeline's **own sum** when the published control was missing. That is the
surviving mechanism behind the figure corrected on 2026-07-21: it produced
1,100,664.62 where the Chancellor's Office prints 1,100,664.61. The parser
fix made the control findable; the fallback that masked its absence was
still there.

**3. The page told every district Calbright's story.** `ccc.html` carried
one hardcoded sentence — "Calbright is the state's online community
college…" — rendered for *any* district whose apportionment was missing.
On any other district that is a fabricated explanation, worse than a
blank. The reason now travels **with the record**, declared per district,
and a district whose absence has no declared reason fails the build rather
than borrowing another's.

**4. The CSV exported the same claim.** `community_supported` wrote the
literal `no` where the fact is unknown. Unknown now exports as an empty
cell, and the header states that an empty flag cell means *not known* — it
does not mean no. The per-FTES bar also drew an unknown at zero width
beside a cell reading "—"; unknowns are now excluded from the scale and
draw no bar.

**Two flaws in the change record itself, found while recording this.** A
correction was keyed on `(layer, built)`, so a rebuild on the same day
re-attached its note to a second, empty batch — which had already happened
to the funded-FTES correction. And two corrections on one layer on one day
could not be told apart. Corrections now carry a stable `id`, are applied
once, and a batch written before ids existed is recognised by the note it
already carries rather than by stamping an id onto a dated record.

**Assertions.** 2131 → 2161 (+30).
