# V10a finding — school object × resource cross-tab: "what did this funding buy?"

*Investigation date: 2026-07-18. Empirical base: the FY 2024-25 SACS
unaudited-actuals general ledger the pipeline already downloads,
cross-tabulated against the object totals (V8) and resource totals
(V9) the site already gates. Every figure computed this week; nothing
estimated unless labeled.*

**Recommendation: (b) SHIP as a reduced, on-demand form — the object
breakdown of an already-named funding source, one level deeper in the
existing V9 view.** The full object × resource matrix reconciles
perfectly but is payload-prohibitive and unreadable. The reduced form
answers the actual question ("Title I money — what did it buy?"),
costs +5.3%, and inherits both gates by construction. The full grid is
refused, not because it fails to tie out — it ties out to the cent on
both margins — but because it is a dense grid no one can read and a
file no phone should carry.

---

## 1. THE GATE — the whole question — passes to the cent, on BOTH margins

The object × resource cross-tab must tie out to *both* the object
totals (V8) and the resource totals (V9), and therefore to Current
Expense. Tested on every one of the 932 published districts:

| Check | Result |
|---|---|
| Cross-tab sums to each resource total (margin 1) | every district, exact |
| Cross-tab sums to each object-family total (margin 2) | every district, exact |
| Cross-tab total == published Current Expense | **0 districts fail; worst residual $0.0000** |

LAUSD: the cross-tab sums to **$10,877,387,458.05** — the published
figure — and its resource margins equal V9's resource totals and its
object margins equal V8's object totals, all to the cent. This is
mechanical: the cross-tab is the same ledger rows keyed by two fields
at once, so it cannot disagree with either one-dimensional rollup. The
reconciliation question is answered as strongly as it can be. What
decides the recommendation is not the gate — it is payload and
legibility.

## 2. Cell count and payload — the full matrix is prohibitive

Most intersections are empty only for small districts; **large
districts are dense.** Non-zero cells per district:

| | min | median | 90th pct | LAUSD |
|---|---|---|---|---|
| all non-zero | 21 | 91 | 173 | 386 |
| ≥ $1,000 | — | 83 | 161 | 373 |
| ≥ $1,000,000 | — | 8 | — | 139 |

LAUSD fills **386 of 456** possible resource×object-family cells —
density 0.85, not sparse. A small district (Ravendale-Termo, 1.98 ADA)
has 25 cells at density 0.42.

Full-matrix payload, three years, whole dollars:

| Floor | Cells / year | Added size (3 yr) | vs 4.64 MB file |
|---|---|---|---|
| ≥ $1,000 | 86,187 | ~5.5 MB | **+119% — prohibitive** |
| ≥ $1,000,000 | 10,336 | ~0.72 MB | +15.5%, but the median district keeps only 8 cells — the detail vanishes exactly where a small district's story lives |

There is no floor that is both affordable and informative for the full
grid: cheap floors gut small districts; complete floors triple the
file. The full cross-tab does not ship.

## 3. Legibility — the reduced form is the readable, affordable answer

A full grid is unreadable; a *selected funding source → its objects*
drill is both legible and cheap. Reading LAUSD's FY 2024-25 ledger:

- **Title I (resource 3010, $434.9M) bought:** certificated salaries
  $222.2M · benefits $110.5M · services $33.8M · classified salaries
  $30.7M · other outgo $23.7M · books & supplies $14.0M. That is the
  answer to "what did Title I buy" — mostly teachers and their
  benefits.
- **Special Education (6500, $1.625B) bought:** certificated salaries
  $501.4M · benefits $479.9M · classified salaries $319.8M · services
  $238.5M · other outgo $82.9M · supplies $2.5M.
- **On-Behalf Pension (7690, $368.1M):** benefits, and only benefits —
  a single cell (object 3101). This matters for the trap (§4).

Six to seven object families per source — a short, readable list,
exactly the object-family breakdown V8 already shows for functions.

**Reduced-form payload:** shipping the object split only for the
resources V9 already names (≥ $1M, ~7.1 per district) and only for the
latest year (the V9 discipline), as a fixed-order object-family array:

| Form | Cells / yr | Added size | vs 4.64 MB |
|---|---|---|---|
| Named-resource object splits, latest year, compact array | ~27,900 (30/district) | ~0.24 MB | **+5.3%** |

Under the standing <10% discipline, and it drills exactly the sources
a reader can already see. Older years keep V9's group totals; the
object-split drill, like V9's named rows, is a current-year feature.

## 4. Traps — the same four, and one new subtlety

- **STRS on-behalf stays labeled inside the cross-tab.** Resource 7690
  intersects exactly one object family — benefits (object 3101,
  $368.1M at LAUSD). Because it is a single clean cell, the on-behalf
  label carries through trivially: the object split of resource 7690
  is "$368.1M benefits — paid by the State on the district's behalf,
  not district spending." No new scoping risk; the V9 handling extends
  unchanged.
- **Indirect-cost transfers.** Objects 7300-7399 (in the "other outgo"
  family within the gated scope) still net across resources — a
  categorical's object split includes its overhead transfer, and
  unrestricted's is shown net. The V9 indirect note covers this; the
  object view makes the transfer visible as an "other outgo" line,
  which is more honest, not less.
- **Unrestricted is not local.** Unchanged. The object split of the
  unrestricted resources (LCFF, EPA, Lottery) shows what that
  state-source money bought by object; the group is still labeled
  Unrestricted, never local.
- **No cell may imply an unsupported breakout.** The object split of
  the unrestricted-LCFF resource shows what LCFF bought *by object*
  (salaries, benefits, …) — which the ledger *does* support — but it
  still cannot split LCFF base vs supplemental/concentration, which
  the ledger does not. The reduced form must not let a reader mistake
  "LCFF by object" for "LCFF base vs supplemental." The V9 LCFF note
  stands and should be repeated where LCFF's object split is shown.
- **New subtlety — negative cells.** Cost-transfer objects produce
  small negative cells (e.g. an indirect-cost credit in the
  unrestricted resource's "other outgo"). They are legitimate and
  already handled by the object view's negative-rendering; the reduced
  form inherits it.

## 5. Recommendation

**(b) SHIP as a reduced, on-demand form.** Concretely, if built:

- One level deeper in the existing V9 funding-source view: expanding a
  named resource reveals its object-family split (the same 6-7
  families V8 uses), latest year only, each summing to that resource's
  total to the cent.
- Both gates enforced in the pipeline, no write on failure: each named
  resource's object split sums to that resource's V9 total *and* the
  object families sum across resources to the V8 object totals — the
  two margins that already gate, now required to hold at their
  intersection.
- The four V9 face statements carry through; the on-behalf label
  attaches to resource 7690's single benefits cell; the LCFF-limit
  note repeats where LCFF's object split appears.
- Payload ~+5.3% (0.24 MB), phone-legible (a short object list per
  expanded source, not a grid).

**Do NOT ship the full object × resource matrix** (option a): it
reconciles perfectly but is +119% at a useful floor and is a dense
grid — for LAUSD, 386 cells — that no reader can parse. The refusal is
on legibility and payload, not fidelity; the fidelity is exact.

Option (c) — don't ship at all — is too conservative: the reduced form
is cheap, legible, cent-exact on both margins, and answers a question
readers genuinely ask ("what did this funding pay for?") that neither
existing drill answers alone. It is worth shipping in the reduced
form; it is not worth shipping as a grid.

---

*Sources: sacs2425.mdb UserGL + Resource tables and currentexpense2425.xlsx
(CDE Annual Financial Data); reconciled against the shipped V8 object
families and V9 resource totals in school-data.js. Analysis script and
raw results preserved in the session scratchpad (v10a_crosstab.py).*
