# V18b — UC extension built: five years ship, FY2019-20 held

**Status: built.** Five fiscal years (FY2020-21 … FY2024-25) ship, each
gated exact-to-the-thousand; FY2019-20 is held. Measured 2026-07-23
against the six Annual Financial Reports, under **pypdf** (the library
the pipeline actually extracts with — #72's feasibility used pdfplumber,
and every conclusion was re-established under pypdf before building).

This records what the build measured, and the two places where
measurement contradicted the plan's premises.

---

## What shipped

| FY | ships | DOE form | Gate 1 residual |
|---|---|---|---|
| 2024-25 | ✓ | systemwide | 0 |
| 2023-24 | ✓ | systemwide | 0 |
| 2022-23 | ✓ | systemwide | 0 |
| 2021-22 | ✓ | systemwide | 0 |
| 2020-21 | ✓ | excluded (DOE added back) | 0 |
| 2019-20 | **held** | excluded | **−351** |

Every shipped year passes, per year: the reconciliation gate at thousand
resolution, the column-sum check (unique at ±1K **and** still unique at
±10K), the sparse-row assignment proof, the printed-header order gate,
the shape gate, and the empty-gate guard.

## The per-vintage declarations (declared, never sniffed)

All in `VINTAGE` in `pipeline/fetch_uc_data.py`:

- **Anchors.** The four older AFRs capitalise the section headers
  (`CAMPUS FINANCIAL FACTS`, `OPERATING EXPENSES BY FUNCTION`); the two
  newest use mixed case. Declared per vintage — not a case-insensitive
  match, which is the widened detector this repo has twice refused.
- **Rows.** `Impairment of capital assets` (FY2019-20/FY2020-21);
  `Other and Impairment of capital assets` combined into one line
  (FY2021-22); `DOE Labs Expenses` relabelled (FY2022-23). The combined
  row forces **longest-label-first** matching — it begins with `Other`,
  itself a declared row, so shortest-first would bind the combined
  quantity to `Other`, a wrong number that parses cleanly. Its own test:
  `test_uc_longest_label_first`.
- **DOE form.** `doeForm` per vintage: `systemwide` (DOE in the campus
  table's Systemwide cell) or `excluded` (DOE absent, added back from the
  audited statement's own DOE operating-expense line). Never inferred
  from whether a row parsed. Test: `test_uc_doe_treatment_declared`.
- **Audit language.** `fullOtherInfo` per vintage — see below.

## Finding 1 — FY2019-20 does not reconcile (held)

The older-vintage identity is *campuses + Systemwide + (DOE added back
from the statement) = audited total*. It ties **exactly** for FY2020-21:

```
38,487,120 + 1,694,402 + 1,042,258 = 41,223,780 = audited   (residual 0)
```

Under the identical model FY2019-20 misses:

```
38,753,728 + 3,575,768 + 1,075,559 = 43,405,055  vs  43,405,406   (−351)
```

Run down (the reviewer asked for the dig before deciding):

- The campus sum is parse-clean — reproduced by hand, cell by cell.
- The campus table carries UC's own printed footnote *"Excludes DOE
  laboratories"* on both pages; adding the audited DOE operating-expense
  line (1,075,559, the current-year column) is the correct reconciliation
  and closes every other year.
- The statement classifies expenses by **natural** category
  (Salaries, Pension, …); the campus table by **function** (Instruction,
  Research, …). Both must total the same audited figure; FY2019-20's
  unaudited functional presentation is 351K short of the audited natural
  total even after DOE. No second exclusion exists (the only footnote is
  DOE), and the implied figure 1,075,910 appears nowhere in the document.

So the earliest year's *unaudited* Campus Facts in Brief simply does not
reconcile to the audited total at the source's own resolution.
**Held, not shipped** — consistent with "a year that can't be gated
doesn't ship; do not relax the gate." It is not silently dropped: it is
encoded not-published (`held` in the payload, with its measured
residual), rendered as a distinct held point on the trend, and the build
**re-measures the residual every run** and fails loudly if it ever
enters the reconciling band, so a future restatement reaches a human
rather than auto-shipping (`test_uc_held_year`).

## Finding 2 — FY2022-23's per-campus core IS derivable (ships)

The plan called for FY2022-23's per-campus core to be **not-published**,
on the premise that DOE being "systemwide-only, not per-campus" made it
underivable. Measured under pypdf, that premise does not hold:

- DOE is systemwide-only in the campus table for **FY2021-22, FY2023-24
  and FY2024-25 too** — FY2022-23 is not special.
- Per-campus core never touches DOE: it is `total − medical − auxiliary`,
  and medical (5 campuses) and auxiliary (10 campuses) are present
  per-campus in **every** year, FY2022-23 included.
- FY2023-24 and FY2024-25 already ship per-campus core under identical
  structure.

Marking FY2022-23 not-published would have published a false "we can't
compute this" about a figure that computes identically to two shipping
years — the exact absent-fact defect the machinery exists to prevent. On
the reviewer's decision, FY2022-23 ships per-campus core normally.

The genuine not-published instance in the shipped payload is therefore
the **held FY2019-20** itself, rendered as a held point — which is what
the not-published rendering is now verified against (real payload, not a
synthetic one).

## The core series is comparable; the assembly is not uniform

Because DOE is stripped either way, the systemwide core is comparably
defined across all five years. What differs is *how* the source table is
assembled: FY2020-21 excludes DOE (added back from the statement);
FY2021-22 on carry it in the Systemwide column. That is a comparability
fact, stated **where the five-year core line crosses it** — a break
marker and note on the trend, and a restatement on each year's record —
without characterising it.

## The ±1K tolerance, and why it is not a relaxation

UC prints in thousands and rounds each figure independently, so a column
total need not equal the sum of its rounded components. FY2020-21's San
Diego column is short by exactly 1 thousand. The column-sum proof
therefore ties to ±1K — but the tolerance is proven not to be what makes
the assignment unique: at **±10K, ten times wider, every year still
admits exactly one assignment**, and the pipeline asserts that on every
run (`_prove_assignment`'s self-guard) so a genuinely ambiguous future
vintage fails rather than being absorbed (`test_uc_column_sum_self_guard`).

## Audit status, per vintage (not carried backward)

Measured: FY2021-22 onward carry the full auditor "other information"
language ("read the other information and consider whether a material
inconsistency exists"); **FY2020-21 does not** — its report has "do not
express an opinion" but predates that standard. So the full quotation is
**not carried back** onto FY2020-21; the page shows a reduced statement
there (`fullOtherInfo` per vintage; `auditFullOtherInfo` on each year).

## Shape, coverage, deflator

- **Multi-year shape** mirrors CCC/K-12: top-level `years`, `systemwide`
  keyed by FY, each campus carrying a `years` map. `revisions.flatten`
  normalises the legacy single-year payload to the same FY-first keys, so
  the FY2024-25 re-addressing moves **no value** (verified: zero diff for
  FY2024-25) and only the four added years enter the record — collapsed
  to one **COVERAGE** fact (911 figures entered, no per-figure noise). A
  tampered FY2024-25 value still shows as a real event, so a restatement
  cannot hide inside the extension.
- **Deflator** covers the whole window as actuals (base FY2024-25); the
  page's nominal/real toggle mirrors schools.html
  (`test_uc_deflator_window`).

## Reproducibility

All six AFR URLs and all five UCOP FTE URLs resolve to the cached bytes
(size + `application/pdf` + `%PDF-` magic verified), so
`fetch_uc_data.py --refresh` reproduces from the live public sources.
Existence is tested on content-type and magic bytes, never on status.

## What each claim rested on

| claim | how |
|---|---|
| every conclusion holds under pypdf | re-measured under pypdf, not pdfplumber |
| five years reconcile to the thousand | Gate 1 per year, residual 0 |
| FY2019-20 misses by 351 | hand-reproduced campus sum + statement DOE |
| the tolerance is not load-bearing | assignment still unique at ±10K, every year |
| FY2022-23 per-campus core is derivable | med/aux present per-campus, all years |
| audit language differs at FY2020-21 | full-document phrase search, per year |
| the reshape moves no value | flatten diff = 0 events for FY2024-25 |
| the URLs are real | fetched; byte-size + magic + content-type match cache |
