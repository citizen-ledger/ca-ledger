# V14 finding — inflation adjustment: a nominal/real toggle

*Investigation date: 2026-07-19. The question: should the Ledger offer a
nominal/real toggle, and if so on what basis? This is the project's FIRST
feature that is a methodological CHOICE rather than reproduction of a
source's own published figure, so it was given the rigor of a data
layer. Investigation only; nothing was built. Every index value below
was fetched, every growth rate computed, and the scripts retained.*

**Recommendation: SHIP, with the deflator California statute names, on
DOF's own fiscal-year file — and label it, on the face, as the
Ledger's own methodological choice rather than as reproduction.**

Four decisions, each argued below:

| | recommendation |
|---|---|
| **Deflator** | The **Implicit Price Deflator for State and Local Government Purchases of Goods and Services**, national, as published in fiscal-year form by California's Department of Finance |
| **Base year** | **Fixed**, at the latest **complete actual** fiscal year; pinned, dated, and never a DOF forecast year |
| **Fiscal-year method** | **None of our own.** DOF publishes the index already averaged to California fiscal years — we adopt that file rather than convert anything ourselves |
| **Scope** | Multi-year trend views only. Excluded by arithmetic: percent-of-total units, the enacted-vs-actual difference, and every single-year layer |

---

## 0. The one number that decides whether this is worth doing

Over the local layers' eight-year window, **FY2016-17 → FY2023-24**,
using DOF's published fiscal-year deflator:

> **71 of 482 California cities — 14.7% — report rising expenditure in
> nominal dollars and falling expenditure in real dollars.** None go the
> other way.

For one city in seven, the site as it stands today reports the opposite
direction from the truth. Statewide, city expenditure is **+60.9%
nominal** and **+22.8% to +26.7% real** depending on index — inflation
accounts for more than half the apparent growth.

That is the case for the feature, and it is not close. The rest of this
finding is about whether the choice can be made defensibly.

---

## 1. Which deflator — and the discovery that reframes the question

### The project's usual move does not work here

The Ledger's standing principle is to adopt a source's own definition
rather than invent one: it strips UC's segments on UC's published lines,
uses CDE's own Current Expense of Education, reconciles to DOF's own
statewide total. Applied here, that principle **returns no answer**, and
this was verified rather than assumed:

- **DOF publishes a fifty-year spending series and never deflates it.**
  Chart A (General Fund, from 1976-77) and Chart B (all funds, from
  1982-83) were fetched and scanned: `constant` ×0, `inflation` ×0,
  `deflator` ×0, `CPI` ×0.
- **CDE's Current Expense workbook — the exact artifact this site
  consumes — has no constant-dollar column.** All 984×7 cells scanned:
  zero hits for inflation, deflator, constant or CPI.
- **The State Controller is an explicit pass-through**: "The financial
  information is posted as submitted by each local government."

All three sources behind the site's multi-year layers publish nominal
only. **There is no convention to adopt.** That is itself the finding,
and it is why this feature is a genuine methodological choice in a way
nothing else on the site has been.

### California law names three different indices, for three purposes

Verified by fetching the actual statutes:

| authority | index | note |
|---|---|---|
| **Art. XIII B §8(e)(1)** (Gann limit) and **Art. XVI §8** (Prop 98) | **California per capita personal income** | **Not a price index.** A nominal income growth rate the Constitution calls "cost of living" |
| **Art. XVI §22** (Prop 2 / BSA) | **California Consumer Price Index** | |
| **Education Code §42238.1(a)(2)** (K-12 COLA) | **"the Implicit Price Deflator for State and Local Government Purchases of Goods and Services for the United States … as reported by the Department of Finance"** | The only actual price deflator named in California statute. Current — amended 2018 |

**The per-capita-personal-income factor must be rejected as a deflator,
and the finding says so explicitly because it is the most quotable
"official California index."** It measures incomes, not prices. Using it
to deflate spending would be a category error with excellent legal
pedigree.

That leaves Education Code 42238.1 as the one place California statute
names a price deflator for government spending — and it names the
national IPD for state and local government purchases, and designates
DOF as its publisher.

### The LAO had this convention, and it has quietly lapsed

- **1999–2008, explicit and stable.** LAO's 2000 Analysis: *"This
  inflation adjustment relies upon using the Gross Domestic Product
  (GDP) implicit price deflator for state and local government purchases
  of goods and services. This GDP deflator is a good general measure of
  the price increases faced by state and local governments."*
- **LAO's 2006 Analysis is the cleanest evidence that California has
  deliberately never unified this**, naming three different indices for
  three programs — California CPI components for social services, the
  national GDP state-and-local deflator for K-12, and the SAL factor for
  trial courts.
- **Today the convention is not restated.** LAO's February 2026 Prop 98
  report publishes an *inflation-adjusted* per-pupil figure — "about
  $300 per student below the previous peak" — and names no index
  anywhere: `deflator` ×0, `constant dollar` ×0 across the whole PDF.
- And LAO argues against its own historical choice: the index is *"not a
  particularly good indicator of increases in school costs"* (2008), and
  separately that CPI understates government cost growth because state
  budgets concentrate in education, health care and human services.

So the recommendation rests on a **statutory** convention that LAO once
followed explicitly and now neither follows consistently nor disavows.
That is weaker than "UC's own segment lines" and the finding does not
pretend otherwise.

### How much the choice actually moves the picture — measured

Cumulative inflation over the local window, **FY2016-17 → FY2023-24**,
both from DOF's own fiscal-year files:

| index | cumulative |
|---|---|
| IPD, State & Local Government Purchases | **+31.0%** |
| California CPI (DOF's population-weighted construction) | **+30.4%** |

**0.6 percentage points apart over eight years.** And at the entity
level the choice is nearly immaterial: of 482 cities, **exactly one —
Loma Linda — has a real direction that differs between DOF's two
published indices** (IPD −0.2%, CPI +0.2%).

For contrast, on the national CPI-U series the spread is wider — CPI-U
US city average +30.7% against CPI-U California +34.4%, a 3.7-point
gap — and the government-purchases deflator sits nearer the California
CPI than the national one. *Government inflates differently* and
*California inflates faster* happen to point the same way.

**But the divergence is not uniform across windows.** On K-12's
three-year window the two DOF indices differ by **2.68 points** —
California CPI +6.36% against IPD +3.69% — which is roughly **42% of
the whole measured inflation**. On a short window the index choice can
flip the sign of a real trend. The finding's confidence that the choice
barely matters is specific to the eight-year local window and must not
be generalised.

**The honest summary: the feature is enormous and the choice is small —
except on short windows, where it is not.**

---

## 2. Fiscal versus calendar year — the question DOF has already answered

Ledger data is fiscal (1 July – 30 June); price indices are monthly or
calendar-annual. The candidate conventions are a twelve-month average, a
midpoint month, or the calendar year in which the fiscal year begins or
ends — and choosing among them is exactly the kind of unforced
methodological decision this project should avoid.

**It does not have to make one.** DOF publishes both candidate indices
*already averaged to California fiscal years*, as static files:

```
https://dof.ca.gov/media/docs/forecasting/economics/economic-indicators/
    inflation/Implicit-Price-Deflators-FY.xlsx    33,554 B   HTTP 200
    inflation/CPI-All-Item-FY.xlsx                58,401 B   HTTP 200
```

Sheet `Deflators_FY`, titled "NATIONAL DEFLATORS (2017=100)", column
`State and Local Index`, fiscal-year values from 1947-48. The CPI file
is headed "STATE FISCAL YEAR AVERAGES".

So the fiscal-year conversion is **a California agency's own published
method, applied to the index California statute names, by the department
that statute designates as its publisher.** That is as close to
reproduction as this feature can get, and it converts the most arbitrary
of the four decisions into no decision at all.

**Recommendation: adopt DOF's fiscal-year file wholesale. Do not
average, interpolate or convert anything.**

---

## 3. Base year

**Official practice is a fixed base expressed as a fiscal year.** OMB's
Historical Table 10.1 is subtitled *"(Fiscal Year 2017 = 1.000)"*, and
OMB rebased once in three budget cycles.

Two things must be said precisely, because loose writing on this topic
gets both wrong:

**The base year cannot change the direction a line moves.** Deflating to
a different base multiplies every point by the same constant. The shape
is invariant. Anyone claiming a base year was chosen to make a trend
look bad is mistaken, and the site should be able to say so flatly.

**But a fixed base does not mean fixed values.** BEA revises the index
annually; OMB restates its constant-dollar tables every year. Measured
across three OMB vintages at an unchanged FY2017 base, the FY2025 GDP
price index moved 1.2808 → 1.2856 (+0.375%). A "rebasing event" in
practice bundles an inert scale change with a real revision, and the
revision part *does* change shape.

**This interacts directly with the change record shipped in V13.** Real
figures would move when DOF republishes even though no nominal figure
moved — and V13's record is explicitly a record of *figures that moved*.
Publishing revised real figures into it without distinction would
corrupt the one surface designed to say what changed.

**Recommendation:** fixed base at the **latest complete actual** fiscal
year; the vendored index file **pinned and dated**; a republished index
treated as a deliberate, announced restatement rather than a silent
refresh; and derived real figures held outside the V13 change record, or
recorded in a separate class that names the index vintage.

### The forecast problem, which is specific and blocking

**DOF flags FY2025-26 through FY2029-30 as forecasts (`f/`) in the file
I fetched.** The state layer's newest year *is* FY2025-26.

Deflating it would mean publishing a real figure whose denominator is a
DOF *projection* — one that will be revised, changing a published real
figure while the nominal never moved.

**Recommendation: deflate only through the latest actual year.** Show
the forecast year nominal-only, and say why on the face. This is the
same discipline as refusing to publish an ungated figure.

---

## 4. Scope — mostly settled by arithmetic, not judgment

Three invariances cut the surface down without anyone exercising taste:

1. **Percent-of-total units are invariant under deflation.** A ratio of
   two same-year figures is unchanged when both are multiplied by the
   same deflator. The toggle must be **disabled, not merely inert**, in
   percent units — a control that provably does nothing reads as
   decoration and invites suspicion that it does something hidden.
2. **The enacted-versus-actual difference is invariant.** Both columns
   are the same year, so `(a·k − e·k)/(e·k) = (a−e)/e` exactly. Deflating
   changes the one number anyone reads by zero. **Exclude the Actuals
   view**, and say why where a reader would expect the control.
3. **Real per-capita is well-defined.** Deflation and division by
   population are independent scalings that commute, so "real per
   resident" is unambiguous. It is a standard construct and may be
   offered — but it stacks two adjustments and should say so.

**In scope:** the state trend and change views (through the latest
actual year), the city and county multi-year views, the K-12 multi-year
view — with the K-12 caveat of §1, since its three-year window is where
the index choice bites hardest.

**Out of scope:** CSU, CCC and UC — all single-year, so there is no
trend to deflate. Special districts are as-filed and unreconciled; the
layer already refuses per-resident figures and comparison, and adding a
second adjustment on top of unverified figures would dress up data the
site deliberately presents at a lower tier. **Recommend excluding it.**

---

## 5. Source access under SCOPE.md

Every route was tested, not assumed:

| route | keyless? | evidence |
|---|---|---|
| **DOF fiscal-year .xlsx** | **YES** | HTTP 200, 33,554 B and 58,401 B, no key, no bot-gate |
| BLS public API v1 | **unreliable** | Returned data on one attempt; on another returned `REQUEST_NOT_PROCESSED` — *"the daily threshold … allocated to the user with registration key  has been reached"*. The unregistered quota is a **shared pool**, exhaustible by strangers |
| BLS flat files | no | HTTP 403 at `download.bls.gov`, including with a contact User-Agent |
| BEA API | no | HTTP 200 with an empty body absent a `UserID` |
| FRED API | no | HTTP 400 without a key |
| FRED graph CSV | yes, but | HTTP 200 and real data, but an undocumented download endpoint, and series identity could not be read from it |

**This settles the choice on its own.** The recommended index is
available as a static file from a California state agency with no key,
no quota and no third party — and every alternative route is either
key-gated, bot-gated, or dependent on a shared quota a stranger can
exhaust. Vendor the file, pin it, date it, and record its digest, as the
project already does for MapLibre and the CSU cache.

**One risk to record:** DOF's file is vintage-coupled to BEA. BEA's
annual NIPA update lands each September; DOF republishes in
mid-November. There is a window each year in which DOF's file and BEA's
underlying data disagree for reasons unrelated to any error. Any
reconciliation test must pin the BEA vintage or tolerate that window.

---

## 6. Neutrality — the reputational crux

This is the first control on the site that a hostile reader could call
massaging the numbers. Three failure modes, and the rule each demands:

**A real chart is screenshotted without its label.** → The deflator,
base year and index vintage must be *inside the rendered view* — in the
basis strip where every layer already states its accounting basis — not
in a tooltip or a method page.

**A real figure is cited without saying which index.** → The citation
string must carry the index name, the base year, and the index file's
date, exactly as it already carries the accounting basis and generated
date. Same for the CSV header.

**A city that grew nominally is quoted as having shrunk.** → For the 71
cities where the direction differs, both figures must be reachable.
Nominal must remain the **default**; real must be opt-in; and no view
may render a real figure without the nominal being one interaction away.

**On presenting it as arithmetic rather than interpretation:** the
strongest available framing is that the site does not choose the index —
*California statute does*, in Education Code 42238.1, and DOF publishes
it. That is true and should be said. But the finding must not overstate
it: the statute names that index for the **K-12 COLA**, not for
deflating city expenditure, and the LAO has criticised it as a measure
of school costs. **The honest formulation is that the Ledger adopts the
only price deflator California statute names for government spending,
applies it unchanged in the fiscal-year form DOF publishes, and states
plainly that this is the Ledger's own methodological choice.**

That last clause matters. Every other figure on this site is
reproduction. This one is not, and the site's credibility rests on the
distinction being visible rather than blurred.

---

## 7. The case against shipping, put properly

The recommendation is only worth something if the opposing case was made:

1. **It is a category change.** The site's credibility rests on
   reproducing sources exactly, with gates that refuse to publish
   unverifiable figures. A deflator is the first number on the site that
   no source published and no gate can check.
2. **The right index depends on the question.** For "could this
   government buy as much as before", a government-purchases deflator.
   For "what did this cost households", a consumer index. The site
   cannot know which the reader means, and picking one answers a
   question the reader did not ask.
3. **The chosen index is imperfect and its own historical champion says
   so.** It is national, not Californian; LAO called it not a
   particularly good indicator of school costs.
4. **On short windows the choice is material** — 42% of measured
   inflation on K-12's three-year window.
5. **It makes published figures revisable for a new reason.** Real
   figures move when the index is republished, which complicates the
   reproducibility and change-record story.

**Why ship anyway:** because the status quo is not neutral. Publishing
only nominal figures is itself a methodological choice — one that
reports the wrong direction for one California city in seven, and
overstates statewide city growth by more than a factor of two. The
question is not whether to make a choice; it is whether to make one
visibly, with the index named and the nominal always available, or
silently by omission. Points 1–5 are arguments for **labelling and
constraining** the feature, which the recommendation does. They are not
arguments for continuing to publish figures that mislead about direction
in 14.7% of cases.

---

## 8. What this commits the project to

Stated plainly, because it is ongoing:

- **A vendored, pinned, dated index file**, refreshed deliberately —
  not a live fetch whose value can change under a published figure.
- **A republication is a restatement.** When DOF updates the file, real
  figures move while nominal figures do not. That must be announced,
  and kept out of (or distinguished within) the V13 change record.
- **The forecast boundary must be maintained.** Each year, the latest
  actual year advances and one more year becomes deflatable. That is a
  per-refresh judgement about which years are actual — small, but real.
- **The label must survive.** The moment a real figure appears anywhere
  without its index named, the feature has become the thing its critics
  would call it.

---

## 9. Not measured

- **Whether CDE states a deflator convention in prose.** Its narrative
  pages are behind Radware bot-detection (HTTP 302 to
  `validate.perfdrive.com`); the CAPTCHA was not bypassed. The workbook
  this site actually consumes was read and has no constant-dollar
  column.
- **A post-2020 LAO document restating the IPD convention.** The
  explicit statements are 1999–2008. Their absence from current reports
  was measured; whether LAO has stated a convention elsewhere recently
  was not established.
- **The population weights in DOF's California CPI.** The component
  metro sets and the regime changes are published in the file's own
  footnotes; the weights are not.
- **Whether any US state transparency site offers a real-dollar
  toggle.** Federal precedent exists — Treasury's own fiscal-data
  repository logged "chart not adjusted for inflation" as a defect and
  shipped a toggle — but no state-level analog was confirmed.
- **The site's own real-dollar figures.** Nothing was built; every
  figure here was computed in scratch scripts, not shipped.
