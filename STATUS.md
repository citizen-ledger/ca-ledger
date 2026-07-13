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

## Update cadence

State: one new fiscal year per annual Budget Act (late June). Run
`python3 pipeline/fetch_state_data.py` after enactment; update the
population constant annually from DOF E-4.

Cities: one new fiscal year per SCO filing cycle (reports for a fiscal
year appear on By the Numbers roughly a year later). Run
`python3 pipeline/fetch_city_data.py --write`; extend `SOURCE_YEARS`
when a new year appears.
