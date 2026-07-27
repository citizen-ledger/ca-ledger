# V26 finding: adoption provenance — who approved this, and when

*Investigated 2026-07-27. Every layer's source probed directly: the
eBudget API live, the SACS `.mdb` archives and SCO Financial Transactions
Report workbooks from the local cache, plus the legislature's access
policy. No build.*

## Recommendation, up front

**(c) Don't ship — merely decorative, which the brief admits as a
reason, and on the one layer that qualifies there is no single date to
show.**

Three findings carry it, and they are independent:

**First, only one layer's own figures were adopted by anybody.** The
state page publishes enacted appropriations; every other layer publishes
an *actual* — a year-end accounting record of money already spent, which
nobody adopts.

Three further pages do render a borrowed appropriation figure, and the
detail matters: **each does so inside a panel whose entire purpose is to
warn that the two bases are different kinds of number.** `ccc.html`
prints "**THESE FIGURES DO NOT ADD TO THE STATE BUDGET**" above its
$9.7B; `schools.html` prints "$81.6B enacted" while saying "one is an
enacted plan and the other is year-end accrual actuals". So an "adopted
[date]" label on those pages would not merely be wrong about the
surrounding numbers — **it would undercut the boundary the panel exists
to draw** (§1.7).

**Second, on the one layer where it does exist, it does not vary.** Nine
published Budget Acts were signed on **June 26, 27 or 28** — six of nine
on June 27. The site already tells readers the budget is "fixed when each
year's Budget Act is signed… typically signed in late June." The proposed
feature would replace *typically late June* with *June 27*, nine times.

**Third, there is no single adoption date to show anyway.** A Budget Act
is not one enactment: **244 distinct bills** in the 2023-24 session carry
a subject naming the Budget Act of 2023, **18 bill versions amend two
Budget Acts at once**, and the Legislature's own citation form is a *set*
of chapters — "the Budget Act of 2023 (Chapters 12, 38, and 189 of the
Statutes of 2023)". One date in a field headed *adopted* is a
simplification the source itself declines to make.

| | |
|---|---|
| layers whose **own** figures are adopted | **1 of 11** (the state page) |
| further pages rendering a *borrowed* appropriation | **3** (K-12, CCC, CSU) |
| adoption fields in the state source | **1** — a prose string |
| adopting-body field in any source | **0** |
| range of nine Budget Act signing dates | **3 days** |
| bills naming the Budget Act of 2023, one session | **244** |
| SACS columns matching date/adopt/approve/board | **0 of 33**, across 4 vintages |
| SCO FTR header cells searched / adoption **dates** found | **27,916 / 0** |

And the sharpest way to put it: **the date is nearly constant where it is
published, unpublished everywhere it would actually vary, and not a
single date where it is most consequential.**

**The site is not avoiding provenance — it already ships the version that
works.** The community-college layer stamps every apportionment with its
round (`ROUND_NAME` at `ccc.html:309` — First Principal, Second
Principal, Recalculation) because those stages are computed from
different information and produce different numbers. That is the same
feature V26 proposes, on the one layer where the stamp changes what a
reader should think. **Provenance earns its place by varying** (§1.4).

---

## 1. What is published, per layer

### 1.1 The state — one field, and the pipeline already reads it

`GET /api/publication/e/{fy}/appInfo` returns nine keys:

```
previousYear, currentYear, budgetYear, publication, publicationTitle,
publicationDate, pit, proposedAppName, ebudgetHome
```

**`publicationDate` is the only adoption field on the site's entire
source surface.** Its value is a prose string:

```
2024-25  ->  "Enacted on June 26, 2024"
2025-26  ->  "Enacted on June 27, 2025"
```

Absent, confirmed against every published year: **no Budget Act chapter
number, no bill number, no separate signing date, and no adopting-body
field.** The word *Enacted* inside a prose string is the whole of the
"who".

The pipeline **already reads it and throws it away**
(`pipeline/fetch_state_data.py:338`) — it is interpolated into a
`sys.stderr` progress line, and `save_cache()` persists only `year`,
`source`, `fetched`, `stateGrandTotal`, `agencies`. This is a known open
item: `docs/V13_CHANGEFEED_FINDING.md` lists storing `publicationDate`
as cheap improvement #5. **That item is about the change record, not
about a reader-facing label, and §5 keeps them apart.**

### 1.2 Cities, counties, special districts — nothing, in 27,916 columns

Every cached SCO Financial Transactions Report workbook was searched:
**11 workbooks, 416 sheets, 27,916 header cells.**

| keyword | hits |
|---|---|
| `adopt` | **0** |
| `resolution` | **0** |
| `ordinance` | **0** |
| `council` | **0** |
| `board` | **0** |
| `budget` | **0** |
| `enact` | **0** |
| `approv` | 116 — every one *Voter-Approved Taxes* / *Voter-Approved Indebtedness* |
| `certif` | 55 — every one *Certificates of Participation* |

Not one adoption date, and — worth noting on its own — **not one
occurrence of the word "budget" anywhere in 27,916 column names.** The
FTR, collected under Government Code §12463, is a report of financial
transactions that occurred.

**One correction to my own sweep, because it changes what the section can
claim.** The keyword list above omitted `appropriat`, which returns **28
header hits** across four sheets — `SD_APPR_LIMIT_INFORMATION`,
`SD_APPR_LIMIT_SCHEDULE`, `CIX_SUMM_STATS`:

```
Appropriations Limit
Total Annual Appropriations Subject to the Limit
Revenues Received (Over) Under Appropriations Limit
```

This is the **Gann limit** (Article XIII B), and it *is* a figure a
governing body adopts by resolution each year — so the flat statement
"the FTR contains nothing anyone adopted" would have been wrong, and a
sweep that stops at its own first list of keywords is how a finding gets
there.

It does not change the conclusion, for two reasons: the FTR carries the
**limit amount only — no adoption date, no resolution number, no
meeting** — so the provenance field still does not exist; and **the site
does not publish the Gann limit** on any layer, so there is no figure for
a date to attach to. It is recorded because the next investigation to ask
"is there anything adopted in the FTR?" should start from a yes.

The only genuine date fields are:

| field | what it is |
|---|---|
| `Fiscal Year End` | the period covered |
| `Electronic Report Due Date` | the **filing deadline**, not an adoption |
| `Contract Date`, `Sunset Date of the Parcel Tax` | substantive, not provenance |

And the form states its own nature: the `ENTITIES_BCU` sheet asks
*"Does the report contain data from audited financial statements?"* The
FTR is a financial report of what happened, not a budget anyone adopted.

### 1.3 K-12 — the brief's premise does not hold for what this site reads

The brief expects "K-12 budgets are board-adopted with dates in the SACS
submission." **Tested directly, and it is false for the SACS
unaudited-actuals archive.**

`sacs2425.mdb` holds **9 tables** — `Charters, Function, Fund, Goal,
LEAs, Object, Resource, UserGL, UserGL_Totals` — and, with system tables
included, only Access's own `MSys*` catalog. Across all of them, **33
distinct column names, of which zero match** `date|adopt|approv|certif|
board|resolut|submit|sign`. Verified on four vintages (FY2017-18,
FY2020-21, FY2022-23, FY2024-25) and on the Alternative Form files.

Two columns look like they might carry a stage and do not:
**`Period` = `"A"` and `Colcode` = `"BA"` for all 1,600,940 rows**, in
every vintage. Single-valued fields carry no distinction. The pipeline
does not read either.

CDE does collect a separate budget-period SACS submission, which *is*
board-adopted. **The site does not read it**, and reading it would be a
new layer on a different basis, not a label on this one.

### 1.4 Higher education — and the one layer that already does this well

CSU and UC are audited GAAP accrual: actuals, with no Trustees or
Regents approval date in the fields the pipeline reads.

**CCC is not purely an actual, and my first draft was wrong to say so.**
Alongside the CCFS-311 spending figure (`ce`), the layer publishes
**state apportionment**: `stateGf`, `fundedFtes`, and the `perFtes`
denominator, read from the Chancellor's Office SCFF Exhibit C. Measured
from `ccc-data.js`: statewide FY2023-24 `stateGf` = $3,479,573,986,
`fundedFtes` = 1,087,711.16. An apportionment is a **funding
determination certified before the district's books close** — not money
already spent.

And here is the part that matters for this investigation: **the site
already publishes the provenance of those figures, and does it well.**
Each apportionment carries its *round*, rendered by name at
`ccc.html:309`:

```js
const ROUND_NAME = {"P1":"First Principal (P1)",
                    "P2":"Second Principal (P2)",
                    "R1":"Recalculation (R1)"};
```

with `meta.roundsDiffer` stating that the three "are computed at
different points from different information, and they are not
interchangeable."

**That is exactly the feature V26 was asked to consider — a provenance
stamp on a figure a body determined — and it already exists on the one
layer where the stamp genuinely varies and genuinely changes the
number.** §3 argues the state's signing date fails that test. CCC passes
it, which is why it shipped. The principle is not "the site avoids
provenance"; it is that provenance earns its place by varying.

### 1.5 The Budget Act's chapter number — obtainable, and not worth having

My first pass on this was wrong and the correction matters, so it is
recorded rather than quietly fixed.

`leginfo.legislature.ca.gov` — the HTML site — does carry a blanket
`User-agent: * / Disallow: /`, and on that basis I initially concluded a
chapter number would need a third manual-cache exception after CSU and
compensation.

**That conclusion was wrong.** The Legislature publishes its own bulk
data on a *different* host, `downloads.leginfo.legislature.ca.gov`, which
carries **no robots exclusion at all** — verified by content, not status:
`/robots.txt` returns a genuine Apache 404 body, the directory index
returns 8,519 bytes listing `pubinfo_1989.zip` … `pubinfo_2025.zip`, and
a range request against `pubinfo_2023.zip` returns `206 Partial Content`,
`Accept-Ranges: bytes`, 1,261,848,876 bytes, opening `50 4b 03 04` — real
ZIP magic. Individual members are extractable by range read without
downloading the archive.

**So the chapter number is automatable, and cost is not the objection.**
The objection is what you get when you look — §4.

### 1.6 The per-layer table

| layer | basis published | own figures adopted? | shows a borrowed appropriation? |
|---|---|---|---|
| **State** | Enacted appropriations · Budgetary-Legal | **yes** | — |
| Cities | Reported actuals | no | no |
| Counties | Reported actuals | no | no |
| K-12 districts | Unaudited actuals · SACS | no | **yes** — "$81.6B enacted" |
| County offices of ed. | Unaudited actuals · SACS | no | no |
| Charter schools | Unaudited actuals · SACS / Alt Form | no | no |
| Special districts | AS FILED · UNRECONCILED | no | no |
| Community colleges | Modified accrual · CCFS-311 | no | **yes** — "$9.7 billion" |
| CSU | Audited GAAP / GASB | no | **yes** — CSV column |
| UC | Audited GAAP / GASB | no | no |
| Compensation | Reported positions, as filed | no | no |

**One of eleven.** To source that count precisely, since a looser version
of this sentence was wrong on the first pass:
`pipeline/build_search_index.py` carries **ten** layer entries and does
**not** mention compensation at all; compensation is published
(`compensation.html`, `compensation-data.js`) but is not indexed. Ten
indexed layers plus compensation is the eleven.

Measured across the shipped payloads: **ten payload files, of which eight
carry a `meta.basis` string** — and every one of those eight describes a
retrospective accounting record, none an appropriation. **Two carry no
`meta.basis`: `data.js` and `deflator-data.js`.** `data.js` is the state
layer, the one that publishes an adopted figure; `deflator-data.js` is
the inflation index and is not a spending layer at all.

### 1.7 The three borrowed appropriations — and why they argue *against*

My first draft of this finding said flatly that only the state page shows
an adopted figure. **That was wrong**, and the correction is the most
useful thing in the investigation.

Three other pages render an appropriation to the reader:

| page | what is rendered | where |
|---|---|---|
| `schools.html` | **"$81.6B enacted"** for FY2024-25, with an `agreement` ratio of 0.9524 | `:632`, from `school-data.js` `meta.overlap.years[fy].agencyEnactedB`, written at `fetch_school_data.py:1598` and tying exactly to `data.js`'s "K thru 12 Education" agency total |
| `ccc.html` | **"$9.7 billion"** state General Fund share, and the **$13.6B** Prop 98 K-14 guarantee | `:590`, from `ccc-data.js` `meta.overlap.statement` |
| `csu.html` | a per-campus **`state_appropriation_thousands`** column for 23 campuses plus a systemwide total | `:550-553`, CSV export |

So a reader sees an appropriated dollar figure on **four** pages, not
one. But look at what surrounds each of them:

- `ccc.html` prints them under the heading **"THESE FIGURES DO NOT ADD TO
  THE STATE BUDGET"**.
- `schools.html` prints its "$81.6B enacted" inside the sentence "the two
  layers agree to roughly 1–3.5% and never to the dollar, **because one
  is an enacted plan and the other is year-end accrual actuals**".

**Every one of these figures exists to mark a boundary between two
bases.** They are there to stop a reader adding an appropriation to an
actual. An "Adopted [date]" label dropped onto those pages would attach
to the single number in the panel that *is* an appropriation while
sitting among thousands that are not — and would push in exactly the
opposite direction from the panel's own sentence.

That is the same failure as §4.1's `data.js` record, found in three more
places. **The refutation of my original claim did not weaken the
recommendation; it produced the strongest argument for it.**

---

## 2. Fact or inference

The brief's line is the right one, and it cuts more than expected.

**A fact:** `"Enacted on June 26, 2024"` for FY2024-25. Printed in the
source, machine-readable, one field.

**Not in the source — the adopting body.** No field names the
Legislature or the Governor. Writing "adopted by the Legislature and
signed by the Governor" would be *our* knowledge of California's
process. It is correct, and it is also **constant for every year on the
page** — which makes it a one-line statement about the state layer, not
a per-year fact. `about.html` already carries that sentence.

**Out of scope by the brief:** who sat on the body, and naming
individuals.

So the honest inventory of what could be attached per year is: **one
prose date, on one layer.** Not a body, not a citation, not a vote.

---

## 3. Would it add anything? The decorative test

Every Budget Act signing date the source publishes:

| FY | signed | | FY | signed |
|---|---|---|---|---|
| 2017-18 | June 27 | | 2022-23 | June 27 |
| 2018-19 | June 27 | | 2023-24 | June 27 |
| 2019-20 | June 27 | | 2024-25 | June **26** |
| 2020-21 | June **26** | | 2025-26 | June 27 |
| 2021-22 | June **28** | | | |

**Nine years. Three distinct dates. A range of three days.** Six of nine
are identical.

This is not an accident of the sample — it is structural. The California
Constitution fixes the Legislature's passage deadline at June 15, and the
fiscal year begins July 1. The signing date is **determined by a
constitutional deadline, not by anything about the budget in question.**
A column of near-identical dates tells a reader nothing they could act
on, and implies a variability that does not exist.

Against that, the site's existing prose is already accurate and already
does the work:

> "Enacted figures are appropriations under California's Budgetary-Legal
> basis of accounting, fixed when each year's Budget Act is signed… One
> new fiscal year is added per annual Budget Act, typically signed in
> late June." — `index.html`

**The feature would convert one true sentence into nine nearly identical
data points.** That is the definition of decorative.

### 3.1 And the "next adoption date" is a sentinel, not a schedule

The brief suggests showing the next adoption date "where the source
publishes a schedule." **The source publishes no schedule.** For years
not yet adopted it returns:

```
2026-27  ->  "Enacted on January 01, 9999",  /statistics -> []
2027-28  ->  "Enacted on January 01, 9999",  /statistics -> []
```

`publication` still reads `"Enacted"` and `pit` still reads `"e"` — a
soft-200 carrying a sentinel date, the exact hazard this project already
documents. DOF is explicitly declining to state a future date. Deriving
one from the constitutional deadline would be our inference, on the wrong
side of §2's line — and a naive build of this field would ship **"1
January 9999"** to the page. The pipeline's current guard is indirect
(it drops years with empty `/statistics`); nothing checks the date.

### 3.2 The symmetry that settles it

**Where the date is published, it barely varies. Where it would vary, it
is not published.**

Local adoption dates genuinely differ — measured through the proxy the
FTR does carry, the fiscal year end:

- **cities: 479 of 482 end June 30** — near-uniform anyway
- **special districts: 9 distinct fiscal-year-ends across 5,111
  entities** — 258 on December 31, 38 on September 30, 32 on February
  28, and five more

Those 352 off-cycle districts adopt budgets on dates a reader could not
guess, and that is exactly the population for which **no source publishes
an adoption date at all.**

---

## 4. The trap: amended budgets

The brief's trap has two halves. **On the half it asked about, the site
is acquitted. On a half it did not anticipate, the proposed label fails
outright — there is no single adoption date to show.**

### 4.0 "The Budget Act" is not one enactment

Read from the Legislature's own bulk data (session `pubinfo_2023.zip`,
`BILL_VERSION_TBL.dat`, 20,525 version rows):

| subject line | versions |
|---|---|
| `Budget Act of 2023.` | 367 |
| `Budget Acts of 2022 and 2023.` | **18** |
| `Budget Act of 2024.` | 18 |
| `Budget Acts of 2021 and 2022.` | 8 |
| `Budget Act of 2023: health.` | 4 |

**244 distinct bills in that one session carry a subject naming the
Budget Act of 2023.** Most are introduced and never chaptered, so that is
an upper bound on activity rather than a count of amendments — but the
shape is unambiguous, and two details settle the question:

- **18 versions amend two Budget Acts at once** (*"Budget Acts of 2022
  and 2023"*). One signing date cannot describe a bill that changes two
  years.
- **Bills naming the Budget Act of 2024 appear in the 2023-24 session,
  and bills naming the Budget Act of 2022 still appear in it too.**
  Amendment activity for a given Budget Act spans sessions, so the
  amending window does not close with the fiscal year.

The Legislature's own drafting convention follows from this: a Budget Act
is cited as a *set* of chapters — "the Budget Act of 2023 (Chapters 12,
38, and 189 of the Statutes of 2023)". **A field headed "adopted" with
one date in it would be a simplification the source itself declines to
make.**

### 4.1 The half the brief asked about — the site is acquitted

DOF restates a fiscal year in each subsequent publication. Every
`/rwaCntl` row carries `pyTotDols` / `cyTotDols` / `byTotDols` — the same
year appears as *budget year*, then *current year*, then *prior year*,
with different values each time. Measured, FY2024-25 as enacted in June
2024 against the same year restated in the 2025-26 publication:

| org | as enacted | restated | change |
|---|---|---|---|
| 0515 | 25,079 | 24,809 | −1.1% |
| 1045 | 3,210 | 3,199 | −0.3% |
| 1111 | 758,520 | 740,098 | −2.4% |
| 1115 | 171,734 | 186,915 | **+8.8%** |
| 1700 | 66,634 | 65,750 | −1.3% |
| 1701 | 178,095 | 175,434 | −1.5% |
| **total** | **1,203,272** | **1,196,205** | −0.6% |

*(thousands; six departments, all six differ)*

**The site reads `byTotDols`** (`fetch_state_data.py:286,288`) — the
budget-year column of each year's own enacted publication. Combined with
`pit: "e"`, that is a point-in-time snapshot at enactment. **So the date
and the figure do correspond: "Enacted on June 26, 2024" is true of the
number shown.**

What remains is softer and still real. The label would say *adopted*,
which reads as *settled*, about a figure DOF has since restated by up to
8.8% at department level. The site handles this today by showing enacted
and actual side by side and explaining the gap as mid-year legislation,
re-appropriations, carryover and reversions (V3).

**And on this layer the two bases share a single record**, so the label
would have nowhere correct to sit. A sample agency in `data.js`:

```json
"Health and Human Services": {
  "gf": 73.962, "sp": 39.684, "bd": 0.0, "fed": 107.304,
  "actual": { "gf": 70.157, "sp": 40.491, "bd": 0.0, "fed": 111.991 }
}
```

The top-level figures are enacted; the nested `actual` object is not.
**"Adopted June 26, 2024" is true of the outer four numbers and false of
the inner four**, in the same object, on the same row of the same table.
That is the adjacency problem recorded as `OPEN.md` pattern 2q one
investigation ago, at the tightest scale it can occur — not two panels on
a page, but two bases in one record.

### 4.2 A wording question this raises, stopping short of calling it a defect

Three files carry the phrase *"fixed when each year's Budget Act is
signed"* — `index.html:599`, `about.html:155`, `reading.html:154`.

**Read strictly, all three are accurate**: the grammatical subject is the
*enacted figures*, and those genuinely are the June snapshot the pipeline
reads. This finding does **not** claim the site states something false,
and no correction is proposed here.

What §4.0 shows is that a reader could take the sentence to mean *the
Budget Act* is settled at signing, which it is not. Today that reading is
available but unprompted. **An "Adopted [date]" data field would promote
it from an available misreading to an asserted fact** — which is a reason
against the feature rather than against the existing sentence.

If anything is worth doing here it is a copy review of those three lines
by someone weighing precision against readability. That is a judgement
call for the site's author, not a finding, and it is out of scope for a
no-build investigation.

---

## 5. What this finding does *not* refuse

Worth separating, so a future reader does not over-read the "no":

- **Storing `publicationDate` in the payload** is a different question
  and remains a live V13 item. As provenance inside the change record —
  where a build can assert that FY2024-25's enacted publication has not
  been silently re-dated — it is cheap and it is not decorative, because
  nothing renders it. **The refusal here is to the reader-facing label.**
- **Reading CDE's budget-period SACS submission** is a possible future
  layer with a real adoption event behind it. It is not this feature, and
  it would carry its own basis, its own gate and its own tier.
- **The one-line prose statement already on `about.html` and
  `index.html`** is correct and should stay. It is the honest version of
  this feature, and it already shipped.

---

## 6. What I did not do

- **I got §1.5 wrong on the first pass** and corrected it mid-
  investigation. `leginfo.legislature.ca.gov` is `Disallow: /`, and I
  concluded from that alone that the chapter number needed a manual
  exception. It does not: the Legislature's bulk host,
  `downloads.leginfo.legislature.ca.gov`, carries no exclusion. **A
  robots block on the HTML front end is not a block on the data**, and
  checking only the obvious host nearly produced a refusal resting on a
  false access claim. I made one request to the blocked host before
  reading its policy, and none after.
- **The §4.0 counts are bills, not chaptered amendments.** 244 is the
  number of distinct bills in one session whose *subject* names the
  Budget Act of 2023; most are introduced and never enacted. It is an
  upper bound on activity, not a count of amendments that took effect. A
  chaptered-only count would be the rigorous figure and I did not
  compute one — the qualitative point (two-year amendments, multi-chapter
  citation) does not depend on it, but the number should not be quoted
  as "244 amendments".
- I did not read the bill *text* members (`.lob`) that would let me date
  each amendment, so I cannot state how long a given Budget Act stays
  open.
- **My first draft claimed only the state page shows an adopted figure.
  That was false** — `schools.html`, `ccc.html` and `csu.html` all render
  a borrowed appropriation (§1.7). I found it by having the claim
  adversarially refuted, not by looking, and the same pass caught three
  further errors: the layer count was mis-sourced to
  `build_search_index.py` (which has ten entries and no compensation),
  the `meta.basis` tally was "eight of nine" when it is eight of ten with
  `deflator-data.js` also lacking one, and §1.2's keyword sweep omitted
  `appropriat` and so missed the Gann limit. **Four errors in one
  finding, all of the same kind: a claim of absence resting on a search I
  chose the terms for.**
- I did not open CDE's budget-period SACS submission to confirm it
  carries a board adoption date. §1.3's claim is only about the
  unaudited-actuals archive the site actually reads.
- The §4 restatement test covers six departments, not the full
  department list; it establishes that restatement happens and is
  material, not its statewide magnitude.
- I did not check whether any city or district publishes an adoption date
  on its *own* website. Thousands of separate sources with no common
  schema is not a layer this site could build, but the finding does not
  prove the fact is nowhere.

## Recommendation

**Don't ship.** Not an "adopted [date]" label, not a next-adoption-date
line, not an adopting-body field.

The honest one-line summary: **only one of eleven layers publishes a
figure anyone adopted; that layer's signing date is fixed within three
days by a constitutional deadline and is not a single date anyway; and
the site already carries the version of this feature that works, on the
one layer whose provenance actually varies.**
