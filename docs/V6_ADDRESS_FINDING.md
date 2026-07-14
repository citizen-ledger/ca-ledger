# V6 finding: address lookup — "every government spending in your name"

_Investigated 2026-07-14. No UI was built; this document is the
deliverable. Every technical claim below was verified empirically on
the investigation date — CORS behavior in a real browser, geocoder
responses for real addresses, live spatial queries against BOE tax-rate
services, and SODA aggregations for the double-counting figures. The
reproducibility appendix lists every probe._

## Recommendation, up front

**(b) SHIP NARROWED.** The feature is buildable on the existing
static, no-server, no-key architecture, and the honest version is:

- Address → **city (or unincorporated county area) + county + state**,
  shown as **stacked separate records that are never summed**;
- **No special-district assignment** — the districts panel says, from
  our own data, "N districts file from {County} County; the Ledger
  cannot determine which serve this address," and links to the
  directory. Assignment is technically reachable via tax-rate-area
  services but fails our own entity-resolution rules (details in §2);
- **No "your total government cost" figure, ever.** Quantified in §4:
  53.8% of county governmental revenues are intergovernmental
  transfers, so a stacked sum would double-count roughly half the
  county figure by construction;
- An address-free **pin-drop fallback** (also the maximum-privacy
  path), because rural address matching measurably fails.

---

## 1. Geocoding — verified, with one architectural surprise

### The Census Geocoder works — but not the way we assumed

`geocoding.geo.census.gov` is free, public, keyless, and fast
(~0.5 s measured). But its CORS is an **allow-list**: the server
returns `Access-Control-Allow-Origin` only to census.gov origins
(verified: `Vary: Origin` present; ACAO absent for a github.io
origin and for localhost; present for `https://www.census.gov`).
**Plain browser `fetch()` is blocked — verified in a real browser**
("Failed to fetch").

The escape hatch is official and verified: the geocoder supports
**JSONP** (`format=jsonp&callback=…`), which a static page consumes
via a script tag, exempt from CORS. Verified end-to-end in a real
browser, including the geographies endpoint. Security note: JSONP
means executing a script served by census.gov over TLS — an
acceptable dependency (we already trust census.gov as a data source),
but it must be stated in the methodology, and the callback should be
a fixed named function, not user-influenced.

**No server and no API key are required. The architecture stands.**

### The geographies endpoint makes point-in-polygon unnecessary for city and county

One call answers everything the city/county layers need:

```
/geocoder/geographies/onelineaddress?address=…&benchmark=Public_AR_Current
  &vintage=Current_Current&layers=Counties,Incorporated Places,Census Designated Places
  &format=jsonp&callback=…
```

returns the matched address, coordinates, **county**, and **place —
with incorporated places (`FUNCSTAT: "A"`) distinguished from CDPs
(`FUNCSTAT: "S"`)**. Verified cases:

| Address | Result |
|---|---|
| 915 I St, Sacramento | `Sacramento city` (A) + Sacramento County |
| 4801 E 3rd St, Los Angeles 90022 | **no incorporated place**; `East Los Angeles CDP` (S) + LA County — correct: a "Los Angeles" mailing address that is NOT in the city |
| 1001 Emerald Bay Rd, South Lake Tahoe (city-edge) | `South Lake Tahoe city` + El Dorado County |
| 12363 Limonite Ave, Eastvale (incorporated 2010) | `Eastvale city` + Riverside County |

This is **authoritative full-resolution TIGER assignment**, which
matters because our own city polygons are Douglas-Peucker-simplified
cartographic boundaries — fine for a map, **not fine for telling a
boundary-edge household which city they live in**. Rule for the
build: the geocoder (or TIGERweb) assigns; our polygons only display.

Census place → Ledger slug crosswalk is already solved in-repo:
`pipeline/make_city_boundaries.py` name-matches all 482 SCO cities to
Census places (with aliases); the build adds place GEOIDs to that
crosswalk at generation time.

### Match-rate honesty and the pin-drop fallback

Rural coverage is real but gappy — measured: 2 of 4 well-formed rural
addresses (Markleeville, Bridgeport) returned NO MATCH. The design
needs: (i) a clear no-match state that never guesses, (ii) the
existing search picker as manual fallback, and (iii) a **pin-drop
mode** using the coordinates endpoint
(`/geocoder/geographies/coordinates?x=…&y=…`), verified to return
`Markleeville CDP` + Alpine County from bare coordinates. Pin-drop
doubles as the zero-address privacy path (§5).

### Rate limits and alternatives

No key and no published rate limit for interactive one-address
lookups (batch is a separate 10,000-address endpoint); user-triggered
volume from a static site is well within any plausible envelope.
Alternatives, assessed:

| Option | CORS | Key | Notes |
|---|---|---|---|
| Census Geocoder (JSONP) | n/a (JSONP) | none | **Chosen.** Official, verified, returns jurisdictions directly |
| TIGERweb ArcGIS REST | **open (echoes origin)** — verified | none | CORS-clean coords→place/county point query; good redundancy for the pin-drop path |
| Nominatim (OSM) | `*` — verified | none | Policy: 1 req/s, user-triggered OK with attribution, access withdrawable; acceptable as a documented fallback geocoder, not a foundation |
| Photon (komoot) | `*` — verified | none | Fair-use, no SLA; same role as Nominatim |
| Google/Mapbox/Geocodio | — | required | Keys + ToS change the architecture; not needed |

Answer to the architecture question: **nothing forces a server or a
key.**

---

## 2. Jurisdiction assignment — and the honest answer on districts

**City and county: solved** (§1) — assignment by the geocoder, not by
client point-in-polygon against simplified shapes.

**Special districts: assignment does NOT ship.** The V5 finding
(no statewide district boundary file) still holds — but this
investigation went further, because the property-tax system has its
own geography, and it deserves an honest verdict rather than a
hand-wave:

### The tax-rate-area (TRA) path — live-verified, and disqualified

BOE/CDTFA publishes, per county per roll year, **TRA polygon layers
and TRA→district tables** as public ArcGIS services (57 county
services found for the 2025 roll year, `services7.arcgis.com`,
CORS `*`). Verified end-to-end on Lake County, from the browser
architecture we'd use: a point query on Lakeport City Hall returned
TRA `001028`, whose table row lists 11 revenue districts.

That verification is also the disqualification:

1. **The names don't join to our records.** The TRA table names are
   county-auditor shorthand: `LAKEPORT COUNTY` (meaning Lakeport
   County Fire Protection District), `HARTLEY` (Hartley Cemetery
   District), `AREA NO. 23, ZONE K (RIVIERA WEST)`. Joining these to
   SCO entitynames requires exactly the fuzzy entity-resolution the
   V4 finding ruled indefensible without shared identifiers — and
   there are none (BOE's `D_CODE` is not an SCO identifier).
2. **It answers a different question.** TRAs enumerate
   *property-tax-levying* entities and their sub-zones: the list
   includes school districts (a layer we don't publish),
   redevelopment successor areas, and improvement zones that are not
   SCO filers — and **omits districts funded by rates and charges**
   (a large share of the enterprise-heavy district layer). "What is
   on your property-tax roll" ≠ "which special districts serve you."
3. **Scale of an honest fix:** a hand-curated TRA-name→SCO-entity
   crosswalk, county by county, for 58 counties × hundreds of
   shorthand names, re-verified every roll year. Possible in
   principle; not a side effect of this feature.

Per the standing rule — never approximate a district from a county,
never guess — **the address view ships without district assignment
and says so.** The honest substitute is already in our data: the
directory carries a county for every district, so the view can state
"**{N} special districts file from {County} County** — the Ledger
cannot determine from an address which of them serve it" and link to
the directory pre-filtered to that county. That is a true statement,
useful, and zero-guess. If a future TRA crosswalk project happens, a
separately-labeled "on your property-tax roll" panel becomes possible
— with the §2.2 caveats stated on its face.

---

## 3. Unincorporated addresses — a feature, verified

Detection is clean and authoritative: the geographies response has
**no Incorporated Places entry** for an unincorporated address, and
usually a CDP (`FUNCSTAT: "S"`). The East Los Angeles case above is
the exact scenario the feature exists for: ~125,000 people whose
mailing address says "Los Angeles" but whose local government is the
County of Los Angeles.

Design consequences (for the approved build):

- The local-government record shown is **the county**, framed
  explicitly: "This address is in unincorporated {County} County.
  The county is its local government." The county record's existing
  unincorporated-share footnote becomes concrete: "{pct}% of the
  county's residents share this arrangement."
- The CDP name, when present, is shown as **community context only**,
  labeled as a Census statistical area, never as a government —
  CDPs file nothing and spend nothing.
- No-CDP rural addresses (verified: pin-drop in Alpine County
  returns county + CDP where one exists, county alone otherwise)
  show the county record alone.

---

## 4. The arithmetic question — NO SUM, and now it's quantified

The instinct is correct, and it is not close. Measured from the SCO
revenue datasets (FY 2023-24, governmental funds, statewide):

- **Counties: 53.8% of governmental revenues are intergovernmental**
  — $56.23B of $104.46B. Split: **$37.55B from the state (35.9%)**,
  $17.83B federal (17.1%), $0.85B other. Per county: Los Angeles
  50.0%, Orange 57.2%, Alpine 52.3% — this is the structure of
  county finance, not an outlier.
- **Cities: 14.1%** intergovernmental ($10.46B of $74.19B) — smaller,
  still material.

So "your county spends $Y per resident" is a figure **roughly half of
which is money that already appears in the state's books** as local
assistance (realignment, Medi-Cal administration, CalWORKs,
Prop 172…). A stacked total would count those dollars twice — and
the federal share three ways once the state view's federal toggle is
on. Beyond double-counting, the layers differ in kind:

| Layer | Basis | What the figure is |
|---|---|---|
| State | Budgetary-Legal, **enacted appropriations** (plan) — actuals exist for 2021-22→2024-25 as a separate view | Statewide ÷ statewide population |
| City/county | SCO FTR **reported actuals** (retrospective) | Entity ÷ same-filing population |
| Districts | **As filed, unreconciled** — a tier that must never join reconciled figures in arithmetic | No resident denominator exists at all |

What is honestly presentable — the design rules for the build:

1. **Stacked separate records, never a total.** Each record carries
   its basis label on its face, in the existing tier vocabulary. No
   element with a combined figure exists in the DOM (CI-assertable,
   like the districts page's no-`$`-in-finding rule).
2. **The anti-sum is stated, with the number**: "These figures do not
   add. About half of county spending is state and federal money that
   also appears in those governments' figures — counting it once in
   each place would count it twice."
3. **Framing is "spending in your name," never "what you pay."**
   Per-resident spending is not tax incidence: renters, commuters,
   tourists, and businesses all pay into these budgets; no honest
   per-address "cost" exists. Copy rule, test-enforced like the
   banned-adjectives list.
4. **Fiscal-year alignment**: show the same FY where layers overlap
   (state actuals and SCO actuals share 2021-22→2023-24), and label
   the state figure "enacted plan" vs "actuals" per the year shown —
   never mixing vintages silently.
5. **The state figure needs an explicit "includes money sent to local
   governments" line** — the mirror image of the county's
   intergovernmental note, so the non-additivity reads as structure,
   not as fine print.

---

## 5. Privacy — what is guaranteed, and how

The site is static; there is no Ledger server to receive anything.
The guarantees, stated so they can be tested:

1. **The address leaves the browser only as a geocoding request to
   census.gov** (JSONP GET; the address appears in that URL and
   census.gov sees it plus the user's IP, standard for any federal
   service; the response sets a census.gov load-balancer cookie —
   disclosed in the methodology). No other host ever receives it:
   no analytics exist on the site (none do today — verifiable in
   source), map tiles are not fetched from the address panel, and
   the fonts request predates and never carries user input.
2. **Never in a permalink.** The URL hash encodes the *resolved
   jurisdictions* (city/county slugs — public facts shared by
   thousands of households), never the address, never coordinates.
   Sharing a permalink reveals "Lakewood + LA County," not a house.
3. **Never in a citation or CSV.** Both are generated from the
   resolved records only; the caveat/citation templates take slugs,
   not input. CI asserts the address input value appears nowhere in
   hash, citation, or CSV output.
4. **Never persisted.** No localStorage of the query; the input is
   cleared state, not saved state.
5. **A zero-address mode exists**: pin-drop sends only map
   coordinates to census.gov (verified working). And for
   maximum-privacy users, a documented degraded path exists that
   sends *nothing anywhere*: client-side point-in-polygon against
   the boundary files we already ship (~580 KB city+county) — with
   the stated caveat that simplified boundaries can misassign
   addresses within a few hundred meters of a city limit, which is
   why it is the fallback and not the default.

---

## 6. Recommendation detail

**(b) SHIP NARROWED**, as specified in the header. Required test
coverage when built: geocoder no-match and JSONP-failure degradation
(search picker still works — same pattern as the map's); East-LA-class
unincorporated correctness; boundary-edge assignment comes from the
geocoder, not our polygons; no summed figure exists in the DOM; the
"in your name / not what you pay" copy present; address absent from
hash/citation/CSV; the district panel states the county-scoped count
and never names a district as "yours."

Out of scope until separately approved: TRA-based "your property-tax
roll" panel (needs the crosswalk project, §2); school districts
(V5 (c) stands); any cost/incidence framing (ruled out, §4.3).

---

## Appendix — reproducibility

- CORS: `curl -D - -H "Origin: https://…github.io"` against
  `geocoding.geo.census.gov/geocoder/locations/onelineaddress` — no
  ACAO for foreign origins, ACAO echo for `https://www.census.gov`;
  real-browser `fetch()` → "Failed to fetch"; JSONP
  (`format=jsonp&callback=cb`) verified in-browser for both
  `locations` and `geographies` endpoints (2026-07-14).
- Geographies fields: `layers=Counties,Incorporated Places,Census
  Designated Places`, `vintage=Current_Current`; FUNCSTAT A/S
  distinguishes incorporated/CDP; four test addresses as tabled in §1.
- Pin-drop: `/geocoder/geographies/coordinates?x=-119.7793&y=38.6946`
  → Markleeville CDP + Alpine County.
- TIGERweb CORS: `tigerweb.geo.census.gov/arcgis/rest/…/query` echoes
  arbitrary Origin with ACAO (verified).
- Nominatim/Photon: ACAO `*` verified; policy
  https://operations.osmfoundation.org/policies/nominatim/ (1 req/s,
  user-triggered permitted, withdrawable).
- TRA: ArcGIS org search for `BOE TRA 2025` → 57 county Feature
  Services (owner `ca_boe`, services7.arcgis.com). Lake County
  (`Lake_2025_Roll_Year`): layer 1 polygons carry only `TRA`; table 2
  (`C17_2025`) carries `CO,TRA,DISTRICT,DIST_CAT,DIST_TYPE,PARENT,
  D_CODE`; 20 DIST_CAT values incl. school/redevelopment/zones; point
  query at (-122.9158, 39.0430) → TRA 001028 → 11 districts incl.
  `LAKEPORT COUNTY` (fire) and `HARTLEY` (cemetery). CORS `*`.
- Double-count: SODA `emxv-k8xv` (county revenues; value column is
  `values`), FY 2024, category sums: Intergovernmental State
  $37.55B / Federal $17.83B / Other $0.85B of $104.46B governmental
  revenues (enterprise/ISF/conduit excluded) = 53.8%; per-county LA
  50.0%, Orange 57.2%, Alpine 52.3%. Cities `rrtv-rsj9`: $10.46B of
  $74.19B = 14.1%.
