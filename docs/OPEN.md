# Open questions and recurring patterns

Things a maintainer will meet again. Each entry names the shape, so the
next instance is recognised rather than re-diagnosed from scratch.

---

## The crosswalk is current-vintage, so re-coded districts recur

**Shape.** A district arrives in an older year with no NCES id, and the
build refuses with `NCES ID MISSING`. It looks like missing data. It is
usually a **re-coding**: California's `(Ccode, Dcode)` key is
administrative and can move, while the federal NCES id does not.

**Why it will keep happening.** `nces_ids` is built from a *single
current-vintage* export of CDE's public directory
(`pubschls.txt`). That export carries only each district's **current**
key. Any earlier key is therefore unresolvable **by construction** —
not by accident, and not fixable by re-downloading. Every future
re-coding will present exactly like Lowell Joint did.

**How to tell a re-coding from a genuine gap.** Four checks, all
measurable from the sources already on disk
(`docs/V16_NCES_IDENTIFIER_FINDING.md` records the method):

1. **The two keys never co-occur.** One row per year, never both. If
   they co-occur, it is not a re-coding — stop.
2. **No step change at the boundary**, judged *against peers* rather
   than in isolation. Lowell Joint moved +14.7% across FY2020-21 →
   FY2021-22, which reads alarming alone but is the 70th percentile of
   973 districts in a year whose median was +10.9% (first full year of
   federal COVID relief). A large jump in a year when everyone jumped
   is not evidence of a different body.
3. **No other district holds either key** in any loaded year, and the
   name and type are stable across the boundary.
4. **The directory shows one continuous Active entity** for that NCES
   id — one district-level row, no `ClosedDate`. A closure and a new
   opening is a different event and must not be declared a re-coding.

**How to declare it.** `RECODED_DISTRICTS` in
`pipeline/fetch_school_data.py`, in the same shape as
`APPORTIONMENT_AVAILABLE` and `LCFF_PUBLISHES`: declared, never
inferred at runtime. `assert_recodings()` requires **both** keys to
actually occur in the loaded years, so an entry cannot rot into a stale
exemption once the window no longer reaches the older key.

**Do not relax the gate.** It exists so the address view cannot
mis-match a district by identifier, and it caught an identity question
the figure gates structurally cannot see — every figure gate passed on
all nine years while this was wrong. *Reconciliation cannot see
identity*, the same way *conservation cannot see classification*.

---

## Charter slug collisions in the extended K-12 window

**Status: open, blocking the nine-year K-12 extension.**

With the NCES re-coding declared, the K-12 build proceeds through every
figure gate on all nine years and then refuses at a different identity
gate:

```
SLUG COLLISION in charters after qualification: 33 records
— the qualifier does not disambiguate these records.
Nothing written; a human must choose a stable identifier.
```

Thirty-three charter records collide after the existing qualifier is
applied. This is the same *class* as the re-coding — identity across a
longer window — but a different mechanism, and it has not been
investigated. It needs its own finding before the extension can ship:
whether these are genuinely distinct schools sharing a name, the same
school recurring under changed identifiers, or records that should
never have been separate.

The gate is behaving correctly. It should not be relaxed either.
