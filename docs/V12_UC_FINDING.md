# V12 finding — University of California: gated and strippable, on UC's own terms

*Investigation date: 2026-07-18. A prove-the-gate investigation, not a
survey: the question was whether the University of California — deferred
in V10b because medical centers dominate its raw figure — can be
published as a stripped, gated core defined by UC's OWN published
categories, never by our judgment about what counts as "education."
Every figure below was fetched and reconciled this week from UC's actual
published statements; both fiscal years' gates were run on real
downloaded data. The CSU and CCC disciplines applied.*

**Recommendation: (a) SHIP stripped and gated — exact to the thousand,
strip defined entirely by UC's own functional lines, auto-fetchable.**
The gate holds at a **zero residual in both of the two most recent
fiscal years**, the strip requires no judgment of ours (UC itself
publishes "Medical centers," "Auxiliary enterprises," and "Department
of Energy laboratories" as separate lines, per campus, in its own
Annual Financial Report), and the source is public and scriptable —
no bot-gate, no manual cache. One honest limit must be carried on the
face of the layer: UC's strip removes the hospital *enterprises*, not
the schools of medicine — and the finding quantifies exactly what that
means (§4).

---

## The proof, first — a zero residual, two years running

UC's Annual Financial Report carries, in its own front matter, a
**"Campus Financial Facts"** table: operating expenses **by function,
per campus**, for all ten campuses, plus a **"Systemwide"** column
(UCOP, the DOE laboratory, systemwide programs, and eliminations —
several of its cells are negative) **with its own printed total**. The
gate is whether ten campuses plus UC's own printed Systemwide column
reproduce the audited statement total. They do — exactly, both years:

| Fiscal year | Sum of 10 campus totals | + Systemwide column (printed) | = | Audited total operating expenses | Residual |
|---|---|---|---|---|---|
| **FY 2024-25** | $58,074,198K | −$306,871K | $57,767,327K | **$57,767,327K** | **$0K — EXACT** |
| **FY 2023-24** | $52,003,294K | +$2,700,134K | $54,703,428K | **$54,703,428K** | **$0K — EXACT** |

This is *stronger* than the CSU gate in one respect: CSU's reconciling
line is computed by the pipeline as a residual; UC **prints its own
reconciling column**, so the identity is verified against two published
figures, not one published figure and a plug.

**Resolution: exact to the thousand.** Like CSU, UC's statements are
denominated in thousands of dollars — that is the finest resolution UC
publishes, so the gate tier is exact fidelity at the source's own
resolution (the CSU tier, not the CCC dollar tier or the K-12 cent
tier). Do not claim finer.

**The audit status of the gate, stated honestly.** The per-campus table
is headed **"Campus Facts in Brief (Unaudited)"**, and PwC's opinion
says so precisely: *"other information comprises pages 4 through 7, but
does not include the basic financial statements"* (FY2024-25; the
FY2023-24 report says pages 6 through 9), on which the auditor
*"do[es] not express an opinion"* — but the auditor states its
responsibility **is "to read the other information and consider whether
a material inconsistency exists between the other information and the
basic financial statements"** (and to describe any uncorrected material
misstatement of it in the report). So the honest gate
statement is: UC-published, auditor-read campus schedules that
reconcile **exactly, to the thousand, at zero residual,** to the
audited statement total (PwC, unmodified opinion, dated November 21,
2025 for FY2024-25). The systemwide total itself is fully audited.

**No better per-campus source exists — by UC's own statement.** No UC
campus has audited standalone statements: UCLA's controller site says
it outright — *"UC campuses do not have standalone audited financial
statements by location. The only audited financial statements are held
at the system level"* — and labels its own campus report *"unaudited
and… prepared by management."* UC's old systemwide per-campus product
("Campus Financial Schedules," Schedules A-D per campus) was
**discontinued after FY2019-20** and its index now returns 404
(verified live; the last edition confirmed via a January 2025 Wayback
snapshot). For current years the AFR's Campus Financial Facts table is
the **only** UC-systemwide per-campus financial publication — and it is
the one that reconciles to the audited total at zero residual.

## 1. Access — public, auto-fetchable, no bot-gate (like CCC, not CSU)

The AFR PDFs are on **ucop.edu** and answer a plain scripted request —
HTTP 200, `application/pdf`, with **no User-Agent even required** (a
bare curl gets 200/206; tested). No 403, no challenge, anywhere:

- FY2024-25 (132 pp., ≈3.45 MB): `ucop.edu/uc-controller/financial-reports/systemwide-reports/annual-financial-reports/24-25/annual-financial-report-2025.pdf`
- FY2023-24 (128 pp., ≈3.45 MB): `.../23-24/annual-financial-report-2024.pdf`
- Index (AFRs 2013-14 through 2024-25): `.../financial-reports/annual-financial-reports.html`
- The combined **Medical Centers AFR** (see §4) is on the same host, same access.

Two access caveats found by testing, not assumption: the legacy host
`finreports.universityofcalifornia.edu` resolves in DNS but is
**TCP-unreachable** ("no route to host" on both 80 and 443 — a dead or
firewalled host, *not* a bot-gate; do not cite finreports URLs). And
web.archive.org was in an outage during this investigation, so the
Wayback fallback is untested.

**No manual-cache exception is needed.** UC joins the state, cities,
counties, K-12, special districts, and CCC on the auto-reproducible
side of the ledger; CSU remains the lone exception.

## 2. The strip — defined by UC's own lines, and only by them

The V10b requirement was that the medical/lab/auxiliary separation be
UC's own segmentation, never our judgment. **It is.** UC's Campus
Financial Facts table publishes, per campus, the functional lines
"Medical centers" and "Auxiliary enterprises"; the Systemwide column
adds "Department of Energy laboratories." The audited statement itself
carries "Department of Energy laboratories" as an expense line
($1,194,419K FY2024-25) that ties to the campus table's figure
**exactly**. The strip is therefore pure arithmetic on UC-published
cells (FY2024-25, thousands):

| UC's own category | Amount | Share of total |
|---|---|---|
| Medical centers (5 campus lines + systemwide elimination) | $22,304,432K | 38.6% |
| Auxiliary enterprises (10 campus lines + elimination) | $1,819,469K | 3.1% |
| Department of Energy laboratories (systemwide line) | $1,194,419K | 2.1% |
| **Core (education & research remainder)** | **$32,449,007K** | **56.2%** |

(FY2023-24 medical centers were $18,843,616K = 34.4% — matching V10b's
"~34%". The jump to 38.6% is real, and the AFRs' own notes explain it:
in 2024 the University "completed the purchase of six hospitals,
physician practice groups, outpatient facilities for its Irvine, Los
Angeles and San Diego medical centers, in exchange for $1.5 billion,"
and in August 2024 UCSF Health "acquired two hospitals for the
preliminary cash consideration of $69.5 million" — acquisitions whose
full-year effect lands in FY2024-25.)

The five campuses **with** medical centers (their FY2024-25 "Medical
centers" line): Davis $3,614,812K, Irvine $3,461,964K, Los Angeles
$3,867,029K, San Diego $3,745,290K, San Francisco $8,207,318K, plus a
−$591,981K systemwide elimination. Berkeley, Merced, Riverside, Santa
Barbara, and Santa Cruz have none — the strip leaves them untouched.

## 3. National labs — one inside (and strippable), two already outside

From UC's own Note 1, quoted:

- **Lawrence Berkeley National Laboratory is INSIDE the statements**:
  *"Specific assets and liabilities and all revenues and expenses
  associated with LBNL, a major United States Department of Energy
  (DOE) national laboratory operated and managed by the University
  under contract directly with the DOE, are included in the
  accompanying financial statements."* Its expenses are the
  **"Department of Energy laboratories"** line — $1,194,419K FY2024-25
  (five-year series $1,042,258 / $990,713 / $1,104,266 / $1,146,576 /
  $1,194,419K) — so it strips on UC's own line, no judgment needed.
- **Los Alamos (Triad National Security, LLC) and Lawrence Livermore
  (Lawrence Livermore National Security, LLC) are NOT consolidated**:
  *"The University's investments in Triad and LLNS are accounted for
  using the equity method"* — only UC's equity in their earnings or
  losses appears (classified as operating). The weapons labs' budgets
  are already outside the total. One transparency note: **the AFR does
  not disclose the dollar amount** of the Triad/LLNS equity income
  anywhere — a build should say "not separately disclosed by UC"
  rather than imply it is zero.

## 4. The honest limit — the strip removes hospitals, not medical schools

This is the caveat that must sit on the face of the layer, not in a
footnote. UC's "Medical centers" line is the **hospital enterprises**
(the entities separately audited in the Medical Centers AFR). The
**schools of medicine and other health-sciences schools remain inside
the core** — their instruction, research, and academic support are not
separable in any UC-published per-campus segmentation, and consistent
with the V10b rule ("UC's own categories, never our judgment") this
finding does **not** invent one. Two facts quantify what that means:

- **UCSF** is a health-sciences-only campus with **no undergraduates**
  (fall 2024: 5,003 students on the AFR's campus-reported count — all
  graduate/professional, its undergraduate cell blank; 3,007 on the
  Info Center's student count, the difference being residents/interns
  — see §5). Even after stripping its $8.2B hospital line, UCSF's core
  is $3,739,393K — about **$747K per enrolled student** on the most
  generous denominator, and well over $1M on the stricter one,
  reflecting a research-and-clinical-training enterprise, not
  undergraduate education. UCSF must carry a structural dagger in any
  per-student view, or be excluded from that view entirely (shown
  records-only) — a build decision, but the finding's data says the
  dagger text writes itself.
- **UCLA**'s core after the strip is $8,951,890K against Berkeley's
  $3,826,449K at nearly identical enrollment — much of the difference
  is the David Geffen School of Medicine and allied health-sciences
  units inside "Instruction" ($3.97B vs Berkeley's $1.14B) and
  "Academic support" ($1.73B vs $155M). Per-student core therefore
  splits the campuses into health-sciences-heavy and not — a mission
  difference to be flagged (daggers), never ranked.

**Cross-validation of the med-center line (and why the two measures
must never be mixed):** UC separately publishes a combined **Medical
Centers Annual Financial Report** in which PwC issues **an opinion on
each of the five medical centers individually** (combining columns:
Davis $3,799,436K, Irvine $3,676,467K, Los Angeles $4,239,920K, San
Diego $3,823,190K, San Francisco $8,375,018K; the printed "Total
(memorandum only)" column: operating expenses **$23,914,031K**
FY2024-25). That corroborates the scale and
the per-campus mapping of the AFR's functional line ($22,304,432K) —
but the two are different measures (standalone-department statements
vs. post-elimination functional classification within the University).
A build strips using the AFR's own line, cites the audited med-center
statements as corroboration, and never sums or substitutes across the
two.

## 5. The denominator — per-campus FTE is achievable (UC beats CSU here)

**UC publishes per-campus student FTE in a stable-URL, scriptable UCOP
document** — something CSU never did. The UCOP operating-budget office
posts one small "actual FTE" PDF per year (pattern
`ucop.edu/operating-budget/_files/documents/{YYYY-YY}.pdf`, editions
2010-11 through 2024-25; the 2024-25 file is 2 pages, 125 KB, returns
200 to a bare no-UA curl, and pypdf extracts it cleanly — verified
directly). Page 1 is **General Campus FTE per campus** (undergraduate /
postbaccalaureate / graduate, including summer, *excluding
self-supporting programs and health sciences* — the exclusions are
printed on the page); page 2 is **Health Sciences FTE per campus** with
**"Resident" as its own labeled line** (e.g. 2024-25: UCSF 4,523 total
of which 9 undergrad-equivalent; UCLA 3,936 of which 1,325 residents).
So the proper higher-ed denominator is achievable: per-FTE, from UC's
own budget-office series, fiscal-year-aligned, with medical residents
separable on UC's own line.

**Headcount is also available, two ways, with a definitional trap
between them.** The Campus Facts table in the AFR itself prints
per-campus fall headcount (fall 2024 total: 305,762) — same PDF, same
fetch as the financial data. UC's Information Center is
Tableau-hosted (`visualizedata.ucop.edu`; UC's own download
instructions state the raw data are *"not available because the raw
data are not shared publicly"*), but its **crosstab CSV export is a
stable, no-auth URL that honors query parameters**
(`.../views/fallenrollmentataglance/Ataglance.csv?YEAR=…&CAMPUS=…` —
tested for 1999-2025, all ten campuses; rows arrive duplicated and
need dedup; Tableau-backed, so renames/upgrades are its fragility).
The trap: **the two headcounts disagree at health-science campuses, by
roughly the medical-resident/intern count** — UCSF 5,003 (AFR,
campus-reported) vs 3,007 (Info Center); UCLA 48,660 vs 47,335; Davis
41,239 vs 39,964 — while matching *exactly* at Berkeley, Merced, and
Santa Cruz. A per-student figure for UCSF moves by two-thirds depending
on which definition is chosen. A build must pick one definition, label
it on the face, and never mix the two.

**Recommended denominator**: per-FTE from the UCOP actual-FTE PDFs
(general campus + health sciences, residents shown on UC's own labeled
line and excluded or included *explicitly*), with the AFR fall
headcount as a cross-check — not the other way around.

## 6. Overlap — smallest of the three systems, and scattered

FY2024-25, from the audited statements: **State educational
appropriations $4,821,601K** (a *nonoperating* revenue under GASB) —
**8.3% of total operating expenses** ($57.77B) and **9.3% of total
operating revenues** ($51.86B); V10b's ~9% confirmed. The live
"these figures do not add" statement should also note that state money
reaches UC through **three different statement sections**: educational
appropriations (nonoperating, $4.82B), state grants and contracts
(operating revenue, $1,008,042K — includes special research
appropriations UC does not itemize), and state capital appropriations
(other changes in net position, $1,636K), plus $24,419K of state
hospital fee grants. The state budget page's enacted UC line is
Budgetary-Legal; UC's figures are GAAP/GASB accrual — never reconciled,
never summed. UC is the least state-funded of the three systems — CSU
≈ 40%+ of core funds and CCC ≈ 51% of total funding, per the shipped
CSU and CCC layers' own gated data; UC ≈ 8-9% of operating expenses,
verified here — which is itself worth saying plainly on the page.

## 7. Comparability traps — the daggers, all data-derived

1. **Medical-center campuses vs not** (5 vs 5) — flagged from UC's own
   per-campus "Medical centers" line; even after the strip, the
   health-sciences residual (§4) keeps these campuses structurally
   different.
2. **UCSF, the structural outlier** — graduate/professional only, no
   undergraduates (blank cell in UC's own table), core ≈ $747K per
   student. Dagger at minimum; records-only for the per-student view
   is defensible.
3. **Research intensity** — UC's own "Research" line spans $67M
   (Merced) to $1.37B (San Diego, San Francisco each); per-student
   figures partly measure research mission, not instruction cost.
4. **Scale** — Merced ($578M total, 9,110 students) is an order of
   magnitude smaller than UCLA ($13.4B); small-campus fixed-cost
   daggers as on other layers.
5. **A restatement wrinkle (gate hygiene, found empirically):** the
   FY2023-24 total was **restated** between reports — $54,703,428K as
   originally published vs $54,516,654K in the FY2024-25 report's
   comparative column, a $186,774K gap that traces to restated FY2024
   expense lines (chiefly depreciation/amortization, −$200,801K). The
   FY2024-25 report separately prints an $820,663K "cumulative effect
   of accounting changes" on FY2024 *beginning net position* (GASB 101
   plus an accounting-principle change) — a different quantity; do not
   conflate the two. **The gate must always run within a single report
   year** (campus columns vs that same report's statement);
   cross-report comparisons must use one basis and label it.

## Recommendation

**(a) SHIP stripped and gated.** Concretely, if built:

- **Gate**: ten campuses + UC's own printed Systemwide column ==
  audited total operating expenses, **exact to the thousand, zero
  residual, no write on failure** — demonstrated on FY2023-24 AND
  FY2024-25. Named accurately as the CSU tier (exact at the source's
  own resolution — thousands), with the "auditor-read other
  information" status stated.
- **Strip**: UC's own three lines — Medical centers, Auxiliary
  enterprises, Department of Energy laboratories — nothing else,
  nothing judged by us. Core = $32.4B (56.2%) FY2024-25. The
  hospitals-not-medical-schools limit stated on the face (§4), with
  UCSF and health-sciences daggers.
- **Labs**: LBNL stripped via UC's own line; Triad/LLNS noted as
  equity-method (outside the total; dollar amount not disclosed by UC).
- **Denominator**: per-FTE from the UCOP actual-FTE PDFs (general
  campus + health sciences; medical residents on UC's own labeled line,
  included or excluded explicitly), cross-checked against the AFR's
  fall headcount; the AFR-vs-Info-Center headcount definitional gap
  stated. UCSF flagged or records-only in the per-student view.
- **Fetch**: `ucop.edu` PDFs by plain scripted GET — auto-reproducible,
  no manual cache; the Medical Centers AFR fetched as corroboration.
  (Parsing note for the build: the campus tables extract as whole-row
  strings; sparse rows — Medical centers, DOE, Other — must be mapped
  by which campuses possess the item, and the mapping must then be
  **proven by a column-sum check**: every campus column's function
  lines must sum exactly to that column's printed total, or nothing is
  written. This is not hypothetical — an independent verification pass
  during this investigation mis-mapped the sparse "Other" row on its
  first attempt and the column-sum check caught it; under the correct
  mapping all eleven columns tie exactly. Campus *totals* rows are
  complete and unambiguous.)
- **Overlap**: live, ~8-9%, with the three-section scatter stated.

This closes the higher-education line: **CSU (thousand, manual-cache),
CCC (dollar, auto), UC (thousand, auto, stripped on UC's own
categories)** — and the one figure the V10b finding refused to publish
raw (a hospital ledger dressed as an education number) ships only in
its honest, UC-segmented form.

---

*Sources (all fetched and parsed this week, scripted, no credentials):
UC Annual Financial Report FY2024-25 and FY2023-24 (ucop.edu — audited
by PricewaterhouseCoopers LLP, unmodified opinions; Campus Facts in
Brief tables, Statements of Revenues, Expenses and Changes in Net
Position, Note 1 including the DOE-laboratories and
Triad/LLNS-equity-method passages, Report of Independent Auditors
"other information" scope); UC Medical Centers Annual Financial Report
FY2024-25 (ucop.edu — per-center PwC opinions, combining statements);
UCOP actual-FTE PDFs (ucop.edu/operating-budget, editions 2010-11
through 2024-25 — per-campus general-campus and health-sciences FTE,
verified no-UA 200 and pypdf-parsed); UC Information Center
(Tableau-hosted; UC's own instructions PDF states raw data are not
shared publicly; the crosstab CSV export endpoint verified scriptable
with ?YEAR/?CAMPUS parameters); UC Accountability Report data-table
XLSX files (stable URLs, verified); UCLA controller pages (the
no-standalone-audit disclaimer and campus Schedule B, for
corroboration); ebudget.ca.gov enacted UC line (basis contrast).
finreports.universityofcalifornia.edu verified dead at TCP level (not
a bot-gate); UC's Campus Financial Schedules verified discontinued
(live 404 + Wayback); web.archive.org in outage during testing, so the
Wayback fallback for the AFR itself is untested. Analysis scripts and
downloaded PDFs preserved in the session scratchpad.*
