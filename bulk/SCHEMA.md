# Citizen Ledger — bulk data schema

*Generated 2026-07-27. One CSV per published layer, covering every entity and every shipped year.*

## Before you use these

**An empty cell is not a zero.** Every file here carries figures that are absent because the source does not publish them — a district that did not file, a year outside a campus's coverage, a department whose actuals have not arrived. An empty cell means *not published*. A real reported zero is written `0`. A spreadsheet that treats both as zero will produce totals no government ever reported.

**The layers do not add up, and are not meant to.** The same dollar appears in more than one file: roughly half of what counties and school districts report receiving is money the state budget already shows sending. There is no combined total, and summing across files produces a number that describes nothing.

**Accounting bases differ per file and are never mixed.** An enacted appropriation is a plan; an actual expenditure is a record; an audited GAAP figure is a third thing. Each file's header names its own basis.

**Gate tiers differ per file, and one file's tier can differ per column.** A *gated* figure reproduces a total the source itself published, to a named resolution. An *as-filed* figure has no published control to check against — it is the government's own number, and nobody has confirmed it. Both are in this set, labelled.

## Stability

**The shape of these files is not stable.** The Ledger is actively developed. Columns may be added, renamed or split as layers change, and a script that reads these files by column position will break. Read by column name, and pin a copy of the file if you need a reproducible result.

That caveat is about **shape, not licence**. The data is CC0 1.0 (public domain): use it for anything, no permission, no attribution required — though a link back helps a reader check it.

Each file's provenance header carries the generation date of the data and the export date of the file. They are different dates and both matter.

## The files

| file | rows | columns | layer |
|---|---|---|---|
| [`cities.csv`](cities.csv) | 3,856 | 22 | Cities — Reported actual revenues and expenditures by function, per city per year. |
| [`community-colleges.csv`](community-colleges.csv) | 1,086 | 15 | Community colleges — District Current Expense of Education with apportionment figures where the source publishes them. |
| [`compensation.csv`](compensation.csv) | 4,132 | 10 | Compensation — Reported positions, wages and retirement/health per employer. Positions, not people. |
| [`counties.csv`](counties.csv) | 456 | 21 | Counties — The same State Controller form, filed by counties. A county serves the whole county. |
| [`csu-campuses.csv`](csu-campuses.csv) | 23 | 7 | CSU campuses — Audited operating expense per campus. One fiscal year — older years cannot be gated. |
| [`k12-schools.csv`](k12-schools.csv) | 16,928 | 27 | K-12 schools — Districts, county offices and charter schools, with the per-pupil denominator and the function split. |
| [`price-deflator.csv`](price-deflator.csv) | 82 | 3 | Price deflator — The index behind every real-dollar figure on the site. A supporting series, not a layer. |
| [`special-districts.csv`](special-districts.csv) | 38,015 | 15 | Special districts — Every filing district, by fund class, as filed and unreconciled. |
| [`state-budget.csv`](state-budget.csv) | 1,837 | 12 | State budget — Enacted appropriations by agency and department, with Department of Finance actuals on the same basis where published. |
| [`uc-campuses.csv`](uc-campuses.csv) | 50 | 20 | UC campuses — Audited expense with medical centres and auxiliaries separated on UC's own lines. |

## Checking a downloaded file

Each file's SHA-256 is recorded when it is generated, so a copy can be checked against the copy this build produced:

```
shasum -a 256 bulk/<file>.csv
```

| file | sha256 |
|---|---|
| `cities.csv` | `f4e740f22724aeb0077b41385c25b3614d5957e6201679a501ccae7d10c5f2d4` |
| `community-colleges.csv` | `4a6fe526e94d43c0e4a79a6e0487840500e69c0b26ca7b0a33dac540ad52fe67` |
| `compensation.csv` | `aa8d87c69d2294f900464e200f784cf6e54bf40cd2c3a7ab8f1c5c50e1d382c5` |
| `counties.csv` | `6640815a3574fffcec51466cd39deeccfeb740d97250c5918cc77a8af8717051` |
| `csu-campuses.csv` | `b7e4910164c8f42a1b6f372d0eb2c52bdfcf897a6f84c9c561c54e513da5f5f6` |
| `k12-schools.csv` | `97e7f36907a7c1f3b326be7f802cd94cf92903ce4d57e40eb3693d31fe941a51` |
| `price-deflator.csv` | `3a658e6af82403d5fdfced36b58fc7a7b40f13353e1ae8e2dffc86e26d0eb68b` |
| `special-districts.csv` | `f34977fbf92a64c2a88e4dc17f88030a8c694634936ab566182429ad30d803ab` |
| `state-budget.csv` | `bc162c0dbc4a3faa9be3c0eb55003b037594a0eb094ac35e46d97ecae4d96409` |
| `uc-campuses.csv` | `d18fc422d2db50ddcbcc359871c3c9a4d7fac368d09b65265e3146da9f615a84` |

The digests above describe *these* files. The `-data.js` payloads they are derived from carry their own digests, verified by `pipeline/verify_digest.py`.

## Column conventions

Suffixes carry the unit, so a column's unit never depends on remembering which file it came from:

| suffix | unit |
|---|---|
| `_usd` | dollars |
| `_kusd` | **thousands** of dollars (the source's own denomination) |
| `_musd` | **millions** of dollars (the source's own denomination) |
| `_busd` | **billions** of dollars (the source's own denomination) |
| `exp_*` | an expenditure component |
| `rev_*` | a revenue component |
| `fn_*` | a published functional classification |

Where a figure is denominated in thousands or millions, that is the **source's** resolution, not a rounding the Ledger applied. Converting to dollars invents precision the source did not publish.

## Per-file notes

Every file repeats its own basis, tier, units and caveats in `#` comment lines above the header row. Those lines are the authoritative description of that file — this document summarises, the file itself governs. Most CSV readers skip `#` lines; if yours does not, drop lines beginning `#`.

Three notes that catch people out:

- **`state-budget.csv`** interleaves agency and department rows. A row with an empty `department` is the agency total. Summing both together double-counts every dollar.
- **`k12-schools.csv`** carries three record types in one file. Only `record_type = district` enters any per-pupil comparison — the Department of Education excludes county offices and charters from its own per-pupil statistic, and so does the Ledger.
- **`compensation.csv`** counts *positions*, not people, and must not be averaged: there is no hours or FTE field, so a mean over these rows is an artifact of the part-time share rather than a typical salary.

## Provenance and verification

Every figure here is reproduced from a payload built by the pipelines in `pipeline/`, each of which reconciles against a published control before it writes anything. The data files carry a SHA-256 digest; the verifier is `pipeline/verify_digest.py`.

The investigation documents that decided what each layer publishes, what tier it earned, and what was refused are in `docs/`, indexed at `findings.html`. Where a layer is as-filed rather than gated, the finding says why, with the measurement.
