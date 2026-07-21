# V15 — Historical depth: how far back each layer honestly reaches

**Status:** investigation only. Nothing built. No pipeline changed.
**Date:** 2026-07-20.
**Question:** can the Ledger answer "how has this moved over decades" rather
than over a handful of years?

---

## The short answer

Yes for four layers, no for two, and partly for three. The binding
constraint is almost never availability. Every local-government source
reaches back twenty-two years. The constraint is that **the older data
means something different**, and in one case the pipeline cannot tell.

| layer | ships now | honest floor | tier | change |
|---|---|---|---|---|
| state enacted | 2020-21 (6 yr) | **2017-18** | gated | +3 years |
| state actuals | 2020-21 (6 yr) | **2017-18** | gated | +3 years |
| cities | 2016-17 (8 yr) | **2016-17** | gated | **no change** |
| counties | 2016-17 (8 yr) | **2016-17** | gated | **no change** |
| special districts | 2016-17 (8 yr) | 2003-04 possible | as-filed | +13, not advised now |
| K-12 | 2022-23 (3 yr) | **2016-17** | gated | +6 years |
| CSU | 2023-24 (1 yr) | **2018-19** | gated | +5 years |
| CCC | 2022-23 (1 yr) | **2009-10** partial | gated | +13 years, split record |
| UC | 2024-25 (1 yr) | **2021-22** | gated | +3 years |

Two layers cannot be deepened at all. That is the most important line in
this document, and it is the one that took the most work to establish.

---

## 1. The governing finding: the guard does not fire

The FY2016-17 city incident is the reason this investigation was
commissioned. After it, `classify_expenditure()` was made shape-driven and
given an explicit refusal:

```
raise SystemExit("UNRECOGNIZED EXPENDITURE SHAPE — refusing to classify: ...")
```

I assumed, reading that, that a pre-2017 row would be rejected. **It is
not.** I ran the shipped classifier against real FY2009-10 rows fetched
live from SCO:

```
rows tested: 8   REFUSED (SystemExit): 0   ACCEPTED SILENTLY: 8

      safetyOther    $15.183B          police:  $0.000B
      streets        $11.715B          fire:    $0.000B
      utilities      $11.307B
      health         $ 7.402B
```

Pre-2017, SCO writes the function group into `category`, `subcategory_1`
**and** `subcategory_2` alike — all three read `Public Safety`. The guard
tests whether `subcategory_1` is a known group. It is. So the row passes,
`line` becomes `"Public Safety"`, which starts with neither `"Police"` nor
`"Fire"`, and $15.2 billion of police and fire spending falls into
`safetyOther` with police and fire reading exactly zero.

Totals conserve perfectly. Classification is entirely wrong. **This is the
FY2016-17 bug, reproduced on demand, against the guard written to prevent
it.**

What stands between the Ledger and shipping it again is the second gate,
not the first. `shape_gate()` rule 1 requires statewide police, fire,
admin, streets and parks to be nonzero in every year, and would fail this
build. The layered defence works — but only because the layer exists. The
lesson generalises past cities: **a refusal guard calibrated on the
vintages you have seen will not refuse a vintage you have not.**

One claim I checked and can refute: an agent in this investigation reported
that only two of the four local pipelines carry a classification-shape
gate, and that STATUS.md overstates coverage. That is wrong. All four carry
one — cities in a named `shape_gate()` function, counties at
`fetch_county_data.py:225`, special districts at `fetch_district_data.py:413`,
K-12 at `fetch_school_data.py:589`. The log is accurate.

---

## 2. Availability, and two traps in measuring it

Every source in scope reaches further back than we use. Measured:

| source | earliest | verified by |
|---|---|---|
| SCO cities / counties / districts | **FY2002-03** | live Socrata query, real rows |
| ebudget JSON API | **FY2017-18** | live API, 12 populated agency rows |
| CDE SACS | FY1999-2000 raw; FY2003-04 usable | live fetch |
| CCC fiscal portal | FY2009-10 | live fetch, gate re-run |
| CSU audited statements | FY2012-13 | PDF downloaded, gate re-run |
| UC annual financial reports | FY2003-04 | PDF downloaded, identity closed |
| DOF deflator | FY1947-48 | shipped file |

**Trap 1 — the soft 200.** `ebudget.ca.gov/api/publication/e/{fy}/statistics`
does not 404 for years it lacks. It returns HTTP 200 with `[]`. Worse,
`/appInfo` returns 200 with a well-formed body whose only tell is the
sentinel date `"Enacted on January 01, 9999"`. An availability check
written against status codes alone concludes the API covers FY2007-08. It
does not. Our pipeline already survives this — `latest_enacted_years()`
requires a non-empty `/statistics` — evidently written by someone who hit
it.

**Trap 2 — the soft 404.** `www.sco.ca.gov` answers HTTP 200 with an
identical 11,561-byte welcome page for *any* path, including invented ones.
Absence cannot be established there by fetching. One agent in this
investigation reported a 404 from that host that it could not have
observed; a skeptic caught it. Recorded here because it is exactly the
failure mode this investigation was meant to be resistant to, and it
occurred anyway.

The generalisable rule: **availability means data came back, not that the
server answered.**

---

## 3. Vintage drift, enumerated

### 3.1 Cities and counties — three regimes, not two

Measured directly against SCO's expenditure dataset (`ju3w-4gxp`),
statewide, all cities:

| FY range | entities | line_description | form_table | category |
|---|---|---|---|---|
| 2003–2016 | 469→482 | 68 | 64 | 8 |
| 2017 | 482 | 269 | 174 | 23 |
| 2018–2024 | 482 | 268 | 174 | 17 |

FY2018's taxonomy is identical to FY2024's — the current regime is stable.
The FY2016-17 incident is usually described as a two-vintage problem. It is
a **three**-vintage problem, and FY2016-17 is a singleton era of its own.

The FY2018 change merged the eight governmental functions into four paired
super-groups: `General Government and Public Safety`, `Health and Culture
and Leisure`, `Public Utilities and Other Expenditures`, `Transportation
and Community Development`. None of the FY2016 category names exists in
FY2018 at all.

### 3.2 The classification trap, quantified

The eight governmental categories carry **100%** of the dataset total in
FY2013–FY2016 and **50.6%** in FY2017. The grand total is continuous
($74.28B → $75.24B, +1.3%). Pre-2017 folded enterprise, capital and debt
*into* the functions; FY2017 broke them out.

Per category, at the break (statewide, $B):

| category | FY2015 | FY2016 | FY2017 | change |
|---|---|---|---|---|
| Public Safety | 17.60 | 18.48 | 18.26 | **−1.2%** |
| Community Development | 5.10 | 5.51 | 4.38 | −20.4% |
| Culture and Leisure | 5.23 | 5.59 | 4.09 | −26.8% |
| General Government | 6.81 | 7.64 | 4.71 | −38.4% |
| Health | 9.18 | 9.88 | 2.94 | −70.2% |
| Transportation | 13.27 | 13.55 | 3.62 | −73.3% |
| Public Utilities | 14.27 | 13.46 | 0.07 | **−99.5%** |
| Other Expenditures | 0.25 | 0.17 | 0.02 | −89.9% |

The functions that break are exactly those with enterprise operations —
utilities, hospitals, transit. Public Safety survives because policing and
fire are not enterprise activities.

### 3.3 Line detail cannot go back at all

FY2009-10, `category='Public Safety'`: `subcategory_1` has **one** distinct
value and `subcategory_2` has **one** distinct value, both `"Public
Safety"`. Police and fire are not separable before FY2016-17 in this
dataset. Not hard to separate — **not present**.

This is decisive. The Ledger's city and county pages are built on the
function split. A series that cannot carry police-per-resident is not a
deeper version of the current product; it is a different one.

### 3.4 Other layers

Full enumerations are in the per-layer research; the load-bearing items:

- **K-12** — LCFF replaced revenue limits in FY2013-14, which rewrites the
  SACS resource-code meaning of restricted vs unrestricted. `lcffsummary{yy}.xlsx`
  cannot exist before it. `UserGL_Totals`, the table our Gate 2 needs, is
  absent at FY2002-03 — that is the provable floor, and it happens to sit
  one year below the recommended one.
- **CCC** — the portal's own coverage begins FY2009-10 for Table VI. The
  apportionment-derived fields (per-FTES, state GF, basic aid) only reach
  FY2019-20. Two different depths in one record.
- **UC** — the audit-status caveat currently on the page **does not exist**
  in older vintages. Carrying the current sentence backward would put a
  false statement on the face of the site.
- **CSU** — older PDFs are not unreadable, as first reported; they carry a
  uniform −29 character shift affecting letters and digits alike. Readable
  once known, invisible if not.

---

## 4. Structural breaks

Events that make a long series misleading *even when every figure is
correct*. Years verified unless marked.

| break | year | layers | what a naive line shows |
|---|---|---|---|
| GASB 34 | phased 2001–2006 | all local | composition shifts that look like spending changes, at different times per entity |
| Triple flip / VLF swap | FY2004-05 | cities, counties, K-12 | property tax rising, sales tax and VLF falling — a swap, not a shift in what residents pay |
| 2008-09 collapse, Prop 1A suspension, K-14 deferrals | FY2008-09 – FY2012-13 | state, all local | deep cuts then dramatic recovery; partly deferral timing |
| Prop 22 | FY2010-11 | local | local revenue smoothing read as recovery |
| **2011 Realignment (AB 109)** | FY2011-12 | counties, state | state corrections falling, county public protection rising — a transfer of duty |
| **RDA dissolution (ABx1 26)** | FY2011-12 | cities, counties, districts | community development collapsing permanently — agencies abolished |
| Prop 30 / Prop 55 | FY2012-13 / 2016 | state, all education | a step up read as growth; a temporary tax later partly extended |
| **LCFF replaces revenue limits** | FY2013-14 | K-12 | categorical revenue collapsing, unrestricted exploding — same money, recoded |
| AB 85 health realignment | FY2013-14 | counties | counties deprioritising health — a redirection |
| **ACA Medi-Cal expansion** | FY2013-14 | state, counties | largest single-agency rise in modern state history — mostly federal share |
| GASB 68 / 75 | FY2014-15 / FY2017-18 (inferred) | accrual layers | benefit expense jumping — recognition, not cash |
| SB 1 roads | FY2017-18 | cities, counties, state | local road spending rising by local choice — a state tax |
| COVID federal relief | FY2019-20 – FY2022-23 | all | expansion then austerity — a one-off, tail to FY2026-27 |

The state agency taxonomy also reorganised around FY2011-12 (inferred):
Transportation and Government Operations appear from nothing, which a naive
agency trend renders as agencies springing into existence.

**What must be said.** Any line crossing one of these needs a stated break,
not a footnote. The site already has the vocabulary for this — the dagger
and the comparability note. The rule should be: *a break is annotated at
the year it occurs, on the line itself, in the same register as the
existing notes.* A twenty-year line with no break marks is a claim that
none occurred.

---

## 5. Entity continuity

The identifier work after the slug-instability defect re-keyed layers onto
each source's own stable code. Backward, that guarantee is uneven.

**SCO publishes no entity code at all** — not for cities, counties or
special districts. Identity is the name string. For cities this happens to
hold: the 482 names are stable and unique across all 22 years. For special
districts it does not — 24% of entities are absent from any given year, and
most of that is late or absent filing rather than formation or dissolution.

Worked cases that would produce wrong series if handled naively:

- **SCV Water** (merger effective 1 Jan 2018): filings overlap in FY2018-19,
  so three entities appear where one reorganisation occurred.
- **Central Fire District** (consolidation 4 Feb 2021, FY2021-22 missing):
  two districts fall off a cliff, a blank year, then a $42.6M district
  appears.
- **K-12 unifications**: the CDS code does **not** survive unification. Four
  cases identified. Each renders as two districts terminating and one
  unrelated district beginning.
- **CDE publishes the fact of a merger but not the date or the target** —
  those fields are 100% empty. A continuity map built on them would not
  fail; it would silently produce nothing.
- **CSU campuses are keyed on display name**: Cal Poly Humboldt (renamed 26
  Jan 2022) becomes two half-length series; Cal Maritime (absorbed 1 Jul
  2025) silently merges into another.
- **State department names lag the legal rename** — DFEH became CRD on 1 Jul
  2022 but appears under the old name in the FY2022-23 budget. A reader
  citing our page would attribute the wrong name to the year.

**The rule that follows.** Continuity must be *asserted from a published
source*, never inferred from name, geography or magnitude. Inference would
have produced a plausible and wrong answer in at least three of the cases
above. Where a source does not publish the linkage, the honest output is
two series and a stated break — not one series, and not a guess.

---

## 6. Shape gates for older eras

The current rules were calibrated on FY2016-17 onward. Backward they fail
in both directions.

**False failures.** Pre-2017 cities have zero debt service and zero capital
outlay *by construction* — those categories did not exist as separate
lines. A presence rule would flag every one of fourteen years. Likewise a
function that genuinely does not exist for an entity (a city contracting
its fire service) is not a defect.

**False passes.** This is the dangerous direction, and §1 is the proof: the
guard passed a vintage that misclassified everything. Presence rules are
the right defence against a column shift *within* a stable form. They are
close to useless against a form change, because the new form is internally
consistent.

**The rule class that is missing** is a cross-boundary continuity check:
when a new vintage is admitted, each function's statewide total must be
within a stated tolerance of the adjacent year, **or** the discontinuity
must be explicitly declared in code. Applied to FY2016→FY2017 this fires on
six of eight functions — which is correct, because six of eight genuinely
changed meaning. A gate that must be told about a break is a gate that
cannot be surprised by one.

Second missing rule: **a function absent by construction must be declared
absent**, not left to read as zero. Otherwise a twenty-year chart shows
California cities carrying no debt at all until FY2016-17.

---

## 7. Inflation over long windows

Deflator coverage is not the constraint — 82 fiscal years, FY1947-48
onward. Four findings change the picture V14 established:

1. **V14's short-window sensitivity finding inverts.** Its reassurance was
   that lengthening the window makes index choice matter less. Measured
   across windows of 2 to 40 years, the fraction-of-inflation metric does
   fall — but the *level* gap between candidate indices keeps growing.
   Shorter is safer for the index choice, not longer.
2. **The gap changes sign at about a seventeen-year window** (start near
   FY2007-08). A fixed directional caveat — "our index tends to run below a
   California consumer index" — is true at eight years and false at twenty.
   The caveat cannot be written once and reused at every depth.
3. **The national-not-Californian limitation compounds.** It is a minor
   purity note on a three-year K-12 view. It is material from roughly an
   eight-year window and dominant at twenty.
4. **"Exactly one city in 482 is index-ambiguous" will not survive.** That
   sentence is currently in the method note. Over twenty years it is almost
   certainly false and must not be carried forward unrecomputed.

V14's fiscal-year conversion and its percent-of-total invariances survive
the long window unchanged. Sections 2 and 4 of that finding do not need
re-litigating; sections on sensitivity do.

---

## 8. Recommendations

### Extend

- **State enacted and actuals → FY2017-18** (6 → 9 years, gated). The API
  floor is hard and full-depth: 190/192/192 departments in the three new
  years, zero fund-class, program and bridge gate failures. Actuals for the
  same three years gate clean off Schedule 9 at no extra engineering.
  Payload roughly +50% on `data.js`.
- **K-12 → FY2016-17** (3 → 8 years, gated). Stops one year above the
  provable `UserGL_Totals` floor. Do not cross LCFF (FY2013-14) — the
  restricted/unrestricted split changes meaning.
- **CSU → FY2018-19** (1 → 6 years, gated). FY2012-13 is the structural
  floor and is reachable, but the −29 character-shift encoding and campus
  eliminations sign handling make the deeper tier a separate project.
- **CCC → FY2009-10 for the Table VI core** (16 years), **FY2019-20 for
  per-FTES**. Ship the record with two explicit depths rather than
  truncating the core to match the shallower field. Three vintages
  (FY2015-16 – FY2017-18) are unretrievable and must be shown as absent,
  not interpolated.
- **UC → FY2021-22** (1 → 4 years, gated). Do not carry the audit-status
  sentence backward — it is not true of older vintages. Do not go below
  FY2008-09 under any framing.

### Do not extend

- **Cities and counties stay at FY2016-17.** This is the finding I most
  expected to come out the other way. Twenty-two years are available and
  the totals reconcile, but the function split — which is what these pages
  *are* — does not exist before FY2016-17, and six of eight functions
  change meaning at the boundary. A deeper series would be a chart of a
  reporting-form change wearing the costume of a spending trend.

  A **total-expenditure-only** series back to FY2002-03 is defensible and
  would be genuinely useful. It is a different product with a different
  page and a different gate, and it should be decided on its own merits,
  not slipped in as "more years".

- **Special districts: not now.** FY2003-04 is reachable but 24% non-filing
  in the current window is already the layer's dominant caveat; older years
  are worse. A deeper as-filed series would mostly chart filing compliance.

### Sequence

The state and K-12 extensions are low-risk and self-contained; they should
go first and separately. CCC's split-depth record needs a design decision
before any code. Cities/counties needs no work at all, which is the point.

---

## 9. What I could not determine

- Whether DOF's pre-2017-18 Enacted Budget packages — which do exist back
  to FY2000-01, contrary to a first report, and do carry structured agency ×
  fund-class tables on the enacted basis — are parseable at our resolution.
  A skeptic established they exist and are not what the earlier agent
  claimed. Nobody established they are usable. This is the single largest
  open opportunity in the investigation.
- Whether historical DOF deflator vintages are stable across republication.
  Two vintages agreed exactly; two is not a series.
- GASB 68/75 effective dates for our specific filers are marked inferred,
  not verified.
- The CCC MIS district code's stability before 2009-10.

## 10. Provenance

Measured by me directly, live, and reproducible from this document: the
SCO three-regime table, the per-category break table, the 100%→50.6%
composition shift, the absence of police/fire separability pre-2017, the
classifier-does-not-refuse result, and the shape-gate wiring across all
four local pipelines.

Everything else rests on a fan-out of nine per-layer investigations, each
challenged by an independent skeptic instructed to refute it. The skeptics
overturned material claims in five of nine layers — including one fabricated
HTTP status, one "files have been removed" claim that was false, and one
"not machine-readable" claim that was an unrecognised character encoding.
Where a per-layer number below is not in the paragraph above, it carries
that provenance and not mine.
