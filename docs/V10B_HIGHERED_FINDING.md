# V10b finding — higher education: UC, CSU, and community college districts

*Investigation date: 2026-07-18. New source, treated with V4/V7-level
skepticism: the default answer to "can this ship gated?" was NO until a
control total was demonstrated. Per-system research verified source
URLs and control-total arithmetic against the actual published
documents (the FY2024 UC AFR and FY2023-24 CSU AFR were extracted and
summed). Where a claim is order-of-magnitude, it is labeled.*

**Recommendation, per system — the three do not get the same answer:**

- **CSU — (a) SHIP gated and comparable.** Cleanest of the three. High confidence.
- **UC — (a) SHIP gated, but ONLY as a med-center/lab/auxiliary-stripped education core.** The raw figure is a hospital ledger, not a school's. Medium confidence.
- **Community college districts — (b) SHIP as-filed with the audit-reconciled label, pending an empirical to-the-cent demonstration that would upgrade it to (a).** The reconciliation *mechanism* is the strongest of the three; the *access* is the weakest. Medium confidence.

**And one hard rule spanning all three: this is a layer gated to each
system's OWN audited total — NOT to the state budget line.** The state
page's higher-ed appropriation is a *subset* of these actuals on a
*different basis*. It can share a page only behind a live "these
figures do not add, and are measured differently" statement, exactly
as K-12 already does — never summed, never differenced, never ranked
across systems.

---

## The crux, stated first: two different things called "the gate"

K-12 gates each district to **CDE's published per-entity figure** on
the same basis — an external party recomputes the number. Higher ed
cannot do that against the state, because of the basis mismatch (§4).
What each system *does* publish is its own **audited systemwide
expenditure total** that campus/district figures reconcile to. So a
higher-ed layer is "gated" the way the **city/county** layer is —
reconciled to the entity's own audited control total — not the way
K-12 is (reconciled to a state agency's independent recomputation).
That is a legitimate, strong gate. It is a different claim, and the
site must not let a reader think a UC campus is verified against the
state the way LAUSD is verified against CDE. It is verified against
UC's own auditor.

## UC — University of California

**Recommendation: (a) SHIP gated, as a stripped education core only.**

- **Control total — EXISTS, verified.** UC's Annual Financial Report
  carries a per-campus "Campus Financial Facts" schedule whose
  operating-expense totals **sum to the audited systemwide total to the
  dollar**: the eleven columns (10 campuses + Systemwide) total
  **$54,703,428 thousand** for FY2024, equal to the audited "Total
  operating expenses." The medical-center functional lines likewise sum
  to the reported systemwide medical-center total ($18,843,616K). The
  researcher confirmed both by extracting and summing the PDF. This is
  a real control total to gate each campus against.
- **But the raw number is a hospital ledger.** Medical centers are
  **34.4% of operating expense** and **~47% of operating revenue**
  (funded by patient billing, not tax or tuition); research is ~13%
  (mostly federal grants); Lawrence Berkeley National Lab ($1.15B) is
  DOE-funded. Total-expense-per-student would rank UCSF — a
  health-sciences campus with **no undergraduates** — as wildly
  "expensive" for reasons that have nothing to do with educating
  Californians. Shipping the raw per-FTE figure would be the higher-ed
  contract-city distortion, worse.
- **What ships:** the **education-and-general core** (Instruction,
  Academic support, Student services, Student financial aid) per
  enrollment FTE, gated to the AFR; with **medical centers, research,
  DOE labs, and auxiliaries shown as separate, labeled companion
  totals** ("largely funded by patient-care revenue," "federal sponsored
  research," "DOE-funded") — never folded into the per-student number.
  The AFR's functional lines make this separation possible on the face.
- **Basis: GAAP/GASB accrual; NOT connectable to the state line.** UC's
  AFR-recognized state educational appropriation (~$4.71B GAAP FY24) is
  a different object from the enacted UC General Fund line (~$4.9B
  budgetary-legal) — the V3 enacted-vs-GAAP mismatch. Gate to UC's own
  audit; state connection is overlap-statement only.
- **Build cost is real:** the control total lives in a **PDF, not a
  feed** — per-year table extraction, like the existing Schedule 9
  actuals pipeline (pypdf precedent exists). IPEDS (bulk CSV, every
  campus, GASB) is the machine-readable cross-check and FTE denominator
  but does **not** reconcile to the AFR totals — it is a check, not the
  control total.
- **Confidence: medium** — the gate is verified, but the honest version
  (core-stripping + companion totals + PDF extraction) is real work,
  and if the stripping can't be done cleanly and stably it should drop
  to records-only rather than ship a misleading per-student figure.

## CSU — California State University

**Recommendation: (a) SHIP gated and comparable — the cleanest layer.**

- **Control total — EXISTS, verified.** CSU's audited systemwide
  financial statements publish a hard total (**$11.63B University
  operating expenses**, $13.82B combined-with-component-units, FY2023-24),
  and **Schedule 8 presents all 23 campuses individually audited**. The
  campus columns + systemwide activity + inter-entity eliminations
  reconcile to the University total (researcher: sum(23 campuses) $11.33B
  + ~$0.30B systemwide/eliminations = $11.63B).
- **Cleanest cross-campus comparison in California higher ed:** **no
  medical centers, little organized research.** Campus operating
  expense is genuinely education. Auxiliaries (foundations, associated
  students, housing — ~$2.38B, ~17% of combined) are **discretely
  presented component units**, cleanly excluded by dropping that column.
- **Denominator:** per-FTE-student (annualized FTES), published
  systemwide and per campus — the honest within-system comparator.
- **Basis: GAAP/GASB; NOT reconcilable to the enacted CSU line.** The
  audited all-funds University total is not the enacted appropriation
  (~$6.18B GF for 2026-27, ~65% of a ~$14.9B budgetary total), and CSU
  releases no budgetary→GAAP reconciling statement. Gate to CSU's own
  audit; overlap-statement to the state.
- **One honest gate caveat to state on the face:** the systemwide total
  reconciles *with eliminations*, not as a bare sum of campus rows — so
  label it "reconciled to CSU's audited systemwide total (with
  inter-entity eliminations)," not "sums to the cent from campus rows."
- **Build cost:** a ~301-page PDF, no feed — PDF extraction like UC and
  like the state Schedule 9. IPEDS is the all-campus machine-readable
  cross-check.
- **Confidence: high** — real control total, individually audited
  campuses, no health/research distortion, clean auxiliary separation.

## Community college districts

**Recommendation: (b) SHIP as-filed with the audit-reconciled label —
upgradeable to (a) only after an empirical to-the-cent demonstration.**

- **Reconciliation mechanism — strongest of the three, in principle.**
  Every district's CCFS-311 annual report is (a) certified by the
  district Chief Business Officer and (b) **reconciled by a mandatory
  independent CPA audit** to the district's GAAP statements (Ed Code
  84040; Contracted District Audit Manual; Title 5). A tiny stable
  universe — **72 districts, ~100% filers** — on a uniform Budget and
  Accounting Manual chart. That is a *stronger external control than
  K-12's* (an independent audit, not a recomputation).
- **But it was NOT demonstrated to the cent, and the access is the
  weakest.** No published machine-readable statewide control-total file
  was confirmed; the CCFS-311 fiscal portal is **one-district-at-a-time
  HTML with no export/API**, DataMart carries no fiscal data, and the
  audit reconciliations are **buried in per-district PDFs**. So the gate
  is *mechanism-confirmed, empirical reconciliation pending*. The honest
  status today is as-filed-with-audit-label, not K-12-grade gated.
- **Tractable because the universe is 72, not thousands** (unlike
  special districts): scripted per-district extraction of CCFS-311 +
  join to each audited statement is feasible. **Before claiming a
  to-the-cent gate, the reconciliation must be demonstrated on 2-3
  districts** (this finding did not do it — no build was run).
- **Comparable core:** the **General Fund (unrestricted + restricted)**,
  per **FTES** — but FTES is a *separate filing* (CCFS-320) from the
  dollars (CCFS-311), so the join carries a vintage/definition-mismatch
  risk that must be daggered. Enterprise/proprietary funds (bookstores,
  cafeterias, parking) and fiduciary funds shown **separately, never in
  the operating per-FTES figure**; foundations are separate 501(c)(3)s
  **outside CCFS-311 entirely** (a K-12-charter-style undercount to note).
- **Basis: modified accrual (BAM). The ONLY system connectable to the
  state line — for the state-aid slice only.** State aid flows through
  SCFF apportionment (FTES-driven); the Prop 98 community-college
  guarantee is a *K-14* number that also counts local property tax, and
  is neither the CCC agency total nor total district spending. A
  does-not-add bridge to the state's community-college line is possible
  for the state-aid portion — a bridge, never an identity.
- **Distortions:** single-college vs multi-college districts; basic-aid
  ("community-supported") districts whose property tax exceeds their
  SCFF entitlement.
- **Confidence: medium** — the control is strong on paper; the build
  hinges on scraping 72 portals/PDFs and proving the reconciliation,
  and on the two-filing FTES join.

## The overlap question — the same double-count K-12 has, per system

The state page's enacted higher-ed appropriation **flows into** these
institutions and is therefore **already inside** each system's actuals.
Placing "state enacted = $X" beside "system spent $Y" invites a reader
to add them — but $X is a *subset* of $Y, not an addend. State share of
each system's total expense differs by design, and that difference is
the whole point:

| System | State funds as share of total spending | (order of magnitude) |
|---|---|---|
| UC | **~8–9%** of ~$54.7B total operating expense | single digits — because hospitals, research, tuition dominate |
| CSU | **~45–55%** of University-only opex | roughly half |
| CCC | **the majority** (Prop 98 / SCFF) | most |

Required on any page that shows both, computed live like the K-12
overlap block, never hardcoded:

1. *"The state's enacted appropriation to [system] is already included
   in [system]'s total spending shown here — a portion of that total,
   not an additional amount. Do not sum them."*
2. *"The two are measured differently: the state figure is an enacted
   budgetary-legal authorization; the institution figure is audited
   GAAP/GASB accrual expense. They are not reconciled to each other."*
3. The overlap share, quantified per system, inline.

They may share a page only as two explicitly-labeled measures with the
non-additivity statement between them — **never a single stacked total,
never a "state gave X, they spent Y, gap = Y−X" framing.** Only CCC's
state-aid slice is genuinely bridgeable, and even there as a
does-not-add bridge, not an identity.

## Cross-system comparison — refused as a ranking

Per-FTE **across** UC, CSU, and CCC is **not honest as a ranking** and
must never be a leaderboard. The three have different statutory missions
(UC: doctoral/research + academic medicine; CSU: comprehensive teaching;
CCC: open-access lower-division/vocational), so per-FTE differs *by
design, not by efficiency.* Even after stripping to a comparable core,
a research university's cost basis legitimately exceeds a teaching
campus's, which exceeds a community college's. Comparison is valid
**within** a system (campus vs campus, shared mission and basis). Across
systems it may appear only as side-by-side, identically-defined-core,
**mission-labeled** figures with an explicit "differences reflect
mission, not performance" caveat — never a raw (unstripped) per-FTE,
never a single ranked number, never an implication that lower per-FTE is
"better value." This is the Ledger's existing "cities and counties are
never compared" rule, applied to three missions instead of two.

## The single biggest trap

**Treating dollars as additive and comparable when they are neither.** A
naive build would (a) set the enacted state higher-ed line next to each
system's total actuals and let readers sum the same dollars twice, and
/or (b) build one cross-system per-FTE leaderboard on raw totals that
ranks UC "most expensive" almost entirely on hospital billing, research,
and a national lab CSU and CCC structurally don't have. The compound
error is doing both — summing enacted-state + GAAP-actuals across three
incommensurable bases and three missions into one number. The fix is the
K-12 pattern per system: a live quantified does-not-add statement, a
defined stripped core, and same-basis, mission-labeled, side-by-side
presentation with no arithmetic that combines the state line with the
institution line.

## Recommendation summary

| System | Verdict | Gate | Denominator | Basis→state | Biggest caveat |
|---|---|---|---|---|---|
| **CSU** | **(a) SHIP gated & comparable** | CSU audited systemwide total (with eliminations), 23 campuses individually audited | per-FTE | overlap-statement only (~45–55%) | PDF extraction; gate ≠ bare campus-row sum |
| **UC** | **(a) SHIP gated, stripped core only** | AFR Campus Financial Facts → audited $54.7B systemwide | per-FTE, **core only** | overlap-statement only (~8–9%) | med centers 34% — must strip & show separately, or drop to records-only |
| **CCC** | **(b) SHIP as-filed w/ audit label; (a) after empirical proof** | CCFS-311 ↔ mandatory CPA audit (mechanism confirmed, cents unproven) | per-FTES (separate CCFS-320 filing) | does-not-add bridge for state-aid slice only | scrape 72 portals/PDFs; prove reconciliation before claiming gated |

None of the three is softened to make it possible: UC's control total
is real but its raw number is a hospital, so it ships only stripped;
CSU is genuinely clean and ships; CCC has the strongest control on paper
but unproven-to-the-cent and worst access, so it ships as-filed until an
empirical reconciliation earns the gated tier. All three are gated to
themselves, never to the state, with a mandatory live overlap statement
— and cross-system comparison is refused as a ranking.

---

*Sources (all verified to resolve; per-system detail with URLs in the
session research record): UC Annual Financial Report
(ucop.edu/uc-controller/financial-reports; FY2024 PDF extracted, campus
totals summed to $54,703,428K); CSU Annual Financial Report
(calstate.edu; FY2023-24 PDF, Schedule 8, $11.63B University total);
CCFS-311 fiscal portal and Contracted District Audit Manual
(cccco.edu; Ed Code 84040); IPEDS Finance (nces.ed.gov/ipeds,
bulk CSV/Access, all campuses, GASB — cross-check and FTE denominator,
NOT the control total); SCO Government Compensation
(publicpay.ca.gov / gcc.sco.ca.gov — payroll cross-check only).
State-share percentages are order-of-magnitude from these figures and
standard California budget structure; a build would compute them live.*
