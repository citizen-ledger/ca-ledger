# V8 finding: how deep the drill-down can honestly go, per layer

_Investigated 2026-07-14. No UI or pipeline was built; this document is
the deliverable. Every sum test below ran on real data — full
populations where feasible, always at least one large and one small
entity — and the residuals reported are measured, not assumed. The
decisive question, per the project owner: children that do not sum
exactly to the gated parent are worse than no drill-down._

## Summary verdict

| Layer | Depth available | Child-sum residual (measured) | Payload cost | Recommendation |
|---|---|---|---|---|
| State — funds | fund detail per department (G/S/B/F(/N/R)) | **$0 for 188/188 departments**, FY 2024-25; $0 on a 20-dept second-year sample | +361–942 KB over 6 yrs (data.js 355 KB) | **SHIP** — the data is already fetched and discarded |
| State — programs | program per department, with names | internally exact 187/187, **but all-funds scope: +$215.2B statewide vs our parents** | +198–328 KB | **SHIP ONLY as a labeled all-funds view** with explicit N/R rows; never under the gf/sp/bd/fed parents as-is |
| State — item level (4260-101-0001) | **does not exist in the API** (PDF only) | — | — | Nothing to ship |
| Schools (SACS) | function × object-family; restricted/unrestricted; resource | **$0.00 for 2,797/2,799 district-years at every depth** (2 = the known $0.02 publication artifact) | +2.06 MB (fn×family), +145 KB (restr/unrestr), +1.43 MB (resource), +5.5 MB (full object) | **SHIP fn×object-family + restricted/unrestricted**; resource optional with caveat; full 4-digit object DON'T (payload) |
| Cities | 237-line statewide form below our functions | exact at source precision; ≤$497/function vs shipped rounded figures | +1.85 MB (all), +1.0 MB governmental-only (city-data.js 1.47 MB) | **SHIP governmental-only, whole-dollar children** |
| Counties | 653-line form: **activity × fund type** (District Attorney, Assessor, Elections…) | exact at source precision; ≤$441/entity total | +0.65 MB | **SHIP** — the most legible drill on the site |
| Special districts | fixed ~9.5-line form per district-year | $0 exactly — but same-source additivity, not reconciliation | +4.7–7.6 MB inline; per-entity slices need ~5,257 files under file:// | **DON'T SHIP** — tier unchanged, payload hostile, and the hospital gross-vs-net trap makes lines actively misleading; the SCO deep link already on every record IS the drill |

**A side-finding outranks the question asked:** the investigation
found a **confirmed bug in shipped city-data.js** — FY 2016-17
`byFunction` is misclassified for all 482 cities (the FY2017 source
vintage shifts columns; Los Angeles ships `{other: 6716.196, debt,
capital}` with **no police or fire**, against $2,609.6M police the
next year — re-verified during synthesis). The reconciliation gate
passed because it gates totals, not classification. Counties 2016-17
verified correct. A repair task was spawned separately; whatever
happens with drill-downs, this fix comes first, and any depth build
must add a classification-shape gate (children non-empty per expected
function) so a column shift can never pass silently again.

---

## 1. State (eBudget)

**What exists below department (complete endpoint inventory, from the
app bundle, all verified live):** `orgProgram/{orgCd}` — one row per
program with `programCode`, `programTitl`, and prior/current/budget-year
dollars and positions; `rwaCntl/support/{orgCd}` and
`rwaCntl/capOutlay/{orgCd}` — one row per fund with fund code, legal
title, and class (G/S/B/F/N/R); plus project lists, HTML program
narratives, and fund-condition statements. **Nothing below
program/fund exists** — appropriation items (the 4260-101-0001
format), object of expenditure, and program×fund all 404; item detail
lives only in the PDF "Detail of Appropriations and Adjustments."

**The fund drill is free and exact.** Our pipeline already downloads
the fund rows for every department-year to compute the federal toggle
— then throws everything else away. Summing support+capOutlay rows by
class reproduces the published gf/sp/bd/fed **exactly ($0) for all
188 departments with fund rows, FY 2024-25** (the 6 without rows have
$0 parents), $0 on a 20-department FY 2020-21 sample, and was
re-verified during synthesis for DHCS against data.js. Fund names are
legal fund titles, in-row. Payload: +361 KB (deduplicated names) to
+942 KB across six years.

**The program drill is honest only on its own terms.** Programs sum
exactly to the API's own all-funds totals (187/187), but that scope
includes nongovernmental-cost (N) and reimbursement (R) classes our
gated figures deliberately exclude: statewide the overhang is
**+$215.2B** (UC +$43.8B, CalPERS +$42.5B…), DHCS alone +$4.11B —
exactly its N + R rows. Ten departments publish $0 parents while
carrying program dollars (STRS: $21.5B). R rows are payments from
other departments — the pass-through double-count we already police
elsewhere. So: programs ship only as an explicitly labeled
**all-funds view** whose children sum to a displayed all-funds
department total, with N and R shown as named rows bridging to the
gated gf/sp/bd/fed figure — or not at all. Program-level prior-year
"actuals" columns must NOT ship as actuals: departments that
dissolve drop out of later publications, and the statewide PY sum
undercounts the gated Schedule 9 actuals by **−2.2% GF / −7.1% SF**.

Traps to encode: 8 negative fund rows (Pro Rata GF −$992M; PSSSA
−$1,054M), 32 negative program lines ("Administration – Distributed",
loan repayments, property-tax offsets), infrastructure sitting
outside program lines (support+capOutlay must combine), program
labels that change code and name year-over-year (no honest program
time series), and 622 of 1,574 fund rows under $0.5M that vanish at
the site's 3-decimal-billions display — **children must ship in
thousands as integers**.

## 2. Schools (SACS)

**Dimensionality inside the gated scope** (Fund 01 EDP-365 filter):
45 objects, ~143–149 resources, 25 goals, 69 functions; at the
natural next rung — the shipped 9 function groups × 7 object families
— an average district has **28.7 cells** (LAUSD 35, Alpine 28).

**The sum test is a clean sweep.** With exact-cents arithmetic
(verified first that no ledger value carries more than 2 decimals):
function-group × object-family, function × 4-digit object, resource
level, and restricted/unrestricted **all sum to the gated Current
Expense figure with $0.00 residual for every district-year tested —
globally 934/934, 932/933, 932/932 across the three years** — the
single exception being San Diego Unified's known $0.02 publication
rounding artifact, whose internal detail partition is itself $0.00.
Resource 7690 (STRS on-behalf) is cleanly visible per district
(LAUSD $368.1M in FY 2024-25) but small districts don't book it
consistently (Alpine: $0 in two of three years) — a resource drill
carries a comparability caveat.

**Payload decides the depth:** fn-group × object-family costs
+2.06 MB raw over three years (school-data.js is 1.99 MB — roughly
doubles); restricted/unrestricted is nearly free (+145 KB); resource
level +1.43 MB; **full 4-digit object depth (+5.55 MB, ~4× the file)
is hostile to the double-click requirement — don't.**

Traps, all measured: intra-fund cost-transfer objects (5710/7310) net
to ~$0 per district but not within a function group, and interfund
5750/7350 don't net at all — 652 of 26,738 fn×family cells are
negative (LAUSD's genAdmin other-outgo cell is **−$39.3M**), so a
child view must render negative segments honestly; alpha codes share
the same Fund 01 rows (`979Z` calculated ending balances, **$36.9B
statewide**, and `PCRA`, the one code with no official title) and
must never leak in; the EDP deductions (~$1.40B statewide: retiree
benefits, facilities, food services, community services) mean a
"show me everything in the General Fund" child would overshoot the
gated parent — the drill must stay inside the exact published
formula and say what is excluded; and code values collide across
dimensions (6500 is an object AND a resource) so lookups are
per-dimension. Every code in scope has an official CDE title in the
same database, except `PCRA`.

## 3. Cities and counties (SCO)

**The "function is the floor" belief is refuted.** Below our
functions both datasets carry a fixed statewide form — zero-filled,
identical labels for every entity: **cities, a 237-line form**
(San Francisco alone gets 268, its consolidation extending to 31
county-function lines); **counties, a 653-line form of activity ×
fund type**. The county lines are the most legible drill anywhere in
this investigation: District Attorney – Prosecution, Public Defender,
Assessor, Elections, Grand Jury — real offices, official form names,
no crosswalk to invent. City depth is thinner where it matters most:
police and fire are single lines (the depth is in streets, housing,
capital, health). **No deeper dataset exists on the portal** — a
full catalog sweep (170 assets) found no object-level or
checkbook-grade data; the FTR form line is the floor of California
local-government transparency.

**Sum test:** the published functions are sums of these same rows,
and at source precision the identity is exact. Against the *shipped*
rounded figures (millions, 3 decimals) the worst residual measured
was **$497 on a function** and $441 on an entity total — pure display
rounding. Two rules follow for any build: **children ship in whole
dollars**, and children reconcile to the unrounded parent (checking
rounded-vs-rounded would show phantom drift in 756 of 4,738 city
cells).

**Payload:** counties +0.65 MB (comfortable atop 0.23 MB); cities
+1.85 MB full or **+1.0 MB governmental-only** — the recommended
scope, matching what the comparison view gates. Under file:// there
is no lazy per-entity fetch without emitting hundreds of script
files, so this ships inline or not at all.

Traps: real negative lines (Santa Clara County's
`Auditor-Controller_General` is negative **every year** — netted
cost-allocation reimbursements — FY 2023-24 −$165.2M); unlabeled
`Other X` slots that dominate some functions (90.4% of county
Public Assistance–Other; 84.9% of city Public Utilities statewide) —
label them "not itemized in the state form"; form drift (the FY2017
city column shift — the source of the shipped-data bug above — and
county form growth 644→653 lines) requiring per-year line
dictionaries; ISF and conduit detail that exists in the rows and must
stay excluded or children exceed parents.

## 4. Special districts

Detail exists — a ragged 4-level hierarchy that is really a ~9.5-line
standardized form per district-year (MWD, a $1.8B agency, files 17
expenditure lines; the maximum anywhere is 51) — legible, and
summing to the published buckets with **$0 residual across all 32
entity-year cells tested** (values are whole dollars; rounding cannot
break it). But: (i) this is **same-source additivity, not
reconciliation** — the line level is exactly as unverifiable as the
bucket level, and the as-filed tier caveat would have to sit on every
level verbatim; (ii) payload is hostile — +4.7 MB at the most
aggressive inline encoding (~3× district-data.js), ~73 MB naive, and
per-entity lazy slices would require ~5,257 script files to survive
file://; (iii) **the hospital trap**: healthcare districts file gross
patient charges netted by negative contractual-adjustment lines
(−$143.5B across the window; a single Palomar Health row is
**−$3.17B**) — a line view would show phantom multi-billion revenue
beside multi-billion negatives, actively more misleading than the
bucket. **DON'T SHIP depth here.** Every district record already
deep-links to SCO's own explorer — that is the drill, at zero
payload and zero tier confusion.

## 5. Cross-cutting rules for any approved depth build

1. **Children sum to the unrounded parent, exactly, as a CI gate** —
   the same discipline as every existing gate, extended one level
   down (state funds: $0; SACS: $0.00; SCO: source-exact,
   whole-dollar children).
2. **Children ship as integers in source units** (thousands for
   state, dollars elsewhere); display rounding never feeds arithmetic.
3. **Negative children render honestly** — they are structural
   (distributed administration, cost-allocation nets, transfer
   objects), not errors; each gets its one-line explanation in the
   methodology, never a hidden clamp to zero.
4. **Excluded scopes stay excluded at depth** (ISF/conduit, EDP
   deductions, N/R fund classes except as explicit labeled bridge
   rows) — and the exclusions are stated where the drill happens.
5. **A classification-shape gate joins the totals gate** (the lesson
   of the FY 2016-17 city bug): per entity-year, expected children
   must be non-empty where the form guarantees them.
6. Labels: every layer's depth carries official names in the source
   itself (fund legal titles, CDE code tables, FTR form lines) —
   **no crosswalk needs inventing anywhere**, and the one untitled
   code found (`PCRA`) stays excluded by construction.

## Appendix — reproducibility

- State: endpoint inventory from ebudget.ca.gov app bundle
  (23 paths); sum tests via
  `api/publication/e/{yr}/rwaCntl/support|capOutlay/{org}` and
  `orgProgram/{org}` vs data.js (DHCS 4260, San Diego River
  Conservancy 3845, Parks 3790; full 188-dept sweep FY 2024-25;
  20-dept FY 2020-21 sample). Program overhang = N+R classes,
  itemized per department. PY-column statewide sums vs gated
  Schedule 9: GF −$4.36B (−2.2%).
- SACS: `pipeline/cache/schools/sacs{2223,2324,2425}.mdb`, exact-cents
  aggregation; per-depth partitions vs `currentexpense{yy}.xlsx`;
  machine-readable results preserved in the session scratchpad
  (`depth_report.json`). Trap magnitudes: 979Z $36.93B; deductions
  $1.40B; LAUSD genAdmin|7350 −$39.28M.
- SCO: schemas via `api/views/{id}.json`; per-line sums via SODA
  `$group` for LA/Amador City (ju3w-4gxp) and LA/Alpine counties
  (uctr-c2j8, value column `values`), FY 2023-24, all functions;
  catalog sweep `api.us.socrata.com/api/catalog/v1?domains=…` (170
  assets). Bug reproduction: `city-data.js` →
  `cities["los-angeles"].years["2016-17"].byFunction`.
- Districts: m9u3-wdam/nkv3-m73r grouped sums vs district-data.js for
  Metropolitan Water District and Camptonville Cemetery District,
  all 8 years, exp and rev (32 cells, $0). Negative-line census:
  5,958 REV rows, −$143.5B, dominated by hospital contractual
  adjustments.
