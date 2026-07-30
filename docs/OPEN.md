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

### 2i. A gate that passes may be a gate drawn around the hole

The special-district expenditure layer was queued to be re-tiered from
as-filed to gated. The case looked strong: the site publishes four
per-fund-class buckets, SCO publishes a control per fund class, and a
prior measurement reported **4,869 of 4,870 bucket figures exact to the
dollar**, zero failures. Re-verification reproduced that arithmetic
exactly — **and the layer still must not be gated.**

**Only one bucket of four has a control whose unit is the same object.**

| bucket | what SCO publishes |
|---|---|
| `gov` | a real per-filer total — same accounting object |
| `ent` | `Total Operating` and `Total Nonoperating` as **separate** columns, 22 across 11 sheets, never their sum |
| `isf` | same shape; 19 entities, too thin to call tested |
| `cf` | same shape — **and the pass is the problem** |

For `ent`/`isf`/`cf`, "reconciling" means adding the components up
ourselves and confirming our own arithmetic. That is not a gate. The
unit differs too: enterprise figures are accrual *expenses* including
depreciation, not modified-accrual *expenditures*.

**The `cf` bucket is the lesson.** It reconciles 14/14 and 13/13 —
perfectly — but only because the site's bucket is conduit-financing-only
while SCO *also* declares **fiduciary-fund activity the Socrata feed
never publishes at all**: measured, zero rows anywhere in `m9u3-wdam`
mention Fiduciary, in any year, while the workbook declares
**$798,570,859** across four transportation filers in two years. Western
Riverside COG publishes **$13.5M** on this site against **$385.4M** of
fiduciary deductions declared beside it — a 28× understatement.

A `cf` gate defined to pass is a gate defined *around* that hole. The
100% would have been the evidence for shipping it.

**The general rule.** Before accepting a reconciliation, ask what the
control is a control *of*, and what it would look like if the source
simply never published part of the answer. A gate that passes at 100%
deserves more suspicion than one that passes at 99%: the residual is
where the questions live, and a perfect score can mean the boundary was
drawn where the residual isn't.

### 2j. The stale claim landed in 74 places, in six wordings

"No control-total dataset exists for special districts" has been on the
site since V5. It is false — a governmental-funds control exists — and
correcting it meant finding every place it had spread. **74 occurrences
across 17 files**, in at least six distinct wordings, of which **36
asserted non-existence** (and had to change) while 32 said only that no
gate is *used* (and stayed true). The two that a search for the sentence
would have missed:

- a headline **stat tile** rendering `["NONE", "CONTROL TOTAL PUBLISHED"]`
- a **causal clause** — "…because no control-total dataset exists" —
  whose *reason* dies with the claim even though the conclusion survives

Also caught: **six test assertions that pinned the false sentence**,
including one whose stated purpose was to guarantee it stayed on the
page. A test can hold a claim in place long after it stops being true.

This is the M-7 lesson repeating, and the count is the point: when a
claim is corrected, enumerate before editing, and classify each hit by
*what it asserts* rather than by the words it uses.

### 2k. A stale build artifact hid a real regression

Rebuilding `search-index.js` as part of this work made a passing test
fail. The test was right and the index was stale: UC's comparability
flags moved to the year level when that layer went multi-year (V18b),
`flag_count()` was not moved with them, and every UC campus silently lost
its note marker. The shipped index had been built *before* that
restructure, so the assertion kept passing against data that no longer
matched the code that produced it. CCC was affected the same way.

**Generated files that are committed can hold a fixed answer in place
across the very change that breaks them.** Rebuild them when the shape
of their inputs changes, not only when their content is supposed to.

### 2l. A layer that cannot refresh itself goes stale in silence

Two layers on this site cannot be rebuilt by `--refresh`: CSU, whose
audited statements are bot-gated, and compensation, whose source
expressly excludes automated retrieval. Both fail in the same quiet way
— the page keeps rendering, every figure stays exactly as published, and
nothing says the record has stopped being current. **A stale record does
not look stale.**

The fix has to reach two different people, so it is announced twice, at
the same threshold, in the same words:

- **the reader** — a vintage band on the layer's own page, always
  visible, that turns conspicuous once past the threshold. Staleness is
  a fact about the record, not only a maintenance task.
- **the maintainer** — a scheduled job (`pipeline/check_vintage.py`,
  run weekly by `.github/workflows/vintage-check.yml`) that opens an
  issue. A test in the suite is not enough: it fires only when somebody
  runs the suite, which is exactly what a forgotten layer does not get.

**Two things that were nearly wrong.** The check first read CSU's
`meta.generated` — the day the pipeline last ran. That measures *our*
activity: the layer could sit three years behind its source and report
current forever, as long as anyone rebuilt for any reason. It now reads
`meta.year`, the fiscal year of the statements themselves. And the
scheduled job **reads dates from the repository and fetches neither
source** — for compensation that is not an optimisation but the whole
point, since a staleness checker that crawled the excluded host would
contradict the reason the exception exists.

### 2m. Two exceptions are a limit; two one-offs are a broken claim

The site's claim is that any figure can be rebuilt from published
sources. Before this work, one layer was excepted and the about page
said so — *"the one layer that is NOT auto-reproducible"*. Adding a
second exception made that sentence false, and the natural failure is to
add a second footnote somewhere else and leave the first standing.

So both are now named **together**, in one breath, wherever the rebuild
claim appears — README, about page, both layer pages, and the pipeline
docstring — with the reason stated: *two documented exceptions are a
limit, two one-offs are how a rebuild claim quietly stops being true.* A
test asserts the old "one layer" sentence is gone, so the claim cannot
silently revert.

**If a third is ever added, it goes in those same places.** The moment
the exceptions are described separately is the moment the reader can no
longer tell how much of the site is actually reproducible.

### 2n. The first page that needs a server

Every page on this site was a file that worked from a double-click:
data arrives by `<script src>`, which a browser loads from `file://`,
so the whole site clones and reads with no server and no build. The
compensation layer broke that, and the break is worth naming because it
was invisible until looked for.

**Verified, not assumed:** `compensation.html` is the only page in the
repository that calls `fetch()` at runtime, and every other page was
re-opened from a `file://` URL after this shipped and renders fully.

The reason is size. 1,407,216 position rows encode to **46.1 MB raw /
14.3 MB gzipped** even with shared vocabularies and integer-array rows,
against a previous site-wide largest payload of 14.8 MB. One file would
make every reader download all of it to look at one city. So the index
loads with the page and per-employer detail is fetched on demand.

**What it cost, measured** — shallow clone, with and without:

| | tree | `.git` | files | clone |
|---|---|---|---|---|
| without | 41 MB | 10 MB | 125 | 0.22 s |
| with | 117 MB | 25 MB | 4,264 | 0.66 s |

The rebuild claim survives; the file count is the bigger change.

**Two things this required beyond the code.** It degrades the way the
map does when tiles fail — naming what failed *and* what still holds,
never a blank and never a substituted number — and on a `file://` path
it says so explicitly, since that is the likeliest cause and the reader
would otherwise think the page is broken. And it is written down in
`docs/SCOPE.md` as Exception 3, beside the two manual-cache exceptions,
because **a load pattern that isn't recorded becomes an undocumented
dependency**: the next person to add a page has no way to know the
double-click rule ever existed.

### 2o. A test that intercepts a request must prove it intercepted one

The degradation test above passed on its first run while testing
nothing. It navigated with `goto(url + "#hash")` to a page already open,
which is a **same-document navigation** — the script never re-runs, no
request is made, and the assertions read the *previous* employer's
successfully-rendered table. The route interception was registered
correctly and simply never fired.

The fix is two lines: force a new document (a query string does it), and
**assert the interception actually happened** before asserting anything
about the failure it was supposed to cause. A negative-path test that
cannot tell "the failure was handled well" from "the failure never
occurred" is not a test.

### 2p. A guard is only as wide as the formats it covers

`strict.py` has protected `.mdb` column reads since the K-12 pipeline hit
four confident wrong numbers. It could not protect anything that never
bound names at all — a spreadsheet row read as `row[2]`, a TSV split into
`parts[5]`, a fixed-width line indexed by position. **That is not a
different defect. It is the same one with the failure moved earlier**, and
it duly happened: the FY2016-17 city workbook orders its columns
differently from the FY2022-23 one, so a positional read correct on the
newer vintage returned entity ids where the fiscal year belonged.

**The header was in the file both times. Nothing read it.**

An audit of every source read in the project found the pattern in four
places and, more usefully, found that **the two worst were the ones with
no gate downstream**:

| site | positional read | protected by |
|---|---|---|
| CSU TSV `headcount` | `parts[5]` | **nothing** — the module's own note says there is no independent figure to reconcile it against, and it is the denominator of every per-student figure |
| district Socrata `co` | `.get()` on a raw dict | **nothing** — it is the county half of the (name, county) identity that keeps two same-named governments apart |
| school LCFF codes | `row[1]`, `row[2]` | header detection pinned column 0 only |
| Schedule 6 history row | `f[4]`, `fields[6]` | a cross-document gate — a shift fails loudly |

**The distinction worth keeping:** a positional read whose output is
immediately reconciled against an independent source is self-protecting;
one whose output is *published* is not. Audit for the second kind first.

Two details that made the fix better than a search-and-replace:

- **The CSU TSV already declared its own schema**, in a comment line the
  parser skipped along with every other comment. The fix was to read the
  declaration that was already there, and to refuse outright when it is
  absent rather than fall back to position.
- **`dict(zip(header, row))` is not a safe binding.** It silently drops a
  row *wider* than its header, so the columns a newer vintage added
  vanish with no error. `strict.bind` refuses that, while still allowing
  a *shorter* row — whose missing names then simply do not exist, which
  is the honest shape for a ragged publisher row.

**Nothing depended on the silent behaviour:** every payload rebuilt
byte-identical (district) or identical but for the build date (CSU), and
the K-12 gates passed unchanged. A guard that changes no output is doing
its job — it changes what happens on the day the source moves.

### 2q. Adjacency is a claim, and no caption retracts it

V25 asked whether voter-approved bonds could be shown against what is
spent from them. Every individual fact was publishable — CEDA's measure
record, CDIAC's issuance, SACS Fund 21 spending — and the layer still
fails, because **what is unreconciled is not a figure but a
relationship**, and the site's tier vocabulary has no label for that.

The three links and how each breaks are in
`docs/V25_MEASURES_FINDING.md`. The transferable part is the shape:

- **A per-figure tier label cannot mark a per-relationship problem.**
  *As-filed* says *this number is unverified*. It has nothing to say
  about two verified numbers placed so as to imply they reconcile.
- **Layout asserts.** A purpose beside a figure reads as that purpose's
  spending. That reading survives any note placed underneath it, because
  the grammar of the page is stronger than the caption.
- **The generic-code check belongs early in any drill-down question.**
  One query settled this: Fund 21 carries **5 distinct resource codes
  over 11,438 rows, 98.5% of them generic**, and **84.6% of $8.74B sits
  in a single object code** while ballots name a median of 4 purposes.
  When the dimension a reader wants does not exist in the source, no
  amount of joining upstream creates it — ask that first, not last.

This is the same refusal as the V21 §4 surplus, the V24 reserve ratio
and the V24a deficit-beside-spending, and it is worth naming as one
rule: **the site does not place two quantities together unless it can
say how they reconcile.**

### 2r. A field that exists is not a field that informs

V26 asked for adoption provenance — who approved each budget, and when.
The field turned out to **exist, be machine-readable, be point-in-time
correct, and still not be worth shipping**, which is a failure mode the
project had not yet named.

`publicationDate` on DOF's eBudget API returns `"Enacted on June 26,
2024"`. It is a genuine published fact and the pipeline already fetches
it. But across the nine published years the value is **June 27, June 27,
June 27, June 26, June 28, June 27, June 27, June 26, June 27** — a
three-day range, six of nine identical, because the signing date is set
by a constitutional deadline rather than by anything about the budget.

The contrast that makes the rule concrete is **already in the codebase**.
The CCC layer stamps every apportionment with its round — `ROUND_NAME` at
`ccc.html:309`, First Principal / Second Principal / Recalculation — and
`meta.roundsDiffer` explains they "are computed at different points from
different information, and they are not interchangeable." That is the
same feature V26 proposed, shipped, on the one layer where the stamp
changes the number. **Provenance earns its place by varying**; the CCC
round does, the Budget Act signing date does not.

The test that generalises: **before building a per-record field, measure
its variance across the records.** A field that is constant, or nearly
so, adds a column and no information, while *implying* a variability
that does not exist. Three checks worth running first:

- **How much does it vary?** Nine years, three distinct values.
- **Does the site already say it better?** `index.html` already read
  "fixed when each year's Budget Act is signed… typically signed in late
  June" — one sentence carrying more than nine near-identical dates.
- **Does it vary where it is unavailable?** Measured: 479 of 482 cities
  close on June 30, but special districts show **9 distinct
  fiscal-year-ends across 5,111 entities**. The population whose adoption
  dates would genuinely differ is exactly the one with **0** adoption
  fields in 27,916 SCO column names. **The date is near-constant where it
  is published and unpublished where it would vary.**

Three smaller lessons from the same probe:

- **A robots block on the HTML front end is not a block on the data.**
  This one nearly produced a wrong refusal. `leginfo.legislature.ca.gov`
  serves `User-agent: * / Disallow: /`, and the first draft of V26 cited
  that to conclude the Budget Act chapter number would need a third
  manual-cache exception. It would not: the Legislature publishes bulk
  session archives on `downloads.leginfo.legislature.ca.gov`, which
  carries **no** exclusion — verified by content, a real Apache 404 for
  `/robots.txt`, an 8,519-byte directory index, and `206 Partial
  Content` with `50 4b 03 04` on a range read. **Check the publisher's
  bulk/download host before recording an access refusal**, and never
  infer a data-access policy from the policy on its web UI.
- **Storing is not showing.** Keeping `publicationDate` in the payload
  for the change record is cheap and useful precisely because nothing
  renders it; that remains a live V13 item. The refusal was to the
  reader-facing label, and the two questions must not be answered
  together.
- **A sentinel is not a date.** For years not yet adopted the same
  endpoint returns `"Enacted on January 01, 9999"` with an empty
  `/statistics`, while still reporting `publication: "Enacted"`. A naive
  build of this field ships *1 January 9999*. The pipeline's existing
  guard is indirect — it drops years with no agency data — and nothing
  checks the date itself.

**And the methodological lesson, which cost seven corrections in one
finding.** V26's first draft asserted that only the state page shows an
adopted figure, and that no source anywhere carries an adopting-body
field. An adversarial pass refuted both — eBudget publishes a per-year
`governor` string at `/api/home/getLink`, and `schools.html` renders "$81.6B
enacted", `ccc.html` renders "$9.7 billion", `csu.html` exports a
`state_appropriation_thousands` column. The same pass found that the
layer count was mis-sourced, the `meta.basis` tally was off by one
payload, and the FTR keyword sweep had omitted `appropriat` — which is
28 header cells and the **Gann appropriations limit**, a genuinely
board-adopted figure sitting in a corpus the finding had just called
free of anything adopted.

They are all one error: **an absence claim resting on a search whose
terms I chose.** `/appInfo`'s nine keys were treated as the source's
whole surface; the refuting agent enumerated the real API by reading
eBudget's own JS bundle. The counts (27,916 cells, 25 columns) made the sweep
*look* exhaustive while the keyword list quietly bounded it. Two habits
follow:

- **State the search terms next to the count**, so "0 hits" is legible as
  "0 hits *for these words*" rather than as "nothing there".
- **For any "the source contains no X" claim, have it refuted before
  publishing it.** Enumerating what *is* present is weak evidence; a
  reader hunting for a counterexample is strong evidence. Every one of
  V26's substantive errors was invisible from inside the original method,
  and the conclusion happened not to rest on any of them — which is luck,
  not method.

### 2s. A two-branch conditional on an N-valued field drops the Nth

Phase C3 taught the payload to distinguish three absence states —
**a real reported zero, not-published, and held**. The data change was
correct and the tests for the data passed. The page broke.

`ccc.html` branched on `basicAidStatus` in two arms, `basic-aid` and
`not-published`, written when the field had exactly those two meanings
plus a silent third (`state-funded`, which correctly renders nothing).
The moment the pipeline emitted `held`, that value matched neither arm
and fell out of the chain. The COMMUNITY-SUPPORTED caveat did not render
wrong — **it did not render at all**, on precisely the 144 district-years
whose figure most needed it, because held means the source published two
figures that disagree.

**The failure is silent by construction, and it fails toward reassurance.**
A missing caveat and an inapplicable caveat are the same pixels. A reader
cannot tell "this page has nothing to warn you about" from "this page has
a warning it does not know how to say", and the first is what an absent
note looks like. The same shape appeared in three more places, found by
sweeping rather than by memory:

| site | shape | what an unrecognised value did |
|---|---|---|
| `ccc.html` `basicAidStatus` | two arms of three | dropped the caveat entirely |
| `schools.html` `basicAidStatus` | `!== "not-published"` reads as KNOWN | rendered as **state-funded** |
| `address.html` `schoolNotes` | same as schools | same |
| `ccc.html` `apportionmentStatus` | `if round / else if not-published` | no comparability strip |

`schools.html` is the sharpest: `baKnown = v.basicAidStatus !==
"not-published"` means *any* future value is treated as known, and being
not `basic-aid`, it renders as state-funded — **an unrecognised state
displayed as a specific, reassuring one.**

**The rule.** Where a field has N values, a chain of N−1 tests is a
defect even when it is currently exhaustive, because exhaustive-today is
a property of the data and the chain is a property of the code, and the
two drift apart without a diff. Enumerate the states in a named list next
to the branch, and give the chain a final arm that says the state was not
recognised. The unrecognised arm should be **noisy and legible to a
reader** — the person harmed by a missing caveat is the reader, not the
maintainer, so a console warning is the wrong instrument.

This is the same defect class as the **enumerated page list**, the
**enumerated digest list** and the **enumerated GATED list** already
recorded here, arriving through a different door. Those enumerate
*subjects* and go stale when a subject is added; this enumerates *states*
and goes stale when a state is added. The remedy is the same in shape —
derive, or fail loudly — but it cannot be "glob the disk", because the
states live in the data. So the guard is a swept assertion:
`test_status_exhaustiveness` discovers every `\w+Status ===` comparison
across the HTML on disk and requires that file to declare what it does
with a value it does not recognise. A new branch is covered the day it
ships, which is the property the enumerated lists lacked.

**And the tests did not catch it, twice over.** The data assertions
passed, because the data was right. The UI assertion that *should* have
caught it was pinned to the old two-state encoding: it built a set named
`held` by filtering on `"not-published"` — the name recorded the intent,
the filter recorded the world before the change, and for as long as the
two states were one value the discrepancy was invisible. **A variable
whose name and whose filter disagree is a comment that lies**, and it
survived review because it passed.

---

### 2t. A defect that heals itself between runs gets dismissed, not fixed

The CCC pipeline wrote two scratch PDFs — `_dcc_tmp.pdf` and
`_exc_tmp.pdf` — **into `pipeline/cache/`**, the tree `cache_guard` exists
to keep read-only. They were byte-for-byte copies of files already sitting
there, written only because pypdf and pdfplumber wanted a path to open.
Five `SystemExit` paths sat between the write and the single unlink, with
no `try/finally`.

**It shipped with the CCC layer and survived every run since, because it
repairs itself.** The sequence is exact:

1. Something exits between the write and the unlink, orphaning the file.
2. The next suite run's cache guard finds it. **One assertion fails.**
3. Later in that same run, the suite executes the pipeline module again
   (it does so four times, each wrapped in `except SystemExit: pass`).
   One of those reaches the unlink and deletes the orphan.
4. The next run is green.

So the observed signal is: *fails once, passes on re-run, no code change
in between.* That is the exact signature of flakiness, and flakiness gets
re-run rather than investigated. The defect was **structurally guaranteed
to be dismissed** — not because anyone was careless, but because it
presented as the one thing a maintainer is trained to discount. It took a
run that failed while someone happened to be reading the output closely
for it to be looked at at all.

**The rule: a failure that does not reproduce is not thereby absolved.**
Before re-running, establish whether the run itself could have cleared the
condition. A test suite that exercises the code it is testing can repair
the state it is testing — and then reports success. "It passed the second
time" is evidence about the second run, not about the defect.

**Fixed by removing the write, not by guarding it.** A `try/finally` was
the obvious repair and is the wrong one: it still creates a writable file
inside a protected directory and merely shortens the window. The invariant
would be *broken and restored* rather than never broken, and a guard whose
assertion is false for part of every run is not an invariant. The cached
source is already on disk and read-only means readable, so both call sites
now read the original — one via `io.BytesIO`, one via the cached path.
It also tightens the evidence chain: the extractor now parses the exact
file the integrity digest covers rather than a copy of it.

**The sweep found a second, quieter one.** `fetch_deflator.py` wrote its
cached xlsx with a bare `dest.write_bytes(blob)`, bypassing
`cache_guard.write_cached`. That leaves a **permanently** writable source
in the protected tree after any `--refresh` — no orphan, no flake, no
symptom at all until some later `cache_guard lock` sweep happened over it.
The self-clearing defect at least announced itself intermittently; this
one never did. **Silence is not evidence of correctness**, and the reason
to sweep by structure rather than by memory is that the quiet defect and
the noisy one look identical to a grep for the thing you already know.

`test_no_scratch_in_protected_dirs` now walks every `pipeline/*.py` with
`ast`, derives each file's protected roots **from its own assignments**
(so a third spelling beside `CACHE` and `CACHE_DIR` is still covered),
propagates through path joins to a fixpoint, and fails on any write,
rename, unlink, chmod, write-mode `open` or `shutil` copy landing inside.
Verified against the pre-fix tree: 4 of 4 sites detected.

---

### 2u. Reading the printed sheet back finds what the screen hides

C4 required every print sheet to carry the basis line, the tier wording,
every note in full, the three absence states and the record's provenance.
The measurement was a real PDF, rendered through the print stylesheet and
read back as text — not the DOM under `emulate_media("print")`, which
measures what a page **intends** to print rather than what a reader holds.

**The structural defect was the enumerated list again, arriving through
CSS.** `index.html` and `cities.html` printed their tier chip and basis
line for one reason only: their print blocks do not hide `.hero`, which is
where both live. `ccc.html`, `csu.html` and `uc.html` **do** hide `.hero`,
so both vanished — and those same three pages reveal a `#printCite`
element that does not exist on them, so the citation string was absent
too. Whether a reader could tell what a figure **measured** depended on
which selectors each page's `@media print` block happened to list, and
that list had already drifted on three of nine layers.

The fix is the same shape as every other cure for an enumerated list:
**the sheet composes its own identity** from the live `basisLine()` and
`citationText()` and from the rendered chip's own label, so no page's
print CSS can take it away and no sheet can state a basis the page is not
showing.

**Two bugs were invisible until the paper was read back:**

- **`ccc.html` printed its own source code.** `citationText()` contained
  `'FY \' + S.year + \' (CCFS-311…'` — inside a single-quoted string,
  `\'` is a literal apostrophe, so `S.year` was never interpolated. Every
  citation this layer produced read *"FY ' + S.year + ' (CCFS-311"*. It had
  shipped, on the one string whose entire purpose is to be quoted
  elsewhere.
- **`ccc.html` printed `undefined`.** The record legend read
  `sw().communitySupported + " COMMUNITY-SUPPORTED"`, and for a year whose
  community-supported figure is HELD or NOT PUBLISHED there is no number —
  so the legend said *"undefined COMMUNITY-SUPPORTED"*. A C3 state
  reaching a place C3 had not been applied.

Both were on screen too. Neither had been noticed, and the reason is
worth naming: **on screen a defect is provisional** — a reader assumes
they caught it mid-load, reloads, and moves on. On paper it is final. The
sheet cannot be refreshed, so reading it back is a harsher test of the
same markup, and it is worth doing precisely because nothing about it is
new code.

**Greyscale is checked by measurement, not by eye.** Every `@media print`
body is parsed for chromatic colour — any value whose red, green and blue
channels are not equal — and the site's one accent, `#2b59d1`, is refused
in a print block outright, because it is reserved for things a reader can
operate and nothing on paper is operable. The positive control carries the
weight: the accent **must** appear outside the print blocks, or an empty
result would mean "found no CSS" rather than "found no colour".

**And the mark is never the encoding.** Every tier chip is checked to pair
its glyph with a text label, with the glyph `aria-hidden`. A printout, a
screen reader and a greyscale photocopy all receive the words; the mark is
decoration on top of them. This is what B-1 promised and what a chip alone
would have quietly broken.

---

### 2v. A bad input does not stay contained — it becomes a confident claim

Mt. Shasta filed a population of ~86,000 against a real ~3,200, and every
per-resident figure derived from it stopped measuring anything. That was
recorded, guarded, and treated as a one-off. It was a shape.

**Six city- and county-years are published by the State Controller as a
COMPLETE schedule of zeros** — all 237 rows, none null, every value the
string `"0"`, expenditures and revenues together — sitting between years in
the ordinary range:

| entity | year | prior year | false derived claims |
|---|---|---|---|
| Hollister | 2021-22 | $69.9M | lowPolice, lowFire, bigSwing |
| Novato | 2021-22 | $58.8M | lowPolice, lowFire, bigSwing |
| Woodland | 2022-23 | $74.8M | lowPolice, lowFire, bigSwing |
| Humboldt County | 2019-20 | — | bigSwing |
| Humboldt County | 2020-21 | (also zero) | **none — by luck** |
| Mendocino County | 2021-22 | — | bigSwing |

The zeros were never the harm. **The derived flags were.** `lowPolice` and
`lowFire` fire when a function divided by a real population falls under
$5/resident, and $0 is under any threshold; `bigSwing` fires when the ratio
to a real prior year leaves a 40% band, and zero leaves every band. So the
live site stated, of three real cities, that **they spend unusually little
on police and fire** — eleven affirmative false claims, each one derived,
each one looking like analysis rather than like a missing input.

**Humboldt FY2020-21 is the entry that matters most.** It carried no flag
at all — not because a guard worked, but because the *prior* year was also
all-zero, so `prev_gov > 0` was false. The absence of a false claim there
was arithmetic luck. A defect whose visible symptom depends on whether the
neighbouring row happens to be broken too is a defect you cannot find by
looking at symptoms.

**Three of the six were found only by sweeping.** Two were reported; the
other four came from querying every entity-year at source for the shape.
Checking the named cases would have fixed half the problem and closed it.

**HELD, not not-published, and the distinction is the whole finding.** SCO
publishes **no filing-status for cities or counties** — the delinquency
lists with `Filed Late` / `Failed to File` cover special districts only.
So at source, a report of zero and a report never filed are
indistinguishable, and *"this is an absent filing"* — which the county
note asserted for a year before this — was a conclusion the data does not
support. It was the Ledger's inference wearing the clothes of a fact.

The honest state is the C3 third one: the source spoke, the Ledger will not
choose. Corroborated rather than assumed — **SCO's own published control
for these entity-years is also zero**, so the gate reproduces zero against
zero and proves nothing, which the county pipeline had already been saying
in its own output (*"control is zero"*) without anything downstream acting
on it.

**Derived in the pipeline, from whether ANY non-zero value appeared while
reading the source** — not reconstructed afterwards by testing the built
total for falsiness. A total of zero can also come from real figures that
offset, and those are different facts. `cities.html` had been inferring the
county note from `if (!yr.expenditures)`, which is precisely what C3
forbids; it now reads the status the pipeline wrote.

**The negative control is where this nearly went wrong.** The first version
asserted that "the derived flags still fire on real filings" by counting
the **union** of the three. A mutation that silenced `lowPolice` and
`lowFire` *globally* passed it, because `bigSwing` alone fires on 274
city-years and carried the check by itself. **A control that one surviving
member can satisfy is not a control over the others.** It now requires each
flag independently, and reads which flags a layer computes from that
layer's **pipeline source** rather than from its payload — reading the
payload would be circular, since a global suppression empties it and the
check would have nothing left to require.

And the same status travels into `bulk/cities.csv` and `bulk/counties.csv`
as a `filing_status` column, because a CSV has no notes panel: a row of
zeros without a marker reproduces the defect in the artefact people load
into a spreadsheet and never revisit.

---

### 2w. Two ways to state a reconciliation wrongly, and both look like findings

Phase D states, at the figure, whether the children on screen sum to the
parent above them. The identities were already gated and already measured.
Stating them turned out to be where the errors were, and both errors
manufacture a number that reads as a discovery about California.

**SCOPE.** The state page's fund list carries federal rows whether or not
the page is showing federal funds, while the department figure follows the
toggle. Summing all funds against a state-only figure reported a **$99.5
billion residual** on a department that reconciles exactly. The two sides of
an identity must have the same scope, and a residual is meaningless until
they do.

The same shape appears wherever several parents share a view: the cities
compare view shows two or three entities at once, so there is no single
parent and no identity to state. Summing its children would produce a
residual against whichever parent happened to be first.

**PRECISION.** Cities store `byFunction` to three decimal places of $1
million — $1,000 granularity — while the state form's line items are exact
dollars. So fifteen rounded function rows differ from the governmental total
by up to a few thousand dollars, always, for reasons that have nothing to do
with any city. Departments-to-funds on the state page has the same shape at
$1M granularity.

**A residual that comes from our own storage is not a residual.** Publishing
it would be the mirror of distributing a real one: distributing makes every
child slightly wrong to make the total right; publishing an artefact makes
the source look inconsistent to make our arithmetic look complete. Both are
labelled, and the label says whose the difference is.

The measurements that make the distinction sayable, taken before any footer
was written:

| identity | result |
|---|---|
| cities function → form lines | within $500 of a $1,000 grain, 37,581/37,581 |
| cities Σfunctions → governmental total | within $3,000, 15 rounded rows |
| schools Σfunctions → Current Expense | **$0.0000**, 8,427/8,427 |
| schools function → objects | **$0.0000**, 50,902/50,902 |
| schools Σfunding-source groups → CE | **$0.0000**, 8,427/8,427 |
| CCC Σdistricts → printed statewide | **$0**, all 15 published years |
| state Σagency rows → DOF control | exact 7/9; residual $2.353M, $1.638M |
| state departments → agency | never reconciles; $4.8B–$13.2B |
| state funds → department | exact within $1M storage, 6,916/6,916 |

Schools is the one layer that can make an unqualified claim, and it can
make it three times — so the footer says which route it is describing
rather than implying all of them.

**AND A THIRD ERROR, ONLY VISIBLE ON PAPER.** The printed sheet reads its
reconciliation from a variable the footer sets. Both run inside the same
`render()`, and the sheet won the race: it read the variable while it was
still empty, so RECONCILES reached **no sheet on any layer** while every
on-screen footer was correct. Inverted — the footer now delivers itself into
the sheet, replacing rather than appending, so whichever paints last the
block is right. Found by rendering a PDF and reading the text back; nothing
on screen showed it, and no amount of reading the code suggested it.

---

### 2x. A failed reconciliation is not a residual, and a minus sign is not an error

UC finished Phase D with the two cases the footer vocabulary had not yet
had to express.

**A HELD YEAR HAS NO RESIDUAL, BECAUSE IT HAS NO FIGURE.** FY2019-20's
campus table does not reconcile: campuses + Systemwide + the added-back DOE
line come to 43,405,055K against an audited 43,405,406K, and the 351K that
would close it appears nowhere in UC's document. Every later year ties
exactly, so this is not a tolerance anyone could widen.

The tempting rendering is a residual line beside the campus figures, the
same shape the state page uses for DOF's $1.638M. That would be wrong, and
the reason is worth stating: **a residual sits beside a figure the Ledger
publishes and qualifies. This year has no such figure.** Showing one would
let a reader take the campus numbers as shipped-with-a-caveat when in fact
nothing is shipped. So the page states the arithmetic and labels the gap
*DOES NOT CLOSE — short by 351K*, and says the year is withheld **for that
reason** rather than published at a lower tier.

**A NEGATIVE PRINTED COLUMN IS A FACT ABOUT THE SOURCE'S TABLE.**
FY2024-25's Systemwide column is −306,871K. It is one printed cell in UC's
own campus table — UC's label: *"Systemwide (UCOP, DOE laboratory &
eliminations)"* — and it nets four things: systemwide operations
(−840,427K), the DOE laboratory (+1,194,419K), and the eliminations that
remove medical-centre (−591,981K) and auxiliary (−68,882K) activity already
counted inside the campus columns. The eliminations are subtractions; in
this year they exceed what the column adds, so the printed cell is
negative. It sums to the audited total exactly.

The rule this settles: **state what the line contains and let the sign
follow.** The page does not call it an anomaly, does not apologise for it,
and does not redistribute it across the ten campuses to remove the minus —
which would move money into ten records where UC put it in none. Every
characterising word is refused by assertion: *error*, *anomalous*,
*incorrect*, *mistake*, *should be*.

**AND THE SCOPE ARTEFACT HERE IS WORTH A BILLION DOLLARS.** UC's campus
table EXCLUDES the DOE laboratory in the earlier vintages and INCLUDES it
from FY2021-22. The identity therefore has two forms, and the form is read
from each year's own `doeForm` declaration. Applying one year's form to
another double-counts or drops the DOE line — mutation-tested, and it
produces a phantom residual of exactly **$1,194,419K** on a year that
closes at zero. Precision is not a risk on this layer at all: UC publishes
thousands and the record stores thousands, so the identity closes at zero
or it does not close, and the footer says so rather than reserving itself
an excuse.

---

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
- **Voter-approved bonds against bond spending.** Refused in
  `docs/V25_MEASURES_FINDING.md`. The sources are individually good —
  CEDA carries the authorised amount for 97% of 2024 school bond
  measures — but no identifier survives from measure to issuance to
  fund. **0 of 273** CEDA district names match a CDIAC issuer name
  exactly; **0.87%** of K-12 issues name a measure at all, in prose;
  and SACS Fund 21 has no measure, issuance or project dimension, so
  the 70.9% of districts carrying two or more authorisations commingle
  them by construction. Closing any link would be our own judgement.
  Standing "no", including for a measure record attached to a district
  page — that still needs the name join, which merges 179 real
  districts.
- **Adoption provenance — who approved a budget, and when.** Refused in
  `docs/V26_ADOPTION_FINDING.md`, on the ground the brief allowed:
  **merely decorative.** Only **1 of 11** layers publishes a figure
  anyone adopted — every other layer is a year-end actual, so a
  "adopted [date]" label there is a category error. On the one layer
  that qualifies, the source carries exactly one adoption field
  (`publicationDate`, a prose string), no adopting-body field, and nine
  years of values spanning **three days**. And there is no single date to
  show: a Budget Act is amended repeatedly and the Legislature cites it
  as a *set* of chapters ("Chapters 12, 38, and 189 of the Statutes of
  2023"). The chapter number **is** obtainable — the Legislature's bulk
  host carries no robots exclusion, contrary to this finding's own first
  draft — so the refusal rests on the field being uninformative, not on
  access. **Still open and separate:** storing `publicationDate` in the
  payload for the change record (V13 cheap improvement #5), which this
  refusal does not touch.
