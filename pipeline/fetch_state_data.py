#!/usr/bin/env python3
"""
The California Ledger — data pipeline (V1, state level)
=======================================================

Rewrites ../data.js with official California expenditure data, in the
exact schema the site expects.

SOURCE (verified 2026-07-08)
----------------------------
Open FI$Cal — the State of California's fiscal transparency portal
(https://open.fiscal.ca.gov). The state's expenditure data is NOT on
data.ca.gov (the old CKAN dataset was removed); Open FI$Cal publishes
"Monthly Spending Transaction Files" — every spending transaction
recorded in FI$Cal, the state's accounting system — as CSVs on Azure
blob storage, listed in a machine-readable pointer file:

    {POINTER_URL}

Files are named Spending_FY<yy>P<pp>.csv where FY<yy> is the fiscal
year BEGINNING in 20<yy> (FY24 = fiscal year 2024-25) and P<pp> is the
accounting period (P01 = July ... P12 = June). Each file is 1-2 GB;
this script streams them without writing them to disk and caches the
aggregated result per fiscal year under pipeline/cache/, so re-runs
and backfills only download what is missing (use --refresh to force).

ACCOUNTING BASIS — important for the site's footer
--------------------------------------------------
These are ACTUAL EXPENDITURE TRANSACTIONS (cash-basis accounting
entries, including reversals and adjustments, which net out), NOT
enacted-budget appropriations. Totals will therefore differ from the
enacted budget published at ebudget.ca.gov. Rows in fund group
"Other NonGovt Cost Funds" (trust, agency and revolving funds) are
excluded, matching how state budget documents present total state
spending; the script reports how much was excluded.

Usage:
    python3 fetch_state_data.py --inspect            # look at the source first
    python3 fetch_state_data.py                      # 2 most recent complete FYs
    python3 fetch_state_data.py --years 2023-24 2024-25
    python3 fetch_state_data.py --refresh            # ignore cache, refetch

data.js is rebuilt from ALL complete cached years on every run, so you
can backfill history one year at a time. Data updates monthly (with a
lag of about two months); run on a schedule for freshness.
"""

import argparse
import csv
import io
import json
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

POINTER_URL = ("https://adwoutputfilesadlsstore.blob.core.windows.net/"
               "transparency/MonthlySpendingTransactionPointer/"
               "MonthlySpendingTransactionPointer.csv")

# Column names in the Monthly Spending Transaction Files (verified
# against the live files with --inspect on 2026-07-08).
COLUMNS = {
    "year": "fiscal_year_begin",      # "2024" = fiscal year 2024-25
    "agency": "agency_name",
    "department": "department_name",
    "fund_group": "fund_group_1",
    "amount": "monetary_amount",      # dollars; negatives are reversals
}

# Fund-group labels in the data -> our four keys. "Other NonGovt Cost
# Funds" is deliberately absent: trust/agency/revolving funds are not
# counted as state spending in budget documents. Unmapped groups are
# skipped and totaled in the run report.
FUND_MAP = {
    "general fund": "gf",
    "special funds": "sp",
    "bond funds": "bd",
    "federal funds": "fed",
}

# DOF population estimates (millions), used only for the per-resident
# figure: the January 1 estimate that falls inside each fiscal year,
# from DOF report E-4 (2026 vintage, 2020 census benchmark). Update
# annually from dof.ca.gov -> Demographics -> Estimates.
POPULATION = {
    "2020-21": 39.38, "2021-22": 39.16, "2022-23": 39.17,
    "2023-24": 39.45, "2024-25": 39.65, "2025-26": 39.59,
}

MAX_RETRIES = 3
FETCH_WORKERS = 4
CACHE_DIR = Path(__file__).resolve().parent / "cache"
OUT_PATH = Path(__file__).resolve().parent.parent / "data.js"

FUND_KEYS = ("gf", "sp", "bd", "fed")


# ----------------------------------------------------------------------
# Source discovery
# ----------------------------------------------------------------------
def http_get(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "ca-ledger-pipeline/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def load_manifest():
    """Returns {fiscal_year ('2024-25'): {period (int): download_url}}."""
    with http_get(POINTER_URL) as r:
        text = r.read().decode("utf-8-sig")
    manifest = defaultdict(dict)
    for row in csv.DictReader(io.StringIO(text)):
        name = row.get("FileName", "")
        url = row.get("Download", "")
        if not (name.startswith("Spending_FY") and url):
            continue
        try:
            fy = int(name[11:13])        # Spending_FY24P01.csv -> 24
            period = int(name[14:16])    #                      -> 01
        except ValueError:
            continue
        year = f"20{fy:02d}-{(fy + 1) % 100:02d}"
        manifest[year][period] = url
    return dict(manifest)


def complete_years(manifest):
    return sorted(y for y, periods in manifest.items() if len(periods) == 12)


# ----------------------------------------------------------------------
# Fetching + aggregation
# ----------------------------------------------------------------------
def new_node():
    return {k: 0.0 for k in FUND_KEYS} | {
        "departments": defaultdict(lambda: {k: 0.0 for k in FUND_KEYS})
    }


def aggregate_file(url: str, label: str):
    """Stream one monthly CSV and return (agg, skipped_counter).
    agg = {agency: node} — the file is a single fiscal year, so no year level.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        agg = defaultdict(new_node)
        skipped = Counter()   # fund_group label -> dollars skipped
        rows = bad = 0
        try:
            with http_get(url, timeout=300) as resp:
                text = io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline="")
                reader = csv.DictReader(text)
                for rec in reader:
                    rows += 1
                    try:
                        amount = float(rec[COLUMNS["amount"]])
                    except (KeyError, TypeError, ValueError):
                        bad += 1
                        continue
                    fund_raw = (rec.get(COLUMNS["fund_group"]) or "").strip()
                    fund = FUND_MAP.get(fund_raw.lower())
                    if fund is None:
                        skipped[fund_raw or "(blank)"] += amount
                        continue
                    agency = (rec.get(COLUMNS["agency"]) or "").strip() or "(unspecified)"
                    dept = (rec.get(COLUMNS["department"]) or "").strip() or "(unspecified)"
                    node = agg[agency]
                    node[fund] += amount
                    node["departments"][dept][fund] += amount
            print(f"  {label}: {rows:,} rows"
                  + (f", {bad:,} malformed" if bad else ""), file=sys.stderr)
            return agg, skipped
        except Exception as e:  # noqa: BLE001 — retry transient network failures
            wait = 15 * attempt
            print(f"  {label}: attempt {attempt}/{MAX_RETRIES} failed ({e}); "
                  f"retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{label}: giving up after {MAX_RETRIES} attempts")


def merge(target, source):
    for agency, node in source.items():
        tnode = target[agency]
        for k in FUND_KEYS:
            tnode[k] += node[k]
        for dept, dv in node["departments"].items():
            tdept = tnode["departments"][dept]
            for k in FUND_KEYS:
                tdept[k] += dv[k]


def fetch_year(year: str, period_urls: dict):
    """Download and aggregate all 12 monthly files of one fiscal year."""
    print(f"FY {year}: fetching {len(period_urls)} monthly files "
          f"({FETCH_WORKERS} at a time)…", file=sys.stderr)
    agg = defaultdict(new_node)
    skipped = Counter()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {
            pool.submit(aggregate_file, url, f"FY {year} P{p:02d}"): p
            for p, url in sorted(period_urls.items())
        }
        for fut in as_completed(futures):
            file_agg, file_skipped = fut.result()
            merge(agg, file_agg)
            skipped.update(file_skipped)
    print(f"FY {year}: done in {time.time() - t0:,.0f}s", file=sys.stderr)
    return agg, skipped


# ----------------------------------------------------------------------
# Per-year cache
# ----------------------------------------------------------------------
def cache_path(year: str) -> Path:
    return CACHE_DIR / f"FY{year}.json"


def save_cache(year, agg, skipped, n_periods):
    CACHE_DIR.mkdir(exist_ok=True)
    payload = {
        "year": year,
        "fetched": date.today().isoformat(),
        "periods": n_periods,
        "skipped_dollars": dict(skipped),
        "agencies": {
            name: {**{k: node[k] for k in FUND_KEYS},
                   "departments": {d: dict(v) for d, v in node["departments"].items()}}
            for name, node in agg.items()
        },
    }
    cache_path(year).write_text(json.dumps(payload), encoding="utf-8")


def load_cached_years():
    """Returns {year: cache_payload} for every complete cached year."""
    out = {}
    if CACHE_DIR.is_dir():
        for p in sorted(CACHE_DIR.glob("FY*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("periods") == 12:
                out[data["year"]] = data
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
            cached[year]["agencies"].items(),
            key=lambda kv: -sum(kv[1][k] for k in FUND_KEYS),
        ):
            depts = [
                {"name": dn, **{k: round(dv[k] / 1e9, 3) for k in FUND_KEYS}}
                for dn, dv in sorted(node["departments"].items(),
                                     key=lambda kv: -sum(kv[1].values()))
            ]
            agencies.append({
                "id": slugify(name), "name": name,
                **{k: round(node[k] / 1e9, 3) for k in FUND_KEYS},
                "departments": depts,
            })
        budgets[year] = {"agencies": agencies}
        trend[year] = {
            "state": round(sum(a["gf"] + a["sp"] + a["bd"] for a in agencies), 1),
            "federal": round(sum(a["fed"] for a in agencies), 1),
        }
    return {
        "meta": {
            "source": "open.fiscal.ca.gov",
            "sourceLabel": "Open FI$Cal Monthly Spending Transaction Files "
                           "(actual expenditures, open.fiscal.ca.gov)",
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
    ap = argparse.ArgumentParser(description="Rebuild data.js from Open FI$Cal")
    ap.add_argument("--inspect", action="store_true",
                    help="show available files and a sample record, then exit")
    ap.add_argument("--years", nargs="*", default=None,
                    help="fiscal years to fetch, e.g. --years 2023-24 2024-25 "
                         "(default: the 2 most recent complete years)")
    ap.add_argument("--refresh", action="store_true",
                    help="refetch requested years even if cached")
    args = ap.parse_args()

    print("Loading Open FI$Cal file manifest…", file=sys.stderr)
    manifest = load_manifest()
    complete = complete_years(manifest)
    print(f"  {sum(len(v) for v in manifest.values())} files, "
          f"complete fiscal years: {', '.join(complete)}", file=sys.stderr)

    if args.inspect:
        latest = sorted(manifest)[-1]
        p, url = sorted(manifest[latest].items())[-1]
        print(f"\nSample from FY {latest} P{p:02d}:")
        with http_get(url) as r:
            head = r.read(8192).decode("utf-8", errors="replace")
        lines = head.splitlines()
        print("Fields:", lines[0])
        print("First record:", lines[1] if len(lines) > 1 else "(empty)")
        return

    wanted = args.years if args.years else complete[-2:]
    for year in wanted:
        if year not in manifest:
            sys.exit(f"FY {year} not in the manifest (available: "
                     f"{', '.join(sorted(manifest))})")
        if year not in complete:
            print(f"  warning: FY {year} has only "
                  f"{len(manifest[year])}/12 periods published — skipping "
                  f"(partial years would understate totals)", file=sys.stderr)
            continue
        if not args.refresh and cache_path(year).exists():
            print(f"FY {year}: cached — skipping fetch (use --refresh to force)",
                  file=sys.stderr)
            continue
        agg, skipped = fetch_year(year, manifest[year])
        save_cache(year, agg, skipped, len(manifest[year]))
        for label, dollars in sorted(skipped.items(), key=lambda kv: -abs(kv[1])):
            print(f"  excluded fund group {label!r}: ${dollars / 1e9:,.2f}B",
                  file=sys.stderr)

    cached = load_cached_years()
    if not cached:
        sys.exit("No complete fiscal years cached — nothing to write.")
    payload = build_payload(cached)

    for w in plausibility_report(payload):
        print(f"  PLAUSIBILITY WARNING: {w}", file=sys.stderr)

    write_data_js(payload)


if __name__ == "__main__":
    main()
