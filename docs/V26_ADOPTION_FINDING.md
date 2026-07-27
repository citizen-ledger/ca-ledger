# V26 finding: adoption provenance — who approved this, and when

*Investigated 2026-07-27. Every layer's source probed directly: the
eBudget API live, the SACS `.mdb` archives and SCO Financial Transactions
Report workbooks from the local cache, plus the legislature's access
policy. No build.*

## Recommendation, up front

**(c) Don't ship — merely decorative, which the brief admits as a
reason.**

Two findings carry it, and they are independent:

**First, the adoption date exists on exactly one layer of eleven.** Every
other layer publishes an *actual* — a year-end accounting record of money
already spent. Nobody adopts an actual. On those layers an adoption date
is not unavailable, it is a **category error**.

**Second, on the one layer where it does exist, it does not vary.** Nine
published Budget Acts were signed on **June 26, 27 or 28** — six of nine
on June 27. The site already tells readers the budget is "fixed when each
year's Budget Act is signed… typically signed in late June." The proposed
feature would replace *typically late June* with *June 27*, nine times.

| | |
|---|---|
| layers publishing an **adopted** figure | **1 of 11** (the state page) |
| adoption fields in the state source | **1** — a prose string |
| adopting-body field in any source | **0** |
| range of nine Budget Act signing dates | **3 days** |
| SACS columns matching date/adopt/approve/board | **0 of 33**, across 4 vintages |
| SCO FTR columns searched, adoption dates found | **2,729 / 0** |

And the sharpest way to put it: **the date is nearly constant where it is
published, and unpublished everywhere it would actually vary.**

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

Not one adoption field, and — worth noting on its own — **not one
occurrence of the word "budget" anywhere in 27,916 column names.** The
FTR, collected under Government Code §12463, is a report of financial
transactions that occurred. There is no budget form in it to date.

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

### 1.4 Higher education — all three publish actuals

CCC is modified-accrual CCFS-311 spending; CSU and UC are audited GAAP
accrual. None is an adopted figure, and none of the three sources
carries a board or Regents approval date in the fields the pipeline
reads.

### 1.5 The Budget Act's chapter number — behind a total robots exclusion

The one thing that would make this a real citation — *Budget Act of 2024
(Chapter 22, Statutes of 2024)* — lives at `leginfo.legislature.ca.gov`,
whose `robots.txt` is:

```
User-agent: *
Disallow: /
```

**A blanket exclusion of all automated retrieval.** Adding the chapter
number would require a **third** manual-cache exception, after CSU and
the compensation layer. `docs/OPEN.md` pattern 2m already records the
rule: *two exceptions are a limit; two one-offs are a broken claim.*
Spending the third on a decorative field would be a poor trade.

### 1.6 The per-layer table

| layer | basis published | adopted by anyone? |
|---|---|---|
| **State** | Enacted appropriations · Budgetary-Legal | **yes** |
| Cities | Reported actuals | no |
| Counties | Reported actuals | no |
| K-12 districts | Unaudited actuals · SACS | no |
| County offices of ed. | Unaudited actuals · SACS | no |
| Charter schools | Unaudited actuals · SACS / Alt Form | no |
| Special districts | AS FILED · UNRECONCILED | no |
| Community colleges | Modified accrual · CCFS-311 | no |
| CSU | Audited GAAP / GASB | no |
| UC | Audited GAAP / GASB | no |
| Compensation | Reported positions, as filed | no |

**One of eleven.** The eleven are the layer entries in
`pipeline/build_search_index.py`; they ship as **nine** payload files
(K-12 districts, county offices and charters share `school-data.js`).
Counted either way the answer is one — and measured directly, **eight of
the nine payloads carry a `meta.basis` string, every one of which
describes a retrospective accounting record and none of which describes
an appropriation.** The ninth, `data.js`, is the state layer and is the
exception in both senses: it has no `meta.basis`, and it is the one that
publishes an adopted figure.

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

**The brief's trap is real in the source, and the site is already on the
right side of it.** This is a genuine acquittal, not a manufactured
problem.

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

- I did not scrape `leginfo`. Its `robots.txt` excludes all automated
  retrieval; I read the policy, made one request before reading it, and
  stopped. The chapter-number question is therefore answered on access
  grounds, not by measurement of the data behind it.
- I did not count how many bills amend a Budget Act in a typical year.
  That would sharpen §4, but §4 is already resolved in the site's favour
  by the `byTotDols` / `pit` finding, so the count would not change the
  recommendation.
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
figure anyone adopted; its adoption date is fixed within three days by a
constitutional deadline; and the site already says so in a sentence that
is more informative than the date would be.**
