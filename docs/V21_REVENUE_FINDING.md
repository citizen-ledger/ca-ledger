# V21 finding: the revenue layer — what can be published honestly

_Investigated 2026-07-24. No UI was built; this document is the
deliverable. The site today shows only spending. This asks what the
other half of the ledger — what each government collected, and from
what — can be published to the standard the rest of the record holds._

## Recommendation, up front

**Revenue is more publishable than expected.** Unlike the vendor and
recipient investigations ([V4](V4_VENDOR_FINDING.md),
[V16](V16_RECIPIENT_FINDING.md), [V16a](V16A_LA_RECIPIENT_FINDING.md)),
where the data existed and the control total did not, revenue has
**published control totals at almost every layer**, and they reconcile —
in the flagship case, exactly, 10,515 times out of 10,515.

| Layer | Tier | Honest tier name |
|---|---|---|
| **Cities** | **(a) gated** | reconciled to the cent — 10,515 city-years, 0 fail |
| **Counties** | **(a) gated** | reconciled to the cent — 1,251 county-years, 0 fail |
| **Community colleges** | **(a) gated** | reconciled to the dollar, **General Fund only** |
| **State** | **(a) gated** | exact in thousands, **statewide by source — no entity axis** |
| **K-12** | **(a) county/statewide + (b) per district** | two labels on one page, never one |
| **Special districts** | **(b) as-filed** for v1 | a real control exists but is not yet earned — §2.5 |
| **UC** | **(b) systemwide only**, or defer | campus revenue is source-labelled *Unaudited* |
| **CSU** | **(c) don't ship** | no endpoint reached, no control identified |
| **Property tax split (BOE Table 14/15)** | **(a) as its own page** | exact as published — must **not** validate per-entity property tax |

**But the gate certifies arithmetic, and on revenue the gap between
arithmetic and meaning is far wider than on spending.** That is the
finding's real content, and the reason this document spends more space
on caveats than on the gate. Irvine's FY2023 revenue reconciles to the
Controller's published total **to the dollar** — and 50.7% of it is a
single line labelled the same way other cities label small donations.
Shipping revenue under the site's existing "reconciled" vocabulary
would silently transfer credibility the spending layer earned onto
figures the source refuses to explain. Any build must carry the
mitigations in §6, and must qualify the word *reconciled* in the same
sentence it appears.

---

## 1. What exists, and at what depth

### Cities and counties — already fetched, already partly shipped

A framing correction first: the brief says the pipelines fetch revenue
and "discard it." They do not. `city-data.js` **already ships**
`revenues` and `enterprise.revenues` per city-year (los-angeles
2023-24: `revenues` 10596.697, `enterprise.revenues` 11015.795), and
the county pipeline computes `meta.intergovernmental` from the same
data. What is discarded is the **category breakdown**. That is the
actual question, and it is a smaller and more tractable one.

**City revenue** (`rrtv-rsj9`), FY2023 statewide, 20 categories:
Taxes $43.92B · Electric Enterprise $10.10B · Water Enterprise $8.07B ·
Charges for Current Services $6.77B · Internal Service Fund $6.57B ·
Sewer Enterprise $5.67B · Intergovernmental–Federal/County/Other $5.42B ·
Intergovernmental–State $5.16B · Airport Enterprise $4.24B ·
Miscellaneous $3.60B · Other Enterprise $3.00B · Fines/Forfeitures
$2.83B · Harbor & Port $1.74B · Solid Waste $1.64B · Hospital $1.45B ·
Special Benefit Assessments $1.35B · Licenses & Permits $1.31B · Transit
$1.05B · Gas $0.32B · Conduit Financing $0.

Depth runs `category → subcategory_1..4 → line_description`, and the
real detail is at `line_description`. Under Taxes, `subcategory_1`
splits only two ways, but the line level resolves properly: FY2024
Secured and Unsecured Property Taxes $10.56B, Sales and Use $9.40B,
Property Tax In-Lieu of VLF $4.65B, Transient Occupancy $2.95B,
Business License $2.81B, Utility Users $2.29B, Franchises $1.69B.
**Property tax is isolable** — seven distinct lines totalling $19.33B,
43.3% of the Taxes category.

**County revenue** (`emxv-k8xv`), FY2024, total $130.00B:
Intergovernmental–State $37.55B (28.9%) · **Property Taxes $26.83B**
(20.6%, its own category, unlike cities) · Intergovernmental–Federal
$17.83B (13.7%) · Hospital Enterprise $13.13B · Charges for Services
$10.34B · Internal Service Fund $7.62B · and eight smaller.

Window FY2003–FY2024 (22 years) for both; the site ships FY2017–FY2024.

> **A schema divergence that StrictRow exists to catch.** The city
> revenue value column is `value`; the county's is **`values`**. A
> loose reader sums nothing and reports zero. It broke my first run,
> and returned a real Socrata error (`no-such-column`) rather than an
> empty result — caught by reading content, not status.

### Special districts

`nkv3-m73r`, FY2024 total $106.08B across 4,726 filing entities,
FY2003–FY2024. Categories are **fund-type buckets, not revenue-source
buckets** — there is no `Taxes` category as cities have; district taxes
sit under fund categories and resolve at `line_description`, where
property tax is actually *cleaner* than for cities (named statutory
lines: Current Secured and Unsecured (1%), Voter-Approved Taxes,
Tax Increment, Parcel Tax, Property Assessments). Districts have **no
resident denominator** — the existing expenditure pipeline deliberately
omits population for this reason, and revenue must do the same.

### K-12

CDE SACS unaudited actuals, table `UserGL` — the **deepest source on
the site**: every dollar at the full account string (LEA × school ×
fund × resource × goal × function × object). FY2024-25 = 1,600,940 GL
rows, statewide objects 8000–8799 = **$148,513,435,857.19** across
1,044 LEAs: LCFF sources $78.79B, other local $31.95B, other state
$26.25B, federal $11.52B. Nine complete years FY2016-17…FY2024-25 —
**exactly the window the K-12 expenditure layer already ships**, so
revenue adds no new year seam.

### Community colleges

*Not in the brief, and nearly missed.* The CCFS-311 portal's
`StatewideReportDropdown` — which the existing CCC pipeline already
drives with value `40` — also carries **`37` = "Table IV.1 Summary of
General Fund Revenues"** and `38` = "Table IV.2 General Fund Revenue by
Source", **16 fiscal years (2009-10…2024-25)**, per district plus a
printed `Statewide` row. FY2022-23 statewide: Federal $1,077,664,338 /
State $7,684,000,804 / Local $5,374,648,142 / Total $14,136,313,284.

### State

The enacted budget is appropriations, not revenue — correct. But DOF
publishes **Schedule 8, "Comparative Statement of Revenues"**
(`BS_SCH8.pdf` in every eBudget publication), with seven sections and
143 coded revenue lines. FY2023-24 actual, $ thousands: Major Taxes and
Licenses 229,598,163 · Regulatory 14,009,542 · Miscellaneous 25,219,993 ·
Investment Income 4,694,066 · Revenue from Local Agencies 1,232,953 ·
Services to the Public 742,752 · Use of Property and Money 313,308.
Largest lines: Personal Income Tax $117.95B, Corporation Tax $35.46B,
Retail Sales and Use $34.61B.

**Ten complete actual years, FY2015-16…FY2024-25, gap-free** — and
notably this **includes FY2020-21, the year the site had to drop for
expenditure actuals** because Schedule 9 would not reconcile. The
revenue window is one year longer than the spending window.

Three limits are properties of the source and must be stated, not
engineered around:

- **No entity axis.** Schedule 8 is organised by revenue *source*
  statewide. There is no per-department revenue anywhere, so this layer
  **cannot mirror the spending layer's department drill-down**.
- **No federal funds.** Revenue is General + Special only; the spending
  side includes federal and bond funds.
- **PDF only.** The eBudget JSON API that powers the spending layer has
  no revenue endpoint — `/revenue`, `/revenues`, `/rev` return honest
  JSON 404s with real error bodies while `/appInfo` and `/statistics`
  return 200 with real payloads, so the absence is genuine, not a bot
  block.

---

## 2. The gate, tested empirically

The test replicates the shipped expenditure gate exactly
([fetch_city_data.py:489](../pipeline/fetch_city_data.py):489) —
`ours = sum(all categories)`, fail if
`abs(ours − official) > max($1000, official × 0.001)`.

### 2.1 Cities and counties — exact, and the strongest gate on the site

| Window | City-years | Exact | Fail | County-years | Exact | Fail |
|---|---:|---:|---:|---:|---:|---:|
| FY2017–FY2024 (shipped) | 3,853 | 3,853 | **0** | 453 | 453 | **0** |
| FY2003–FY2024 (full control) | 10,515 | 10,515 | **0** | 1,251 | 1,251 | **0** |

Worst drift **$0.00**. Not "within tolerance" — exact, tighter than the
expenditure gate's own tolerance, with zero orphans in either direction.
The controls are `ky7j-fsk5.total_revenues` and
`da2q-agh9.total_revenues`, the exact analogues of the expenditure
controls the site already gates against.

Testing the control's scope: reconciling **governmental-only** figures
against it passes just 11.9% (cities) and 0.9% (counties), so the
published control is **all-funds, including enterprise** — the same
shape as `total_expenditures`.

### 2.2 State — zero residual, four independent controls

Ten years, four gates, residual **exactly zero** (zero in thousands
against Schedules 8 and 1; zero in millions against Schedule 6). This
is a *stronger* control structure than the expenditure layer, which has
one cross-document tie; revenue has three. I verified the anchor
myself: `BS_SCH8.pdf` (456,380 bytes, %PDF-1.7) line 401 reads
`TOTALS, REVENUES $195,261,190 $80,549,587 $275,810,777`, and the
internal footing holds under my own arithmetic —
majors $229,598,163 + minors $46,212,614 = **$275,810,777** exactly.

Two gaps a skeptic should know: Gate 3 returned "no-row" for one of ten
years (a parser-locator gap on a changed Schedule 1 layout, covered by
the other three gates and confirmed by hand), and mutation testing was
run on **one** year, not ten. Both are build tasks, not source defects.

**Only the "Actuals" column may ever be published.** The two "Estimated"
columns in the same table are forecasts that move enormously: FY2022-23
General Fund went 219,707 → 205,134 → 178,557 actual ($M), a **−$41.2B
(−18.7%)** revision.

### 2.3 Community colleges — exact to the dollar

Seven of sixteen years tested; every one reconciles the recomputed
district rows to the printed `Statewide` row with **$0 residual on all
four columns** (Federal / State / Local / Total), and fed+state+local =
total holds for every district row in every year tested. Same gate
mechanism as the shipped Table VI expenditure gate. **Scope caveat:
General Fund only** — other-fund revenue lives in per-district reports
that were not fetched.

### 2.4 K-12 — a genuine split tier, and it must be labelled as two things

**Gate that passes:** raw `UserGL` recomputed against CDE's own
`UserGL_Totals` — zero disagreements, to the cent.

> **Correction (2026-07-25, during the build).** The cell count first
> published here, *63,811*, does not reproduce and its provenance is not
> recoverable. Re-measured from the cached databases: the **revenue-only**
> control (objects 8000–8799) is **64,811 cells across nine years** —
> 61,839 county and 2,972 statewide — with **zero disagreements** and a
> worst residual of **$0.0000687**, a float-accumulation artifact that
> lands in every year on the statewide Fund 01 cell, the cell with the
> most summands. The **all-object** control is **356,484 cells**, not
> 63,811. No object-range variant, with or without a nonzero filter,
> produces the original figure. The shipped layer uses the measured
> numbers, which it recomputes on every run rather than quoting.

**But `UserGL_Totals` contains only 58 county keys plus one state key.
No district row exists in it.**

**Gate that fails:** the Principal Apportionment LCFF Summary tested as
a per-district control — 987 districts, SACS 8000–8099 vs published
Total LCFF Entitlement: **5 exact (0.5%)**, 110 within $1,000 (11.1%),
269 within 0.1% (27.3%); statewide $69.60B published vs $77.98B ledger,
**+12.03%**. A recertified entitlement is simply a different quantity
from a district's closed accrual.

I verified the pivot myself: **Current Expense of Education — the
workbook that gates K-12 expenditures to the cent per district — has no
revenue column on any of its three sheets** (District 7 cols, County 5,
Statewide 4). There is no per-district revenue control.

So K-12 revenue is **reconciled to the cent at statewide and county
scope, and as-filed at the district**. The district figure is
recomputed from the raw ledger and structurally guaranteed to sum into
a published county control, but is never independently confirmed at the
district itself. Since the district table is what a reader actually
sees, **publishing it under a single "reconciled" headline is precisely
what the reconciliation discipline exists to prevent.** Two labels, one
page.

The one per-LEA publication carrying a TOTAL REVENUES line — the SACS
Data Viewer — starts FY2022-23 (three of nine years) and sits behind an
active Cloudflare Turnstile. It was correctly not circumvented, and is
not a usable gate target for a no-server pipeline.

### 2.5 Special districts — a real control, not yet earned

The direct analogue of `ky7j-fsk5` does not exist: the full SCO catalog
(170 datasets) contains exactly four per-capita/totals datasets, all
city or county.

**But a previously unused control does exist**, and I verified it
myself rather than take it on report. SCO publishes the raw Financial
Transactions Report workbooks as Socrata *blobby* views. I resolved
`dp5e-7wm8` → blobId, downloaded **25,966,124 bytes** (magic `504b`,
"Microsoft Excel 2007+" — note `/files/latest` returns a JSON 404, a
textbook soft-404), and found sheet `16 SD_GOV_FUNDS_REV_EXP`, 442
columns, **col 201 = `Total Revenues_Total Governmental Funds`** — the
filer's own declared total. Reconciling Socrata line items against it:

- **FY2023: 3,183 entity-years matched, 3,183 exact to the cent
  (100.000%)** — $25,259,723,281 = $25,259,723,281.
- FY2024: 3,159 matched, 3,158 exact (99.968%), zero gate failures, one
  $3 near-miss.

**And yet the honest v1 tier is (b) as-filed**, for three reasons that
survive that result:

1. **The control is per-statement, never per-entity.** SCO publishes a
   governmental-funds total and, separately, each proprietary fund's
   operating and nonoperating totals. It publishes **no all-funds
   district total**. Any headline "district X took in $Y" would be the
   Ledger's own addition of separately-gated components — a materially
   weaker claim than the city layer's single published `total_revenues`.
2. **Entity matching is by name, with no shared key.** The blobs carry
   an Entity ID the Socrata table does not expose. My own reconciliation
   matched on normalised name — which means a name crosswalk can
   silently pass on the *wrong* entity, the exact failure mode
   [fetch_district_data.py](../pipeline/fetch_district_data.py) already
   records for Rural North Vacaville Water District.
3. **The handful of hard fails were attributed to vintage-revision
   drift, and nobody re-fetched a newer vintage to prove it.** That is
   an inference presented as a diagnosis.

Add that the control lives in ~103 MB of xlsx across six vintages whose
sheet and column names drift (a per-vintage declaration table is
mandatory, exactly the CCC Exhibit C pattern), and the responsible call
is: **ship as-filed, with a documented path to (a)** once entity keying
and per-vintage declarations are proven.

> **Spin-off, out of scope here and worth its own investigation.** The
> same sheet carries **col 285, `Total Expenditures_Total Governmental
> Funds`**. The site's special-district *expenditure* layer ships
> as-filed today because no control was known. This control may gate it
> too — meaning an already-shipped layer may be **under-claiming** its
> tier. Untested; flagged, not asserted.
>
> **Tested, 2026-07-25 — and the answer is no.** The layer stays
> as-filed. Only the `gov` bucket has a control whose unit is the same
> object; for `ent`, `isf` and `cf` the Controller publishes operating
> and nonoperating components and never their sum, so "reconciling"
> them means confirming our own arithmetic. Worse, the `cf` bucket
> reconciles 14/14 **only because** the site's bucket is
> conduit-financing-only while SCO separately declares
> **$798,570,859** of fiduciary-fund activity that the Socrata feed
> publishes nowhere — a gate there would have been drawn around the
> hole. What was corrected instead is the claim: "no control-total
> dataset exists" was false, and is now stated as the measured limit
> everywhere it appeared (74 occurrences, 17 files). See docs/OPEN.md
> 2i–2k.

---

## 3. The comparability traps

### 3.1 Enterprise (ratepayer) revenue — the same separation, and it matters more

Enterprise is **32.8%** of city revenue statewide (FY2024, $39.76B of
$121.22B). Per city it is far more skewed: Santa Clara **72.7%**,
Riverside 58.4%, Los Angeles 51.0%, Redding 50.8%, Palo Alto 50.2%,
Roseville 50.1%. **26 of 482 cities take more than half their revenue
from enterprise funds.** Special districts are worse — the majority of
their $106B is enterprise (water, electric, hospital, transit).

A city that runs its own utility looks vastly richer unless enterprise
is separated exactly as the expenditure side already separates it. The
control total includes enterprise, so the gate **cannot** do this
separation — the pipeline must, and the classification must be visible.

### 3.2 Intergovernmental transfers — the largest double-count on the site

This is the never-sum problem in its sharpest form: **the same dollar
literally appears as one government's spending and another's revenue.**

- **Counties, FY2023:** Intergovernmental–State $34,641,662,056 +
  Federal $17,089,337,518 = **$51.73B, 42.7% of $121.18B**. County
  "revenue" is largely not county-raised revenue. (FY2024: $56.23B,
  43.3% of $130.00B.)
- **K-12, FY2024-25:** state aid + EPA + other state = **$75.84B,
  51.1%** of $148.51B — already counted as appropriations in the state
  layer. Federal adds $11.52B.
- **Community colleges, FY2022-23:** the State column is **$7.68B of
  $14.14B (54.4%)** — the same Prop 98 money the state layer shows.
- **Cities:** $10.46B (FY2024), 8.6% — smaller, and it spiked to 10.9%
  in FY2022 on federal COVID aid.
- **State → local, measured from the state side:** realignment sales
  tax alone is **$14,060,139K** (2011 $9.31B + 1991 $4.75B) — state
  revenue remitted to counties and reappearing as county revenue.

There is also double-counting **inside** layers, which the gate cannot
see because it is inside the control:

- **Cities: Internal Service Fund revenue $6,574,649,520 (5.8% of
  FY2023)** — money a city charges its own departments. Counties:
  $6,892,175,554 (5.7%).
- **K-12: ~$4.7B/yr of LEA-to-LEA circulation** — pass-through
  $1.13B, inter-LEA transfers $3.52B, and object 8096 (in-lieu-of-
  property-tax to charters) sitting at **−$1.13B** at the paying
  district and positive at the charter.
- **Special districts: JPAs are 41.8%** of the total ($39.80B of
  $95.22B FY2023), funded by contributions from member cities and
  counties already counted at the member; self-insurance member
  contributions alone are $8.44B.

### 3.3 Property tax — where I was wrong, and what is actually true

The brief states that because all four layers receive shares of the
same levy, "summing revenue across layers double-counts massively." I
tested that rather than repeating it, and my own provisional reasoning
was **half right and half wrong** — so both halves are recorded here.

**What is true:** the levy *is* a partition. The Board of Equalization
publishes the four-way split (Table 14/15, an OData endpoint, 58
counties × 13 years). FY2022-23: City $11.083B, County $12.669B,
School (K-14) $47.617B, Other Districts $17.653B, **Total $89.022B** —
and the parts sum to the total to within **$12,000 on $89.0B**. Each
dollar is allocated to exactly one government. So in principle,
summing shares reproduces the levy once, not a multiple of it. My
provisional arithmetic (~$88.5B across layers vs a ~$90–100B levy) was
consistent with that.

**What I got wrong:** the site's layers do **not** reproduce that
partition. What SCO reports, against BOE's control for the same three
layers, FY2022-23:

| Layer | SCO reports | BOE control | Ratio |
|---|---:|---:|---:|
| Cities | $17.568B | $11.083B | **1.59×** |
| Counties | $25.104B | $12.669B | **1.98×** |
| Special districts | $8.968B | $17.653B | **0.51×** |
| **Sum of three** | **$51.640B** | **$41.405B** | **1.247× (+24.7%)** |

**Almost the entire $10.2B gap is one item: Property Tax In-Lieu of
VLF, $10.640B** (cities $4.373B + counties $6.267B). It is ERAF-funded,
and BOE books it in the *School* column while cities and counties book
it as their own property tax. My provisional note that this is "a state
backfill, not the 1% levy" was right, and it turns out to be the whole
crux. Two smaller items follow: RDA dissolution pass-through and
residual (ABX1 26) $3.346B, and $2.219B of "less-than-countywide"
revenue booked in the county file that belongs to dependent districts.

And the errors **do not cancel — they compound**: cities and counties
run 1.59× and 1.98× *over*, districts 0.51× *under*.

Per entity it is worse than the statewide ratio suggests. The VLF swap
is a **median 35.7%** of what a city calls its property tax (quartiles
25.0 / 35.8 / 50.3%, **maximum 99.4%** — at least one city's entire
reported "property tax" is the swap, not its AB 8 share).

**What this permits.** The components are separable *exactly*, by
string match on a populated `line_description`: the VLF swap, the RDA
pass-through/residual, the dependent-district lines, and the AB 8 share
itself. So a build can publish the AB 8 share as the levy share and the
VLF swap as its own labelled line, never added by the UI. But a
reconstructed property-tax figure **fails the site's own standard by a
wide margin** — cities 4.2% off (42× tolerance), counties 9.7% (97×),
districts hopeless — and that residual is itself unexplained, which
means the classification is unproven, not merely incomplete. Per-entity
property tax is therefore **pinned, not reconciled**, weaker than the
city/county expenditure tier.

Two further hard limits: BOE's control is **per county only** (there is
no published per-city or per-district allocation), and BOE publishes a
**single combined K-14 School column** that cannot be split — so
neither `schools.html` nor `ccc.html` can ever be gated against it.

**The clean product here is BOE Table 14/15 itself**, shipped as its
own "where the property tax goes" page: internally exact, the source's
own figure, no reconstruction. It must never be presented as validating
the per-entity property-tax numbers.

### 3.4 One-time vs recurring — not separable, and it actively impersonates

This is the trap that most threatens the layer's honesty, and the
answer is unambiguous: **one-time revenue cannot be identified.**

The only explicitly one-time-labelled line, "Gain on Disposal of Capital
Assets," is **$88.79M — 0.078%** of city revenue (FY2023), exists only
in enterprise funds, and reports a net accounting gain rather than
proceeds. Meanwhile the unresolvable "(Specify)" buckets hold
**$27.78B — 11.80% of all city and county revenue** (I verified:
cities 13.83%, counties 9.88%). The opaque bucket is **313× larger**
than the labelled one.

I verified the decisive mechanism myself. On Indio's $135,567,319 row,
`subcategory_2`, `subcategory_3`, `subcategory_4` and `line_description`
are all the **identical string**, "Other Miscellaneous Revenues
(Specify)_General Revenues". **The four-level hierarchy is not four
levels of detail — it terminates at the label it started with.** SCO's
form asks filers to specify; SCO publishes the label and never the
answer. There is no deeper field to appeal to.

Bond proceeds, governmental-fund asset-sale proceeds and transfers-in
are not merely unlabelled — **the rows do not exist**. Both datasets
carry `type = "Revenues"` and nothing else. That is an absence, not a
labelling gap, and no filter recovers it.

The entity-level damage is severe, and it does not merely hide — it
misleads in the opposite direction:

- **Irvine FY2023**: $429.2M → **$918.8M** → $723.7M. One line,
  +$465.6M "Contributions from Nongovernmental Sources" — **50.7% of
  the year** — under the same label other cities use for small
  donations. It reconciles to `total_revenues` to the dollar
  ($918,762,465).
- **Indio FY2023**: 40.2% of the year in one "(Specify)" line.
- **Carson FY2023**: +$66.5M filed **inside `category='Taxes'`**, so in
  a category view — exactly how the site renders spending today —
  Carson reads as a city whose tax revenue jumped 39%. A reader draws
  the precise opposite of the correct conclusion.

And **non-filing is encoded as literal `0`** in the control datasets
(Hollister FY2022, Novato FY2022, Woodland FY2023; Humboldt FY2020–21,
Mendocino FY2022). A naive port would gate against zero and render a
revenue collapse. "Not published is never zero" applies here literally;
`fetch_city_data.py` already has the right guard at `official[key] > 0`.

---

## 4. Does revenue unlock a surplus or deficit? No — on every layer

Revenue minus expenditure must not be published, computed, or implied —
not as surplus, deficit, balance, "net", or two bars placed side by
side. The scopes are asymmetric on every layer, for different reasons:

- **Cities/counties**: revenue excludes bond proceeds and other
  financing sources entirely, while expenditure **includes** the Capital
  Outlay ($7.220B) and Debt Service ($3.370B) those proceeds fund —
  9.9% of city expenditures. The difference is structurally biased
  toward a fictitious deficit for any entity in a bond-funded capital
  cycle. Measured: 74.3% of city-years show a "surplus", 25.7% a
  "deficit", with extremes at Monrovia FY2018 **−146%** and El Segundo
  FY2021 −136%. The district workbook confirms this from the source
  side, reporting "Other Financing Sources (Uses)" and "Special and
  Extraordinary Items" as blocks **separate from** Total Revenues.
- **K-12**: revenue gates at county scope, expenditure at district
  scope — and Current Expense of Education is an exclusion-adjusted
  subset, not total expenditure. Two different denominators.
- **CCC**: revenue is total General Fund; the shipped expenditure figure
  is CEE after ECS 84362 exclusions. The difference has no referent.
- **State**: revenue is General + Special ($275.811B FY2023-24);
  spending includes Bond and **Federal** ($303.246B). The ~$27B gap is
  **scope, not shortfall**.

The honest sentence: *"Revenue and spending on this site are measured on
different scopes and do not net. We do not publish a surplus or deficit
and a reader should not compute one."*

---

## 5. Payload, measured

Adding revenue categories to `city-data.js`, using **real values** and
shipping only nonzero categories:

| | raw | gzip |
|---|---:|---:|
| today | 3,143.9 KB | **767.2 KB** |
| with `revByCategory` | 3,754.4 KB | **943.9 KB** |
| **growth** | **+610.5 KB (+19%)** | **+176.7 KB (+23.0%)** |

Nonzero categories per city-year: min 0, **median 11**, max 16 (40,828
real cells, against 77,120 if all 20 shipped including zeros — most
cities have no airport, harbour, hospital or gas fund).

A first simulation using a constant value reported only +4% gzipped;
that was an artifact of unrealistic compressibility, and is recorded
here because it is exactly the kind of measurement that flatters a
build. The real cost is **+23%**, and `county-data.js` (250.8 KB
gzipped today) would grow comparably.

---

## 6. If a revenue layer is built, these ship with it

Not after it. The gate is real, and it certifies a narrower claim than
readers will assume; these are what close the gap.

1. **An unexplained-share indicator**, per entity-year: the share of
   revenue sitting in "(Specify)" and named-but-ambiguous lines,
   rendered on the figure itself. Irvine FY2023 ≈ 51%, Indio ≈ 40%,
   Carson ≈ 26%, statewide 11.8%. Fully derivable from published
   fields. Presented as *unexplained share* — **never** as an estimate
   of one-time revenue.
2. **No growth rates, trend arrows, or CAGRs on revenue** — or gate
   them behind the indicator so a high-unexplained-share year renders
   no trend claim.
3. **Gaps, never zeros**, for non-filing years.
4. **Enterprise separated** from governmental, as the expenditure side
   already does.
5. **The word "reconciled" qualified in the same sentence it appears**:
   *reconciled means the arithmetic matches the source's own total, not
   that the revenue is recurring.*
6. **Never-sum statements per layer**, each naming its own largest
   overlap: counties 42.7% intergovernmental; K-12 51.1% state money
   plus $4.7B/yr internal circulation; CCC 54.4% state; districts 41.8%
   JPA recirculation; cities 5.8% internal service fund; state excludes
   federal entirely. **And property tax never summed across layers** —
   $51.640B reported against a $41.405B control for the same three
   layers.

---

## 7. What I did not do, and what remains unverified

- **CSU revenue was never probed** — no endpoint reached, no control
  identified. That alone is why it is (c), and the (c) is provisional
  on a probe, not a finding that nothing exists.
- **UC revenue was read from a cached PDF, not fetched live.** Only a
  systemwide total was established; per-campus revenue appears solely
  under "Campus Facts in Brief **(Unaudited)**" — the source disclaims
  it itself.
- **CCC**: 7 of 16 available years gate-tested; per-district all-funds
  reports never fetched, so the General-Fund-only caveat is a real
  scope limit, not a formality.
- **Special districts**: the FY2003–FY2016 blob was not tested; the
  vintage-drift diagnosis for the handful of failures was not proven by
  re-fetch; and the expenditure-side spin-off (col 285) was not run.
- **State**: one of ten years has a gate that did not execute, and
  mutation testing covered one year.
- **Property tax**: the residual after stripping the VLF swap (cities
  4.2%, counties 9.7%) is **unexplained**, which makes the
  classification unproven rather than merely incomplete.
- **Numbers I decline to repeat**: a "rough floor" of $40–55B for
  special-district overlap was offered without a shown computation. It
  is not carried into this finding's conclusions.

---

## Recommendation

**Ship revenue, layer by layer, at the tier each layer earns — and
never under one label.** Cities, counties, community colleges and the
state are **(a) gated**, with the state's zero-residual, four-control
structure the strongest and its no-entity-axis limit the most
restrictive. K-12 is **two tiers on one page**: reconciled to the cent
at county and statewide scope, as-filed at the district, because the
district row a reader sees has no published control. Special districts
are **(b) as-filed for v1**, with a real and verified control that is
not yet earned — per-statement rather than per-entity, matched by name
without a shared key. UC is **systemwide-only or deferred**; CSU is
**(c)** pending a probe. The BOE property-tax split is **(a) as its own
page**, and must never be presented as validating per-entity property
tax.

The single most important sentence for whoever builds this: **the
reconciliation gate checks arithmetic, not economic substance.** On
spending, those two ran close together. On revenue they do not — 11.8%
of local revenue sits in lines the source declines to explain, and a
year can reconcile to the dollar while half of it is a windfall wearing
the label of a routine donation. A layer that ships the gate without
the mitigations in §6 would be accurate in every figure and misleading
in every reading, which is the one failure mode this record exists to
avoid.
