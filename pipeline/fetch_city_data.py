#!/usr/bin/env python3
"""
Citizen Ledger — city data pipeline (V2)
===============================================

Rewrites ../city-data.js with official city financial data from the
State Controller's Office "By the Numbers" portal
(https://bythenumbers.sco.ca.gov), in the schema cities.html expects.

SOURCE (VERIFIED 2026-07-13 against the live Socrata API)
---------------------------------------------------------
Datasets (Socrata ids), all on bythenumbers.sco.ca.gov:

    ju3w-4gxp   City - Expenditures       (line items, FY 2003-2024)
    rrtv-rsj9   City - Revenues           (line items)
    ykhf-vfsr   City Expenditures Per Capita   (official per-city totals —
                used as the reconciliation target, see SANITY CHECKS)
    tsz3-29gc   Check List of Services Provided (FY 2002-03 to 2015-16 —
                the maintained service-provision list; codes verified from
                the dataset's "City Service Codes.docx" attachment)

Row shape (expenditures): entity_name, fiscal_year (ending year: "2024"
= FY 2023-24), county, category, subcategory_1, subcategory_2,
line_description, value (dollars), estimated_population (from the same
filing — the population denominator comparability rule).

Fund structure, verified from the data:
  - category "... Enterprise Fund"  -> business-type activity (water,
    sewer, solid waste, electric, gas, airport, harbor/port, hospital,
    transit, other) with Operating/Nonoperating subcategories.
  - category "Internal Service Fund" and "Conduit Financing" -> neither
    governmental nor enterprise; tracked separately, excluded from both
    totals (internal service double-counts, conduit is pass-through).
  - everything else -> governmental activity; subcategory_1 is the
    function group (General Government, Public Safety, Transportation,
    Community Development, Health, Culture and Leisure, Public
    Utilities, Other Expenditures, Debt Service, Capital Outlay) and
    subcategory_2 the line ("Police_Current Expenditures", ...).

Reconciliation (verified before this was written): for Los Angeles FY
2024, governmental + enterprise + internal service + conduit sums to
$21,517,484,103 — exactly the official total_expenditures in
ykhf-vfsr. The same identity is enforced for every city-year loaded.

FISCAL YEARS: 2017-2024 in source labels (= 2016-17 .. 2023-24), the
era with the current form layout. Pre-2017 filings use a different
category layout and are not loaded.

COMPARABILITY (see docstring history in git and STATUS.md)
----------------------------------------------------------
1. CONTRACT CITIES — per-city service-provision codes for police and
   fire come from the SCO services checklist (most recent vintage:
   FY 2015-16), plus a data-derived flag when a city's police or fire
   line is under $5/resident in the displayed year. cities.html
   footnotes both, neutrally.
2. ENTERPRISE FUNDS — the schema keeps governmental and enterprise
   blocks separate; `expenditures`/`byFunction` are GOVERNMENTAL
   activities and are what the comparison view compares. Enterprise
   activity is shown per city in its own block.
3. CONSOLIDATED CITY-COUNTY — San Francisco (the state's only one) is
   flagged; its filings include county functions (verified: it is the
   only city reporting Assessor / District Attorney / Probation lines).
4. CAPITAL/DEBT SPIKES — capital outlay and debt service are visible
   functions (not folded away), and the load computes a year-over-year
   swing marker cities.html can footnote.
5. POPULATION — estimated_population from the same SCO filing, never a
   mixed vintage.

Usage:
    python3 fetch_city_data.py --inspect     # re-verify datasets/columns
    python3 fetch_city_data.py               # dry run: fetch + validate, no write
    python3 fetch_city_data.py --write       # rebuild ../city-data.js
"""

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402
import negative_balance  # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402
from strict import StrictRow  # noqa: E402

DOMAIN = "bythenumbers.sco.ca.gov"
DS_EXPEND = "ju3w-4gxp"
DS_REVEN = "rrtv-rsj9"
DS_PERCAP = "ykhf-vfsr"
DS_REV_PERCAP = "ky7j-fsk5"      # SCO's published per-city TOTAL REVENUES —
                                 # the revenue reconciliation target, exactly
                                 # parallel to ykhf-vfsr on the spending side
DS_SERVICES = "tsz3-29gc"

# THE PUBLISHER DISAGREES WITH ITSELF. SCO's city revenue dataset names
# its amount column `value`; the COUNTY revenue dataset (emxv-k8xv, used
# by fetch_county_data.py) names the same quantity `values`. Neither is
# a typo and neither is documented. The name is declared here, once, and
# aliased to `v` in every $select, so exactly one line differs between
# the two pipelines instead of the difference being scattered through
# every row read. See strict.py for why this is worth a named constant.
REVEN_VALUE_COL = "value"

# The source's own admission that it is not telling you what this is.
# SCO's form asks the filer to name what went into a residual line —
# "(Specify)" — and then publishes only the label, never the filer's
# answer. Marking these is a property of the SOURCE'S OWN TEXT, not a
# hand-maintained list of line names: any new residual line SCO adds is
# marked the day it appears, and nothing here encodes a judgement about
# which named lines are "really" ambiguous.
UNEXPLAINED_TOKEN = "(Specify)"
DS_COUNTY_PERCAP = "miui-wb29"   # SCO's COUNTY per-capita totals — used only
                                 # to detect a city reporting more residents
                                 # than the county containing it

SOURCE_YEARS = [str(y) for y in range(2017, 2025)]   # "2017".."2024"
SERVICES_VINTAGE_SOURCE_YEAR = "2016"                 # FY 2015-16
LOW_SERVICE_PER_CAPITA = 5.0                          # dollars/resident

FUNCTIONS = [
    ("police",       "Police"),
    ("fire",         "Fire"),
    ("safetyOther",  "Other public safety"),
    ("streets",      "Streets & transportation"),
    ("housing",      "Community development & housing"),
    ("sanitation",   "Sewer & solid waste"),
    ("health",       "Health & welfare"),
    ("parks",        "Parks & recreation"),
    ("library",      "Libraries"),
    ("cultureOther", "Other culture & leisure"),
    ("utilities",    "Public utilities (governmental)"),
    ("admin",        "General government"),
    ("other",        "Other expenditures"),
    ("debt",         "Debt service"),
    ("capital",      "Capital outlay"),
]

ENTERPRISE_FUNDS = [
    ("water",           "Water"),
    ("sewer",           "Sewer"),
    ("solidWaste",      "Solid waste"),
    ("electric",        "Electric"),
    ("gas",             "Gas"),
    ("airport",         "Airports"),
    ("harborPort",      "Harbor & port"),
    ("hospital",        "Hospital"),
    ("transit",         "Transit"),
    ("otherEnterprise", "Other enterprise"),
]
ENTERPRISE_BY_CATEGORY = {   # category name (whitespace-normalized) -> key
    "Water Enterprise Fund": "water",
    "Sewer Enterprise Fund": "sewer",
    "Solid Waste Enterprise Fund": "solidWaste",
    "Electric Enterprise Fund": "electric",
    "Gas Enterprise Fund": "gas",
    "Airport Enterprise Fund": "airport",
    "Harbor and Port Enterprise Fund": "harborPort",
    "Hospital Enterprise Fund": "hospital",
    "Transit Enterprise Fund": "transit",
    "Other Enterprise Fund": "otherEnterprise",
}

# Service-provision codes, from the checklist dataset's attachment
# "City Service Codes.docx" (verified 2026-07-13).
SERVICE_CODES = {
    "A": "provided by paid city employees",
    "B": "provided by city volunteers",
    "C": "provided wholly or in part through contract with another city",
    "D": "provided wholly or in part through contract with the county",
    "E": "provided wholly or in part through contract with the private sector",
    "F": "provided wholly or in part through contract with a special district "
         "or other public agency",
    "G": "provided, without city contract, by another city",
    "H": "provided, without city contract, by a special district or other "
         "public agency",
    "I": "provided, without city contract, by the county",
    "J": "provided, without city contract, by the private sector",
    "K": "not provided within the city",
}

OUT_PATH = Path(__file__).resolve().parent.parent / "city-data.js"
MAX_RETRIES = 3
PAGE = 50000

# U.S. Census Bureau place gazetteer (public domain): lat/lng for every
# incorporated place in California. LSAD 25 = city, 43 = town; the 482
# incorporated places match the SCO's 482 reporting cities one-to-one.
GAZETTEER_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
                 "2024_Gazetteer/2024_gaz_place_06.txt")
# SCO entity names that differ from the gazetteer beyond normalization
# (verified 2026-07-13). Report-and-fail on anything new — never guess.
GAZETTEER_ALIASES = {
    "amador": "amador city",       # SCO "Amador" = Census "Amador City city"
    "mt shasta": "mount shasta",   # SCO "Mt. Shasta" = Census "Mount Shasta city"
}


# ----------------------------------------------------------------------
# Fetching
# ----------------------------------------------------------------------
def soda(dataset: str, **params):
    """One SODA query, paged if needed. Returns all rows.

    A GROUPED QUERY MUST DECLARE AN ORDER. Paging is `$limit`/`$offset`,
    and offset paging over an unordered result is only as stable as the
    server's incidental row order: the same offset can re-serve a row it
    already sent and skip one it has not, so the page boundaries silently
    drop and duplicate groups. Summing the result then produces a total
    that is wrong in both directions and looks entirely plausible.

    THIS IS NOT HYPOTHETICAL. Adding `line_description` to the revenue
    fetch took it from ~9,600 groups per year to 176,949 — over the
    50,000 page size — and every one of 3,837 city-years then missed its
    published control, in both directions, by up to $41M. The gate
    caught it, which is the system working; this guard is so that the
    next grouped query cannot reintroduce it. The expenditure fetch was
    measured at 98,351 groups per year, also over the page size, and so
    was relying on incidental ordering too.
    """
    if "$group" in params and "$order" not in params:
        raise RuntimeError(
            f"GROUPED QUERY WITHOUT $order on {dataset}: paging a GROUP BY "
            "with $offset over an unordered result drops and duplicates "
            "groups at the page boundaries, and the resulting sums look "
            "plausible. Declare an $order over the grouped columns.")
    rows, offset = [], 0
    while True:
        q = dict(params)
        q["$limit"] = PAGE
        q["$offset"] = offset
        url = f"https://{DOMAIN}/resource/{dataset}.json?" + urllib.parse.urlencode(q)
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "ca-ledger-pipeline/2.0",
                    "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    page = [StrictRow(row, f"{dataset} (SCO {DOMAIN})")
                            for row in json.load(r)]
                break
            except Exception as e:  # noqa: BLE001 — retry transient failures
                last_err = e
                time.sleep(3 * attempt)
        else:
            raise RuntimeError(f"GET {url} failed after {MAX_RETRIES} tries: {last_err}")
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def fy_label(source_year: str) -> str:
    """SCO fiscal_year is the ENDING year: '2024' -> '2023-24'."""
    y = int(source_year)
    return f"{y - 1}-{str(y)[-2:]}"


# ----------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------
GOV_GROUPS = {"Public Safety", "Health", "Culture and Leisure",
              "General Government", "Transportation",
              "Community Development", "Public Utilities",
              "Other Expenditures", "Debt Service", "Capital Outlay"}


def classify_expenditure(category, sub1, sub2):
    """Returns ('gov', function_key) | ('ent', fund_key) |
    ('isf', None) | ('conduit', None).

    SHAPE-DRIVEN, not year-driven. Three source layouts have shipped:
      A  pre-FY 2016-17 : the group is repeated in `category`,
                          `subcategory_1` AND `subcategory_2`. No line
                          breakdown exists at all — police and fire are
                          not separable in this layout.
      B  FY 2016-17     : group in `category`, line in `subcategory_1`
                          (`subcategory_2` for the capital/debt split).
      C  FY 2017-18+    : paired super-group in `category`, group in
                          `subcategory_1`, line in `subcategory_2`.

    RECOGNIZING THE GROUP'S VALUE IS NOT ENOUGH TO TELL A FROM C.
    In layout A `subcategory_1` holds a perfectly valid group name, so a
    value test accepts the row, takes the layout-C branch, and files
    every police and fire dollar under `safetyOther` — while the totals
    gate still passes, because conservation cannot see classification.
    That is the FY 2016-17 defect wearing a different vintage. Measured
    live against FY 2009-10: 8 of 8 row shapes accepted, $15.2B misfiled,
    police and fire both reading exactly $0 (docs/V15_HISTORICAL_FINDING.md).

    So the line slot must be PROVEN to carry a line, not assumed to. If
    the value in the line position is the group itself, position carries
    no information and the row is refused."""
    cat = norm(category)
    if cat in ENTERPRISE_BY_CATEGORY:
        return "ent", ENTERPRISE_BY_CATEGORY[cat], None
    if cat == "Internal Service Fund":
        return "isf", None, None
    if cat == "Conduit Financing":
        return "conduit", None, None
    if norm(sub1) in GOV_GROUPS:                # layout C (and B's split)
        g, line = norm(sub1), norm(sub2)
    elif cat in GOV_GROUPS:                     # layout B
        g, line = cat, norm(sub1)
        if not line or line in GOV_GROUPS:      # FY2017 debt/capital split
            line = norm(sub2)
    else:
        raise SystemExit(
            "UNRECOGNIZED EXPENDITURE SHAPE — refusing to classify: "
            f"category={category!r} sub1={sub1!r} sub2={sub2!r}. "
            "A source vintage has shifted columns again; extend "
            "classify_expenditure deliberately.")
    if not line or line == g:
        raise SystemExit(
            "NO LINE DETAIL IN THIS SOURCE VINTAGE — refusing to classify: "
            f"category={category!r} sub1={sub1!r} sub2={sub2!r}. "
            f"The function group {g!r} occupies the line position too, so "
            "nothing establishes which field the line came from — this is "
            "the pre-FY 2016-17 SCO layout, in which police and fire are "
            "not separable. Classifying it would file every public-safety "
            "dollar under 'safetyOther' while every totals gate passed. "
            "Extend classify_expenditure deliberately if this vintage is "
            "ever to be loaded.")
    if g == "Public Safety":
        if line.startswith("Police"):
            return "gov", "police", line
        if line.startswith("Fire"):
            return "gov", "fire", line
        return "gov", "safetyOther", line
    if g == "Health":
        if line.startswith("Sewers") or line.startswith("Solid Waste"):
            return "gov", "sanitation", line
        return "gov", "health", line
    if g == "Culture and Leisure":
        if line.startswith("Parks and Recreation"):
            return "gov", "parks", line
        if line.startswith("Libraries"):
            return "gov", "library", line
        return "gov", "cultureOther", line
    return "gov", {
        "General Government": "admin",
        "Transportation": "streets",
        "Community Development": "housing",
        "Public Utilities": "utilities",
        "Other Expenditures": "other",
        "Debt Service": "debt",
        "Capital Outlay": "capital",
    }[g], line   # g is guaranteed known; KeyError here is a bug


def classify_revenue(category):
    cat = norm(category)
    if cat in ENTERPRISE_BY_CATEGORY:
        return "ent"
    if cat in ("Internal Service Fund", "Conduit Financing"):
        return "excluded"
    return "gov"


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------
def fetch_year(source_year: str):
    """Aggregates one source fiscal year. Returns
    {city: {pop, county, byFunction, enterprise, isf, conduit,
            revenues, revenuesEnterprise}}"""
    exp = soda(DS_EXPEND,
               **{"$select": "entity_name,county,category,subcategory_1,"
                             "subcategory_2,sum(value) as v,"
                             "max(estimated_population) as pop",
                  "$where": f"fiscal_year='{source_year}'",
                  "$group": "entity_name,county,category,subcategory_1,"
                            "subcategory_2",
                  "$order": "entity_name,county,category,subcategory_1,"
                            "subcategory_2"})
    # REVENUE IS READ AT LINE LEVEL, not category level, because two of
    # the three things the page must say about a revenue figure are
    # properties of the LINE and cannot be recovered from a category
    # subtotal: whether the source itself declined to explain it
    # ("(Specify)"), and how much of the year rests on a single line.
    rev = soda(DS_REVEN,
               **{"$select": "entity_name,category,line_description,"
                             f"sum({REVEN_VALUE_COL}) as v",
                  "$where": f"fiscal_year='{source_year}'",
                  "$group": "entity_name,category,line_description",
                  "$order": "entity_name,category,line_description"})

    cities = defaultdict(lambda: {
        "pop": 0, "county": "",
        "byFunction": defaultdict(float),
        "lines": defaultdict(lambda: defaultdict(float)),
        "enterprise": defaultdict(float),
        "isf": 0.0, "conduit": 0.0,
        "revenues": 0.0, "revenuesEnterprise": 0.0,
        # all-funds revenue, which is what the published control totals —
        # governmental + enterprise + internal service + conduit
        "revTotal": 0.0,
        "revByCategory": defaultdict(float),
        "revUnexplained": 0.0,        # dollars in "(Specify)" lines
        "revTopLine": ("", 0.0),      # largest single line: (label, dollars)
        # AN ALL-ZERO FILING IS NOT A MEASUREMENT OF ZERO.
        # Tracked while READING the source, not reconstructed afterwards
        # from the built totals: a total of zero can also arise from real
        # figures that offset, and those are different facts. This is true
        # only when no non-zero value appeared in any expenditure or
        # revenue row for the entity-year.
        "anyNonZero": False,
    })
    for r in exp:
        name = norm(r["entity_name"])
        c = cities[name]
        c["county"] = norm(r.optional("county")) or c["county"]
        c["pop"] = max(c["pop"], int(float(r.optional("pop") or 0)))
        v = float(r.optional("v") or 0)
        if v != 0:
            c["anyNonZero"] = True
        kind, key, line = classify_expenditure(
            r.optional("category"), r.optional("subcategory_1"),
            r.optional("subcategory_2"))
        if kind == "gov":
            c["byFunction"][key] += v
            if v != 0:
                label = re.sub(r"_Current Expenditures?$", "", line or "").strip()
                c["lines"][key][label or "(unlabeled)"] += v
        elif kind == "ent":
            c["enterprise"][key] += v
        elif kind == "isf":
            c["isf"] += v
        else:
            c["conduit"] += v
    rev_seen = 0
    for r in rev:
        name = norm(r["entity_name"])
        if name not in cities:
            continue
        rev_seen += 1
        v = float(r.optional("v") or 0)
        cat = norm(r.optional("category"))
        line = norm(r.optional("line_description"))
        c = cities[name]
        if v != 0:
            c["anyNonZero"] = True
        # ALL-FUNDS, because that is what SCO's published total_revenues
        # is — the H2 test in docs/V21_REVENUE_FINDING.md measured a
        # governmental-only sum reconciling against it just 11.9% of the
        # time, so a governmental-only gate would be a gate against the
        # wrong number.
        c["revTotal"] += v
        c["revByCategory"][cat] += v
        if UNEXPLAINED_TOKEN in line:
            c["revUnexplained"] += v
        if v > c["revTopLine"][1]:
            c["revTopLine"] = (line, v)
        kind = classify_revenue(cat)
        if kind == "gov":
            c["revenues"] += v
        elif kind == "ent":
            c["revenuesEnterprise"] += v
    # POSITIVE CONTROL FOR A NEGATIVE FINDING. Every derived revenue
    # figure below is a share whose numerator can legitimately be zero,
    # so a fetch that silently returned nothing would render as "no
    # unexplained revenue anywhere" — the most flattering possible
    # reading of a broken query. Assert the fetch actually happened
    # before any of those shares are believed.
    gates.require_rows(rev_seen, 3000,
                       f"FY {fy_label(source_year)} revenue line rows matched "
                       "to a city",
                       "the source publishes roughly 20,000 city revenue "
                       "lines per year; near-zero means the amount column "
                       f"{REVEN_VALUE_COL!r} or the join key changed name")
    print(f"  FY {fy_label(source_year)}: {len(cities)} cities, "
          f"{len(exp):,} expenditure lines, {len(rev):,} revenue lines",
          file=sys.stderr)
    return dict(cities)


def fetch_services():
    """Police/fire provision codes from the FY 2015-16 checklist."""
    rows = soda(DS_SERVICES,
                **{"$where": f"fiscal_year='{SERVICES_VINTAGE_SOURCE_YEAR}'"})
    out = {}
    for r in rows:
        name = norm(r["entity_name"])
        out[name] = {
            "police": norm(r.optional("police_service")).upper()[:1],
            "fire": norm(r.optional("fire_service")).upper()[:1],
        }
    print(f"  services checklist: {len(out)} cities (FY 2015-16 vintage)",
          file=sys.stderr)
    return out


def _norm_place(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().replace(".", "").replace(",", "").replace("'", "")
    return re.sub(r"[\s-]+", " ", s).strip()


def fetch_coordinates():
    """{normalized place name: (lat, lng)} from the Census gazetteer."""
    req = urllib.request.Request(GAZETTEER_URL, headers={
        "User-Agent": "ca-ledger-pipeline/2.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        lines = r.read().decode("utf-8").splitlines()
    header = [c.strip() for c in lines[0].split("\t")]
    idx = {c: header.index(c) for c in ("NAME", "LSAD", "INTPTLAT", "INTPTLONG")}
    out = {}
    for line in lines[1:]:
        cols = line.split("\t")
        if cols[idx["LSAD"]].strip() not in ("25", "43"):   # city, town
            continue
        base = re.sub(r"\s+(city|town)$", "", cols[idx["NAME"]].strip())
        latlng = (round(float(cols[idx["INTPTLAT"]]), 5),
                  round(float(cols[idx["INTPTLONG"]]), 5))
        keys = {_norm_place(base)}
        m = re.match(r"^(.*)\((.*)\)\s*$", base)
        if m:
            keys.add(_norm_place(m.group(1)))
            keys.add(_norm_place(m.group(2)))
        for k in keys:
            out[k] = latlng
    print(f"  gazetteer: {len(out)} place-name keys", file=sys.stderr)
    return out


def coord_for(name, gaz):
    k = _norm_place(name)
    return gaz.get(GAZETTEER_ALIASES.get(k, k))


def fetch_official_totals():
    """{(city, source_year): official total_expenditures} for reconciliation."""
    rows = soda(DS_PERCAP,
                **{"$select": "entity_name,fiscal_year,total_expenditures",
                   "$where": "fiscal_year in("
                             + ",".join(f"'{y}'" for y in SOURCE_YEARS) + ")"})
    return {(norm(r["entity_name"]), r["fiscal_year"]):
            float(r.optional("total_expenditures") or 0) for r in rows}


def fetch_official_revenue_totals():
    """{(city, source_year): official total_revenues} for reconciliation.

    ky7j-fsk5 is the revenue twin of ykhf-vfsr, and it reconciles at the
    same tier: measured over the shipped window, every city-year
    reproduces its published total with a residual of exactly $0.00 —
    tighter than this pipeline's own tolerance. See
    docs/V21_REVENUE_FINDING.md §2.1.
    """
    rows = soda(DS_REV_PERCAP,
                **{"$select": "entity_name,fiscal_year,total_revenues",
                   "$where": "fiscal_year in("
                             + ",".join(f"'{y}'" for y in SOURCE_YEARS) + ")"})
    return {(norm(r["entity_name"]), r["fiscal_year"]):
            float(r.optional("total_revenues") or 0) for r in rows}


# ----------------------------------------------------------------------
# Sanity checks — the file is not written unless every one passes
# ----------------------------------------------------------------------
def county_populations():
    """SCO's own reported population per county-year.

    Used for one check: a city cannot contain more residents than its
    county. That is a contradiction INSIDE SCO's filings — same publisher,
    same year — so it needs no external estimate to detect, and it is the
    only kind of population error this pipeline is willing to assert.
    """
    out = {}
    for r in soda(DS_COUNTY_PERCAP,
                  **{"$select": "entity_name,fiscal_year,estimated_population",
                     "$where": f"fiscal_year >= '{SOURCE_YEARS[0]}' "
                               f"and fiscal_year <= '{SOURCE_YEARS[-1]}'"}):
        try:
            pop = int(float(r.optional("estimated_population") or 0))
        except (TypeError, ValueError):
            continue
        if pop:
            out[(norm(r.optional("entity_name") or ""),
                 r.optional("fiscal_year"))] = pop
    return out


def sanity_check(years_data, official, official_rev):
    errors, warnings = [], []
    reconciled = 0
    unreconciled = []
    rev_reconciled = 0
    rev_unreconciled = []
    for sy, cities in years_data.items():
        bad = gates.check_rows(len(cities), 450,
                               f"FY {fy_label(sy)} city roster",
                               "the source publishes about 482")
        if bad:
            errors.append(bad)
        for name, c in cities.items():
            if c["pop"] <= 0:
                warnings.append(f"{name} FY {fy_label(sy)}: population 0")
            ours = (sum(c["byFunction"].values()) + sum(c["enterprise"].values())
                    + c["isf"] + c["conduit"])
            key = (name, sy)
            # A ZERO OR MISSING CONTROL DOES NOT RECONCILE — it goes
            # UNRECONCILED, and that is recorded rather than skipped. The
            # previous `if key in official and official[key] > 0` quietly
            # dropped the check for any city-year whose published control
            # is 0, so those years passed without ever being compared.
            # Measured: 3 of 3,856 shipped city-years carry a published
            # total of 0 (the zero-filled non-timely filings), and each
            # must be counted as unreconciled, not as verified.
            if key in official and official[key] > 0:
                reconciled += 1
                drift = abs(ours - official[key])
                if drift > max(1000.0, official[key] * 0.001):
                    errors.append(
                        f"{name} FY {fy_label(sy)}: our total ${ours:,.0f} vs "
                        f"official ${official[key]:,.0f} (drift ${drift:,.0f})")
            else:
                unreconciled.append(f"{name} FY {fy_label(sy)}")
                if ours > 0:
                    errors.append(
                        f"{name} FY {fy_label(sy)}: we report ${ours:,.0f} but "
                        f"the published control is "
                        f"{'0' if key in official else 'absent'} — the figure "
                        "cannot be reconciled and must not ship as if it were")

            # THE REVENUE GATE. Same rule, same tolerance, same refusal
            # to treat a zero or absent control as a pass — and, for the
            # same reason as the spending side, against the ALL-FUNDS
            # sum rather than the governmental one.
            #
            # NON-FILING IS ENCODED AS A LITERAL ZERO in this control
            # (measured: Hollister FY2022, Novato FY2022, Woodland
            # FY2023 all carry total_revenues = 0). A gate that accepted
            # a zero control would certify "this city collected nothing"
            # as reconciled, which is the not-published-is-never-zero
            # rule failing in the direction that looks like a finding.
            ours_rev = c["revTotal"]
            if key in official_rev and official_rev[key] > 0:
                rev_reconciled += 1
                drift = abs(ours_rev - official_rev[key])
                if drift > max(1000.0, official_rev[key] * 0.001):
                    errors.append(
                        f"{name} FY {fy_label(sy)} REVENUE: our total "
                        f"${ours_rev:,.0f} vs official "
                        f"${official_rev[key]:,.0f} (drift ${drift:,.0f})")
            else:
                rev_unreconciled.append(f"{name} FY {fy_label(sy)}")
                if ours_rev > 0:
                    errors.append(
                        f"{name} FY {fy_label(sy)} REVENUE: we report "
                        f"${ours_rev:,.0f} but the published control is "
                        f"{'0' if key in official_rev else 'absent'} — the "
                        "figure cannot be reconciled and must not ship as if "
                        "it were")
    # the reconciliation must actually have run on the overwhelming majority
    gates.require_rows(reconciled, 3800,
                       "city-years reconciled against a published control",
                       f"{len(unreconciled)} were unreconciled: "
                       f"{unreconciled[:5]}")
    gates.require_rows(rev_reconciled, 3800,
                       "city-years whose REVENUE reconciled against a "
                       "published control",
                       f"{len(rev_unreconciled)} were unreconciled: "
                       f"{rev_unreconciled[:5]}")
    latest = SOURCE_YEARS[-1]
    la = years_data[latest].get("Los Angeles")
    if not la:
        errors.append("Los Angeles missing from latest year")
    else:
        gov = sum(la["byFunction"].values())
        if not 8e9 < gov < 20e9:
            errors.append(f"Los Angeles governmental total ${gov:,.0f} out of "
                          "plausible range")
    if "San Francisco" not in years_data[latest]:
        errors.append("San Francisco missing from latest year")
    return errors, warnings


# ----------------------------------------------------------------------
# Writer
# ----------------------------------------------------------------------
def slugify(name: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def m(v):  # dollars -> millions, 3 decimals
    return round(v / 1e6, 3)


def build_payload(years_data, services, gaz, county_pops):
    # V8 line dictionary + PARENT-SUM GATE: per city-year-function, the
    # line rows must sum to the UNROUNDED function total exactly
    line_labels = sorted({lbl for cities in years_data.values()
                          for c in cities.values()
                          for fam in c["lines"].values() for lbl in fam})
    line_idx = {lbl: i for i, lbl in enumerate(line_labels)}

    # Revenue label pools, interned the same way the V8 expenditure
    # lines are: the payload carries indices, the meta carries the text
    # once. Measured cost of the revenue block with real values is
    # +23% gzipped (docs/V21_REVENUE_FINDING.md §5); interning is what
    # keeps it there rather than higher.
    rev_cat_labels = sorted({k for cities in years_data.values()
                             for c in cities.values()
                             for k in c["revByCategory"]})
    rev_cat_idx = {k: i for i, k in enumerate(rev_cat_labels)}
    rev_line_labels = sorted({c["revTopLine"][0]
                              for cities in years_data.values()
                              for c in cities.values() if c["revTopLine"][0]})
    rev_line_idx = {k: i for i, k in enumerate(rev_line_labels)}
    for sy, cities in years_data.items():
        for cname, c in cities.items():
            for k, total in c["byFunction"].items():
                lsum = sum(c["lines"].get(k, {}).values())
                if abs(lsum - total) > 1:
                    sys.exit(f"V8 GATE {cname} FY {fy_label(sy)} {k}: lines "
                             f"sum ${lsum:,.0f} vs function ${total:,.0f} — "
                             "nothing written")

    year_labels = [fy_label(y) for y in SOURCE_YEARS]
    all_names = sorted({n for cities in years_data.values() for n in cities})
    slugs = {}
    for name in all_names:
        s = slugify(name)
        if s in slugs.values():
            raise RuntimeError(f"slug collision for {name!r}")
        slugs[name] = s

    cities_out = {}
    for name in all_names:
        slug = slugs[name]
        entry = {"name": name, "county": "", "years": {}}
        coord = coord_for(name, gaz)
        if coord:
            entry["lat"], entry["lng"] = coord
        svc = services.get(name)
        if svc and (svc["police"] or svc["fire"]):
            entry["services"] = {
                k: {"code": v, "label": SERVICE_CODES.get(v, "")}
                for k, v in svc.items() if v
            }
        if name == "San Francisco":
            entry["flags"] = {"consolidated": True}
        prev_gov = None
        prev_all_zero = False
        for sy in SOURCE_YEARS:
            c = years_data[sy].get(name)
            if not c:
                prev_gov = None
                prev_all_zero = False
                continue
            entry["county"] = c["county"] or entry["county"]
            gov = sum(c["byFunction"].values())
            ent = sum(c["enterprise"].values())
            yr = {
                "population": c["pop"],
                "revenues": m(c["revenues"]),
                "expenditures": m(gov),
                                # THE THREE STATES. This filter used to drop any function
                # whose value rounds to $0.000M, which erased the difference
                # between a function the filing REPORTED AS ZERO and one it
                # never mentioned. Measured at source for FY 2023-24 alone:
                # 2,492 functions reported as exactly zero, plus 6 carrying a
                # real amount under $500 (La Habra Heights health $221,
                # Roseville health $12). All were dropped and then read back
                # as a measured $0 by every renderer.
                #
                # The key now exists whenever the filing reported the
                # function, so absence in this dict means absence in the
                # filing, and nothing else. No published figure moves: every
                # value restored is 0.000 at this precision, and the totals
                # were always summed BEFORE this filter.
                "byFunction": {k: m(v) for k, v in c["byFunction"].items()},
                "lines": {k: sorted(
                              ([line_idx[lbl], int(round(v))]
                               for lbl, v in fam.items() if round(v) != 0),
                              key=lambda x: -abs(x[1]))
                          for k, fam in c["lines"].items()
                          if any(round(v) != 0 for v in fam.values())},
                "enterprise": {
                    "total": m(ent),
                    "revenues": m(c["revenuesEnterprise"]),
                    "byFund": {k: m(v) for k, v in c["enterprise"].items()
                               if round(v / 1e6, 3) != 0},
                },
                # ALL-FUNDS revenue: the figure SCO's published control
                # certifies, deliberately a different key from
                # `revenues` (governmental only) so the page can never
                # show one and cite the other's gate.
                "revAll": m(c["revTotal"]),
                "revCats": sorted(
                    ([rev_cat_idx[k], m(v)]
                     for k, v in c["revByCategory"].items()
                     if round(v / 1e6, 3) != 0),
                    key=lambda x: -abs(x[1])),
            }
            # THE TWO MARKS, both derived, neither a hand-list.
            #
            # revUnex — dollars sitting in lines whose own published
            # label carries SCO's "(Specify)" token: the form asked the
            # filer to name it and the answer is not published at any
            # depth. Emitted only when nonzero, so its absence on a
            # record means the source explained every line, not that the
            # field was forgotten.
            if round(c["revUnexplained"] / 1e6, 3) != 0:
                yr["revUnex"] = m(c["revUnexplained"])
            # revTop — the largest single line and its size. A year can
            # reconcile exactly and still rest on one line; that is a
            # fact about the filing, stated as a number, with no
            # inference that the money is one-time.
            top_label, top_val = c["revTopLine"]
            if top_label and round(top_val / 1e6, 3) != 0:
                yr["revTop"] = [rev_line_idx[top_label], m(top_val)]
            if round(c["isf"] / 1e6, 3):
                yr["internalService"] = m(c["isf"])
            if round(c["conduit"] / 1e6, 3):
                yr["conduitFinancing"] = m(c["conduit"])
            notes = []
            # A CITY CANNOT CONTAIN MORE RESIDENTS THAN ITS COUNTY.
            #
            # When SCO's own filings say it does, the city's population is
            # wrong — and every per-resident figure derived from it is not a
            # measurement of anything. The figure is NOT corrected: the
            # population ships exactly as filed, because that is what the
            # source says. What is withheld is the per-resident DERIVATION,
            # which the page must not present as measured.
            #
            # Measured across 3,856 city-years: five violations, all
            # Mt. Shasta (FY2017-18, FY2020-21..FY2023-24), which files a
            # population near 86,000 against a real ~3,200 and against its
            # county's own ~43,000. Those five years are also what drove
            # Siskiyou's unincorporated share to an impossible -137%.
            county_pop = county_pops.get((norm(c["county"]), sy))
            if c["pop"] and county_pop and c["pop"] > county_pop:
                notes.append("populationContradicted")
                yr["populationContradicted"] = (
                    f"This city's filing reports {c['pop']:,} residents, more "
                    f"than the {county_pop:,} its own county reports for the "
                    f"same year in the same State Controller dataset. One of "
                    f"the two is wrong; both are shown as filed. Per-resident "
                    f"figures are not derived for this year, because a "
                    f"denominator this source contradicts would not measure "
                    f"anything.")
            # AN ALL-ZERO FILING IS HELD, AND NOTHING IS DERIVED FROM IT.
            #
            # SCO publishes a COMPLETE schedule for these entity-years —
            # all 237 rows, none null, every value the string "0" — for
            # both expenditures and revenues at once. A city of 42,554
            # residents did not spend $0 while spending $70M the year
            # before and $90M the year after, and SCO publishes no
            # filing-status for cities or counties, so there is no source
            # statement to tell a zero filing from a missing one.
            #
            # The Ledger therefore refuses to choose: the figures ship as
            # filed, because that is what the source says, and the year is
            # marked HELD so no reader mistakes it for a measurement.
            #
            # THIS IS THE MT. SHASTA SHAPE. A bad input produced confident
            # derived flags: lowPolice and lowFire fired because $0 police
            # spending divided by a real population is below any
            # threshold, and bigSwing fired because the ratio to a real
            # prior year is zero. The page then stated, of three real
            # cities, that they spend unusually little on police and fire.
            # Measured: 6 entity-years, 11 false derived claims.
            #
            # Note Humboldt FY2020-21 carried NO flag — not because the
            # guard worked, but because the PRIOR year was also all-zero,
            # so `prev_gov > 0` was false. Absence of a flag there was
            # luck, not correctness, which is why suppression is explicit
            # here rather than left to the arithmetic.
            all_zero = not c.get("anyNonZero", True)
            if all_zero:
                notes.append("filingHeld")
                yr["filingStatus"] = "held"
                yr["filingHeldReason"] = (
                    "The State Controller publishes a complete schedule for "
                    "this year in which every expenditure and revenue line is "
                    "zero. This city reports figures in the ordinary range in "
                    "the years either side, and the Controller publishes no "
                    "filing-status for cities, so the Ledger cannot tell a "
                    "report of zero from a report that was never filed. The "
                    "Controller’s own published control for this year is also "
                    "zero, so there is nothing to reconcile against — "
                    "reproducing a published zero would prove nothing. The "
                    "figures are shown exactly as filed; nothing is derived "
                    "from them, and no comparison to another year is drawn.")
            if (c["pop"] > 0 and "populationContradicted" not in notes
                    and not all_zero):
                if c["byFunction"].get("police", 0) / c["pop"] < LOW_SERVICE_PER_CAPITA:
                    notes.append("lowPolice")
                if c["byFunction"].get("fire", 0) / c["pop"] < LOW_SERVICE_PER_CAPITA:
                    notes.append("lowFire")
            # ...and a swing measured against, or into, a held year is not
            # a swing in spending. Both directions are suppressed: the
            # year after an all-zero year would otherwise read as a 100%
            # increase off a floor that was never there.
            if (prev_gov and prev_gov > 0 and not all_zero and not prev_all_zero
                    and (gov / prev_gov > 1.4 or gov / prev_gov < 0.6)):
                notes.append("bigSwing")
            if notes:
                yr["notes"] = notes
            entry["years"][fy_label(sy)] = yr
            prev_gov = gov
            prev_all_zero = all_zero
        if entry["years"]:
            cities_out[slug] = entry

    # ---- NEGATIVE FUND BALANCE, per docs/V24A. The count of years is the
    # published fact; no dollar figure is carried and there is no field
    # for one, because a deficit figure beside the spending figure on the
    # same record invites the ratio V24 refused. Joined on (name, county)
    # with the county taken from the Controller's own ENTITIES tab.
    negbal = negative_balance.history("city")
    idx = {}
    for rec in cities_out.values():
        idx.setdefault((norm(rec["name"]), (rec.get("county") or "").lower()),
                       []).append(rec)
    n_att = n_amb = n_miss = 0
    for eid, rec in negbal.items():
        hit = idx.get((norm(rec["name"]), (rec.get("county") or "").lower())) or []
        if len(hit) > 1:
            n_amb += 1
            continue
        if not hit:
            n_miss += 1
            continue
        hit[0]["negBalance"] = {
            "years": rec["years"],
            "of": len(negative_balance.YEARS),
            "windowEdge": negative_balance.edge_cases(rec["years"]),
        }
        n_att += 1
    if n_amb:
        raise SystemExit(
            f"NEGATIVE BALANCE: {n_amb} entities match more than one city by "
            "(name, county); attaching a deficit history to the wrong "
            "government is refused. Nothing written")
    if not n_att:
        raise SystemExit(
            f"NEGATIVE BALANCE: computed a history for {len(negbal)} cities "
            "and attached none — the join key is wrong; nothing written")
    print(f"negative balance: {n_att} attached, {n_miss} unmatched",
          file=sys.stderr)

    return {
        "meta": {
            "source": DOMAIN,
            "sourceLabel": "City annual financial reports, State Controller's "
                           "Office “By the Numbers” "
                           "(bythenumbers.sco.ca.gov) — reported actual "
                           "expenditures and revenues",
            "generated": date.today().isoformat(),
            "lineLabels": line_labels,
            "linesNote": "V8 depth: per city-year, lines = "
                         "{function: [[lineLabelIdx, whole dollars]]} — "
                         "governmental activities only, official FTR form "
                         "line names, children sum to the unrounded "
                         "function totals exactly (gated). 'Other …' lines "
                         "are not itemized in the state form.",
            "units": "millions of dollars",
            "basis": "Reported actual revenues and expenditures from each "
                     "city's annual financial report to the State Controller. "
                     "Governmental activities are shown by function; "
                     "ratepayer-funded enterprise activities (water, power, "
                     "airports, harbors…) are shown separately. Internal "
                     "service funds and conduit financing are excluded from "
                     "both blocks.",
            "servicesChecklistVintage": "2015-16",
            "revCategoryLabels": rev_cat_labels,
            "revLineLabels": rev_line_labels,
            "revenueNote":
                "revAll is ALL FUNDS — governmental, enterprise, internal "
                "service and conduit — because that is what the Controller's "
                "published total_revenues (ky7j-fsk5) certifies, and every "
                "city-year reproduces it exactly. `revenues` remains the "
                "governmental-only figure and is NOT what the revenue gate "
                "checked. revCats are those all-funds categories, nonzero "
                "only.",
            "unexplainedNote":
                "revUnex is the dollars in lines whose own published label "
                f"carries the Controller's {UNEXPLAINED_TOKEN!r} token — the "
                "form asked the filer to name what went into a residual line "
                "and publishes only the label, never the answer, at any "
                "subcategory depth. Derived from the source's text, not from "
                "a list of line names kept here. Absent means zero such "
                "lines, not unmeasured.",
            "topLineNote":
                "revTop is [label index, millions] for the single largest "
                "revenue line of that year. A year can reconcile to the "
                "published total exactly and still rest on one line; this "
                "reports that, and asserts nothing about whether the money "
                "recurs.",
            "datasets": {"expenditures": DS_EXPEND, "revenues": DS_REVEN,
                         "perCapita": DS_PERCAP,
                         "revenuePerCapita": DS_REV_PERCAP,
                         "services": DS_SERVICES},
        },
        "years": year_labels,
        "functions": [{"key": k, "name": n} for k, n in FUNCTIONS],
        "enterpriseFunds": [{"key": k, "name": n} for k, n in ENTERPRISE_FUNDS],
        "cities": cities_out,
    }


def write_city_js(payload):
    prev = revisions.previous_payload(OUT_PATH)
    stamp(payload)   # meta.integrity: SHA-256 of the canonical payload
    header = ("/* GENERATED by pipeline/fetch_city_data.py on "
              f"{date.today().isoformat()} from State Controller's Office "
              "data (bythenumbers.sco.ca.gov) — do not edit by hand. */\n")
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    OUT_PATH.write_text(header + "window.CA_CITY_DATA = " + body + ";\n",
                        encoding="utf-8")

    revisions.record_revision('city', prev, payload,
                              source_signal=revisions.socrata_updated(
                                  ["ju3w-4gxp","rrtv-rsj9","ykhf-vfsr","tsz3-29gc"]))
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB, "
          f"{len(payload['cities'])} cities, {len(payload['years'])} years)")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def shape_gate(years_data):
    """THE CLASSIFICATION-SHAPE GATE (hard; added 2026-07-14 after the
    FY 2016-17 misclassification shipped). The totals gate proves
    conservation of money; this gate proves the money landed in the
    right functions:
      1. statewide, every core function (police, fire, admin, streets,
         parks) must be nonzero in every year;
      2. statewide, 'other' must never exceed 10% of governmental
         spending (clean vintages measure <= 0.6%; the broken FY
         2016-17 measured 83.2%);
      3. per city: police/fire above $1M in both adjacent years cannot
         be zero in between — unless the whole governmental filing for
         that year is zero at the source (SCO publishes zero-filled
         forms for some non-timely filers: Hollister and Novato FY
         2021-22, Woodland FY 2022-23, verified at source). The $1M
         materiality floor exists because tiny incidental lines
         legitimately touch zero (Mendota fire: $16k, $0, $1.5k —
         verified at source); a real department cannot.
      4. statewide, a residual bucket cannot swallow its group: the
         unnamed remainder of Public Safety and of Culture and Leisure
         must stay a minority of that group.

    Rule 4 exists because rules 1-3 all reduce to "is this named line
    zero", and a layout in which the line position echoes the group
    defeats them in exactly one step: every dollar lands in the
    residual bucket, which is nonzero, so nothing named looks missing.
    Measured on the pre-FY 2016-17 vintage the residual reads 100% of
    Public Safety while police and fire read $0. Clean shipped years
    measure 9.5-10.6% (safety) and 11.7-14.3% (culture), so the 35%
    bound has wide headroom and still catches a total swallow.
    Two independent rules, not one, now stand between this project and
    repeating its worst defect."""
    errors = []
    yrs = SOURCE_YEARS
    # A shape gate that iterates nothing accumulates no failures and reports
    # success. Every rule below loops over years_data, so an empty load — or
    # a year that parsed to no cities — would pass silently.
    gates.require_rows(len(years_data), len(yrs), "city-years to shape-check")
    for _sy in yrs:
        gates.require_rows(len(years_data.get(_sy) or {}), 400,
                           f"cities in FY {fy_label(_sy)}",
                           "the shape gate would check nothing for that year.")
    core = ("police", "fire", "admin", "streets", "parks")
    residual = (("safetyOther", ("police", "fire")),
                ("cultureOther", ("parks", "library")))
    statewide = {sy: {} for sy in yrs}
    for sy in yrs:
        for name, c in years_data[sy].items():
            for k, v in c["byFunction"].items():
                statewide[sy][k] = statewide[sy].get(k, 0.0) + v
    for sy in yrs:
        tot = sum(statewide[sy].values())
        for k in core:
            if statewide[sy].get(k, 0) <= 0:
                errors.append(f"SHAPE FY {fy_label(sy)}: statewide "
                              f"{k!r} is zero — classification broke")
        if tot and statewide[sy].get("other", 0) / tot > 0.10:
            errors.append(f"SHAPE FY {fy_label(sy)}: 'other' is "
                          f"{statewide[sy]['other']/tot*100:.1f}% of "
                          "governmental spending (clean years are <1%)")
        for res, named in residual:
            grp = statewide[sy].get(res, 0) + sum(
                statewide[sy].get(k, 0) for k in named)
            if grp and statewide[sy].get(res, 0) / grp > 0.35:
                errors.append(
                    f"SHAPE FY {fy_label(sy)}: {res!r} is "
                    f"{statewide[sy][res]/grp*100:.1f}% of its group — the "
                    "residual bucket has swallowed the named lines, which "
                    "is what a line position echoing the group looks like")
    for i in range(1, len(yrs) - 1):
        prev_y, cur_y, next_y = yrs[i-1], yrs[i], yrs[i+1]
        for name in years_data[cur_y]:
            cur = years_data[cur_y][name]
            if sum(cur["byFunction"].values()) == 0:
                continue                      # zero-filled source filing
            prev = years_data[prev_y].get(name)
            nxt = years_data[next_y].get(name)
            if not prev or not nxt:
                continue
            for fn in ("police", "fire"):
                if (prev["byFunction"].get(fn, 0) > 1_000_000
                        and nxt["byFunction"].get(fn, 0) > 1_000_000
                        and cur["byFunction"].get(fn, 0) == 0):
                    errors.append(f"SHAPE {name} FY {fy_label(cur_y)}: "
                                  f"{fn} is zero between two nonzero "
                                  "years — classification suspect")
    return errors


def main():
    ap = argparse.ArgumentParser(
        description="Rebuild city-data.js from SCO 'By the Numbers'")
    ap.add_argument("--inspect", action="store_true",
                    help="print dataset ids and a sample row, then exit")
    ap.add_argument("--write", action="store_true",
                    help="rewrite city-data.js (default: dry run)")
    args = ap.parse_args()

    if args.inspect:
        rows = soda(DS_EXPEND, **{"$limit": 1})
        print("Datasets:", DS_EXPEND, DS_REVEN, DS_PERCAP, DS_SERVICES)
        print("Sample expenditure row:", json.dumps(rows[0], indent=2))
        return

    print("Fetching official per-city totals (reconciliation target)…",
          file=sys.stderr)
    official = fetch_official_totals()
    print(f"  {len(official):,} city-year totals", file=sys.stderr)
    print("Fetching official per-city REVENUE totals (reconciliation "
          "target)…", file=sys.stderr)
    official_rev = fetch_official_revenue_totals()
    print(f"  {len(official_rev):,} city-year revenue totals", file=sys.stderr)
    print("Fetching services checklist…", file=sys.stderr)
    services = fetch_services()
    print("Fetching Census place gazetteer (coordinates)…", file=sys.stderr)
    gaz = fetch_coordinates()

    years_data = {}
    for sy in SOURCE_YEARS:
        years_data[sy] = fetch_year(sy)

    errors, warnings = sanity_check(years_data, official, official_rev)
    errors += shape_gate(years_data)
    # coordinate coverage: report failures rather than guessing or
    # silently dropping — an unmatched city fails the write.
    unmatched = sorted({n for cities in years_data.values() for n in cities
                        if not coord_for(n, gaz)})
    for n in unmatched:
        errors.append(f"no gazetteer coordinate match for {n!r} — add an "
                      "explicit entry to GAZETTEER_ALIASES")
    for w in warnings[:20]:
        print(f"  note: {w}", file=sys.stderr)
    if len(warnings) > 20:
        print(f"  … and {len(warnings) - 20} more notes", file=sys.stderr)
    if errors:
        for e in errors[:40]:
            print(f"  FAIL: {e}", file=sys.stderr)
        sys.exit(f"{len(errors)} sanity check failure(s) — city-data.js "
                 "left untouched.")
    print("All sanity checks passed (every city-year reconciles against the "
          "official SCO per-capita dataset totals).", file=sys.stderr)

    print("Fetching county populations (contradiction check)…", file=sys.stderr)
    county_pops = county_populations()
    payload = build_payload(years_data, services, gaz, county_pops)
    if not args.write:
        latest = payload["years"][-1]
        la = payload["cities"]["los-angeles"]["years"][latest]
        print(json.dumps({"meta": payload["meta"],
                          "losAngeles " + latest: la}, indent=2)[:1500])
        sys.exit("Dry run complete — re-run with --write to rebuild "
                 "city-data.js.")
    write_city_js(payload)


if __name__ == "__main__":
    main()
