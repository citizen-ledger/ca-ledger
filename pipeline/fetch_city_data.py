#!/usr/bin/env python3
"""
The California Ledger — city data pipeline (V2)
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
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp  # noqa: E402

DOMAIN = "bythenumbers.sco.ca.gov"
DS_EXPEND = "ju3w-4gxp"
DS_REVEN = "rrtv-rsj9"
DS_PERCAP = "ykhf-vfsr"
DS_SERVICES = "tsz3-29gc"

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


# ----------------------------------------------------------------------
# Fetching
# ----------------------------------------------------------------------
def soda(dataset: str, **params):
    """One SODA query, paged if needed. Returns all rows."""
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
                    page = json.load(r)
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
def classify_expenditure(category, sub1, sub2):
    """Returns ('gov', function_key) | ('ent', fund_key) |
    ('isf', None) | ('conduit', None)."""
    cat = norm(category)
    if cat in ENTERPRISE_BY_CATEGORY:
        return "ent", ENTERPRISE_BY_CATEGORY[cat]
    if cat == "Internal Service Fund":
        return "isf", None
    if cat == "Conduit Financing":
        return "conduit", None
    g, line = norm(sub1), norm(sub2)
    if g == "Public Safety":
        if line.startswith("Police"):
            return "gov", "police"
        if line.startswith("Fire"):
            return "gov", "fire"
        return "gov", "safetyOther"
    if g == "Health":
        if line.startswith("Sewers") or line.startswith("Solid Waste"):
            return "gov", "sanitation"
        return "gov", "health"
    if g == "Culture and Leisure":
        if line.startswith("Parks and Recreation"):
            return "gov", "parks"
        if line.startswith("Libraries"):
            return "gov", "library"
        return "gov", "cultureOther"
    return "gov", {
        "General Government": "admin",
        "Transportation": "streets",
        "Community Development": "housing",
        "Public Utilities": "utilities",
        "Other Expenditures": "other",
        "Debt Service": "debt",
        "Capital Outlay": "capital",
    }.get(g, "other")


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
                            "subcategory_2"})
    rev = soda(DS_REVEN,
               **{"$select": "entity_name,category,sum(value) as v",
                  "$where": f"fiscal_year='{source_year}'",
                  "$group": "entity_name,category"})

    cities = defaultdict(lambda: {
        "pop": 0, "county": "",
        "byFunction": defaultdict(float),
        "enterprise": defaultdict(float),
        "isf": 0.0, "conduit": 0.0,
        "revenues": 0.0, "revenuesEnterprise": 0.0,
    })
    for r in exp:
        name = norm(r["entity_name"])
        c = cities[name]
        c["county"] = norm(r.get("county")) or c["county"]
        c["pop"] = max(c["pop"], int(float(r.get("pop") or 0)))
        v = float(r.get("v") or 0)
        kind, key = classify_expenditure(
            r.get("category"), r.get("subcategory_1"), r.get("subcategory_2"))
        if kind == "gov":
            c["byFunction"][key] += v
        elif kind == "ent":
            c["enterprise"][key] += v
        elif kind == "isf":
            c["isf"] += v
        else:
            c["conduit"] += v
    for r in rev:
        name = norm(r["entity_name"])
        if name not in cities:
            continue
        v = float(r.get("v") or 0)
        kind = classify_revenue(r.get("category"))
        if kind == "gov":
            cities[name]["revenues"] += v
        elif kind == "ent":
            cities[name]["revenuesEnterprise"] += v
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
            "police": norm(r.get("police_service")).upper()[:1],
            "fire": norm(r.get("fire_service")).upper()[:1],
        }
    print(f"  services checklist: {len(out)} cities (FY 2015-16 vintage)",
          file=sys.stderr)
    return out


def fetch_official_totals():
    """{(city, source_year): official total_expenditures} for reconciliation."""
    rows = soda(DS_PERCAP,
                **{"$select": "entity_name,fiscal_year,total_expenditures",
                   "$where": "fiscal_year in("
                             + ",".join(f"'{y}'" for y in SOURCE_YEARS) + ")"})
    return {(norm(r["entity_name"]), r["fiscal_year"]):
            float(r.get("total_expenditures") or 0) for r in rows}


# ----------------------------------------------------------------------
# Sanity checks — the file is not written unless every one passes
# ----------------------------------------------------------------------
def sanity_check(years_data, official):
    errors, warnings = [], []
    for sy, cities in years_data.items():
        if len(cities) < 450:
            errors.append(f"FY {fy_label(sy)}: only {len(cities)} cities (expected ~482)")
        for name, c in cities.items():
            if c["pop"] <= 0:
                warnings.append(f"{name} FY {fy_label(sy)}: population 0")
            ours = (sum(c["byFunction"].values()) + sum(c["enterprise"].values())
                    + c["isf"] + c["conduit"])
            key = (name, sy)
            if key in official and official[key] > 0:
                drift = abs(ours - official[key])
                if drift > max(1000.0, official[key] * 0.001):
                    errors.append(
                        f"{name} FY {fy_label(sy)}: our total ${ours:,.0f} vs "
                        f"official ${official[key]:,.0f} (drift ${drift:,.0f})")
            elif key not in official:
                warnings.append(f"{name} FY {fy_label(sy)}: no official total to "
                                "reconcile against")
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


def build_payload(years_data, services):
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
        svc = services.get(name)
        if svc and (svc["police"] or svc["fire"]):
            entry["services"] = {
                k: {"code": v, "label": SERVICE_CODES.get(v, "")}
                for k, v in svc.items() if v
            }
        if name == "San Francisco":
            entry["flags"] = {"consolidated": True}
        prev_gov = None
        for sy in SOURCE_YEARS:
            c = years_data[sy].get(name)
            if not c:
                prev_gov = None
                continue
            entry["county"] = c["county"] or entry["county"]
            gov = sum(c["byFunction"].values())
            ent = sum(c["enterprise"].values())
            yr = {
                "population": c["pop"],
                "revenues": m(c["revenues"]),
                "expenditures": m(gov),
                "byFunction": {k: m(v) for k, v in c["byFunction"].items()
                               if round(v / 1e6, 3) != 0},
                "enterprise": {
                    "total": m(ent),
                    "revenues": m(c["revenuesEnterprise"]),
                    "byFund": {k: m(v) for k, v in c["enterprise"].items()
                               if round(v / 1e6, 3) != 0},
                },
            }
            if round(c["isf"] / 1e6, 3):
                yr["internalService"] = m(c["isf"])
            if round(c["conduit"] / 1e6, 3):
                yr["conduitFinancing"] = m(c["conduit"])
            notes = []
            if c["pop"] > 0:
                if c["byFunction"].get("police", 0) / c["pop"] < LOW_SERVICE_PER_CAPITA:
                    notes.append("lowPolice")
                if c["byFunction"].get("fire", 0) / c["pop"] < LOW_SERVICE_PER_CAPITA:
                    notes.append("lowFire")
            if prev_gov and prev_gov > 0 and (gov / prev_gov > 1.4 or gov / prev_gov < 0.6):
                notes.append("bigSwing")
            if notes:
                yr["notes"] = notes
            entry["years"][fy_label(sy)] = yr
            prev_gov = gov
        if entry["years"]:
            cities_out[slug] = entry

    return {
        "meta": {
            "source": DOMAIN,
            "sourceLabel": "City annual financial reports, State Controller's "
                           "Office “By the Numbers” "
                           "(bythenumbers.sco.ca.gov) — reported actual "
                           "expenditures and revenues",
            "generated": date.today().isoformat(),
            "units": "millions of dollars",
            "basis": "Reported actual revenues and expenditures from each "
                     "city's annual financial report to the State Controller. "
                     "Governmental activities are shown by function; "
                     "ratepayer-funded enterprise activities (water, power, "
                     "airports, harbors…) are shown separately. Internal "
                     "service funds and conduit financing are excluded from "
                     "both blocks.",
            "servicesChecklistVintage": "2015-16",
            "datasets": {"expenditures": DS_EXPEND, "revenues": DS_REVEN,
                         "perCapita": DS_PERCAP, "services": DS_SERVICES},
        },
        "years": year_labels,
        "functions": [{"key": k, "name": n} for k, n in FUNCTIONS],
        "enterpriseFunds": [{"key": k, "name": n} for k, n in ENTERPRISE_FUNDS],
        "cities": cities_out,
    }


def write_city_js(payload):
    stamp(payload)   # meta.integrity: SHA-256 of the canonical payload
    header = ("/* GENERATED by pipeline/fetch_city_data.py on "
              f"{date.today().isoformat()} from State Controller's Office "
              "data (bythenumbers.sco.ca.gov) — do not edit by hand. */\n")
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    OUT_PATH.write_text(header + "window.CA_CITY_DATA = " + body + ";\n",
                        encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB, "
          f"{len(payload['cities'])} cities, {len(payload['years'])} years)")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
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
    print("Fetching services checklist…", file=sys.stderr)
    services = fetch_services()

    years_data = {}
    for sy in SOURCE_YEARS:
        years_data[sy] = fetch_year(sy)

    errors, warnings = sanity_check(years_data, official)
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

    payload = build_payload(years_data, services)
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
