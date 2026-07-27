# V25 finding: voter-approved bonds and measures against what is spent from them

*Investigated 2026-07-27. Four sources probed live; the chain tested
end to end against SACS FY2024-25, the CDIAC issuance file (76,703 rows,
56,783,584 bytes) and the CEDA 2024 school-district report. No build.*

## Recommendation, up front

**(c) Don't ship.**

Not because the sources are poor — CEDA is better than expected and
carries the authorised amount in 97% of bond measures — but because
**the identifier chain is broken at all three links, and every one of
them would have to be closed by our own judgement.**

| link | needs | what exists | verdict |
|---|---|---|---|
| measure → issuer | a shared key | **0 of 273** CEDA district names match a CDIAC issuer name exactly | broken |
| measure → issuance | a measure field on the issue | **177 of 20,253** K-12 issues (**0.87%**) name one, in free prose | broken |
| issuance → spending | a bond dimension in the fund ledger | SACS Fund 21 has **no** issuance, measure or project code | broken |

Per the brief: **if the link must be inferred, that is editorial and the
layer fails.** It must be inferred three times.

And the sceptical reading of §5 is the one that holds. The only
presentation that survives the mechanics — ballot purpose beside
bond-fund spending — is the one that **implies a reconciliation that
does not exist**, and that implication is the whole of the harm.

---

## 1. What is actually published, machine-readably

**The Secretary of State publishes nothing.** Its own page states it
plainly:

> "the Secretary of State does not certify or compile local election
> results."

Local measure results live in **58 separate county databases** of widely
varying quality. There is no state-level machine-readable local measure
feed.

**CEDA is the only statewide aggregation** — a joint project of CSU
Sacramento's Institute for Social Research and the Center for California
Studies with the SOS, annual since 1995, current through 2025. It is
distributed as **PDF reports** (Excel datasets are also offered).

Parsed directly from the 2024 school-district report (161 pages):

| | 2024 |
|---|---|
| school-district measures | **340** |
| passed / failed | **256 / 84** |
| at a 55% threshold | 340 (all) |
| mention bonds | 336 |
| **carry a parseable authorised amount** | **326 (97%)** |

Each entry carries county, election date, an abbreviated district name,
the measure letter, the outcome, the threshold, and **the full ballot
text** — which contains the authorised principal, the tax rate, and the
stated purposes.

**CDIAC** publishes issuance: 77 columns, 20,253 K-12 issues. Useful and
detailed on the debt itself. **No election, measure or proposition
field.** The nearest columns are `Statutory Authority` (a code section,
**blank on 60.3%** of K-12 issues), `Primary Purpose` (a fixed taxonomy)
and free-prose `Issue Name` / `Project/Series Name`.

**CDE** publishes school and district directory, enrolment and
accountability files. It has no local bond-measure dataset; school
facilities funding is administered elsewhere and is not a measure record.

---

## 2. The decisive question: does an identifier chain survive?

**No. It breaks three times, and each break alone is fatal.**

### 2.1 Measure → issuer: there is no shared key

CEDA names districts as they appear on the ballot; CDIAC names them as
they appear on the bond. Of **273 distinct CEDA 2024 district names,
exactly 0 match a CDIAC issuer name exactly.**

Normalising — lowercase, strip *school / district / unified / elementary
/ union / high / joint* — raises it to 90.1%. **That normalisation is
not safe.** Applied to CDIAC's own 2,144 K-12 issuer names it **collides
179 of them**, merging governments that are genuinely distinct:

```
'porterville'  ← Porterville Elementary School District
               ← Porterville Unified School District
               ← Porterville Union High School District
'fullerton'    ← Fullerton Joint Union High School District
               ← Fullerton School District
'campbell'     ← Campbell Union High School District
               ← Campbell Union School District
```

These are separate governments, with separate boards, separate bonds and
separate taxpayers. This site has already ruled on exactly this hazard:
V24a keys negative-balance history on the Controller's **Entity ID and
never on the name**, because two governments sharing a name would be
merged. The same discipline forbids this join.

### 2.2 Measure → issuance: the measure is not a field

Of **20,253 K-12 issues, 177 (0.87%) name a ballot measure** anywhere in
`Issue Name` or `Project/Series Name`. **20,066 (99.08%) do not.**

The 0.87% is generous. Ten further rows match the word *measure* in an
unrelated sense — *"Energy Conservation Measures"* — and were excluded
by hand. A regex looking for measures on this corpus finds mostly
building retrofits.

Where a measure *is* named it is prose, not data:

```
General Obligation Bonds, Election of 2024 (Measure E) Series A
GO Bonds, Election of 2024, Series 2026 & 2026 GO Refunding Bonds
2026 Bond Anticipation Notes | Measure H
```

Parsing that is inference, on 0.87% of the corpus.

### 2.3 Issuance → spending: the fund ledger has no bond dimension

**This is the break that cannot be worked around, because it is inside
the site's own data.**

SACS FY2024-25, Fund 21 (Building Fund — where bond proceeds are spent)
and Fund 51 (Bond Interest and Redemption):

| | |
|---|---|
| Fund 21 rows | **11,438** across **593 districts** |
| Fund 51 rows | 11,047 |
| distinct resource codes in Fund 21 | **5** |
| on generic resources `9010` + `0000` | **11,264 (98.5%)** |
| Goal code `0000` (undefined) | **10,938 (95.6%)** |

There is no measure code, no issuance code, no project code. **A
district's entire bond programme is one undifferentiated pot.**

### 2.4 And most districts have more than one authorisation in that pot

Of the 764 K-12 issuers naming any election year in CDIAC, **542
(70.9%) name two or more distinct elections.** 320 name three or more;
153 name four or more.

Traced end to end, FY2024-25:

| district | Fund 21 spending | rows | resources | distinct elections in CDIAC |
|---|---|---|---|---|
| **Sacramento City Unified** | **$261,533,707** | 43 | `9010`, `0000` | **5** — 1999, 2002, 2012, 2020, 2024 |
| Long Beach Unified | $242,403,359 | 36 | `9010` | 4 — 1999, 2008, 2016, 2022 |
| Santa Clara Unified | $38,892,283 | 31 | `9010`, `0000` | 5 — 1997, 2004, 2010, 2014, 2018 |

Clovis Unified and East Side Union High each name **eight**.

Sacramento City Unified spent **$261.5 million** from Fund 21 last year
against **five separate voter authorisations**. Nothing in the data
says how much served which. Any split would be ours.

**That is the answer to the brief's decisive question, and it is no.**

---

## 3. What the site already has

**Less than the brief assumed, and the gap is exactly the bond funds.**

- **K-12 is Fund 01 only.** The layer reads the General Fund; Funds 21
  and 51 are entirely outside it. The site currently publishes **no**
  school bond spending at all.
- **Cities and counties** carry *Debt Service* and *Capital Outlay* as
  visible functions on the SCO crosswalk — real money, correctly
  scoped, but with **no bond identity**: nothing ties a debt-service
  dollar to an issue, let alone to a measure.
- **V22 already refused all five debt sources**, including K-12 bonds,
  on the finding that SACS object 9661 has zero rows in all nine years.
  V25 does not disturb that; it adds that the *spending* side has no
  measure dimension either.

So building this would mean standing up bond funds as a new layer **and**
inventing the joins in §2. Two large pieces of new surface, both
resting on inference.

---

## 4. The traps, measured

**Refunding — the largest and the least visible.** 3,349 of 20,253 K-12
issues (16.5%) carry a refunding amount, totalling **$84,869,348,767 of
$315,801,612,102 principal — 26.9%.** Post-2017 it is **31.1%**. More
than a quarter of "bonds issued" is refinancing existing debt, not new
money for projects. A total that does not net it out overstates what
voters funded by a third.

**Authorised but unissued — the gap is most of the money.** 2024's
passed measures authorise **at least $42,418,905,000** (from the 188
with a cleanly parseable amount — so the true figure is higher). CDIAC
issues naming a 2024 election total **$11,430,358,438**. That is **at
most 26.9% issued**, roughly eighteen months on. Districts issue in
series over a decade or more. A page showing authorised money as though
it were available or spent would be wrong by a factor of four; a page
showing issued money as the measure's size would understate it as badly.

**Failed and re-run measures.** **84 of 340** 2024 school measures
(24.7%) failed. A failed measure leaves no trace in any issuance or
accounting record — it exists only in CEDA. A layer built from CDIAC
would silently show only winners, which misrepresents what districts
asked for.

**Multi-purpose measures — this is the norm, not an edge case.** Ballot
text names a **median of 4 distinct purposes**, up to 8. A typical one:

> "…fix deteriorating roofs, plumbing and electrical; build additional
> classrooms/school facilities to relieve overcrowding and support
> student achievement in science, technology, engineering, arts/math…"

There is no allocation across those purposes anywhere — not on the
ballot, not in CDIAC, not in SACS.

**Campaign language versus accounting category — the two vocabularies do
not meet.** Only **48 of 340** measures use any accounting vocabulary at
all. Meanwhile the accounting side collapses everything:

| object | FY2024-25 Fund 21 | share |
|---|---|---|
| **6200 Buildings and Improvement of Buildings** | **$7,392,099,648** | **84.6%** |
| 6170 Land improvement | $374,706,210 | 4.3% |
| 5800 Professional/consulting services | $313,099,815 | 3.6% |
| 6400 Equipment | $301,340,414 | 3.4% |
| 6100 Land | $152,874,184 | 1.7% |
| *(15 further objects)* | | 2.4% |
| **total** | **$8,740,953,847** | |

**The ballot promised four things; the ledger records one line.**
"Leaky roofs", "earthquake safety", "science labs" and "accessibility"
are all object 6200. The distinction voters were asked to approve is
not merely hard to trace — **it does not exist in the accounting.**

**The ADTR does not rescue this.** CDIAC's Annual Debt Transparency
Report columns look promising and are not. Overall **81.2%** of K-12
issues are `N/A`. Even restricted to issues sold 2017 and later, where
SB 1029 applies: **63.6% Pending, 15.2% Ended, 6.0% Past Due, and only
12.9% Filed.** And the reported quantity is **proceeds *unspent*** —
there is no spent-by-purpose, no project and no measure column. It
tells you what is left, never what it bought.

---

## 5. What survives — and why the tempting answer is the harmful one

Taken one at a time, several facts are individually sound:

- CEDA's record of a measure — district, letter, date, outcome,
  authorised amount — is a published fact.
- SACS Fund 21 spending per district is a filed fact.
- CDIAC issuance per district is a filed fact.

**The temptation is to put them on one record.** A district page reading:
*passed Measure H in 2024 authorising $451.6M for classrooms, roofs and
science labs — spent $261.5M from its building fund last year.* Every
number there is true and sourced.

**It is still the misleading version, and the brief names why:
adjacency implies reconciliation.** A reader seeing a purpose beside a
figure will take the figure as the measure's spending on that purpose.
It is not, and the measurements say so precisely:

- **the $261.5M serves five authorisations**, not Measure H (§2.4)
- **84.6% of it is one object code** while the measure named four
  purposes (§4)
- **26.9% of issuance statewide is refunding** (§4)
- **the two records cannot even be joined** without a name match that
  merges 179 real districts (§2.1)

None of that is fixable by a caption. A label saying *these figures are
not reconciled to each other* sits directly beneath a layout whose
entire visual grammar asserts that they are. The site has refused this
shape before — V21 §4 refused a surplus because two flows on different
scopes must not be subtracted; V24 refused the reserve ratio; V24a
refused a deficit figure beside spending **specifically because
adjacency invites the division.** This is the same refusal, and the
adjacency here is stronger, because a purpose is a *claim about what the
money did.*

There is no gated version: no published control reconciles any measure
to any spending, and none could, since the quantity does not exist.
There is no honest as-filed version either — as-filed labels an
unreconciled *figure*, and what is unreconciled here is the
*relationship*, which a tier label cannot mark.

The one thing that could be published honestly is **a measure record
with no spending on it at all** — what was on the ballot, what it
authorised, whether it passed. Even that requires the §2.1 name join to
reach a district record, which is the join that merges Porterville's
three districts. **It fails on the same defect, at the door.**

---

## 6. What I did not do

- I parsed the CEDA 2024 PDF only. 1995–2025 exist; the Excel
  distribution was not retrieved (the CSU DSpace handle returned 403 and
  the CSUS project page 404), so the format claim rests on the SOS
  description plus the PDFs I read.
- I did not contact the 58 county elections offices. §2.1 fails on the
  statewide record; a county-by-county key, if one exists, would not
  repair §2.3, which is the fatal link.
- The 26.9% issued figure in §4 uses the 188 measures with a cleanly
  parseable amount out of 256 passed. The denominator is understated, so
  the true issued share is **lower** than 26.9%.
- I did not test community college measures separately, though CEDA
  carries them; the SACS argument in §2.3 is K-12-specific and CCC's
  fund structure was not examined.
- The purpose count in §4 splits ballot text on semicolons. The
  103 measures counted as single-purpose are likely a parsing artifact
  of measures that use commas; the median of 4 is the robust figure.

## Recommendation

**Don't ship.** Not a gated layer, not an as-filed layer, not a measure
record attached to a district page.

The honest one-line summary: **California publishes what voters
approved and publishes what districts spent, and there is no identifier
anywhere between them — so any page placing the two side by side would
be making the connection itself, in a medium where placement is a
claim.**
