# The California Ledger — V1 (state level)

A nonpartisan, static, interactive record of California state spending.
No frameworks, no build step, no server. Open `index.html` in a browser
and it works — including offline.

## What's in the box

| File | What it is |
|---|---|
| `index.html` | The state-budget page on the Ledger design system: record surface with dollar ruler, proportional bar with drill-down, Allocation / Change / Trend views, unit switching, cite + saved views. Zero runtime dependencies. |
| `data.js` | The dataset the state view renders: six years of enacted state budgets (2020-21 through 2025-26), generated from official data. |
| `pipeline/fetch_state_data.py` | Regenerates `data.js` from the Department of Finance's eBudget API. Python 3, stdlib only. |
| `cities.html` | The V2 city view: city picker with search, governmental expenditures by function with per-resident figures, a separate enterprise-activities block, service-provision footnotes, and a 2-4 city side-by-side comparison. |
| `city-data.js` | The city dataset: all 482 reporting cities × 8 fiscal years (2016-17 through 2023-24) of reported actual revenues and expenditures, generated from official SCO data. |
| `pipeline/fetch_city_data.py` | Regenerates `city-data.js` from the SCO "By the Numbers" Socrata API. Refuses to write unless every city-year total reconciles against the SCO's own published totals. |
| `pipeline/verify_digest.py` | Recomputes each data file's SHA-256 integrity digest (also shown on both pages under RECORD INTEGRITY). |
| `pipeline/make_ca_outline.py` | Regenerates the California outline embedded in `cities.html` from the Census cartographic boundary file (public domain), with the projection constants the map's dots use. |
| `tests/run_tests.py` | Headless test suite — one command, 135 assertions on the real data. |
| `STATUS.md` | Data provenance: source, accounting basis, validation against published totals, and the history of how the source was chosen. |

## Run it

Double-click `index.html`, or:

```
cd ca-ledger
python3 -m http.server 8000     # then open http://localhost:8000
```

## Features

- **Appropriation bar with drill-down** — one proportional bar over a dollar ruler, grayscale ramp by size, ghost strip showing prior-year shares; click a segment or row to open that agency's departments.
- **Three views** — Allocation (sortable table with data-derived † method notes), Change (mirrored center-axis chart on a symmetric scale, gross decreases and increases always shown together), Trend (six-year columns plus per-agency small multiples).
- **Unit switching** — dollars, per resident, or % of total; every figure recomputes.
- **Federal funds toggle** — state funds only vs. state + federal pass-through.
- **Fund-source schedule** — General / Special / Bond / Federal.
- **Permalinks** — the full view state (year, view, unit, federal toggle, drill, sort, filter) lives in the URL hash; citations reproduce the exact view.
- **Cite + Download CSV** — a plain-text citation to the clipboard, and a CSV whose header names the source, basis, generation date, and permalink.
- **Saved views** — stored in localStorage on the reader's device only.
- **Record integrity** — each data file carries a SHA-256 digest, displayed on the page with instructions to verify it independently.
- **Map view (city page)** — a Search/Map toggle beside the search picker: California outline as plain inline SVG (no tile services, no libraries), one dot per city with area scaled to population, neutral regional zooms for the dense metros, keyboard-accessible dots, and selection identical to the search picker. Dots are uniform ink — the map shows where, never how much.
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

One command, 135 assertions against the real data files: V1 and V2
rendering on the Ledger design system, drill-down and view/unit
controls, permalink hash round-trips, CSV export contents, citation
output, Change-view arithmetic, a banned-adjective scan, neutrality
checks (direction always in ink, never judgment colors), the corrected
city accounting labels (governmental activities — never "general fund
only"), the city comparability footnotes, the enterprise-fund block,
and the RECORD INTEGRITY digests (verified live with
`pipeline/verify_digest.py`). The suite serves the repo under a
`/ca-ledger/` subpath (the GitHub Pages layout), so it also proves
permalinks and citations emit the served public URL. Requires Python
3.9+, `pip install playwright`, and system Chrome (or `playwright
install chromium`).

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
