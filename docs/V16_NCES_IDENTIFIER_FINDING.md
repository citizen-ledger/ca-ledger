# V16 — The NCES identifier gap blocking the K-12 nine-year window

**Status: investigation only. Nothing built, nothing shipped.**
Measured 2026-07-22 against the sources, on branch `k12-six-years` (PR #61).

The nine-year K-12 window passes every figure gate — all nine years
reconcile to CDE's published Current Expense of Education to the cent —
but the write is refused by the NCES-identifier gate:

```
NCES ID MISSING for 1 district(s) — the address view cannot match them
by identifier; nothing written:
  Lowell Joint (1964766)
```

That gate protects identifier-matched address assignment. It must be
answered, not relaxed. This is the answer.

---

## 1. Is this one district or a class?

**One district, and it is not really missing — it moved.**

The pipeline keys districts on `(Ccode, Dcode)`. Lowell Joint Elementary
appears in SACS under **two different keys** across the window:

| fiscal years | SACS key | county | in CDE directory | NCES |
|---|---|---|---|---|
| FY2016-17 … FY2020-21 | `1964766` | 19 — Los Angeles | **no** | — |
| FY2021-22 … FY2024-25 | `3064766` | 30 — Orange | yes | `0623010` |

Measured directly from each year's `sacs{yy}.mdb` `LEAs` table. The
boundary is **FY2021-22**: that year already files under county 30.

So the extension introduces a *second* key for a district the Ledger
already ships. Today's payload carries it once, as
`lowell-joint-elementary`, CDS `3064766`, NCES `0623010`, county Orange
— fully matched. The extension adds `1964766`, which resolves to
nothing, and the gate fires on that new key.

**A raw scan of all SACS LEAs shows ~58 unmatched rows per year, but
that number is not the population this gate governs.** It counts
charters filing separately, county offices and JPAs, all of which the
pipeline excludes before building `districts`. The gate's own
population — K-12 districts — contains exactly one unmatched key, in
all nine years, and it is this one.

## 2. Why is it missing?

**Not a parse failure, not a merger, not a directory omission.**
Lowell Joint is a *joint* district: it straddles the Los Angeles /
Orange county line, serving Whittier, La Habra and La Habra Heights.
CDE re-assigned its administrative county code from 19 to 30, and the
current public-schools directory carries only the current code.

Checked at the source:

- The directory export has **zero** rows for CDS7 `1964766`.
- It has rows for `3064766` — district row plus schools — all carrying
  NCES `0623010`, status Active.
- Every "Lowell" row in the directory was inspected; the only
  Lowell Joint entity is the county-30 one.

So the identifier did not change: **`0623010` is the district's NCES id
throughout**. What changed is the state's own county-based key. The
crosswalk is built from a **single current-vintage directory export**,
so it can only ever resolve the current key. The older key is
unresolvable *by construction*, not by accident — and this will recur
for any district CDE re-codes.

## 3. What does the address view actually need?

It needs the **NCES id**, and nothing else. `address.html` builds
`ncesToSlug` from each district's `nces` array and matches the Census
GEOID against it — identifier only, never name, never geography.

**The "no identifier-matched record" path already exists** and already
behaves correctly (`resolveSchools`, address.html:498–521):

```js
if (unmatched.length){
  S.schools = [];
  S.schoolNote = "The Census Bureau places this address in … which has
    no identifier-matched record in the Ledger's school data —
    nothing is shown rather than a guess.";
}
```

It shows nothing and says why. This is V7's contract, already built.

**Therefore a district-year with no resolvable key can ship as a record
— searchable, citable, with gated figures — while being correctly
absent from address lookup.** The two capabilities are already
separate in the code.

And in this specific case the address view is **not degraded at all**:
Lowell Joint's NCES id is `0623010` in every year, it is reachable
through the current key, so any address in the district still resolves.
Only the *older SACS key* fails to resolve, and that key is an internal
join artefact, not something a reader ever sees.

## 4. The shape of the fix

A declared per-year identifier-availability table, in the shape of
`APPORTIONMENT_AVAILABLE` and `LCFF_PUBLISHES`:

- The absence is **recorded**, with its reason, not inferred at runtime.
- The gate **honours a declared absence** and refuses an undeclared one
  — the CCC pattern exactly.
- The record says plainly that this district-year cannot be matched by
  identifier, rather than guessing.

**But this case deserves a prior question**, because a declaration
would record something misleading. The two keys are *the same
district*. Publishing them as two records — one matched, one not —
would tell a reader that Lowell Joint appears twice, in two counties,
one of which cannot be found by address. That is worse than the gap.

Two candidate treatments, and they differ in what they claim:

**(a) Declare the identifier absence.** Ship `1964766` as its own
record with identifier-matching declared unavailable. Honest about the
crosswalk, but publishes one district as two, and invites the reader to
compare a five-year series against a three-year one as if they were
different bodies.

**(b) Declare the re-coding.** Record `1964766 → 3064766` as one
district whose state key changed at FY2021-22, so the nine years form
one continuous series carrying NCES `0623010` throughout. This is a
statement about identity, which the repo already makes elsewhere
(`COMMON_ADMIN_NCES`, the district `(name, county)` keying from f22fe79).

**(b) is what the source supports** — the NCES id is constant, the
district is continuous, and only California's administrative code
moved. But it is an identity claim, and identity claims in this
codebase have caused real defects when made casually. It needs its own
verification: that the two keys never co-occur in one year, that the
figures are continuous across the boundary, and that no other district
shares either key.

## Recommendation

**Hold the extension** — but briefly, and not because the gap is
unresolvable.

This is not a case where the data cannot be gated: every figure gate
passes on all nine years. It is a case where shipping now would require
choosing an identity treatment without having verified it, and the
wrong choice publishes one district as two.

The next step is small and bounded: verify treatment (b) — the two keys
never co-occur, the figures are continuous across FY2021-22, no other
district holds either key — and, if it holds, declare the re-coding and
ship all nine years as one continuous record. If it does not hold, fall
back to (a), which is honest and already supported by the address
view's existing refusal path.

**Do not relax the gate.** It caught a real identity question that the
figure gates could not see — the same lesson as *conservation cannot
see classification*, one level up: **reconciliation cannot see
identity.**

## What was measured

| claim | how |
|---|---|
| Lowell Joint absent from directory under `1964766` | full scan of the directory export, 18,385 rows |
| present under `3064766` with NCES `0623010` | same scan; every "Lowell" row inspected |
| SACS key is 19 through FY2020-21, 30 from FY2021-22 | `mdb-export … LEAs` on five vintages |
| exactly one district in the gate's population | the gate's own output on the nine-year run |
| the ~58/year raw figure is a different population | charters/COEs/JPAs excluded before `districts` |
| the address view already refuses unmatched GEOIDs | address.html `resolveSchools`, read in full |
| today's payload ships it matched, three years | `school-data.js` |
