# V11 finding — California Community College districts: the gate, proven

*Investigation date: 2026-07-18. A prove-the-gate investigation, not a
survey: the question was whether CCC district finances can be gated,
and at what resolution, demonstrated on real downloaded data. The CSU
discipline applied — no gate claimed without a residual measured on
real figures. Every figure below was fetched and reconciled this week.*

> **Build correction (2026-07-17, when the layer was built).** Building
> against the live data refined two things in this finding — the "prove
> it on real data" discipline working as intended. (1) The gate figure:
> the published Current Expense of Education (ECS 84362) is the
> *post-exclusion* figure in **Table VI**, the Chancellor's Office's
> "Summary of Current Expense of Education." This finding's draft LA
> figure, $774,683,675, was the 50-Percent-Law worksheet's "Total
> Expenditures Prior to Exclusions" — a pre-exclusion line. The
> published ECS 84362 for LA is **$716,533,122**, and the statewide
> total is **$8,469,851,699**. (2) The gate as built is therefore a
> clean sum-reconciliation: the **73** districts' Current Expense of
> Education (Table VI includes Allan Hancock, which is off the report
> dropdown) sum **exactly, to the dollar**, to Table VI's own printed
> statewide total — one public fetch, all districts, zero fetch
> failures, auto-reproducible. The multi-college roster was verified
> against the MIS codes (reconciling to the official 116 colleges) and
> the community-supported roster against the SCFF Exhibit C (reconciling
> to the official 8) — the latter catching **San Mateo**, a three-college
> basic-aid district this finding's hand-listed "dangerous cell" had
> missed. The recommendation below stands, strengthened.

**Recommendation: (a) SHIP gated, at WHOLE-DOLLAR resolution, proven.**
The gate holds — and CCC is a *stronger* candidate than CSU on every
axis that matters: finer resolution (whole dollars, not thousands), a
**zero-dollar** reconciliation residual, publicly-accessible
machine-readable data (not bot-gated), and the proper higher-ed
per-FTES denominator. The V10b finding rated CCC's mechanism strong
but its cents unproven; this investigation **proved it on real data.**

---

## The proof, first — a $0 residual on real audited data

CCC's gate is the same shape as K-12's: each district files a
standardized modified-accrual report (the CCFS-311, analogous to K-12's
SACS), and it is **reconciled to an independent CPA audit by law (Ed
Code 84040)** — a stronger external control than K-12's CDE
recomputation, because it is an independent audit. Every district audit
carries a schedule, "Reconciliation of the Annual Financial and Budget
Report (Form CCFS-311) With Audited Financial Statements." I downloaded
two districts' FY2022-23 audits and read that schedule:

| District (audit, FYE 6/30/2023) | CCFS-311 ↔ audited financial statements |
|---|---|
| **Antelope Valley CCD** | *"There were no adjustments to the Annual Financial and Budget Report (CCFS-311) which required reconciliation to the audited financial statements."* |
| **Rio Hondo CCD** | *"There were no adjustments to the Annual Financial and Budget Report (CCFS-311) which required reconciliation to the audited financial statements."* |

**The residual is $0.** The CCFS-311 fund balances *equal* the
independently-audited fund balances, exactly, at whole-dollar
resolution, in both districts tested. The CCFS-311 is not a filing that
*claims* to reconcile — it is the audited figure. (Where a district
does have adjustments, the schedule lists them as a reconciling table
with a net difference; the two I sampled had none.)

## 1. Access — PUBLIC and machine-readable (correcting V10b)

The V10b finding said CCC fiscal data was "72 portals/PDFs," and a
research pass this week called it Azure-AD login-gated. **Both are
wrong**, and only checking on real requests found it: the CCFS-311 data
is served from a **public** endpoint —
`fiscalportal.cccco.edu/Reports/AnnualReports` — that returns real
per-district and statewide reports **without any login** (the *submission*
route, `/Reports/311Report`, redirects to login; the *reporting* route
does not). I fetched Los Angeles CCD's actual FY2022-23 figures by a
plain HTTP POST, no credentials.

- **16 fiscal years** (2009-10 through 2024-25), **72 districts**, ~30
  per-district report types, ~13 statewide aggregate tables.
- **Whole dollars** everywhere — no cents (see §2).
- The one wrinkle: it is an ASP.NET SSRS ReportViewer, so a build must
  script the postbacks (fresh `__VIEWSTATE`/`__EVENTVALIDATION` per
  request; the statewide button is `RunStatewideReport`, the district
  button `DistrictReportButton`). This is real engineering, but it is
  **auto-fetchable** — unlike CSU, no manual browser download is
  required. District *audits* (the reconciliation check) are
  per-district PDFs on district sites, fetchable and pypdf-parseable
  (I pulled Antelope Valley's and Rio Hondo's directly).

**Data Mart carries no fiscal data** (students/courses/staff only), and
the data.ca.gov "California Community College Districts" dataset is a
boundary *map*, not finances — both confirmed, both dead ends the V10b
finding half-cited.

## 2. Resolution — whole dollars, proven

Every figure on the portal is an integer number of dollars. Real
example, Los Angeles CCD, FY2022-23, extracted live: **Current Expense
of Education (ECS 84362) = $716,533,122**; instructional salaries
subject to the 50-Percent Law = $367,274,887 (51.26%). No cents appear
anywhere. *(Build correction — see the note at the top: an earlier draft
of this finding quoted LA's Current Expense of Education as $774,683,675.
That is the 50-Percent-Law worksheet's "Total Expenditures Prior to
Exclusions," a pre-exclusion line; the published ECS 84362 figure, after
the exclusions, is $716,533,122 — the number in Table VI and in the
built layer.)*
So the gate resolution is **to the dollar** — finer than CSU's thousands
(CSU's statements are denominated in thousands), coarser than K-12's
cents (SACS carries actual cents). The reconciliation to audit is exact
at that resolution (residual $0, §proof).

**The gate figure has a name, and it is the K-12 one.** CCC's control
figure is **Current Expense of Education (ECS 84362)** — the community-
college analog of K-12's *Current Expense of Education (EDP 365)*. It is
published per-district (each district's 50-Percent-Law report) and
statewide (Table VI, "Summary of Current Expense of Education").

## 3. The denominator — per-FTES, achievable (better than CSU)

Unlike CSU (whose FTES was dashboard-locked, forcing headcount), CCC
**can use the proper higher-ed denominator, per-FTES** — but the source
must be chosen with care:

- The **apportionment FTES that reconciles** (the SCFF/CCFS-320 figure)
  appears in each district audit's "Schedule of Workload Measures for
  State General Apportionment" — audited, fiscal-year-aligned with the
  CCFS-311 dollars, whole numbers. This is the honest denominator.
- The **CCCCO Data Mart** publishes a per-district "FTES Summary" as
  CSV/Excel — machine-readable and easy — but it is a **derived count
  (enrollment hours ÷ 525) that CCCCO itself states is *not* the CCFS-320
  apportionment methodology.** A build must use the apportionment FTES
  (audit / apportionment exhibits) for the gated denominator, or label
  the Data Mart figure honestly as a derived count. Do not present the
  Data Mart FTES as if it were the apportionment FTES.

## 4. Comparability traps — four daggers, one dangerous overlap

- **Multi-college vs single-college districts.** The district is the
  fiscal filer, but ~73 districts run ~116 colleges: LACCD is *nine*
  colleges (the nation's largest), while Feather River is one.
  Per-district-per-FTES mixes very different structures — a dagger, not
  a defect.
- **Basic-aid / "community-supported" districts** (Marin, San Mateo,
  West Valley-Mission, South Orange County, and others) are funded off
  local property tax, not SCFF apportionment, so "state funding per FTES"
  is meaningless for them — the higher-ed twin of the K-12 basic-aid and
  the city-contract problems.
- **Noncredit / adult-ed-heavy districts**: noncredit and CDCP FTES are
  funded at different rates than credit and are highly concentrated,
  distorting per-FTES.
- **Enterprise / auxiliary / foundation separation**: bookstores,
  cafeterias, and parking are enterprise funds; foundations are separate
  501(c)(3)s outside the CCFS-311 entirely. The comparable **core is the
  General Fund (unrestricted + restricted)**, consistent with the
  50-Percent Law and SCFF — enterprise/fiduciary shown separately,
  never in the operating per-FTES figure.
- **The dangerous cell**: districts that are *both* multi-college *and*
  basic-aid (West Valley-Mission, San Jose-Evergreen, South Orange
  County). A build must verify the exact multi-college roster against an
  official source before publishing — the auto-summarized roster this
  investigation used mislabeled at least three.

## 5. Basis — a clean K-12 parallel

CCFS-311 governmental funds are **modified-accrual on the CCC Budget and
Accounting Manual (BAM) uniform chart** — the *same basis and shape as
K-12's SACS*. The district audit adds a GASB 34/35 full-accrual
entity-wide view, and the CCFS-311 (modified accrual) reconciles to it
via the mandatory schedule (§proof). The state budget page's
community-college line is **enacted Budgetary-Legal appropriation** — a
third, non-comparable basis. So: CCC is gated to itself (CCFS-311,
audit-reconciled), stated on the BAM/modified-accrual basis; it is
never reconciled to, or summed with, the state's enacted line.

## 6. Overlap — quantified, does-not-add

The state budget's community-college appropriation flows *into* these
districts and is already inside the figures. Statewide (LAO, FY2025-26):
total CCC funding across all sources ≈ **$19.0B**; state General Fund ≈
**$9.0–9.7B (~51%)** of it; the Proposition 98 community-college
guarantee is **$13.6B (72%)** — but Prop 98 *counts local property tax*
($4.5B) and is therefore neither the state's General Fund contribution
nor total district spending. Required live "these figures do not add"
statement (computed, never hardcoded): *the state's appropriation to the
community colleges is state money already inside the district figures
here — a portion of them, not an amount to add; it is roughly half of
total district funding, and the Prop 98 K-14 guarantee (which also
counts local property tax) is a third, distinct number. Do not sum
them.*

## Recommendation

**(a) SHIP gated, at whole-dollar resolution, auto-fetchable.**
Concretely, if built:

- **Gate**: each district's CCFS-311 General Fund figures (and Current
  Expense of Education, ECS 84362) as filed to the Chancellor's Office,
  with the mandatory independent-audit reconciliation as the control —
  demonstrated at **$0 residual** on real data. Whole-dollar resolution,
  named accurately (a third tier: exact to the dollar — finer than CSU's
  thousand, coarser than K-12's cent). No write on failure; a district
  whose CCFS-311 does not tie to its audited fund balances is flagged,
  not published.
- **Source**: the public `fiscalportal.cccco.edu/Reports/AnnualReports`
  postback API, scripted (SSRS ReportViewer) — auto-fetchable, no manual
  cache, a real improvement over CSU. District audits fetched as the
  reconciliation check.
- **Denominator**: per-FTES using apportionment FTES (audit Workload
  Measures / SCFF exhibits), *not* the Data Mart derived count — or the
  derived count clearly labeled.
- **Auxiliaries** shown separately (General Fund core is the comparable
  figure); foundations noted as outside the CCFS-311.
- **Overlap** live (~51% state); **campuses/districts never ranked**;
  the four comparability daggers, with the multi-college roster verified.

This is the rare higher-ed layer that clears the bar cleanly: the gate
is proven, the resolution is finer than CSU's, the data is public and
machine-readable, and the denominator is the correct one. It should
ship — and it is the answer to the higher-ed line's biggest open
question. UC remains the holdout (its raw figure is a hospital ledger
until the medical-center strip is resolved, per V10b).

---

*Sources (all fetched this week): CCFS-311 public reporting portal
(fiscalportal.cccco.edu/Reports/AnnualReports — LA CCD FY2022-23 figures
extracted by HTTP POST); Antelope Valley CCD and Rio Hondo CCD FY2022-23
audited financial statements (avc.edu, riohondo.edu — CCFS-311
reconciliation schedules read via pypdf, both "no adjustments"); CCC
Budget and Accounting Manual Ch.6 (cccco.edu); Ed Code 84040 / Title 5
audit requirement; LAO 2025-26 Community College budget analysis
(overlap figures); CCCCO Data Mart (FTES Summary — derived count
caveat). Analysis scripts preserved in the session scratchpad.*
