# The California Ledger — V1 (state level)

A nonpartisan, static, interactive record of California state spending.
No frameworks, no build step, no server. Open `index.html` in a browser
and it works — including offline.

## What's in the box

| File | What it is |
|---|---|
| `index.html` | The state-budget site: layout, styles, all interactivity, hand-rolled SVG charts. Zero runtime dependencies. |
| `data.js` | The dataset the state view renders: six years of enacted state budgets (2020-21 through 2025-26), generated from official data. |
| `pipeline/fetch_state_data.py` | Regenerates `data.js` from the Department of Finance's eBudget API. Python 3, stdlib only. |
| `cities.html` | The V2 city view (preview): city picker with search, per-function expenditure bar, per-resident figures, and a 2-4 city side-by-side comparison. Runs on clearly labeled sample data. |
| `city-data.js` | SAMPLE dataset for the city view — illustrative figures in a schema modeled on the State Controller's city annual financial reports. Do not cite. |
| `pipeline/fetch_city_data.py` | Will regenerate `city-data.js` from the SCO "By the Numbers" Socrata API. Endpoints unverified until first run from an unrestricted network; fails loudly and leaves the sample untouched otherwise. |
| `STATUS.md` | Data provenance: source, accounting basis, validation against published totals, and the history of how the source was chosen. |

## Run it

Double-click `index.html`, or:

```
cd ca-ledger
python3 -m http.server 8000     # then open http://localhost:8000
```

## Features

- **Appropriation Bar** — total spending as one proportional bar; click any segment (or table row, or legend chip) to drill into that agency's departments and fund mix.
- **Federal funds toggle** — state funds only vs. state + federal pass-through (Medi-Cal, unemployment insurance, etc.). Every figure on the page recomputes.
- **Fiscal year selector** with year-over-year change and per-resident figures.
- **Fund-source breakdown** — General / Special / Bond / Federal.
- **Six-year trend chart.**
- **Change from the prior year** — per-agency year-over-year change in dollars and percent, sortable, increases and decreases always shown together in one table.
- **Sortable, filterable full table** with a totals row.
- **Permalinks** — the full view state (fiscal year, federal toggle, selected agency, table sort, filter) lives in the URL hash, so any view can be shared and cited; the page restores it on load.
- **Download this data** — a client-side CSV of the current table view, with a comment header naming the source dataset, accounting basis, and generation date; the raw `data.js` is linked next to it.
- **Cite** — in the agency detail panel, copies a plain-text citation (figure, agency, fiscal year, source, accounting basis, permalink, access date) to the clipboard.
- **Methodology section** — what the figures are, what they are not, exact source, update cadence, and known caveats, linked from the top banner and the footer.
- Responsive to mobile, keyboard-navigable, respects reduced-motion.

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

## Neutrality choices, on purpose

- No adjectives attached to numbers. No "only," no "ballooning."
- Every view shows shares and per-resident figures so scale is visible
  without editorializing.
- Federal pass-through is a user-controlled toggle, not an editorial
  decision baked into the total.
- Sources, method, and accounting basis are stated on the page itself.

## V2 (cities) — preview shipped, sample data

`cities.html` is live as a preview on clearly labeled sample data
(yellow banner, same pattern V1 used before real data loaded): a
searchable city picker, a per-function expenditure bar with
per-resident figures, and the centerpiece — a symmetric 2-4 city
comparison of per-resident spending by function, where every city gets
the same treatment. Permalinks, CSV export, and Cite work on the city
views; sample status is stamped into CSV headers and citations.

The production source is the State Controller's Office: all 480+
California cities file standardized annual financial reports,
published with a public API at bythenumbers.sco.ca.gov (Socrata) —
reported actual revenues and expenditures, one fiscal year per annual
filing cycle. `pipeline/fetch_city_data.py` targets that API; its
endpoints are unverified until first run from a network that can reach
sco.ca.gov (this environment cannot), and it will not overwrite the
sample until a fetch fully validates.
