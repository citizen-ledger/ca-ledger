# V23 finding: public employee compensation — what can be published honestly

*Investigated 2026-07-25 against the SCO Government Compensation in
California (GCC) 2024 exports for cities, counties, special districts
and K-12. No build.*

## Recommendation, up front

**(c) Don't ship.** Not position-level, and not entity-level either.

Two independent verdicts, each sufficient:

1. **Position-level is refused on privacy.** 157,305 records across the
   four files are a single identifiable person. Removing a name column
   that never existed anonymises nothing.
2. **Entity-level survives privacy and fails everything else.** There is
   **no control to gate against at any layer**, and the one number a
   reader would actually compute — compensation as a share of spending —
   is **not computable**, because the numerator and denominator have
   different fund scopes and the source carries no fund field.

What is left after both is a single ungated, uncheckable number per
entity that cannot safely be divided by anything on the site. That is
not a thin true layer; it is a number with no defensible use.

---

## 1. The privacy determination — decided, and it decides most of it

**Records are individuals, not position aggregates.** SCO's own
documentation says the site shows cost "for positions regardless of the
individuals", and the schema has **no name field**. Neither fact makes
the record an aggregate:

- each row carries one incumbent's actual `RegularPay`, `OvertimePay`
  and `TotalWages`
- a single `(employer, department, position)` group runs up to **3,591
  rows** — so rows are people, not classifications

**157,305 of those groups contain exactly one row.**

| file | rows | position groups | single-incumbent | share |
|---|---|---|---|---|
| City | 345,097 | 75,094 | **42,683** | 56.8% |
| County | 416,950 | 53,543 | **25,556** | 47.7% |
| Special district | 183,170 | 56,443 | **34,820** | 61.7% |
| K-12 | 461,999 | 94,839 | **54,246** | 57.2% |

**155,157 of the 157,305 (98.6%) are non-elected** — ordinary employees
with a full privacy expectation, not people who stood for office.

And identifiability rises exactly as entity size falls:

| city population | position groups | single person | share |
|---|---|---|---|
| **under 10,000** | 3,507 | 2,481 | **70.7%** |
| 10,000–50,000 | 16,926 | 11,023 | 65.1% |
| 50,000–250,000 | 37,241 | 21,734 | 58.4% |
| 250,000+ | 17,420 | 7,445 | 42.7% |

In a city of 6,000 with one Finance Director, publishing "Finance
Director, Finance Department, City of X — $187,432" identifies one
private person to everyone who would care. **The governing distinction
is that a public employee is not a public figure** — power and
discretion, not employer. A city manager's compensation answers an
accountability question; a payroll clerk's transfers as gossip about a
neighbour.

This is the V16a wall in a new place, and it is not softened by the
absence of a name column.

---

## 2. Entity-level totals — no gate exists at any layer

Measured GCC 2024 totals:

| layer | employers | rows | wages | retirement + health | total |
|---|---|---|---|---|---|
| City | 479 | 345,097 | $31.85B | $8.59B | **$40.45B** |
| County | 57 | 416,950 | $36.75B | $12.36B | **$49.11B** |
| Special district | 3,159 | 183,170 | $13.64B | $3.63B | **$17.27B** |
| K-12 | 437 | 461,999 | $24.59B | $8.61B | **$33.19B** |

**Cities and counties: no control exists, and none can.** The SCO
financial reports that this site already reads publish city and county
expenditure **by function and by form line, never by object**. I
searched every column of the city expenditure dataset (`ju3w-4gxp`):
across `category` (27 values), `subcategory_1` (60), `subcategory_2`
(60) and `form_table` (60), the only personnel-shaped hit is
`CURR_EXP_EMPLOYMENT` — an *employment programme* service area, not
payroll. **There is no salaries-and-benefits figure in the city
financial report to reconcile against.**

**Special districts: the control existed and was discontinued.** SCO
does publish `Salaries and Wages` and `Employee Benefits` categories for
districts — **for FY2003 through FY2016 only**. There is **no
overlapping year** with the GCC data. Even in FY2016 only ~1,200 of
~5,000 districts reported them.

**K-12: a correlation, not a gate.** SACS does carry salaries and
benefits as objects, and the site publishes them. Comparing GCC total
compensation against the site's own SACS personnel cost for the 317
districts that join by name:

- median ratio **0.948**, p10 **0.877**, p90 **1.063**
- **19.9% of districts show GCC exceeding** the site's personnel cost
- mean **2.072** against a median of 0.948 — the spread is dominated by
  bad name-joins, the hazard this project has been bitten by before

A ±10% band with a fifth of cases inverted is not a reconciliation.

---

## 3. Coverage — two layers fail before anything else

Normalised-name join against the site's own rosters:

| layer | site entities | GCC employers | matched | coverage |
|---|---|---|---|---|
| Cities | 482 | 479 | 479 | **99.4%** |
| Counties | 57 | 57 | 57 | **100.0%** |
| Special districts | 5,214 | 3,154 | 3,093 | **59.3%** |
| K-12 districts | 861 | 426 | 317 | **36.8%** |

K-12 at 36.8% and special districts at 59.3% are below anything this
site has ever shipped. And **non-reporting is not distinguishable from
zero** in the export: an entity that filed nothing and an entity with no
employees are both simply absent.

---

## 4. Is it additive? No — and the failure is specific

The brief asked whether entity compensation is a second view of a number
the site already publishes. The answer differs by layer, and the
combination is the problem:

- **for cities and counties it is genuinely new** — the site publishes
  no personnel figure at all — **and it is exactly where no control
  exists**
- **for K-12 it is ~95% of a figure the site already publishes gated to
  the cent** — so where it *can* be checked, it adds nothing

New where it cannot be verified; duplicative where it can.

**And the share-of-spending reading is not available.** GCC total
compensation ÷ the site's published city expenditure, 479 cities:

| | median | p10 | p25 | p75 | p90 |
|---|---|---|---|---|---|
| ratio | **0.431** | 0.203 | 0.300 | 0.537 | 0.641 |

That 3× spread is **not** a measure of how labour-intensive different
cities are. The site's expenditure figure is **governmental activities
only**; GCC covers **every employee the entity reports, including
enterprise departments**. Los Angeles shows compensation of $9.10B
against governmental spending of $12.02B — 75.7% — while carrying a
further **$9.50B of enterprise spending** whose staff are in the
numerator and whose costs are not in the denominator.

**The export has no fund field.** `DepartmentOrSubdivision` is free
text. The correction cannot be made, so the ratio cannot be published,
so the entity total cannot be safely divided by anything on this site.

---

## 5. The comparability traps, measured

- **Pension reporting is not uniform, and the source says so.** The
  `IncludesUnfundedLiability` flag is set per employer: **139,863 city
  records True, 205,234 False** — $4.53B of retirement dollars reported
  on one convention and $4.06B on the other. Median retirement-and-
  health as a share of wages is **0.283** where the flag is true and
  **0.261** where it is false. Two identically-paid positions at two
  cities show different total compensation for a pure reporting reason,
  and it cannot be corrected because the unfunded component is not
  separately reported.
- **Part-year and part-time positions sit in the same table as
  full-time ones**, with no hours or FTE field. Any average over that
  population is meaningless, which removes "average pay" as a
  presentation.
- **Overtime is a separate column** (`OvertimePay`) and is real money,
  but including it distorts any typical-pay reading and excluding it
  understates cost.
- **Contract cities recur.** A city with no police department has no
  police positions, exactly as it has no police spending — the same
  trap the expenditure layer already carries.
- **Non-reporting is invisible**, as in §3.

---

## 6. The senior-role question — answered, and it fails

The brief asked whether a defensible, **data-derived** boundary exists
for roles where the accountability argument genuinely holds. Tested
rather than assumed:

- the export carries exactly two role flags: `ElectedOfficial` and
  `Judicial`
- **`Judicial` is entirely unused** — 0 rows across all four files
- `ElectedOfficial` marks **12,937 of 1,407,216 rows (0.92%)**
- **there is no chief-executive flag.** Identifying "city manager" or
  "superintendent" would require pattern-matching job titles — which is
  precisely the editorial judgement that was ruled out

So the only data-derived boundary is *elected*. It is defensible — these
people stood for office and their pay is set in public. **It is also
almost empty of the content the argument was about:**

| | median total comp | under $25k | under $5k |
|---|---|---|---|
| city elected officials (n=3,144) | **$13,246** | 64.7% | 34.3% |
| district elected officials (n=7,086) | **$0** | 93.8% | 84.3% |

California local elected officials are overwhelmingly unpaid or paid a
nominal stipend. A layer restricted to them would publish mostly zeros
and answer no question about where money goes, because almost none goes
there. And **57.8% of elected city position-groups are still
single-incumbent** — a mayor is one person — so even this narrow layer
publishes individuals, albeit ones with a real public-figure argument.

**The boundary that would carry accountability content — chief
executives and department heads — cannot be drawn from the data. It can
only be drawn by our own opinion about which jobs matter, which is the
test the brief set, and it fails it.**

---

## 7. The reproducibility constraint

`gcc.sco.ca.gov` (where `publicpay.ca.gov` redirects) **expressly
excludes automated retrieval**: its `robots.txt` carries a Cloudflare
managed block naming `ClaudeBot`, `GPTBot`, `CCBot`, `Google-Extended`
and others, with `Content-Signal: ai-train=no, use=reference`. A human
with a browser is welcome to the data; an automated pipeline is not.

**The data behind this finding was therefore downloaded manually.** That
is a real constraint on reproducibility and it belongs beside the CSU
manual-cache exception: a layer built on it could not be rebuilt by
`--refresh`, and its integrity story would rest on a file a human
fetched rather than on a pipeline anyone can re-run. **If anything from
this source ever ships, that must be stated on the page**, not only in a
method note.

This is also an argument on its own: a source that forbids automated
retrieval is a poor foundation for a site whose central claim is that
every figure can be rebuilt from published sources.

---

## 8. What I did not do

- I did not obtain the state or higher-education GCC files; the four
  local files were the ones supplied. State and CSU coverage is
  therefore untested, though §1 and §4 would apply unchanged.
- The K-12 and district joins are by normalised name; some of the
  ratio outliers in §2 are certainly bad matches rather than real
  scope differences. That weakens the outliers, not the median.
- I did not test earlier GCC vintages for schema drift.
- I did not attempt to determine whether `DepartmentOrSubdivision` could
  be classified into governmental vs enterprise by hand. If a future
  investigation does, §4's ratio objection weakens — §1 does not.

## Recommendation

**Don't ship.** Position-level is refused on privacy and that is not
negotiable. Entity-level clears privacy and then fails on all three of
the remaining tests: no control at any layer, coverage below anything
this site ships for two of four layers, and a headline ratio that cannot
be computed because the source has no fund field.

The honest one-line summary: **this source answers "what does each
person earn", which the site must not publish, and cannot reliably
answer "what does this government spend on people", which it could.**
