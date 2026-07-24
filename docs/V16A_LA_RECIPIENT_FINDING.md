# V16a finding: the Los Angeles checkbook — can a recipient layer be built?

_Investigated 2026-07-24. No UI was built; this document is the
deliverable. Follows [V16](V16_RECIPIENT_FINDING.md), which found that
Los Angeles is the best local check register in California — a
queryable, near-100%-named payment ledger — and asked whether an
LA-only recipient layer could be built honestly._

## Recommendation, up front

**(c) Don't build a recipient index.** Not because the data is thin —
it is the richest local payment record in the state — but because the
one thing a recipient layer must do, and this one cannot, is keep the
names of private individuals out of a permanent public search. The LA
checkbook contains natural-person payees — legal-settlement recipients,
claimants, refund and relocation payees, individual landlords, sole
proprietors — and **the dataset carries no field that reliably
separates a person from an organization.** Three independent
suppression strategies were tested adversarially against the live data;
all three converged on the same verdict: individuals can be handled
only by dropping below the name level entirely. Every name-level
configuration that was actually measured still publishes some
individuals — a measured floor in the hundreds, an honest estimate in
the hundreds-to-thousands. The governing rule set for this
investigation was explicit: _a design that occasionally publishes a
settlement recipient's name is a failure._ This one would.

A name-suppressed **aggregate** view (category and fund totals, with
individual categories shown as withheld-name sums) is privacy-safe and
could be built. But it reconciles to no published control, it is not a
_recipient_ layer — it answers "how much, by category," which the
site's existing city layer already answers — and it is not what the
question asked. It is noted in §5 and set aside.

What follows is the evidence, because the recommendation rests on it and
because "LA publishes a clean checkbook, why not mirror it?" is a
reasonable question that deserves a measured answer rather than a
reflex.

## What LA actually publishes

The dataset is **Checkbook L.A. Data** (Socrata `pggv-e4fn` on
`controllerdata.lacity.org`), the payment record behind the City
Controller's public "Checkbook LA" tool. Measured against the live
endpoint on 2026-07-24:

- **6,384,402 rows**, complete for **FY2018 through FY2026** (FY2027
  just beginning; six stray pre-2018 rows). Fresh — the latest
  `transaction_date` is 2026-07-09, two weeks before this investigation.
- **Auto-fetchable** — the full Socrata SoQL/JSON API answers
  aggregate and facet queries directly; a scheduled re-pull is viable.
  (The reconciliation control, by contrast, is a manual PDF; see §1.)
- **Near-100% vendor-named**, with a genuine identifier: `vendor_id` is
  present on all but 2 rows, **30,454 distinct**, and **28,461 of those
  carry exactly one name** — a clean per-payee anchor that consolidates
  spelling variants without any fuzzy matching. (One pathological
  "sundry" id, `07SJ59`, pools 6,792 one-time-payee names; 1,992 other
  ids carry a handful each. Identity is anchored on `vendor_id` as LA
  assigns it — names are never merged across ids, per the V16 rule that
  "ABC Inc" and "ABC Incorporated" stay separate unless an authority
  says otherwise.)

This is, unambiguously, the best local checkbook in California. The
access problem that killed the state vendor route in V4 does not exist
here. The blocker is entirely privacy, and it is not a soft one.

## 1. Reconciliation — as-filed, never gated

**There is no published control total the checkbook reconciles to.**
The dataset's own metadata describes it only as "City spending data …
used to power the Controller's Checkbook L.A application. Data since
fiscal year 2018" — no control figure, no methodology, no
reconciliation statement. No LA document — ACFR, PAFR, adopted budget,
or Controller page — states a figure defined to equal the checkbook's
sum. Two structural reasons, each sufficient on its own:

- **Basis.** The checkbook is **cash disbursement**, keyed to payment
  date and net of cancellations (`CANCELLATION` −$344M, `ADJUSTMENT`
  −$38M over the window). LA's ACFR is GAAP — full accrual
  (government-wide) and modified accrual (funds) — carrying
  depreciation, pension/OPEB accruals, and revenue-timing entries a
  cash checkbook can never contain.
- **Entity scope.** The checkbook is a bespoke consolidation of **four
  feeder systems** — FMS (city core) $63.76B, LADWP $30.28B, LAWA-SAP
  (airports) $8.16B, HARBOR-ERP (port) $2.0B — so it spans governmental
  funds, three proprietary enterprises, **and** fiduciary funds
  (Pension Trust $14.1B, Agency $5.8B). No single ACFR statement covers
  that union: the government-wide statement excludes fiduciary activity,
  the governmental-funds statement excludes all six enterprises, and the
  proprietary statements report accrual operating expense, not cash.

For the record, the checkbook's own cash sums (measured):
FY2018 $10.723B · FY2019 $10.863B · FY2020 $10.919B · FY2021 $11.134B ·
FY2022 $9.934B · FY2023 $11.987B · FY2024 $11.283B · FY2025 $13.224B ·
FY2026 $13.993B (partial). Against the one governmental control that
does exist (ACFR/SCO governmental-funds expenditures), the checkbook's
governmental slice runs about **half** — FY2024 checkbook-governmental
$5.998B vs ACFR governmental $12.022B — because the checkbook is vendor
disbursements, excluding salaries, benefits, debt principal, and
inter-fund transfers.

So even the **dollars** here would ship as-filed and labelled, never
gated to a control total. That alone would not stop a build — the
special-districts layer already ships as-filed. The privacy finding is
what stops it.

## 2. What it honestly is, and how it relates to the LA figure already shown

The site already publishes an LA number in its city layer: the CA State
Controller's "By the Numbers" governmental-activities expenditure. That
figure **equals the ACFR governmental-funds total expenditures to the
dollar** — verified across four years (FY2022-23 $9,939.996M = ACFR
$9,939,996K; FY2023-24 $12,021.531M ≈ ACFR $12,021,529K). It is an
accrual, governmental-only, all-vendors-and-payroll expenditure total.

The checkbook is a different thing that happens to land near the same
magnitude, which is exactly the trap. Decomposing the checkbook's
$104.2B over the window by fund type:

- **Governmental** (general + special revenue + capital + debt) =
  **$40.33B, 38.7%** of the checkbook.
- **Non-governmental** = **61.3%** — enterprise (DWP/airport/harbor)
  42.2%, pension trust 13.5%, agency 5.6% — a universe the site's
  governmental figure never touches at all.

And even the 38.7% governmental slice is not the site's number: it is
cash vendor payments (~half the accrual total, as above), not the full
governmental expenditure. So the checkbook's $11.3B (FY2024) and the
site's $12.0B look like the same quantity and are not: most of the
checkbook is outside the site's universe, and the part inside it
measures something narrower. Presenting the checkbook as a drill-down of
the site's LA figure would be **false**, and the "does not add"
statement would have to say precisely this — a different basis, a
different and larger universe, overlapping by roughly a third and equal
nowhere.

## 3. The privacy design — the decisive question

**There is no person/organization type field** anywhere in the 61
columns. Whether a payee is a human being must therefore be _inferred_,
and the question is whether it can be inferred reliably enough to
guarantee no individual is ever published. It cannot. The evidence, all
measured against the live data:

**LA's own privacy mask exists — and has a hole exactly where the harm
is greatest.** The Controller already replaces some payees with a
`PRIVACY-<DEPARTMENT>` token: **472,993 rows / $630.8M** across ~40
departments, name and id both masked. But **legal settlements escape
it** — of 18,526 rows flagged `SETTLEMENT/JUDGMENT` ($1.629B), only 622
fall under a PRIVACY token. The other ~17,900 carry **real payee names,
9,370 distinct, unredacted** (a redaction-token scan matched ≈0). The
one category with the clearest expectation of privacy — people who sued
the city and settled — is published today by name.

**The settlement flag itself leaks.** 1,059 rows / $17.0M sit in
settlement- and judgment-named accounts without the flag set; another
64 name settlements only in the free-text description. A suppressor
built on the flag alone misses them.

**The individual surface is far larger than settlements** — refunds
(5,821 rows), reimbursements (8,349), relocation (1,249), right-of-way
property acquisition (99), claims and litigation, aid and assistance
($553M / $417M), stipends — plus categories that _mix_ individuals and
organizations and cannot be dropped wholesale without gutting the data:
rent (28,098 rows), medical (33,240), benefits ($2.27B).

**Three suppression strategies, tested adversarially, unanimous
verdict.** Each was asked to construct the strongest scheme it could and
then to prove zero individuals published:

- **Category / account suppression** — drop the settlement flag *and*
  its leaks *and* every individual-prone account, suppress at the name
  level (withhold a name if _any_ of its rows is dropped), withhold the
  whole sundry id. Residual: after even an org-suffix exclusion, **431
  distinct "LASTNAME, FIRSTNAME"-shaped names survive in ordinary
  accounts, across 18,982 rows / $1.45B** — and that comma heuristic
  misses every person written "FIRST LAST." Irreducible class: sole
  proprietors in generic service accounts, indistinguishable by any
  field from a firm.
- **Name-pattern classifier** (whitelist inversion — publish only
  positively org-styled names, withhold the rest). Residual: natural
  persons operating under org-token DBAs ("SMITH ENTERPRISES"),
  eponymous firms indistinguishable from two-token personal names,
  family trusts. On the settlement set specifically, **67% of names are
  ambiguous** — neither a personal comma-form nor a corporate suffix —
  so the classifier cannot see them.
- **Registry whitelist** (publish only names matched to a CA Secretary
  of State entity number or SAM/UEI as a corporate form). Residual,
  measured on the live names: **185 "LAW OFFICES OF <person>", 257
  "<person> M.D./D.D.S./& ASSOCIATES", 207 "<person> DBA <business>"** —
  person-named registered entities that pass the whitelist and publish a
  person's name. And, per [V16 §7](V16_RECIPIENT_FINDING.md), no
  authoritative source resolves a free-text name to an entity number;
  doing it by fuzzy match is the fabricated crosswalk the rules forbid.
  (This scheme was reasoned and floor-measured by name pattern; a live
  SoS/SAM match was **not** executed — see §6.)

The strongest mechanism that can be specified — the fail-closed union of
all of the above: honor `PRIVACY-*`; drop `settlement_judgment` plus
settlement/judgment/claim/litigation accounts plus
description-settlements; drop every individual-prone category; suppress
by name not by row; withhold the entire sundry id; and then publish only
names bearing a positive organizational token — is **provably fail-safe
on the row and not fail-safe on the person.** An unclassifiable payee
defaults to withheld, which is correct. But a sole proprietor in a
generic "professional services" account is never _unclassifiable_ to the
scheme — it looks exactly like an eligible organization — so it is
published, not withheld. Fail-safe protects only against the categories
the scheme can see; it cannot protect against a person the dataset gives
it no field to detect.

The only configuration that reaches provable zero is to **withhold all
payee names and publish aggregates.** Every reviewer reached that point
independently. That is not a name-level recipient index; it is §5.

## 4. "But the names are already public" — why (c) still holds

This is the strongest objection to (c), and it is true: every name is
already published, by name, on the Controller's own Checkbook LA site, a
public record under the California Public Records Act. If the city
already puts it online, why should the Ledger decline to mirror it?

Three reasons, and the finding rests on them rather than waving the
objection away:

1. **Aggregation, searchability, permanence.** A settlement recipient's
   name sitting in a 6.4-million-row municipal dataset behind a query
   tool is, in the practical-obscurity sense long recognized in
   public-records law, differently exposed than the same name lifted
   into a permanent, deliberately durable, cross-government archive built
   to be searched and cited and to outlive its sources. The Ledger's own
   stated premise is that "a record that is only files has less to
   lose" — permanence is the point, and permanence is precisely what
   raises the stakes for a named individual.
2. **The Ledger sets its bar above the technical minimum.** It already
   declined to build exactly this kind of feature once —
   [V4](V4_VENDOR_FINDING.md) refused a state vendor search that was
   technically assemblable — on the reasoning that for a name-search
   product "the governing rule is that names attract mobs." "It is
   technically public" has never been this project's standard for what
   it will publish; "we can stand behind every figure and every
   consequence of publishing it" is.
3. **Republication is the Ledger's own act.** Mirroring a settlement
   payee's name into this archive is a fresh disclosure the project
   would own, not the city's. The rule set for this investigation —
   publishing a settlement recipient's name is a failure — is a rule
   about what _this_ record does, and the measured floor of leaked
   individuals is greater than zero at every name-level configuration.

None of this argues the city is wrong to publish its checkbook. It
argues that the Ledger, given its purpose and its standard, should not
be the one to turn that checkbook into a permanent searchable index of
who the city paid — because it cannot do so without carrying some
individuals along, and it has said it will not.

## 5. The narrow safe alternative, and why it isn't the ask

Names withheld, the same data supports an honest **aggregate** view:
department × fund × category × year dollar totals, with the
individual-prone categories shown as withheld-name sums — _"legal
settlements: $1.629B across 18,526 payments, FY2018–FY2026, names
withheld."_ That is privacy-safe (it never publishes a payee) and it is
the shape the user's brief offered as an option.

It is not recommended as a build, for three reasons. It **reconciles to
no control** (§1), so it ships as-filed. It is **not a recipient
layer** — it answers "how much did LA spend, by category," which the
site's city layer already answers on a firmer (reconciled, accrual)
basis, so it largely duplicates existing coverage at a lower tier. And
the early years carry a **fund-classification thinness** (governmental
sums tagged at only ~$2.0–2.4B in FY2018–FY2020 vs ~$4.8–6.1B from
FY2021, a tagging gap not a real change) that would need diagnosis
before any per-fund figure shipped. A safe aggregate is buildable; it
just isn't the thing "who received the money" asked for, and it isn't
worth a distinct layer.

## 6. What I did not do, and the limits of the evidence

In the spirit of the rest of the record:

- **No live registry match was executed.** The registry-whitelist
  residual (§3) is a floor measured by name pattern, combined with
  V16 §7's established finding that name→ID resolution requires
  fabrication — not a run against the CA SoS or SAM.gov APIs. A live
  match would refine the leaked-individual count; it would not change the
  verdict, because the measured floor of person-named registered
  entities is already greater than zero.
- **The exact number of natural persons in the data is unmeasurable
  from the dataset** — which is itself the finding. There is no field to
  count them; the residual is a measured floor (hundreds) plus an honest
  order estimate (hundreds to low thousands of distinct names). A finding
  that the count is unknowable is a stronger reason for (c) than any
  specific number would be.
- **The FY2024 primary ACFR PDF returned 403** to automated fetch;
  governmental control totals were taken from the FY2025 ACFR's ten-year
  statistical table and the FY2023 primary statement (both retrieved,
  content-verified). Immaterial to the recommendation, which does not
  gate on these figures.
- **I did not compute the size of the surviving safe-name index**,
  because provable zero fails regardless of its size — a large index
  that still leaks 185 person-named entities is no safer than a small
  one.

## Recommendation

**(c) Don't build a recipient index for the Los Angeles checkbook.**
The reconciliation would be as-filed (no published control); the basis
and overlap are statable and honest; the identifier anchor is real. The
blocker is singular and decisive: the data cannot reliably separate
individuals from organizations, the strongest specifiable suppression
mechanism — settlement flag ∪ settlement/claim/litigation accounts ∪
description-settlements ∪ individual-prone categories ∪ existing
`PRIVACY-*` mask ∪ name-level (not row-level) suppression ∪
whole-sundry-id withholding ∪ organizational-token whitelist, everything
fail-closed — was specified and shown to still publish a measured floor
of individual names, and the rule that a design which occasionally names
a settlement recipient is a failure is not one to soften to make a layer
possible.

Reopeners are concrete: if LA's Controller adds a payee person/organization
flag, or extends its `PRIVACY-*` mask to cover settlements and the other
individual categories at source, the separability problem is solved by
the publisher and this becomes a genuine (b) as-filed recipient layer —
the best in the state. Until then, the honest answer is not to build it.
