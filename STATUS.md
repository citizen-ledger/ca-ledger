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

Most recent fully published Summary Charts year (2024-25 Budget Act):

| | data.js | Published Summary Charts¹ | Difference |
|---|---|---|---|
| General Fund | $211.504B | $211,504M | 0.000% |
| Special Funds | $83.985B | $83,985M | 0.000% |
| Bond Funds | $2.373B | $2,373M | 0.000% |
| **Total state funds** | **$297.862B** | **$297,862M** | **0.000%** |

¹ "2024-25 Total State Expenditures by Agency", California State Budget
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

## Update cadence

One new fiscal year per annual Budget Act (late June). Run
`python3 pipeline/fetch_state_data.py` after enactment; update the
population constant annually from DOF E-4.
