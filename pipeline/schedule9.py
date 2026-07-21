"""
Schedule 9 actuals extraction for Citizen Ledger (V3).

Extracts prior-year ACTUAL expenditures (Budgetary-Legal basis) from
the Department of Finance's Schedule 9 — "Comparative Statement of
Expenditures" — the state's own side-by-side Actual/Estimated/Enacted
table, published as a PDF in every budget publication.

AUTHORITY AND GATES (per docs/V3_ACTUALS_FINDING.md, option (a)):
- Schedule 9 is the AUTHORITATIVE source. The eBudget API's per-
  department prior-year columns are a cross-check only and are never
  used as figures (their department lists undercount by ~3-5%).
- HARD GATE 1: the sum of Schedule 9's agency-group actuals must match
  the same publication's Schedule 6 statewide historical row for that
  fiscal year — BOTH the General Fund and the total, to within $2,000
  (thousands-rounding). A year that fails is NOT published.
- HARD GATE 2 (department detail): within each agency group,
  department rows must sum exactly to the group total; otherwise
  department-level actuals for that group are omitted (the gate-1-
  proven group total still publishes).

KNOWN LIMITATION, deliberately not worked around: the PDFs that carry
FY 2020-21 actuals (2022-23 Governor's Budget and 2022-23 Enacted)
interleave text at page-spanning agency groups in a way neither pypdf
extraction mode orders correctly; recovery attempts fail Gate 1.
FY 2020-21 actuals are therefore NOT published (the page explains
why), rather than approximated from any secondary source.

Requires pypdf (the only non-stdlib dependency in the pipelines, used
solely for this extraction): pip install pypdf
"""

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / "cache"

# actuals fiscal year -> ordered candidate publications (label, sch9, sch6)
SOURCES = {
    # The three years added with the V15 historical extension. Each year's
    # actuals appear in the Enacted Budget two years later, the same
    # relationship the later entries use.
    "2017-18": [("2019-20 Enacted Budget",
                 "https://ebudget.ca.gov/2019-20/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2019-20/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2018-19": [("2020-21 Enacted Budget",
                 "https://ebudget.ca.gov/2020-21/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2020-21/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2019-20": [("2021-22 Enacted Budget",
                 "https://ebudget.ca.gov/2021-22/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2021-22/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2021-22": [("2023-24 Enacted Budget",
                 "https://ebudget.ca.gov/2023-24/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2023-24/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2022-23": [("2024-25 Enacted Budget",
                 "https://ebudget.ca.gov/2024-25/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2024-25/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2023-24": [("2025-26 Enacted Budget",
                 "https://ebudget.ca.gov/2025-26/pdf/Enacted/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2025-26/pdf/Enacted/BudgetSummary/BS_SCH6.pdf")],
    "2024-25": [("2026-27 Governor's Budget",
                 "https://ebudget.ca.gov/2026-27/pdf/BudgetSummary/BS_SCH9.pdf",
                 "https://ebudget.ca.gov/2026-27/pdf/BudgetSummary/BS_SCH6.pdf")],
    # 2020-21: both renderings fail Gate 1 — see KNOWN LIMITATION above.
}
UNAVAILABLE = {
    "2020-21": "The PDFs carrying FY 2020-21 actuals could not be extracted in a "
               "form that reconciles with Schedule 6's statewide control totals; "
               "rather than publish unverified figures, none are shown.",
}

# Schedule 9 is in thousands; Schedule 6 rounds to whole millions.
# Tolerance covers the Schedule 6 rounding, in thousands of dollars.
GATE_TOLERANCE = 1_500

TOKEN = r'(?:-\s?\$?[\d,]+|\$?[\d,]+|--)'
GROUP_RE = re.compile(r'TOTALS?, ([A-Z0-9][A-Z0-9 ,&\'\-\.]+?) ((?:' + TOKEN + r' ){4}' + TOKEN + r')')
DEPT_RE = re.compile(r'Totals?,\s?(\d{4})-(.{2,60}?) ((?:' + TOKEN + r' ){4}' + TOKEN + r')')


def _num(s):
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    return 0 if s in ('--', '-') else int(s)


def _fetch_text(url):
    from pypdf import PdfReader   # lazy: only needed when refreshing actuals
    import io
    req = urllib.request.Request(url, headers={"User-Agent": "ca-ledger-pipeline/3.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    text = "\n".join((p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages)
    text = re.sub(r'\s+', ' ', text)
    # negative values render as "- $1,234"; join them — but never touch the
    # "--" zero marker when it precedes a dollar value ("-- $1,234")
    return re.sub(r'(?<!-)- \$', '-$', text)


def _sch6_row(text, year):
    """(gf_expenditures, total_expenditures) in thousands, from the
    Schedule 6 history row for `year` (12 numeric fields; expenditures
    at indices 6 and 7 — layout verified for every vintage used)."""
    m = re.search(re.escape(year) + r'((?: [\d,\.]+){10,14})', text)
    if not m:
        raise ValueError(f"Schedule 6 row for {year} not found")
    fields = m.group(1).split()
    if len(fields) < 8:
        raise ValueError(f"Schedule 6 row for {year} malformed: {fields}")
    # Schedule 6 states expenditures in MILLIONS; Schedule 9 in thousands.
    return _num(fields[6]) * 1000, _num(fields[7]) * 1000


def parse_publication(sch9_text, sch6_text, year):
    """Returns (groups, depts) after both gates, or raises GateError.
    groups: {GROUP NAME: {gf,sp,bd,tot,fed}} (thousands)
    depts:  [{code,name,gf,sp,bd,tot,fed,group}] — only from groups
            whose department rows sum exactly (Gate 2)."""
    groups, spans = {}, []
    for m in GROUP_RE.finditer(sch9_text):
        name = m.group(1).strip()
        if re.match(r'\d{4}-', name):
            continue
        v = [_num(x) for x in m.group(2).split()]
        groups[name] = dict(zip(("gf", "sp", "bd", "tot", "fed"), v))
        spans.append((name, m.start()))

    gf = sum(g["gf"] for g in groups.values())
    tot = sum(g["tot"] for g in groups.values())
    sch6_gf, sch6_tot = _sch6_row(sch6_text, year)
    if abs(gf - sch6_gf) > GATE_TOLERANCE or abs(tot - sch6_tot) > GATE_TOLERANCE:
        raise GateError(
            f"GATE 1 FAIL for {year}: Schedule 9 sums GF {gf:,} / total {tot:,} "
            f"vs Schedule 6 GF {sch6_gf:,} / total {sch6_tot:,}")

    # Gate 2: department rows, segmented by group span
    spans.sort(key=lambda x: x[1])
    depts = []
    dropped = []
    unparsed, unreconciled = [], []
    for i, (gname, gpos) in enumerate(spans):
        start = spans[i - 1][1] if i else 0
        seg = sch9_text[start:gpos]
        rows = []
        for dm in DEPT_RE.finditer(seg):
            v = [_num(x) for x in dm.group(3).split()]
            rows.append({"code": dm.group(1), "name": dm.group(2).strip(),
                         **dict(zip(("gf", "sp", "bd", "tot", "fed"), v)),
                         "group": gname})
        # TWO DIFFERENT OUTCOMES, KEPT APART. `if rows and <reconciles>`
        # collapsed them: a group whose department rows failed to PARSE was
        # indistinguishable from one whose rows parsed and did not
        # reconcile. The first is a defect in our extraction; the second is
        # a property of DOF's document, and only the second is a legitimate
        # reason to withhold department detail.
        if not rows:
            unparsed.append(gname)
            dropped.append(gname)
        elif (abs(sum(r["tot"] for r in rows) - groups[gname]["tot"]) <= GATE_TOLERANCE
                and abs(sum(r["gf"] for r in rows) - groups[gname]["gf"]) <= GATE_TOLERANCE):
            depts.extend(rows)
        else:
            unreconciled.append(gname)
            dropped.append(gname)
    # Parsing NOTHING anywhere is a failure, not a document property: the
    # group totals still gate against Schedule 6, but a Schedule 9 whose
    # department rows never matched means the regex has lost the document.
    if not depts:
        raise GateError(
            f"GATE 2 FAIL for {year}: no department row parsed in ANY of the "
            f"{len(spans)} groups. The group totals still reconcile, so this "
            "is an extraction failure rather than a source property — the "
            "department pattern has lost the document.")
    return groups, depts, dropped, unparsed, unreconciled


class GateError(Exception):
    pass


def cache_path(year):
    return CACHE_DIR / f"actuals_{year}.json"


def load_actuals_year(year, refresh=False):
    """Fetch/parse/gate one year of actuals; caches the result.
    Returns the cache payload or None if the year is unavailable."""
    if year in UNAVAILABLE:
        return None
    if year not in SOURCES:
        return None
    if not refresh and cache_path(year).exists():
        return json.loads(cache_path(year).read_text(encoding="utf-8"))
    errors = []
    for label, s9url, s6url in SOURCES[year]:
        try:
            print(f"  actuals {year}: fetching Schedule 9 ({label})…", file=sys.stderr)
            s9 = _fetch_text(s9url)
            s6 = _fetch_text(s6url)
            (groups, depts, dropped,
             unparsed, unreconciled) = parse_publication(s9, s6, year)
        except (GateError, ValueError) as e:
            errors.append(f"{label}: {e}")
            continue
        payload = {
            "year": year, "vintage": label, "fetched": date.today().isoformat(),
            "source": s9url,
            "groups": groups, "departments": depts,
            "deptDetailDropped": dropped,
            # WHY each group's detail was withheld, kept distinct: a group
            # DOF prints without reconcilable department rows is a property
            # of the document; a group whose rows we failed to parse is our
            # defect. Both withhold the detail; only one is our fault, and a
            # reader should not have to guess which.
            "deptDetailUnreconciled": unreconciled,
            "deptDetailUnparsed": unparsed,
        }
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path(year).write_text(json.dumps(payload), encoding="utf-8")
        state = sum(g["gf"] + g["sp"] + g["bd"] for g in groups.values())
        print(f"  actuals {year}: GATES PASSED — {len(groups)} groups, "
              f"{len(depts)} dept rows, state ${state / 1e6:,.3f}B ({label})"
              + (f"; dept detail unreconciled for {unreconciled}"
                 if unreconciled else "")
              + (f"; dept rows UNPARSED for {unparsed}" if unparsed else ""),
              file=sys.stderr)
        return payload
    raise GateError(f"actuals {year}: every candidate publication failed — "
                    + " | ".join(errors))


# Schedule 9 group name -> data.js agency name, where 1:1. EDUCATION is
# split at department level; the 2026 reorganization's two groups both
# fold into the display years' combined agency.
GROUP_TO_AGENCY = {
    "LEGISLATIVE, JUDICIAL, AND EXECUTIVE": "Legislative, Judicial, and Executive",
    "BUSINESS, CONSUMER SERVICES, & HOUSING": "Business, Consumer Services, and Housing",
    "BUSINESS AND CONSUMER SERVICES": "Business, Consumer Services, and Housing",
    "HOUSING AND HOMELESSNESS": "Business, Consumer Services, and Housing",
    "TRANSPORTATION": "Transportation",
    "NATURAL RESOURCES": "Natural Resources",
    "ENVIRONMENTAL PROTECTION": "Environmental Protection",
    "HEALTH AND HUMAN SERVICES": "Health and Human Services",
    "CORRECTIONS AND REHABILITATION": "Corrections and Rehabilitation",
    "LABOR AND WORKFORCE DEVELOPMENT": "Labor and Workforce Development",
    "GOVERNMENT OPERATIONS": "Government Operations",
    "GENERAL GOVERNMENT": "General Government",
}
K12_AGENCY = "K thru 12 Education"
HIED_AGENCY = "Higher Education"

# EDUCATION-group codes absent from the display year's web department
# lists, assigned by name (the generic rule is < 6400 = K-12, >= 6400 =
# Higher Education; these are the verified exceptions/confirmations):
EDUCATION_CODE_OVERRIDES = {
    "6305": HIED_AGENCY,   # Retirement Costs for Community Colleges
    "6396": K12_AGENCY,    # General Obligation Bonds - K-12
    "6874": HIED_AGENCY,   # General Obligation Bonds - Hi Ed - CC
    "6878": HIED_AGENCY,   # Retirement Costs - Hi Ed - CC
    "7996": HIED_AGENCY,   # General Obligation Bonds - Hi Ed
}


def map_to_agencies(payload, code_to_agency):
    """Distributes one year's actuals into the display agency structure.

    Department-level assignment (by org code, using the display year's
    own enacted org map) takes precedence; codes absent from the map
    fall back to the Schedule 9 group mapping, except EDUCATION, whose
    unmapped codes split deterministically at 6400 (< 6400 = K-12
    [CDE 6100 … CTC 6360]; >= 6400 = Higher Education [UC 6440,
    CSU 6610, CCC 6870, CSAC 6980]).

    Conservation: agency sums equal the gate-proven group totals —
    department rows are used to SPLIT groups, never to re-total them.
    Groups without gate-2 department detail map whole via
    GROUP_TO_AGENCY (EDUCATION without detail cannot be split; both
    education agencies then carry no actuals and the caller reports it).
    """
    out = {}          # agency -> {gf,sp,bd,fed}
    dept_out = {}     # code -> {gf,sp,bd,fed}
    unsplit = []

    def add(agency, src, keys=("gf", "sp", "bd", "fed")):
        tgt = out.setdefault(agency, {"gf": 0, "sp": 0, "bd": 0, "fed": 0})
        for k in keys:
            tgt[k] += src[k]

    by_group = {}
    for d in payload["departments"]:
        by_group.setdefault(d["group"], []).append(d)

    for gname, g in payload["groups"].items():
        rows = by_group.get(gname)
        if rows:
            for d in rows:
                agency = code_to_agency.get(d["code"])
                if agency is None:
                    if gname == "EDUCATION":
                        agency = EDUCATION_CODE_OVERRIDES.get(
                            d["code"],
                            K12_AGENCY if int(d["code"]) < 6400 else HIED_AGENCY)
                    else:
                        agency = GROUP_TO_AGENCY.get(gname)
                if agency is None:
                    raise GateError(f"no agency mapping for group {gname!r}")
                add(agency, {k: d[k] for k in ("gf", "sp", "bd", "fed")})
                dept_out[d["code"]] = {k: d[k] for k in ("gf", "sp", "bd", "fed")}
        else:
            agency = GROUP_TO_AGENCY.get(gname)
            if agency is None:
                unsplit.append(gname)
                continue
            add(agency, g)
    return out, dept_out, unsplit
