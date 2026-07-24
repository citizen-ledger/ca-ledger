# V18 — UC's campus segmentation is not uniform across the four added years

**Status: investigation. The extension is NOT built.**
Measured 2026-07-23 against the six Annual Financial Reports, on branch
`uc-four-years`.

The instruction was explicit: *confirm UC published the same segment
lines in each added year, and if a year's segmentation differs, that's a
finding, not a mapping exercise.* It differs — in four different ways
across six years. This records what each vintage actually publishes.

---

## The sources are all present

Every AFR and every UCOP FTE PDF for FY2019-20…FY2024-25 fetches and is
a real PDF, verified on `%PDF-` magic bytes **and** `application/pdf`
content-type, never on status:

| FY | AFR | UCOP FTE |
|---|---|---|
| 2024-25 | 3.4 MB ✓ *(shipped)* | 126 KB ✓ |
| 2023-24 | 3.5 MB ✓ *(shipped)* | 126 KB ✓ |
| 2022-23 | 23.2 MB ✓ | 125 KB ✓ |
| 2021-22 | 1.4 MB ✓ | 124 KB ✓ |
| 2020-21 | 4.4 MB ✓ | 118 KB ✓ |
| 2019-20 | 4.5 MB ✓ | 116 KB ✓ |

Availability is not the blocker. What the documents *say* is.

## The DOE laboratories line is published four different ways

`STRIP_LINES` is `["Medical centers", "Auxiliary enterprises",
"Department of Energy laboratories"]` — the three UC-published segments
subtracted to derive the comparable "core". Across the window that third
line is not one thing:

| FY | DOE in the campus table | form | "Excludes DOE laboratories" footnote |
|---|---|---|---|
| 2024-25 | **yes** | per-campus row | no |
| 2023-24 | **yes** | per-campus row | no |
| 2022-23 | **no** | `DOE Labs Expenses`, one systemwide figure (1,104,266) | **yes** |
| 2021-22 | **yes** | `Department of Energy laboratories`, one systemwide figure (990,713) | **yes** |
| 2020-21 | **no** | absent from the campus table | **yes** |
| 2019-20 | **no** | absent from the campus table | **yes** |

Four treatments: a per-campus row; a systemwide-only line under the
current label; a systemwide-only line under a **different** label
(`DOE Labs Expenses`); and outright absence.

**The strip is therefore not the same operation in each year.** Where
the campus table already excludes DOE, subtracting it computes a
different quantity than where it is included. A "core" series built by
applying one strip across all six years would be comparing
differently-composed figures and calling the difference a trend.

## A second row difference

FY2019-20 and FY2020-21 publish **`Impairment of capital assets`** as a
function row. FY2021-22 onward do not, and it is not in
`FUNCTION_ROWS`. The parser would meet an unrecognised row in exactly
the two oldest years — which its refusal is designed to catch, and
should.

## The parser's anchor does not match the older vintages

`fetch_year` locates the table by `"Campus Financial Facts" in text`.
The four older AFRs render that heading in **capitals** —
`CAMPUS FINANCIAL FACTS5` — so the anchor finds **zero pages** in all
four. Measured: `[7, 8]` and `[9, 10]` for the two shipped years, `[]`
for every added year.

The table is there (page 9 in the older vintages, page 7 in the
newest), and the older layout differs further: campus names in capitals
(`BERKELEY DAVIS IRVINE…`) against mixed case now, and a `STUDENTS`
sub-header where the current vintage has `Population segment`.

This one is a parser change, not a finding — but it must be a
**declared per-vintage anchor**, in the shape of `CE_VINTAGE` and
`ALT_SCHOOL_COL`, not a loosened case-insensitive match. A case-blind
search is precisely the widened detector this repo has refused twice.

## The audit-status sentence — do not carry it backward unchecked

The shipped claim quotes PwC's *"other information comprises pages 4
through 7"*. **That string does not appear in the first twenty pages of
any of the six reports**, including the two currently shipped — so the
sentence cannot be verified from the text at the location the pipeline
reads, in any year.

What *is* verifiable in all six: the table is headed `Campus Facts in
Brief (Unaudited)`. In the older vintages that heading is split across
two lines, which is why a naive substring test reports it differently.

The page-range claim needs re-verification against each report before
it is repeated for any year, including the two already published. That
is a live-data check I have not completed, and it should not be assumed
because it reads plausibly.

## Recommendation

**Hold the extension.** Not for lack of sources — all twelve fetch
cleanly — but because shipping now would publish a core series whose
third strip component means four different things across six years,
with no statement to that effect.

The bounded next steps, in order:

1. **Decide the DOE treatment across the break.** Either publish the
   core only for years where the segmentation matches and mark the rest
   not-published, or publish all six with a declared structural-break
   statement naming which years exclude DOE from the campus table.
   This is a judgement about what the figure means, and belongs with a
   human.
2. **Declare the per-vintage table anchor and row set** — capitals
   heading, `Impairment of capital assets` in the two oldest years —
   the way `CE_VINTAGE` declares K-12's.
3. **Re-verify the PwC page-range sentence** against each report, and
   correct it for the shipped years if it does not hold.

Do not relax the strip identity, the column-sum check, or the
sparse-row proof to accommodate a vintage difference.

## What was measured

| claim | how |
|---|---|
| all twelve sources are real PDFs | fetch + magic bytes + content-type, never status |
| DOE published four different ways | row census across both table pages, six AFRs |
| `Impairment of capital assets` in the two oldest years only | same census |
| the anchor finds zero pages in the added years | `"Campus Financial Facts" in text`, per page, six AFRs |
| the PwC page-range string is absent | regex over the first twenty pages of each report |
