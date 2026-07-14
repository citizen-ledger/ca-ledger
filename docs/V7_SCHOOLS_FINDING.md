# V7 finding: K-12 schools

_Investigated 2026-07-14. No UI or pipeline was built; this document is
the deliverable. Every load-bearing claim was established empirically —
the source files were downloaded and opened, the reconciliation gate was
tested by recomputation against published figures (and re-verified
independently of the first analysis), and the state-overlap bridge was
computed from the actual general ledger against this repo's own
data.js. A reproducibility appendix closes the document._

## Recommendation, up front

**(a) SHIP GATED AND COMPARABLE — with the comparison scoped to school
districts, and the other entity types shipped as records only.**

The V5 assumption that K-12 would be another as-filed tier turns out to
be wrong in the best way: this can be the most rigorously gated layer
on the site. Specifically:

- **School districts (932): gate per-LEA, compare per-ADA.** Every
  district-year total reproduces CDE's independently published
  "Current Expense of Education" figure **to the cent — 932 of 932
  districts in FY 2024-25, and 932 of 933 in FY 2023-24 with a worst
  residue of $0.02** (a rounding artifact in San Diego Unified's
  published figure). This is a stronger gate than the county layer's
  $1,000 tolerance. Comparison uses per-ADA — the standard education
  denominator — with data-derived structural footnotes (below).
- **County offices of education (58): records only, never compared.**
  CDE itself excludes COEs from its per-ADA statistic; they carry zero
  K12ADA in the SACS tables, run large pass-through books, and serve
  populations (court schools, community schools, SELPAs) no district
  serves. Comparing them would be the contract-city mistake at scale.
- **Charters (1,281): records only, never compared, with the filing
  mode stated on every record.** The structure is quantified in §2;
  the double-count traps are structural and the page must carry them.
- **The state-layer overlap is renderable, never addable** (§5): the
  honest bridge — about half of every school dollar is the state
  layer's K-12 money — ships as a computed statement in the
  does-not-add pattern the address view established.

The comparability and overlap questions, which the project owner said
would decide this, both resolve in favor of shipping: per-ADA is
honest for districts with three footnotable distortions, and the
overlap has a precise, quantified statement that prevents
double-counting instead of forbidding the layer.

---

## 1. Sources — bulk, annual, ~7-month lag, no API needed

**Primary: CDE's SACS unaudited actuals**, one self-extracting archive
per fiscal year at
`https://www3.cde.ca.gov/fiscal-downloads/sacs_data/{YYYY-YY}/sacs{yyyy}.exe`
(landing page: https://www.cde.ca.gov/ds/fd/fd/). Verified by download
and extraction:

- The `.exe` is **ZIP-compatible** — plain `unzip` opens it — and
  contains one Access `.mdb` (JET4), readable cleanly with `mdbtools`.
  FY 2024-25: 44 MB download, 466 MB database.
- **Years:** FY 2003-04 through 2024-25 linked (CDE states files exist
  back to 1995-96). A parallel per-year archive carries the charter
  **Alternative Form** data
  (`…/charterdata/{YYYY-YY}/alt{yyyy}data.exe`).
- **Cadence/lag** (verified via HTTP Last-Modified): annual, posted
  ~7 months after the June-30 close (FY 2024-25 posted 2026-02-04).
- **Structure** (FY 2024-25): `UserGL` — 1,600,940 general-ledger rows
  (county/district/school codes, fund, resource, goal, function,
  object, value); `UserGL_Totals` — 916,350 rows of **CDE's own
  county and state rollups**, a built-in reconciliation target;
  `LEAs` (1,045 filers, with K-12 ADA); `Charters` (1,281, with
  per-charter ADA and filing mode); code lookup tables.
- **One operational caveat:** cde.ca.gov *HTML pages* sit behind
  Radware bot detection, but the *file URLs* (www3 host and
  `documents/*.xlsx` paths) download without challenge. A pipeline
  automates against file URLs.

**The gate target: CDE's "Current Expense of Education"** annual Excel
(https://www.cde.ca.gov/ds/fd/ec/ — FY 1998-99→2024-25), carrying
per-district total current expense (**EDP 365**), ADA, and per-ADA
cost. **Per-LEA funded-ADA and LCFF detail:** the LCFF Summary Data
workbooks (https://www.cde.ca.gov/fg/aa/pa/lcffsumdata.asp,
FY 2019-20→2025-26; 2,269 LEA rows spanning districts, COEs, and
charters).

**Ed-Data (ed-data.org)** — CDE + EdSource + FCMAT/CSIS — is SACS
re-presented (its finance tables cite "SACS Unaudited Actual Data" as
their source), with an undocumented but open JSON API and a 3,500-row
export cap. Useful as a spot-check surface; not a pipeline foundation,
and not independent. **NCES/Census F-33** covers ~1,040 CA units with
a ~22-month lag; its documentation confirms the data are
CDE-submitted SACS crosswalked to Census categories — an independent
*processing chain*, not an independent *collection*: good as an
optional cross-check on our pipeline, incapable of validating the
SACS collection itself. Nothing found is a better foundation than
CDE's own files.

## 2. Entities — 100% district filing, and the charter structure quantified

**Filers, FY 2024-25** (SACS `LEAs` table): 513 elementary + 346
unified + 72 high-school districts, 58 COEs, 51 JPAs
(ROPs/SELPAs/transport), 5 common-administration filings = **1,045
SACS filers**, plus **574 charters on the Alternative Form**.

**Completeness, measured against CDE's public directory** (18,385-row
schools/districts file, mid-year vintage): after reconciling the five
common-administration filings (two districts filing one report — all
eight "missing" districts are exactly their constituents),
**traditional-LEA completeness is 100.0%. Zero true non-filers.**
Charters: 1,275 of 1,278 directory-active filed (99.8%); the three
non-filers reported zero ADA. This is the structural opposite of
special districts (~1 in 6 non-timely): AB 1200 gives every district a
county-office fiscal overseer and every COE a CDE reviewer, and the
filing chain holds.

**The charter complication, precisely** (from the `Charters` table,
687,029 charter ADA total):

| Filing mode | Schools | ADA share | Dollars |
|---|---|---|---|
| Own SACS submission | 384 | 30.2% | $4.37B |
| Alternative Form (separate archive) | 574 | 50.1% | $5.12B |
| Inside authorizer's books, Fund 09/62 (separable) | 169 | 9.6% | $1.09B |
| Inside authorizer's **Fund 01, commingled — inseparable** | 149 | 10.1% | ≈$1.4–1.5B (est.) |

What this forces: (i) a district-only view silently misses ~$9.5B of
charter spending and misattributes ~$2.5B of dependent-charter
spending as district spending; (ii) summing district and charter
filings double-counts the separable $1.09B unless Fund 09/62 is
netted; (iii) districts book **−$1.78B** of in-lieu-of-property-tax
transfers to charters (object 8096) that reappear as charter revenue;
(iv) the 149 commingled charters (~10% of charter ADA) cannot be
separated from their authorizers at all — a stated limit, not a
guessable one. And the distortion is not hypothetical: **New
Jerusalem Elementary reports 17.8 ADA of its own and sponsors 5,445
ADA of charters** (Oro Grande: 83.5 vs 6,091; Dehesa: 378.5 vs
13,304). Any district figure must carry a sponsored-charter flag
where this ratio is material — it is this layer's contract-city
dagger.

## 3. The reconciliation gate — buildable, to the cent

**CDE publishes an independent per-district total, and raw-ledger
recomputation reproduces it exactly.** The Current Expense of
Education formula (documented by CDE): Fund 01, objects 1000–5999 +
6500 + 7300–7399, minus non-agency goals (7100–7199), community
services (goal 8100), food services (function 3700), retiree benefits
(objects 3701–3702), and facilities (function 8500) — with one
empirically established detail: only district-entity rows
(`SchoolCode = '0000000'`), which resolves all 16 districts that
otherwise mismatch by their in-book charter schools.

Result across **all 932 published districts, FY 2024-25: 932/932
exact to the cent** (LAUSD $10,877,387,458.05 — reproduced
independently twice in this investigation; Alpine County Unified
$3,649,869.58; a 14.6-ADA elementary, $731,135.20). FY 2023-24:
932/933 exact, worst residue $0.02.

**The second gate covers everyone else:** `UserGL_Totals` inside the
database is CDE's own rollup of the ledger — and summing raw `UserGL`
reproduces **every county cell (25,538) and every state cell (1,288)
with zero mismatches** in FY 2024-25 (and zero in FY 2023-24); the
charter Alternative Form's totals table has the same property. So the
gating pattern is: districts gate per-LEA against a published
external total; COEs, JPAs, and charters gate through CDE's published
county/state rollups. This makes K-12 a **gated layer** — the tier
decision the project owner flagged resolves to the top tier, not the
districts tier.

## 4. The denominator — ADA works, with three named distortions

**ADA is in the SACS database itself** (`LEAs.K12ADA` per district,
`Charters.K12ADA` per charter) and is **identical to the Current
Expense file's ADA to the cent** — same vintage, same publication.
Two mechanics to encode: COEs and JPAs carry K12ADA = 0 in SACS
(COE funded-ADA lives in the LCFF Summary "Annual" sheet); and LCFF
*funded* ADA ≠ *attendance* ADA (hold-harmless provisions) — the
Ledger divides by the attendance ADA that CDE itself uses for its
per-ADA statistic, never a mixed vintage.

Per-ADA is honestly comparable for districts **with three structural
footnotes**, each derivable from the data:

1. **Basic aid ("excess tax") districts — the K-12 contract-city
   problem, measured: 127 districts (13.7%)** have local property
   tax above their LCFF entitlement and keep the excess (Palo Alto
   $33,959/ADA vs the statewide $21,214 — 1.60×; Carmel 1.88×;
   Laguna Beach 1.77×). Their per-ADA spending reflects tax-base
   geography, not choices; the flag comes straight from the LCFF
   Summary (local revenue > entitlement).
2. **Necessary-small-school funding:** 127 districts under 100 ADA
   (228 under 250) carry funding floors that produce structural
   per-ADA outliers (Alpine County: ~$70,800/ADA countywide). Flag
   below a size threshold.
3. **Sponsored-charter distortion** (§2): flag districts whose
   separately-reported charter ADA is a material multiple of their
   own.

## 5. The overlap — quantified, connectable, never addable

The state layer's "K thru 12 Education" agency (from this repo's
data.js): **FY 2023-24 enacted $80.4B state funds** (GF 79.3 + SP 0.5
+ BD 0.6; federal $8.2B displayed separately); FY 2024-25 $81.6B.
LEA books (SACS all funds + Alternative Form), FY 2023-24: **$156.8B
total revenues**. The bridge, computed from revenue objects:

| Where LEA money comes from, FY 2023-24 | $B | share |
|---|---|---|
| **State-sourced** (LCFF state aid $47.1 incl. EPA $7.05 + other state $27.1, ex-lottery) | **79.5** | **50.7%** |
| Local property taxes inside LCFF (never in the state budget) | 28.8–29.0 | 18.5% |
| Federal (ESSER tail; falls to $11.8B the next year) | 17.3 | 11.0% |
| Local taxes outside LCFF (GO-bond levies $7.7, parcel taxes $1.8, RDA $0.9) | ~10.4 | 6.6% |
| Lottery, fees, interest, internal items | rest | ~13% |

The state-sourced $79.5B is **98.9% of the state layer's $80.4B** —
the two layers see the same money, from two directions, and agree to
1–3.5% (never to the dollar: enacted appropriations vs year-end
accruals, with Prop 98 revised after enactment). What must be said,
and what the build must render as a computed statement:

1. **"About half of every school dollar is the state layer's K-12
   money, arriving as LCFF state aid, EPA, and categorical programs.
   Most of the rest is local property tax the state never spends,
   and federal grants. Adding this layer to the state layer would
   count the same dollars twice — the Ledger never adds them."**
   (The address-view does-not-add pattern, with these figures
   computed by the pipeline each run.)
2. **EPA** (Prop 30/55, $7–13B/yr) is continuously appropriated
   outside the Budget Act but *inside* DOF's GF display — flag, never
   double-add. **STRS on-behalf** contributions appear in both layers
   at different values ($3.9B enacted vs $3.3B LEA-recognized) — a
   named basis difference.
3. **Not all agency dollars reach LEAs** (CDE state operations, State
   Library, preschool contracts with non-LEA providers), and **LEA
   statewide sums contain ~$3.3B of inter-LEA pass-throughs plus
   $4–5B of internal self-insurance premiums** — any statewide figure
   the Ledger shows is CDE's own published rollup, with the
   pass-through note, or nothing.
4. **Prop 98 is K-14 and counts property taxes** — the guarantee is
   neither the state agency total nor total school funding; the page
   must not present any of the three as the others.
5. **Fiscal years align; federal does not** (multi-year grant
   recognition) — the federal row bridges loosely and says so.

## 6. What the approved build would look like (for scoping only)

One new layer: 932 district records, gated per-LEA to the cent,
compared per-ADA with the three structural daggers; COE and charter
records detail-only under the rollup gate, charter filing-mode on
every record; the commingled-charter limit stated; the overlap
statement rendered from pipeline-computed figures; no cross-layer
sums anywhere; the address view gains a "your school districts"
panel only if district geography is solved separately (school
district boundaries ARE a Census TIGER layer — unlike special
districts — so assignment is feasible; scope it as its own step).
Estimated data weight: in family with city-data.js.

---

## Appendix — reproducibility

- SACS archives: `www3.cde.ca.gov/fiscal-downloads/sacs_data/2024-25/sacs2425.exe`
  (43,941,888 B, Last-Modified 2026-02-04; ZIP-compatible; contains
  sacs2425.mdb, 465,690,624 B) and `…/2023-24/sacs2324.exe`; charter
  Alternative Form: `…/charterdata/2024-25/alt2425data.exe`. Read via
  mdbtools (`mdb-export {db} UserGL` etc.).
- Current Expense of Education:
  `www.cde.ca.gov/ds/fd/ec/documents/currentexpense2425.xlsx`
  ("As of January 29, 2026"; District sheet, data from row 12,
  columns CO/CDS/District/EDP 365/ADA/per-ADA/LEA Type) and
  `…/currentexpense2324.xlsx`. Statewide sheet FY 2024-25:
  $101,236,938,810.13 over 4,772,169.51 ADA.
- Gate test: recompute EDP 365 per the CDE formula (Fund 01; objects
  1000–5999, 6500, 7300–7399; deductions goals 7100–7199 and 8100,
  functions 3700 and 8500, objects 3701–3702; SchoolCode='0000000'
  only; alpha object codes like 'PCRA' fall outside the numeric
  ranges) — 932/932 exact FY 2024-25; re-verified independently for
  LAUSD ($10,877,387,458.05) during synthesis of this finding.
  Rollup gate: sum UserGL vs UserGL_Totals — 0 mismatches across all
  county (25,538) and state (1,288) cells, both vintages.
- Universe: CDE public schools/districts directory (live download is
  bot-gated; Wayback snapshot 2025-05-30 used, 18,385 rows); LEAs
  joined on 7-digit county+district code, charters on 14-digit CDS.
- ADA identity: statewide CE ADA 4,772,169.51 = LEAs.K12ADA
  4,704,001.43 + Fund-01 dependent-charter ADA 68,168.08 (to the
  cent); Alameda USD equal in both files (8,794.74).
- Basic aid: LCFF Summary 2024-25 Annual sheet, district rows
  (n=929): local revenue > total LCFF entitlement → 127 districts
  (cross-check: 130 with net state aid $0).
- Overlap: data.js `budgets["2023-24"]` / `["2024-25"]` K-12 agency
  (gf+sp+bd); SACS revenue objects grouped 8011–8019 / 8020–8089 /
  8090–8099 / 8100–8299 / 8300–8599 / 8600–8799, objects 8800s and
  8900s excluded; Alternative Form revenues included. Ed-Data JSON
  endpoints (undocumented): `ed-data.org/FinanceData/…/{CDS}?year=`;
  F-33 unit file `elsec24.xlsx` (posted 2026-05-07, 14,077 records,
  1,040 CA units).
