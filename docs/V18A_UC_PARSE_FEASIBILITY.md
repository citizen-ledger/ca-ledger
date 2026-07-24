# V18a — UC extension: all six years are parseable. The declarations needed, measured.

**Status: feasibility ESTABLISHED for all six years. The extension is
NOT built.** Measured 2026-07-23 against the six AFRs, branch
`uc-six-years`.

V18 recommended holding the extension and the decision came back:
publish all six with a declared structural-break statement. This
establishes that the parse is achievable for every year in the window,
and pins down exactly which per-vintage declarations it requires — so
the build is specified rather than exploratory.

Nothing in the pipeline or payload was changed by this investigation.

---

## The result

Assignments satisfying every printed column total. **The gate requires
exactly one** — zero means the arithmetic cannot close, more than one
means it is ambiguous. Both are refusals.

| FY | exact (<0.5) | ±1 thousand | ±10 thousand | |
|---|---|---|---|---|
| 2019-20 | 1 / 1 | 1 / 1 | 1 / 1 | unique |
| 2020-21 | 1 / **0** | 1 / 1 | 1 / 1 | unique |
| 2021-22 | 1 / 1 | 1 / 1 | 1 / 1 | unique |
| 2022-23 | 1 / 1 | 1 / 1 | 1 / 1 | unique |
| 2023-24 | 1 / 1 | 1 / 1 | 1 / 1 | unique *(shipped)* |
| 2024-25 | 1 / 1 | 1 / 1 | 1 / 1 | unique *(shipped)* |

*(page 0 / page 1)*

Five of six years prove **at exact tolerance** once the right rows are
declared. One year needs one unit at the source's own printed
resolution, and section 4 is about whether that is legitimate.

## 1. A declared per-vintage anchor — required

The four older AFRs capitalise both anchors:

| | shipped vintage | older vintage |
|---|---|---|
| page | `Campus Financial Facts` | `CAMPUS FINANCIAL FACTS5` |
| section | `Operating expenses by function` | `OPERATING EXPENSES BY FUNCTION` |

**Only the section headers differ.** The row labels are mixed case in
every vintage (`Instruction`, `Medical centers`), so the declaration is
narrow — two strings per vintage, not a case-blind search. A
case-insensitive match is the widened detector this repo has twice
refused, and it is not needed here.

## 2. The row set differs per vintage — three distinct declarations

Each was found by the gate refusing, not by inspection:

| vintage | declared row | what it is |
|---|---|---|
| 2019-20, 2020-21 | `Impairment of capital assets` | a separate function row |
| 2021-22 | `Other and Impairment of capital assets5` | **the two rows COMBINED into one line** |
| 2022-23 | `DOE Labs Expenses` | the DOE line under a different label |

The FY2021-22 combined row is a new finding, not in V18. UC merged
`Other` and `Impairment` into a single printed line for that year alone.

**This requires longest-label-first matching**, because
`Other and Impairment of capital assets5` begins with `Other`, which is
itself a declared row. Matched shortest-first the line binds to `Other`,
silently attributing the combined quantity to one of its two parts —
a wrong number that parses cleanly. The row table must be ordered by
descending label length, and that ordering needs its own test.

## 3. Why each blocked year was blocked

Page 1 carries Riverside…Santa Cruz plus the printed Systemwide column,
where the DOE line lives.

- **FY2021-22** — the combined row bound to `Other`, dropping the
  `Impairment` quantity. Fixed by the declared combined label.
- **FY2022-23** — `DOE Labs Expenses` matched no declared row and was
  not extracted at all, leaving Systemwide short by 1,104,266. Fixed by
  the declared alias.
- **FY2020-21** — every row recognised, arithmetic still short. Cause in
  section 4.

## 4. FY2020-21: UC's own rounding, and the control that justifies ±1

FY2020-21's San Diego column is short by **exactly 1** — one thousand
dollars, one unit at the printed resolution. Worked by hand:

```
San Diego total            6,149,349
  full rows sum            3,750,033
  residual needed          2,399,316
  Medical centers          2,396,943
  Impairment                   2,372
  assigned                 2,399,315   <- short by 1
```

Every other column in that year ties **exactly**, and the assignment is
otherwise forced: Medical centers, Impairment and Other each land in the
only columns that can accept them.

UC prints in thousands and rounds each figure independently, so a column
total is not obliged to equal the sum of its rounded components.
Requiring exact equality demands a precision the source does not claim —
which is the same error, in the opposite direction, as reading an absent
figure as zero.

**The control that makes this safe:** at **±10 thousand** — ten times
looser — every year still admits **exactly one** assignment. The
tolerance is not what makes the proof succeed; the arithmetic is. A
tolerance wide enough to start admitting alternatives would show up as a
count above one, and it does not, at ten times the width proposed.

So ±1 thousand is modelling the source's stated precision, not loosening
the gate. It should be **declared as the source's resolution**, with the
±10 uniqueness control kept as a standing test — so that if a future
vintage ever does become ambiguous, the test fails rather than the
tolerance quietly absorbing it.

## What this settles, and what it does not

**Settled:** every year in the window can be parsed and every year
passes the column-sum proof uniquely. Availability was never the blocker
(V18) and now extraction isn't either.

**Not settled — the substantive question V18 raised is untouched.** DOE
is still published four different ways across six years, and this
finding is only about *reading* the table, not about what a core series
built across it means. Specifically outstanding:

1. The DOE treatment table — per year, declared: subtract /
   already-excluded / systemwide-only. Never inferred from whether a row
   parses, which is precisely what the four different labels above would
   make tempting.
2. **FY2022-23's per-campus core.** DOE is systemwide-only that year, so
   a per-campus core cannot be derived on the same basis as FY2023-24
   and FY2024-25. Per the decision, that year's per-campus core is
   not-published while its systemwide figure ships — using the
   three-valued encoding from #55, not a zero.
3. The break statement on the trend view and the record — where the
   series crosses it, not only in a method note.
4. COVERAGE suppression, deflator window check, printed-header order
   gate, shape gate, empty-gate guard, per-year gate report.
5. Tests: the longest-label-first ordering, the ±10 uniqueness control,
   and a positive control for each declared row — a negative that never
   fires proves nothing.

## What was measured

| claim | how |
|---|---|
| all six years prove uniquely | exhaustive order-preserving placement search over every sparse row, both pages, six AFRs |
| widening to ±10 thousand admits no alternative | same search at three tolerances — the positive control on the tolerance itself |
| FY2020-21 is short by exactly 1 on San Diego alone | per-column residual, all six columns, arithmetic reproduced by hand above |
| FY2021-22 combines Other and Impairment | verbatim row dump, page 1 |
| FY2022-23's DOE row is unrecognised | census of printed rows against the declared row set |
| only section headers change case, not row labels | label census across all six vintages |
