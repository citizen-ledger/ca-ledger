#!/usr/bin/env python3
"""
Citizen Ledger — data pipeline (V1, state level)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402
import schedule9  # noqa: E402  (pypdf loaded lazily, only when refreshing actuals)

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
# THE RECONCILIATION GATE (no write on failure, like every other layer)
# ----------------------------------------------------------------------
# DOF publishes a statewide control total — `stateGrandTotal` — on every
# /statistics row, distinct from the agency rows beside it. THE GATE: the
# sum of DOF's own displayed agency rows (General + Special + Bond, the
# site's state-funds basis) must equal that published total EXACTLY, in
# THOUSANDS. Nothing is written if any year fails.
#
# The gate runs on the UNROUNDED thousands. An earlier tamper pin summed
# the per-agency figures after they were rounded to $0.001B for display
# and came out $2M light against DOF's published total; that was our
# rounding, not a basis difference. Unrounded, FY2024-25 sums to
# 297,861,977 thousands — exactly DOF's published $297,862M.
#
# ONE YEAR DOES NOT RECONCILE INSIDE DOF'S OWN DATA. For FY2025-26 the
# declared grand total EXCEEDS the sum of its own twelve agency rows by
# 1,638 thousands ($1.638M, 0.0005%). Verified stable across refetches
# and not explained by hidden rows (all twelve are displayed), by capital
# outlay (adding it overshoots by $9.35B), or by department detail
# (departments never sum to agencies in any year — see the limits below).
# It is DOF's inconsistency, not our extraction: this pipeline copies
# generalFundTotal / specialFundTotal / bondFundTotal verbatim.
#
# It is recorded here as an EXACT reviewed constant, never a tolerance
# band. A band would silently swallow the next, different discrepancy; an
# exact constant catches all extraction drift and names the source's own
# anomaly. If the residual changes, the build fails and a human looks.
# The Ledger reports DOF's agency rows AS PUBLISHED and does not
# reconcile the difference away — the same discipline as CSU's visible
# reconciling row.
SOURCE_RESIDUAL = {          # Σ(agency rows) − stateGrandTotal, in thousands
    "2025-26": -1638,
}
#
# TWO STATED LIMITS.
#   1. The gate is at AGENCY level. It cannot be pushed down to
#      departments: agencies carry items with no department attribution,
#      so departments never sum to agencies in ANY year (−$4.8B even in a
#      year that reconciles exactly at agency level). The department and
#      fund drills carry their own separate identities instead.
#   2. It does not catch a TRANSFER BETWEEN TWO AGENCIES. Moving money
#      from one agency to another leaves the statewide total unchanged
#      and passes this gate. That gap is recorded, not closed.


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


def _fund_rows(funds):
    """[[fundCd, class, thousands]] — plus the legal title as a fourth
    member ONLY where DOF publishes more than one title under one code in
    this department-year. Carrying it unconditionally would repeat ~190
    titles per year for no gain; carrying it never would render two
    genuinely different funds as one repeated name."""
    titles = {}
    for cd, title, _cls in funds:
        titles.setdefault(cd, set()).add(title)
    rows = []
    for (cd, title, cls), v in funds.items():
        row = [cd, cls, v]
        if len(titles[cd]) > 1:
            row.append(title)
        rows.append(row)
    return rows


def dept_depth(year: str, org_cd: str):
    """Everything below the department that the V8 finding approved:
    fund rows (the drill whose children sum exactly to the gated
    parents), the N/R totals (the bridge), and programs (the labeled
    all-funds view). All dollars in THOUSANDS, kept as integers —
    integer source units per the V8 cross-cutting rules."""
    # KEYED ON (fundCd, legal title, class) — THE TUPLE DOF DISTINGUISHES BY.
    # Keying on fundCd alone ADDED rows the source publishes separately and
    # kept whichever class arrived first. Enumerated across all 1,155
    # dept-years in the six loaded budgets: 43 collisions, every one of them
    # fund 0001, where DOF emits "General Fund" and "General Fund,
    # Proposition 98" as distinct rows. The Proposition 98 guarantee is a
    # real distinction and was being folded away.
    funds = {}          # (fundCd, title, class) -> thousands
    fund_names = {}
    nr = {"N": 0, "R": 0}
    fed = 0
    infra = 0           # capital outlay, ALL classes — programs exclude it
    for ep in ("rwaCntl/support", "rwaCntl/capOutlay"):
        rows = get_json(f"{year}/{ep}/{org_cd}", ok_404=True) or []
        for r in rows:
            if ep == "rwaCntl/capOutlay":
                infra += int(round(r.get("byTotDols") or 0))
            cls = r.get("fundClassCd")
            v = int(round(r.get("byTotDols") or 0))
            if cls == "F":
                fed += v
            if cls in ("N", "R"):
                nr[cls] += v
            if cls in ("G", "S", "B", "F"):
                cd = r.get("fundCd") or "?"
                title = (r.get("fundLglTitl") or cd).strip()
                funds[(cd, title, cls)] = funds.get((cd, title, cls), 0) + v
                fund_names.setdefault(cd, title)
    prog = get_json(f"{year}/orgProgram/{org_cd}", ok_404=True) or {}
    prog_rows = prog.get("lines") or []
    programs = [[(r.get("programCode") or "").strip(),
                 (r.get("programTitl") or "").strip(),
                 int(round(r.get("byDols") or 0))]
                for r in prog_rows]
    # the API's own totals rows anchor the program gate
    tot = {"excl": None, "infra": 0, "all": None}
    for tr in prog.get("totals") or []:
        ti = (tr.get("programTitl") or "")
        v = int(round(tr.get("byDols") or 0))
        if "excluding Infrastructure" in ti:
            tot["excl"] = v
        elif "Infrastructure" in ti:
            tot["infra"] = v
        elif "All Expenditures" in ti:
            tot["all"] = v
    return {
        "fed": fed,
        "progTotals": tot,
        "infra": infra,
        "funds": sorted(_fund_rows(funds), key=lambda x: (-abs(x[2]), x[0])),
        "nr": [nr["N"], nr["R"]],
        "programs": sorted(programs, key=lambda x: -abs(x[2])),
        "fundNames": fund_names,
    }


def fetch_year(year: str):
    """Returns ({agency_name: {gf,sp,bd,fed, departments:{...}}},
    stateGrandTotal), all values in THOUSANDS of dollars (budget-year
    enacted). The published control total travels with the rows so the
    gate can be re-run on every build, not only on fetch."""
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
            depths = list(pool.map(lambda d: dept_depth(year, d["orgCd"]), depts))

        dept_nodes = {}
        for d, depth in zip(depts, depths):
            node = {
                "code": d["orgCd"],
                "gf": d["generalFundTotal"] or 0, "sp": d["specialFundTotal"] or 0,
                "bd": d["bondFundTotal"] or 0, "fed": depth["fed"] or 0,
                "funds": depth["funds"], "nr": depth["nr"],
                "programs": depth["programs"],
                "fundNames": depth["fundNames"],
            }
            # V8 PARENT-SUM GATES (hard). Children sum to the UNROUNDED
            # parent, in thousands:
            #  - fund rows by class == the statistics parents (G/S/B);
            #    F is identical by construction;
            #  - programs (all funds) == gf+sp+bd+fed+N+R.
            by_cls = {}
            for row in depth["funds"]:            # [cd, class, thousands, title?]
                cl, v = row[1], row[2]
                by_cls[cl] = by_cls.get(cl, 0) + v
            for cls, key in (("G", "gf"), ("S", "sp"), ("B", "bd")):
                parent = node[key] or 0
                if abs(by_cls.get(cls, 0) - parent) > 1:
                    raise SystemExit(
                        f"V8 GATE {year} {d['legalTitl'].strip()!r}: fund "
                        f"class {cls} sums to {by_cls.get(cls, 0):,} vs "
                        f"parent {parent:,} (thousands) — nothing written")
            if depth["programs"]:
                # HARD GATE: program lines must equal the API's own
                # "excluding Infrastructure" total — a mismatch is source
                # corruption, never shippable.
                psum = sum(x[2] for x in depth["programs"])
                excl = depth["progTotals"]["excl"]
                if excl is not None and abs(psum - excl) > 1:
                    raise SystemExit(
                        f"V8 GATE {year} {d['legalTitl'].strip()!r}: program "
                        f"lines {psum:,} vs the API's own total {excl:,} — "
                        "nothing written")
                # THE BRIDGE: ship programs only when the program display
                # reconciles EXACTLY to the fund display —
                # programs + infrastructure == gf+sp+bd+fed+N+R. Where the
                # Budget's two displays disagree (e.g. Wildlife
                # Conservation Board 2020-21, whose "All Expenditures"
                # double-counts its capital outlay), the department ships
                # its fund drill only, marked programsOmitted — a reader
                # must never be able to conclude the gated totals are
                # wrong, so an unclear bridge means no program view.
                all_funds = ((node["gf"] or 0) + (node["sp"] or 0)
                             + (node["bd"] or 0) + node["fed"]
                             + depth["nr"][0] + depth["nr"][1])
                infra_unalloc = all_funds - psum
                if -1 <= infra_unalloc <= depth["infra"] + 1:
                    node["infraUnalloc"] = max(0, infra_unalloc)
                else:
                    node["programs"] = []
                    node["programsOmitted"] = True
            dept_nodes[d["legalTitl"].strip()] = node
        node = {
            "code": agency_cd,          # DOF's own webAgencyCd — the stable id
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

    omitted = [dn for n in out.values()
               for dn, dv in n["departments"].items()
               if dv.get("programsOmitted")]
    if omitted:
        print(f"  programs omitted (fund/program displays disagree): "
              f"{len(omitted)} dept(s): {', '.join(omitted[:6])}"
              + (" …" if len(omitted) > 6 else ""), file=sys.stderr)
    total = sum(n["gf"] + n["sp"] + n["bd"] for n in out.values())
    if grand_check:
        print(f"FY {year}: state funds ${total / THOUSANDS_PER_BILLION:,.3f}B "
              f"(DOF stateGrandTotal ${grand_check / THOUSANDS_PER_BILLION:,.3f}B, "
              f"residual {total - grand_check:+,}k)", file=sys.stderr)
    return out, grand_check


# ----------------------------------------------------------------------
# Per-year cache (enacted figures never change once published)
# ----------------------------------------------------------------------
def cache_path(year: str) -> Path:
    return CACHE_DIR / f"enacted_{year}.json"


def save_cache(year, agencies, grand_total):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path(year).write_text(json.dumps({
        "year": year,
        "source": "ebudget-enacted",
        "fetched": date.today().isoformat(),
        "stateGrandTotal": grand_total,
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
            out[data["year"]] = {"agencies": data["agencies"],
                                 "stateGrandTotal": data.get("stateGrandTotal")}
    return out


# ----------------------------------------------------------------------
# The gate
# ----------------------------------------------------------------------
def gate_years(cached):
    """Every year's agency rows must sum to DOF's published
    stateGrandTotal, exactly, in thousands — allowing only the reviewed
    per-year source residual. Raises SystemExit (nothing written) on any
    failure. Returns {year: {"totalK","controlK","residualK"}}."""
    report, failures = {}, []
    for year in sorted(cached):
        agencies = cached[year]["agencies"]
        control = cached[year].get("stateGrandTotal")
        total = sum((n["gf"] or 0) + (n["sp"] or 0) + (n["bd"] or 0)
                    for n in agencies.values())
        if control is None:
            failures.append(f"{year}: no DOF stateGrandTotal cached — refetch "
                            f"this year (--refresh) so the gate can run")
            continue
        residual = total - control
        expected = SOURCE_RESIDUAL.get(year, 0)
        if residual != expected:
            failures.append(
                f"{year}: agency rows sum to {total:,}k but DOF's published "
                f"stateGrandTotal is {control:,}k — residual {residual:+,}k, "
                f"expected {expected:+,}k"
                + (" (a recorded source residual; if DOF has corrected or "
                   "changed it, update SOURCE_RESIDUAL after review)"
                   if expected else ""))
        report[year] = {"totalK": total, "controlK": control,
                        "residualK": residual}
    if failures:
        for f in failures:
            print(f"  STATE GATE FAIL: {f}", file=sys.stderr)
        raise SystemExit(f"{len(failures)} state gate failure(s) — nothing written")
    for year, r in sorted(report.items()):
        note = "" if not r["residualK"] else \
            f"  [recorded source residual {r['residualK']:+,}k — DOF's own]"
        print(f"FY {year}: STATE GATE PASSED — agency rows {r['totalK']:,}k "
              f"== DOF stateGrandTotal {r['controlK']:,}k{note}", file=sys.stderr)
    return report


# ----------------------------------------------------------------------
# data.js writer (schema unchanged — index.html depends on it)
# ----------------------------------------------------------------------
# THE AGENCY IDENTITY, PINNED TO DOF'S OWN CODE.
#
# The published id was slugify(name)[:24] — derived from a display name and
# then truncated. Two hazards, and the second is the live one:
#
#   collision: two agency names agreeing in their first 24 slug characters
#              would share an id. Enumerated across all 12 agencies in the
#              six loaded budgets: 0 collisions today, but truncation is
#              load-bearing for 5 of the 12 (the longest full slug is 38
#              characters), so the margin is thinner than it looks.
#   rename:    a DOF rename moving no money at all would change the id, and
#              the change record — which keys on it — would republish every
#              figure beneath that agency as disappeared and then appeared.
#              Measured: 4,821 keys for the largest agency, 22,931 across
#              all twelve. That is the slug-instability lesson again.
#
# Pinning the id to webAgencyCd removes both. The MAPPING is declared rather
# than computed so the published ids keep the exact values they have today —
# no permalink breaks, no re-keying churn in the record — while the NAME no
# longer feeds the identity. An unknown code refuses the build rather than
# silently minting an id from a name.
AGENCY_IDS = {
    "0010": "legislative-judicial-and",
    "1000": "business-consumer-servic",
    "2500": "transportation",
    "3000": "natural-resources",
    "3890": "environmental-protection",
    "4000": "health-and-human-service",
    "5210": "corrections-and-rehabili",
    "6010": "k-thru-12-education",
    "6013": "higher-education",
    "7000": "labor-and-workforce-deve",
    "7500": "government-operations",
    "8000": "general-government",
}


def agency_id(code, name):
    """The published agency identity. Declared per DOF code, never derived
    from the display name."""
    if code not in AGENCY_IDS:
        raise SystemExit(
            f"UNKNOWN AGENCY CODE {code!r} ({name!r}) — the published "
            "identity is pinned to DOF's webAgencyCd and this code has no "
            "declared id. Add it to AGENCY_IDS deliberately; do not fall "
            "back to slugifying the name, which is what made the identity "
            "move when DOF renamed an agency.")
    return AGENCY_IDS[code]


def slugify(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:24]


def attach_actuals(payload, cached, refresh=False):
    """Adds Schedule 9 prior-year actuals (Budgetary-Legal basis) to the
    payload: agency.actual / department.actual (billions) plus
    meta.actuals vintage/unavailability notes. Gate failures raise —
    nothing is written on a failed reconciliation."""
    meta = {}
    for year in payload["years"]:
        if year in schedule9.UNAVAILABLE:
            meta[year] = {"unavailable": schedule9.UNAVAILABLE[year]}
            continue
        if year not in schedule9.SOURCES:
            meta[year] = {"unavailable":
                          "Actual expenditures for this fiscal year have not yet "
                          "been published; they first appear in the Governor's "
                          "Budget the following January."}
            continue
        acts = schedule9.load_actuals_year(year, refresh=refresh)
        code_to_agency = {}
        for aname, node in cached[year]["agencies"].items():
            for dv in node["departments"].values():
                if dv.get("code"):
                    code_to_agency[dv["code"]] = aname
        by_agency, by_dept, unsplit = schedule9.map_to_agencies(acts, code_to_agency)
        if unsplit:
            raise schedule9.GateError(
                f"actuals {year}: unmapped Schedule 9 groups {unsplit}")
        # conservation: mapped sums equal the gate-proven group sums
        for k, gk in (("gf", "gf"), ("sp", "sp"), ("bd", "bd")):
            mapped = sum(v[k] for v in by_agency.values())
            gated = sum(g[gk] for g in acts["groups"].values())
            if abs(mapped - gated) > schedule9.GATE_TOLERANCE:
                raise schedule9.GateError(
                    f"actuals {year}: conservation failure on {k}: "
                    f"{mapped:,} vs {gated:,}")
        B = THOUSANDS_PER_BILLION
        for a in payload["budgets"][year]["agencies"]:
            act = by_agency.get(a["name"])
            if act:
                a["actual"] = {k: round(act[k] / B, 3)
                               for k in ("gf", "sp", "bd", "fed")}
            for d in a["departments"]:
                dact = by_dept.get(d.get("code"))
                if dact:
                    d["actual"] = {k: round(dact[k] / B, 3)
                                   for k in ("gf", "sp", "bd", "fed")}
        note = {"vintage": acts["vintage"]}
        if acts.get("deptDetailDropped"):
            note["deptDetailDropped"] = acts["deptDetailDropped"]
        missing = [a["name"] for a in payload["budgets"][year]["agencies"]
                   if "actual" not in a]
        if missing:
            note["agenciesWithoutActuals"] = missing
        meta[year] = note
    payload["meta"]["actuals"] = {
        "basis": "Actual expenditures under the Budgetary-Legal basis of "
                 "accounting, as published by the Department of Finance in "
                 "Schedule 9 (Comparative Statement of Expenditures) of the "
                 "publication named per year; reconciled against Schedule 6 "
                 "statewide control totals before publication.",
        "years": meta,
    }


def build_payload(cached):
    years_sorted = sorted(cached.keys())
    budgets, trend = {}, {}
    # SCOPED PER YEAR. One global dict merged six budget acts and ~190
    # departments per year, so a fund renamed between acts kept only the
    # last title and every earlier year rendered under a name it did not
    # have. Enumerated: 23 fund codes drift across the loaded window —
    # 3085 Mental Health Services -> Behavioral Health Services (Prop 1),
    # 3246 Fair Employment and Housing -> Civil Rights Enforcement and
    # Litigation, 3209 Office of Patient Advocate -> Health Plan
    # Improvement, among others. Same lesson as the school resource
    # titles, which are already per-year for exactly this reason.
    fund_names = {}     # fiscal year -> {fundCd: legal title}
    for year in years_sorted:
        fund_names.setdefault(year, {})
        agencies = []
        for name, node in sorted(
            cached[year]["agencies"].items(),
            key=lambda kv: -(kv[1]["gf"] + kv[1]["sp"] + kv[1]["bd"] + kv[1]["fed"]),
        ):
            depts = []
            for dn, dv in sorted(
                    node["departments"].items(),
                    key=lambda kv: -sum(kv[1][k] for k in FUND_KEYS)):
                dd = {"name": dn,
                      **({"code": dv["code"]} if dv.get("code") else {}),
                      **{k: round(dv[k] / THOUSANDS_PER_BILLION, 3)
                         for k in FUND_KEYS}}
                # V8 depth: children in integer thousands (source units)
                if dv.get("funds"):
                    dd["funds"] = dv["funds"]
                    for cd, nm in (dv.get("fundNames") or {}).items():
                        fund_names[year].setdefault(cd, nm)
                if dv.get("nr") and any(dv["nr"]):
                    dd["nr"] = dv["nr"]
                if dv.get("programsOmitted"):
                    dd["programsOmitted"] = True
                elif dv.get("programs"):
                    dd["infraUnalloc"] = dv.get("infraUnalloc", 0)
                if dv.get("programs"):
                    dd["programs"] = dv["programs"]
                depts.append(dd)
            agencies.append({
                "id": agency_id(node.get("code"), name), "name": name,
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
            "fundNames": fund_names,
            "depth": "Per department: funds = [[fundCd, class, thousands, "
                     "legal title where one code carries more than one]] "
                     "(G/S/B/F only — children of the gated parents, exact); "
                     "nr = [nongovernmental-cost, reimbursements] thousands "
                     "(the bridge); programs = [[code, title, thousands]] "
                     "on an ALL-FUNDS scope: programs + infraUnalloc = "
                     "gf+sp+bd+fed+nr, exact — departments whose program "
                     "display does not reconcile to their fund display "
                     "carry programsOmitted instead of a misleading view. Program "
                     "prior-year columns are deliberately not carried: they "
                     "undercount the gated actuals (V8 finding).",
        },
        "years": years_sorted,
        "trend": trend,
        "budgets": budgets,
    }


def write_data_js(payload):
    prev = revisions.previous_payload(OUT_PATH)
    stamp(payload)   # meta.integrity: SHA-256 of the canonical payload
    header = ("/* GENERATED by pipeline/fetch_state_data.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(
        header + "window.CA_LEDGER_DATA = "
        + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    revisions.record_revision('state', prev, payload)
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
    ap.add_argument("--refresh-actuals", action="store_true",
                    help="refetch Schedule 9 actuals even if cached")
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
        save_cache(year, *fetch_year(year))

    cached = load_cached_years()
    if not cached:
        sys.exit("No fiscal years cached — nothing to write.")
    gate = gate_years(cached)          # raises SystemExit; nothing written
    payload = build_payload(cached)
    payload["meta"]["gate"] = {
        "control": "DOF stateGrandTotal (published on every /statistics row)",
        "basis": "General + Special + Bond, in thousands, unrounded",
        "level": "agency",
        "years": {y: {"agencyRowsK": r["totalK"], "publishedControlK": r["controlK"],
                      "residualK": r["residualK"]} for y, r in gate.items()},
        "sourceResidualNote":
            "For FY 2025-26 the Department of Finance's own published statewide "
            "total exceeds the sum of its own twelve published agency rows by "
            "$1.638 million (0.0005%). That difference is DOF's, not this "
            "record's: the agency figures here are DOF's as published. The "
            "Ledger reports them unchanged rather than reconciling the "
            "difference away, and the build fails if the difference changes.",
        "limits": [
            "The gate is at agency level. It cannot be pushed down to "
            "departments: agencies carry items with no department attribution, "
            "so departments never sum to agencies in any year.",
            "It does not catch a transfer between two agencies — moving money "
            "from one to another leaves the statewide total unchanged.",
        ],
    }
    attach_actuals(payload, cached, refresh=args.refresh_actuals)

    for w in plausibility_report(payload):
        print(f"  PLAUSIBILITY WARNING: {w}", file=sys.stderr)

    write_data_js(payload)


if __name__ == "__main__":
    main()
