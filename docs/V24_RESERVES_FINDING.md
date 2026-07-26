# V24 finding: reserves and fund balances — what can be published honestly

*Investigated 2026-07-25/26. Four layers measured, three traps tested.
No build.*

## Recommendation, up front

**Ship nothing — no total, no five-way breakdown, no unassigned-only
figure, no months-of-spending ratio, and no separate reserves page.**

One thing does ship, and it is not a reserve presentation: a refusal
sentence on the layer pages, in the same dress as the existing "NO
PER-RESIDENT FIGURE" and "NO COMPARISON, NO TOTALS" blocks.

| layer | data | control | recommendation |
|---|---|---|---|
| cities | full GASB 54, 482 entities | none published | **don't ship** |
| counties | full GASB 54, 57 entities | none published | **don't ship** |
| special districts | full GASB 54, 3,345 entities | none published | **don't ship** |
| K-12 | full GASB 54 as SACS objects | county/statewide only | **don't ship** |
| state (SFEU/BSA) | published, but a projection | — | **don't ship** |
| CCC / CSU / UC | see §2.5 | — | **don't ship** |

The data is good. On three layers the classification is complete and the
filer's arithmetic is perfect. **The refusal is a design verdict, and it
is the same one V22 reached about debt**, reached again by measurement
rather than by analogy.

---

## 1. The settling measurement

The brief asked for the equivalent of V22's "0.99×" before anything
else. Here it is, measured against each layer's own published spending
on this site:

| layer | median | p75 | p90 | p99 | max | share holding >1 year |
|---|---|---|---|---|---|---|
| **cities** | 1.25× | 1.72× | 2.48× | 4.62× | 8.0× | **69.2%** (333/481) |
| **special districts** | 2.23× | 8.52× | 38.74× | **566×** | — | **68.8%** (1,880/2,731) |
| **K-12** (all funds ÷ Current Expense) | 0.93× | 1.28× | 1.80× | 3.72× | 7.8× | **45.0%** (419/932) |

**Two different failure modes, both disqualifying.**

For **K-12** the reserve and the spending figure are *the same size*:
statewide, 932 districts hold **$97,009,563,139** of ending fund balance
against the **$101,236,938,810** of Current Expense of Education the
site publishes for those same districts — **0.958×**. That is V22's city
debt case almost exactly ($114.363B against $115.830B, 0.99×), which
V22 called "numerically indistinguishable" and treated as decisive.

For **special districts** the opposite: the ratio is so dispersed that a
reserve can be *hundreds of times* the spending figure beside it. LA
County Regional Park and Open Space District holds **$790,514,000**
against **$35,766,000** of annual spending — 22.1×. On a record whose
only other number is "FY 2023-24 · $35,766,000", a second dollar figure
22 times larger carries nothing that says it is a different kind of
quantity.

A figure that is either indistinguishable from the flow or absurdly
larger than it, in the same unit, on a page whose entire vocabulary is
annual, is the V22 problem in both directions at once.

---

## 2. What exists, per layer

### 2.1 Cities, counties, special districts (SCO)

The Financial Transactions Report workbooks carry a full governmental
balance sheet with the complete GASB 54 breakdown — measured directly,
FY2024:

| layer | entities | total | nonspendable | restricted | committed | assigned | **unassigned** |
|---|---|---|---|---|---|---|---|
| cities | 482 | $78.52B | 2.6% | 52.1% | 14.6% | 14.8% | **16.0%** |
| counties | 57 | $61.93B | 2.0% | 47.3% | 12.2% | 15.7% | **22.8%** |
| special districts | 3,345 | $28.79B | 1.8% | 69.6% | 5.0% | 8.9% | **14.7%** |

Coverage is strong. For special districts 2,924 of 3,345 (87.4%) carry a
usable split; the 94 with only a total all report a genuine **$0**; and
**327 report the literal string `NULL`** — not-published, distinguishable
from zero exactly as the district expenditure layer already handles.
Cities and counties have **zero** `NULL` totals and **zero** rows where
the five classes fail to sum to the printed total.

### 2.2 K-12 (SACS)

The GASB 54 vocabulary is carried in full as object codes — 9711/9712/
9713/9719 nonspendable, 9740 restricted, 9750+9760 committed, 9780
assigned, 9789+9790 unassigned — populated in all nine years
FY2016-17…FY2024-25, the same window the K-12 layers already ship.
Statewide FY2024-25, of **$105.763B**: restricted 50.5%, assigned 22.1%,
**unassigned 16.3%**, committed 7.7%, nonspendable 0.4%, net position
3.1%.

Two qualifications. Object **979Z is one code covering two kinds of
quantity** — 529 of 10,139 FY2024-25 fund-keys carry **$3.230B** of *net
position* (9796 Net Investment in Capital Assets, 9797 Restricted Net
Position) rather than fund balance, and net investment in capital assets
is school buildings, not money. And the split does not survive the move
to charters: the Alternative Form uses different codes and **546 of 574
filers (95.1%) report net position only**.

### 2.3 The gate — none exists where a reader looks

**K-12 has a real control at the wrong scope.** Raw UserGL 97xx
recomputed against CDE's own `UserGL_Totals`: **57,821 control cells
across nine years, zero disagreements, worst residual $0.000237**. But
`UserGL_Totals` carries **zero district-scope rows** in all nine years,
and CDE's Current Expense workbook — which gates district *expenditure*
to the cent — has **no fund balance column**. The district row a reader
actually sees has no control. This is V21 §2.4's split tier again.

**The SCO layers have no control at all.** The Socrata catalog is 170
views; a regex for `balance|reserve|fund bal|net position|equity` over
every view name returns **0 hits**. SCO's Special District Annual Report
page states that since 2014 it publishes open data instead of a report.

**What looks like a control is the filer's own arithmetic.** The five
classes sum to the printed total in **3,345 of 3,345** special-district
rows, and in every city and county row. That is self-reconciliation —
per V22 §2i, a 100% pass deserves more suspicion, not less.

### 2.4 The state — a projection, not an actual

The SFEU and BSA are published, but the figures in the enacted budget
are **projections at the time of enactment**, not year-end actuals. The
site already refuses to publish forecasts as facts — that is the whole
basis of the Schedule 8 actuals discipline (V21 §2.2), where the
Estimated columns had been wrong by −18.7%. A reserve figure that is a
forecast is the same object under a different name.

### 2.5 CCC, CSU, UC

CCC's CCFS-311 Tables III.1/III.2 do carry fund balance, but inherit
every problem above. CSU and UC publish **net position**, which is not
the same kind of object as governmental fund balance — full accrual
versus modified accrual — and includes capital assets. Putting them on
one page with the others would compare different things.

---

## 3. The interpretation trap

The citizen question is *"we're told there's no money — is there?"* A
total fund balance figure answers it **wrongly**, and the size of the
error is measured:

| layer | total | unassigned | overstatement |
|---|---|---|---|
| cities | $78.52B | $12.57B | **6.2×** |
| counties | $61.93B | $14.13B | **4.4×** |
| special districts | $28.79B | $4.24B | **6.8×** |
| K-12 | $105.76B | $17.24B | **6.1×** |

Most fund balance is legally unavailable: bond proceeds that may only
build the thing they were sold for, grant money with a purpose,
ratepayer reserves, debt service set aside by covenant.

**And the honest-looking alternatives fail too.**

- **The five-way breakdown with no total** does not help: five dollar
  figures in a column add, and the largest class fails on its own —
  restricted alone exceeds a full year of governmental spending for
  **940 of 1,502 special districts (62.6%)**.
- **Unassigned only** fails twice. It is empty for most filers —
  **1,690 of 3,345 special-district rows (50.5%)** report zero or blank,
  122 report a negative — and where positive it is *still* a stock that
  outruns the flow: it exceeds a year of spending for **52.7%** of the
  districts that report it. For cities the unassigned median is 0.35×,
  which is the one figure in this finding that behaves; but it is
  unavailable or negative for half the special-district universe, so it
  cannot be the site's uniform answer.

---

## 4. Months of spending — the presentation that nearly worked

This is the framing public-finance professionals actually use, and it is
the only one that converts a stock into flow units. **It does not
survive**, for three measured reasons — and one claimed reason that I
checked and found false, recorded here so it is not repeated.

**It fails because the denominator is not determinate.** Computing
months from the workbook's own Total Expenditures versus the
governmental figure this site publishes for the same entity-year gives a
different answer for **110 of 2,705 entities (4.1%)**, and differs by
more than 2× for 64. Templeton Community Services District reads **28.8
months** on one denominator and **28,094 months** on the other. Both are
published by the same publisher for the same entity and year.

**It fails because the choice of class changes the answer, and every
choice is defensible.** Five variants a professional would recognise
give statewide medians of **27.2, 2.1, 13.0, 13.7 and 27.8 months**. Per
entity the spread across the five is p90 **4.12×**, p99 **60.88×**. LA
Metro reads **22.1 months or 0.8 months** depending which is chosen.

**It fails because it is unstable when the reserve is not.** Year over
year the months figure moves by more than 50% for **1,067 of 2,605
entities (41.0%)**. For 278 it moves more than 2× while the balance
itself moved less than 20% — the ratio is reporting the denominator's
lumpiness, not the entity's position. Colorado River JPA: **74.4 →
6,792.0 months** on a balance that went $437,156 → $436,385.

And the tail is not a rounding artifact: median 27.2 months, p90 474.1,
p99 6,882.3, **max 151,767 months** — County Service Area No. 97 (Kern),
$50,589 of balance against $4 of expenditure, **12,647 years of
spending**. A statistic whose honest rendering includes "12,647 years"
is not converting a stock into flow units; it is dividing by something
that is sometimes not a rate at all.

This is the compensation layer's no-averages rule (V23a §4) in a new
place: **a computed statistic the site would itself be producing and
could not defend.**

> ### A claim I checked and had to reject
>
> The investigation initially reported that **the numerator is not
> determinate either** — that SCO states total governmental fund balance
> twice in one workbook (sheet 22's balance sheet and sheet 16's
> operating statement) and contradicts itself in 120 of 2,997
> entity-years, 14 of them in sign, with Cosumnes CSD at
> +$143,167,612 on one sheet and −$49,631,082 on the other.
>
> **That is wrong, and the error was ours.** Sheet 22 carries exactly one
> row per entity-year (6,708 rows / 6,708 entity-years). Sheet 16 carries
> **7,158 rows over 6,691 entity-years — 293 entities file 2 to 7 rows**.
> Cosumnes is entity 3977 with four rows: $36,530,651 + $103,879,586 +
> $52,388,457 − $49,631,082 = **$143,167,612**, exactly sheet 22's
> figure. The original comparison took one row against the entity total.
>
> Keyed on Entity ID and summed per entity, the two statements agree in
> **6,019 of 6,019 comparable entity-years, zero disagreements, zero
> sign flips**. The numerator is determinate. The other three reasons
> above stand on their own and are sufficient.
>
> This is the per-row-versus-per-entity hazard this project keeps
> meeting, and it is recorded because the retraction is more useful than
> the claim would have been.

---

## 5. The other traps

**GASB 54 (FY2010-11) does not affect this site.** It replaced the
reserved/unreserved/designated scheme entirely, so a series crossing it
measures two things — but the site's windows begin FY2016-17, five years
after. **This is a non-issue here, and saying so is more useful than
carrying a warning about a break the data never reaches.**

**Negative balances are real and must never render as zero.** 95 special
districts report a negative total and 122 a negative unassigned; one
city reports a negative total. A deficit is a genuine and newsworthy
state, and it is the single most reader-relevant fact in this dataset —
which is an argument for a *targeted* future treatment, not for a total.

**Enterprise fund balance is ratepayer money**, and the site already
separates enterprise from governmental everywhere else. Any reserve
figure that silently included it would break that discipline.

**Reported-zero versus not-reported** transfers cleanly: 327
special-district `NULL` totals against 94 genuine zeros.

---

## 6. What I did not do

- I did not test cities and counties for the months-of-spending
  instability in §4; those measurements are special-district only. The
  §1 ratio and §3 composition figures are measured for all three.
- The state SFEU/BSA figures were not independently re-fetched from
  eBudget; the projection-versus-actual point rests on the published
  documents' own framing.
- I did not measure whether a *negative-balance-only* presentation could
  work. It is the one framing this finding does not dispose of, and §5
  says why it might deserve its own investigation.

## Recommendation

**Ship nothing.** The stock/flow collision in §1 disposes of every layer
before any question of data quality, and the interpretation trap in §3
disposes of every total. Months of spending was the one framing that
converted the units, and it fails on three independent measurements.

If a refusal sentence ships, it should say what the site knows rather
than only what it declines:

> This site publishes flows — money collected and spent during a year.
> A reserve is a position: what a government holds on one date. The two
> are never comparable and never add. The Ledger publishes no reserve
> figure, because most of what is held is legally restricted to a
> purpose — for California's special districts, 69.6% of it — and a
> total would answer "is there money?" with a number roughly six times
> larger than the part that is actually unrestricted.
