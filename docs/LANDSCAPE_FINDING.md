# Landscape finding: does anything like Citizen Ledger already exist?

_Investigated 2026-07-13. Six research sweeps (official/state-run,
nonprofit/think-tank, academic/expert, journalistic/civic-tech,
commercial/national, and a special-districts deep dive). Every claim
below was verified by a live page fetch, rendered-browser inspection,
or direct API query on the investigation date — not from memory or
search snippets. Nothing was built; this document is the deliverable._

## The honest verdict, up front

**We are less novel than the pitch and more novel than the fear.**
Nearly every *piece* of the Ledger has a precedent, and on the
city/county comparison use-case a live overlapping project exists
(BenchmarkUSA, found in this sweep, running on our exact upstream).
Our data is almost entirely a re-presentation of the State
Controller's own portal. What has no precedent anywhere — official,
nonprofit, academic, journalistic, or commercial — is the
combination we treat as the product: the reconciliation gate, the
explicit evidentiary tiering, all five layers on one neutral surface,
and the findings themselves (the vendor-data coverage measurement and
the special-district results are unpublished by anyone). The
dominant pattern in this landscape is not competition but
**abandonment**: the four most ambitious precedents are all dead.

---

## 1. The inventory

Fields per entry: coverage → source → reconciles? → status →
neutrality → access.

### Official / state-run

- **SCO "By the Numbers"** (https://bythenumbers.sco.ca.gov;
  cities/counties/districts explorer apps). Our upstream, assessed
  as a product: nine local-government data areas, FY 2002-03→2023-24,
  Socrata/Tyler pivot explorers — one stacked bar per app, one
  breakdown dimension at a time, no side-by-side entity comparison,
  no per-capita in the explorer (per-capita exists only as separate
  featured datasets), no maps, three siloed apps with no cross-layer
  navigation, no filing-status surface in the UI. **Republishes
  as-submitted and disclaims it**, verbatim: "The financial
  information is posted as submitted by each local government… The
  State Controller's Office is not responsible for the accuracy of
  this information." Current (FY 2023-24 loaded). Neutral, free.
  *Data overlap with the Ledger: near-total. Product overlap: modest.*
- **Open FI$Cal** (https://open.fiscal.ca.gov). State expenditure
  transactions, monthly, FY 2015-16→present, "151 departments …
  representing 79% of state expenditures" per its own homepage;
  vendor names only in a narrower AP-module dataset with enumerated
  exclusions (https://open.fiscal.ca.gov/learning-center/spending-vs-vendor-reports.html).
  Its FAQ states its figures "will not match other published
  financial statements of the state" — the philosophical opposite of
  a reconciliation gate. Current, neutral, free.
- **ebudget.ca.gov** (Department of Finance). The state budget
  presentation layer, 2017-18→2026-27, drill-down tables and CSV
  export; never shows actuals against budgets. It is the control
  total, not a consumer of one. Current, free.
- **LAO historical data** (https://lao.ca.gov/policyareas/state-budget/historical-data).
  State-only Excel downloads back to 1950-51/1984-85, updated
  Aug 2025; LAO itself warns the history "may not provide sufficient
  information to evaluate trends" across accounting changes. Free.
- **California State Auditor local high-risk dashboard** — **dead.**
  Ranked ~470 cities on ACFR-derived fiscal-health scores from 2019;
  taken down October 2023, old URL 404s; the audit program continues
  as per-city reports (https://www.auditor.ca.gov/reports/2025-801/).
  Cities only; counties and special districts were "later stages"
  that never came.
- **Government Compensation in California** (https://publicpay.ca.gov).
  Salaries/benefits for ~2M positions at 5,000+ employers incl.
  special districts. Compensation, not spending. Current, free.
- **DebtWatch** (https://debtwatch.treasurer.ca.gov). All state and
  local debt issuance since 1984, updated daily. Notable middle-tier
  disclaimer: data "reviewed by CDIAC but … not independently
  audited." Current, free.
- **data.ca.gov / lab.data.ca.gov** — a CKAN catalog, not a
  dashboard; no curated spending product.
- **reportingtransparency.ca.gov** — Schwarzenegger-era document
  site, **shut down November 2011** when Gov. Brown rescinded the
  order and vetoed a contract-posting bill
  (https://truthout.org/articles/california-gov-brown-shuts-down-transparency-website/).
  US PIRG's "Following the Money" gave California repeated **"F"
  grades (2013-2016)** for lacking a one-stop spending portal
  (https://pirg.org/california/edfund/media-center/california-receives-an-f-in-annual-report-on-transparency-of-government-spending/).

### Nonprofit / advocacy / think tank

- **Transparent California** (https://transparentcalifornia.com).
  Closest in *shape* — one free site spanning state, cities,
  counties, K-12, higher ed, AND special districts, 2010→2024 —
  but **compensation only** (salaries/pensions via ~2,500 CPRA
  requests/yr). Republishes as received. Current (2026 platform
  rebuild announced). Run by Nevada Policy Research Institute;
  right-of-center watchdog framing around a dry database. Free.
- **OpenTheBooks** (https://www.openthebooks.com/california/). The
  only organization that attempted a California state *checkbook*:
  after Controller Yee rejected its request and it **lost in court
  (Jan 2022)**, it assembled FY2021 line-item payments itself from
  **442 separate CPRA requests** — 201,684 vendors, $87.2B
  (https://openthebooks.substack.com/p/historic-announcement-californias)
  against a ~$300B budget, with no payment descriptions and no
  reconciliation to any control total; its CA checkbook page now
  carries year filters 2017-2025. Active (founder died Aug 2024; new
  CEO). Explicit waste-watchdog advocacy voice. Free.
- **California Policy Center — Local Fiscal Health Dashboard**
  (https://californiapolicycenter.org/fiscal-health-dashboard/,
  launched Oct 2024). The only current, interactive, multi-entity CA
  local fiscal tool from this sector: A-F grades for 470+ cities,
  58 counties, ~940 school districts, computed from audited ACFRs
  via Hoover Institution methodology. Publishes ACFR delinquency
  counts. **No special districts; grades, not ledgers.** Current
  (July 2026 data notes). Free-market advocacy shop; data-serious.
- **Truth in Accounting / Data-Z** (https://www.data-z.org). 50
  states + 75 largest cities (~15 CA), ACFR-restated into "Taxpayer
  Burden" metrics; 2026 cities report scaled back to 5 cities.
  Restates rather than reconciles. Current. Fiscal-hawk flavor. Free.
- **Reason Foundation — CalPERS Monitor** (https://calpers.reason.org).
  Pensions only. Current (Apr 2026). Libertarian advocacy. Free.
- **Hoover Institution / Stanford SLGI Municipal Finance Dashboard**
  (https://municipalfinance.stanford.edu). Nationwide ACFR-derived
  fundamentals incl. CA entities; the methodological parent of CPC's
  dashboard. Academic, center-right home. Free, active.
- **Lincoln Institute — Fiscally Standardized Cities**
  (https://www.lincolninst.edu/data/fiscally-standardized-cities/).
  Closest in *comparability rigor*: standardizes city finances by
  folding in overlapping county/school/special-district shares —
  but only **16 CA cities** of 212, Census-sourced, FY1977-2023,
  2-3 year lag. Neutral, free, maintained.
- **California Budget & Policy Center** (https://calbudgetcenter.org)
  — state budget *analysis*, progressive/equity framing, no data
  repository. **CalTax** (https://www.caltax.org) — advocacy, no
  data tools. **Next 10 Budget Challenge**
  (https://www.budgetchallenge.org) — state budget *simulator*,
  educational, 2026 edition current. **Pew Fiscal 50** — states
  only, indicator curation.
- **California Common Sense / US Common Sense — dead.** The
  mission-twin: Stanford-born (2010), nonpartisan, built "the
  first-ever interactive data transparency portal" for California
  and multi-government analyses. uscommonsense.org no longer
  resolves; cacs.org serves a blank page; last Form 990 (2020)
  shows ~$3,600 revenue vs a ~$750K peak in 2015
  (https://projects.propublica.org/nonprofits/organizations/273128463).

### Academic / expert

- **CaliforniaCityFinance.com — Michael Coleman's "California Local
  Government Finance Almanac"** (https://www.californiacityfinance.com).
  The closest living *expert* precedent: 25+ years of city (and
  county) revenue/expenditure analysis from SCO FTR data, with
  per-capita normalization, as **static Excel/PDF downloads** — no
  portal, no API, no districts, no state layer, no reconciliation
  discipline. The analysis layer is current (June 2026 election
  results; FY 2026-27 budget analyses); the comparative spreadsheet
  layer is largely frozen at FY 2008-09/FY 2018-19 vintages. A
  one-person shop (League of California Cities' longtime fiscal
  advisor), structurally city-perspective, no succession plan. Free.
- **Stanford Pension Tracker — dead.** Shut down Feb 28, 2022; both
  domains fail DNS
  (https://west.stanford.edu/news/bill-lane-center-proud-new-home-pension-tracker).
- **UC Berkeley IGS LoCAL digitization**
  (https://igs.berkeley.edu/library/california-local-government-documents)
  — 1M+ pages of local budgets/financial reports digitized as PDF
  scans; an archive, not data. Complementary, not competitive.
  No other Berkeley/UCLA/USC/Claremont unit assembles multi-entity
  CA fiscal figures (verified program-by-program).
- **Special-districts scholarship** (Goodman/NIU, UIC GFRC "shadow
  governments"): national Census-of-Governments framing; **no
  California special-district finance dataset or tool has ever been
  released by an academic** (https://www.cgoodman.com/data).
- **FDTA/XBRL modernization**: the joint data-standards rule was
  finalized June 2026 (effective Oct 1, 2026), but municipal-issuer
  substance waits on a forthcoming SEC/MSRB Phase-2 rulemaking
  (~2027-28), covers securities disclosures rather than SCO filings,
  and California has no XBRL mandate
  (https://www.federalregister.gov/documents/2026/06/25/2026-12787/financial-data-transparency-act-joint-data-standards).
  Nothing here obsoletes the Ledger on any near horizon.

### Journalistic / civic tech

Every spending or budget tool in this sector is **single-jurisdiction**;
most are dead.

- **Checkbook L.A.** (https://lacontroller.io;
  https://controllerdata.lacity.org) — the best-maintained civic
  spending tool in California: LA city vendor payments refreshed
  monthly (dataset updated 2026-07-10, verified via Socrata API).
  One city; continuity is hostage to each controller election — the
  previous controller's propertypanel.la is already DNS-dead.
- **SF Open Book / DataSF** (https://openbook.sfgov.org) — SF only,
  official, current.
- **Open Budget Oakland** (https://openbudgetoakland.org) — frozen:
  last budget loaded 2021-23, last GitHub commit Mar 2022. **Open
  Budget Sacramento** (https://openbudgetsac.org) — data frozen at
  FY2018. Code for America ended the brigade program in Jan 2023;
  the genre died with it.
- **CalMatters** — no standing fiscal data tool (verified against
  their current Data & Trackers page); one-off budget interactives
  ended 2021; Digital Democracy covers legislation, not money.
- **Newspaper databases** — compensation only; only the Sacramento
  Bee's state-worker pay database survives.
- **County portals** (LA https://auditor.lacounty.gov/auditor-open-data/,
  Orange https://www.ocgov.com/about-county/openoc, San Diego,
  Santa Clara) — each covers exactly one county; none is
  vendor-level except none; **no multi-county spending dashboard
  exists anywhere**.

### Commercial / national

- **BenchmarkUSA** (https://benchmarkusa.org/ca) — **the closest
  live overlap, found in this sweep and verified firsthand.** A
  one-person, free, explicitly nonpartisan project covering **all
  482 CA cities and 58 counties from CA State Controller data,
  FY2003-FY2024 (current)**, with per-capita metrics, rankings,
  entity profiles, and AI/MCP data access; started with New York
  (30 years of Comptroller data), roadmap to more states. What it
  does that we do: per-entity SCO-derived city/county figures with
  per-capita comparison, free and current. What it does that we
  refuse: **it ranks** (its core product is rankings and "Debt
  Service %" leaderboards). What we do that it doesn't: state
  enacted-vs-actuals, special districts, evidentiary tiering, a
  published reconciliation gate (its methodology page describes
  sources and exclusions, not control-total verification), same-filing
  population denominators (it divides by Census ACS estimates),
  integrity digests.
- **ClearGov** (https://cleargov.com/california/local-governments) —
  the cautionary twin: free auto-generated transparency profiles for
  every CA city with SCO-style category breakdowns and peer
  comparisons **exist but are frozen at FY2018** (verified firsthand:
  the Trinidad profile's own links route to `/2018/revenue`).
  Current data only for paying customers. Universal coverage was
  built, then left to fossilize as lead-gen.
- **OpenGov** (https://opengov.com) — hundreds of CA agency portals
  (budget-to-actuals, sometimes checkbook), each a per-customer
  silo; no public cross-entity view. **Tyler/Socrata** — the
  platform under SCO's own portal. **CitySpend**
  (https://www.cityspend.org) — 871 US cities ≥50k (~120+ CA),
  Census-based, A-F scores, anonymous operator. **Munetrix/Polco**
  — gated. **MuniNet** — sunset.
- **Bond data**: **EMMA** (https://emma.msrb.org) — free per-issuer
  audited financials, PDF-only, debt-issuers only. **Merritt/
  Investortools, DPC DATA** — per-entity ACFR data at scale exists
  commercially and is **paywalled** ($3,000/dataset/yr academic rate).
- **Census Bureau** (Census of Governments / ASSLGF) — the only
  national collection identifying individual CA special districts;
  quinquennial for full coverage, sampled between, ~2-year lag,
  reclassified to Census categories. The substrate for USAFacts
  (aggregates only), Urban Institute SLF-DQS (aggregates only,
  through 2022), GFOA dashboards.
- **GovSpend** — paywalled B2B procurement intelligence.
  **Ballotpedia** — prose articles, budget pages last updated 2017.

### Special districts specifically (the layer we most expected company)

- **SCO districts explorer** (https://districts.bythenumbers.sco.ca.gov)
  — the only public special-district finance tool, period. One pivot
  chart; no district profile pages; no filing-status surface; no
  reconciliation; as-submitted disclaimer. Its own homepage
  breakdown corroborates our double-counting finding: FY 2023-24
  revenues are 43.5% JPA ($46.1B) and 24.0% dependent districts
  ($25.5B) — SCO's own categories say most "special district" money
  is legal forms and money also in other governments' books.
- **Little Hoover Commission 2017**
  (https://lhc.ca.gov/report/special-districts-improving-oversight-transparency)
  — the only published prose critique adjacent to ours: aggregation
  is unreliable because SCO commingles JPAs/nonprofits/dependent
  districts (Rec 10), reserve definitions are inconsistent (Rec 8),
  and even the Commission had to get totals from SCO staff by hand.
  An interpretability critique, not a reconciliation critique. No
  filing-rate statistic (verified against the full report text).
- **Edward Ring / California Globe (Sept 2020)**
  (https://californiaglobe.com/articles/why-cant-government-financial-reporting-match-private-sector-standards/)
  — notes the Controller **discontinued the consolidated annual
  reports** (which had statewide totals and a non-filer appendix)
  when moving to By the Numbers. Framed as "no analysis," not "no
  control totals." (The old consolidated PDFs survive, e.g.
  https://www.californiacityfinance.com/SCOspdistr200607.pdf.)
- **CSDA map** (https://www.csda.net/about-special-districts/map) —
  boundaries/contacts for independent districts only, explicitly
  unverified, no finance. **SDLF transparency certificate** — a
  checklist credential, no data. **LAFCO/CALAFCO** — per-county PDF
  service reviews, never aggregated; the state's 2015 special-district
  GIS layer is unreachable. **Grand juries** — 13,076 reports
  archived at https://civilgrandjury.org, never aggregated into data.
- **Journalism** — one-off investigations (OC Register 2013 series,
  LA Times/Central Basin, Desert Sun/ProPublica on IID, Mt. Diablo
  healthcare district); none produced a reusable tool.
- **State Auditor** — episodic single-district audits; the statewide
  dashboard never reached districts before it was killed.

---

## 2. The graveyard (a pattern, not a footnote)

Verified dead or frozen during this investigation: California Common
Sense (the mission-twin; DNS-dead), Stanford Pension Tracker
(DNS-dead), the State Auditor's high-risk dashboard (removed Oct
2023 — even the *official* comparability tool was abandoned), Open
Budget Oakland and Sacramento (frozen 2021/2018), ClearGov's
universal CA profiles (frozen FY2018), Ballotpedia's budget pages
(2017), reportingtransparency.ca.gov (2011), Mercury News salary
database (~2016), propertypanel.la (DNS-dead), CalMatters' budget
interactives (2021, embed platform TLS-expired), MuniNet (archived),
the state's special-district GIS layer (unreachable). The pattern:
multi-entity California fiscal transparency has been attempted
repeatedly and has died every time the founder's attention, a
funder, an election, or a staffing decision moved on. This is the
strongest argument for the Ledger's architecture (static files,
committed pipelines, tests, no server) — and an honest warning that
novelty is not the scarce resource here; **survival is**.

---

## 3. The four questions, answered directly

### Q1. Does anything cover our span — state enacted AND actuals AND all cities AND all counties AND special districts, in one place?

**No.** Verified against every sector. The only things spanning all
layers are: (a) SCO's own By the Numbers — locals only, no state
layer, three siloed apps, no comparison; (b) Transparent California —
all layers including districts, but compensation only; (c) the
Census of Governments — quinquennial, lagged, reclassified,
aggregate-first. The state layer's own two official surfaces
(ebudget, Open FI$Cal) are disconnected sites run by two agencies,
and no one anywhere pairs enacted budgets with Schedule 9 actuals.
Closest partial spans: BenchmarkUSA (cities+counties, live, same
upstream) and CPC's dashboard (cities+counties+schools, grades not
ledgers). **Nobody has the special-districts layer at all** — the
SCO's own explorer is the only other public tool that touches
district finance.

### Q2. Does anything apply a reconciliation gate?

**No — and the two closest sources explicitly disclaim the
opposite.** SCO By the Numbers: "posted as submitted… not
responsible for the accuracy." Open FI$Cal: its data "will not match
other published financial statements of the state." DebtWatch
occupies a middle tier ("reviewed… but not independently audited").
The tools that *start* from audited figures (Truth in Accounting,
Hoover/CPC dashboards) restate or grade rather than verify
reproduction of published totals, and say so nowhere as a gate.
Lincoln's FiSC standardizes for comparability but inherits Census
imputation. We found no project, in any sector, that states —
let alone enforces in CI — "figures that do not reproduce the
source's published control totals are not published." The gate is
genuinely ours.

### Q3. Has anyone published our findings?

**The vendor finding — no, with adjacent prior art to cite.** No
one has published the measurement that vendor-named FI$Cal
transactions cover ~12% of same-month recorded spending with no
usable identifiers. Adjacent published claims, all measuring
something else: the state's own "79% of state expenditures" claim
for Open FI$Cal *overall* (https://open.fiscal.ca.gov/about.html) plus
its qualitative admission that the vendor dataset "does not include
every state expenditure transaction"; the Independent Institute/
OpenTheBooks 2020 projection that Open FI$Cal would cover ~65% with
ten units never included
(https://www.independent.org/article/2020/01/21/californias-hidden-checkbook/);
and OTB's Forbes-era headline that California "hides" ~$300B/yr. One
material nuance for our own records: **OpenTheBooks did assemble a
California vendor checkbook** (FY2021, 442 CPRA requests, $87.2B,
no descriptions, no reconciliation). Our V4 statement — that no
source *the state offers* can answer what a vendor was paid — stands,
but V4 should cite OTB's compilation as the workaround that proves
the gap; a reader who finds OTB before finding that caveat would
think V4 overclaimed.

**The special-district findings — no, and this is the clearest
novelty in the project.** Nobody — not SCO, LHC, the Auditor, CSDA,
academics, or press — has published (a) the observation that no
independent control-total dataset exists for districts so
reconciliation is structurally impossible, (b) any quantified
non-timely-filing rate (SCO publishes the raw per-year lists; we
verified via its API that FY 2023-24 is 785 late + 51 failed = 836,
and prior years ran 942-1,105 — ~17-23% for five years running —
and no one has ever stated a rate in prose), or (c) a directory
joining every district to per-year filing status. Cite as adjacent
prior art: LHC 2017 (commingling critique) and Ring 2020
(discontinued consolidated reports). One correction-proofing nuance
for our copy: the SCO explorer's homepage *displays* a statewide
as-filed total ($106.08B FY 2023-24 revenues), so our claim must
stay precisely what it already is — no *independent* control total
to reconcile against — never "no statewide number exists."

### Q4. Where are we genuinely different — and where are we duplicating?

**Duplicating (be honest about it):**
- *Per-entity city/county figures with per-capita comparison from
  SCO data*: BenchmarkUSA does this now, free, current, nonpartisan;
  ClearGov did it universally and let it rot; Coleman has done the
  expert version for 25 years; FiSC does the rigorous version for 16
  cities. Our city/county layers are better-disciplined
  (reconciliation, same-filing denominators, no rankings,
  comparability footnotes, enterprise separation) — but the
  *use-case* is occupied, and we should not present it as virgin
  ground.
- *State budget presentation*: ebudget.ca.gov is the official
  product; our Allocation/Trend views re-present its data with
  better interaction, which is genuine but incremental.
- *Data collection itself*: we collect nothing new. Every number we
  publish exists on a state Socrata portal or in a DOF PDF. Our
  pipeline adds discipline, not data.

**Genuinely different (verified unoccupied):**
1. **The reconciliation gate** — no precedent in any sector (Q2).
2. **The full span on one surface** — state enacted + actuals +
   cities + counties + districts (Q1).
3. **Explicit evidentiary tiering** — no other multi-layer site
   distinguishes reconciled from as-filed tiers; the SCO hides the
   distinction in a footer disclaimer, and everyone else ignores it.
4. **Neutrality by construction** — every current multi-entity
   comparator editorializes structurally: CPC/CitySpend/TIA grade,
   BenchmarkUSA ranks, OTB campaigns. A record that refuses to rank
   is an unoccupied position, not a shared default.
5. **The findings as product** — the vendor-coverage measurement and
   all three special-district results are first publications (Q3).
6. **Verifiability plumbing** — integrity digests, committed
   pipelines, CI that enforces the copy rules; nobody else ships
   the discipline as part of the record.

**Collaborate rather than compete:**
- **BenchmarkUSA** is the one live project close enough that a
  conversation should precede any public positioning. Philosophies
  differ at the core (rankings vs. a record that refuses to rank),
  so a merger is unlikely to fit — but data-method comparison,
  mutual citation, or shared upstream tooling would benefit both,
  and we should expect to be asked "how is this different from
  BenchmarkUSA?" and answer with Q4's list rather than surprise.
- **Michael Coleman** is the domain authority on CA municipal
  finance; his almanac is complementary (interpretation) to ours
  (record). Worth seeking his review of our comparability handling
  before wide release.
- **SCO itself** is upstream and under-resourced (a late-1990s
  platform per LHC). Our special-district findings are, in effect,
  free QA on their portal; offering them to SCO (and to the Little
  Hoover Commission, whose 2017 recommendations they extend) is the
  collaborative move with the most leverage.
- **Not** natural partners: the advocacy dashboards (CPC, OTB,
  TIA) — data-serious but editorially opposite; citing them is fine,
  joining them would spend our neutrality.

---

## 4. What would change this finding

Watch for: (1) FDTA Phase 2 SEC/MSRB rulemaking (~2027-28) — if
machine-readable ACFRs arrive, the audited-actuals layer opens for
everyone; (2) BenchmarkUSA's roadmap (more states; any move into
districts or reconciliation); (3) any SCO modernization of By the
Numbers (LHC Rec 8-10 implementation would absorb parts of our
districts finding); (4) revival attempts of the Auditor's dashboard.
Re-run this investigation before any public launch; it was current
on 2026-07-13.

## Method

Six parallel sweeps (official, nonprofit/think-tank,
academic/expert, journalistic/civic-tech, commercial/national,
special-districts deep dive), each verifying candidates by live
fetch, rendered-browser inspection, GitHub commit API, ProPublica
Form 990s, or Socrata SODA queries rather than search snippets;
key load-bearing claims (BenchmarkUSA coverage and methodology,
ClearGov's FY2018 freeze) re-verified firsthand in a second pass.
Dead sites were confirmed dead by DNS/HTTP, not assumed. Where a
claim rests on a single fetch it carries its URL above so it can be
re-checked directly.
