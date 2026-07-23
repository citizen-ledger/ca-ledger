# V17a — Prerequisites for re-keying charters on (county, school code)

**Status: prerequisites 1 and 3 established; prerequisite 2 NOT resolved.
No implementation. The re-key is not built.**

Measured 2026-07-22 against the SACS sources, nine years FY2016-17…FY2024-25.

The instruction was explicit: *do not proceed until the counts agree or
the difference is explained and declared*. They do not yet agree. This
records what is established, what is not, and a correction to V17.

---

## Prerequisite 1 — UNIQUENESS: **established**

**`(county, school code)` never identifies two records in the same year.**

| test | result |
|---|---|
| distinct `(county, school code)` pairs, nine years | 1,561 |
| pairs mapping to **2+ rows within a single year** | **0** |
| pairs with an empty or all-zero school code | 0 |

Zero within-year multiplicities is the decisive property: within any
year the pair is a unique identifier, which is what a key must be.

**180 pairs carry more than one name across the nine years.** That is
renaming, not a uniqueness failure — but it had to be distinguished from
*code reuse after closure*, which would be a genuine violation:

- 42 of the 180 have names too dissimilar to be spelling drift
  (`LA's Promise Charter High #1` → `Russell Westbrook Why Not? High`;
  `Inspire Charter School – South` → `Cabrillo Point Academy`).
- **All 42 are present in a continuous run of years — zero have a gap.**
  A reused code requires the first school to stop and a later one to
  start, which shows as a gap. There are none.

So the 180 are renames, the key holds, and a charter's name is
demonstrably *not* part of its identity — which is the same conclusion
#22 reached for districts.

## Prerequisite 2 — THE COUNT: **not resolved, narrowed**

The pipeline reports **33** collisions. V17 reported **32**. Both are
wrong in different ways, and the residual is not yet explained.

**First, a correction to V17.** Its enumeration read a column named
`CharterNum`. The `Charters` table's real columns are:

```
Ccode, Dcode, SchoolID, CharterNumber, CharterName,
ReportType, ReportLevel, FundUsed, K12ADA
```

There is no `CharterNum` and no `SchoolCode` — so V17's qualifier fell
back silently to the school code, producing differently-shaped slugs and
a **wrong count of 32**. Read correctly, the registry has **40**
colliding slugs. V17's *categorisation* stands — every collision is one
charter under two authorizer keys — but its count does not, and this is
the third time in this sequence that reading a column by an assumed name
has produced a confident wrong number.

**Second, the population difference is real but incompletely modelled.**
The pipeline's population is charters with financial rows
(`charter_gl` + `alt_data`), not the whole registry:

| population | count |
|---|---|
| registry collisions (all `Charters` rows) | **40** |
| with financial rows, by my reconstruction | **37** |
| the pipeline's own figure | **33** |

Direction established: the pipeline's set is a subset of the registry's,
and every one of its 33 slugs is inside the 40 (verified: the set
difference *pipeline − registry* is empty).

**The residual four are not explained.** They lie in how `charter_gl`
is actually built — `ReportLevel` distinguishes charters that file
separately (`CharterSchool`, `StateBoardOfEducation`) from those
reporting inside an authorizer (`SchoolDistrict`,
`CountyOfficeOfEducation`), and `FundUsed` distinguishes commingled
Fund 01 from Fund 09/62. My reconstruction did not apply those filters.

**This must be closed before the re-key is written**, because the fix's
correctness is judged by "the collisions are gone", and a count that
cannot be reproduced cannot tell a dissolved collision from one that
moved out of the population being counted.

## Prerequisite 3 — THE AUTHORIZER CHANGE: **both, and it is a note**

A charter moving from a district authorizer to a direct-funded block
changes **who oversees it and how its money reaches it**. It is a
comparability fact of the same kind as the city contract-service note
and the county unincorporated share.

The recommendation is **both**, because they answer different questions:

1. **Per-year attribute on the record.** The authorizer belongs in
   `years[fy]`, beside the figures it governs — it is a property of the
   charter *in that year*, exactly as the re-key establishes. A reader
   looking at one year should see who authorised it that year.

2. **A note on the series where it changes.** A reader comparing across
   the boundary is comparing a period of district oversight against a
   period of direct funding. The existing note machinery already carries
   this class of statement, and the change is derivable — no declaration
   needed, because after the re-key the pipeline can see both sides.

Silently smoothing the change would produce exactly the defect the gate
prevented: a continuous-looking series across a real discontinuity.

The note should say what changed and between which years, and must not
characterise it — 22 of the 40 move to direct funding, which is a
routine consequence of California charter law, not an event.

## What is NOT established

- The residual 4 records between my 37 and the pipeline's 33.
- Whether `(county, school code)` is unique in the **financial** tables
  as well as the registry — tested on `Charters` only.
- Whether any currently-published charter slug changes under the re-key,
  and therefore whether the #22 retired-slug treatment is needed. This
  cannot be answered until the population is settled.

## Recommendation

**Close prerequisite 2 first, then re-key.** The remaining work is
bounded: reproduce `charter_gl` exactly as `process_year` builds it,
reconcile to 33, and record the filter in the finding so the number is
reproducible by the next reader.

Do not relax the gate, and do not write the re-key against an
unreproducible count.
