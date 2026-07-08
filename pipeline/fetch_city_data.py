#!/usr/bin/env python3
"""
The California Ledger — city data pipeline (V2)
===============================================

Rewrites ../city-data.js with official city financial data, in the
schema cities.html expects.

SOURCE (UNVERIFIED — read this first)
-------------------------------------
The State Controller's Office requires all California cities to file
standardized annual financial reports and publishes them at
"By the Numbers" (https://bythenumbers.sco.ca.gov), a Socrata site
with a public SODA API. That is the one uniform source for city-level
revenues and expenditures.

IMPORTANT: unlike the state pipeline (fetch_state_data.py), whose
endpoints were verified against the live eBudget API before data was
published, THIS SCRIPT'S ENDPOINTS ARE UNVERIFIED. It was written in
an environment whose egress policy blocks *.sco.ca.gov and
*.socrata.com, so the dataset identifiers below are best-effort and
must be confirmed the first time this runs from an unrestricted
network. The script is written to fail loudly and leave the existing
city-data.js untouched unless a fetch fully succeeds and validates.

What must be verified on first run:
  1. The Socrata catalog search below returns the city revenues and
     expenditures datasets (run with --inspect).
  2. The dataset's four-character Socrata id ("fourfour") — set it in
     DATASET_ID once known, or pass --dataset.
  3. Column names: the SCO datasets historically use fields like
     entity_name, fiscal_year, category / type, and value/amount —
     the exact names must be read from --inspect output and mapped in
     COLUMN_MAP below.
  4. The functional categories and how they map to the site's
     function keys (FUNCTION_MAP below is a starting guess).

Usage:
    python3 fetch_city_data.py --inspect              # discover datasets + columns
    python3 fetch_city_data.py --dataset XXXX-XXXX    # fetch with a known dataset id
    python3 fetch_city_data.py --cities "Los Angeles" "Fresno"

Accounting basis (for the page footer, once real data loads): cities
report ACTUAL revenues and expenditures in their annual reports —
retrospective figures, not budgets. One new fiscal year per annual
filing cycle (reports for a fiscal year are published the following
year). This differs from the state view, which shows enacted
appropriations.

COMPARABILITY REQUIREMENTS (blockers for the comparison view)
--------------------------------------------------------------
Naive per-capita comparison of city expenditures is misleading unless
the load handles these structural factors. The site's comparison view
must not ship on real data until each is addressed (researched
2026-07-08; see STATUS.md for sources):

1. CONTRACT CITIES. Dozens of California cities contract police to
   the county sheriff (the "Lakewood model"; ~40 in Los Angeles
   County alone) and/or fire to county or district agencies.
   Contract cities show systematically lower per-capita police
   spending, and the studies that measured it attribute part of the
   gap to demographics and workload, not efficiency. The dataset
   itself does not label contract cities. The load must either derive
   a per-city service-provision flag from a maintained list or flag
   cities whose police/fire line is implausibly low or zero, and the
   UI must footnote them neutrally in any comparison.
2. ENTERPRISE FUNDS. City utilities (water, power, sewer, airports,
   harbors) are business-type activities funded by ratepayers, not
   general taxes. Cities differ in what they operate (LA runs a
   utility; most cities do not), which distorts totals. The SCO data
   distinguishes governmental from enterprise activity — PRESERVE
   that distinction in the schema (separate governmental vs
   enterprise blocks per city) and compare on governmental activities
   by default.
3. CONSOLIDATED CITY-COUNTY. San Francisco reports city and county
   functions in one entity; its figures are not comparable to any
   other city. Footnote or exclude from comparison.
4. CAPITAL AND DEBT SPIKES. A single bond issue or capital project
   can multiply a small city's one-year total. Any comparison should
   surface which year is shown and footnote large single-year swings
   rather than smoothing them.
5. POPULATION DENOMINATORS. Use the population reported in the same
   SCO filing (or DOF E-1 for the same year), never a mixed vintage.

If these cannot be resolved from the data plus a maintained flag
list, ship city detail views only and keep the comparison feature on
sample/disabled — a wrong comparison is worse than none.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

SCO_DOMAIN = "bythenumbers.sco.ca.gov"
CATALOG_URL = ("https://api.us.socrata.com/api/catalog/v1"
               "?domains=" + SCO_DOMAIN + "&search_context=" + SCO_DOMAIN
               + "&q=city%20expenditures&limit=30")
# Four-character Socrata dataset id for city expenditures — UNVERIFIED.
# Find it with --inspect and set it here (or pass --dataset).
DATASET_ID = None

# Map from the site's function keys to SCO functional category names.
# UNVERIFIED best-effort guesses; correct them from --inspect output.
FUNCTION_MAP = {
    "police":     ["Police"],
    "fire":       ["Fire"],
    "streets":    ["Streets", "Transportation"],
    "parks":      ["Parks and Recreation", "Recreation"],
    "library":    ["Library", "Culture"],
    "housing":    ["Community Development", "Housing"],
    "sanitation": ["Sewer", "Sanitation", "Waste"],
    "health":     ["Health"],
    "admin":      ["General Government", "Administration"],
    "debt":       ["Debt Service"],
}
# Column names in the SODA dataset — UNVERIFIED; read from --inspect.
COLUMN_MAP = {
    "entity": "entity_name",
    "year": "fiscal_year",
    "category": "category",
    "value": "value",
}

OUT_PATH = Path(__file__).resolve().parent.parent / "city-data.js"


def get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "ca-ledger-pipeline/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def inspect():
    print("Searching the Socrata catalog for SCO city datasets…", file=sys.stderr)
    print("GET " + CATALOG_URL, file=sys.stderr)
    try:
        cat = get_json(CATALOG_URL)
    except Exception as e:  # noqa: BLE001 — report and stop, do not guess
        sys.exit("Catalog query failed: %s\n"
                 "This is expected on a network that blocks sco.ca.gov / "
                 "socrata.com. Run from an unrestricted network." % e)
    for r in cat.get("results", []):
        res = r.get("resource", {})
        print("%-10s %s" % (res.get("id"), res.get("name")))
    print("\nPick the city expenditures dataset, then:", file=sys.stderr)
    print("  python3 fetch_city_data.py --dataset <id>  # prints sample rows first",
          file=sys.stderr)


def sample_rows(dataset_id):
    url = "https://%s/resource/%s.json?$limit=5" % (SCO_DOMAIN, dataset_id)
    print("GET " + url, file=sys.stderr)
    rows = get_json(url)
    print(json.dumps(rows, indent=2))
    print("\nConfirm COLUMN_MAP and FUNCTION_MAP against these rows, then "
          "re-run with --write.", file=sys.stderr)


def fetch(dataset_id, cities, write):
    col = COLUMN_MAP
    where = ""
    if cities:
        quoted = ",".join("'%s'" % c.replace("'", "''") for c in cities)
        where = "&$where=" + urllib.parse.quote(
            "%s in(%s)" % (col["entity"], quoted))
    url = ("https://%s/resource/%s.json?$limit=500000%s"
           % (SCO_DOMAIN, dataset_id, where))
    print("GET " + url, file=sys.stderr)
    rows = get_json(url)
    if not rows:
        sys.exit("Dataset returned no rows — nothing written.")
    missing = [k for k in col.values() if k not in rows[0]]
    if missing:
        sys.exit("Columns %s not present in dataset (have: %s). Fix "
                 "COLUMN_MAP; city-data.js left untouched."
                 % (missing, sorted(rows[0].keys())))
    if not write:
        print(json.dumps(rows[:5], indent=2))
        sys.exit("Dry run (columns validated, %d rows). Re-run with --write "
                 "to rebuild city-data.js." % len(rows))
    # Aggregation to the site schema goes here once the real dataset's
    # shape is known. Deliberately unimplemented until then: writing
    # city-data.js from unverified guesses would put wrong numbers on a
    # page that promises official data.
    sys.exit("Aggregation not implemented yet — map the verified dataset "
             "shape first (see docstring). city-data.js left untouched.")


def main():
    ap = argparse.ArgumentParser(
        description="Rebuild city-data.js from SCO 'By the Numbers' (Socrata)")
    ap.add_argument("--inspect", action="store_true",
                    help="search the Socrata catalog for candidate datasets")
    ap.add_argument("--dataset", default=DATASET_ID,
                    help="Socrata dataset id (xxxx-xxxx)")
    ap.add_argument("--cities", nargs="*", default=None,
                    help="limit to these city names")
    ap.add_argument("--write", action="store_true",
                    help="actually rewrite city-data.js (default: dry run)")
    args = ap.parse_args()

    if args.inspect:
        inspect()
        return
    if not args.dataset:
        sys.exit("No dataset id known yet. Run --inspect first (from a "
                 "network that can reach %s)." % SCO_DOMAIN)
    if args.cities or args.write:
        fetch(args.dataset, args.cities, args.write)
    else:
        sample_rows(args.dataset)


if __name__ == "__main__":
    main()
