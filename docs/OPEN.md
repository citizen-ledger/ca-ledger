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

### 1b-ii. CCC FY2019-20 revenue is held — the source disagrees with itself

The community-college layer publishes General Fund revenue (CCFS-311
Table IV.1) for **fourteen** of its fifteen years. **FY2019-20 publishes
none.**

The reason is not a parse failure, and that is what makes it a held year
rather than a bug. Every one of that year's 72 district rows foots
(Federal + State + Local = Total), and the printed statewide row foots
too. But the district rows sum to **$6,219,157,723** of State revenue
while the statewide row printed beneath them says **$6,199,157,723** —
exactly **$20,000,000** less, and the same $20,000,000 in the Total
column. Both numbers are the Chancellor's Office's own.

The Ledger does not get to choose which of a source's two figures is
right, and will not publish a district table that does not add up to the
total printed beside it. So the year shows no revenue, with that
measured discrepancy as the stated reason — the same disposition as UC
FY2019-20, and for the same reason: a gap that is small relative to the
total but *irreducible* is still a gap.

Note that FY2019-20's **Current Expense of Education is unaffected** and
gates like every other year. It is only the revenue that is held.

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

### 2e. A query that reconciles today can be relying on undefined behaviour

**Shape.** A paged query returns the right answer, every gate passes, and
the figures are correct — because the server happened to order its rows
consistently, not because anything asked it to. Nothing in the code, the
tests, or the source documents the dependency. The day the result set
crosses a page boundary, or the server changes its incidental ordering,
the answer silently becomes wrong in both directions.

**The case.** `soda()` pages with `$limit`/`$offset`. Offset paging over
an *unordered* result is only as stable as the server's accidental row
order: the same offset can re-serve a row it already sent and skip one it
has not, so groups are dropped and duplicated at the page boundaries and
the sums stay entirely plausible.

Adding `line_description` to the city revenue fetch (V21) took it from
~9,600 groups per year to **176,949** — past the 50,000 page size — and
**all 3,837 city-years then missed their published control, in both
directions, by up to $41M**. The reconciliation gate caught it and
refused to write, which is the system working exactly as intended.

The part worth recording is what the investigation of that failure
turned up: **the expenditure query has been over the page boundary the
whole time.** Measured at **98,351 groups per year** against the same
50,000 limit, also with no `$order`. It has always reconciled — so it
has always been *correct* — but only because Socrata happened to return
stable ordering across pages. It worked by luck, and the only thing that
would ever have told us otherwise was a gate failing.

**What changed.** `soda()` now raises on any grouped query that does not
declare an `$order`, so the class of bug cannot be reintroduced silently;
both city queries and both county queries declare one.

**Still open.** `fetch_district_data.py` has its own local `soda()` and
four grouped queries with no `$order`. Measured, they are **42,117** and
**37,319** groups against a 50,000 limit — under it, so they fetch in a
single page and no paging occurs today. They are correct, and they are
within ~16% of the boundary; the district roster only grows. They were
deliberately left untouched (that pipeline is mid-review for a separate
tier question) and should get the same guard when it is next opened.

**The general rule.** "It reconciles" is evidence about today's data, not
about the contract. When a query's result set can grow past a page, make
the ordering explicit — and prefer a guard that refuses the ambiguous
case over a test that would only notice after the numbers moved.

### 2f. In a printed table, every parsing error looks like a number

**Shape.** Extracting figures from a PDF table is not like reading a
feed. A feed that breaks yields an error or an empty result. A printed
table that is mis-parsed yields *a number* — correctly typed, plausibly
sized, sitting in the right column — and nothing downstream can tell it
from the truth. The only defence is an identity the document itself
guarantees, asserted on every row.

**The case.** Schedule 8 (state actual revenues, V21) took eight
distinct hazards to parse, and **not one of them produced an error**:

| Hazard | What it produced |
|---|---|
| `$ --` zero form | window slid into the next row — $6.4B General Fund residual |
| a bare comma matched as a value | run chained through name commas — 136 lines parsed as 3 |
| a value matched a *prefix* of the next account code | 136 parsed as 71 |
| name contains digits (`Leases - 1 Percent`, `2011 Realignment`) | window off by one, in **both** directions |
| `$ -7,533,537` — minus *after* the dollar sign | totals row truncated to four tokens |
| `- -` as an alternative zero marker | rows silently dropped |
| the `"- $"` rewrite inherited from `schedule9.py` | ten positive figures turned negative |
| our own `- -` fix firing inside `- --` | produced `---`, dropping rows again |

The seventh is the interesting one, because it has **no correct answer
in isolation**: `- $` is a real negative in `Revenue Transfers - $931,165`
and a wrapped name's trailing hyphen in `Excise Tax - $177,475 … Beer and
Wine`. Removing the rewrite loses real negatives; keeping it mis-signs
names. Nothing in the text distinguishes them.

**What resolved it.** The document guarantees an identity — General Fund
+ Special Funds = Total, in each of three column groups. So the parser
does not *decide* where the nine values start: it tests every candidate
window against that identity and requires exactly one to satisfy it.
Ambiguity is refused rather than guessed. The sign question is then a
*hypothesis* the same identity settles — the row is retried with the
leading sign reversed only if nothing foots, and that repair fires
**exactly once across ten publications**, on the single row it exists
for.

**The general rule.** When parsing a printed table, find an arithmetic
identity the publisher already guarantees and assert it per row, before
any total is computed. A totals gate alone is not enough — it tells you
*that* something is wrong, not *which* row, and several of the hazards
above cancelled partially and would have needed only a slightly looser
tolerance to pass. Prefer refusing a row you cannot align over reading
it optimistically.

### 2g. "No mark earned" is not the same claim as "fully itemised"

**Shape.** Three layers in a row were asked the same question — does this
source have a legibility defect worth marking? — and the first two
answered no for the *same* reason: no placeholder construct exists, the
words *specify*, *unspecified*, *all other*, *sundry*, *unallocated*
appear nowhere. It is tempting to reuse that sentence. **For K-12 it
would have been false.**

SACS carries nine catch-all revenue objects. `All Other State Revenue`
alone is **$16.6B, 11.2% of all K-12 revenue**; the nine together are
**$29.0B, 19.5%**. Reusing the sibling prose would have put a
demonstrably untrue sentence on the page.

**But no mark is earned all the same**, for a different and narrower
reason: the mark the city and county records carry is for a *withheld
write-in* — a field where the filer typed an answer the publisher did
not print. **SACS has no free-text field anywhere in its schema.** It is
codes and values throughout, every code resolves to a title CDE
publishes, and $0 of revenue sits on an unnamed resource. There is
nothing for a filer to type, so there is nothing to withhold.

**And the honest qualifier.** "No mark" must not be heard as "every
dollar is itemised". Most catch-all money stays traceable because the
account string also names a Resource — 8590 decomposes across 107 named
resources, 94% of its dollars on a specifically named one. What is
generic at *both* levels — a catch-all object on an unrestricted or
residual resource — is **~5.5% of revenue**, and the layer measures that
share on every run and publishes it beside the year rather than
describing it.

**The general rule.** A verdict inherited from a sibling layer is not a
verdict. Ask the question against *this* source's data, and when the
answer is "no defect of that kind", check whether a defect of some
*other* kind is being waved past by the same sentence. Publish the
qualifier as a number, not an adjective.

### 2h. A published cell count that does not reproduce

`docs/V21_REVENUE_FINDING.md` shipped the figure *63,811 published
control cells* for the K-12 gate. Building the layer, it did not
reproduce: the revenue-only control is **64,811** cells, the all-object
control **356,484**. A brute-force search over every object range with
and without a nonzero filter produced no variant equal to 63,811, and
the figure appears once, in prose, with no script beside it.

The number was corrected in place with a visible correction note rather
than quietly edited, and the shipped layer **recomputes its cell count
every run** instead of quoting a constant. A figure a reader could check
should never be a literal in prose when it can be a measurement in code
— that is the same rule the site applies to the data it publishes, and
it applies to the findings too.

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
