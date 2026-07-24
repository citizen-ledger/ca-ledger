# V20 — FY2018-19's Exhibit C: readable for one fact, not for two

**Status: investigation only. Nothing built, nothing shipped.**
Measured 2026-07-24 against `pipeline/cache/ccc/exhibitc/exhibitc-2018-19.pdf`
(146 pages, declares "2018-19 Second Principal Apportionment").

The expected answer was "this vintage cannot be parsed honestly." That is
**not** what the document says. One fact reads cleanly and reconciles to
the dollar; two are genuinely absent. The reasons are worth recording
because two of them are new.

---

## 1. The structure is different because the formula was new

FY2018-19 is the **first Student Centered Funding Formula year**, and its
Exhibit C is laid out accordingly:

- **Page 0 is a district page** (Allan Hancock), not the statewide
  summary. **Statewide Totals sits at page 144**, near the end. Later
  vintages put it first. Nothing turns on this — the parser finds the
  statewide page by its entity name, not its position — but it is why the
  document first appeared to contain no controls at all.
- The revenue block is annotated with its own algebra (`k`, `l`, `m`,
  `n`, `p`, `q`) and per-row explanations ("Only for non basic aid
  districts", "Also displayed on Exhibit A"). Those annotations turn out
  to matter — see §3.

## 2. The state general fund is published — under a THIRD name

The V19b lesson repeats, one vintage further back. Across the window this
single fact carries three different labels:

| vintage | label |
|---|---|
| 2018-19 | **`State General Apportionment`** (`Total State General Apportionment`) |
| 2019-20, 2020-21 | `State General Entitlement` |
| 2022-23, 2023-24 | `State General Fund Allocation` |

Concluding "absent" from a regex miss would have been a **false absence**
for the third time. The statewide figure is printed plainly:
`Total State General Apportionment 2,700,724,947`
(= General Apportionment 2,632,972,774 + FTFH 67,752,173).

## 3. BOTH extractors corrupt this vintage's numbers — differently

This is the new problem, and it is not the document's fault so much as
its glyph positioning:

| extractor | numbers | district names |
|---|---|---|
| **pypdf** | spurious space **after a comma** — `62, 147,582` — on **46 of 72** pages | **3 names lose leading characters**: `rth Orange County CCD`, `alo Verde CCD`, `ralta CCD` |
| **pdfplumber** | spurious space **after the first digit** — `3 0,373,971`, `$ 2 ,632,972,774` | **0 corrupted** — all 72 clean |

pypdf's name truncation is the serious one: a district whose name loses
its first characters cannot be matched to its code without fuzzy
matching, and fuzzy identity matching is what this repo refuses. Under
pypdf only 64 of 72 districts parsed and the sum was short by
$333,883,803. Under pdfplumber the names are clean but only 19 of 72
parsed, because the whitespace lands elsewhere.

**So the extractor is a per-vintage property**, exactly as the anchors and
row labels already are. Declaring *which library reads a vintage* would be
a new kind of declaration for this pipeline, and this is the vintage that
needs it.

## 4. A BOUNDED repair — and why it is not a loosened pattern

Stripping whitespace inside numbers is, in general, precisely the
loosening this repo refuses: in a table of adjacent numeric columns it
silently welds two different figures into one confident wrong number.

It is safe **here** only because the value is **delimited on both sides by
the document's own printed text** — the declared label before it and the
row's own annotation after it:

```
Total State General Apportionment  3 0,373,971  Also displayed on Exhibit A. p = n + o
                                  └──── the captured span ────┘
```

Measured over all 72 district pages: **every** captured span is a single
number token once whitespace is removed — **zero** spans contain two
tokens. A span that cannot hold two figures cannot merge two figures.

And the repair is validated by an independent control rather than by
inspection:

```
72 districts, all parsed
district sum = 2,700,724,947
statewide    = 2,700,724,947
residual     = +0        (exact, to the dollar)
```

An exact tie across 72 districts is not something a mis-repair produces.

## 5. Funded FTES is NOT published at this vintage

`Funded FTES` appears **nowhere** in the document — 0 of 146 pages. Later
vintages print it as one labelled figure ("Funded FTES: 1,113,323.71"),
used as the EPA denominator and as the per-FTES denominator.

FY2018-19 instead prints **Section Ia: FTES Allocation**, a category table
(Credit / Special Admit / Incarcerated / CDCP / Noncredit) whose `Totals`
row offers several candidates — Applied #1, Applied #2, Paid
(1,127,216.76), FTES Reported (1,111,541.16), a 3-year average — and no
statement of which is the funded figure.

Choosing one and labelling it "funded FTES" would be an unforced
judgement about which quantity corresponds, with **no printed control to
validate the choice against**. That is the decision this project avoids.

**Funded FTES stays not-published for FY2018-19** — and with it
`perFtes`, which is Current Expense ÷ funded FTES.

## 6. Community-supported has no control at all

`Community Supported` appears **0 times**. The only related text is the
per-row annotation "Only for non basic aid districts". There is **no
printed count** anywhere in the document.

Eight districts do show a property-tax excess (South Orange, San Mateo,
West Valley-Mission, MiraCosta, San Jose-Evergreen, Marin, Napa Valley,
Sierra Joint — the same roster as neighbouring years). But a derivation
with nothing to reconcile against is exactly what V19 refused for
FY2019-20 and FY2023-24, where a control existed and disagreed. Here no
control exists to agree or disagree.

**Community-supported stays not-published for FY2018-19.**

## Recommendation

**FY2018-19 can be read honestly for one fact, and should be — but not in
the same shape as the others.** Concretely:

| fact | verdict |
|---|---|
| state general apportionment | **readable**; reconciles exactly (+0) |
| funded FTES | **not-published** — no such figure exists at this vintage |
| community-supported | **not-published** — no printed control exists |
| perFtes | **not-published** — depends on funded FTES |

Building it requires one thing the pipeline does not yet have: a
**declared per-vintage extractor** (`pdfplumber` for this vintage,
`pypdf` for the rest) together with the bounded label→annotation repair.
That is a real addition to the declaration vocabulary, and it should be
its own PR rather than folded into the wiring change.

Until then FY2018-19's apportionment facts remain not-published, which is
the correct state — three of its four are not-published permanently in any
case.

## What was measured

| claim | how |
|---|---|
| statewide page is at index 144 | entity-name scan over all 146 pages |
| the state general fund is published under a third label | statewide and district revenue blocks read verbatim |
| pypdf corrupts 46/72 pages and 3 names | regex census over every district page |
| pdfplumber corrupts 0 names | same census, second extractor |
| the bounded span cannot merge columns | every one of 72 spans is a single token after whitespace removal |
| the repair reconciles | 72-district sum vs the printed statewide total, residual +0 |
| funded FTES does not exist here | full-document search for the label; Section Ia read verbatim |
| no community-supported control exists | full-document search |
