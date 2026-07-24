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

## The audit-status sentence — RESOLVED, and this section was wrong

> **CORRECTION.** This finding originally said the quoted string "does
> not appear in ... any of the six reports". **That was wrong.** I had
> searched only the first twenty pages. The auditors' report sits around
> page 30, and searching the full documents finds the sentence in four
> of the six. The error was mine, not the source's.

Searched in full, the picture is:

| FY | "other information comprises pages …" |
|---|---|
| 2024-25 | **4 through 7** |
| 2023-24 | **6 through 9** |
| 2022-23 | 6 through 9 |
| 2021-22 | 6 through 9 |
| 2020-21 | no such auditor language |
| 2019-20 | no such auditor language |

The site quoted **"pages 4 through 7"**, which is verbatim correct for
FY2024-25 and **wrong for FY2023-24 — a year that also ships.** The two
oldest reports predate the standard that added an "other information"
section to the auditor's report, so the language is absent entirely.

**Fixed:** the page range is no longer quoted; it is described, with a
note that it differs between reports. Every fragment still quoted was
checked verbatim against BOTH shipped reports. No figure moved.

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
3. ~~Re-verify the PwC page-range sentence.~~ **Done** — it did not
   hold for FY2023-24 and has been corrected; see above.

Do not relax the strip identity, the column-sum check, or the
sparse-row proof to accommodate a vintage difference.

## What was measured

| claim | how |
|---|---|
| all twelve sources are real PDFs | fetch + magic bytes + content-type, never status |
| DOE published four different ways | row census across both table pages, six AFRs |
| `Impairment of capital assets` in the two oldest years only | same census |
| the anchor finds zero pages in the added years | `"Campus Financial Facts" in text`, per page, six AFRs |
| the PwC page range is 4-7 in FY2024-25 and 6-9 in FY2023-24 | regex over the FULL text of each report — the first-twenty-pages search that produced the original wrong claim missed the auditors' report, which sits near page 30 |
| every other quoted fragment is verbatim in both shipped years | substring check against the full text of each |
