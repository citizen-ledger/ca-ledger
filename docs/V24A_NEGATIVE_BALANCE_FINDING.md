# V24a finding: negative fund balances — the narrow case V24 left open

*Investigated 2026-07-26. Eight fiscal years measured directly,
FY2016-17…FY2023-24. No build.*

## Recommendation, up front

**(c) Don't ship as a layer — no count, no list, no statewide figure.**

**But one narrower thing does survive**, and it is not the bare list the
brief anticipated: a **neutral per-record statement on the entity's own
record**, saying that the entity filed a negative total governmental
fund balance in this year and in how many of the last eight, **with no
dollar figure and no characterisation**.

The reason the list fails and the per-record statement survives is the
same measurement: **45% of these entities are negative in exactly one
year of eight**, and a list presents a one-year event and an eight-year
condition as the same fact. On a record, the year count distinguishes
them; in a list, it cannot.

V24 was right that this is a different object from a reserve — it needs
no restricted split, no denominator, and cannot be misread as available
money. It is not, however, the simple fact it appears to be.

---

## 1. What exactly is negative

**FY2023-24: 95 special districts and one city.** The city is **Isleton**
(Sacramento County), and it is the cleanest case in the whole dataset —
negative in both years available, deepening from **−$416,751** to
**−$752,104**.

Among the 95 districts, the negative sits in different places:

| shape | count |
|---|---|
| unassigned negative, no other class positive | 64 |
| unassigned negative, other classes positive | 18 |
| **negative total without a negative unassigned** | **13** |

And the distinction the brief anticipated is real and large. **122
districts carry a negative unassigned balance; only 82 of them have a
negative total.** The other **40 have a negative unassigned and a
positive total** — a genuinely different fact, and the more common
reading of "the general fund is underwater while restricted money sits
elsewhere."

**Nine districts report a negative *restricted* balance**, which is
conceptually odd on its face — restricted means legally constrained, and
a negative one means spending ran ahead of the restricted resource. Ten
such entities exist in the whole FY2024 universe, so nearly all of them
are in this group.

---

## 2. Is it verifiable?

**Three checks are available. Two pass, and they are the same check
twice. The one that tests anything independent fails disproportionately
on exactly these entities.**

| check | negatives |
|---|---|
| balance-sheet total = operating-statement end-of-year (summed per entity) | **94 / 94** |
| five GASB 54 classes sum to the printed total | **95 / 95** |
| **beginning + net change = end of year** | **66 / 94 (70.2%)** |

The first two are restatements of the same balance-sheet figure — SCO
stating one number twice, which V24 already established is
self-reconciliation. The third is the only one that brings in an
independent quantity, the year's activity, and it **fails for 29.8% of
negative-balance entities against 15.2% of positive-balance ones**.

**Filing quality is measurably worse, by roughly a factor of two, on the
very entities the site would be naming.** No external control exists
(V24 §2.3: a regex over all 170 SCO Socrata view names returns zero
hits).

So this is **as-filed**, and as-filed is *not* sufficient for a fact this
consequential — not because as-filed is a weak tier in general, but
because the specific population fails the source's own internal check at
twice the base rate.

---

## 3. Is it persistent?

**Mostly not.** Across the eight years, 294 entities carry a negative
total at least once:

| negative in… | entities |
|---|---|
| **exactly 1 year** | **132** |
| 2 years | 61 |
| 3 years | 35 |
| 4 years | 23 |
| 5 years | 17 |
| 6 years | 9 |
| 7 years | 6 |
| **all 8 years** | **11** |

**45% of the affected population is negative in exactly one year.** Only
11 entities are negative throughout.

And the single-year cases mostly **cannot be classified**: of the 132,
only **50** sit between two positive years (the reversion signature
consistent with a timing artifact), **7** do not, and **75 are at the
edge of the window** where there is no year on one side to compare. The
window supports the distinction for fewer than half the cases it matters
for.

The steady annual count — 87, 89, 83, 95, 93, 89, 89, 95 — conceals this
completely. It looks like a stable population of ~90 troubled districts.
It is not: it is a largely rotating cast.

---

## 4. What does it actually mean?

**The data does not distinguish fiscal distress from accounting timing,
and it does not distinguish either from a financing vehicle behaving
normally.** Three measurements, none of which the filings resolve:

**Most are too small to be distress.** Median deficit **$81,167**. **51
of 95 are under $100,000**; 88 of 95 under $1M. A district with a
$40,000 negative balance is not a government in trouble; it is a
rounding-scale timing difference on a small book.

**14% are not service governments at all.** 13 of 95 are named as
financing authorities, JPAs or public facilities corporations — City of
San Diego Public Facilities Financing Authority (−$79,238,931, the
largest in the set), La Mesa Public Financing Authority, Oakland Joint
Powers Financing Authority. These are conduit and financing structures
whose balances behave differently by design. #87 already established
that 42.6% of district bonded-debt filers are financing vehicles.

**The largest cases are structurally complex, not simply negative.**
Academic Village Finance Authority reports a **negative restricted
balance of −$60,525,043**. San Francisco County Transportation Authority
holds **+$39,600,584 restricted against −$45,286,284 unassigned** for a
total of −$5,604,120 — an entity with substantial real money whose
unassigned position is deeply negative.

**Nothing in the filing says which is which.** There is no cause field,
no note, no flag. Characterising these 95 as anything — distressed,
deficit-running, at risk — would be the Ledger supplying an
interpretation the source does not contain. Per the brief: determined,
not characterised, and the determination is **ambiguous by construction**.

The genuinely persistent cases are visible and few: Flood Control
Maintenance Area No. 9 and Barstow Fire Protection District are negative
in all eight years. Isleton is negative in both available city years and
deepening. Those are stable facts. They are 12 entities, not 96.

---

## 5. What presentation survives

**A count fails.** "95 special districts carry a negative fund balance"
is true and misleading: 45% are one-year events, 14% are financing
vehicles, and the median is $81,167.

**A list fails for the same reason**, and adds a second problem — a list
is read as a peer group, and these entities have almost nothing in
common beyond the sign of one cell.

**A dollar figure fails, and is the easiest to argue.** It invites
exactly one comparison: against the entity's spending, shown on the same
record. That is the ratio V24 refused, in a smaller font. A −$81,167
balance beside $2.4M of annual spending reads as "3% underwater", a
statistic the site would be producing and could not defend.

**A statewide total is absurd** and worth naming so nobody builds it:
summing deficits across unrelated entities produces a number describing
nothing.

**What survives is a per-record statement**, on the entity's own record,
in the layer's existing as-filed vocabulary:

> This district filed a **negative total governmental fund balance** for
> FY 2023-24, and in **3 of the last 8 years**. The Controller publishes
> no explanation of why a balance is negative, and this site does not
> supply one: a negative balance may reflect a deficit, or spending that
> ran ahead of a reimbursement within the year. The figures on this
> record are as filed and are not reconciled against any published
> control.

Why this survives what the aggregate presentations do not:

- **the year count is the fact that distinguishes** a one-off from a
  condition, and it is in the data — 1-of-8 and 8-of-8 render
  differently and truthfully
- **it makes no claim about causes**, which the data cannot support
- **it carries no dollar figure**, so it invites no ratio
- **it appears only where a reader is already looking at that entity**,
  so it never becomes a league table
- it inherits the layer's existing unreconciled tier, which is honest
  about §2

**This is thin, and it should be.** It says: *this entity filed a
negative balance, this often, and we cannot tell you why.*

---

## 6. What I did not do

- I did not examine counties; the FY2024 county file has **zero**
  negative totals, so there was nothing to examine.
- I did not test K-12 for negative fund balances. SACS carries the same
  vocabulary and the question is the same shape; it is a genuine gap and
  the finding does not cover that layer.
- I did not attempt to read any entity's ACFR to establish a cause for a
  specific deficit. That would answer §4 for one entity at a time and is
  not scalable to 95, but it is the only route that would.
- The single-year reversion test in §3 cannot classify 75 of 132 cases
  because the window has no year on one side. A longer window — the SCO
  workbooks reach back to FY2002-03 — would shrink that.

## Recommendation

**Don't ship a negative-balance layer.** Ship, if anything, a per-record
statement with the eight-year count and no dollar figure.

The honest one-line summary: **the sign of the number is reliable, the
meaning of the sign is not, and the only thing in the data that
distinguishes a bad year from a bad decade is the count of years — so
that count, and nothing else, is what may be shown.**
