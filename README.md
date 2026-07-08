# The California Ledger — V1 (state level)

A nonpartisan, static, interactive record of California state spending.
No frameworks, no build step, no server. Open `index.html` in a browser
and it works — including offline.

## What's in the box

| File | What it is |
|---|---|
| `index.html` | The entire site: layout, styles, all interactivity, hand-rolled SVG charts. Zero runtime dependencies. |
| `data.js` | The dataset the site renders. **Currently sample data, clearly labeled in the UI.** |
| `pipeline/fetch_state_data.py` | Rewrites `data.js` from official data (Open FiscalCal via data.ca.gov). Python 3, stdlib only. |

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
- **Sortable, filterable full table** with a totals row.
- Responsive to mobile, keyboard-navigable, respects reduced-motion.

## Loading real data (do this once)

The pipeline was written without network access to ca.gov, so two
constants need one-time verification — this is stated plainly at the
top of the script:

1. Find the Open FiscalCal expenditure dataset on https://data.ca.gov
   and copy its datastore **resource id** into `RESOURCE_ID`.
2. Run `python3 pipeline/fetch_state_data.py --inspect` to see the real
   column names; adjust `COLUMNS` and `FUND_MAP` if they differ.
3. Run `python3 pipeline/fetch_state_data.py`. It rewrites `data.js`,
   the yellow "sample data" banner disappears automatically, and the
   footer cites the live source and generation date.

For freshness, run the script on a schedule (cron, or a GitHub Action
committing the regenerated `data.js`). State expenditure data updates
roughly monthly; enacted budgets annually.

## Neutrality choices, on purpose

- No adjectives attached to numbers. No "only," no "ballooning."
- Every view shows shares and per-resident figures so scale is visible
  without editorializing.
- Federal pass-through is a user-controlled toggle, not an editorial
  decision baked into the total.
- Sources and method are on the page itself.

## V2 (cities) — the plan

The State Controller's Office requires all 480+ California cities to
file standardized annual financial reports, published with a public
API at bythenumbers.sco.ca.gov (Socrata). That is the one uniform
source for city-level revenues and expenditures. V2 adds a second
pipeline script against that API, a city picker, and per-capita
comparisons between cities — same schema pattern as `data.js`.
