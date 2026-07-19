# V13 finding — change-detection feed and data archival

*Investigation date: 2026-07-18. The question: can the Ledger publish a
public record of every data revision — when a vintage was loaded, which
figures moved, by how much, and whether the source restated its own
published data or the Ledger corrected its own extraction? Investigation
only; nothing was built. Every number below was measured on this
repository, and the scripts are named so each can be re-run.*

**Recommendation: (a) BUILD IT — as a forward-only revision record,
starting empty, after fixing a blocking identifier defect first.**

The feature is affordable to the point of being nearly free: the
Ledger's entire real revision history is **31 events, 636 bytes
gzipped**, and git has been retaining every vintage all along at about
**4.4 KB per all-layer refresh**. The archival question, which looked
like the core decision, turns out not to be a decision at all — the
archive already exists.

Three things are harder than they look, and two of them are the reason
this finding does not simply say "ship it":

1. **A blocking defect must be fixed first.** For 31 K-12 and charter
   records the Ledger's own entity identifiers are **not stable across
   builds** — the same source data produces a different `school-data.js`
   depending on `PYTHONHASHSEED`. A feed built today would publish
   **2,149 fabricated restatements** that never happened. This is a
   louder version of the exact problem the feed exists to solve, and it
   is a live defect independent of this feature.
2. **Attribution cannot be automated today on any layer, and the
   source-restatement-versus-source-redefinition distinction can never
   be automated on any layer.** That is a permanent human commitment on
   every future refresh, forever. Section 3 states it without softening.
3. **Backfill yields one event, and it is our own bug.** The feed starts
   empty. Section 4 recommends saying so on the page rather than
   engineering around it.

The citation tie-in — the feature's highest use — is **feasible**, and
better than expected: every citation the site has ever emitted already
carries the build vintage, so citations already in the wild can be
served, at day resolution, with a stated caveat.

---

## 0. What was measured, and what was not

All measurements are against `main` at `a65ae93`, working tree clean.
Seven parallel investigations were run, each independently
adversarially verified by a second reviewer instructed to re-measure
rather than re-read; the verification raised 77 problems, and the
corrections are folded in below. Where a headline number was disputed
between the two, I re-measured it myself; those are marked **(measured
here)** and their scripts are named.

**Not measured, and it matters:** whether any upstream source has *in
fact* restated a figure the Ledger already published. Testing that
requires re-fetching every source live and comparing to shipped data.
So this finding establishes what a feed would cost and whether it can
be honest — not how much it would have to report.

---

## 1. Archival strategy — the decision that isn't one

### The archive already exists

Git has been retaining every vintage of every data file since the
project began. The only question is what a *new* retained vintage costs,
and the answer is: very little, because git's delta compression works
extremely well on these files even though they are single-line JSON
(deltas are byte-based, not line-based).

| Option | Clone cost per refresh | Phone payload cost | Verdict |
|---|---|---|---|
| **(A) Full vintages retained in-repo** | **~4,400 B** for a realistic all-layer revision; **~1.07 MB** for a whole new fiscal year across all ten layers | **0 B** — old vintages sit in history; no page fetches them | **Already happening.** Not a new cost. |
| **(B) Compact diff-only record** | same as (A) — it is a committed file | **20.5 B per event gzipped** (measured here) | The only option a phone pays for, and it is tiny |
| **(C) Reconstruct from git history** | **0 B** | **0 B** | Free and fast — **2.16 s** to diff all 17 historical pairs across all 10 layers — but invisible to a reader on the site |

A 40-figure restatement of the 5.1 MB `school-data.js` costs **on the
order of 600–1,100 bytes** in the pack. (The two investigations
measured 900 B and 1,058–1,090 B using different perturbation sets and
different re-serialisation paths; the range is honest, the order of
magnitude is not in doubt.)

### The headline cost, measured here with a stated schema

The entire real revision history of this project, as diff records:

```
real events in the entire history: 31
  raw  4,390 B      gzip 636 B      (20.5 B/record gzipped)

sample record:
{"v":1,"layer":"city","built":"2026-07-14","kind":"correction",
 "e":"american-canyon","y":"2016-17","k":"byFunction/other",
 "old":22.938,"new":0.41}
```

Scaling that same schema on real entity ids and realistic values:

| events | raw | gzipped |
|---:|---:|---:|
| 100 | 15,618 B | 2,373 B |
| 1,000 | 157,662 B | 20,882 B |
| 10,000 | 1,578,869 B | 203,905 B |
| 50,000 | 7,893,950 B | 1,016,748 B |

Script: `scratchpad/v13/mine/feedsize.py`. The schema is printed above
so the byte counts are checkable — a byte count with no reproducible
construction is the wrong kind of number for this project.

### The one real payload constraint: ship it per layer, not site-wide

The heavy pages are not the constraint; the light ones are. Current
eager payloads:

| page | layers loaded | raw | gzipped |
|---|---|---:|---:|
| address.html | 7 | 12,319,040 | 3,159,694 |
| schools.html | 1 | 5,165,027 | 1,326,092 |
| cities.html | 4 | 4,367,700 | 1,214,738 |
| districts.html | 1 | 2,320,216 | 496,918 |
| index.html | 1 | 684,461 | 183,046 |
| ccc.html | 1 | 58,651 | 16,854 |
| uc.html | 1 | 48,023 | 15,414 |
| csu.html | 1 | 34,502 | 11,510 |

A single global revision file shipped to every page would double
`csu.html` at **823 events** and `uc.html` at **1,062** (bisected on
real records) while `schools.html` would not notice until 60,000. **The
record must be split per layer.** At the measured real-world event rate
this is a non-issue for decades, but the split costs nothing to design
in and everything to retrofit.

### A note on the repository's size, because the obvious denominator is wrong

**82.2% of this repository's tracked content is an accident** (measured
here). A stray top-level directory literally named `undefined/` holds
198 verification screenshots and CSV fixtures — **76.4 MB of 92.9 MB
tracked**. Honest project content is **16.5 MB**.

```
undefined       76.4 MB   198 files   82.2%
(root)          12.4 MB    32 files   13.3%
docs             2.6 MB    26 files    2.8%
vendor           1.1 MB     2 files    1.2%
```

Any "how many refreshes until the clone doubles" figure computed
against the polluted total is meaningless. Against honest content,
retention is still cheap — but this is flagged because it is a real
defect, it is unrelated to this feature, and it should be fixed on its
own terms. It has been raised separately.

---

## 2. What counts as a change

### The addressable universe

**715,910 numeric cells** across the eight layers (**701,421**
dollar-valued), spanning **8,347 entities** and **49,840 entity-years**.
The parse was validated by recomputing every layer's anchor from it and
comparing against the constants in `tests/run_tests.py` — all pass.

| layer | cells | entities | entity-years |
|---|---:|---:|---:|
| district-data.js | 300,312 | 5,196 | 38,010 |
| school-data.js | 203,294 | 2,290 | 6,175 |
| city-data.js | 144,368 | 482 | 3,856 |
| county-data.js | 44,091 | 57 | 456 |
| data.js | 22,900 | 213 | 1,233 |
| ccc-data.js | 590 | 74 | 74 |
| uc-data.js | 232 | 11 | 12 |
| csu-data.js | 123 | 24 | 24 |

Two layers — special districts and K-12 — are **70.3%** of the total.

### Entity-year-figure is the right granularity, but not the right filter

The brief's instinct is correct: a restated cent in one district is not
a revision worth publishing; a $40M agency restatement is. But **a
single absolute-dollar threshold cannot express that**, because the
publication resolution differs by eight orders of magnitude across
layers:

| layer | quantum — one unit of the last published digit |
|---|---|
| data.js (agency/dept) | **$1,000,000** |
| data.js (funds/programs), city/county headline, CSU, UC | $1,000 |
| district-data.js, CCC, city/county `lines[]` | $1 |
| school-data.js | **$0.01** |

A one-quantum move is a million dollars in the state layer and a cent
in the K-12 layer. At a $1,000 threshold the state layer cannot express
a sub-threshold change at all, while the school layer has 895 non-zero
cells whose entire value is below it. **Materiality must be expressed
per layer, relative to that layer's own published resolution and
aggregate** — not as one global dollar figure.

Modelled against the real data, per-layer-relative rules (a cell moving
by ≥0.01% of its layer's aggregate) are the only ones that spread
evenly across layers; absolute-dollar rules select nothing at all from
CSU/CCC/UC even though those layers' median cell is a quarter of a
billion dollars, and percent-of-cell rules route almost everything to
the small-value layers.

### The structural events matter more than the value events

This is the most important result in this section, and it comes from
the one real correction in the project's history. The FY2016-17 city
misclassification fix touched **all 482 cities**, but expressed as a
diff it is:

| expression | count | dollars |
|---|---:|---:|
| changed on a **shared** path (what a naive feed reports) | **31** | $3,061.8M |
| paths **dropped** (the bloated `other` bucket) | 452 | $35,774.0M |
| paths **added** (police, fire, streets, parks…) | 3,760 | $36,241.5M |

**A naive "figure X changed from A to B" feed would surface 31 events
out of a 482-city correction and miss ~$36B of the movement**, because
a reclassification moves money between keys that did not previously
exist. A feed must treat *field appeared* and *field disappeared* as
first-class events, or it will systematically under-report exactly the
class of error the totals gate cannot see — which is the class that
matters most.

Structural churn is also the steady-state volume driver: special
districts alone turn over **~80–100 appearances and ~70–120
disappearances per year**. Cities and counties are full rectangular
panels (0 appearances across all 7 transitions), so an entity appearing
*there* is by itself notable.

### Two unanchored blocks worth knowing about

Only **0.9%–1.5%** of cells are anchored to a figure a reader can
independently look up at the source. (The two investigations differ on
whether the city/county tamper pins count; the range is stated rather
than resolved.) Two blocks have nothing at all:

- **`district-data.js` `rev` — 151,056 cells with no gate, no sum
  identity, and no pin.** `DIST_PIN` sums `exp` only. A revenue figure
  could move by any amount and nothing in the repo would notice. That
  is 21.5% of all dollar cells.
- **K-12 county offices and charters** have no pin and no external
  anchor; their internal sum identities hold, so a coordinated move of
  a total and its children passes.

Neither is caused by this feature, and neither blocks it. Both are
places where a change feed would be the *only* detection mechanism —
which is an argument for building it.

---

## 3. Source-restatement vs our-correction — the honesty crux

**Attribution is HUMAN-REQUIRED on all eight layers today. Not one
layer can do it automatically.**

The mechanical test — re-run the same extraction code over two cached
vintages of the source — requires retaining two vintages. **No layer
retains two.** Every cache writer overwrites in place, and
`pipeline/cache/` is gitignored (exactly one file is tracked). What
differs between layers is how far each is from being *able* to:

| tier | layers | state of play |
|---|---|---|
| **1. Mechanism present, retention absent** | UC, CCC, K-12, CSU | Raw source bytes are cached and extraction is a pure offline function of them — proven by re-running all four with the network hard-blocked. UC reproduces its shipped payload **bit-for-bit to the digest**. Only the second vintage is missing. |
| **2. Mechanism absent by construction** | state enacted, state actuals | The cache stores **post-extraction output**. Re-running new code against an old cached payload cannot exercise the extraction — extraction already happened before the cache was written. |
| **3. No artifact at all** | cities, counties, special districts | Zero cache; every run is a live SODA fetch, and the pipeline pushes aggregation *into* the source (`$select=sum(value)&$group=…`), so the raw rows never reach this machine. Confirmed by hard failure offline. |

For Tier 3 — three of eight layers — **attribution is not merely
un-automated, it is impossible at any effort.** Once the Controller
revises a figure, the old one cannot be reproduced by anyone, including
us. The only surviving evidence is the previous `city-data.js` in git,
which is an output and cannot separate a source restatement from our
own extraction change.

### There are five categories, not two

The brief's two-way split is right about what matters but misses three
real cases, all of which occur in this repository:

- **(c) We changed scope or method deliberately.** This is the *most
  common* cause of a shipped figure moving. The CCC correction is the
  clean example: Los Angeles CCD moved from $774,683,675 to
  $716,533,122 because the V11 finding had quoted the pre-exclusion
  total instead of ECS 84362. Same source, same code path, different
  definition chosen by us. **This one genuinely can be automated** —
  record the pipeline commit SHA in `meta` at build time and category
  (c) becomes a one-line check. Nothing does this now.
- **(d) The source changed its own basis or definition.** Also occurs,
  repeatedly — SCO moved its own column layout between vintages
  (the defect that produced `shape_gate()`); CDE retitles resources
  (46 in our window); DOF's Schedule 9 group names carry a real agency
  reorganization absorbed silently by a lookup table.
- **(e) An upstream *Ledger* layer changed.** `fetch_county_data.py`
  reads `../city-data.js`; `fetch_school_data.py` reads `../data.js`. A
  county figure can move because *cities* were refreshed. Detectable
  via git, but nothing checks it and no `meta` field records which
  upstream build was consumed.

### The honest ceiling

Even with perfect retention everywhere, the machine can only ever emit
a three-way verdict:

| machine output | requires |
|---|---|
| `OUR METHOD CHANGED` (c) | pipeline commit SHA in `meta` — trivial, not done |
| `OUR EXTRACTION CHANGED` (b) | new code + old cached bytes → new number |
| `THE SOURCE CHANGED` (a **or** d) | old code + new cached bytes → new number |

**The (a)/(d) split cannot be automated on any layer, ever.** A
restatement and a redefinition are observationally identical: in both
cases old code on new source yields a new number. They differ only in
the source's *intent*, which lives in its release notes or a phone
call, not in its bytes.

So the honest formulation is: attribution can be made automatic for the
**(b)/(c) boundary** — "did *we* make a mistake?" — on the four Tier-1
layers, and on the two state layers with cache changes. It can **never**
be automated for the **(a)/(d) boundary** — "did the source restate, or
redefine?" — on any layer.

### The workflow commitment, stated without softening

If the Ledger publishes a claim of the form *"this figure changed
because the source restated it"*, then **on every future refresh, on
every layer, forever**, a human must:

1. Diff the new output against the previous shipped output, per figure.
   (Possible today — git retains every shipped data file.)
2. For **cities, counties, and special districts**, decide the cause
   **with no evidence available**. This is not a judgement that can be
   researched later; the evidence is gone the moment the fetch
   completes.
3. For **CSU**, personally re-perform a browser extraction and attest
   that the TSV diff reflects the source and not their own reading of
   the PDF. There is no code to check them.
4. For **all eight**, read the source's own release notes to separate
   (a) from (d) — the step no engineering removes.
5. Not be misled by the digest. **`meta.generated` is inside the
   digest**, so a no-op rebuild on a later date changes it. "The digest
   changed" carries no information about whether a figure moved. A
   *figures-only* digest — the canonical digest with the whole `meta`
   block stripped — would make "did anything actually move?" an O(1)
   question. It does not exist today.

This is the same class of commitment the README already accepts for the
tamper pins ("the constants are re-derived and reviewed, never updated
silently"), and `tests/run_tests.py` already draws the honest
published-control-versus-tamper-pin distinction. That discipline is the
right precedent and the natural place to attach this one. **The gap is
that the pins prove the file still holds what the pipeline wrote;
nothing proves what the source held when it wrote it.**

### The cheapest real improvements, in order

1. **Retain the previous cache vintage on refresh** (UC, CCC, K-12,
   state) — write to `name.<sourcedigest>.ext` and keep the last N.
   **UC would work immediately with no other change.**
2. **Record a figures-only digest** beside `meta.integrity`.
3. **Record the pipeline commit SHA in `meta`** — makes (c)
   automatically excludable.
4. **Read and store Socrata's `rowsUpdatedAt`** for cities, counties and
   districts. The field exists — one probe of the city-expenditures
   dataset returned `2025-10-30T16:40:44Z` — and costs one extra GET.
   It is the only signal available to the three layers that have
   nothing. *(Measured on 1 of the 15 datasets those layers use; the
   other 14 are unverified.)*
5. **Store DOF's `publicationDate`**, already read at
   `fetch_state_data.py:252` and currently discarded to stderr.
6. **Cache the Schedule 9 PDF bytes**, moving state actuals to Tier 1.
7. **Give K-12 a `--refresh` flag.** It has none; refreshing it means a
   human deletes cache files by hand — the exact moment the old vintage
   is lost, performed manually, with nothing recording what was
   deleted.

---

## 4. Retroactive coverage — the feed starts empty

**Backfill would yield exactly one event, and it is our own bug fix.**

The repository is 10 days old (2026-07-08 → 2026-07-18), 82 commits, 24
data-file versions across 16 consecutive pairs. **Four of the eight
layers — special districts, CSU, CCC, UC — have exactly one commit and
can contribute nothing.**

Naive path-keyed diffing across all history reports **2,819 changed
figures** (measured here, `scratchpad/v13/mine/count.py`). That number
is almost entirely artefact:

| | count | disposition |
|---|---:|---|
| naive path-keyed "changed" figures | 2,819 | — |
| K-12, from slug reassignment | **−2,149** | **100% phantom** (§5) |
| cities, sample data → real data | **−639** | must be excluded — publishing "Los Angeles sanitation changed from $1,529.8M to $729.6M" when the first figure was labelled `SAMPLE` would be actively dishonest |
| **real in-place restatements, entire history** | **31** | all one commit, all FY2016-17, all city `byFunction` — **our own classifier bug** |

Re-keyed on the stable CDS identifier, **all four K-12 pairs give
CHANGED = 0** (measured here, `scratchpad/v13/mine/rekey.py`). Not one
K-12 figure has ever been restated.

Of the 16 pairs: **0** source restatements, **1** genuine correction
(ours), 2 sample→real replacements, and **13 pairs that changed not one
published figure**. The history is the layers being *built*.

Zero source restatements is structurally expected rather than lucky:
enacted figures do not change once enacted, and a 10-day window against
pinned sources gives no source the opportunity to restate.

The CCC report-8 correction — the other known real correction — is
**not in data-file history at all**. The pre-exclusion figure appears
only in the finding document and the build's correction note; the
shipped `ccc-data.js` had the correct value from its first and only
commit. That is the general pattern here: **this project's discipline
catches errors pre-commit, which is good for the record and fatal for
backfill.**

**Recommendation: state on the page that the record begins on the day it
ships.** A backfilled feed would advertise retroactive coverage it does
not have — one entry, mislabelled as a source change, plus noise. The
value of this feature is entirely prospective, which is an argument for
building it, not for pretending it has a past.

---

## 5. The blocking defect — entity identifiers are not stable across builds

Two investigations found this independently while looking for
revisions, and I reproduced it directly. **It must be fixed before a
feed exists, and it is worth fixing regardless of this feature.**

`pipeline/fetch_school_data.py:772` sorts a **set** of `(county,
district)` code tuples with a key function that returns **the name
alone**:

```python
all_keys = sorted({k for fy in Y for k in years[fy]["ce"]},
                  key=lambda k: years[Y[-1]]["ce"].get(k, ...)["name"])
```

For identical names the sort is a pure tie, so the winner of the bare
slug is decided by set-iteration order — i.e. by `PYTHONHASHSEED`,
which Python randomises per process. Reproduced here against the three
real districts named "Jefferson Elementary"
(`scratchpad/v13/mine/seed.py`):

```
PYTHONHASHSEED=0  jefferson-elementary -> San Mateo    (cds 4168916)
PYTHONHASHSEED=1  jefferson-elementary -> San Joaquin  (cds 3968544)
PYTHONHASHSEED=5  jefferson-elementary -> San Benito   (cds 3567488)
```

All three outcomes appear in the repository's actual git history, in
exactly this flip-flopping pattern.

**Blast radius (measured here):** 11 duplicated district names covering
**25 of 934 district records**; 3 duplicated charter names covering
**6 of 980**. County offices, cities and counties have no collisions
today; `coes[slugify(...)]` has no collision guard at all, so a future
duplicate county-office name would silently overwrite a record.
(`fetch_district_data.py` is safe — it hard-fails on collision.)

**Why this blocks the feature:** the feed's entire premise is that an
identifier names an entity. For 31 records it does not. A feed keyed on
slugs would have emitted **2,149 phantom restatements** across four
commits that changed nothing — 1,109 of them exceeding $1M, the largest
$95,226,240. And the failure mode is worse than the one being fixed: a
reader following an old `schools.html#c=jefferson-elementary` link sees
a *different district's* figures presented under the cited name, and no
revision banner would fire, because the figure was never revised — it
was reassigned.

It also undermines the digest story: re-running the pipeline on
unchanged source can produce a different `school-data.js` and therefore
a different published SHA-256, with no source change. The *figures* are
reproducible; the identifiers and the digest are not.

**Fix:** tie-break the sort on the CDS code, and give every colliding
district a county-suffixed slug rather than letting one win the bare
form. Charters need a composite identity (charter number is not unique
on its own). Then assert slug stability in the test suite — nothing
does today, and `PYTHONHASHSEED` is pinned nowhere.

---

## 6. The citation tie-in — feasible, and better than expected

### The anchor already exists

The brief anticipated that a citation made today carries no vintage
marker. **That is not what the code does.** All eight pages emit the
build vintage:

> …Source: City annual financial reports, State Controller's Office
> "By the Numbers" (bythenumbers.sco.ca.gov) — reported actual
> expenditures and revenues, **data generated 2026-07-14**. Permalink:
> …/cities.html#c=oakland. **Accessed 2026-07-19.**

So **citations already in the wild can be served.** That is unusual for
a retrofitted revision feature and it is the single strongest argument
for building this one.

### Three real limits, stated plainly

- **Day resolution only, and it is lossy.** **Five of ten** data files
  have same-day build collisions — up to three distinct builds share
  one date stamp. The `generated` stamp can say "your citation predates
  a revision" only when the revision crossed a date boundary.
- **Permalinks encode a view, not a figure** — entity, year, tab, unit,
  sort, query. Two loads of `#c=oakland` a year apart are
  indistinguishable to the page even if Oakland's figure moved
  underneath.
- **Do not key detection on the digest.** Two same-day `city-data.js`
  builds have different digests and **zero changed figures** — the
  delta was purely additive (the V8 `lines` layer). A page that
  announced "this figure has since been revised" on digest mismatch
  would have lied about all 482 cities × 8 years. **Diff figures, not
  files.**

### Design options

| option | cost | verdict |
|---|---|---|
| **A — vintage param + build-level index** | +13 B on the permalink; ~1 KB gz index | Feasible and cheapest, but can only say "something in this file changed" — useless across 5,239 special districts in one file. Good as a banner, not a figure claim |
| **B — sparse per-figure revision index** | **20.5 B/event gzipped**; the whole real history is **636 B** | **Recommended.** Per-figure precision, sidesteps the digest trap, split per layer |
| **C — per-entity "last revised" stamp in every payload** | 44 KB gz on `district-data.js` alone, to record zero actual revisions | **Reject** — dense storage of an overwhelmingly sparse fact |
| **D — figure digest in the citation** | +24 B citation, +11 B permalink, no payload | Feasible but **cannot serve any existing citation** (no digest is in any citation today), and only ever yields "differs", never "revised on ⟨date⟩". A complement to B, not a replacement |
| **E — "check a citation" affordance** | none beyond B | **Recommended alongside B.** A reader pastes their citation, the page reads the date out of it and reports against B's index. The only option that serves citations already published |

### One implementation trap worth recording now

Unknown URL parameters are ignored gracefully on all eight pages — but
they are then **silently erased on the first user interaction**, because
the hash is re-emitted from state. A vintage parameter must be added to
the *writer*, not just the reader, or a reader who clicks a year arrow
loses the anchor and any permalink they then copy is un-anchored. Note
that the writer is a separate `hashOf()` function on only five of the
eight pages; on `csu.html`, `ccc.html` and `uc.html` the hash is written
inline.

---

## 7. Naming — copy an authority rather than invent one

The distinction the brief asks for is standard and citable. The UK ONS
states it most explicitly:

- **Revision** — "updates to previously published statistics… that
  improve quality by incorporating improved methods, additional data
  sources or statistics that were unavailable at the point of initial
  publication."
- **Correction** — "amendments that are made to published statistics in
  response to the identification of mistakes following their initial
  publication."

ONS states the two should not be confused.
(<https://www.ons.gov.uk/methodology/methodologytopicsandstatisticalconcepts/revisions/guidetostatisticalrevisions>)

Recommended vocabulary:

| term | who owns the change | trigger |
|---|---|---|
| **Revision** — or **restatement** for a source re-publishing a prior year | **the source** | new data, methodology, benchmarking |
| **Correction** — **erratum** for a minor one | **us** | our own mistake |

Never "revision" for a Ledger bug; never "correction" for a DOF
restatement. BEA supplies the third rung (an *erratum* is a minor
supporting-table error). The US Census Bureau supplies the cheapest
possible per-figure marker, verified verbatim in a current publication:
a legend reading `(a) Advance estimate  (r) Revised estimate`, with the
flag printed inline on the restated figure. Eurostat supplies the
structural proof that mature publishers keep the two in **separate
policy documents** — which is the cleanest way to make it impossible
for a reader to confuse "DOF moved a number" with "we had a bug."

For staleness-at-citation the only good precedent is not a statistical
agency at all — it is **Crossmark** (Crossref), whose insight is a
durable pointer embedded in the artifact the reader keeps, so it can
alert them months or years after download. Agencies put banners on
release pages, which never reach a reader who already copied the
figure.

### Does anything in California do this?

**No — with two qualifications that should be stated rather than
discovered by a reader.** Checked across SCO By the Numbers, Open
FI$Cal, DOF/ebudget, CDE, and data.ca.gov:

- SCO's Socrata datasets expose `rowsUpdatedAt` and **no** version,
  vintage, or archive field; they are single tables spanning many
  fiscal years, rewritten wholesale.
- data.ca.gov has **zero** fiscal revision logs and **zero** fiscal
  vintage archives; CKAN's versioning APIs are not exposed.
- **Qualification 1: DOF's historical budget archive is a genuine
  25-year vintage series** (2000-01 through 2026-27, each year's
  publications preserved separately). Because every January Governor's
  Budget reprints prior-year actuals, the raw material for a revision
  triangle exists publicly. What DOF does not publish is any revision
  log, or any marker on a restated figure.
- **Qualification 2: CDE has exactly one published re-release note** —
  "The 2010-11 database was re-released May 4, 2012 to reflect a minor
  update to the Charters table."

The precise claim that holds: **no California fiscal publisher tracks
revisions — none marks a restated figure, none logs what changed, and
the one archive that preserves vintages never says a figure moved.**

Also worth recording: the project has already been bitten once. The V12
finding measured UC's FY2023-24 total at $54,703,428K as originally
published versus $54,516,654K in the following year's comparative
column — a **$186,774K** restatement, which is why the UC gate must run
within a single report year.

---

## 8. Recommendation

**Build it, forward-only, in this order.**

**Prerequisite (not optional):** fix the slug instability of §5 and
assert identifier stability in the test suite. Until then any feed
publishes fiction.

**Then:**

1. **Record the diff at build time** — every refresh compares the new
   payload to the previous shipped one, per figure, keyed on stable
   identifiers, and appends events to a **per-layer** record. Treat
   *field appeared* and *field disappeared* as first-class events, not
   just value changes (§2 — otherwise the feed misses ~$36B of the one
   real correction in our history).
2. **Label every event by category**, using the ONS vocabulary, with
   the labelling rules of §3 — automatic where it can be (method change
   via pipeline SHA; extraction change via retained cache on the four
   Tier-1 layers), and **human-entered where it cannot be**.
3. **Add the three cheap provenance fields** — figures-only digest,
   pipeline commit SHA, and source revision signal where one exists.
   These are independently worthwhile and make the feed's claims
   checkable.
4. **Surface it**: a per-layer revision record on the page, and a
   "check a citation" affordance that reads the `generated` date out of
   a pasted citation (§6, options B + E).
5. **Say on the face that the record begins the day it ships**, and
   that day-resolution matching is lossy where two builds share a date.

**Materiality:** publish every event, but rank and default-collapse by
a **per-layer relative** rule (§2). A global dollar threshold is wrong
in both directions.

### The workflow commitment this imposes

Stated plainly, because it is permanent and it is the real price of the
feature:

- **Every future refresh, on every layer, forever, requires a human to
  attribute each changed figure.** Automation can narrow the question
  to "the source changed" — it can never answer whether the source
  *restated* or *redefined*.
- **On cities, counties and special districts the human will have no
  evidence to reason from**, unless recommendation 3 (retention) is
  taken for those layers too — and for those three that means caching
  raw rows the pipeline does not currently fetch.
- **On CSU it is entirely a human claim**, because the extraction is a
  browser session that exists nowhere in the repository.

If that commitment is not acceptable, the honest fallback is a
**mechanical-only feed**: publish *that* figures changed, and by how
much, with no attribution claim at all. That is still novel in this
landscape, still serves the citation promise, and requires no
per-refresh human judgement. It would be a smaller feature and an
honest one. **What must not ship is an attribution label the pipeline
cannot support** — a feed that guesses at "the source restated this"
would be exactly the kind of unearned claim the rest of this project
is built to avoid.

---

## 9. Not measured

- **Whether any upstream source has in fact restated a figure the
  Ledger already published.** Requires re-fetching every source live.
  This is the finding's own thesis demonstrated: all six
  `enacted_*.json` cache files were re-fetched on 2026-07-18, and
  **nothing anywhere records whether a single figure moved**, because
  the prior payloads were overwritten.
- **Socrata `rowsUpdatedAt` for 14 of the 15 datasets** the three SODA
  layers use; one was probed.
- **Cold-cache reconstruction timings** (dropping the OS page cache
  needs root) and **brotli** payload sizes (not installed; GitHub Pages
  serves brotli, so real payloads are likely smaller than the gzip
  figures quoted).
- **Live in-browser rendering** of the citation strings; they were
  produced by executing the shipped `citationText()` in Node against
  shipped data rather than in a browser.
- **The real-world rate at which California agencies restate published
  figures** — no layer here has ever been restated in place, so there
  is no empirical distribution to fit. The materiality modelling in §2
  rests on a stated hypothetical, not an observed distribution.

---

## Appendix — defects found in passing

Independent of this feature, and raised separately:

1. **`undefined/` — 76.4 MB, 82.2% of tracked content** (§1), 198
   verification artifacts committed by accident.
2. **Google Fonts is an undocumented third runtime dependency.**
   `docs/SCOPE.md` names exactly two runtime third-party services;
   `fonts.googleapis.com` and `fonts.gstatic.com` are referenced on all
   ten pages. SCOPE.md is the document that decides what future
   features are allowed, so it should state the site's real runtime
   surface.
3. **The state pipeline degrades silently offline.** A network-dead run
   fetches zero years, emits no error, rebuilds from whatever is
   cached, and writes a `data.js` with a fresh `generated` date — a new
   vintage stamp on old data.
4. **`fetch_csu_data.py` hardcodes `ELIMINATIONS` and `COMBINED`** under
   a comment saying they come from the checked-in TSV header row. Worth
   confirming the comment matches where the constants actually live.
5. **`school-data.js` county offices and charters have no tamper pin**
   and no external anchor (§2).
6. **`district-data.js` `rev` is entirely unconstrained** — 151,056
   cells, 21.5% of all dollar cells, with no gate, identity, or pin
   (§2).
