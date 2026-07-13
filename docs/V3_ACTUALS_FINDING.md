# V3 finding: can actual spending be published beside enacted appropriations?

_Investigated 2026-07-13. No UI was built; this document is the deliverable._

## Recommendation, up front

**(a) SHIP** — one source qualifies: the Department of Finance's own
prior-year **actual** expenditures, published on the identical
Budgetary-Legal basis in every budget publication (Schedule 9,
"Comparative Statement of Expenditures", and the same eBudget API that
already feeds V1). It is complete (reconciles to DOF's statewide
historical total to the million), department-level, and — decisively —
it is the state's *own* side-by-side presentation: every California
budget document already prints "Actual / Estimated / Enacted" in
adjacent columns on one accounting basis. V3 would be reproducing the
state's own comparative statement, not inventing a comparison.

Every other actuals source fails on basis, coverage, or access. The
required caveats are listed at the end; the difference column must be
explained as *what changed between enactment and year-end* (mid-year
legislation, re-appropriations, carryover timing, reversions) — never
as error, waste, or overrun.

---

## 1. Sources evaluated

### A. Open FI$Cal (open.fiscal.ca.gov) — REJECTED (again, now with a control)

Monthly transaction files from the state's accounting system.
Re-examined using the aggregates cached from the earlier V1
investigation (pipeline/cache/FY*.json, FY 2023-24 and 2024-25 fully
aggregated from ~44M transaction rows).

- **Coverage:** ~79% of budgetary expenditures by its own About page,
  and the gap is structural: departments that run their own accounting
  systems ("deferred": CDCR, Caltrans, DOJ, Department of Water
  Resources; "exempt": UC, CalPERS/CalSTRS) are absent entirely.
- **Granularity:** transaction level (best in class) — where it covers.
- **Basis:** modified accrual for FI$Cal departments, cash for the
  rest. Not Budgetary-Legal; its own FAQ says totals "will not match"
  the Governor's Budget figures.
- **Lag:** monthly, ≥60 days.
- **Access:** excellent (CSV on Azure blob storage).
- **Verdict:** the FY 2023-24 test below shows what publishing it would
  do: CDCR at −97% "under budget" — a coverage artifact indistinguishable,
  on the page, from a real number.

### B. State Controller's Office expenditure reporting — NOT COMPARABLE

- **Monthly Statement of General Fund Cash Receipts and
  Disbursements:** cash basis, General Fund only, monthly PDFs/Excel.
  High frequency, wrong basis, no special/bond funds, no department
  detail matching the budget structure.
- **"By the Numbers" (bythenumbers.sco.ca.gov):** local governments
  only (it is our V2 source); it has no state-department data.
- **Budgetary/Legal Basis Annual Report (BLBAR):** historically the
  canonical year-end actuals on exactly our basis, published by the
  SCO. Since the June 30, 2020 reporting year the SCO's budgetary-legal
  presentation is folded into/published alongside the ACFR era
  documents; either way it is a large PDF with fund-level statements,
  no API, and a lag around a year or more. Right basis, unusable
  access, and no department-level table matching the agency structure.
  (DOF's Schedule 9 figures are the same budgetary-legal actuals,
  already organized by budget org code.)

### C. California ACFR (SCO) — NOT COMPARABLE

Audited, GAAP basis (modified accrual fund statements, full accrual
government-wide). Latest available covers FY ending June 30, 2025
(ACFR25web.pdf) — a lag under a year currently. Organized by *function*
and *fund type*, not by the budget's agency/department structure; PDF
only. A GAAP actual next to a Budgetary-Legal enacted figure is exactly
the not-like-for-like subtraction this investigation was told to guard
against: GAAP recognizes on accrual events, budgetary-legal on
appropriation charges (including encumbrances), and the two produce
legitimately different totals for the same year. The ACFR's value is as
the audit anchor, not as a column in our table.

### D. DOF prior-year actuals (Schedule 9 / eBudget API) — QUALIFIES

Every DOF budget publication carries three years per line item:
**Actual** (prior year), Estimated (current year), Proposed/Enacted
(budget year). Verified empirically this session:

- The eBudget site's own UI labels the prior-year column
  `"Actual <year>*"` (verified in its JS bundle: `{data:"pyDols",
  label:"Actual<br>"+previousYear+"*"}`).
- The API we already use exposes it: `rwaCntl/support/{orgCd}` and
  `rwaCntl/capOutlay/{orgCd}` return `pyTotDols` per fund with the
  same G/S/B/F fund classes as our enacted figures.
- **Schedule 9** ("Comparative Statement of Expenditures", PDF, text-
  extractable, in every publication's BudgetSummary) publishes the
  complete department-level table: Actual / Estimated / Estimated ×
  (GF, Special, Selected Bond, Budget Total, Federal).
- **Internal consistency:** the eleven agency-group totals extracted
  from the 2025 Budget Act Schedule 9 for Actual 2023-24 sum to
  **$303.246B — matching Schedule 6's historical statewide total
  ($303,246M) to the million.**
- **Coverage:** complete — every budget org code, including every
  department Open FI$Cal zeroes out. CDCR actual 2023-24: $18.796B.
- **Basis:** Budgetary-Legal — *identical* to our enacted figures, from
  the same publisher, in the same org taxonomy.
- **Granularity:** department (org code) × fund class × character
  (state operations / local assistance / capital outlay).
- **Lag:** actuals for FY Y first appear in the January Y+1 Governor's
  Budget (~6.5 months after FY close; FY 2024-25 actuals are already
  published in the 2026-27 Governor's Budget) and are re-stated at the
  following June's enactment. January and June vintages matched exactly
  in the case tested (CDCR GF 2023-24: identical to the dollar).
  Minor later restatements are possible (Schedule 6's history is the
  canonical running series).
- **Access:** the same API V1 uses (per-department, machine-readable,
  ~96.8% of the statewide total via the web display's department lists
  — see the known gap below) plus the Schedule 9 PDF (100% complete,
  reliably text-parseable; agency totals verified this session).

## 2. The critical question — comparability

Our enacted figures are appropriations under the Budgetary-Legal basis
at Budget Act signing. The DOF prior-year actuals are expenditures
under the *same* basis, from the *same* source system, in the *same*
organizational taxonomy. The subtraction is therefore legitimate — and
it is not our editorial invention: **Schedule 9's explicit purpose is
this comparison**, and every printed budget shows the columns
side by side.

What the difference *means* still requires care. Enacted-at-signing vs
final actual differs because of:

1. **Mid-year legislation** — supplemental and deficiency
   appropriations, budget-solution reductions (2023-24 is a vivid
   example: the state cut mid-year as revenues fell).
2. **Re-appropriations and carryover** — multi-year capital authority
   is enacted once and spent across years (Transportation's pattern).
3. **Reversions** — authority that lapsed unspent.
4. **Continuously appropriated funds** moving with formula/caseload.

None of these is error or waste, and several agencies legitimately
spend *more* than the June enactment. The view must say this in plain
language. With that framing, the comparison is honest; without it, even
a basis-perfect subtraction would mislead.

One structural nuance: Schedule 9 groups K-12 and Higher Education as
one "Education" agency; our V1 splits them (the API's current web
mapping). For the actuals column, either combine our two education
agencies in the comparison view or allocate Schedule 9's education
departments to our split via their org codes (they are disjoint sets —
a lossless mapping by department, worth confirming in implementation).

## 3. Reconciliation test — FY 2023-24 (closed year)

Enacted = our data.js (2023 Budget Act, at signing). DOF actual =
Schedule 9 of the 2025 Budget Act publication. FI$Cal = the cached
aggregation of every published transaction, as the control. State funds
(GF + special + selected bond), billions.

| Agency | Enacted | DOF actual | Δ | Δ% | FI$Cal "actual" | Verdict on Δ |
|---|---|---|---|---|---|---|
| Health & Human Services | $113.646B | $110.570B | −$3.08B | −2.7% | $111.39B | Real variance (caseload, mid-year solutions). FI$Cal is coincidentally close here because DHCS/DSS run in FI$Cal. |
| Corrections & Rehabilitation | $18.543B | $18.796B | +$0.25B | +1.4% | $0.49B | Real, small overage (deficiency spending is routine for CDCR). The FI$Cal figure is a **coverage artifact** — CDCR does not use FI$Cal — and would have published as "−97%". |
| Education (K-12 + Higher Ed) | $103.881B | $93.361B | −$10.52B | −10.1% | $93.64B† | Real: the 2023-24 Prop 98 guarantee dropped with revenues and mid-year solutions cut school appropriations. |
| Transportation | $20.999B | $16.440B | −$4.56B | −21.7% | $5.10B | Real, dominated by capital timing: enacted authority spent across later years. FI$Cal again a coverage artifact (no Caltrans). |
| Government Operations | $4.234B | $4.643B | +$0.41B | +9.7% | $1.47B | Real overage (mid-year items); FI$Cal artifact. |
| **Statewide** | **$310.803B** | **$303.246B** | **−$7.56B** | **−2.4%** | ~$244.6B | Real net variance for a year of budget solutions; the FI$Cal statewide gap (−21%) is mostly missing departments. |

† FI$Cal's education number appearing "right" is luck: CSU flows in via
SCO interface while UC is absent, roughly offsetting the Prop 98 drop.
An artifact that *happens* to land near the truth is still an artifact.

The pattern is unambiguous: DOF-actual deltas are explainable,
directionally mixed, and match known fiscal history; FI$Cal deltas are
dominated by which departments happen to use the accounting system.

Known artifact in the *API access path* (not the source): the web
display's department lists sum to ~95-97% of agency totals (the same
M-3 gap our enacted view already documents — measured at 4.6% for
enacted 2023-24, 3.2% for the PY aggregation, e.g. CDCR's realignment
special funds are in Schedule 9 but not the web department list).
Schedule 9 itself has no such gap. Implementation should therefore
treat **Schedule 9 as the authoritative extraction** and use the API
columns as a per-department cross-check, or publish API-derived figures
only with per-agency coverage stated (which would demote this to
recommendation (b) — unnecessary, since Schedule 9 parses cleanly).

## 4. Recommendation

**(a) SHIP.**

- **Source:** DOF prior-year actual expenditures — Schedule 9 of each
  year's enacted-budget publication (ebudget.ca.gov), cross-checked
  against the eBudget API's `pyTotDols` and against Schedule 6's
  statewide total (which the extraction must reproduce exactly, as it
  did this session).
- **Basis:** Budgetary-Legal — identical to the enacted column. This is
  the only actuals source in California on our basis with department
  granularity and full coverage.
- **Availability/lag:** actuals for FY Y publish ~6.5 months after
  year end (January Governor's Budget) and are re-stated at the June
  enactment; actuals exist today for 2020-21 through 2024-25 — five of
  V1's six years (2025-26 actuals arrive January 2027).
- **Caveats that must appear on the face of the view:**
  1. "Actual" is as published by the Department of Finance in the
     following year's budget (Budgetary-Legal basis, unaudited by the
     Ledger; DOF may restate prior-year figures in later publications).
  2. The difference column reflects what changed between enactment and
     year end — mid-year legislation, re-appropriations and carryover
     of multi-year authority, and reversions. It is not a measure of
     error, efficiency, or waste, and actuals legitimately exceed
     enactment for some agencies. (Neutral ▲▼ direction only, per the
     house rules; both gross over and gross under always shown
     together, Change-view style.)
  3. Vintage line: which publication each actual column came from.
  4. Education grouping: if shown at Schedule 9's grouping, say so; if
     split to match V1, the department-level mapping must be stated.
- **Explicitly rejected:** Open FI$Cal (coverage artifacts masquerade
  as variance), ACFR (GAAP basis — not like-for-like; PDF; function-
  level), SCO cash statements (cash basis, GF-only).

### What would have changed the answer

If DOF did not publish prior-year actuals on the budgetary basis at
department level — or if they failed to reconcile to the statewide
historical series — no honest comparison would exist: FI$Cal would need
either full department onboarding (CDCR, Caltrans, DOJ, DWR, UC) or a
published crosswalk of what it omits per agency-year, and the ACFR
would need a budgetary-basis, budget-structure companion schedule with
machine access. "Don't ship" was a live option until Schedule 9's
agency totals reproduced Schedule 6 to the million.
