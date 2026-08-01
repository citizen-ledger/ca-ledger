# V26 — Peer-group comparison: investigated, not built

*Investigated 2026-07-31. Measured against the shipped payloads and against the
State Controller's live catalogue. **Recommendation: (c) don't build it.***

---

## The question

A per-resident figure means little without knowing whether it is typical. A
reader sees **$103 per resident** for Lakewood police and has nothing to
compare it against.

The decisive question is not whether readers would find a peer group useful.
They would. It is whether a defensible peer definition can be **derived from
data**, or whether grouping requires the Ledger's own judgement about which
governments belong beside each other. Every other refusal on this site rests
on *we don't decide*.

The answer is not the one this investigation expected, and it is not the
simple one. **A current, source-published, far richer service classification
does exist** — the brief's premise that the checklist stops at FY2015-16 is
wrong, and that is corrected below. It still does not yield a peer group,
for a reason that turns out to be structural rather than circumstantial.

---

## Recommendation

**(c) Don't build it.** Four independent grounds, any one of which would be
sufficient, measured in that order of decisiveness:

1. **The published classification is not a partition, and the faithful
   version is degenerate.** Grouping by it requires a collapse rule no
   source publishes (§2).
2. **The underlying figure is not stable enough to carry the comparison.**
   The same peer statement about Lakewood moves from *"unremarkable"* to
   *"less than half of typical"* in one year, with nothing about Lakewood
   changing that the site can see (§6).
3. **The conclusion's sign depends on the axis the site picks** for 39.8% of
   California cities (§4).
4. **The site already reaches every peer set a reader can name.** The only
   thing a site-chosen set adds is the site choosing (§5).

Two real defects surfaced along the way. Neither depends on this
recommendation and both should be fixed regardless (§7).

---

## 1. What axis — every candidate, measured

All figures FY2023-24, 482 cities, police spending per resident unless
stated. The baseline every axis must beat:

| | n | median | IQR | **IQR / median** |
|---|---|---|---|---|
| all cities, police $/resident | 482 | $407 | $242 | **0.60** |
| all cities, total $/resident | 482 | $1,623 | $1,081 | **0.67** |

### Explanatory power

Variance explained in **log₁₀** police-per-resident, against a permutation
null that reassigns the same group sizes at random. The log scale is not a
stylistic choice: on the raw scale Vernon alone ($73,088/resident,
population 205) dominates the total sum of squares and *every* axis tests at
chance, which flatters the refusal rather than testing it.

| axis | R² | null 95th | verdict |
|---|---|---|---|
| population bands (6) | 0.044 | 0.024 | above chance |
| police service code (5) | 0.101 | 0.027 | above chance |
| population band × police code | **0.166** | 0.078 | above chance |
| county (54 groups) | 0.223 | 0.187 | barely above, and 54 groups |
| fire service code | 0.057 | — | weak |

**The best realistic axis explains about 17% of the variation.** Roughly
83% of why one California city spends more per resident on police than
another is captured by nothing the site holds.

### What that means for one city

Lakewood's actual peer sets, with dispersion and its own position:

| peer definition | n | peer median | IQR/median | Lakewood's percentile |
|---|---|---|---|---|
| population ±25% | 75 | $374 | 0.53 | **1** |
| population band 50–100k | 104 | $372 | 0.52 | **1** |
| police service code D | 133 | $276 | 0.54 | **3** |
| band **and** code D | 30 | $260 | **0.28** | **0** |
| same county (Los Angeles) | 88 | $405 | **0.92** *(worse than baseline)* | 0 |

Only the crossed axis meaningfully tightens the spread — and it halves the
group to 30. Across 43 distinct peer definitions swept in this
investigation, Lakewood's percentile within its own group ranged **0 to 8**,
at or below the 5th percentile in 42 of 43. **Grouping does not explain
Lakewood. It re-asks the question in a way that sounds like an answer.**

---

## 2. Is any axis source-defined? — the brief's premise, corrected

**The brief states the Controller's services checklist has a most recent
vintage of FY2015-16. That is the dataset the site reads. It is not the most
recent one.**

SCO publishes [`8nra-c2cw`](https://bythenumbers.sco.ca.gov/api/views/8nra-c2cw.json),
*"Check List of Services Provided for Fiscal Years 2016-17 to 2023-24"* —
rows updated **2026-01-14**, 3,854 rows, all 482 cities in each of the eight
years, and **eleven services** rather than two:

> police · fire · emergency medical · street lighting · public transit ·
> community development & planning · solid waste · sewers · parks &
> recreation · libraries · water

…plus sworn-officer and firefighter headcounts. It covers **exactly** the
eight fiscal years the site publishes, per year rather than frozen.

So the honest answer to *"is the service axis source-defined?"* is **yes,
and better than assumed.** It is a California source's own statement about
its own entities, current, and it would be reproduction to adopt it.

**And it still does not give a peer group. Two measured reasons:**

### It is not a partition

The field is **multi-select**. In FY2023-24, **147 of 482 cities (30.5%)
file more than one police code**, and **311 of 482 (64.5%)** file at least
one multi-code across the eleven services. `AB` — *paid city employees* **and**
*city volunteers* — is the second most common police value, at 132 cities.

To group by this, someone must decide whether `AB` belongs with `A`, with
`B`, or in a class of its own. **SCO publishes the description; it does not
publish that decision.** Twelve distinct police strings, twenty-six fire
strings, thirty-nine transit strings — each one a place where a grouping
requires a rule the source declines to state.

### The faithful version is degenerate

Use all eleven services as a service profile — the most defensible,
least-judgement reading of the source, taking it exactly as published:

> **480 distinct profiles across 481 cities. 479 cities (100%) are alone in
> their own group. The largest group has two members.**

**This is the finding, and it is structural rather than a limitation of this
particular source.** The more faithfully the data describes a city, the more
unique that city becomes. Coarsen it enough to make groups, and you are
choosing what to ignore. The data can describe a city precisely **or** group
it usefully, never both — and **every position on the dial between them is
the Ledger's, not California's.**

### Everything else that was checked

| source | publishes a peer grouping? |
|---|---|
| SCO "By the Numbers" (170 datasets) | No city classification of any kind |
| SCO counties raw data | A "Class Data" column exists; the statutory county class (Gov. Code §28020) is **frozen at 1971 populations** for the express purpose of setting officer salaries |
| DOF E-1/E-5 | Population estimates, no grouping |
| Census of Governments | Government **type** (the site's layers already are this); population-size bands published only as state-level counts, never a per-entity roster |
| CDE "similar schools" rank | **Discontinued.** Died with the Academic Performance Index; last API report 2013. It also grouped *schools* on *academic demographics* — wrong entity, wrong variable |
| CDE district type | Published and adoptable — and explains **0.0006–0.0024** of per-ADA variance in every one of the site's nine years |
| CCC Chancellor's Office | Multi-college/single-college and community-supported status both test **at chance** on per-FTES (n=72) |
| CSU / UC | UC's "comparison institutions" are *outside* universities for faculty-salary benchmarking, not a grouping of UC campuses |

### The one apparent exception, and why it is not one

K-12 **basic-aid status** is published, is carried in the payload, and
explains **η² = 0.152** of per-ADA variance — by far the strongest
source-published axis anywhere on the site. It looks like the exception.

It is not, and the reason generalises:

| FY2024-25, current expense per ADA | n | median | IQR/median |
|---|---|---|---|
| all districts | 876 | $20,207 | **0.28** |
| state-funded | 763 | $19,753 | **0.25** |
| basic-aid | 113 | $27,473 | **0.44** *(wider)* |

**Basic aid shifts the median without narrowing the spread.** Its η² comes
entirely from a level difference between two groups, not from making the
members of either group comparable to each other. A classification that
predicts the level is not a classification that makes entities peers — and
peer comparison needs the second thing. Knowing a district is basic-aid
tells you it will be expensive; it does not tell you what expensive means
for *that* district.

---

## 3. The boundary problem

Under round-number population bands (<10k / 10–25k / 25–50k / 50–100k /
100–250k / 250k+):

- **117 of 482 cities (24.3%)** sit within 10% of a cutoff; 57 (11.8%) within 5%.
- Shift every threshold by **+10%** and **361 of 482 cities (74.9%)** see their
  peer set change by more than a quarter (Jaccard < 0.75). Mean Jaccard falls to 0.66.
- Quintile and log-spaced schemes are better but not stable: at ±10%, 26.8%
  and 4.6% of cities respectively cross the same line.

The closest pairs the cutoff separates:

| | | | |
|---|---|---|---|
| Loma Linda | 24,965 · $287.64 | Riverbank | 25,006 · $210.39 |
| Azusa | 49,420 · $457 | Aliso Viejo | 50,068 · $192 |
| Vista | 99,723 · $282.77 | Hesperia | 100,087 · $223.49 |

**Loma Linda and Riverbank are 41 residents apart** — 0.16% — and land in
different peer groups.

**One honest qualification.** The band *medians* at the 50,000 line differ by
only 5% ($355 vs $372), so the boundary does not much distort the yardstick.
It distorts *membership*: Azusa and Aliso Viejo are 648 residents apart and
2.4× apart in the figure being compared, which says less about the boundary
than about how little population explains (§1).

---

## 4. What a reader would actually infer

The objection to test was: *several entities in one view with a common
denominator will be ordered by the eye regardless of sort order or
labelling.* It survives testing, and the measurements make a stronger point
than the objection did.

**The conclusion's sign depends on the axis, for two fifths of California
cities.** Applying six defensible axes to every city, **190 of 477 (39.8%)**
are above their peer median on at least one axis and below it on another.
Median spread of the "percent of typical peer" statement: **1.46×**; 7.1% of
cities move more than 2×; maximum 6.70× (Ferndale: 0.32× of peers under a
population band, 2.15× under a spending band).

For Lakewood, the same sentence, same year, same numerator:

| axis | "spends this % of typical peer" |
|---|---|
| population band **and** code D (n=17) | **41.5%** |
| LA County and code D (n=38) | 40.6% |
| police code D (n=133) | 37.5% |
| round band 50–100k (n=104) | 27.8% |
| 20 nearest by population (n=21) | 25.3% |

**A 1.64× swing produced entirely by a choice the site would make and the
data does not.**

**The distribution-only form relocates the objection rather than avoiding
it.** "Median police spending among the 133 cities that contract policing
with their county is $276; this city is $103" names no other city — but the
same sentence reads $249, $254, $276 or $407 depending only on which cities
the site conditions on. And the chosen 133 span $0 to $34,153, with only 67
of them inside their own interquartile range.

**Small peer sets are hostage to one outlier.** At n=8, dropping the single
highest peer moves the subject's percentile by a median of 6.2 points. For
Sand City, "spends 70.1% of the typical peer" becomes "157.2%" — a sign
flip — on removing one city. 5.0% of n=8 peer sets contain a member at least
ten times the set median.

**And clustering cannot make the choice for you.** 1-D k-means on log
population, k ∈ {3,4,5,6,8,10} × three seeds: Lakewood's cluster ranges from
56 to 205 cities, and within-cluster sum of squares falls smoothly with **no
elbow**. California city population is a continuum. *k* is a free parameter
nothing in the data fixes.

---

## 5. What the comparison view already does

`cities.html` already compares 2–4 reader-selected entities: capped at four
in all four entry paths, **ordered alphabetically at two independent points**
with the code comment naming neutrality as the reason, on a shared scale,
within one layer, with **every comparability note for every selected entity
printed in full**. There is no sort control on the page. No "vs" framing
exists anywhere in reader-facing copy.

The reader can already reach **2,239,709,641** distinct 2–4 city sets.

**A peer group adds no reachability whatsoever. The entire difference is
that the site would choose the set instead of the reader.** That is the whole
feature, and it is also the whole objection — the brief asked for it to be
named plainly, and that is the plain naming.

The site has already refused this in three places, two of them adopted rules:

> **GUARDRAILS §1** — "No ranking, in any form… Cities, counties and
> districts are ordered **alphabetically, always**. A reader who wants a
> ranking can sort the CSV; the arithmetic is theirs and so is the judgement
> that follows from it."

> **GUARDRAILS §3** — "No derived scores… **no per-capita rankings dressed as
> analysis**… if a reader wants a test, they take the CSV."

> **`districts.html` D-3** — "**even within-type comparison would assert a
> likeness the data cannot support** — none is offered."

A peer percentile is a per-capita ranking dressed as analysis. §3 already
decides this; the investigation's job was to test whether a source-defined
grouping would earn an exception. It would not, for the reasons in §2.

---

## 6. The instability that decides it independently

Even granting a perfect grouping, it would be laid over a figure that cannot
carry it.

**Lakewood's police line fell from $15.4M to $8.3M in a single year while the
city's total spending rose from $73.2M to $83.4M.** The site's derived flags
do not fire: `bigSwing` watches the total, not the function.

The same peer statement, same city, same peer definition, three consecutive
years:

| | peer median | Lakewood | % of typical | percentile |
|---|---|---|---|---|
| FY2021-22 | $221 | $183 | 82.7% | 17 |
| FY2022-23 | $241 | $192 | 79.7% | 13 |
| **FY2023-24** | $260 | **$103** | **39.7%** | **0** |

A peer view would have published *"Lakewood spends less than half what
comparable cities spend on policing"* — a confident, prominent, checkable
claim about a real city — on the strength of a one-year movement whose cause
the site cannot determine. **This is the Mt. Shasta shape:** a bad or
reclassified input producing a confident derived statement.

It is not isolated:

- **Lancaster's** police line: $35.8M → $6.9M → $39.8M across three years.
- **6.2%** of function-year transitions with a ≥$1M base move more than 40%
  while the city's total moves less than 10% — the reclassification
  signature. **388 of 482 cities (80%)** show it at least once.

The site publishes these figures with a gate on the *total*, which they pass.
Nothing gates the split between functions, because the Controller publishes
no control for it. A peer comparison at the function level — which is what
"$103 per resident on police" is — inherits every bit of that instability and
presents it as a finding about a city.

---

## 7. Two defects found, independent of this recommendation

Neither is about peer groups. Both are about data the site publishes today.

**a. The site reads a retired SCO dataset.** `pipeline/fetch_city_data.py:101`
sets `DS_SERVICES = "tsz3-29gc"` (FY2002-03 to 2015-16). SCO's current
`8nra-c2cw` covers exactly the eight years the site publishes, per year, with
eleven services instead of two, and was updated 2026-01-14.

*Nothing on the site is currently wrong because of this.* Comparing like with
like — the stored letter against the first letter of the current code — the
two agree for **471 of 482 cities (97.7%)**; only 11 reflect a genuine change
of arrangement (Agoura Hills, American Canyon, Biggs, Blue Lake, Calimesa,
Commerce, Fort Jones, La Quinta, Lathrop, Menifee, Willows). But the site is
reading a superseded file and presenting a decade-old snapshot as current.

**b. The pipeline silently collapses a multi-select field.**
`pipeline/fetch_city_data.py:497`:

```python
"police": norm(r.optional("police_service")).upper()[:1],
```

The `[:1]` truncates. SCO's service field has always been multi-select:
**147 of 482 cities (30.5%) file more than one police code** and 83 (17.2%)
more than one fire code. A city that files `AB` — its own paid officers
**and** volunteers — is stored, displayed and exported as `A`.

This is the more serious of the two, and it is the site's own defect class:
**the Ledger deciding, silently, inside a field it presents as the source's
own statement.** The single letter carries a tier chip's authority and a
label quoted verbatim from SCO's codebook, while dropping information the
source published. It should either carry the full code or say that it does
not.

Lakewood is not affected (`D` police, `H` fire, both single).

---

## What would change this finding

- **SCO, CDE or another California authority publishing an actual peer
  roster** — "these entities belong beside each other" — rather than a
  classification the Ledger would have to elect to group by. Nothing in the
  catalogue does this today.
- **A published control for the function-level split**, which would let §6's
  instability be gated rather than merely observed.

Absent both, a peer group is the Ledger deciding which governments belong
beside each other, and then disclaiming the inference it has arranged. The
brief asked whether that objection survives testing. It does — and the
measurements in §2 and §6 are stronger than the objection was.
