# V23a finding: public employee compensation, reopened on accuracy grounds

*Investigated 2026-07-25 against the SCO Government Compensation in
California (GCC) 2024 exports for cities, counties, special districts
and K-12, obtained by manual download. No build.*

## Recommendation, up front

**(b) As-filed, with five conditions that are not optional.**

The layer can be published accurately. It cannot be gated — a published
control exists but can never be reconciled to, for a structural reason
given in §1 — and it cannot carry any computed average, because a
quarter of the records are not full-year positions and the source has no
hours field to tell you which.

| | verdict |
|---|---|
| **tier** | as-filed, labelled, on the site's existing unreconciled vocabulary |
| **basis** | its own layer, never a drill-down of spending (§2) |
| **must carry** | pension-reporting dagger (§3), contract-service mark (§4), non-filer mark (§4) |
| **must never** | compute an average or median over the reported population, rank, or divide by spending |

## 0. The decision this supersedes

V23 refused this layer on privacy grounds. **That refusal is withdrawn,
and the reason is recorded here rather than left implicit.** It applied a
comfort standard — *this might expose someone* — to a site whose
refusals are otherwise epistemic: we decline to publish what we cannot
verify, or what a reader would predictably misread. This data is
accurate, disclosable by law, already published by the State Controller,
and republished by others. The site's premise is that the public record
belongs to the public and that the difficulty of reading it is an
accident of publication rather than a feature worth preserving.

The privacy facts V23 measured remain true and are not restated as
objections: 157,305 position-groups across the four files contain a
single incumbent, 98.6% of them non-elected. They are recorded because
a future reader should know the layer publishes identifiable people by
description, and that this was a decision rather than an oversight.

Everything below is about accuracy only.

---

## 1. The gate — a control exists, and cannot be reconciled to

**Two internal identities hold perfectly, and neither is a gate.**

| identity | City | County | Special district | K-12 |
|---|---|---|---|---|
| `RegularPay + Overtime + LumpSum + OtherPay = TotalWages` | 100.000% | 100.000% | 100.000% | 100.000% |
| `DB + EmpCostCovered + Deferred + Health = TotalRetirementAndHealth` | 100.000% | 100.000% | 100.000% | 100.000% |

Zero failures in 1,407,216 rows. But both are SCO's own arithmetic
*within a single row*. Reproducing them proves the file is
self-consistent, not that any figure is right. This is
self-reconciliation, exactly as anticipated.

**A genuine external control exists for the mandated layers.** SCO's
press release of **25 June 2025** states, for reporting year 2024:

> "This report covers 746,358 positions and a total of nearly $67.28
> billion in 2024 wages." — 461 cities and 55 counties, with "Twenty two
> cities and two counties failed to file or provided incomplete
> information."

Recomputed from the export:

| | published | export | residual |
|---|---|---|---|
| positions | 746,358 | **762,047** | **+15,689 (+2.10%)** |
| wages | ~$67.28B | **$68,598,276,417** | **+$1.32B (+1.96%)** |
| cities | 461 | 479 | +18 |
| counties | 55 | 57 | +2 |

Under the site's own gate rule — fail if the residual exceeds
`max($1,000, official × 0.001)` — **this fails by a factor of twenty**.

**And the failure cannot be fixed by a per-vintage declaration**, which
is what closed the analogous CCC and CDIAC cases. The export's
`LastUpdatedDate` runs to **15 January 2026**, seven months after the
release. The +18 cities are late filers closing most of the 22-city gap
the release itself reported. The published total is a *point-in-time
announcement*; the export is a *live database*. **SCO publishes no
as-of-date total**, so there is no instant at which the two can be
aligned, and no declaration can name one.

The K-12 case is worse and is a different problem: **reporting is
voluntary for that layer**. SCO's release of 5 December 2025 states 360
of 1,883 K-12 education employers filed fully compliant reports — 19.1%.
The layer is a self-selected sample; each entity's own figure is its
own, but nothing aggregate over it means anything.

**Verdict: as-filed at every layer.** The reconciliation target is named
for the record — SCO's annual press-release totals — with the finding
that it is unusable as a gate.

---

## 2. What the figure is, precisely

**It is not a share of spending and must never be rendered as one.** V23
measured GCC total compensation ÷ the site's published city expenditure:
median **0.431**, p10–p90 **0.203–0.641**. That spread is enterprise
intensity, not labour intensity — the site's expenditure figure is
governmental activities only, while GCC covers every employee the
employer reports, including enterprise departments. Los Angeles shows
$9.10B of compensation against $12.02B of governmental spending while
carrying a further $9.50B of enterprise spending whose staff are in the
numerator and whose costs are not in the denominator.

**The export has no fund field.** `DepartmentOrSubdivision` is free
text. The correction cannot be made, so the ratio must not be offered,
and the layer is its own page on its own basis.

What the figure covers, to be stated on the face:

- **one row = one position as the employer reported it**, for the
  calendar year, including part-year and part-time positions
- **`TotalWages`** = regular pay + overtime + lump-sum + other pay
- **`TotalRetirementAndHealthContribution`** = employer's defined-benefit
  contribution + any employee share the employer covers + deferred
  compensation + health/dental/vision
- **excluded**: the employee's own contributions, and — for most
  employers — any unfunded-liability payment (§3)
- **no fund attribution, no hours, no FTE, no headcount of persons** —
  a person holding two positions appears twice

---

## 3. The pension trap — a dagger, derived from the flag

This is the sharpest comparability defect and the source itself marks
it. `IncludesUnfundedLiability` is set **per employer** — measured, **0
of 479 cities, 0 of 3,159 districts and 0 of 437 K-12 employers mix
values across their own rows**, so the flag is an employer-level
property and a dagger derived from it is exact.

| | records | retirement + health dollars | median share of wages |
|---|---|---|---|
| flag **true** | 139,863 | **$4,532,986,143** | **0.283** |
| flag **false** | 205,234 | **$4,060,195,393** | **0.261** |

*(cities; positions over $50,000)*

Two identically-paid positions at two employers show different total
compensation for a pure reporting reason, and **the unfunded component
is not separately reported**, so it cannot be netted out. The 2.2-point
median gap is the visible part; per-employer it can be far larger.

**How it renders.** Every record of an employer whose flag is true
carries a dagger, on the record and in any export, reading in substance:
*this employer's retirement figure includes payments toward unfunded
liability; employers marked otherwise exclude it, and the two are not
comparable.* Derived from the flag on every build, never hand-listed —
the same discipline as the contract-service daggers already on the city
layer.

---

## 4. The other traps, measured

**Part-year and part-time — this is what kills averages.** There is no
hours field and no FTE field. Using the source's own
`MinPositionSalary` as the yardstick, **89,206 of 345,097 city rows
(25.8%) show `RegularPay` below half the position's own minimum
salary** — people who did not work the full year at that rate, sitting
in the same table as full-time staff. A further 4.6% publish no minimum
at all, so they cannot be classified either way.

**Any mean or median over that population is a number the site would
itself be producing and could not defend.** It is not a "typical
salary"; it is an artifact of the part-time share. This removes average
pay, median pay, and any per-position summary statistic from the layer.

**Overtime.** 172,792 city rows (**50.1%**) carry overtime; median
**8.4%** of wages, p90 **32.0%**. It is real money and must be shown,
but as its own component — never folded into a figure labelled as pay
for a role.

**Contract cities — already solvable.** 143 of 479 cities in the export
(**29.9%**) have no police-titled position at all. That is the same fact
the expenditure layer already handles: the site's services checklist
carries `police: {code: "D", provided wholly or in part through contract
with the county}`. The absence must be marked from that existing field,
not left as an apparent zero.

**Not-published versus zero.** Three cities on the site's roster —
**Banning, Chino, Willits** — are absent from the export entirely; no
employer present reports $0 total wages, and only 224 individual rows
(0.06%) carry $0. So the two states *are* distinguishable, **but only
because the site holds its own roster**: nothing in the export marks a
non-filer. The layer must diff against the roster and render the
difference as not-published, never as zero.

---

## 5. What can be presented

Survives:

- **per-entity position listings** — position title, department, and the
  pay components shown separately (regular, overtime, lump-sum, other,
  and the retirement/health total), each row as filed
- **counts of reported positions** per entity, described as positions
  reported and never as employees or headcount
- **entity totals** of wages and of retirement-and-health, as filed,
  labelled unreconciled
- **distribution by classification** only if shown as counts within
  bands, never as a central tendency

Refused on accuracy grounds:

- **any average or median** over the reported population (§4)
- **any ranking or "top earners" view** — out of scope by construction,
  and a ranking is the presentation most likely to be read as a finding
  about a person rather than about a payroll
- **compensation as a share of spending** (§2)
- **any cross-entity comparison of totals** without the §3 dagger and
  the §4 contract mark, because both are employer-level and both move
  the number for non-substantive reasons

---

## 6. Reproducibility — a CSU-class exception

`gcc.sco.ca.gov` (where `publicpay.ca.gov` redirects) **expressly
excludes automated retrieval**: a Cloudflare-managed `robots.txt` block
naming `ClaudeBot`, `GPTBot`, `CCBot`, `Google-Extended` and others,
with `Content-Signal: ai-train=no, use=reference`. The data behind this
finding was downloaded manually by a human, which the same policy
permits.

Consequences, all of which must be stated on the page and not only in a
method note:

- **the layer cannot auto-refresh.** `--refresh` cannot rebuild it; a
  human must fetch the files.
- **the integrity story changes shape.** The site's claim is that any
  figure can be rebuilt from published sources by anyone running the
  pipeline. Here it becomes: any figure can be rebuilt by anyone who
  first downloads four files by hand. The SHA-256 pin still proves the
  file has not changed since the build; it cannot prove the file is what
  the source would serve today.
- **the vintage is frozen at download.** Since §1 shows the source is a
  live database with no as-of-date total, the export's own
  `LastUpdatedDate` range — here 20 November 2025 to 15 January 2026 —
  is the only vintage marker available and must be published with it.

This sits beside the CSU manual-cache exception as the second such case,
and the two should be described together wherever the site explains its
rebuild claim.

---

## 7. What I did not do

- Only the four local files were supplied; state, CSU, UC, community
  college, courts and First 5 categories are untested. §1's voluntary-
  reporting finding applies to several of them.
- I did not test earlier GCC vintages for schema drift, so no
  multi-year series is justified by this finding.
- The `MinPositionSalary` part-year test in §4 is a proxy, not a
  measurement of hours; it establishes that a large minority of rows are
  not full-year, not exactly which.
- I did not verify the 143 no-police cities against the services
  checklist case by case; the two counts are consistent in magnitude but
  the join was not run.

## Recommendation

**Ship as-filed, or not at all.** The five conditions in §§3–5 are what
make it accurate: the pension dagger, the contract mark, the non-filer
mark, no computed averages, and no share-of-spending. A version without
them would be a number the site itself made misleading, which is the one
failure mode this project exists to avoid.

The honest summary of what the layer is: **a faithful republication of
what each employer reported, position by position, that cannot be
reconciled against anything and must never be averaged.**
