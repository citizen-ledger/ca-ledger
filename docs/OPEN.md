# Open questions and recurring patterns

The honest record of what is deliberately unfinished, and why — and the
shapes a maintainer will meet again, named so the next instance is
recognised rather than re-diagnosed from scratch.

This file is normative about *state of the work*, not history; the dated
history lives in STATUS.md, and the reasoning behind each decision lives
in the numbered findings under `docs/`.

---

## Part 1 — What is deliberately not published, and why

These are not gaps to be filled by trying harder. Each is a place where
the source does not support a figure the site would otherwise show, and
the site says so rather than deriving one. "Not published" is a
first-class value here: it renders differently from a real zero and
differently from a rendering error (a number that is unknown is *absent*,
which yields NaN, not 0; a status that is unknown is a three-valued
string, because `false` is a real answer with no room left to mean
"unknown").

### 1a. CCC apportionment facts do not extend across all fifteen years

The community-college layer carries **fifteen** fiscal years of Current
Expense of Education (FY2009-10…FY2023-24), each gated to the dollar. Its
**apportionment-derived** facts — funded FTES, State General Fund,
community-supported status, and the per-FTES rate built on funded FTES —
reach only the years with a readable SCFF Exhibit C, and not uniformly
even there. The matrix, as shipped:

| FY | round | Current Expense | funded FTES | state GF | community-supported |
|---|---|---|---|---|---|
| 2009-10 … 2017-18 | — | ✓ | — | — | — |
| 2018-19 | P2 | ✓ | **not-published** | ✓ | **not-published** |
| 2019-20 | R1 | ✓ | ✓ | ✓ | **not-published** |
| 2020-21 | P1 | ✓ | ✓ | ✓ | ✓ |
| 2021-22 | — | ✓ | — | — | — |
| 2022-23 | R1 | ✓ | ✓ | ✓ | ✓ |
| 2023-24 | P2 | ✓ | ✓ | ✓ | **not-published** |

Each dash and each "not-published" has a stated, declared reason
(`APPORTIONMENT_FACTS` and `APPORTIONMENT_FACT_UNPUBLISHED` in
`pipeline/fetch_ccc_data.py`; findings V19, V20):

- **2009-10…2017-18 and 2021-22 — no readable Exhibit C.** No verified
  file exists for 2021-22 (the soft-404 discipline: cccco.edu returns 200
  for paths that do not exist, so a file counts only on `%PDF-` magic).
  The earlier years predate what the Ledger has fetched. Their
  apportionment facts are absent, not zero.
- **funded FTES, 2018-19 — the document prints no such figure.** It
  carries a Section Ia FTES *Allocation* table whose Totals row offers
  several candidates (Applied #1, Applied #2, Paid, FTES Reported, a
  three-year average) and never says which is funded. Choosing one would
  be an unforced judgement with no printed control to check it. `perFtes`
  is not published for that year in consequence.
- **community-supported, 2018-19 / 2019-20 / 2023-24 — the derivation
  cannot be reconciled.** Each of those documents prints a
  community-supported *count* (or, in 2018-19, none at all) that
  disagrees with the eight districts showing a property-tax excess, with
  Sierra Joint CCD the marginal case every time; 2023-24 points to a memo
  it does not contain. Publishing a derived roster that contradicts the
  Chancellor's Office's own count is refused. Where the count ties
  exactly (2020-21, 2022-23), the status ships.

**This is stable, not a to-do.** The only way to add a fact here is a new
source that reconciles, not a looser parse.

### 1b. UC FY2019-20 is held — an irreducible 351K reconciliation gap

The UC layer ships five years (FY2020-21…FY2024-25). **FY2019-20 is held**
(`docs/V18B`), encoded not-published and rendered as a distinct held point
on the trend, never as a zero and never silently dropped. The build
re-measures its residual on every run and fails loudly if it ever closes,
so a future restatement reaches a human rather than auto-shipping.

The gap is real and irreducible: the unaudited Campus Facts in Brief plus
UC's own added-back DOE line misses the audited total by **351 thousand**,
where every later year ties exactly. The dig (V18B, Finding 1) confirmed
it is not a parse artifact — the campus sum is internally self-consistent,
the audited total is self-consistent, there is only one exclusion
footnote, and the single figure that would close it (1,075,910) appears
nowhere in the document. It closes only with a source restatement, which
is UC's to make, not ours to manufacture.

### 1c. City and county reported-zero, and the one deliberate asymmetry

A function a government **reported as zero** is a real statement about its
filing; a function it **never reported** is absent. Conflating them was a
defect fixed at all six read sites: the emit step dropped any line rounding
to $0, and every read site then turned the gap back into a measured $0.
The keys are now kept — **20,335** restored to the city layer, **561** to
the county layer (`reported-zero-not-erased` / `-county` in
`pipeline/revisions.py`) — so a reported zero renders distinctly from an
absent one, and `address.html`'s `countyRecord`, which had no absence
branch at all, now says "absent filing" rather than showing zeros.

The one place city and county are **deliberately asymmetric** is San
Francisco: a consolidated city-and-county that files once. It lives in
`city-data.js` and is **asserted absent from `county-data.js`**, with its
polygon routed to the city record, so it is counted exactly once. That
asymmetry is intentional and test-asserted; do not "fix" it by adding SF
to the county layer.

---

## Part 2 — Recurring shapes worth recognising

Four defect classes have each appeared more than once. They are not bugs
to fix once; they are properties of consuming government data, and the
value here is recognising the third instance from the first two.

### 2a. Single-vintage crosswalks make re-codings recur

**Shape.** An entity arrives in an older year with no stable identifier
and the build refuses (`NCES ID MISSING`, or a slug collision). It looks
like missing data. It is usually a **re-coding**: an administrative key
(`(Ccode, Dcode)`, an authorizer `Dcode`) moved while the stable identity
(the NCES id, the CDS school code) did not.

**Why it keeps happening.** The crosswalk (`nces_ids`, the MIS roster) is
built from a *single current-vintage* export that carries only each
entity's current key. Any earlier key is unresolvable **by construction** —
not by accident, not fixable by re-downloading. Every future re-coding
presents exactly like Lowell Joint (#63) and the charter collisions (V17)
did.

**Prefer a derived key over an enumerated exemption.** When one entity
splits across keys, ask first whether the *key* is wrong. A declaration is
right when the source genuinely re-coded one thing once (Lowell Joint: one
entry, guarded by `assert_recodings()` so it cannot rot). A derivation fix
is right when the same thing happens to many entities for the same
structural reason (charters: re-keyed on `(county, school code)` in the
K-12 nine-year build, dissolving 33 collisions at once rather than
declaring 33 exemptions). Enumerating what a better key would dissolve
produces a maintenance surface that rots as the window moves.

*Reconciliation cannot see identity*, one level up from *conservation
cannot see classification* — every figure gate passed on all nine K-12
years while the identity was wrong.

### 2b. The same fact carries a different label each vintage — the third-label trap

**Shape.** A fact reads as *absent* for an older vintage, and the
temptation is to declare it not-published. Check for the value under a
different name first: declaring absence from a regex miss is a **false
absence**, the mirror of reading an absent figure as zero.

**Measured three times, same fact.** The CCC state general fund is
printed as `State General Fund Allocation` (FY2022-23, FY2023-24),
`State General Entitlement` (FY2019-20, FY2020-21), and `State General
Apportionment` (FY2018-19) — three labels for one fact across the window.
Each was first read as "this vintage publishes no state general fund at
all"; each was a renamed row (V19b, V20). The row labels are now declared
per vintage (`gfLabel`), matched exactly, never by a widened alternation
that would accept any label in any year.

### 2c. The extractor is a per-vintage property too

**Shape.** A PDF vintage parses cleanly under one library and silently
corrupts under another — and the corruption is not an exception, it is
wrong numbers or truncated identities that parse fine.

**The case (V20).** FY2018-19's Exhibit C: pypdf inserts a space after a
comma on 46 of 72 pages *and truncates three district names* (corrupted
identity, unmatchable without the fuzzy matching this repo refuses);
pdfplumber keeps every name but breaks the figures elsewhere. Neither
library is "better." So the extractor is declared per vintage
(`APPORTIONMENT_AVAILABLE[fy]["extractor"]`), never chosen by try-one-then-
fall-back, and a vintage that declares none is refused. Where an extractor
corrupts a figure with whitespace, the value is read from the **bounded
span** between the document's own printed label and its own printed
annotation, with the span asserted on every read to be short and to hold
exactly one well-formed comma-grouped integer — an assertion strong enough
to catch a two-column merge, which a bare digits-and-commas test would
accept.

### 2d. An unexercised declaration can hold a wrong value behind a gate

**Shape.** A declared table (`APPORTIONMENT_AVAILABLE`, `CE_VINTAGE`, a
per-vintage label) carries a placeholder that is never read, because a
gate upstream refuses the case before the placeholder is used. The wrong
value sits there indefinitely without failing anything.

**The case.** FY2018-19's `gfLabel` was left at `"State General
Entitlement"` — guessed in V19b without measuring that vintage. It was
never exercised, because the fact-declaration gate refused the year before
any label was read. That is the gate *working* (a year with no declared
facts is not read), but it means a declaration can be silently wrong for a
long time. When you finally exercise a placeholder, measure it against the
source rather than trusting it; and prefer declarations that a test
exercises even when the feature that uses them is not yet turned on.

---

## Part 3 — Test-quality debt

The suite is large (2,700+ assertions, real data, mutation-hardened where
it has been swept) but not uniformly hardened. Known debt, from the
vacuous-gate audit (STATUS 2026-07-20/21) and after:

- **The vacuous-assertion sweep is not complete.** The audit that found
  catch-all selectors and self-guarded assertions closed the load-bearing
  gates but left a tail of lower-severity findings (roughly a dozen at the
  time) not yet re-anchored and proven by mutation. The rule to apply to
  each: an assertion that can pass on an empty match is the dormant-
  assertion bug in a new place; re-anchor it to an element that exists
  only when its subject is actually rendered, and prove it fails when the
  subject is broken.
- **Two gates from the vacuous-gate sweep remain open** as recorded in
  STATUS: the state *program* gate and Schedule 9's Gate 2. The other two
  (the cities zero-control reconciliation and the UC strip tautology) were
  closed.
- **The sibling-divergence audit's proof phase is incomplete.** The county
  classifier position guard was ported and the sibling inventories cached,
  but the mutation-proof pass across all divergent siblings did not finish
  within one session and was not resumed.
- **New multi-year tests pin the publishing year explicitly.** Several CCC
  and UC assertions now read a specific fiscal year (e.g. FY2022-23 for the
  community-supported control, FY2024-25 for UC) rather than "the newest
  year", because the newest year no longer publishes every fact. That is
  correct, but it means a future window extension must revisit which year
  those controls are pinned to.

---

## Part 4 — Investigated, not built

- **Vendor / who-the-state-pays.** Investigated in `docs/V4_VENDOR_FINDING.md`
  and revisited since: California does not publish vendor-payment data that
  can be honestly reconciled to its budget — the state's own vendor files
  cover roughly a tenth of recorded spending, with no stable identifiers.
  A second look did not change the conclusion. The refusal, not a
  precise-looking figure with unknowable gaps, is the published result. It
  is not on a to-do list; it is a standing "no" pending a source that
  reconciles.
- **Deeper history for cities, counties, and CSU.** Refused, with reasons,
  in `docs/V15_HISTORICAL_FINDING.md`. Cities and counties cannot go before
  FY2016-17 without becoming a *different* product — police and fire are
  not separable in the Controller's data before the FY2017 taxonomy change
  (both subcategory values read "Public Safety"), so a deeper series could
  not carry the per-service figures the pages are built on. CSU cannot be
  extended at all: `calstate.edu` returns HTTP 403 to every scripted
  request, so the control total for any older year is uncomputable, not
  merely unreconciled — and a year that cannot be gated does not ship.
