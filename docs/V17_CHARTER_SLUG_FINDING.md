# V17 — The charter slug collisions blocking the K-12 nine-year window

**Status: investigation only. Nothing built, nothing shipped.**

> **CORRECTION (V17a).** This finding's count of **32 is wrong.** The
> enumeration read a column named `CharterNum`; the `Charters` table has
> `CharterNumber` and `SchoolID`, so the qualifier fell back silently and
> under-counted. Read correctly the registry has **40** colliding slugs,
> of which the pipeline gates a financial subset it reports as 33.
> The CATEGORISATION below stands — every collision is one charter under
> two authorizer keys — but the numbers do not. See
> `docs/V17A_CHARTER_REKEY_PREREQS.md`.
Measured 2026-07-22 against the SACS sources, on branch `lowell-recoding`.

With the NCES re-coding declared (#63), the nine-year K-12 build passes
every figure gate and then refuses at a further identity gate:

```
SLUG COLLISION in charters after qualification: 33 records
— the qualifier does not disambiguate these records.
Nothing written; a human must choose a stable identifier.
```

This is the same *class* as Lowell Joint — reconciliation cannot see
identity — but a different mechanism, and the treatment is different.

---

## 1. What are they? One category, not four

**All of them are the same shape: one charter under two authorizer
keys.** Enumerated from each year's `Charters` table across the nine
years:

| shape | count |
|---|---|
| same county **and same school code**, different `Dcode` | **32** |
| two distinct charters sharing a name | 0 |
| a name reused after closure | 0 |
| anything else | 0 |

The county and the CDS **school code** are identical on both sides of
every collision. Only the `Dcode` — the authorizing body — differs.

Two sub-shapes, by what the `Dcode` changes *to*:

| transition | count | meaning |
|---|---|---|
| `6xxxx`/`7xxxx` → `1xxxx` | **22** | district-authorized → a direct-funded charter block |
| `6xxxx`/`7xxxx` → `6xxxx`/`7xxxx` | **10** | one district authorizer to another |

Examples, with the year each key is in force:

```
almond-acres-charter-academy      68825  FY2016-17..FY2020-21
                                  10405  FY2021-22..FY2024-25
alternatives-in-action            61119  FY2016-17..FY2020-21
                                  10017  FY2021-22..FY2024-25
anahuacalmecac-international…     76885  FY2016-17..FY2018-19
                                  64733  FY2019-20..FY2024-25
```

**The #63 co-occurrence test passes for all 32**: the two keys are never
present in the same year. Every one is a clean handoff.

*(Count discrepancy, stated rather than smoothed: the pipeline reports
**33**, this enumeration finds **32**. The pipeline's population is
charters with financial rows in `charter_gl`/`alt_data`; mine is the
`Charters` registry. The extra record is inside that difference and
should be identified before any fix is written — it may be a 33rd of
the same shape, or the one case that is not.)*

## 2. Is the slug derivation the problem? Yes, and it is the root

Districts were fixed in #22 to key on **CDS**, the source's own stable
identity, with every holder of a shared name qualified. **Charters did
not get that treatment.** They key on `(name, charter number)`, and the
pipeline's own comment says the number is not unique:

> the charter number is NOT unique on its own (0756 is shared by the
> nine High Tech schools), so it qualifies a shared NAME, never
> identifies a charter

So the qualifier cannot disambiguate here — **and it should not.** The
two records are not two entities that need telling apart; they are one
entity that the key splits in two. `assign_slugs` is behaving exactly
as designed: it refuses because *no* qualifier can separate them.

The charter's stable identity is already in the data: **(county, school
code)** is invariant across every one of the 32 transitions. The
`Dcode` is the authorizer, which is an *attribute* of the charter in a
given year, not part of its identity — the same error as keying a
district on a county code that can move.

## 3. Live today, or extension-only?

**Extension-only. Zero of the 32 exist within the shipped three years.**

Every collision needs a year before FY2022-23 to appear. The current
payload is unaffected, and this is not a live defect.

## 4. Treatment — and why it is *not* 32 declarations

The obvious move, following #63, is to declare 32 re-codings. **I do not
recommend it**, for two reasons.

**The continuity test does not uniformly pass.** Applying #63's method
across the FY2020-21 → FY2021-22 boundary, against 558 peer charters
present both years under one key (median +12.0%, 10th/90th −3.2% /
+35.1%):

| charter | change | verdict |
|---|---|---|
| Alternatives in Action | +10.6% | inside the peer band |
| Audeo Charter II | −6.4% | **outside**, on the low side |
| Almond Acres | — | not in the Alternative Form both years |

One clean, one marginal, one untestable by that route. Declaring all 32
would assert continuity that has been demonstrated for one of them.

**And 32 hand-written declarations is a large stale-exemption surface.**
`RECODED_DISTRICTS` carries one entry, guarded by `assert_recodings()`.
Thirty-two entries, each needing both keys to remain in the window,
becomes a maintenance liability that will silently rot as the window
moves.

**The honest treatment is to fix the derivation, not to enumerate the
symptoms.** Key charter identity on `(county, school code)` — the pair
that is invariant across all 32 transitions and is the source's own
stable identifier — with the authorizer carried as a per-year attribute.
That dissolves all 32 collisions structurally, exactly as #22 dissolved
the district-name collisions, rather than declaring them one at a time.

It is the same conclusion #22 reached for districts, applied to the
layer that did not get it: **identity comes from the source's stable
code, never from a name plus a qualifier that the source does not
guarantee.**

## Recommendation

**Re-key charters on `(county, school code)`; do not declare 32
re-codings, and do not relax the gate.**

Before building, three things must be established — this finding does
not establish them:

1. **Is `(county, school code)` unique across all nine years?** It must
   be verified as an identifier, not assumed because it happens to be
   stable across these 32.
2. **Resolve the 33rd record.** The pipeline counts 33 and this
   enumeration finds 32; the difference sits between the registry and
   the financial tables and may be a different shape.
3. **The authorizer becomes a per-year attribute.** A charter that
   changes authorizer has a real, publishable fact attached to that
   change, and the page should be able to say so — it is a
   comparability note, not a detail to drop.

The gate is doing its job. It refused rather than handing one of two
records an identifier describing both, and it surfaced a derivation
defect that the figure gates cannot see.

## What was measured

| claim | how |
|---|---|
| all 32 are same-county, same-school-code, different `Dcode` | full enumeration of `Charters` across nine `sacs{yy}.mdb` |
| the keys never co-occur | per-year presence test, all 32 |
| 22 move to a `1xxxx` direct-funded block, 10 district-to-district | `Dcode` prefix classification |
| zero exist in the shipped three years | presence test restricted to FY2022-23..FY2024-25 |
| charters key on `(name, number)`, districts on CDS | `assign_slugs` call sites, and the pipeline's own comment |
| continuity is not uniform | Alternative Form totals vs 558 peers at the FY2021-22 boundary |
