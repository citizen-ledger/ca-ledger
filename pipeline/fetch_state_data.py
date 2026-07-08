#!/usr/bin/env python3
"""
The California Ledger — data pipeline (V1, state level)
=======================================================

Rewrites ../data.js with official California ENACTED BUDGET data, in
the exact schema the site expects.

SOURCE (verified 2026-07-08)
----------------------------
The Department of Finance's eBudget site (https://ebudget.ca.gov) —
the JSON API that powers its "Enacted Budget" publication:

    https://ebudget.ca.gov/api/publication/e/{fiscal_year}/...

Endpoints used, per fiscal year:
    /appInfo                    sanity check: publication == "Enacted"
    /statistics                 agencies with GF / Special / Bond totals
    /statistics/{agencyCd}      departments of one agency, same fields
    /rwaCntl/support/{orgCd}    department expenditures by fund
    /rwaCntl/capOutlay/{orgCd}  capital-outlay expenditures by fund

Dollar fields are in THOUSANDS. Fund class codes in rwaCntl rows:
G = General Fund, S = Special Funds, B = Bond Funds, F = Federal Funds,
N = Nongovernmental-cost funds, R = Reimbursements. The site's gf/sp/bd
figures come from /statistics (they include capital outlay and match
the enacted Summary Charts exactly — verified: 2024-25 sums to
$297,862M, the published total). Federal figures are the F-class rows
of rwaCntl support + capOutlay. N and R are excluded, matching how
budget documents present state spending.

ACCOUNTING BASIS — important for the site's footer
--------------------------------------------------
These are ENACTED-BUDGET EXPENDITURE ESTIMATES (appropriations under
California's Budgetary-Legal basis), as published at enactment of each
year's Budget Act — not actual cash spending, which the state does not
publish in full machine-readable form (Open FI$Cal covers only the
~79% of departments that use the FI$Cal accounting system; see
STATUS.md). Enacted figures for a given year are fixed at enactment
and never revised, so cached years never need refetching.

Usage:
    python3 fetch_state_data.py --inspect            # look at the source first
    python3 fetch_state_data.py                      # default: 6 most recent enacted years
    python3 fetch_state_data.py --years 2024-25 2025-26
    python3 fetch_state_data.py --refresh            # ignore cache, refetch

data.js is rebuilt from ALL cached years on every run. A new enacted
budget is published once a year (late June); rerun then.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

API_BASE = "https://ebudget.ca.gov/api/publication/e"

# How many recent enacted fiscal years to load by default. The API
# serves publications back to at least 2018-19.
DEFAULT_YEARS = 6

# DOF population estimates (millions), used only for the per-resident
# figure: the January 1 estimate that falls inside each fiscal year,
# from DOF report E-4 (2026 vintage, 2020 census benchmark). Update
# annually from dof.ca.gov -> Demographics -> Estimates.
POPULATION = {
    "2020-21": 39.38, "2021-22": 39.16, "2022-23": 39.17,
    "2023-24": 39.45, "2024-25": 39.65, "2025-26": 39.59,
}

MAX_RETRIES = 3
FETCH_WORKERS = 8
CACHE_DIR = Path(__file__).resolve().parent / "cache"
OUT_PATH = Path(__file__).resolve().parent.parent / "data.js"

FUND_KEYS = ("gf", "sp", "bd", "fed")
THOUSANDS_PER_BILLION = 1e6


# ----------------------------------------------------------------------
# Fetching
# ----------------------------------------------------------------------
def get_json(path: str, ok_404=False):
    url = f"{API_BASE}/{path}"
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "ca-ledger-pipeline/2.0",
                              "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404 and ok_404:
                return None
            last_err = e
        except Exception as e:  # noqa: BLE001 — retry transient failures
            last_err = e
        time.sleep(2 * attempt)
    raise RuntimeError(f"GET {url} failed after {MAX_RETRIES} attempts: {last_err}")


def latest_enacted_years(n: int):
    """Most recent n fiscal years with a populated Enacted publication.
    (A stub publication for the upcoming year can exist with an empty
    /statistics — e.g. 2026-27 showed 'Enacted on January 01, 9999' —
    so a year only counts if it actually has agency data.)"""
    years = []
    y = date.today().year
    # An enacted budget for FY y-(y+1) appears in late June of year y.
    for start in range(y, y - n - 3, -1):
        fy = f"{start}-{str(start + 1)[-2:]}"
        try:
            info = get_json(f"{fy}/appInfo")
            if not (info and info.get("publication") == "Enacted"):
                continue
            if not get_json(f"{fy}/statistics"):
                continue
        except RuntimeError:
            continue
        years.append(fy)
        if len(years) == n:
            break
    return sorted(years)


def dept_federal(year: str, org_cd: str) -> float:
    """Federal-fund dollars (thousands) for one department:
    F-class rows of the support + capital-outlay fund tables."""
    fed = 0.0
    for ep in ("rwaCntl/support", "rwaCntl/capOutlay"):
        rows = get_json(f"{year}/{ep}/{org_cd}", ok_404=True) or []
        fed += sum((r.get("byTotDols") or 0)
                   for r in rows if r.get("fundClassCd") == "F")
    return fed


def fetch_year(year: str):
    """Returns {agency_name: {gf,sp,bd,fed, departments:{name:{...}}}},
    all values in THOUSANDS of dollars (budget-year enacted)."""
    info = get_json(f"{year}/appInfo")
    if info.get("publication") != "Enacted":
        raise RuntimeError(f"{year}: publication is {info.get('publication')!r},"
                           " not Enacted")
    agencies_raw = [a for a in get_json(f"{year}/statistics")
                    if a.get("displayOnWebFlg") == "Y"]
    print(f"FY {year}: {len(agencies_raw)} agencies "
          f"({info.get('publicationDate')})", file=sys.stderr)

    out = {}
    grand_check = agencies_raw[0].get("stateGrandTotal") if agencies_raw else None

    for a in agencies_raw:
        agency_cd = a["webAgencyCd"]
        dept_rows = [d for d in get_json(f"{year}/statistics/{agency_cd}")
                     if d.get("displayOnWebFlg") == "Y"]
        # dedupe by orgCd, keep first occurrence
        seen = set()
        depts = []
        for d in dept_rows:
            if d["orgCd"] in seen:
                continue
            seen.add(d["orgCd"])
            depts.append(d)

        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            feds = list(pool.map(lambda d: dept_federal(year, d["orgCd"]), depts))

        dept_nodes = {}
        for d, fed in zip(depts, feds):
            dept_nodes[d["legalTitl"].strip()] = {
                "gf": d["generalFundTotal"] or 0, "sp": d["specialFundTotal"] or 0,
                "bd": d["bondFundTotal"] or 0, "fed": fed or 0,
            }
        node = {
            "gf": a["generalFundTotal"] or 0, "sp": a["specialFundTotal"] or 0,
            "bd": a["bondFundTotal"] or 0,
            "fed": sum(v["fed"] for v in dept_nodes.values()),
            "departments": dept_nodes,
        }
        out[a["legalTitl"].strip()] = node
        st = (node["gf"] + node["sp"] + node["bd"]) / THOUSANDS_PER_BILLION
        print(f"  {a['legalTitl'][:44]:44} state ${st:8.3f}B  "
              f"fed ${node['fed'] / THOUSANDS_PER_BILLION:8.3f}B  "
              f"({len(dept_nodes)} depts)", file=sys.stderr)

    total = sum(n["gf"] + n["sp"] + n["bd"] for n in out.values())
    if grand_check:
        drift = abs(total - grand_check)
        print(f"FY {year}: state funds ${total / THOUSANDS_PER_BILLION:,.3f}B "
              f"(API stateGrandTotal ${grand_check / THOUSANDS_PER_BILLION:,.3f}B, "
              f"drift ${drift / 1e3:,.0f}k)", file=sys.stderr)
    return out


# ----------------------------------------------------------------------
# Per-year cache (enacted figures never change once published)
# ----------------------------------------------------------------------
def cache_path(year: str) -> Path:
    return CACHE_DIR / f"enacted_{year}.json"


def save_cache(year, agencies):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path(year).write_text(json.dumps({
        "year": year,
        "source": "ebudget-enacted",
        "fetched": date.today().isoformat(),
        "agencies": agencies,
    }), encoding="utf-8")


def load_cached_years():
    out = {}
    if CACHE_DIR.is_dir():
        for p in sorted(CACHE_DIR.glob("enacted_*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            # older caches may hold nulls where the API returned null
            for node in data["agencies"].values():
                for k in FUND_KEYS:
                    node[k] = node[k] or 0
                for dv in node["departments"].values():
                    for k in FUND_KEYS:
                        dv[k] = dv[k] or 0
            out[data["year"]] = data["agencies"]
    return out


# ----------------------------------------------------------------------
# data.js writer (schema unchanged — index.html depends on it)
# ----------------------------------------------------------------------
def slugify(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:24]


def build_payload(cached):
    years_sorted = sorted(cached.keys())
    budgets, trend = {}, {}
    for year in years_sorted:
        agencies = []
        for name, node in sorted(
            cached[year].items(),
            key=lambda kv: -(kv[1]["gf"] + kv[1]["sp"] + kv[1]["bd"] + kv[1]["fed"]),
        ):
            depts = [
                {"name": dn,
                 **{k: round(dv[k] / THOUSANDS_PER_BILLION, 3) for k in FUND_KEYS}}
                for dn, dv in sorted(
                    node["departments"].items(),
                    key=lambda kv: -sum(kv[1][k] for k in FUND_KEYS))
            ]
            agencies.append({
                "id": slugify(name), "name": name,
                **{k: round(node[k] / THOUSANDS_PER_BILLION, 3) for k in FUND_KEYS},
                "departments": depts,
            })
        budgets[year] = {"agencies": agencies}
        trend[year] = {
            "state": round(sum(a["gf"] + a["sp"] + a["bd"] for a in agencies), 1),
            "federal": round(sum(a["fed"] for a in agencies), 1),
        }
    return {
        "meta": {
            "source": "ebudget.ca.gov",
            "sourceLabel": "Enacted state budgets, Budgetary-Legal basis "
                           "(California Department of Finance, ebudget.ca.gov)",
            "generated": date.today().isoformat(),
            "population": POPULATION,
        },
        "years": years_sorted,
        "trend": trend,
        "budgets": budgets,
    }


def write_data_js(payload):
    header = ("/* GENERATED by pipeline/fetch_state_data.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(
        header + "window.CA_LEDGER_DATA = "
        + json.dumps(payload, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH} "
          f"({OUT_PATH.stat().st_size / 1024:.0f} KB, "
          f"{len(payload['budgets'])} fiscal years)")


# ----------------------------------------------------------------------
# Plausibility report (flag, per project rules, before publishing)
# ----------------------------------------------------------------------
def plausibility_report(payload):
    warnings = []
    for year, b in payload["budgets"].items():
        state_total = sum(a["gf"] + a["sp"] + a["bd"] for a in b["agencies"])
        for a in b["agencies"]:
            t = a["gf"] + a["sp"] + a["bd"]
            if state_total and t / state_total > 0.60:
                warnings.append(f"FY {year}: {a['name']} is "
                                f"{t / state_total:.0%} of state funds")
            for k in FUND_KEYS:
                if a[k] < 0:
                    warnings.append(f"FY {year}: {a['name']} {k} is negative "
                                    f"(${a[k]}B)")
    years = payload["years"]
    for i in range(1, len(years)):
        a, b = payload["trend"][years[i - 1]]["state"], payload["trend"][years[i]]["state"]
        if a and b and (b / a > 2 or a / b > 2):
            warnings.append(f"{years[i]} state total (${b}B) is more than 2x "
                            f"off from {years[i - 1]} (${a}B)")
    return warnings


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Rebuild data.js from ebudget.ca.gov "
                                             "enacted budgets")
    ap.add_argument("--inspect", action="store_true",
                    help="show available years and a sample agency row, then exit")
    ap.add_argument("--years", nargs="*", default=None,
                    help="fiscal years to fetch, e.g. --years 2024-25 2025-26 "
                         f"(default: the {DEFAULT_YEARS} most recent enacted years)")
    ap.add_argument("--refresh", action="store_true",
                    help="refetch requested years even if cached")
    args = ap.parse_args()

    if args.inspect:
        years = latest_enacted_years(DEFAULT_YEARS)
        print("Enacted publications found:", ", ".join(years))
        sample = get_json(f"{years[-1]}/statistics")[0]
        print("Sample agency row:", json.dumps(sample, indent=2))
        return

    wanted = args.years if args.years else latest_enacted_years(DEFAULT_YEARS)
    print("Fiscal years:", ", ".join(wanted), file=sys.stderr)
    for year in wanted:
        if not args.refresh and cache_path(year).exists():
            print(f"FY {year}: cached — skipping fetch (use --refresh to force)",
                  file=sys.stderr)
            continue
        save_cache(year, fetch_year(year))

    cached = load_cached_years()
    if not cached:
        sys.exit("No fiscal years cached — nothing to write.")
    payload = build_payload(cached)

    for w in plausibility_report(payload):
        print(f"  PLAUSIBILITY WARNING: {w}", file=sys.stderr)

    write_data_js(payload)


if __name__ == "__main__":
    main()
