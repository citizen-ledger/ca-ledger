# V19 — Per-vintage Exhibit C parsers: FY2023-24 (P2)

**Status: FY2023-24's parser is built and gated. No payload or page
change** — this PR delivers the per-vintage parser machinery and its
gates only; wiring years into the shipped payload is a separate step.
Measured 2026-07-24 against the archived Exhibit C PDFs.

---

## The machinery

Two declared tables now govern reading any Exhibit C:

**`APPORTIONMENT_AVAILABLE[fy]["declares"]`** — the exact masthead the
document must carry. The identity guard (#59: *the URL is not the year*)
matches that declared string over the **whole first page**, not its first
400 characters.

> **The 400-character window was the defect, not the document.**
> FY2023-24 does declare itself — "2023-24 Second Principal" — but at
> character ~6,700, because the summary table extracts ahead of the
> masthead. The old guard refused a file that identifies itself perfectly
> well. The fix widens the *window*, never the *match*: the string is
> still per-vintage declared and exact, so a file archived under one
> year's path declaring another's is still refused (tested).

**`APPORTIONMENT_FACTS[fy]`** — which facts that vintage's Exhibit C
publishes, declared from measurement against the printed control:

- `True` → the fact must parse for **every** district *and* its district
  sum must tie to Exhibit C's own printed statewide total. Failing either
  stops the build.
- `False` → **not-published**. Never derived, never defaulted to zero, no
  reconciliation run (there is no control), and a stated reason travels
  with it in `APPORTIONMENT_FACT_UNPUBLISHED`.

A vintage with no entry cannot be read at all — adding a year means
declaring what it publishes, deliberately.

`verify_apportionment_vintage(fy)` runs one vintage's parser and its
gates standalone, so a vintage is proven readable before any year is
wired in.

## FY2023-24 (P2) — result

| fact | result |
|---|---|
| funded FTES | **published** — 1,087,711.15 vs printed 1,087,711.16, residual −0.01 |
| state General Fund | **published** — 3,479,573,986 vs printed 3,479,573,986, residual **0** |
| community-supported | **NOT-PUBLISHED** |

### Why community-supported is not published

Exhibit C prints **"7 Fully Community Supported Districts"**, but
**eight** districts on that same document show a property-tax excess. The
document does not say which of the eight is not among the seven — it
refers the reader to a memo it does not contain:

> "See memo for additional information regarding revenue deficit at
> 2023-24 P2" — alongside a **7.9944% revenue deficit of $763,789,279**,
> where FY2022-23 printed a **0.0000%** deficit and its eight-district
> derivation matched its control exactly.

Sierra Joint CCD's excess falls from $12.5M to $2.0M between the two
years and is the marginal case. Two candidate rules were tested and both
refuted: `stateGf == 0` matches neither year (community-supported
districts still receive small allocations), and `ptaxExcess < 0` matches
FY2022-23's control but over-counts FY2023-24's by one.

Rather than publish a derived roster that contradicts the Chancellor's
Office's own printed count, the status is not published for this year.
The declaration is **load-bearing, not decoration**: a test flips it to
published and confirms the gate then fails (8 derived vs 7 printed).

## A source that exists after all — FY2023-24 Table VI

Checked while scoping: the fiscal portal **does** serve a FY2023-24
Table VI (dropdown value 15; the pipeline's declared window merely stops
at 14). It renders 73 districts and passes the whole-dollar gate
**exactly** — district Current Expense sums to $9,454,228,830, equal to
the printed Statewide total, residual 0.

So FY2023-24 is a potentially **complete** year (Current Expense *and*
apportionment), not the apportionment-only year it first appeared to be.
That is recorded here for the wiring step; nothing is wired in this PR.

## The other three vintages, measured

| vintage | round | funded FTES | state GF | community-supported |
|---|---|---|---|---|
| 2020-21 | P1 | parses, reconciles (resid 0.01) | **absent from all 146 pages** | absent |
| 2019-20 | R1 | parses, reconciles (resid 0.06) | **absent from all 146 pages** | absent |
| 2018-19 | P2 | **nothing parses** | absent | absent |

FY2019-20 and FY2020-21 genuinely do not print a State General Fund
Allocation row at those vintages — so that fact stays not-published
rather than derived, which is exactly what the declared fact table is
for. FY2018-19's statewide page sits at index 144 rather than 0 and none
of the later vintages' patterns match any page; whether it can be read
honestly is the open question for its own PR.

## Rounds differ, and that is a comparability fact

P1, P2 and R1 are different stages of the same year's apportionment and
are not interchangeable — FY2022-23 ships from an **R1**, FY2023-24 from
a **P2**. The round is recorded per vintage and carried in the parser's
report. **The page statement is not in this PR** because no fact from a
second vintage ships yet; it lands with the wiring step, on the record
and the series, in the same shape as UC's DOE-assembly break rather than
as a method-note footnote.

## What was measured

| claim | how |
|---|---|
| FY2023-24 declares itself | its masthead string located at char ~6,700 of page 0 |
| both published facts reconcile | district sums vs Exhibit C's own printed statewide totals |
| community-supported cannot be reconciled | 8 property-tax-excess districts vs a printed count of 7; two candidate rules tested and refuted |
| the not-published declaration is load-bearing | flipping it to published fails the gate |
| FY2022-23 moved no figure | flatten/diff old vs new payload: 590 cells, 0 events |
| a FY2023-24 Table VI exists | live portal fetch, 73 districts, whole-dollar gate residual 0 |
