# V9 finding — school funding sources: the SACS resource dimension

*Investigation date: 2026-07-17. Empirical base: the FY 2022-23,
2023-24, and 2024-25 SACS unaudited-actuals archives the pipeline
already downloads (sacs{yy}.mdb), tested against the published Current
Expense of Education files and the shipped record. Every figure below
was computed from those files this week; nothing is estimated unless
labeled as an estimate.*

**Recommendation: (a) SHIP, with plain-language funding-source
grouping — the grouping taken verbatim from CDE's own published
classification, the names taken verbatim from CDE's own code table,
and three daggers carried on the face.** The gate question, which
decides everything, is settled in the strongest possible way: the
resource breakout reproduces every published district figure to the
cent in all three years, because it is the same ledger regrouped, and
we proved it empirically rather than assuming it. The two genuine
hazards — a range CDE never assigned to a source, and money that is
"spending" a district never touches — are handled by naming, not by
inventing.

---

## 1. What the resource dimension contains

Every UserGL row we already stream carries a 4-character `Resource`
code — the funding source of that expenditure. The same .mdb ships an
official **`Resource` lookup table (Code, Title)**: CDE's own names,
in the same download, no new fetch. FY 2024-25 carries 662 coded
titles; **every code used in each year's ledger has a title in that
year's own table** (checked: zero untitled codes in any of the three
vintages).

Two versioning facts that shape any build:

- **Titles drift between vintages** — 46 codes are retitled between
  the FY 2022-23 and FY 2024-25 tables, and codes are added and
  retired continuously (22 added and 38 inactivated since July 2022;
  COVID-era ESSER codes are aging out). Names must be read from each
  fiscal year's own table, never crosswalked across years — the same
  vintage-locking rule the FY2017 city incident taught.
- CDE also publishes a standalone **Master List of Resources**
  (`cde.ca.gov/fg/ac/ac/documents/masterlistofresources.xlsx`, revised
  2026-04-23: Resource, U/F flag, Description, Date Added, Inactive
  Date) and fixed-width code tables
  (`cde.ca.gov/fg/ac/ac/validcodedesc.asp`). The titles are identical
  to the in-database table; the .mdb table is sufficient and is the
  one we already have.

A typical district's ledger uses **27 distinct resources** (median;
minimum 10, 90th percentile 43, maximum 76; LAUSD 78). Raw codes
alone would be a wall — but the titles are legible on their face.
LAUSD's FY 2024-25 current expense, top lines, exactly as the official
table names them:

| Resource | Official title | $M |
|---|---|---|
| 0000 | Unrestricted | 4,937.4 |
| 6500 | Special Education | 1,625.0 |
| 1400 | Education Protection Account | 975.2 |
| 7435 | Learning Recovery Emergency Block Grant | 633.7 |
| 2600 | Expanded Learning Opportunities Program | 631.4 |
| 3010 | ESSA: Title I, Part A, Basic Grants Low-Income and Neglected | 434.9 |
| 7690 | On-Behalf Pension Contributions (STRS) | 368.1 |
| 8150 | Ongoing & Major Maintenance Account (RMA) | 365.1 |
| 3310 | Special Ed: IDEA Basic Local Assistance | 116.4 |
| 6010 | After School Education and Safety (ASES) | 100.2 |

That table answers "why does this district spend this way" in the
reader's own language. This is the drill worth shipping.

## 2. THE GATE — settled, to the cent, in all three years

Resource is not a new measurement; it is a regrouping of the same
rows the record already gates. We tested it anyway, empirically,
district by district, exactly as the standing rule requires:

| Fiscal year | Districts | Reconcile to published CE | Worst residual |
|---|---|---|---|
| 2024-25 | 932/932 | to the cent | $0.0000 |
| 2023-24 | 933/933 | to the cent | $0.0200 † |
| 2022-23 | 934/934 | to the cent | $0.0000 |

† the same single publication-rounding artifact the V7 investigation
documented; it is CDE's, not ours.

Spot checks on the extremes: LAUSD sums to **$10,877,387,458.05**
against a published $10,877,387,458.05; Ravendale-Termo Elementary
(1.98 ADA, 10 resources) sums to $350,135.31 against $350,135.31.
The function × resource-group cross-tab also reproduces every
function total exactly (0 mismatches). **Resource depth inherits the
existing gate; nothing about it is a new tier.**

## 3. The restricted/unrestricted relationship — one partition, finer

The restricted/unrestricted split the record already displays **is a
resource-range aggregate**: the pipeline computes it as resource ≥
2000 (SACS's own definition; see §4). The resource breakout is
therefore a refinement of the displayed split, not a parallel figure
that could disagree. Verified on the shipped record: LAUSD FY 2024-25
ships unrestricted $5,989,305,511.11 / restricted $4,888,081,946.94,
and the resource-derived partition equals both **to the cent**. A
build should nest the resource view inside the existing
restricted/unrestricted line so the page shows one hierarchy, not two
adjacent claims.

## 4. The official classification — ranges, published; per-code source
column: none anywhere

No CDE artifact carries a per-code federal/state/local column — not
the Master List, not the valid-codes tables, not SACS Query. What CDE
publishes is the **classification by number range, in CSAM Procedure
310** (California School Accounting Manual, 2024 edition, "Resource
(Project/Reporting) Classification"), verbatim:

- **0000–1999 UNRESTRICTED RESOURCES**
- **2000–9999 RESTRICTED RESOURCES**, of which:
  - **3000–5999 Federal Resources Restricted**
  - **6000–7999 State Resources Restricted**
  - **8000–9999 Local Resources Restricted**

Applying these ranges is applying CDE's own published rule — it is
not an invented crosswalk. Statewide FY 2024-25 current expense
splits: unrestricted $62.43B (49.2% of it on resource 0000 alone),
state-restricted $25.16B, federal-restricted $5.39B,
local-restricted $4.70B.

Two honest edges the build must carry on the face, not bury:

1. **CSAM assigns no source to 2000–2999.** The range is "restricted"
   but sits before the federal block, and CDE never says whose money
   it is. Exactly one code is live there: **2600, Expanded Learning
   Opportunities Program, $3.56B**. The clean handling is to show it
   as a named row under its official title and classify the range as
   "Restricted — other (CDE assigns no source range)" — never to
   silently file it under "state" because we happen to know ELOP is a
   state program. If we know it, the reader can read the title.
2. **"Unrestricted" is not "local."** The 0000–1999 block contains
   LCFF apportionment, the Education Protection Account ($975M at
   LAUSD alone), and unrestricted Lottery — state-source money that
   is unrestricted in use. The group must be labeled
   **"Unrestricted"**, as CDE labels it — never "local funds." (In
   SACS, formal by-source classification lives on *revenue* objects —
   8010–8099 LCFF Sources / 8100–8299 Federal / 8300–8599 Other
   State / 8600–8799 Other Local — which is the vocabulary CDE and
   Ed-Data use; our expenditure grouping should borrow those nouns
   only where the resource ranges genuinely support them.)

**LCFF base vs. supplemental/concentration cannot be built.** CDE's
LCFF FAQ, verbatim: "All LCFF funding is accounted for as an
unrestricted resource" and districts "are not required to" track
base/supplemental/concentration separately; the State Auditor (Report
2019-101) confirms the ledger does not carry the split. Readers will
ask; the method note should state this plainly rather than let the
absence look like an omission. (The one adjacent thing that *does*
exist: 7399 "LCFF Equity Multiplier" is a separately-coded restricted
state resource.)

## 5. Payload — measured

FY 2024-25, EDP scope, districts only; three-year totals extrapolate
by ~3×:

| Option | Cells per year | Est. added file size (3 yrs) | Note |
|---|---|---|---|
| Raw per-code | 27,219 pairs | ~1.1–1.5 MB (+~30% on 4.05 MB) | illegible without grouping anyway |
| Five groups only | 4,508 | ~150 KB | legible but flattens Title I into "federal" |
| Function × group | 20,705 | ~600 KB | grid nobody asked for |
| **Hybrid (recommended)**: group totals + named codes ≥ $1M + one combined tail per group | 6,621 named + ~4.5k group/tail | **~300–400 KB** | named rows cover **96.2% of dollars**; the tail sums exactly |

The hybrid keeps the V8 payload discipline: under 10% growth, and
every displayed row still sums to the cent because the tail row
carries the exact remainder.

## 6. Traps specific to this dimension

- **On-behalf pension contributions (resource 7690): $3.40B statewide
  is inside current expense but is money districts never touch** —
  the state pays CalSTRS directly and SACS books it as revenue and
  expense ($368.1M at LAUSD). Any funding-source view that lists 7690
  without saying this misleads; it needs the same dagger the overlap
  panel already gives STRS on-behalf, worded on the row.
- **Indirect-cost transfers move overhead between sources.** Objects
  7300–7399 inside the gated scope shift roughly **$1.0–1.2B** out of
  categorical resources into unrestricted (measured FY 2024-25:
  unrestricted −$1,184.4M; federal +$212.0M, state +$516.2M, ELOP
  block +$139.4M, local +$93.4M). Totals still reconcile exactly —
  but a categorical's per-source figure includes payments to the
  district's own overhead. One method note, stated once: "per-source
  figures include each program's share of district overhead,
  transferred at the district's approved indirect rate."
- **Negative cells exist and are legitimate**: 113 district-resource
  cells are negative in FY 2024-25 (netted corrections; largest
  examples are hundreds of dollars). Render as the record already
  renders negatives — true minus, never hidden.
- **No double-count against the object view.** Resource is orthogonal
  to function → object: both drills partition the same gated parent
  and both sum to it exactly. The build must present them as sibling
  views of one figure (tabs or stacked panels), never as figures that
  could be added to each other.
- **Vintage-locked titles** (§1): read names from each year's own
  table; 46 retitles across our window prove why.
- **COEs and charters**: out of scope for this drill exactly as they
  are for per-ADA — the resource view rides on the gated district
  tier only. Commingled-charter districts keep their existing face
  caveat; their resource rows include the commingled charters, same
  as every other figure on those records.

## 7. Recommendation

**(a) SHIP, districts only, as the hybrid.** Concretely:

- Group by CSAM Procedure 310's published ranges, labeled with CDE's
  own words: **Unrestricted · Federal restricted · State restricted ·
  Local restricted · Restricted — other range** (the last currently
  containing only ELOP, shown by name).
- Within each group, named rows for that district's resources ≥ $1M
  under their official vintage titles, plus one "smaller resources,
  combined" row carrying the exact remainder.
- Nested inside the existing restricted/unrestricted line, which the
  groups reproduce to the cent by construction.
- Three daggers on the face: on-behalf pensions (7690 rows), the
  indirect-cost note, and — in the method notes — the plain statement
  that LCFF base/supplemental/concentration does not exist in any
  district ledger and therefore does not exist here.
- Hard gates added to the pipeline, same rule as everywhere: per
  district, resource rows + tails sum to the published Current
  Expense to the cent; group sums equal the shipped
  restricted/unrestricted split to the cent; no write on failure.
- Payload cost ~300–400 KB (+<10%); phone-legible because the median
  district shows ~5 group rows and a dozen named rows, not 27 codes.

Option (b) — raw codes only — is unnecessary: the official names ship
with the data. Option (c) — don't ship — would be the answer only if
the gate had failed or the names had to be guessed; neither is true.
This is the rare drill that is simultaneously cent-exact, officially
named, structurally consistent with what we already display, and
cheap. The daggers are not optional; without the 7690 and
indirect-cost notes the view would quietly overstate what districts
control, and that is the kind of soft mislead this record exists to
refuse.

---

*Sources: sacs{22,23,24}{23,24,25}.mdb UserGL + Resource tables (CDE
Annual Financial Data, cde.ca.gov/ds/fd/fd/); currentexpense{yy}.xlsx
(EDP 365); CSAM 2024, Procedure 310
(cde.ca.gov/fg/ac/sa/documents/csam2024complete.pdf); Master List of
Resources (cde.ca.gov/fg/ac/ac/resource.asp); CDE LCFF FAQ
(cde.ca.gov/fg/aa/lc/lcfffaq.asp); California State Auditor Report
2019-101; SACS Query (www2.cde.ca.gov/sacsquery/querybyresource.asp);
Ed-Data district finance reports (ed-data.org). Analysis scripts and
raw results preserved in the session scratchpad (v9_analysis.py,
v9_results.json).*
