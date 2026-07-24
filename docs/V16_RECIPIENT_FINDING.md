# V16 finding: who received the money? A second pass at recipient data

_Investigated 2026-07-24. No UI was built; this document is the
deliverable. This is the recipient/payee investigation; the earlier
`docs/V16` file (NCES identifier resolution) is a different note — the
number is deliberately reused because the question is the same shape:
can an identity be published honestly?_

## The question

The Ledger shows what California governments **allocated** — enacted
appropriations, actuals, per-pupil ledgers, audited campus totals. It
does not show **who received** the money: no vendor, no contractor, no
grantee, no payee. V4 tested the one obvious route (FI$Cal vendor
payments) and recommended **don't ship**. This is the full second pass
the V4 finding asked for: every route to recipient/payee/vendor data
across California government, each tested against a live endpoint, each
given a recommendation — **(a)** buildable as a gated layer that
reconciles to a published control, **(b)** buildable as an as-filed
record, honestly labelled, reconciling to nothing, or **(c)** not
buildable, with the specific blocker named so this does not need a
third pass.

The governing rules were fixed before testing and did not bend to make
a layer possible: existence is proven by content-type and content,
never by an HTTP status; a source is a candidate for a **gated** layer
only if it publishes a **control total** to reconcile against — no
target means as-filed at best; no vendor identity is ever fabricated
from a fuzzy match; and any list that would name **private
individuals** receiving public money crosses a privacy line the
corporate-vendor case does not. A subset that is honest beats a whole
that is not.

## The answer, up front

**Nothing at the state level clears the gate.** Across seven routes,
not one publishes recipient names *and* a control total to reconcile
them against. The wall V4 hit is the wall: California discloses what it
plans and what it spends in aggregate, and it discloses payees only in
places that reconcile to nothing. The honest recommendations are:

| # | Source | Recipient names? | Control total? | Recommendation |
|---|---|---|---|---|
| 1 | FI$Cal vendor payments | partial (~12%) | none | **(c)** not buildable |
| 2 | Cal eProcure / state awards | behind WAF | none | **(c)** not buildable |
| 3 | Department disclosure (CDCR/Caltrans/DHCS) | none / un-exportable | none | **(c)** not buildable |
| 4 | State Grants Portal (grants.ca.gov) | **yes** | none (self-reported) | **(b)** as-filed only |
| 5 | Local check registers (SF, LA) | **yes** | each city's own ACFR | **(a)** gated — SF+LA only |
| 6 | USAspending (federal→CA) | **yes**, with UEIs | $447.5B federal | **(b)** as-filed, different government |
| 7 | Identifier resolution (SoS #, UEI) | — | none | **(c)** not buildable |

The one place a reconciled recipient layer is possible is **not the
state at all** — it is the two large cities that run a real published
checkbook (San Francisco and Los Angeles), each reconciling to its own
city report, never summed, individuals suppressed. Everything at the
state level is either not buildable or as-filed. That distribution is
itself the finding.

---

## 1. FI$Cal vendor payments — re-measured, still (c)

V4's centerpiece was re-measured against the same still-latest month
(Vendor_FY25P10 / Spending_FY25P10, uploaded 2026-07-04), both to
confirm V4 and to test a new question it left open: is the vendor-named
data a *clean subset* of some department's spending — such that even if
the whole is only ~12%, a **complete, honest slice** for particular
departments could be gated and shipped?

**The aggregate reproduces V4 exactly.** Vendor-named payments total
**$4,806,857,530** across 315,191 rows (14,872 distinct names); the
same month's full spending file totals **$40,897,014,501** across
3,930,969 rows → **11.75% of recorded spending carries a vendor
name.** 45,209 rows are `CONFIDENTIAL` ($320M); 22,616 (7.2%) are
negative reversals; 15,107 names sit at the ~30-character truncation
cap. The frontier has not moved since V4 — April 2026 is still the
latest published month — so there is no coverage growth to report.

**The new test fails, and fails informatively.** Per-department
vendor-named dollars as a share of that department's spending-file
total do **not** behave like a subset. The ratio ranges from **0.7%**
(Health Care Services) to **over 180%**:

| Department | vendor-named | same-month spending | ratio |
|---|---:|---:|---:|
| Housing & Community Devt | $387.9M | $361.3M | **107%** |
| Resources Recycling & Recovery | $339.2M | $181.3M | **187%** |
| Public Health | $234.6M | $339.0M | 69% |
| General Services | $138.7M | $254.4M | 55% |
| Social Services | $186.1M | $6.20B | 3.0% |
| Health Care Services | $105.8M | $15.1B | 0.7% |

A ratio above 100% is impossible if vendor-named payments were a subset
of the spending file. They are not: the two published files are
**different populations that do not nest** — different transaction
scopes, and department names that do not normalise identically between
the two. (I did not prove the exact mechanism, and do not assert one;
the point survives either way.) The consequence is decisive for a
gated layer: there is **no department for which one can say "here is
all of what it paid, by name."** The whole is ~12%, the parts are
unstable, and neither is a control total. The "honest complete slice"
does not exist.

**A footnote correcting V4's phrasing, in V4's favour.** V4 wrote that
"CDCR, Caltrans, DOJ, DWR, UC are absent entirely." Measuring the
FY25P10 *spending* file (178 departments), several of these appear as
partial slivers — University of California $514.8M, State Water
Resources Control $222.4M, State & Community Corrections $58.2M,
Secretary for Transportation Agency $66.0M — figures that are a small
fraction of each body's true monthly spend. The independently-probed
department route (§3) confirmed that Caltrans's vendor **names** remain
absent from the central vendor file. So "absent entirely" is imprecise:
these bodies are present thinly in the totals but carry no usable payee
detail. That is *worse* for a search product than clean absence — a
thin sliver looks like an answer and is not — which strengthens, not
weakens, V4's conclusion.

**Recommendation: (c) not buildable.** No control total; not a subset;
no stable identifier; frontier stalled. Unchanged from V4, now with the
subset hypothesis tested and closed.

## 2. Cal eProcure / state contract awards — (c)

The State Contract and Procurement Registration System (caleprocure.ca.gov)
is the state's awards universe: contracts and purchase orders over
$5,000.

- **Access, tested:** the live site returns **403 to every non-browser
  client** (a WAF fingerprint gate); a browser user-agent gets HTTP 200
  and a JavaScript single-page-app shell with **no API and no bulk
  export**. Scraping a bot-gated PeopleSoft UI is not a legitimate or
  stable public-record pipeline.
- **The public extract is still dead:** data.ca.gov's SCPRS "Purchase
  Order Data" covers **FY2012-13 through 2014-15 only**, last modified
  **2019-10-23**. It is, notably, *identifier-richer* than the live
  payments data — it carries a numeric Supplier Code plus name and ZIP
  — but those are DGS-internal eSCPRS codes, not a public registry key
  (no UEI, no Secretary-of-State number, no crosswalk), and the file is
  eleven years stale.
- **Reconciliation target: none.** DGS publishes no annual "total
  contract awards / total obligations" figure, statewide or per agency.
  An awards list therefore reconciles to nothing.
- **Basis mismatch:** awards are **commitments** (maximum obligated
  value at signing), not payments and not appropriations; no published
  key bridges an award to any fund, program, or budget line the Ledger
  shows.
- **Privacy:** low — awards are overwhelmingly corporate.

**Recommendation: (c) not buildable.** Two independent fatal blockers:
no reachable current bulk feed, and no reconciliation target. A frozen
FY2012-15 historical carve-out is the only conceivable (b), but it is a
decade stale, reconciles to nothing, and its only identifier is a dead
internal code — not worth shipping.

## 3. Department-level disclosure (CDCR, Caltrans, DHCS) — (c)

Tested whether the departments most worth watching publish their own
payee data, bypassing the central file.

- **CDCR** (cdcr.ca.gov/obs): **zero** payment or contract datasets —
  the page is bidding guidance.
- **DHCS** (data.chhs.ca.gov): **zero** payee-payment datasets among
  its hundreds of health/program datasets; Medi-Cal capitation appears
  only as program tables, never as a payee ledger.
- **Caltrans** (payhist.dot.ca.gov): a per-vendor query tool covering a
  rolling **~18 months**, **excluding major construction contractors**
  (the department's single largest spend category), **un-exportable**
  and **un-totaled**.
- The only cross-department vendor-name aggregation is the central Open
  FI$Cal file of §1 — which carries no Caltrans vendor names and no
  control total.

**Reconciliation target: none at the departmental level.** No sampled
department publishes a payee control total. **Privacy:** live — DHCS's
largest outflows are Medi-Cal payments for individual beneficiaries
(names stripped at source, and any layer must likewise exclude
individuals); Caltrans right-of-way payments can name private property
owners.

**Recommendation: (c) not buildable.** No California department
publishes machine-readable payee data with a reconcilable total. The
one department invisible to the central file (Caltrans) offers only a
rolling, construction-excluded, un-exportable lookup.

## 4. State Grants Portal (grants.ca.gov) — (b), as-filed only

This is the strongest *new* state-level candidate, and the clearest
illustration of why "recipient names exist" is not sufficient. Under
AB 132, state grantmakers report grant **awards** to a central portal.

- **Reachable and real:** grant awards with recipient names and dollar
  amounts, **FY2022-23 forward** (nothing prior). Award counts
  11,698 / 15,208 / 7,613 for FY2022-23 / 23-24 / 24-25; self-summed
  dollars ~$16.9B / $19.7B / $17.9B ≈ **$54.5B over three years**;
  53 distinct agencies in the latest year.
- **Reconciliation target: none.** The ~$54.5B is a **sum of
  self-reported rows, not a control total.** The data is grantmaker
  self-reported with an up-to-one-year lag, and recent years
  **demonstrably undercount** — FY2024-25 shows 7,613 awards against
  FY2023-24's 15,208, because the latest year is still filling in. It
  does not reconcile to the enacted budget: `TotalAwardAmount` is total
  multi-year award value (spanning e.g. 2024-2028, including matching
  funds and bond/federal sources), an award-basis parallel register,
  not a fiscal-year cash figure.
- **Identifiers: none stable for the recipient.** The row key
  (`PortalID`) is unique per row; `GrantID` identifies the
  *solicitation*, not the recipient (320 distinct across 7,613 rows);
  `RecipientName` is free text with visible typos ("Cooper Acadamy",
  "Biship Pauite Tribe"), no UEI, no entity number. Cross-year recipient
  resolution would require exactly the fuzzy matching the ground rules
  forbid.
- **Privacy: a hard line is present.** `RecipientType` "Individual" =
  **780 named private individuals in FY2024-25 alone**, thousands across
  three years, plus 87 tribal governments and many small nonprofits.
  Publishing these as a searchable payment ledger crosses from
  corporate-vendor transparency into exposing individuals' receipt of
  public money.

**Recommendation: (b) as-filed only, and only if built with guards.**
It could ship *only* labelled as "a self-reported AB 132 grant-award
register, FY2022-23 forward, incomplete for recent years, reconciled to
nothing, award-basis not budget-basis," with **named individuals
suppressed or aggregated** and no cross-year recipient identity
claimed. It cannot be gated (no control total) and cannot be
represented as a share of the budget. Worth revisiting as a labelled
companion; not worth pretending it is more.

## 5. Local check registers (SF, LA) — (a), the one gated route

The route V4 did not pursue, and the only one where a **reconciled**
recipient layer proved possible. Eight large jurisdictions were
probed for a queryable payment-level vendor dataset.

- **Only two of eight publish one.** **San Francisco** — DataSF
  "Vendor Payments" (`n9pm-xkyq`), **independently verified here:
  8,079,109 rows**, queryable via API, fiscal years 2007–2027,
  near-100% vendor-named, self-totaling to the city's disbursement
  universe (FY2024 **$15.29B**, FY2025 $16.75B). **Los Angeles** —
  Controller's Checkbook, FY2018-2027, ~6.5M rows, with a **stable
  `vendor_id` on 99.9997% of rows** (a genuine per-vendor anchor within
  LA). The other six (San Diego, San Jose, Long Beach, Oakland,
  Sacramento) expose **no** vendor-payment dataset through an API, and
  no county check register surfaced. Statewide coverage via this route
  is, in practice, **two cities.**
- **Reconciliation target: exists, but city-local.** Each register
  reconciles to **that city's own** ACFR / Controller total
  disbursements — a broader, different universe (all funds, debt,
  internal transfers) than the SCO governmental-activities figure the
  Ledger already ships for that city. Presenting a register as a
  drill-down of the existing city number would be **false** — it
  decomposes a larger, different total. The honest framing is a
  **companion**: "here is this city's own checkbook, reconciled to its
  own report."
- **Identifiers: split, and in-city only.** LA has `vendor_id` (stable
  within LA). SF has no ID but its names are **untruncated** (full legal
  names, 38+ characters — unlike FI$Cal's 30-char cap that V4 rejected).
  Neither crosswalks to the other or to any registry, so **cross-city
  aggregation is impossible** and must never be attempted ("AT&T in LA"
  cannot be proven the same entity as "AT&T in SF").
- **Privacy: real, and handled differently by each city.** LA flags
  2,124 FY2024 rows as `settlement_judgment` — legal settlements, often
  to **named individuals** who sued the city — and does not aggregate
  small one-off payees, so private persons can appear by name. SF
  already handles this: sub-threshold one-off payees are collapsed into
  a "Single Payment Payees" bucket ($297.7M in FY2024). A responsible
  build must **suppress settlements and individual-person payees**,
  publishing only corporate/institutional vendors above a threshold —
  mirroring SF's own discipline.

**Recommendation: (a) buildable as a gated layer — narrowly.** Scope
strictly to **SF + LA**, each as a per-city companion reconciled to and
labelled against **its own** ACFR/Controller total, **never** against
the SCO figure the Ledger shows and **never** summed across cities.
Identifier anchor: LA `vendor_id` (in-city only); SF untruncated
free-text (in-city only, flagged). Privacy gate: drop settlements and
individual payees. This is the honest shape of the only reconciled
recipient data California local government actually publishes. It is
two cities, not a state layer, and must say so.

## 6. USAspending (federal → California) — (b), a different government

Federal award data for recipients in California, tested live at the
USAspending API.

- **Reachable, with a real control:** FY2024 federal dollars to
  California-based recipients total **$447,516,428,654** — a genuine
  published federal control total — and top recipients carry **stable
  UEIs** (9 of the top 10). This is the one route with both names and
  durable identifiers.
- **But it is federal money, not state spending.** Two disqualifiers
  for anything resembling the state layers: (i) **$197.3B (44%) is
  "MULTIPLE RECIPIENTS"** — individuals aggregated for privacy at
  source, so nearly half is nameless by design; (ii) the named half
  **mixes federal pass-through to state agencies** (Health Care
  Services $100.9B = Medicaid, Social Services $21B, Education $7.4B,
  Caltrans $5.5B) **with genuine corporate recipients** (SpaceX $3.8B,
  Lawrence Livermore $3.2B, General Atomics, Health Net). Summing or
  comparing this to any Ledger figure would double-count the
  pass-through and mix two governments' books.

**Recommendation: (b) as-filed, and only as an explicitly *federal*
record.** It is publishable — the data is clean and identified — but
only labelled "federal money flowing to California, on the federal
government's basis," never as a share of the state budget and never
netted against a state figure. It answers a real question, but a
different one from the rest of the Ledger, and the labelling must carry
that weight or it will mislead.

## 7. Identifier resolution (SoS entity #, SAM/UEI) — (c)

The question underneath all the others: even where names exist, can
they be resolved to a **stable identity** so a reader searching one
company sees one company?

- **Stable identifiers do exist** in the authoritative registries — CA
  Secretary of State entity numbers (7-char legacy and 12-char "B"
  format; bulk Master Unload is the full registry for $100) and federal
  UEIs (12-char, via SAM/USAspending). The problem is **not** ID
  stability.
- **The problem is ID *assignment*.** No authoritative source maps a
  FI$Cal (or grant, or register) free-text name to a registry number.
  Each registry performs **fuzzy keyword search** returning candidates,
  or **exact lookup by a number you already hold** — neither performs
  certified name→ID resolution. Converting "SMITH CONSTR" (truncated)
  into an entity number means **choosing among candidates**, a
  probabilistic decision the registry does not certify: the fabricated
  crosswalk the ground rules forbid.
- **Coverage is also partial and non-overlapping.** The SoS registry
  excludes sole proprietors, DBAs, out-of-state unregistered entities,
  and government agencies — all of which appear as payees. SAM/UEI
  covers only federally-registered entities; most state vendors are not
  registered. No single registry covers the payee population, and none
  covers named individuals.

**Recommendation: (c) not buildable.** Identifiers are stable but
**unassignable without fabrication.** This confirms V4's core blocker
and is the reason §1, §2, §3, and §4 cannot be deduplicated into
per-recipient identities even where names are present.

---

## What changes, and what does not

**What V4 got right, now re-tested:** the FI$Cal route is not buildable
— reproduced to the dollar, and the "honest complete slice" escape
hatch is now closed (the vendor file is not a subset of any
department's spending). No stable identifier exists anywhere in the
state's payee data, and none can be assigned without fabrication (§7).

**What the second pass adds:** two routes V4 did not fully weigh change
the recommendation *at the margin*, without moving the state-level
conclusion.

- **Local check registers (§5) are the real opening** — but they are
  two cities, on each city's own basis, reconciled to each city's own
  report, never summed. Honestly framed, this is buildable as a gated
  **companion**, and it is the only reconciled recipient data in the
  whole investigation.
- **The Grants Portal (§4) and USAspending (§6)** are publishable only
  **as-filed and heavily labelled** — self-reported and undercounted in
  the first case, a different government's money in the second — and
  both carry a **hard privacy line** around named individuals that the
  corporate-vendor case does not.

**The state-level answer is unchanged and now well-tested:** no state
source publishes recipient names together with a control total to
reconcile them against. The reconciliation gate — the site's central
discipline — cannot see identity, because California does not publish
identity and a total on the same page. Where it does publish a payee
list (grants, one federal feed, two city checkbooks), the total is
either self-reported, federal, or city-local; where it publishes a
reconcilable state total, there are no names. That gap is not a
rendering problem to be fixed. It is a fact about what the state
discloses, and — like V4 — it is worth stating plainly as one.

## If anything here is ever built

In priority order, and none of it is required:

1. **SF + LA check-register companion** — tier (a), per-city,
   reconciled to each city's own ACFR/Controller total, individuals and
   settlements suppressed, never summed, never presented as a drill-down
   of the SCO figure. The only reconciled recipient data that exists.
2. **AB 132 grant-award register** — tier (b), labelled self-reported /
   incomplete / award-basis, named individuals suppressed, no cross-year
   identity claimed.
3. **Federal-to-California record** — tier (b), labelled explicitly
   federal, never netted against a state figure, "MULTIPLE RECIPIENTS"
   shown as the 44% it is.

Everything else — FI$Cal vendors, state awards, departmental
disclosure, identifier resolution — is **(c) not buildable**, for the
specific blockers named above, so this does not need a third pass.
