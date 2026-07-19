#!/usr/bin/env python3
"""
Citizen Ledger — K-12 schools pipeline (V7, option (a): gated and
comparable, comparison scoped to school districts).

Rebuilds ../school-data.js from the California Department of
Education's SACS unaudited-actuals archives.

Sources per fiscal year (verified in docs/V7_SCHOOLS_FINDING.md):
  https://www3.cde.ca.gov/fiscal-downloads/sacs_data/{YYYY-YY}/sacs{yy}.exe
      → sacs{yy}.mdb  (JET4; UserGL general ledger, UserGL_Totals =
        CDE's own county/state rollups, LEAs, Charters, code tables)
  https://www3.cde.ca.gov/fiscal-downloads/charterdata/{YYYY-YY}/alt{yy}data.exe
      → alt{yy}data.mdb (charter Alternative Form + its own totals)
  https://www.cde.ca.gov/ds/fd/ec/documents/currentexpense{yy}.xlsx
      → CDE-published per-district Current Expense of Education
        (EDP 365) with ADA — THE GATE TARGET
  https://www.cde.ca.gov/fg/aa/pa/documents/lcffsummary{yy}.xlsx
      → LCFF entitlement / local revenue (basic-aid flag), COE funded
        ADA

THE GATE (no write on failure, and it is exact):
  1. Every published district's EDP 365 must be REPRODUCED FROM THE
     RAW GENERAL LEDGER to within $0.05 (the investigation reproduced
     932/932 to the cent for FY 2024-25; one $0.02 publication
     rounding artifact exists in FY 2023-24). The formula is CDE's:
     Fund 01; objects 1000-5999, 6500, 7300-7399; minus goals
     7100-7199 and 8100, functions 3700 and 8500, objects 3701-3702;
     district-entity rows only (SchoolCode '0000000').
  2. Aggregating raw UserGL must reproduce CDE's own UserGL_Totals —
     every state cell and every county cell (fund × object) — and
     the Alternative Form data must reproduce its own totals table.
  3. Structural: 58 COEs; the published district count; ADA present.

TIERS ENCODED (per the approved finding):
  - districts: gated per-LEA against a published figure; compared
    per-ADA with three data-derived daggers (basic aid, small-ADA
    funding floors, sponsored-charter distortion) plus the
    commingled-charter limit stated on affected records.
  - county offices: records only, never compared (CDE itself excludes
    them from its per-ADA statistic).
  - charters that file separately (own SACS or Alternative Form):
    records only, gated through the rollups.
  - charters reported inside an authorizer's books: named directory
    entries pointing at the authorizer; the Fund 01 commingled subset
    cannot be separated and the affected district records say so.
  - JPAs (ROPs/SELPAs): out of scope for records in this version;
    their dollars are inside the rollup gates.

THE OVERLAP BLOCK (meta.overlap) is computed here on every run —
statewide LEA revenues by source from the ledger, against the state
layer's K-12 agency read from ../data.js — so the UI's
figures-do-not-add statement renders live values and hardcodes none.

Usage:
    python3 fetch_school_data.py            # dry run: fetch + gates
    python3 fetch_school_data.py --write    # rebuild ../school-data.js
Requires: mdbtools (mdb-export) and openpyxl — pipeline-only deps,
like pypdf for the state actuals.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "schools"
OUT_PATH = ROOT / "school-data.js"

# NCES LEA ids for the address view's identifier-based matching: the
# Census geocoder's school-district GEOID equals the NCES LEA id, and
# CDE's public directory carries NCESDist per district. Five SACS
# filers are common-administration arrangements (two legal districts
# filing one report, per CDE's readme); the directory lists their
# CONSTITUENT districts, so those constituents' NCES ids map to the
# filer. This constant is the documented administrative structure,
# verified against the directory — not name matching.
PUBSCHLS = CACHE / "pubschls.txt"   # CDE directory export (live URL is
# bot-gated; obtainable via web.archive.org snapshot of
# https://www.cde.ca.gov/schooldirectory/report?rid=dl1&tp=txt)
COMMON_ADMIN_NCES = {
    "0603090": "2376349", "0631230": "2376349",   # Arena Union / Point Arena
    "0625130": "5040717", "0625150": "5040717",   # Modesto City Elem / High
    "0630230": "4940246", "0630250": "4940246",   # Petaluma Elem / JUH
    "0635590": "4440261", "0635600": "4440261",   # Santa Cruz City Elem / High
    "0635810": "4940253", "0635830": "4940253",   # Santa Rosa Elem / High
}

YEARS = [("2223", "2022-23"), ("2324", "2023-24"), ("2425", "2024-25")]
GATE_TOL = 0.05          # per-district vs published EDP 365
ROLLUP_TOL = 0.05        # per fund×object cell vs CDE's own totals

COUNTIES = [  # CDE county codes are alphabetical, 01..58
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras", "Colusa",
    "Contra Costa", "Del Norte", "El Dorado", "Fresno", "Glenn",
    "Humboldt", "Imperial", "Inyo", "Kern", "Kings", "Lake", "Lassen",
    "Los Angeles", "Madera", "Marin", "Mariposa", "Mendocino", "Merced",
    "Modoc", "Mono", "Monterey", "Napa", "Nevada", "Orange", "Placer",
    "Plumas", "Riverside", "Sacramento", "San Benito", "San Bernardino",
    "San Diego", "San Francisco", "San Joaquin", "San Luis Obispo",
    "San Mateo", "Santa Barbara", "Santa Clara", "Santa Cruz", "Shasta",
    "Sierra", "Siskiyou", "Solano", "Sonoma", "Stanislaus", "Sutter",
    "Tehama", "Trinity", "Tulare", "Tuolumne", "Ventura", "Yolo", "Yuba"]

FN_GROUPS = [
    ("instruction",   "Instruction",                    1000, 1999),
    ("instrRelated",  "Instruction-related services",   2000, 2999),
    ("pupilServices", "Pupil services",                 3000, 3999),
    ("ancillary",     "Ancillary services",             4000, 4999),
    ("community",     "Community services",             5000, 5999),
    ("enterprise",    "Enterprise",                     6000, 6999),
    ("genAdmin",      "General administration",         7000, 7999),
    ("plant",         "Plant services",                 8000, 8999),
    ("otherOutgo",    "Other outgo",                    9000, 9999),
]
OBJ_FAMILIES = [
    ("certSalaries",  "Certificated salaries",  1000, 1999),
    ("classSalaries", "Classified salaries",    2000, 2999),
    ("benefits",      "Employee benefits",      3000, 3999),
    ("supplies",      "Books & supplies",       4000, 4999),
    ("services",      "Services & operations",  5000, 5999),
    ("capital",       "Capital outlay",         6000, 6999),
    ("otherOutgo",    "Other outgo",            7000, 7999),
]


def download(url, dest):
    if dest.exists():
        return
    print(f"  downloading {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "ca-ledger-pipeline/1.0"})
    dest.write_bytes(urllib.request.urlopen(req, timeout=600).read())


def ensure_year_files(yy, fy_dashed):
    CACHE.mkdir(parents=True, exist_ok=True)
    files = {
        "sacs_exe": (f"https://www3.cde.ca.gov/fiscal-downloads/sacs_data/"
                     f"{fy_dashed}/sacs{yy}.exe", CACHE / f"sacs{yy}.exe"),
        "alt_exe":  (f"https://www3.cde.ca.gov/fiscal-downloads/charterdata/"
                     f"{fy_dashed}/alt{yy}data.exe", CACHE / f"alt{yy}data.exe"),
        "ce":   (f"https://www.cde.ca.gov/ds/fd/ec/documents/currentexpense{yy}.xlsx",
                 CACHE / f"currentexpense{yy}.xlsx"),
        "lcff": (f"https://www.cde.ca.gov/fg/aa/pa/documents/lcffsummary{yy}.xlsx",
                 CACHE / f"lcffsummary{yy}.xlsx"),
    }
    for key in ("ce", "lcff"):
        download(*files[key])
    for key, mdb_name in (("sacs_exe", f"sacs{yy}.mdb"), ("alt_exe", f"alt{yy}data.mdb")):
        mdb = CACHE / mdb_name
        if not mdb.exists():
            url, exe = files[key]
            download(url, exe)
            with zipfile.ZipFile(exe) as z:   # the .exe is ZIP-compatible
                inner = [n for n in z.namelist() if n.lower().endswith(".mdb")][0]
                mdb.write_bytes(z.read(inner))
    return CACHE / f"sacs{yy}.mdb", CACHE / f"alt{yy}data.mdb", files["ce"][1], files["lcff"][1]


def mdb_rows(mdb, table):
    proc = subprocess.Popen(["mdb-export", str(mdb), table],
                            stdout=subprocess.PIPE, text=True)
    for row in csv.DictReader(proc.stdout):
        yield row
    proc.stdout.close()
    if proc.wait() != 0:
        raise SystemExit(f"mdb-export failed for {mdb}:{table}")


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def assign_slugs(records, label):
    """Deterministic, collision-free slugs — the identifier contract.

    `records` is a list of (identity, name, qualifier) where `identity`
    is the source's own stable code (CDS for districts and county
    offices, the charter key for charters). The slug is a function of
    the published name alone when that name is unique, and of the name
    plus its qualifier when it is not — so no entity ever wins a bare
    slug that another entity of the same name could have won instead.

    Two properties this guarantees, both asserted in the test suite:

      1. The result depends only on the source data, never on the order
         Python happened to iterate a set. The old code sorted a set of
         code tuples keyed on the NAME alone, so for the duplicated
         names the tie was broken by set-iteration order — i.e. by
         PYTHONHASHSEED, which Python randomizes per process. The same
         source produced a different school-data.js, and therefore a
         different published SHA-256, on every run.
      2. Every name that is shared is disambiguated for EVERY holder of
         it. Letting one of three "Jefferson Elementary" districts hold
         the unqualified slug is a claim we cannot support: it names one
         district with an identifier that describes three.

    Raises rather than guessing if a qualifier fails to disambiguate.

    Returns (slug_by_identity, ambiguous), where `ambiguous` maps each
    unqualified slug that is NOT issued to the qualified slugs that
    share that name. Earlier builds handed the unqualified slug to an
    arbitrary one of them, so links using it are genuinely ambiguous —
    that map lets the page say which entities a stale link could have
    meant instead of silently picking one.
    """
    by_name = defaultdict(list)
    for ident, name, qualifier in records:
        by_name[slugify(name)].append((ident, name, qualifier))
    out, ambiguous = {}, {}
    for base in sorted(by_name):
        group = sorted(by_name[base], key=lambda r: r[0])
        if len(group) == 1:
            out[group[0][0]] = base
            continue
        for ident, name, qualifier in group:
            out[ident] = slugify(name + "-" + str(qualifier))
        ambiguous[base] = sorted(out[ident] for ident, _, _ in group)
    if len(set(out.values())) != len(out):
        dupes = sorted(s for s in set(out.values())
                       if list(out.values()).count(s) > 1)
        raise SystemExit(
            f"SLUG COLLISION in {label} after qualification: {dupes} — "
            "the qualifier does not disambiguate these records. "
            "Nothing written; a human must choose a stable identifier.")
    return out, ambiguous


def fn_group(code):
    if code.isdigit():
        n = int(code)
        for key, _, lo, hi in FN_GROUPS:
            if lo <= n <= hi:
                return key
    return "otherOutgo"


def obj_family(n):
    for key, _, lo, hi in OBJ_FAMILIES:
        if lo <= n <= hi:
            return key
    return "otherOutgo"


# CSAM Procedure 310 assigns the funding source of a resource ONLY by
# number range (there is no per-code source column in any CDE artifact).
# Ranges, verbatim: 0000-1999 unrestricted; 2000-9999 restricted, of
# which 3000-5999 federal, 6000-7999 state, 8000-9999 local. CDE assigns
# NO source to 2000-2999 (it sits before the federal block); we surface
# that range as its own group and never file it under a source. This
# grouping is the restricted/unrestricted split, finer: "unrestricted"
# here equals resource < 2000, exactly as edp_restr splits it — so the
# resource partition can never disagree with the displayed split.
RES_GROUPS = [
    ("unrestricted",    "Unrestricted"),
    ("federal",         "Federal restricted"),
    ("state",           "State restricted"),
    ("local",           "Local restricted"),
    ("restrictedOther", "Restricted — other (CDE assigns no source range)"),
]
STRS_ON_BEHALF_RES = "7690"   # On-Behalf Pension Contributions (state pays
# CalSTRS directly on the district's behalf; booked as object 3101 within
# resource 7690, entirely inside Current Expense — the district never
# touches this cash). Always shown as its own named row so a group total
# is never read as district-controlled spending. See face note below.
ELOP_RES = "2600"             # Expanded Learning Opportunities Program —
# the one live code in the unassigned 2000-2999 range; shown by name.
NAMED_FLOOR = 1_000_000.0     # named rows at >= $1M; the rest combine into
# an exact-remainder tail per group (the finding's hybrid).


def res_group(code):
    """Resource -> CSAM funding-source group. Non-digit codes fold into
    unrestricted, matching edp_restr's `isdigit() and >= 2000` rule, so
    the two views are one partition (empirically no alpha codes appear in
    Current Expense in any shipped vintage)."""
    if not code.isdigit():
        return "unrestricted"
    n = int(code)
    if n < 2000:
        return "unrestricted"
    if n < 3000:
        return "restrictedOther"
    if n < 6000:
        return "federal"
    if n < 8000:
        return "state"
    return "local"


OBJ_ORDER = [k for k, _, _, _ in OBJ_FAMILIES]


def obj_cells(res_obj):
    """V10a reduced cross-tab: the object-family split of ONE resource, as
    a fixed OBJ_FAMILIES-ordered whole-dollar array that sums EXACTLY to
    the resource's whole-dollar display value. The largest cell absorbs
    the rounding remainder (the same exact-remainder trick the group tails
    use), so the object breakdown ties to the resource total to the cent
    and the resource value is unchanged from V9. Trailing zeros trimmed.
    Returns (display_value, array)."""
    cents = {k: round(res_obj.get(k, 0.0), 2) for k in OBJ_ORDER}
    dv = round(round(sum(cents.values()), 2))     # == V9's round(resource$)
    dollars = {k: round(cents[k]) for k in OBJ_ORDER}
    diff = dv - sum(dollars.values())
    if diff:
        big = max(OBJ_ORDER, key=lambda k: (abs(dollars[k]), k))
        dollars[big] += diff
    arr = [dollars[k] for k in OBJ_ORDER]
    while arr and arr[-1] == 0:
        arr.pop()
    return dv, arr


def build_by_resource(res_map, res_obj_map=None):
    """The finding's hybrid, per district-year: CSAM-range groups, named
    rows for resources >= $1M (STRS on-behalf 7690 always named so it is
    never buried in a group total), and one exact-remainder tail per
    group. Named rows carry whole dollars (funding sources render as
    $Xm / per-ADA, never to the cent); the tail absorbs the remainder so
    every group STILL sums to the cent — group total = sum(named) + tail,
    and sum(group totals) = the gated Current Expense, exactly.
    When res_obj_map is given (V10a), each named row also carries its
    object-family split [code, whole$, [obj array]] — the reduced
    object × resource cross-tab, summing to the row's own total.
    Returns {group: {total (cents), named:[[code, whole$, obj?]], tail}}."""
    grouped = defaultdict(list)          # group -> [(code, value)]
    for code, v in res_map.items():
        grouped[res_group(code)].append((code, round(v, 2)))
    out = {}
    for gkey, _ in RES_GROUPS:
        rows = grouped.get(gkey, [])
        total = round(sum(v for _, v in rows), 2)
        named, named_sum = [], 0.0
        for code, v in sorted(rows, key=lambda cv: (-abs(cv[1]), cv[0])):
            if abs(v) >= NAMED_FLOOR or code == STRS_ON_BEHALF_RES:
                dv = round(v)            # whole dollars for display rows
                row = [code, dv]
                if res_obj_map is not None:
                    odv, arr = obj_cells(res_obj_map.get(code, {}))
                    row = [code, odv, arr]   # odv == dv by construction
                named.append(row)
                named_sum += dv
        out[gkey] = {"total": total, "named": named,
                     "tail": round(total - named_sum, 2)}
    return out


def slim_by_resource(by, named):
    """Ship the group total (`v`) for every non-empty group, every year —
    that is the funding-source answer, gated to the cent and nesting into
    restricted/unrestricted. The named-code rows (`n`) and their
    exact-remainder tail (`t`) are shipped for the latest year only: three
    years of every $1M+ code would be ~+18% on the file, so the finding's
    hybrid is held to the payload discipline by carrying the named detail
    on the current year and the group totals on all years. The pipeline
    still GATES the full breakout at full fidelity in every year."""
    out = {}
    for gkey, d in by.items():
        if abs(d["total"]) < 0.005 and not d["named"]:
            continue
        o = {"v": d["total"]}
        if named:
            if d["named"]:
                o["n"] = d["named"]
            if abs(d["tail"]) >= 0.005:
                o["t"] = d["tail"]
        out[gkey] = o
    return out


def edp_in_scope(obj, goal, func):
    """CDE's Current Expense of Education (EDP 365) row filter."""
    in_objects = (1000 <= obj <= 5999) or obj == 6500 or (7300 <= obj <= 7399)
    if not in_objects:
        return False
    gnum = int(goal) if goal.isdigit() else -1
    if 7100 <= gnum <= 7199 or goal == "8100":
        return False
    if func in ("3700", "8500"):
        return False
    if obj in (3701, 3702):
        return False
    return True


REV_GROUPS = (  # (key, ranges) — revenue objects, per the V7 finding
    ("lcffStateAid", [(8011, 8011), (8012, 8012), (8015, 8015), (8019, 8019)]),
    ("propertyTaxes", [(8020, 8089)]),
    ("lcffTransfers", [(8090, 8099)]),
    ("federal", [(8100, 8299)]),
    ("otherState", [(8300, 8599)]),
    ("localOther", [(8600, 8799)]),
)


def rev_group(n):
    for key, ranges in REV_GROUPS:
        for lo, hi in ranges:
            if lo <= n <= hi:
                return key
    return None


def process_year(yy, fy):
    sacs, alt, ce_path, lcff_path = ensure_year_files(yy, fy)
    import openpyxl

    # ---- LEA + charter registries
    leas = {}
    for r in mdb_rows(sacs, "LEAs"):
        leas[(r["Ccode"], r["Dcode"])] = {
            "name": r["Dname"].strip(), "type": r["Dtype"].strip(),
            "ada": float(r["K12ADA"] or 0)}
    charters = {}
    for r in mdb_rows(sacs, "Charters"):
        charters[(r["Ccode"], r["Dcode"], r["SchoolCode"])] = {
            "name": r["CharterName"].strip(),
            "number": r["CharterNumber"].strip(),
            "level": r["ReportLevel"].strip(), "fund": (r.get("FundUsed") or "").strip(),
            "type": (r.get("ReportType") or "").strip(),
            "ada": float(r["K12ADA"] or 0)}
    n_coe = sum(1 for v in leas.values() if v["type"].startswith("County Office"))
    if n_coe != 58:
        raise SystemExit(f"FY {fy}: {n_coe} COEs (expected 58) — nothing written")

    # ---- resource titles: CDE's OWN names, from THIS year's table only
    # (titles drift across vintages — 46 retitles in our window — so they
    # are never crosswalked across years; the FY2017 vintage lesson).
    res_title = {}
    for r in mdb_rows(sacs, "Resource"):
        res_title[r["Code"].strip()] = r["Title"].strip()

    # ---- stream the general ledger once
    edp = defaultdict(float)                 # (c,d) -> EDP365
    edp_fn = defaultdict(lambda: defaultdict(float))
    edp_fn_obj = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    edp_restr = defaultdict(lambda: [0.0, 0.0])   # [unrestricted, restricted]
    edp_by_res = defaultdict(lambda: defaultdict(float))    # (c,d) -> code -> $
    edp_res_obj = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    edp_by_obj = defaultdict(lambda: defaultdict(float))    # (c,d) -> objfam -> $
    edp_fn_grp = defaultdict(lambda: defaultdict(float))    # (c,d) -> (fn,grp) -> $
    res_stats = defaultdict(float)   # statewide: strsOnBehalf, indirect_<grp>
    coe_fn = defaultdict(lambda: defaultdict(float))
    coe_tot = defaultdict(float)
    charter_gl = defaultdict(lambda: defaultdict(float))   # (c,d,s) -> family
    charter_gl_tot = defaultdict(float)
    dep_funds_exp = defaultdict(float)       # (c,d) -> fund 09/62 exp
    rev = defaultdict(float)
    rev_detail = defaultdict(float)          # epa 8012, strs 8590, lottery 8560, passthrough
    rollup = defaultdict(float)              # ("99" or ccode, fund, object) -> value
    for r in mdb_rows(sacs, "UserGL"):
        c, d, s = r["Ccode"], r["Dcode"], r["SchoolCode"]
        obj_s, fund = r["Object"], r["Fund"]
        v = float(r["Value"] or 0)
        rollup[("99", fund, obj_s)] += v
        rollup[(c, fund, obj_s)] += v
        obj = int(obj_s) if obj_s.isdigit() else -1
        if obj < 0:
            continue
        lea = leas.get((c, d))
        is_coe = lea and lea["type"].startswith("County Office")
        if 8000 <= obj <= 8799:
            g = rev_group(obj)
            if g:
                rev[g] += v
            if obj == 8012: rev_detail["epa"] += v
            # STRS on-behalf is object 8590 within resource 7690 only —
            # bare 8590 is the whole "all other state revenue" bucket
            if obj == 8590 and r["Resource"] == "7690":
                rev_detail["strsOnBehalf"] += v
            if obj == 8560: rev_detail["lottery"] += v
            if obj in (8287, 8587, 8697) or 8781 <= obj <= 8799:
                rev_detail["passThrough"] += v
            continue
        if not (1000 <= obj <= 9999):
            continue
        if s != "0000000":
            if 1000 <= obj <= 7999:
                charter_gl[(c, d, s)][obj_family(obj)] += v
                charter_gl_tot[(c, d, s)] += v
            continue
        if fund == "01":
            if edp_in_scope(obj, r["Goal"], r["Function"]):
                edp[(c, d)] += v
                g = fn_group(r["Function"])
                edp_fn[(c, d)][g] += v
                # V8 depth: object family within the gated scope, and the
                # restricted/unrestricted split (resource >= 2000 is
                # restricted, SACS's own definition)
                edp_fn_obj[(c, d)][g][obj_family(obj)] += v
                res = r["Resource"].strip()
                restricted = res.isdigit() and int(res) >= 2000
                edp_restr[(c, d)][1 if restricted else 0] += v
                # V9: funding source. Resource dollars per district, and
                # the function × resource-group cross-tab that must
                # reproduce every function total.
                edp_by_res[(c, d)][res] += v
                # V10a: the reduced object × resource cross-tab — object
                # family within each resource, and the plain object-family
                # margin the aggregate must reconcile to.
                of = obj_family(obj)
                edp_res_obj[(c, d)][res][of] += v
                edp_by_obj[(c, d)][of] += v
                edp_fn_grp[(c, d)][(g, res_group(res))] += v
                if res == STRS_ON_BEHALF_RES:
                    res_stats["strsOnBehalf"] += v
                if 7300 <= obj <= 7399:      # indirect-cost transfers
                    res_stats["indirect_" + res_group(res)] += v
            if is_coe and 1000 <= obj <= 7999:
                coe_fn[(c, d)][fn_group(r["Function"])] += v
                coe_tot[(c, d)] += v
        elif fund in ("09", "62") and 1000 <= obj <= 7999:
            dep_funds_exp[(c, d)] += v

    # ---- GATE 2: CDE's own rollups, cell by cell
    published = defaultdict(float)
    for r in mdb_rows(sacs, "UserGL_Totals"):
        c, d = r["Ccode"], r["Dcode"]
        scope = "99" if (c == "99" or d == "99999") else c
        published[(scope, r["Fund"], r["Object"])] += float(r["Value"] or 0)
    bad_cells = 0
    for key, pv in published.items():
        if abs(rollup.get(key, 0.0) - pv) > ROLLUP_TOL:
            bad_cells += 1
    if bad_cells:
        raise SystemExit(f"FY {fy}: {bad_cells} rollup cells disagree with "
                         "CDE's UserGL_Totals — nothing written")

    # ---- Alternative Form charters (+ their own totals gate)
    alt_data = defaultdict(lambda: defaultdict(float))
    alt_tot = defaultdict(float)
    alt_by_obj = defaultdict(float)
    for r in mdb_rows(alt, "Alternate_Form_Data"):
        o = r["ObjectCode"]
        v = float(r["total"] or 0)
        alt_by_obj[o] += v
        n = int(o) if o.isdigit() else -1
        if 1000 <= n <= 7999:
            alt_data[(r["Ccode"], r["Dcode"], r["SchoolCode"])][obj_family(n)] += v
            alt_tot[(r["Ccode"], r["Dcode"], r["SchoolCode"])] += v
        elif 8000 <= n <= 8799:
            g = rev_group(n)
            if g:
                rev[g] += v
            if n == 8012: rev_detail["epa"] += v
            if n == 8560: rev_detail["lottery"] += v
    bad_alt = 0
    for r in mdb_rows(alt, "Alternate_Form_Totals"):
        if abs(alt_by_obj.get(r["ObjectCode"], 0.0) - float(r["total"] or 0)) > ROLLUP_TOL:
            bad_alt += 1
    if bad_alt:
        raise SystemExit(f"FY {fy}: {bad_alt} Alternative Form totals disagree "
                         "— nothing written")

    # ---- GATE 1: published Current Expense of Education, to the cent
    wb = openpyxl.load_workbook(ce_path, read_only=True)
    ws = wb["District"]
    rows = ws.iter_rows(values_only=True)
    header = None
    ce = {}
    for row in rows:
        if header is None:
            if row and str(row[0]).strip() == "CO":
                header = [str(x or "").replace("\n", " ").strip() for x in row]
            continue
        if row[0] is None:
            continue
        rec = dict(zip(header, row))
        c = str(rec["CO"]).zfill(2)
        d = str(rec["CDS"]).zfill(5)
        ce[(c, d)] = {"name": str(rec["District"]).strip(),
                      "edp": float(rec["EDP 365"]),
                      "ada": float(rec["Current Expense ADA"]),
                      "type": str(rec["LEA Type"]).strip()}
    # THE CLASSIFICATION-SHAPE GATE (hard): per district, ADA>0 implies
    # instruction dollars > 0; statewide, the core function groups must
    # be nonzero. A function-code shift would keep the to-the-cent
    # totals gate green while gutting the classification.
    shape_fail = []
    sw = defaultdict(float)
    for key, fn in edp_fn.items():
        for g, v in fn.items():
            sw[g] += v
    for g in ("instruction", "instrRelated", "pupilServices", "genAdmin", "plant"):
        if sw.get(g, 0) <= 0:
            shape_fail.append(f"statewide {g!r} is zero")
    for (c, d), pub in ce.items():
        if pub["ada"] > 0 and edp_fn.get((c, d), {}).get("instruction", 0) <= 0:
            shape_fail.append(f"{pub['name']} ({c}-{d}): ADA {pub['ada']} "
                              "but zero instruction dollars")
    if shape_fail:
        for s in shape_fail[:10]:
            print("  SHAPE FAIL:", s, file=sys.stderr)
        raise SystemExit(f"FY {fy}: {len(shape_fail)} classification-shape "
                         "failure(s) — nothing written")

    gate_fail = []
    for (c, d), pub in ce.items():
        ours = edp.get((c, d), 0.0)
        if abs(ours - pub["edp"]) > GATE_TOL:
            gate_fail.append(f"{pub['name']} ({c}-{d}): computed ${ours:,.2f} "
                             f"vs published ${pub['edp']:,.2f}")
    if gate_fail:
        for g in gate_fail[:20]:
            print("  GATE FAIL:", g, file=sys.stderr)
        raise SystemExit(f"FY {fy}: {len(gate_fail)} district(s) fail the "
                         "Current Expense gate — nothing written")

    # ---- LCFF: basic aid + COE funded ADA
    wb = openpyxl.load_workbook(lcff_path, read_only=True)
    sheet = None
    for name in wb.sheetnames:
        n = name.replace(" ", "")
        if n.endswith("Annual") or n.endswith("AN"):
            sheet = name
    if sheet is None:
        raise SystemExit(f"FY {fy}: no Annual sheet in {lcff_path.name}")
    ws = wb[sheet]
    header, basic_aid, coe_ada = None, {}, {}
    col = {}
    for row in ws.iter_rows(values_only=True):
        if header is None:
            if row and str(row[0]).strip() == "County Code":
                header = [str(x or "").strip() for x in row]
                for i, h in enumerate(header):
                    if h.startswith("Total LCFF Entitlement"): col["ent"] = i
                    elif "Local Revenue" in h: col["local"] = i
                    elif h.startswith("Total Funded ADA"): col["ada"] = i
                if len(col) < 3:
                    raise SystemExit(f"FY {fy}: LCFF columns not found ({header})")
            continue
        if row[0] is None:
            continue
        c, d, s = str(row[0]).zfill(2), str(row[1]).zfill(5), str(row[2]).zfill(7)
        def num(i):
            v = row[i]
            return float(v) if isinstance(v, (int, float)) else 0.0
        if s != "0000000":
            continue
        lea = leas.get((c, d))
        if not lea:
            continue
        if lea["type"].startswith("County Office"):
            coe_ada[(c, d)] = num(col["ada"])
        else:
            basic_aid[(c, d)] = num(col["local"]) > num(col["ent"])

    # ---- charter sponsorship / commingling per district
    sponsored = defaultdict(float)
    commingled = defaultdict(lambda: [0, 0.0])   # count, ada
    for (c, d, s), ch in charters.items():
        # ReportLevel values: CharterSchool / StateBoardOfEducation file
        # separately; SchoolDistrict / CountyOfficeOfEducation report inside
        # the authorizer. FundUsed is a word: "General" = Fund 01
        # (commingled), CharterSpecRevenue = Fund 09, CharterEnterprise = 62.
        if ch["level"] in ("CharterSchool", "StateBoardOfEducation"):
            sponsored[(c, d)] += ch["ada"]
        elif ch["level"] and ch["fund"] == "General":
            commingled[(c, d)][0] += 1
            commingled[(c, d)][1] += ch["ada"]

    # V8 PARENT-SUM GATES (hard): the depth partitions must equal the
    # gated Current Expense figure to the cent, district by district
    depth_fail = []
    for key, pub in ce.items():
        total = edp[key]
        fo = sum(v for fam in edp_fn_obj[key].values() for v in fam.values())
        ru = sum(edp_restr[key])
        if abs(fo - total) > 0.005 or abs(ru - total) > 0.005:
            depth_fail.append(f"{pub['name']}: fn×obj {fo:,.2f} / "
                              f"restr-split {ru:,.2f} vs {total:,.2f}")
    if depth_fail:
        for s in depth_fail[:8]:
            print("  V8 GATE FAIL:", s, file=sys.stderr)
        raise SystemExit(f"FY {fy}: {len(depth_fail)} depth partition(s) "
                         "do not sum to the gated figure — nothing written")

    # V9 RESOURCE GATES (hard, no write on failure): the funding-source
    # breakout must reproduce the gated figure to the cent, be a strict
    # refinement of the restricted/unrestricted split, and not distort
    # any function total.
    res_fail = []
    for key, pub in ce.items():
        total = round(edp[key], 2)
        by = build_by_resource(edp_by_res[key])
        # 1. group totals + the hybrid tails sum to Current Expense
        grp_sum = round(sum(g["total"] for g in by.values()), 2)
        disp_sum = round(sum(round(sum(v for _, v in g["named"]), 2) + g["tail"]
                             for g in by.values()), 2)
        if abs(grp_sum - total) > 0.005 or abs(disp_sum - total) > 0.005:
            res_fail.append(f"{pub['name']}: groups {grp_sum:,.2f} / "
                            f"displayed {disp_sum:,.2f} vs {total:,.2f}")
            continue
        # 2. resource partition == the displayed restricted/unrestricted
        unr = by["unrestricted"]["total"]
        restr = round(sum(by[g]["total"] for g, _ in RES_GROUPS
                          if g != "unrestricted"), 2)
        if (abs(unr - round(edp_restr[key][0], 2)) > 0.005 or
                abs(restr - round(edp_restr[key][1], 2)) > 0.005):
            res_fail.append(f"{pub['name']}: resource partition "
                            f"unr {unr:,.2f}/restr {restr:,.2f} != split "
                            f"{edp_restr[key][0]:,.2f}/{edp_restr[key][1]:,.2f}")
            continue
        # 3. function × resource-group reproduces every function total
        fn_from_grp = defaultdict(float)
        for (g, _grp), v in edp_fn_grp[key].items():
            fn_from_grp[g] += v
        for g, v in edp_fn[key].items():
            if abs(fn_from_grp[g] - v) > 0.005:
                res_fail.append(f"{pub['name']}: fn×group {g} "
                                f"{fn_from_grp[g]:,.2f} != {v:,.2f}")
                break
    if res_fail:
        for s in res_fail[:10]:
            print("  V9 GATE FAIL:", s, file=sys.stderr)
        raise SystemExit(f"FY {fy}: {len(res_fail)} resource partition(s) "
                         "fail the funding-source gates — nothing written")

    # V10a REDUCED CROSS-TAB GATES (hard, no write on failure): the
    # object × resource cross-tab must tie to BOTH margins — every
    # resource's object split sums to that resource's total, and the
    # object families aggregate across resources to the object-family
    # totals (V8), hence to Current Expense — and the SHIPPED whole-dollar
    # object arrays of the named resources must sum to each named value.
    xt_fail = []
    for key, pub in ce.items():
        ro = edp_res_obj[key]
        # margin 1: sum over object family within each resource == by_res
        for res, fams in ro.items():
            if abs(sum(fams.values()) - edp_by_res[key][res]) > 0.005:
                xt_fail.append(f"{pub['name']} res {res}: object split "
                               f"!= resource total"); break
        if xt_fail and xt_fail[-1].startswith(pub['name']):
            continue
        # margin 2: sum over resource within each object family == by_obj
        m_obj = defaultdict(float)
        for res, fams in ro.items():
            for of, v in fams.items():
                m_obj[of] += v
        bad_margin2 = any(abs(m_obj[of] - edp_by_obj[key][of]) > 0.005
                          for of in edp_by_obj[key])
        # and the whole cross-tab totals to Current Expense
        if bad_margin2 or abs(sum(m_obj.values()) - round(edp[key], 2)) > 0.05:
            xt_fail.append(f"{pub['name']}: cross-tab object margin or "
                           f"total off"); continue
        # the SHIPPED named object arrays sum to the named display value
        by = build_by_resource(edp_by_res[key], edp_res_obj[key])
        for g in by.values():
            for row in g["named"]:
                if len(row) == 3 and sum(row[2]) != row[1]:
                    xt_fail.append(f"{pub['name']} res {row[0]}: shipped "
                                   f"object array {sum(row[2])} != {row[1]}")
                    break
    if xt_fail:
        for s in xt_fail[:10]:
            print("  V10a GATE FAIL:", s, file=sys.stderr)
        raise SystemExit(f"FY {fy}: {len(xt_fail)} object×resource cross-tab(s) "
                         "fail the both-margins gate — nothing written")

    return {
        "leas": leas, "charters": charters, "ce": ce, "edp": edp,
        "edp_fn": edp_fn, "edp_fn_obj": edp_fn_obj, "edp_restr": edp_restr,
        "edp_by_res": edp_by_res, "edp_res_obj": edp_res_obj,
        "res_title": res_title,
        "res_stats": dict(res_stats), "coe_fn": coe_fn, "coe_tot": coe_tot,
        "coe_ada": coe_ada, "charter_gl": charter_gl,
        "charter_gl_tot": charter_gl_tot, "alt_data": alt_data,
        "alt_tot": alt_tot, "dep_funds_exp": dep_funds_exp,
        "basic_aid": basic_aid, "sponsored": sponsored,
        "commingled": commingled, "rev": dict(rev),
        "rev_detail": dict(rev_detail),
        "n_districts": len(ce),
    }


def main():
    ap = argparse.ArgumentParser(description="Rebuild school-data.js")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    state_js = json.loads((ROOT / "data.js").read_text(encoding="utf-8")
                          .split("=", 1)[1].rsplit(";", 1)[0])

    years = {}
    for yy, fy in YEARS:
        print(f"FY {fy}:", file=sys.stderr)
        years[fy] = process_year(yy, fy)
        print(f"  gates passed: {years[fy]['n_districts']} districts to the "
              f"cent; rollups exact; alt totals exact", file=sys.stderr)

    latest = YEARS[-1][1]
    Y = [fy for _, fy in YEARS]

    # ---- NCES crosswalk (identifier matching for the address view)
    if not PUBSCHLS.exists():
        raise SystemExit(f"{PUBSCHLS} missing — download the CDE public "
                         "schools/districts directory export (see comment "
                         "at COMMON_ADMIN_NCES) before running")
    nces_ids = defaultdict(list)
    with open(PUBSCHLS, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            cds = (r.get("CDSCode") or "").strip()
            nces = (r.get("NCESDist") or "").strip()
            if len(cds) == 14 and cds.endswith("0000000") and nces and nces != "No Data":
                target = COMMON_ADMIN_NCES.get(nces, cds[:7])
                if nces not in nces_ids[target]:
                    nces_ids[target].append(nces)

    # ---- assemble districts (driven by the published CE list)
    districts = {}
    # titles for the codes that actually appear as named rows, per year —
    # CDE's own words, this vintage's table only; a code with no title in
    # its own year ships as its raw code (never invented, never grouped).
    res_titles_used = {fy: {} for fy in Y}
    # sorted on the CDS key itself — the source's own stable identity —
    # so the iteration order cannot depend on PYTHONHASHSEED.
    all_keys = sorted({k for fy in Y for k in years[fy]["ce"]})
    newest_of = {k: next((years[fy]["ce"][k] for fy in reversed(Y)
                          if k in years[fy]["ce"]), None) for k in all_keys}
    district_slugs, district_ambig = assign_slugs(
        [(k, newest_of[k]["name"], COUNTIES[int(k[0]) - 1]) for k in all_keys],
        "K-12 districts")
    for key in all_keys:
        c, d = key
        newest = newest_of[key]
        slug = district_slugs[key]
        entry = {"name": newest["name"], "county": COUNTIES[int(c) - 1],
                 "type": newest["type"], "cds": c + d,
                 "nces": nces_ids.get(c + d, []), "years": {}}
        for fy in Y:
            yd = years[fy]
            if key not in yd["ce"]:
                continue
            pub = yd["ce"][key]
            fn = {k: round(v, 2) for k, v in yd["edp_fn"][key].items()}
            com = yd["commingled"].get(key)
            by_res = build_by_resource(yd["edp_by_res"][key],
                                       yd["edp_res_obj"][key])
            named_year = (fy == latest)
            if named_year:
                for g in by_res.values():
                    for row in g["named"]:
                        t = yd["res_title"].get(row[0])
                        if t:
                            res_titles_used[fy][row[0]] = t
            entry["years"][fy] = {
                "ada": round(pub["ada"], 2),
                "currentExpense": round(yd["edp"][key], 2),
                "cePublished": round(pub["edp"], 2),
                "byFunction": fn,
                "byFunctionObject": {g: {o: round(v, 2) for o, v in fam.items()}
                                     for g, fam in yd["edp_fn_obj"][key].items()},
                "byResource": slim_by_resource(by_res, named_year),
                "unrestricted": round(yd["edp_restr"][key][0], 2),
                "restricted": round(yd["edp_restr"][key][1], 2),
                "basicAid": bool(yd["basic_aid"].get(key, False)),
                "smallNSS": pub["ada"] < 250,
                "sponsoredCharterADA": round(yd["sponsored"].get(key, 0.0), 2),
                "commingledCharters": ({"count": com[0], "ada": round(com[1], 2)}
                                       if com else None),
                "depFundsCharterExp": round(yd["dep_funds_exp"].get(key, 0.0), 2),
            }
        districts[slug] = entry

    no_nces = [f"{e['name']} ({e['cds']})" for e in districts.values()
               if not e["nces"]]
    if no_nces:
        raise SystemExit("NCES ID MISSING for " + str(len(no_nces))
                         + " district(s) — the address view cannot match "
                         "them by identifier; nothing written:\n  "
                         + "\n  ".join(no_nces[:20]))

    # ---- county offices (records only)
    coes = {}
    coe_keys = sorted(k for k, lea in years[latest]["leas"].items()
                      if lea["type"].startswith("County Office"))
    coe_slugs, coe_ambig = assign_slugs(
        [(k, years[latest]["leas"][k]["name"], COUNTIES[int(k[0]) - 1])
         for k in coe_keys], "county offices")
    for key in coe_keys:
        lea = years[latest]["leas"][key]
        c, d = key
        entry = {"name": lea["name"], "county": COUNTIES[int(c) - 1],
                 "cds": c + d, "years": {}}
        for fy in Y:
            yd = years[fy]
            if key not in yd["coe_tot"]:
                continue
            entry["years"][fy] = {
                "fundedADA": round(yd["coe_ada"].get(key, 0.0), 2),
                "expenditures": round(yd["coe_tot"][key], 2),
                "byFunction": {k: round(v, 2) for k, v in yd["coe_fn"][key].items()},
            }
        coes[coe_slugs[key]] = entry

    # ---- charters that file separately; dependent ones as pointers
    charters_out, dependents = {}, []
    latest_reg = years[latest]["charters"]
    # sorted on the charter key itself, for the same reason as districts.
    all_charter_keys = sorted(
        {k for fy in Y for k in list(years[fy]["charter_gl"]) + list(years[fy]["alt_data"])})
    charter_reg = {}
    for key in all_charter_keys:
        reg = next((years[fy]["charters"][k] for fy in reversed(Y)
                    for k in [key] if k in years[fy]["charters"]), None)
        if reg is not None:
            charter_reg[key] = reg
    # the charter number is NOT unique on its own (0756 is shared by the
    # nine High Tech schools), so it qualifies a shared NAME, never
    # identifies a charter; assign_slugs raises if that is not enough.
    charter_slugs, charter_ambig = assign_slugs(
        [(k, r["name"], (r["number"] or k[2]).lower())
         for k, r in charter_reg.items()], "charters")
    for key in all_charter_keys:
        reg = charter_reg.get(key)
        if reg is None:
            continue
        c, d, s = key
        slug = charter_slugs[key]
        auth = years[latest]["leas"].get((c, d)) or years[Y[0]]["leas"].get((c, d))
        entry = {"name": reg["name"], "county": COUNTIES[int(c) - 1],
                 "charterNumber": reg["number"],
                 "authorizer": auth["name"] if auth else "State Board of Education",
                 "years": {}}
        for fy in Y:
            yd = years[fy]
            if key in yd["charter_gl"]:
                entry["years"][fy] = {
                    "mode": "sacs",
                    "ada": round(yd["charters"].get(key, {}).get("ada", 0.0), 2),
                    "expenditures": round(yd["charter_gl_tot"][key], 2),
                    "byObject": {k: round(v, 2) for k, v in yd["charter_gl"][key].items()},
                }
            elif key in yd["alt_data"]:
                entry["years"][fy] = {
                    "mode": "alt",
                    "ada": round(yd["charters"].get(key, {}).get("ada", 0.0), 2),
                    "expenditures": round(yd["alt_tot"][key], 2),
                    "byObject": {k: round(v, 2) for k, v in yd["alt_data"][key].items()},
                }
        if entry["years"]:
            charters_out[slug] = entry
    FUND_LABEL = {"General": "Fund 01", "CharterSpecRevenue": "Fund 09",
                  "CharterEnterprise": "Fund 62"}
    # name, then the charter key — an explicit tie-break so the shipped
    # order of same-named dependents cannot drift between builds.
    for key, ch in sorted(latest_reg.items(), key=lambda kv: (kv[1]["name"], kv[0])):
        if ch["level"] in ("CharterSchool", "StateBoardOfEducation") or not ch["level"]:
            continue
        c, d, s = key
        auth = years[latest]["leas"].get((c, d))
        dependents.append({
            "name": ch["name"], "county": COUNTIES[int(c) - 1],
            "authorizer": auth["name"] if auth else "",
            "fund": FUND_LABEL.get(ch["fund"], ch["fund"]),
            "ada": round(ch["ada"], 2),
            "commingled": ch["fund"] == "General"})

    # ---- the overlap block, live
    agency = None
    for fy in Y:
        b = state_js["budgets"].get(fy)
        if not b:
            continue
        for a in b["agencies"]:
            if "K thru 12" in a["name"]:
                agency = agency or {}
                agency[fy] = round(a["gf"] + a["sp"] + a["bd"], 3)
    overlap_years = {}
    for fy in Y:
        yd = years[fy]
        rev, det = yd["rev"], yd["rev_detail"]
        total = sum(rev.values())
        state_sourced = rev["lcffStateAid"] + rev["otherState"] - det.get("lottery", 0)
        overlap_years[fy] = {
            "leaRevenuesB": round(total / 1e9, 3),
            "stateSourcedB": round(state_sourced / 1e9, 3),
            "stateShare": round(state_sourced / total, 4),
            "propertyTaxB": round(rev["propertyTaxes"] / 1e9, 3),
            "propertyTaxShare": round(rev["propertyTaxes"] / total, 4),
            "federalB": round(rev["federal"] / 1e9, 3),
            "federalShare": round(rev["federal"] / total, 4),
            "agencyEnactedB": agency.get(fy) if agency else None,
            "agreement": (round(state_sourced / 1e9 / agency[fy], 4)
                          if agency and agency.get(fy) else None),
            "epaB": round(det.get("epa", 0) / 1e9, 3),
            "strsOnBehalfB": round(det.get("strsOnBehalf", 0) / 1e9, 3),
            "interLeaPassThroughB": round(det.get("passThrough", 0) / 1e9, 3),
        }

    payload = {
        "meta": {
            "source": "cde.ca.gov",
            "sourceLabel": "California Department of Education — SACS unaudited "
                           "actuals, Current Expense of Education, and LCFF "
                           "summary data",
            "generated": date.today().isoformat(),
            "units": "as-reported dollars (exact); ADA as published",
            "identifiers": "Slugs are a function of the published name, "
                           "qualified by county (districts, county offices) "
                           "or charter number when a name is shared. Records "
                           "are keyed on CDE's own CDS code throughout, so "
                           "the same source data always produces the same "
                           "identifiers and the same digest.",
            "ambiguousSlugs": {k: v for k, v in (
                ("districts", district_ambig), ("countyOffices", coe_ambig),
                ("charters", charter_ambig)) if v},
            "basis": "Unaudited actual expenditures as filed by each LEA under "
                     "SACS. District figures are the Current Expense of "
                     "Education (Fund 01 current operating expense, CDE's EDP "
                     "365) and REPRODUCE CDE'S PUBLISHED PER-DISTRICT FIGURE "
                     "TO THE CENT before publication; county-office and "
                     "charter figures reconcile through CDE's own published "
                     "county/state rollups and Alternative Form totals.",
            "gates": {
                "district": "recomputed EDP 365 == published Current Expense "
                            f"of Education within ${GATE_TOL:.2f}, every "
                            "district-year (932/932 to the cent, FY 2024-25)",
                "rollup": "sum(UserGL) == CDE's UserGL_Totals for every state "
                          "and county fund-by-object cell; Alternative Form "
                          "data == its totals table",
            },
            "comparisonScope": "School districts only, per ADA. County offices "
                               "of education are records only — CDE itself "
                               "excludes them from its per-ADA statistic. "
                               "Charters are records only. K-12 entities are "
                               "never compared to or summed with cities, "
                               "counties, special districts, or the state.",
            "overlap": {
                "years": overlap_years,
                "latest": latest,
                "statement": "computed on every pipeline run; the UI must "
                             "render these values and hardcode none",
                "traps": "EPA (Prop 30/55) is continuously appropriated "
                         "outside the annual Budget Act but inside the DOF "
                         "General Fund display; STRS on-behalf contributions "
                         "appear in both layers at different values; "
                         "statewide LEA sums contain inter-LEA pass-throughs; "
                         "Proposition 98 is a K-14 guarantee that also counts "
                         "property taxes — it is neither the agency total "
                         "nor total school funding.",
                "agreementNote": "enacted appropriations vs year-end accrual "
                                 "actuals agree to roughly 1-3.5 percent and "
                                 "never to the dollar",
            },
            "resource": {
                "groups": [{"key": k, "name": n,
                            "restricted": k != "unrestricted"}
                           for k, n in RES_GROUPS],
                "namedFloorM": round(NAMED_FLOOR / 1e6, 1),
                "namedYear": latest,   # named codes shipped for this year;
                # all years carry gated group totals (payload discipline)
                "strsOnBehalfRes": STRS_ON_BEHALF_RES,
                "elopRes": ELOP_RES,
                # live statewide figures per year (Current Expense scope,
                # districts) so the UI hardcodes no dollar amount
                "stats": {fy: {
                    "strsOnBehalfB": round(years[fy]["res_stats"]
                                           .get("strsOnBehalf", 0) / 1e9, 3),
                    "indirectToUnrestrictedB": round(-years[fy]["res_stats"]
                        .get("indirect_unrestricted", 0) / 1e9, 3),
                } for fy in Y},
                # the four face requirements, stated once, plainly
                "onBehalfNote": "Resource 7690, On-Behalf Pension "
                    "Contributions, is money the State pays to CalSTRS "
                    "directly on the district's behalf. It is inside the "
                    "Current Expense of Education but the district never "
                    "receives or spends this cash — it is not district "
                    "spending. Shown as its own row wherever it appears.",
                "indirectNote": "Per-source figures include each program's "
                    "share of district overhead, transferred into it at the "
                    "district's approved indirect-cost rate; unrestricted is "
                    "shown net of those reimbursements. The transfers net to "
                    "zero across the district, so totals reconcile exactly.",
                "unrestrictedNote": "Unrestricted is not local. Resource 0000 "
                    "and the rest of the unrestricted range hold LCFF "
                    "apportionment, the Education Protection Account, and "
                    "unrestricted Lottery — largely STATE money the district "
                    "may spend without a categorical restriction. Local "
                    "restricted is a separate group.",
                "lcffNote": "LCFF is accounted for as a single unrestricted "
                    "resource. Base, supplemental, and concentration grants "
                    "are NOT tracked separately in any district's general "
                    "ledger (CDE's LCFF FAQ; California State Auditor "
                    "2019-101), so no base-vs-supplemental breakout exists "
                    "here — the ledger does not contain one.",
                "otherRangeNote": "The 2000-2999 range has no funding source "
                    "assigned in CDE's classification (CSAM Procedure 310); "
                    "its codes are shown by their official names, never filed "
                    "under a source.",
                "objectSplitNote": "Each named funding source expands to what "
                    "it bought, by object — the same salary / benefit / "
                    "supply / service families the function view uses. The "
                    "objects sum to the funding source's total to the cent, "
                    "and across all sources to the same object totals. This "
                    "is the reduced cross-tab: a source's own object split, "
                    "never the full object-by-source grid.",
            },
            "commingledNote": "Charters reported inside an authorizer's Fund "
                              "01 cannot be separated from the district's own "
                              "figures; affected district records state the "
                              "count and ADA on their face.",
            "jpas": "ROPs, SELPAs, and other JPAs file to CDE and are inside "
                    "the rollup gates but are out of scope as records in this "
                    "version.",
        },
        "years": Y,
        "functions": [{"key": k, "name": n} for k, n, _, _ in FN_GROUPS],
        "objectFamilies": [{"key": k, "name": n} for k, n, _, _ in OBJ_FAMILIES],
        "resourceTitles": res_titles_used,
        "districts": districts,
        "countyOffices": coes,
        "charters": charters_out,
        "dependentCharters": dependents,
    }
    stamp(payload)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"{len(districts)} districts · {len(coes)} county offices · "
          f"{len(charters_out)} charter records · {len(dependents)} dependent "
          f"charter pointers · payload ≈ {len(body) / 1048576:.2f} MB",
          file=sys.stderr)
    ol = overlap_years[latest]
    print(f"overlap FY {latest}: state-sourced {ol['stateShare']*100:.1f}% of "
          f"${ol['leaRevenuesB']:.1f}B LEA revenues; agency "
          f"${ol['agencyEnactedB']}B; agreement {ol['agreement']}",
          file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_school_data.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(header + "window.CA_SCHOOL_DATA = " + body + ";\n",
                        encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1048576:.2f} MB)")


if __name__ == "__main__":
    main()
