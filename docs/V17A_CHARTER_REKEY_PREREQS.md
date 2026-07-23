# V17a — Prerequisites for re-keying charters on (county, school code)

**Status: all three prerequisites established. The re-key is NOT built —
that is the next step, and it is now unblocked.**

Measured 2026-07-22 against the SACS sources, nine years FY2016-17…FY2024-25.

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

## Prerequisite 2 — THE COUNT: **RESOLVED — reconciled to 33**

The pipeline reports **33**. V17 reported **32**. Both were wrong, in
different ways, and both are now explained.

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

**Second, the population difference.**
The pipeline's population is charters with financial rows
(`charter_gl` + `alt_data`), not the whole registry:

| population | count |
|---|---|
| registry collisions (all `Charters` rows) | **40** |
| with financial rows (the pipeline's population) | **33** |

Every one of the pipeline's 33 slugs is inside the 40 — verified: the
set difference *pipeline − registry* is empty.

### The filter, recorded so the number is reproducible

`ReportLevel` and `FundUsed` turned out to be red herrings — they are
read into the registry but do **not** filter the population. The
population is exactly:

```
all_charter_keys = { keys in charter_gl }  ∪  { keys in alt_data }
                   ∩  { keys with a registry entry }

charter_gl  =  UserGL rows where
                 SchoolCode != "0000000"      (a school-level row)
                 AND 1000 <= Object <= 7999   (expenditure objects)
alt_data    =  every Alternate_Form_Data row, keyed on the vintage's
               own school column (ALT_SCHOOL_COL: SchoolID through
               FY2021-22, SchoolCode from FY2022-23)
registry    =  the Charters table, keyed (Ccode, Dcode, <vintage col>),
               carrying CharterName and CharterNumber
```

Reproduced against the nine years: **1,190 charter keys, all 1,190
carrying a registry entry, 33 colliding slugs — exactly the pipeline's
figure.**

My earlier 37 came from including UserGL school-level rows outside the
1000–7999 object range, which are revenue and balance-sheet rows rather
than expenditure. The 40 is the whole registry, including 7 charters
that never file financials in any year and so never reach the payload.

    registry              40 collisions
    minus never-filing     7
    = the payload's       33

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

## What is still NOT established

- Whether `(county, school code)` is unique in the **financial** tables
  as well as the registry. Prerequisite 1 tested `Charters` only. The
  re-key reads the financial tables too, so this must be checked before
  the key is changed.
- Whether any currently-published charter slug changes under the
  re-key, and therefore whether the #22 retired-slug treatment is
  needed. Answerable now that the population is settled, but not yet
  answered.

## Recommendation

**Re-key charters on `(county, school code)`.** The population is
reproducible, the key is unique within every year, and the authorizer
treatment is decided. Two checks remain, both bounded, and both listed
above.

Do not relax the gate.
