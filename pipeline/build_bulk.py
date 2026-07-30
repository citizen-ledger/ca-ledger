#!/usr/bin/env python3
"""
Bulk data exports: one complete CSV per published layer, plus a schema.

WHAT THIS IS FOR. The site already exports the view a reader is looking
at. A researcher wants the opposite: every entity and every shipped year
in one file, with enough provenance in the file itself that it can be
read a year later by someone who never visited the site.

THE ONE STRUCTURAL RULE. The layer list is DISCOVERED from the payloads
on disk, never declared here. Every `*-data.js` at the publishing root
must have an exporter in EXPORTERS; a payload without one stops the
build. That is deliberate: a new layer that ships without a bulk export
is the failure this file exists to prevent, and a hand-maintained list
would simply be edited to agree with whatever shipped.

NOT-PUBLISHED IS AN EMPTY CELL, NEVER A ZERO. Every layer here carries
figures that are absent rather than zero — a district that did not file,
a department with no actuals yet, a year outside a campus's coverage. In
a spreadsheet those two must not collapse. An absent figure is written
as an empty field; a real zero is written as `0`. Every file's header
says so, because a CSV is read far from its documentation.

Reads only what is already on disk. No network, no new dependencies.
"""

import csv
import hashlib
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# WHAT THIS WRITES, DECLARED — see build_findings_manifest.py for why.
# The per-layer CSVs are derived from the payloads on disk, so they are
# covered as a set rather than named one by one; the suite asserts that
# every shipped layer has an export, which is the check that matters.
OUTPUTS = ["bulk-manifest.js", "bulk/SCHEMA.md", "bulk/*.csv"]

OUT = ROOT / "bulk"

# The site's own licence and stability position, repeated in every file
# because a CSV travels away from the page that offered it.
LICENCE = "CC0 1.0 Universal (public domain). Cite freely; no permission needed."
STABILITY = ("This file's SHAPE is not stable. The Ledger is actively developed: "
             "columns may be added, renamed or split as layers change. Pin a copy "
             "if you need reproducibility. The DATA is CC0 and that does not change.")
ABSENT = ("Empty cell = not published by the source. It is NOT zero. "
          "A real reported zero is written as 0.")


def load(name):
    """Read a `-data.js` payload. They are `var X = {...};` — one assignment."""
    src = (ROOT / name).read_text(encoding="utf-8")
    return json.loads(src[src.index("=") + 1:].strip().rstrip(";"))


def num(v):
    """A cell: absent stays absent, numbers stay numbers.

    `None` becomes "" rather than 0 — the distinction this module exists
    to preserve. Floats that are integral print without a trailing .0 so
    a spreadsheet does not show 37.0 positions.
    """
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return v


def basis_line(basis, units, tier, span):
    """The one-line restatement the pages carry, adapted for a whole-layer file.

    A per-view CSV can name ONE fiscal year because a view has one. A bulk
    export spans every shipped year, so it states the span instead of
    inventing a single year — the line must describe the file it is in.
    Composed from the same four things the pages state: what is measured,
    the unit, the inflation basis, and the period. Nominal is stated
    explicitly rather than assumed: every bulk figure is as the source
    published it, and the Ledger's real-dollar adjustment is a VIEW, not
    something baked into an export.
    """
    return " · ".join([basis.split(";")[0].split("—")[0].strip().upper(),
                       units.split(";")[0].strip().upper(),
                       "NOMINAL AS PUBLISHED",
                       span.upper(),
                       tier.split(".")[0].split("—")[0].strip().upper()])


def header(meta, title, basis, tier, units, extra=(), span="ALL SHIPPED YEARS"):
    """The provenance block every export carries, matching the per-view CSVs."""
    lines = [
        f"# Citizen Ledger — {title} — COMPLETE LAYER EXPORT",
        f"# Source dataset: {meta.get('sourceLabel') or meta.get('source') or 'see the finding document'}",
        f"# Accounting basis: {basis}",
        f"# Gate tier: {tier}",
        f"# Units: {units}",
        # the same restatement the layer page shows above its figures, so a
        # bulk row and a screenshot of the site describe themselves alike
        f"# Measured as: {basis_line(basis, units, tier, span)}",
        f"# Data generated: {meta.get('generated', 'unknown')}",
        f"# Exported: {date.today().isoformat()}",
        f"# Absent values: {ABSENT}",
        f"# Licence: {LICENCE}",
        f"# Stability: {STABILITY}",
        "# Schema: bulk/SCHEMA.md · Method: about.html · Findings: findings.html",
    ]
    lines += [f"# {e}" for e in extra]
    return lines


def write_csv(fname, head, cols, rows):
    OUT.mkdir(exist_ok=True)
    buf = io.StringIO()
    for h in head:
        buf.write(h + "\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    n = 0
    for r in rows:
        w.writerow(r)
        n += 1
    (OUT / fname).write_text(buf.getvalue(), encoding="utf-8")
    return fname, n, len(cols)


# --------------------------------------------------------------------------
# One exporter per payload. Each returns (filename, rows, columns) and owns
# its own flattening — the layers genuinely differ in shape and a single
# generic flattener would either lose the shape or invent one.
# --------------------------------------------------------------------------

def export_state(_name):
    d = load("data.js")
    m = d["meta"]
    cols = ["fiscal_year", "agency", "department", "department_code",
            "enacted_general_fund_busd", "enacted_special_funds_busd",
            "enacted_bond_funds_busd", "enacted_federal_funds_busd",
            "actual_general_fund_busd", "actual_special_funds_busd",
            "actual_bond_funds_busd", "actual_federal_funds_busd"]
    rows = []
    for fy in d["years"]:
        for ag in d["budgets"].get(fy, {}).get("agencies", []):
            a = ag.get("actual") or {}
            rows.append([fy, ag["name"], "", "",
                         num(ag.get("gf")), num(ag.get("sp")),
                         num(ag.get("bd")), num(ag.get("fed")),
                         num(a.get("gf")), num(a.get("sp")),
                         num(a.get("bd")), num(a.get("fed"))])
            for dep in ag.get("departments", []):
                da = dep.get("actual") or {}
                rows.append([fy, ag["name"], dep["name"], dep.get("code", ""),
                             num(dep.get("gf")), num(dep.get("sp")),
                             num(dep.get("bd")), num(dep.get("fed")),
                             num(da.get("gf")), num(da.get("sp")),
                             num(da.get("bd")), num(da.get("fed"))])
    head = header(
        m, "state budget",
        "Enacted appropriations on California's Budgetary-Legal basis, with "
        "Department of Finance prior-year actuals on the identical basis where published",
        "GATED — reproduces the Department of Finance's own statewide total",
        "billions of dollars",
        extra=["A row with an empty department is the AGENCY total, not a department. "
               "Do not sum agency rows and department rows together.",
               "Actuals arrive about six and a half months after a year ends, so the "
               "newest years carry enacted figures only — those actual_* cells are empty, not zero."])
    return write_csv("state-budget.csv", head, cols, rows)


def _local_gov(payload, coll_key, fname, title, extra=()):
    """Cities and counties share the State Controller's form and shape."""
    d = load(payload)
    m = d["meta"]
    funcs = [f["key"] for f in d["functions"]]
    fnames = {f["key"]: f["name"] for f in d["functions"]}
    # filing_status TRAVELS WITH THE ROW. A held entity-year exports as a
    # row of zeros, and a CSV has no notes panel to qualify it — so without
    # this column the export reproduces exactly the defect the pages were
    # just fixed for, and does it in the artefact people load into a
    # spreadsheet and never revisit.
    cols = (["slug", "name", "county", "fiscal_year", "filing_status",
             "population", "revenues_musd", "expenditures_musd"]
            + [f"exp_{k}_musd" for k in funcs])
    rows = []
    for slug, e in sorted(d[coll_key].items()):
        for fy in d["years"]:
            y = (e.get("years") or {}).get(fy)
            if not y:
                continue
            bf = y.get("byFunction") or {}
            rows.append([slug, e["name"], e.get("county", ""), fy,
                         y.get("filingStatus") or "as-filed",
                         num(y.get("population")), num(y.get("revenues")),
                         num(y.get("expenditures"))]
                        + [num(bf.get(k)) for k in funcs])
    head = header(
        m, title,
        "Reported actual revenues and expenditures from standardized annual "
        "financial reports filed with the State Controller; governmental "
        "activities only — ratepayer-funded enterprise funds, internal service "
        "funds and conduit financing are excluded from the function figures",
        "AS FILED — reconciled to the Controller's published statewide totals "
        "where one exists; the function split is the Controller's own",
        "millions of dollars; population in persons",
        extra=tuple(extra) + (
            "Function columns: " + "; ".join(f"exp_{k}_musd = {v}" for k, v in fnames.items()),
            "An entity-year absent from this file filed nothing for that year.",
            "filing_status = held means the Controller publishes a complete "
            "schedule of zeros for that entity-year, between years in the "
            "ordinary range, and publishes no filing-status that would say "
            "whether a zero report was filed or none was. Every figure on a "
            "held row is zero as filed; NOTHING is derived from it and it must "
            "not be read as a measurement of zero spending. Filter these rows "
            "out before any comparison.",))
    return write_csv(fname, head, cols, rows)


def export_city(_n):
    return _local_gov("city-data.js", "cities", "cities.csv", "cities",
                      extra=["A $0 in a function column can be a real filed zero — a city that "
                             "contracts the service to its county files $0. The site's services "
                             "checklist distinguishes the two; see about.html.",
                             "Three city-years are held: Hollister and Novato FY2021-22, "
                             "Woodland FY2022-23. See filing_status."])


def export_county(_n):
    return _local_gov("county-data.js", "counties", "counties.csv", "counties",
                      extra=["A county serves the whole county, including residents of every "
                             "city inside it. County and city figures must not be added.",
                             "Three county-years are held: Humboldt FY2019-20 and FY2020-21, "
                             "Mendocino FY2021-22. See filing_status."])


def export_school(_n):
    d = load("school-data.js")
    m = d["meta"]
    funcs = [f["key"] for f in d["functions"]]
    fnames = {f["key"]: f["name"] for f in d["functions"]}
    REV = ["lcffStateAid", "propertyTaxes", "lcffTransfers", "otherState",
           "localOther", "federal"]
    cols = (["slug", "record_type", "name", "county", "district_type", "cds",
             "nces", "fiscal_year", "ada", "current_expense_usd",
             "ce_published_usd", "revenue_tier"]
            + [f"rev_{k}_usd" for k in REV]
            + [f"exp_{k}_usd" for k in funcs])
    rows = []
    for kind, key in (("district", "districts"), ("county-office", "countyOffices"),
                      ("charter", "charters")):
        for slug, e in sorted(d.get(key, {}).items()):
            for fy in d["years"]:
                y = (e.get("years") or {}).get(fy)
                if not y:
                    continue
                bf = y.get("byFunction") or {}
                rv = y.get("revenueAsFiled") or {}
                rows.append([slug, kind, e["name"], e.get("county", ""),
                             e.get("type", ""), e.get("cds", ""),
                             ";".join(e.get("nces") or []), fy,
                             num(y.get("ada")), num(y.get("currentExpense")),
                             num(y.get("cePublished")), y.get("revenueTier", "")]
                            + [num(rv.get(k)) for k in REV]
                            + [num(bf.get(k)) for k in funcs])
    head = header(
        m, "K-12 schools",
        "Unaudited actual expenditures as filed under the state's Standardized "
        "Account Code Structure (SACS); Current Expense of Education",
        "GATED TO THE CENT for school districts, against the Department of "
        "Education's published Current Expense of Education. County offices and "
        "charter schools are RECORDS ONLY — the Department excludes them from its "
        "per-pupil statistic and so does the Ledger",
        "dollars; ADA in average daily attendance",
        extra=["record_type distinguishes district / county-office / charter. Only "
               "district rows enter any per-pupil comparison; do not compute one "
               "across record types.",
               "revenue_tier states the tier of that row's revenue figures, which is "
               "NOT the same tier as the expenditure figures beside them.",
               "Function columns: " + "; ".join(f"exp_{k}_usd = {v}" for k, v in fnames.items())])
    return write_csv("k12-schools.csv", head, cols, rows)


def export_district(_n):
    d = load("district-data.js")
    m = d["meta"]
    BUCKETS = ["gov", "ent", "isf", "cf"]
    BNAMES = {"gov": "governmental funds", "ent": "enterprise funds",
              "isf": "internal service funds", "cf": "conduit financing"}
    cols = (["slug", "name", "county", "activity", "district_type",
             "fiscal_year", "filing_status"]
            + [f"exp_{b}_usd" for b in BUCKETS]
            + [f"rev_{b}_usd" for b in BUCKETS])
    rows = []
    years = d["years"]
    for slug, e in sorted(d["districts"].items()):
        filings = e.get("filings") or ""
        for i, fy in enumerate(years):
            exp = (e.get("exp") or [None] * len(years))[i]
            rev = (e.get("rev") or [None] * len(years))[i]
            if exp is None and rev is None:
                continue
            rows.append([slug, e["name"], e.get("county", ""),
                         e.get("activity", ""), e.get("type", ""), fy,
                         filings[i] if i < len(filings) else ""]
                        + [num(exp[j]) if exp else "" for j in range(4)]
                        + [num(rev[j]) if rev else "" for j in range(4)])
    head = header(
        m, "special districts",
        "Reported as filed with the State Controller, by fund class",
        "AS FILED — UNRECONCILED. Three of the four fund-class buckets have no "
        "published total to check against: for enterprise, internal-service and "
        "conduit funds the Controller publishes operating and nonoperating "
        "components and never their sum. A control exists for the governmental "
        "bucket only. No figure in this file has been verified against an "
        "independently published total",
        "as-filed dollars",
        extra=["Fund-class columns: " + "; ".join(f"{b} = {n}" for b, n in BNAMES.items()),
               "filing_status is the Controller's own per-year code for that district; "
               "'-' means no filing is recorded for that year.",
               "An entity-year with no filing at all is omitted rather than written as zero."])
    return write_csv("special-districts.csv", head, cols, rows)


def export_ccc(_n):
    d = load("ccc-data.js")
    m = d["meta"]
    cols = ["district_code", "name", "colleges", "fiscal_year",
            "current_expense_usd", "instructional_salaries_usd",
            "pct_instructional_salaries", "funded_ftes", "per_ftes_usd",
            "state_general_fund_usd", "rev_federal_usd", "rev_state_usd",
            "rev_local_usd", "rev_total_usd", "community_supported_status"]
    rows = []
    for e in sorted(d["districts"], key=lambda x: x["name"]):
        for fy, y in sorted((e.get("years") or {}).items()):
            rv = y.get("revenue") or {}
            rows.append([e.get("code", ""), e["name"],
                         ";".join(e.get("colleges") or []), fy,
                         num(y.get("ce")), num(y.get("instrSal")),
                         num(y.get("pct50")), num(y.get("fundedFtes")),
                         num(y.get("perFtes")), num(y.get("stateGf")),
                         num(rv.get("fed")), num(rv.get("state")),
                         num(rv.get("local")), num(rv.get("tot")),
                         y.get("basicAidStatus", "")])
    head = header(
        m, "community college districts",
        "Modified accrual on the community-college Budget and Accounting Manual "
        "uniform chart; Current Expense of Education (ECS 84362)",
        "GATED TO THE DOLLAR against the Chancellor's Office printed statewide total",
        "dollars; FTES in full-time-equivalent students",
        extra=["Apportionment-derived columns (funded_ftes, per_ftes_usd, "
               "state_general_fund_usd, community_supported_status) reach only the "
               "years with a readable apportionment document, and are empty elsewhere. "
               "That is an absence of source, not a zero.",
               "community_supported_status is three-valued: a status, or "
               "'not-published' where the derivation could not be reconciled."])
    return write_csv("community-colleges.csv", head, cols, rows)


def export_csu(_n):
    d = load("csu-data.js")
    m = d["meta"]
    yr = m.get("year") or m.get("vintage") or ""
    cols = ["campus", "fiscal_year", "operating_expenses_kusd",
            "state_appropriation_kusd", "operating_revenue_kusd",
            "headcount", "per_student_usd"]
    rows = [[c["name"], yr, num(c.get("opexpK")), num(c.get("stateAppropK")),
             num(c.get("opRevK")), num(c.get("headcount")), num(c.get("perStudent"))]
            for c in sorted(d["campuses"], key=lambda x: x["name"])]
    head = header(
        m, "CSU campuses",
        "Audited GAAP / GASB full accrual, from CSU's systemwide financial statements",
        "GATED TO THE THOUSAND against the audited statement total — exact "
        "fidelity at the source's own denomination, which is thousands",
        "thousands of dollars, except per_student_usd which is dollars",
        extra=["This layer is a single fiscal year. Older years cannot be gated: the "
               "source returns HTTP 403 to every scripted request, so an older year's "
               "control total is uncomputable rather than merely unreconciled. "
               "See docs/V15_HISTORICAL_FINDING.md.",
               "This is NOT the state budget's enacted basis and the two are never added."])
    return write_csv("csu-campuses.csv", head, cols, rows)


def export_uc(_n):
    d = load("uc-data.js")
    m = d["meta"]
    fset = []
    for c in d["campuses"]:
        for y in (c.get("years") or {}).values():
            for k in (y.get("functions") or {}):
                if k not in fset:
                    fset.append(k)

    def slug(s):
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

    cols = (["campus", "fiscal_year", "total_kusd", "medical_centers_kusd",
             "auxiliaries_kusd", "education_core_kusd"]
            + [f"fn_{slug(f)}_kusd" for f in fset])
    rows = []
    for c in sorted(d["campuses"], key=lambda x: x["name"]):
        for fy, y in sorted((c.get("years") or {}).items()):
            fn = y.get("functions") or {}
            rows.append([c["name"], fy, num(y.get("totalK")), num(y.get("medK")),
                         num(y.get("auxK")), num(y.get("coreK"))]
                        + [num(fn.get(f)) for f in fset])
    held = ", ".join(sorted(d.get("held", {}))) or "none"
    head = header(
        m, "UC campuses",
        "Audited GAAP / GASB full accrual, with medical centres, auxiliaries and "
        "the Department of Energy laboratory separated on UC's own published lines",
        "GATED TO THE THOUSAND against UC's audited statement total",
        "thousands of dollars",
        extra=[f"Held years (published as a labelled absence, not at a lower standard): {held}. "
               "A held year's rows are absent from this file rather than present with zeros.",
               "education_core_kusd is the teaching-and-research remainder after the strip. "
               "The strip is UC's own functional lines; nothing is deleted.",
               "Function columns are UC's published functional classification, prefixed fn_."])
    return write_csv("uc-campuses.csv", head, cols, rows)


def export_compensation(_n):
    d = load("compensation-data.js")
    m = d["meta"]
    cols = ["slug", "name", "layer", "county", "positions_reported",
            "total_wages_usd", "retirement_and_health_usd", "population",
            "elected_positions", "retirement_includes_unfunded_liability"]
    # keyed by slug — the slug is the join key the per-entity detail files use,
    # so it is carried rather than dropped
    rows = [[slug, e["name"], e.get("layer", ""), e.get("county", ""),
             num(e.get("positions")), num(e.get("wages")), num(e.get("retHealth")),
             num(e.get("population")), num(e.get("elected")),
             "true" if e.get("unfundedInRetirement") else "false"]
            for slug, e in sorted(d["entities"].items(),
                                  key=lambda kv: (kv[1].get("layer", ""), kv[1]["name"]))]
    head = header(
        m, "public employee compensation",
        "Positions as reported by each employer to the State Controller for the "
        "calendar year, including part-year and part-time positions",
        f"AS FILED — {m.get('tier', 'unreconciled')}. A published control exists and "
        "can never be reconciled to: the source is a live database with no as-of-date "
        "total, so there is no instant at which the two can be aligned",
        "dollars; positions are positions, NOT persons",
        extra=["A person holding two positions appears in two rows. This is a count of "
               "positions reported, never a headcount of people.",
               "retirement_includes_unfunded_liability is an employer-level reporting "
               "flag. Two identically-paid positions at two employers show different "
               "totals for a pure reporting reason, and the unfunded component is not "
               "separately reported, so it cannot be netted out.",
               "Do NOT compute an average or median over these rows. There is no hours "
               "or FTE field, and a quarter of city rows show pay below half the "
               "position's own stated minimum. See docs/V23A_COMPENSATION_BUILD_FINDING.md.",
               f"Vintage: {m.get('vintage', 'see the finding document')}"])
    return write_csv("compensation.csv", head, cols, rows)


def export_deflator(_n):
    d = load("deflator-data.js")
    m = d["meta"]
    cols = ["fiscal_year", "index_value", "is_forecast"]
    fc = set(m.get("forecastYears") or [])
    rows = [[fy, num(v), "true" if fy in fc else "false"]
            for fy, v in sorted(d["fy"].items())]
    head = header(
        m, "price deflator",
        m.get("index", "Implicit Price Deflator for State and Local Government "
                       "Purchases of Goods and Services"),
        "NOT A GATED LAYER — this is a published index the Ledger applies, and the "
        "choice to apply it is the Ledger's own methodological decision rather than "
        "reproduction of a source's figure",
        f"index, base year {m.get('baseYear', 'see meta')}",
        extra=["Supporting series, not a spending layer. It is here because the real-dollar "
               "figures on the site cannot be reproduced without it.",
               "is_forecast marks years the source projects rather than reports."])
    return write_csv("price-deflator.csv", head, cols, rows)


# Keyed by payload filename. Discovery below refuses any payload not here.
EXPORTERS = {
    "data.js": export_state,
    "city-data.js": export_city,
    "county-data.js": export_county,
    "school-data.js": export_school,
    "district-data.js": export_district,
    "ccc-data.js": export_ccc,
    "csu-data.js": export_csu,
    "uc-data.js": export_uc,
    "compensation-data.js": export_compensation,
    "deflator-data.js": export_deflator,
}


def discover():
    """Every shipped payload at the publishing root, from disk.

    `data.js` is named explicitly because it does not carry the `-data.js`
    suffix; everything else is globbed, so a new layer appears here the
    moment it ships whether or not anyone remembered this file.
    """
    found = sorted(p.name for p in ROOT.glob("*-data.js"))
    if (ROOT / "data.js").exists():
        found.append("data.js")
    return sorted(found)


def main():
    payloads = discover()
    missing = [p for p in payloads if p not in EXPORTERS]
    if missing:
        raise SystemExit(
            f"bulk: no exporter for {missing}. A layer that ships without a bulk "
            "export is the defect this check exists to catch — add an exporter to "
            "EXPORTERS in pipeline/build_bulk.py. Nothing written.")
    stale = [p for p in EXPORTERS if p not in payloads]
    if stale:
        raise SystemExit(
            f"bulk: EXPORTERS names {stale}, which is not on disk. Either the layer "
            "was removed and its exporter should go too, or the payload is missing "
            "from the build. Nothing written.")

    written = []
    for p in payloads:
        written.append(EXPORTERS[p](p))
    # manifest first: the schema quotes its digests, so a stale manifest
    # would silently publish digests for the previous build's files
    write_manifest(written, payloads)
    write_schema(written)
    total = sum(r for _, r, _ in written)
    for f, r, c in written:
        print(f"  bulk/{f:26} {r:>8,} rows  {c:>3} cols", file=sys.stderr)
    print(f"bulk: {len(written)} files, {total:,} rows", file=sys.stderr)


TITLES = {
    "state-budget.csv": ("State budget", "Enacted appropriations by agency and "
                         "department, with Department of Finance actuals on the "
                         "same basis where published."),
    "cities.csv": ("Cities", "Reported actual revenues and expenditures by "
                   "function, per city per year."),
    "counties.csv": ("Counties", "The same State Controller form, filed by "
                     "counties. A county serves the whole county."),
    "k12-schools.csv": ("K-12 schools", "Districts, county offices and charter "
                        "schools, with the per-pupil denominator and the function split."),
    "special-districts.csv": ("Special districts", "Every filing district, by "
                              "fund class, as filed and unreconciled."),
    "community-colleges.csv": ("Community colleges", "District Current Expense of "
                               "Education with apportionment figures where the "
                               "source publishes them."),
    "csu-campuses.csv": ("CSU campuses", "Audited operating expense per campus. "
                         "One fiscal year — older years cannot be gated."),
    "uc-campuses.csv": ("UC campuses", "Audited expense with medical centres and "
                        "auxiliaries separated on UC's own lines."),
    "compensation.csv": ("Compensation", "Reported positions, wages and "
                         "retirement/health per employer. Positions, not people."),
    "price-deflator.csv": ("Price deflator", "The index behind every real-dollar "
                           "figure on the site. A supporting series, not a layer."),
}


def write_manifest(written, payloads):
    """A payload the page renders its table from, so the listing is DERIVED.

    Hand-writing the file table into `bulk.html` would let it drift the
    moment a layer's row count changed. The page reads this instead, in
    the same `<script src>` way every other page reads its data — no
    fetch(), so `bulk.html` still opens from a file:// path.
    """
    files = []
    for f, rows, cols in sorted(written):
        title, blurb = TITLES.get(f, (f, ""))
        blob = (OUT / f).read_bytes()
        files.append({"file": f, "title": title, "blurb": blurb,
                      "rows": rows, "cols": cols, "bytes": len(blob),
                      # so a downloaded copy can be checked against the
                      # copy this build produced, the same way the -data.js
                      # payloads carry a digest
                      "sha256": hashlib.sha256(blob).hexdigest()})
    payload = {"generated": date.today().isoformat(),
               "sourcePayloads": payloads,
               "licence": LICENCE, "stability": STABILITY, "absent": ABSENT,
               "files": files}
    (ROOT / "bulk-manifest.js").write_text(
        "var BULK = " + json.dumps(payload, indent=1) + ";\n", encoding="utf-8")


def write_schema(written):
    """The schema document, written for someone who will never read the site."""
    rows = {f: (r, c) for f, r, c in written}
    lines = [
        "# Citizen Ledger — bulk data schema",
        "",
        f"*Generated {date.today().isoformat()}. One CSV per published layer, "
        "covering every entity and every shipped year.*",
        "",
        "## Before you use these",
        "",
        "**An empty cell is not a zero.** Every file here carries figures that are "
        "absent because the source does not publish them — a district that did not "
        "file, a year outside a campus's coverage, a department whose actuals have "
        "not arrived. An empty cell means *not published*. A real reported zero is "
        "written `0`. A spreadsheet that treats both as zero will produce totals no "
        "government ever reported.",
        "",
        "**The layers do not add up, and are not meant to.** The same dollar appears "
        "in more than one file: roughly half of what counties and school districts "
        "report receiving is money the state budget already shows sending. There is "
        "no combined total, and summing across files produces a number that describes "
        "nothing.",
        "",
        "**Accounting bases differ per file and are never mixed.** An enacted "
        "appropriation is a plan; an actual expenditure is a record; an audited GAAP "
        "figure is a third thing. Each file's header names its own basis.",
        "",
        "**Gate tiers differ per file, and one file's tier can differ per column.** "
        "A *gated* figure reproduces a total the source itself published, to a named "
        "resolution. An *as-filed* figure has no published control to check against — "
        "it is the government's own number, and nobody has confirmed it. Both are in "
        "this set, labelled.",
        "",
        "## Stability",
        "",
        "**The shape of these files is not stable.** The Ledger is actively "
        "developed. Columns may be added, renamed or split as layers change, and a "
        "script that reads these files by column position will break. Read by column "
        "name, and pin a copy of the file if you need a reproducible result.",
        "",
        "That caveat is about **shape, not licence**. The data is CC0 1.0 "
        "(public domain): use it for anything, no permission, no attribution "
        "required — though a link back helps a reader check it.",
        "",
        "Each file's provenance header carries the generation date of the data and "
        "the export date of the file. They are different dates and both matter.",
        "",
        "## The files",
        "",
        "| file | rows | columns | layer |",
        "|---|---|---|---|",
    ]
    for f in sorted(rows):
        r, c = rows[f]
        title, blurb = TITLES.get(f, (f, ""))
        lines.append(f"| [`{f}`]({f}) | {r:,} | {c} | {title} — {blurb} |")

    lines += [
        "",
        "## Checking a downloaded file",
        "",
        "Each file's SHA-256 is recorded when it is generated, so a copy can be "
        "checked against the copy this build produced:",
        "",
        "```",
        "shasum -a 256 bulk/<file>.csv",
        "```",
        "",
        "| file | sha256 |",
        "|---|---|",
    ]
    import json as _j
    man = _j.loads((ROOT / "bulk-manifest.js").read_text(encoding="utf-8")
                   .split("=", 1)[1].strip().rstrip(";")) if (ROOT / "bulk-manifest.js").exists() else {"files": []}
    for f in man.get("files", []):
        lines.append(f"| `{f['file']}` | `{f['sha256']}` |")
    lines += [
        "",
        "The digests above describe *these* files. The `-data.js` payloads they are "
        "derived from carry their own digests, verified by `pipeline/verify_digest.py`.",
        "",
        "## Column conventions",
        "",
        "Suffixes carry the unit, so a column's unit never depends on remembering "
        "which file it came from:",
        "",
        "| suffix | unit |",
        "|---|---|",
        "| `_usd` | dollars |",
        "| `_kusd` | **thousands** of dollars (the source's own denomination) |",
        "| `_musd` | **millions** of dollars (the source's own denomination) |",
        "| `_busd` | **billions** of dollars (the source's own denomination) |",
        "| `exp_*` | an expenditure component |",
        "| `rev_*` | a revenue component |",
        "| `fn_*` | a published functional classification |",
        "",
        "Where a figure is denominated in thousands or millions, that is the "
        "**source's** resolution, not a rounding the Ledger applied. Converting to "
        "dollars invents precision the source did not publish.",
        "",
        "## Per-file notes",
        "",
        "Every file repeats its own basis, tier, units and caveats in `#` comment "
        "lines above the header row. Those lines are the authoritative description "
        "of that file — this document summarises, the file itself governs. Most "
        "CSV readers skip `#` lines; if yours does not, drop lines beginning `#`.",
        "",
        "Three notes that catch people out:",
        "",
        "- **`state-budget.csv`** interleaves agency and department rows. A row with "
        "an empty `department` is the agency total. Summing both together "
        "double-counts every dollar.",
        "- **`k12-schools.csv`** carries three record types in one file. Only "
        "`record_type = district` enters any per-pupil comparison — the Department of "
        "Education excludes county offices and charters from its own per-pupil "
        "statistic, and so does the Ledger.",
        "- **`compensation.csv`** counts *positions*, not people, and must not be "
        "averaged: there is no hours or FTE field, so a mean over these rows is an "
        "artifact of the part-time share rather than a typical salary.",
        "",
        "## Provenance and verification",
        "",
        "Every figure here is reproduced from a payload built by the pipelines in "
        "`pipeline/`, each of which reconciles against a published control before it "
        "writes anything. The data files carry a SHA-256 digest; the verifier is "
        "`pipeline/verify_digest.py`.",
        "",
        "The investigation documents that decided what each layer publishes, what "
        "tier it earned, and what was refused are in `docs/`, indexed at "
        "`findings.html`. Where a layer is as-filed rather than gated, the finding "
        "says why, with the measurement.",
        "",
    ]
    (OUT / "SCHEMA.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
