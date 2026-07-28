# Citizen Ledger — bulk data schema

*Generated 2026-07-28. One CSV per published layer, covering every entity and every shipped year.*

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
| `cities.csv` | `77a64e67fdb171e4c2a5ff6bccb5e380d2d8472154dd26f31e1f73ada8d33b2a` |
| `community-colleges.csv` | `39d41a79c6cad48e7dd5aa1a0ffc95b8b8d472b462bdd3277078b01e256067b3` |
| `compensation.csv` | `51fa1887809228a033b2a1b361a52c9870ca0b7d8b5449a303e3e3c7ca5f9390` |
| `counties.csv` | `418120b45b0b6843c924af1fe02eaa431565c0d8dc04bf2d69afb28073e085e0` |
| `csu-campuses.csv` | `e4257be380a0d2290009650774b81db1dfb24954f626322ff52769ddf797907d` |
| `k12-schools.csv` | `63c8bdd0d98180f0713fc908e8f38b7b95ace13321b9707304459b03fa2c517a` |
| `price-deflator.csv` | `7f0578dbf364a96fac8e7d91e94df86bdbe22eea05b098ddd4936011f239a6e9` |
| `special-districts.csv` | `276ce0f067791e3b357965ca99f7e4f3be94ad23852b21a6ca90c024e929538c` |
| `state-budget.csv` | `3fce840a953b96b5b4e6e5c7962dc1188457ae3d60c5be4a82d3e33144a38a09` |
| `uc-campuses.csv` | `63c8aa98aa60599fac797bb5468281853cf4ce438a56df5a51f4fb2795c5b3c4` |

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
