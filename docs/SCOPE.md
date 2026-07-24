# Scope decisions — standing

_This document records scope decisions that are permanent, with their
reasoning, so no future session re-proposes them. It is normative, not
historical; the dated history lives in STATUS.md._

## The architectural rule

**Citizen Ledger has no server, no API keys, no per-use costs, and no
runtime third-party services. Any proposed feature that requires one
is out of scope by default.**

The site is static files: open them and they work, today and in ten
years, at zero runtime cost and zero maintenance. That is not a
technical preference — it is the project's main defense against the
failure mode documented in docs/LANDSCAPE_FINDING.md: every serious
California fiscal-transparency precedent (California Common Sense,
Stanford's Pension Tracker, the State Auditor's own dashboard,
ClearGov's universal profiles) died when its builder's attention,
funding, or staffing moved on. **Survivability is the scarce resource
in this landscape**, and every key, bill, and server is a way to die.

Precision about the two existing runtime enhancements, so the rule is
applied correctly rather than argued around:

- the map view loads vendored MapLibre and keyless OpenFreeMap tiles;
- the address view sends the typed address to the U.S. Census
  Bureau's public geocoder.

**These two are the whole list, and the test suite now enforces it**
(`test_runtime_origins`): no page may load a subresource from any other
host. That assertion exists because the list had quietly grown to three
— every page loaded IBM Plex Mono from `fonts.googleapis.com` and
`fonts.gstatic.com`, undocumented here, which meant this document had
stopped describing the site. The font is now vendored under
`vendor/fonts/` (SIL OFL 1.1, licence included), so the page renders
with no third-party request at all, and a reader's IP and user-agent
are no longer disclosed to Google on every page view. A normative rule
that is not asserted decays into a preference; this one is asserted.

Both are **keyless, unmetered, free, and non-load-bearing**: when
they fail, the record still works (test-asserted degradation). That
is the boundary. An enhancement may use a runtime service only if it
requires no key, no account, no billing relationship, and its failure
breaks nothing. Anything requiring an API key, a server, or per-use
cost does not qualify — by default, without a new finding.

## Reproducibility — where it fully holds, and the one exception

Every layer regenerates from its official source by re-running its
pipeline against public data — **except CSU.** State, cities, counties,
special districts, K-12, the community-college districts, and UC all
fetch their sources automatically (SCO, DOF, CDE, the Chancellor's
Office CCFS-311 portal, and ucop.edu), so anyone can reproduce every
figure from scratch. That is a core honesty claim of the site.

**The CSU (higher-education) layer is the one exception, and it is
stated loudly wherever CSU appears** — the CSU page's method box reads
`NOT AUTO-REPRODUCIBLE`, and the about-page source table and the
pipeline docstring say the same. CSU's only source of an audited control total is
the systemwide financial statements PDF on `calstate.edu`, which is
**bot-gated**: a browser "Human Check" returns HTTP 403 to any
scripted download (curl, the pipeline's own fetcher, and archive.org
all fail; verified). The figures were extracted from the real audited
PDFs through a browser and are checked in at
`pipeline/cache/csu/csu-fy2324.tsv`; refreshing the layer for a new
fiscal year requires a **manual browser download** of the CSU audited
statements and Fact Book into `pipeline/cache/csu/`, then re-running
the extractor. This is the same class of exception as the one
bot-gated file the K-12 pipeline already documents (`pubschls.txt`),
scaled up to a gate source.

Why CSU ships anyway (per docs/V10B_HIGHERED_FINDING.md): the gate is
real and proven — the 23 campuses plus a visible systemwide &
eliminations line reconcile **exactly, to the thousand**, to CSU's
audited University total, and the audited combining identity holds
exactly. "Exact to the thousand" is the finest resolution CSU
publishes (its statements are denominated in thousands), so it is
exact fidelity at the source's own resolution — a different,
accurately-named tier from K-12's to-the-cent, not a looser version.
The **community-college districts** are now built too (per
docs/V11_CCC_FINDING.md), and they are a *stronger* case than CSU on
every axis: the source is **public and auto-fetchable** (no bot-gate,
no manual cache — the CCFS-311 reporting portal answers a plain POST),
and the gate is finer and proven on real data. The 73 districts'
Current Expense of Education (ECS 84362 — the community-college analog
of K-12's) sum **exactly, to the dollar**, to the Chancellor's Office's
own printed statewide total, and each district's figure is
independently validated off the portal by the mandatory CPA audit (Ed
Code 84040). "Exact to the dollar" is a third, accurately-named
resolution tier — finer than CSU's thousand, coarser than K-12's cent —
at the resolution the CCFS-311 portal publishes. This layer now carries
**fifteen fiscal years** (FY2009-10 through FY2023-24), the portal's own
coverage, each year gated to the dollar; the SCFF apportionment-derived
figures (funded FTES, state general fund, community-supported status,
per-FTES) reach only the five years with a readable Exhibit C (FY2018-19 through FY2023-24, FY2021-22 excepted), and not
every fact in each — the rest are declared not-published, never derived
(the per-vintage extractor, label and fact declarations are recorded in
docs/V19–V20). Per-FTES, where it ships, uses the apportionment funded
FTES, not the Data Mart derived count.

**UC is now built too (per docs/V12_UC_FINDING.md), in its honest,
stripped form only.** The V10b concern — that a raw UC figure is a
hospital ledger (medical centers are ~34-39% of operating expense) —
was resolved not by our judgment but by UC's own segment reporting:
UC's Annual Financial Report publishes "Medical centers", "Auxiliary
enterprises", and "Department of Energy laboratories" as its own
per-campus functional lines, so the strip is pure arithmetic on
UC-published cells, with the stripped components shown separately,
never deleted. The gate: ten campuses plus UC's own PRINTED Systemwide
column equal the audited total operating expenses **exactly, to the
thousand** (the CSU tier — the finest resolution UC publishes), proven
for **each of five fiscal years, FY2020-21 through FY2024-25** (per
docs/V18B_UC_SIX_YEAR_BUILD.md), with every campus column proven by a
**column-sum check** (the sparse rows' column assignment established
uniquely by exhaustion — the parsing trap the V12 finding documented —
and still unique at ten times the source's rounding tolerance).
**FY2019-20 is held**, not shipped: its unaudited campus table misses
the audited total by ~351K where every later year ties, so it is
declared held and re-measured every build rather than shipped at a
lower tier. UC publishes the DOE laboratory two ways across the window
(the FY2020-21 campus table excludes it, added back from the audited
statement; FY2021-22 on carry it inside the Systemwide column); the
core strip removes the same quantity either way, and that assembly
break is stated where the five-year core line crosses it.
The per-campus table is UC's auditor-read "other information," marked
"(Unaudited)"; that status is stated on the page per vintage (the
FY2020-21 report predates the fuller auditor language, so it is not
carried back) — the audited figure is the systemwide total the campuses
reconcile to. The strip's limit
is stated on the face: hospitals are stripped, **medical schools are
not** (health-sciences instruction/research stays in core; UCSF
carries the structural dagger). Sources are public ucop.edu URLs —
auto-fetchable, no manual cache. All three higher-education systems
now meet the bar: CSU (thousand, manual-cache), CCC (dollar, auto),
UC (thousand, auto, stripped on UC's own categories).

## Windows and depths — how far each layer reaches, and the refusals

Each layer covers exactly the years its source supports at a resolution
the gate can prove. The stopping points are decisions with reasons, not
artifacts of what was loaded, so they are recorded here to keep a future
session from re-proposing an extension that was already refused.

- **State (budget + actuals) — 9 years**, FY2017-18…FY2025-26: the span
  DOF's structured budget API serves; earlier years return empty, not an
  error (docs/V15).
- **Cities / counties / special districts — 8 years**, FY2016-17…FY2023-24.
- **K-12 — 9 years**, FY2016-17…FY2024-25.
- **Community colleges — 15 years**, FY2009-10…FY2023-24 (apportionment
  facts on four of them; see above).
- **CSU — 1 year**, FY2023-24. **UC — 5 years**, FY2020-21…FY2024-25, with
  FY2019-20 held.

Three historical extensions are **refused, permanently, with their
reasons** (docs/V15_HISTORICAL_FINDING.md; the vendor case is
docs/V4_VENDOR_FINDING.md):

1. **Cities and counties cannot go before FY2016-17.** The State
   Controller's expenditure taxonomy changed at FY2017; before it, police
   and fire are not separable (both read "Public Safety"). A deeper series
   could not carry the per-service figures these pages are built on, so it
   would be a *different* product, not a deeper one — not a data gap to
   fill.
2. **CSU cannot be extended at all.** `calstate.edu` returns HTTP 403
   (Imperva "Human Check") to every scripted request, so the control total
   for any older year is **uncomputable, not merely unreconciled**. A year
   that cannot be gated does not ship. (This is also why CSU is the one
   manual-cache layer above.)
3. **Vendor / who-the-state-pays data is not published at all.** California
   publishes no vendor-payment data reconcilable to its budget — its own
   files cover ~10% of recorded spending with no stable identifiers.
   Investigated and re-examined; the refusal is the published result.

The rule these share: a figure ships only when it reconciles to a control
the source itself published. Absent that control, the honest output is a
stated absence, never a precise-looking number with unknowable gaps. The
current unfinished work and the recurring shapes behind these decisions
are kept in docs/OPEN.md.

## "Ask the Ledger" — permanently out of scope

A natural-language query interface ("ask a question about California
spending, get an answer") is **permanently out of scope**. Decided
2026-07-14 by the project owner.

Reasoning, recorded so it does not get re-litigated:

1. Answering a free-form question requires an LLM API call per
   question. An API call requires an API key. A key cannot live in a
   static page, so it requires a server — and with it billing,
   secrets, rate limits, abuse handling, and a monthly reason to
   exist. That breaks the static, zero-runtime-cost, zero-maintenance
   architecture, which is the survivability defense above.
2. The Ledger is already queryable: search across every layer,
   filters, side-by-side comparison, per-entity records, CSV export,
   and permalinks that reproduce any view exactly. A conversational
   layer would add convenience, not capability.
3. Convenience priced in survivability is a bad trade here. The
   landscape finding's graveyard is full of more convenient tools.

There is also a neutrality cost worth noting: a model paraphrasing
the record would reintroduce exactly the editorial voice the Ledger
bans — adjectives, emphasis, implied comparison — between the reader
and the figures. The record speaks in numbers with stated bases;
that is the product.

No reference to this feature existed in the repository when this
decision was recorded (verified by search of all pages, docs, and
pipeline files). This document exists so none is ever added.
