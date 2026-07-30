# A-2 — Per-entity static pages: what they would cost, and what they would buy

*Measured 2026-07-29. Investigation only; nothing built. Every figure below
was re-measured on the current tree rather than quoted from `SCOPE.md`,
because the recorded `.git` figure turned out to be understated more than
five-fold — see §2.*

**Recommendation: (c) don't build the 8,257-page version, and (b) build one
narrow thing instead — a per-entity deep-link parameter for CCC, CSU and UC,
which is 106 entities' worth of missing addressability and needs no new
files at all.** The reasoning is in §5; it rests on a single measurement:
the site already carries a per-entity index of **exactly the same 8,257
entities**, in one 0.49 MB file, and 8,151 of them already have a working
per-entity link.

---

## 1. How many pages

Counted from the payloads, not estimated:

| layer | entities |
|---|---|
| special districts | 5,241 |
| K-12 charters | 1,154 |
| K-12 districts | 941 |
| cities | 482 |
| state departments (union of all years) | 206 |
| CCC districts | 73 |
| K-12 county offices | 58 |
| counties | 57 |
| CSU campuses | 23 |
| state agencies | 12 |
| UC campuses | 10 |
| **total** | **8,257** |

Compensation employers are a further **4,132** and are not in the brief's
list; they already have per-entity `comp/*.json` files, so adding pages for
them would double the file count again. They are excluded from every figure
below and named here so the exclusion is deliberate.

**The 8,257 is not a coincidence.** `search-index.js` already contains
`"entities": 8257`, and its per-layer breakdown matches the table above
row for row — 5,241 districts, 1,154 charters, 941 schools, 482 cities, 218
state (12 agencies + 206 departments), 73 CCC, 58 COEs, 57 counties, 23
CSU, 10 UC. The proposal would give a file to each member of a set the site
already enumerates in a single file. That is §5's whole argument.

---

## 2. What it weighs — and a correction to the record

### The current tree, re-measured

| | recorded in `SCOPE.md` | **measured 2026-07-29** |
|---|---|---|
| working tree (tracked) | 117 MB | **94.6 MB** |
| `.git` | 25 MB | **133 MB** |
| tracked files | 4,264 | **4,285** |
| local clone | 0.66 s | **1.12 s** |

Two of the four recorded numbers are wrong in opposite directions, and the
`.git` one is wrong by 5×. The brief's earlier check found 104 MB; it is now
133 MB. **`SCOPE.md` §"What it costs, measured" is stale and §6 of this
document replaces it.**

The working-tree figure is *lower* than recorded because `SCOPE.md`'s 117 MB
appears to have included content that is no longer tracked. The `.git`
figure is higher for a reason that matters to this decision — see "the
recurring cost" below.

Also worth recording because it will mislead someone: `du -sh` on the
checkout reports **7.9 GB**. That is `pipeline/cache` (7.3 GB of fetched
source documents), which is gitignored and is not in a clone. The number a
cloner experiences is 94.6 MB of files plus a 126 MB `.git`.

### What entity pages would add

Per-entity record markup, measured by rendering real records and weighing
the DOM: **special district 5.0 KB · K-12 district 10.7 KB · city 15.5 KB**.
Weighting each layer by its own measured size gives **53.6 MB of record
markup** for 8,257 pages before any page shell.

The shell is the swing factor, and the site's current pattern is the
expensive one — every page inlines its own CSS (`ccc.html`: 23.0 KB of CSS,
37.4 KB of JS):

| shell strategy | added to tree | median page | tracked files | working tree |
|---|---|---|---|---|
| shared external CSS/JS, +3 KB boilerplate | **+77.8 MB** | 9.6 KB | 4,285 → **12,542** | 94.6 → **172.4 MB** |
| CSS inlined per page (today's pattern) | **+239.0 MB** | 29.6 KB | 4,285 → **12,542** | 94.6 → **333.6 MB** |

So the cheap version roughly **doubles** the repository and **triples** the
file count; the version consistent with how the site is built today roughly
**quadruples** it.

### The recurring cost, which is the one that decides this

Git stores a new blob for every changed file in every commit, forever. HTML
compresses to about **0.31** of raw, so one version of the cheap variant
costs `.git` roughly **+21.8 MB**, and the inlined variant **+66.9 MB**.

That is per *version*, not once. The `comp/` precedent measures the
frequency directly: `comp/` has been written twice, and the second write —
a change to how two columns are encoded, no figures altered — **rewrote
2,183 of its 4,132 files**. A payload rebuild that moves any figure would
rewrite most of 8,257 entity pages the same way.

**This is why `.git` is 133 MB against a recorded 25 MB.** The per-entity
file pattern is cheap to adopt and expensive to keep, and the cost lands on
every future rebuild rather than on the commit that introduces it. Ten
rebuilds of the cheap variant is another ~220 MB of `.git` that can never
be reclaimed without rewriting history.

---

## 3. `file://` or `fetch()` — is this a fourth exception?

`SCOPE.md` records three architectural exceptions: two manual-cache sources
(CSU, compensation) and one runtime `fetch()` (compensation's on-demand
position detail). A fourth needs its own finding, and the answer depends
entirely on how an entity page gets its data. Three options, and they are
not equivalent:

**(a) Inline the entity's figures at generation time.** Works from
`file://`, no network, no fetch. **No new exception.** This is the only
option that keeps the durability claim intact — and it is the one that
creates the drift problem in §4 and the size problem in §2.

**(b) `<script src="city-data.js">`.** Works from `file://` and adds no
exception, but a page for one city loads **3.92 MB** to show 15.5 KB, and a
K-12 district page loads **15.57 MB**. Technically compliant, practically
indefensible.

**(c) `fetch()` a per-entity JSON.** This *is* a fourth architectural
exception, and it fails from `file://` on every browser — the exact
property `SCOPE.md` protects when it says the site can be "cloned, opened,
and read with no server". It would also make 8,257 pages non-functional for
the offline-archive case that the durability argument rests on.

So the only admissible design is (a) — which means every entity page
contains a *copy* of figures that already exist in the payload.

---

## 4. What generates them, and can they drift?

This is the strongest objection and it is not a cost objection.

Option (a) means **two artefacts state the same figure**: the payload the
pages are generated from, and the 8,257 pages. They agree only if
regenerated together, every time, without exception. If a payload is rebuilt
and the pages are not, the site publishes two different numbers for one
entity and looks authoritative doing it.

**That is the ground C-4 was rejected on** — a second source of truth for
one figure — and nothing about entity pages makes it less true. The
mitigations are real but they are not free:

- generation must be a step *inside* each layer's pipeline run, not a
  separate script anyone could forget;
- the suite must assert, per entity, that the page's figures equal the
  payload's — 8,257 more assertions, or one swept assertion over 8,257
  files, added to a suite that currently runs 4,396 in ~15 minutes;
- the gate must refuse to write a payload whose pages did not regenerate,
  or the failure mode is silent.

None of that is exotic. It is, however, a permanent obligation attached to
every future data change on nine layers, in exchange for the benefit in §5.

---

## 5. What it actually buys — and the case against

The stated benefits are **citation** and **search**. Measured against what
the site already does, most of the citation benefit is already delivered and
the search benefit is largely external.

**Citation is already per-entity.** Every layer page carries a stable
fragment permalink (`cities.html#c=los-angeles`), and C4 put a full citation
string — title, figures, basis, source, generated date, permalink, accessed
date — on the record and on the printed sheet. A path-based URL
(`/cities/los-angeles.html`) would be *tidier* and would survive tools that
strip fragments, which is a real if narrow robustness gain. It would not add
information; the citable record already exists.

**Internal search is already per-entity.** `search-index.js` indexes all
8,257 entities in **0.49 MB** and deliberately carries no figures, so
results from layers measured on different bases cannot be compared. Entity
pages would not improve this. What they would improve is *external* search —
crawlers do not treat fragments as separate documents, so today Google sees
16 pages where it could see 8,273.

**So the honest summary: the principal benefit is SEO.** Not citation, which
exists; not search, which exists. Discoverability by external search
engines, plus a modest citation-robustness gain. That may be worth wanting —
a reader who searches "Hollister city budget" and finds this record rather
than not finding it is the reader the site is for. But it should be argued
as SEO, and weighed against ~78–239 MB, 8,257 files, a doubled-to-quadrupled
`.git` that grows on every rebuild, and a permanent two-sources-of-truth
obligation across nine layers.

Two further sceptical notes:

- **8,257 pages of largely templated text is what a search engine treats as
  thin or duplicative content.** The SEO benefit is not proportional to the
  page count, and may be materially less than it appears.
- **`GUARDRAILS.md` §1 bans rankings, and entity pages are where comparison
  pressure will arrive** — "similar entities", "compare to nearby", "how
  does this city rank". Nothing in the proposal requires that, but the
  surface invites it in a way the current per-layer tables do not.

### The one genuine gap, and it is small

`search-index.js` records `param: null` for **CCC (73), CSU (23) and UC
(10)** — confirmed in each page's `applyHash`, which reads unit, sort and
year but has no entity parameter. So **106 of 8,257 entities are indexed and
searchable but not individually addressable**: a search result can only land
the reader on the whole-layer table.

That is a real defect in the citation story, and it is the only one the
measurement found. It is fixable with a deep-link parameter on three pages —
the same `#c=` / `#d=` pattern the other seven layers already use — and it
creates **no new files, no drift risk, and no new architectural exception**.

---

## 6. Recommendation

**(c) Do not build per-entity pages for 8,257 entities.** The cost is
measured and large, the recurring `.git` cost lands on every future rebuild,
the only `file://`-compatible design duplicates every figure, and the
principal benefit is SEO rather than the citation and search the proposal
claims — both of which the site already provides.

**(b) Build the narrow thing instead:** a per-entity deep-link parameter for
`ccc.html`, `csu.html` and `uc.html`, closing the 106-entity addressability
gap. Its own PR, no new files.

**If the SEO argument is accepted anyway**, the narrowest defensible subset
is **cities + counties (539 pages, ~5.2 MB)** — the entities a member of the
public is most likely to search by name, at 6.5% of the file count and 6.7%
of the size of the full proposal. Special districts, at 5,241 pages and 63%
of the count, are the least searched by name and should be last, not first.
Charters (1,154) raise a separate problem the schools layer already records:
their reporting is voluntary and self-selected, so a page per charter gives
equal prominence to a set that is not comparable.

**Not a fourth architectural exception** under design (a) — and if anyone
proposes design (c), `fetch()` per entity, that is a fourth exception and it
breaks `file://` for 8,257 pages.
