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

    # ---- stream the general ledger once
    edp = defaultdict(float)                 # (c,d) -> EDP365
    edp_fn = defaultdict(lambda: defaultdict(float))
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
                edp_fn[(c, d)][fn_group(r["Function"])] += v
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

    return {
        "leas": leas, "charters": charters, "ce": ce, "edp": edp,
        "edp_fn": edp_fn, "coe_fn": coe_fn, "coe_tot": coe_tot,
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

    # ---- assemble districts (driven by the published CE list)
    districts, slug_taken = {}, {}
    all_keys = sorted({k for fy in Y for k in years[fy]["ce"]},
                      key=lambda k: years[Y[-1]]["ce"].get(k, years[Y[0]]["ce"].get(k, {"name": ""}))["name"])
    for key in all_keys:
        c, d = key
        newest = next((years[fy]["ce"][key] for fy in reversed(Y)
                       if key in years[fy]["ce"]), None)
        slug = slugify(newest["name"])
        if slug in slug_taken:
            slug = slugify(newest["name"] + "-" + COUNTIES[int(c) - 1])
        slug_taken[slug] = True
        entry = {"name": newest["name"], "county": COUNTIES[int(c) - 1],
                 "type": newest["type"], "cds": c + d, "years": {}}
        for fy in Y:
            yd = years[fy]
            if key not in yd["ce"]:
                continue
            pub = yd["ce"][key]
            fn = {k: round(v, 2) for k, v in yd["edp_fn"][key].items()}
            com = yd["commingled"].get(key)
            entry["years"][fy] = {
                "ada": round(pub["ada"], 2),
                "currentExpense": round(yd["edp"][key], 2),
                "cePublished": round(pub["edp"], 2),
                "byFunction": fn,
                "basicAid": bool(yd["basic_aid"].get(key, False)),
                "smallNSS": pub["ada"] < 250,
                "sponsoredCharterADA": round(yd["sponsored"].get(key, 0.0), 2),
                "commingledCharters": ({"count": com[0], "ada": round(com[1], 2)}
                                       if com else None),
                "depFundsCharterExp": round(yd["dep_funds_exp"].get(key, 0.0), 2),
            }
        districts[slug] = entry

    # ---- county offices (records only)
    coes = {}
    for key, lea in sorted(years[latest]["leas"].items(),
                           key=lambda kv: kv[1]["name"]):
        if not lea["type"].startswith("County Office"):
            continue
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
        coes[slugify(lea["name"])] = entry

    # ---- charters that file separately; dependent ones as pointers
    charters_out, dependents = {}, []
    seen_slugs = set()
    latest_reg = years[latest]["charters"]
    all_charter_keys = sorted(
        {k for fy in Y for k in list(years[fy]["charter_gl"]) + list(years[fy]["alt_data"])},
        key=lambda k: (latest_reg.get(k, {}).get("name") or
                       next((years[fy]["charters"][k]["name"] for fy in reversed(Y)
                             if k in years[fy]["charters"]), "")))
    for key in all_charter_keys:
        reg = next((years[fy]["charters"][k] for fy in reversed(Y)
                    for k in [key] if k in years[fy]["charters"]), None)
        if reg is None:
            continue
        c, d, s = key
        slug = slugify(reg["name"])
        if slug in seen_slugs:
            slug = slugify(reg["name"]) + "-" + (reg["number"] or s).lower()
        seen_slugs.add(slug)
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
    for key, ch in sorted(latest_reg.items(), key=lambda kv: kv[1]["name"]):
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
