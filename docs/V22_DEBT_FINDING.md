# V22 finding: debt and long-term obligations — what can be published honestly

*Investigated 2026-07-25. Five sources probed live, four hard problems
answered. No build.*

## Recommendation, up front

**Ship nothing. All five sources: (c) don't ship.**

| source | recommendation | why, in one line |
|---|---|---|
| CDIAC | **don't ship** | the complete product is a flow; the stock product covers 54% of cities and starts in 2017 |
| SCO city / county / district | **don't ship** | no control at any layer, and "Principal Payable" is par for some filers and carrying value for others |
| State GO / lease revenue | **don't ship** | the data is good and the gate mostly holds; a $71.9B balance cannot sit near a $321.1B annual flow |
| CalPERS / CalSTRS | **don't ship** | the same employer on the same date shows nine liabilities spanning 5.77×, two of them at the *same* discount rate |
| K-12 / CCC bonds | **don't ship** | the debt stock is not in the data the pipeline reads — SACS object 9661 has zero rows in all nine years |

And the four hard problems: **each one independently blocks shipping.**
Per-resident debt and overlapping debt are refused outright, not
labelled.

This is not a data-quality verdict. On three of the five sources the
data is better than expected and at least one gate reproduces a
published control **exactly to the cent**. The refusal is a design
verdict, and it is the same one in every case.

---

## 1. The central design problem, resolved before anything else

Every figure on this site is a **flow**: money collected or spent during
a fiscal year. Debt is a **stock**: what is owed as of an instant. They
are different kinds of quantity. They share a unit — dollars — and
nothing else.

The site has already ruled on a weaker version of this. V21 §4 refused
to compute a surplus or deficit because revenue and spending, though
both flows, are measured on different scopes. A stock beside a flow is
worse: not a different scope, a different kind.

**The measurement that settles it.** California cities filed
**$114,363,062,810** of outstanding debt for FY2024, against published
city total expenditures of **$115,830,469,221** in the same year. The
stock is **0.99×** the flow. On a page whose entire vocabulary is annual
spending, those two numbers are *numerically indistinguishable*. A
reader has no way to see that one is a rate and one is a level.

The state case is the same shape: $71.87B of GO outstanding against the
site's $321.051B state total reads as "22% of one year's spending",
which is a sentence with no meaning.

There is no rendering discipline that fixes this — no label, no colour,
no separate column. **The only safe treatment is a separate page with
its own vocabulary, and none of the five sources earns one.**

---

## 2. The sources, measured

### 2.1 CDIAC — two products, and the complete one is the wrong kind

CDIAC is reachable and honest: DebtWatch's unauthenticated JSON API,
`robots.txt` allows everything, bulk download works in one call
(56,783,584 bytes / 76,703 rows for the issuance dataset), and — unlike
cccco.edu — **it does not soft-404**: a nonsense dataset id returns a
real HTTP 404 with 0 bytes.

**The issuance dataset is a flow, and a balance cannot be derived from
it.** 76,703 records, CY1984–CY2026, $2.527T of original principal.
Summing it would be wrong three times over, each measured:

- **refunding** — the Refunding Amount field totals **$830.1B, 33.2%**
  of sold principal, so every refunded dollar is in the file at least
  twice
- **amortisation** — $22.355B of scheduled principal was repaid in
  RY2025 alone; a sum of issuances never subtracts a payment
- **defeasance** — $30.9B refunded-or-refinanced in RY2025, legally gone
  but still in the file at par

**The stock product exists and is truncated.** The SB 1029 Annual Debt
Transparency Report carries real outstanding principal, RY2017–RY2025 —
but only for debt whose Report of Final Sale was filed on or after
2017-01-21. Measured consequence: **22,276 issues sold before that date,
carrying $823.7B of original principal and maturing after 2025-06-30,
appear in no outstanding figure CDIAC publishes.** Coverage against this
site's own rosters is **261 of 482 cities (54.1%)** and **36 of 57
counties (63.2%)**.

**No usable control.** The ADTR issuer-group report reproduces the row
data to the cent in 9 of 9 years — but it is CDIAC's own second view of
one database, so the gate certifies only that DebtWatch agrees with
DebtWatch. CDIAC's flagship annual report publishes **no outstanding
total at all**: full-text extraction of all 39 pages finds two
occurrences of "outstanding", both in prose.

### 2.2 SCO — the strongest data, and a column that means two things

This is where I was initially most optimistic, and where I was wrong in
an instructive way.

The Financial Transactions Report workbooks carry a genuine per-issue
stock — sheet `17 CIX_LT_DEBT`, 32 columns, with an **Entity ID the
Socrata feed does not expose**. FY2024 outstanding: cities
**$114,363,062,810**, counties **$19,143,366,003**, special districts
**$129,338,895,959**.

**I tested the roll-forward identity myself and got 99.96%.** Beginning
+ adjustment + issued + premium at issuance − paid − defeased −
amortized = end. Current portion + noncurrent portion = end holds at
100.00%.

**That measurement is real and it is uninformative.** Testing two bases
separately shows why:

| | par basis only | carrying basis only | both | neither |
|---|---|---|---|---|
| cities (4,371 issue-years) | 0 | **1,893 (43.3%)** | 2,478 | 0 |
| counties (642) | 0 | 219 (34.1%) | 423 | 0 |
| districts (5,100) | 0 | 2,370 (46.5%) | 2,727 | 3 |

On **43.3% of city issues the column labelled "Principal Payable" is the
carrying amount including unamortized bond premium, not par principal**.
The remaining 56.7% satisfy both identities because they have no premium
activity — so they cannot be classified either way. Berkeley's ACFR
confirms it directly: SCO prints $212,975,137 where the ACFR shows par
$202,670K + premium $10,305K = $212,975K.

This is **docs/OPEN.md 2a — "conservation cannot see classification" —
one level worse**. The arithmetic is immaculate on essentially every
row while the unit is not the same unit twice. An as-filed label does
not fix a column that means two different things, and my 99.96% proved
the filer's addition, not the object.

Three further blocks, each sufficient:

- **No control exists at any layer.** The full SCO catalog is 170 views;
  a regex for `debt|liabilit|outstanding|bond|indebted` over every view
  name returns 19 hits, all of them Net Pension or Net OPEB.
- **The enterprise separation V21 §3.1 requires cannot be made.** `Fund
  Type` is the literal string `NULL` on **621 of 2,209 city bonded-debt
  rows (28.1%), $7,351,540,709 = 7.3% of the dollars.**
- **Attribution is broken at the district layer.** **409 of 959 district
  bonded-debt filers (42.6%) are financing or joint-powers authorities
  holding $41.97B of $117.65B (35.7%)** — "City of Santa Ana Public
  Financing Authority" files as a special district while the sponsor's
  ACFR carries the same debt as a blended component unit. No field says
  whose debt it is.

### 2.3 State GO and lease revenue — good data, refused anyway

Three distinct objects, all in dollars, all in two documents:

- **stock** — DOF Schedule 11 at the 2025 Budget Act, as of 2025-06-30:
  GO authorized $182,247,176K, unissued $42,272,576K, **outstanding
  $71,872,170K**; STO's Debt Affordability Report adds lease-revenue
  ($8.90B) that Schedule 11 excludes, for a printed **$81.67B**
- **flow** — debt service, which **the site already publishes**: summed
  from BS_SCH9, FY2023-24 actual **$6,154,330K**
- **neither** — DAR Appendix B, future debt service *requirements* on
  bonds already sold, **$107,656,799,914.88** — a projection

A real cross-publisher control exists (Schedule 11 vs DAR Appendix A)
and mostly holds, **for GO only, not lease-revenue**. Authorized-but-
unissued is a fourth object again: $42.3B that is not owed.

The refusal is §1, plus one thing worth recording: **the site's own
state page already contains $6,798,136K of GO debt service inside its
$321.051B total (2.118%), but displays only item 9600 at $81.450M.** The
overlap the brief anticipated is real and is *understated* on the page
today.

### 2.4 CalPERS / CalSTRS — the number is not determinate

The brief asked whether the site could publish the source's own figure
at the source's own stated assumptions, never recomputing. **It cannot,
and the reason is sharper than the discount-rate problem as usually
stated.**

CalSTRS STRP net pension liability at 2024-06-30, $M, from the Milliman
GASB 67/68 report:

| discount rate | 4.10% | 6.10% | **7.10% (stated)** | 8.10% | 10.10% |
|---|---|---|---|---|---|
| net pension liability | 259,269 | 119,461 | **67,163** | 23,492 | **(44,324)** |

The GASB-required ±1% band alone spans **$95,969M — 143% of the stated
figure**. Two CalPERS plans **change sign inside that band**: JRF II is
an asset of $(134,164)K at 6.9% and a liability of $153,650K at −1%.

**The single most damaging measurement is one employer on one date.**
City of Dublin, CalPERS ID 6598539431, 2024-06-30 — nine liabilities,
eight of them printed by CalPERS in the same 36-page report:

| basis | rate | liability |
|---|---|---|
| termination | 3.61% | $75,431,943 |
| low-default-risk (ASOP 4) | 5.35% | $47,539,702 |
| funding, real return −1% | **5.80%** | **$39,799,657** |
| funding, price inflation −1% | **5.80%** | **$28,928,317** |
| headline funding UAL | 6.80% | $25,062,184 |
| GASB 68 accounting | 6.90% | $22,650,689 |
| funding, real return +1% | **7.80%** | **$13,062,825** |
| funding, inflation +1% | **7.80%** | **$17,504,624** |

**Max/min = 5.77×. And two different liabilities are printed at the same
5.80% (37.6% apart), two more at the same 7.80%.** So the proposed
mitigation — show the discount rate beside the figure — **does not make
the number determinate**. The rate alone does not identify the
measurement. There is no single sentence that makes a chosen one of
these nine the honest one.

The only per-employer *dollars* either system publishes are **flows**
(employer contributions), which this site's spending layer already
carries.

### 2.5 K-12 and community college bonds — the stock is simply absent

The most clear-cut of the five. **SACS carries no debt stock at all**:

- object **9661 "General Obligation Bond Payable" is defined in the
  Object table and has ZERO rows in `UserGL` in all nine years**
  (1617..2425), as do 9662 and 9666; 9661 is absent from
  `UserGL_Totals` (237 distinct objects)
- the long-term-debt objects that *are* populated (9660, 9667–9669)
  occur only in Funds 62/63/67 — proprietary funds under full accrual,
  ~$3.66B in FY2024-25, **none of it district GO bonds**
- Fund 97 "(Obsolete) General Long-Term Debt Account Group" has zero rows

**Fund 51 is the debt service and the levy, not the debt.** FY2024-25 it
carries $7.75B of voted-indebtedness levies and $3.84B of bond
redemptions — the money set aside to pay bonds, not the bonds.

CDIAC publishes a K-12 outstanding figure by issuer group ($68.9B
RY2024), but it inherits the 2017 truncation in §2.1 and joins to
districts only by name.

---

## 3. The hard problems

### 3.1 Debt service vs debt outstanding — blocks

The site publishes debt service today, on several layers. It is the
annual payment; this would be the balance. **They must never appear on
the same page, table, chart or CSV.**

The reason they cannot be reconciled for a reader is that the two flows
that would connect the stock to the flow are **not available**: new
borrowing is absent from the site's sources entirely, and principal and
interest are not separable in the site's existing expenditure data —
only principal repayment reduces the stock.

### 3.2 Overlapping debt — blocks

The table exists. Three real California ACFRs carry "Direct and
Overlapping Governmental Activities Debt", apportioned by assessed-
valuation share. It is published **as a PDF page per entity per year**,
never machine-readable at scale, and the tables state their own limits.

Apportioning by assessed valuation is a defensible convention and not a
measurement — it answers "what share of the overlapping government's
tax base is inside this city", not "what does this city owe".

### 3.3 Per-resident debt — blocks, and the gate is the danger

**The data clears the bar.** Summing ADTR `PrincipalOutstandingEndPeriod`
over 9,876 RY2025 filings gives **$450,630,924,679.19** against the
published statewide figure of **$450,630,924,679.19** — residual
**$0.00**, 0 join failures, nine years deep. If per-resident debt were a
data problem it would already be shippable.

**It is not a data problem.** One address in the City of Los Angeles
sits inside **twelve** debt-issuing governments. ADTR RY2025 outstanding
÷ the 3,814,318 population the city filed with the Controller:

| scope | per resident |
|---|---|
| city, governmental issuers only | $1,724 |
| + city enterprise (DWP, Airports, Harbor) | $8,683 |
| + overlapping local (LAUSD, LACCD, Metro, MWD, …) | $15,254 |
| + State of California | $29,955 |

**Every one is correct. They differ by 17.1×.** Nothing in the data says
which is "the" figure — that is an editorial choice wearing a decimal
point.

And the scale error is the point: **LA's FY2023-24 governmental spending
is $3,152 per resident. The stacked debt figure is $29,955 — 9.5×
larger, in the same unit, on the same page**, for a thing that was never
spent in any year.

Three further reasons, each independent: **86.2% of special-district
debt is revenue bonds** repaid by ratepayers who are not the resident
population (5.8% is GO); special districts **have no resident
denominator at all**, which this site already refuses by design; and for
pension liability it would divide an actuarial estimate at a contested
rate into a per-person bill.

### 3.4 Structural breaks and conduit debt — blocks

**GASB 68** (FY2015) moved net pension liability onto the face of the
balance sheet; **GASB 75** did the same for OPEB (FY2018); **GASB 87**
(leases) and **GASB 96** (subscription IT) both *add* liabilities that
were previously off-balance-sheet. A liability series crossing those
years is not measuring one thing, and the site's window crosses all
four.

**Conduit debt** — issued by an agency on behalf of a private party — is
not the issuing government's obligation. The site already excludes
conduit financing from expenditures via `classify()`'s `cf` bucket. In
the debt sources it is **not reliably separable**, which is the whole
problem: publishing it would attribute private obligations to
government.

---

## 4. If this is ever revisited

The one candidate that is not disposed of by §1 is **CDIAC principal
sold in a year — a flow, on its own page, conduit-excluded, tier (b)
as-filed**, because no control total exists for it either. That is a
different product from the one this brief asked about, and it is not
recommended here.

Two things a future investigation should not re-derive:

- the only gate-eligible target found anywhere is the CDIAC annual
  report's CY2015–CY2025 Total Principal table — **statewide only, a
  flow, and it fails this site's own 0.1% tolerance in 3 of 11 years**
  against the live API, on vintage drift
- SCO's debt schema is **stable across vintages** (sheets 17–21
  identical FY2021-22 and FY2023-24), so the obstacle there is the
  filer-dependent basis in §2.2, not schema drift

## 5. What I did not do

- I did not open every California ACFR; three were read in full for the
  overlapping-debt table.
- I did not test CDIAC's ADTR name-join against this site's rosters
  beyond cities and counties.
- The Dublin figures are eight printed values plus one derived from
  CalPERS' own published allocation factors; the derivation is stated
  rather than presented as printed.
- I did not attempt to determine whether the 56.7% of SCO issue-years
  that satisfy both bases could be classified by some other field. If a
  future investigation finds one, the §2.2 objection weakens but the §1
  objection does not.

## Recommendation

**Ship nothing.** The stock/flow separation in §1 disposes of every
source on its own, before any question of data quality. Where the data
is strong — the state's Schedule 11, CDIAC's ADTR reconciling to the
cent — that strength is precisely what would make a misleading figure
credible.

If the site ever publishes anything from this territory, §3.3's sentence
belongs on its face:

> This site publishes flows — money collected and spent during a year.
> Debt is a stock: what is owed as of a date. The two are never
> comparable and never add. The Ledger publishes no per-resident debt
> figure for any government, and no debt total for any layer.
