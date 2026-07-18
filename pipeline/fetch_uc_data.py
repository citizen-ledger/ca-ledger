#!/usr/bin/env python3
"""
Citizen Ledger — University of California pipeline (V12).

Rebuilds ../uc-data.js from UC's own published Annual Financial Reports
and the UCOP actual-FTE series. Like CCC (and unlike CSU), this layer is
FULLY AUTO-REPRODUCIBLE: every source is a public ucop.edu URL that
answers a plain scripted GET — no login, no bot-gate, no manual cache
(that exception remains CSU's alone; see docs/SCOPE.md).

FISCAL YEAR DISPLAYED: 2024-25 (the latest audited AFR). The gate is
proven for BOTH FY2024-25 and FY2023-24 on each run.

────────────────────────────────────────────────────────────────────
THE GATE — EXACT TO THE THOUSAND, both years (no write on failure)
────────────────────────────────────────────────────────────────────
UC's statements are denominated in THOUSANDS of dollars — the finest
resolution UC publishes — so the gate tier is exact fidelity at the
source's own resolution (the CSU tier; never called "to the cent").
Two identities must hold exactly:

  1. TEN CAMPUSES + UC'S OWN PRINTED SYSTEMWIDE COLUMN == the audited
     total operating expenses, for FY2024-25 AND FY2023-24:
        FY2024-25:  58,074,198 + (−306,871)  == 57,767,327
        FY2023-24:  52,003,294 + 2,700,134   == 54,703,428
     (Both proven in docs/V12_UC_FINDING.md at zero residual; this is
     stronger than CSU's gate in one respect — the reconciling column
     is UC-PUBLISHED, not a pipeline-computed plug.)

  2. THE COLUMN-SUM CHECK, per the finding's build prescription: every
     campus column's function lines must sum EXACTLY to that column's
     printed total. The per-campus table extracts as whole-row strings
     and several rows are SPARSE (Medical centers, Department of Energy
     laboratories, Other) — a naive mapping of a sparse row to columns
     is exactly how an independent verification pass went wrong during
     the investigation. This pipeline therefore BRUTE-FORCES every
     order-preserving assignment of each sparse row's values to columns
     and requires that EXACTLY ONE combined assignment makes all
     columns tie to their printed totals. Zero assignments, or more
     than one, is a gate failure — nothing is written.

AUDIT STATUS, stated honestly (and carried onto the page): the
per-campus table is headed "Campus Facts in Brief (Unaudited)" and is
the auditor's "other information" — PwC's report states "The other
information comprises pages 4 through 7, but does not include the basic
financial statements," on which they "do not express an opinion," while
their stated responsibility is "to read the other information and
consider whether a material inconsistency exists between the other
information and the basic financial statements." The audited figure the
table reconciles to — the systemwide total — carries PwC's unmodified
opinion. Never imply the campus detail carries the systemwide total's
audit status.

────────────────────────────────────────────────────────────────────
THE STRIP — UC's own published lines ONLY, shown, never deleted
────────────────────────────────────────────────────────────────────
The medical/laboratory/auxiliary separation is defined ENTIRELY by
UC's own functional lines in its own table — never by our judgment
about what counts as "education":
  • "Medical centers"                    (FY2024-25: $22,304,432K, 38.6%)
  • "Auxiliary enterprises"              (FY2024-25:  $1,819,469K,  3.1%)
  • "Department of Energy laboratories"  (FY2024-25:  $1,194,419K,  2.1%)
  → CORE (education & research remainder): $32,449,007K, 56.2%.
The DOE line is Lawrence Berkeley National Laboratory, which UC's Note 1
states is included in the statements; Los Alamos (Triad) and Lawrence
Livermore (LLNS) are equity-method LLCs ALREADY OUTSIDE the total, and
UC does not disclose the equity income amount. The stripped components
are always shown separately — never silently deleted.

THE LIMIT, non-negotiable and on the face of the page: UC's
segmentation strips the hospital ENTERPRISES, not the schools of
medicine. Health-sciences instruction/research stays inside the core
(UCSF's stripped core is still ≈$747K per enrolled student). The page
states this wherever per-student figures appear, with UCSF and
health-sciences daggers.

DENOMINATOR: per-campus student FTE from UCOP's stable-URL actual-FTE
PDFs (general campus + health sciences; medical residents are on UC's
own labeled "Resident" line and are EXCLUDED from the denominator,
explicitly — they are employees-in-training, not enrolled students; the
resident counts are carried in the data so the choice is auditable).

Usage:
    python3 fetch_uc_data.py            # dry run: fetch/parse + gates
    python3 fetch_uc_data.py --write    # rebuild ../uc-data.js
    python3 fetch_uc_data.py --refresh  # force re-fetch (ignore cache)
Requires: pypdf.
"""

import argparse
import itertools
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "uc"
OUT_PATH = ROOT / "uc-data.js"

FY_DISPLAY = "2024-25"
AFR = {
    "2024-25": ("afr-2025.pdf",
                "https://www.ucop.edu/uc-controller/financial-reports/systemwide-reports/"
                "annual-financial-reports/24-25/annual-financial-report-2025.pdf"),
    "2023-24": ("afr-2024.pdf",
                "https://www.ucop.edu/uc-controller/financial-reports/systemwide-reports/"
                "annual-financial-reports/23-24/annual-financial-report-2024.pdf"),
}
FTE_PDF = ("fte-2024-25.pdf",
           "https://www.ucop.edu/operating-budget/_files/documents/2024-25.pdf")

CAMPUSES = ["Berkeley", "Davis", "Irvine", "Los Angeles", "Merced",
            "Riverside", "San Diego", "San Francisco", "Santa Barbara", "Santa Cruz"]
PAGE1 = CAMPUSES[:5]                    # Berkeley … Merced
PAGE2 = CAMPUSES[5:] + ["Systemwide"]   # Riverside … Santa Cruz + printed Systemwide col

FUNCTION_ROWS = [
    "Instruction", "Research", "Public service", "Academic support",
    "Student services", "Institutional support",
    "Operation and maintenance of plant", "Student financial aid",
    "Medical centers", "Auxiliary enterprises",
    "Depreciation and amortization", "Department of Energy laboratories",
    "Other",
]
STRIP_LINES = ["Medical centers", "Auxiliary enterprises",
               "Department of Energy laboratories"]

# Corroboration only (never part of the gate, never summed with the AFR
# figures): the separately-audited UC Medical Centers AFR FY2024-25
# combining statement, per-center opinions by PwC — a DIFFERENT measure
# (standalone-department basis) from the AFR's post-elimination
# functional line. Used for a scale sanity check and the method note.
MEDCTR_AFR_TOTAL_K = 23_914_031
MEDCTR_AFR_URL = ("https://www.ucop.edu/uc-controller/financial-reports/systemwide-reports/"
                  "medical-center-reports/24-25/medical-center-report-2025.pdf")


# ── fetch helpers ────────────────────────────────────────────────────
def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Citizen Ledger data pipeline"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def _cached(name, url, refresh):
    path = CACHE / name
    if path.exists() and not refresh:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    blob = _fetch(url)
    if not blob.startswith(b"%PDF"):
        raise SystemExit(f"UC: {url} did not return a PDF — nothing written")
    # atomic write so a fetch interrupted mid-cache never leaves a
    # truncated PDF that poisons subsequent non---refresh runs
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(blob)
    import os
    os.replace(tmp, path)
    return path


def _num(s):
    s = s.strip().replace("$", "").replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    return -int(s) if neg else int(s)


# ── the campus-facts parser with the column-sum proof ────────────────
def _row_values(line):
    return [_num(m) for m in re.findall(r"\(?\$?[\d][\d,]*\)?", line)]


def _parse_facts_page(text, columns):
    """Extract the function rows between 'Operating expenses by function'
    and the campus-totals row. Returns ({label: [values-in-order]}, totals)."""
    i = text.find("Operating expenses by function")
    if i < 0:
        return None, None
    # strip only footnote markers — "*", "[1]", or a bare single digit
    # ("Other1 …" / a wrapped "2 (26,039) …" continuation line) — never
    # value digits (values in this table are always multi-digit)
    marker = re.compile(r"^\s*(?:\*|\[\d\]|\d(?=\s))*\s*")
    lines = [ln.strip() for ln in text[i:].split("\n")[1:]]
    rows, totals = {}, None
    for j, line in enumerate(lines):
        if line.startswith("Total"):
            totals = _row_values(line)
            break
        for lab in FUNCTION_ROWS:
            if line.startswith(lab):
                vals = _row_values(marker.sub("", line[len(lab):]))
                if not vals and j + 1 < len(lines):
                    # the row wrapped: label alone, values on the next line
                    nxt = lines[j + 1]
                    if not nxt.startswith("Total") and \
                       not any(nxt.startswith(o) for o in FUNCTION_ROWS):
                        vals = _row_values(marker.sub("", nxt))
                if vals:
                    rows[lab] = vals
                break
    if totals is None or len(totals) != len(columns):
        return None, None
    return rows, totals


def _prove_assignment(rows, totals, columns):
    """Brute-force order-preserving assignments of every sparse row's
    values to columns; return the UNIQUE assignment under which every
    column's function lines sum exactly to its printed total. This is
    the column-sum check the V12 finding prescribes — zero or multiple
    valid assignments is a gate failure."""
    n = len(columns)
    full, sparse = {}, {}
    for lab, vals in rows.items():
        if len(vals) == n:
            full[lab] = vals
        elif len(vals) < n:
            sparse[lab] = vals
        else:
            return None, (f"row '{lab}' has {len(vals)} values for {n} columns")
    labs = sorted(sparse)
    options = [list(itertools.combinations(range(n), len(sparse[lab]))) for lab in labs]
    winners = []
    for combo in itertools.product(*options):
        cols = [0] * n
        for vals in full.values():
            for c in range(n):
                cols[c] += vals[c]
        for lab, pos in zip(labs, combo):
            for p, v in zip(pos, sparse[lab]):
                cols[p] += v
        if cols == totals:
            winners.append(combo)
            if len(winners) > 1:
                break
    if len(winners) != 1:
        return None, (f"column-sum check: {len(winners)} sparse-row assignments tie "
                      f"(need exactly 1) for sparse rows {labs}")
    grid = {lab: dict(zip(columns, vals)) for lab, vals in full.items()}
    for lab, pos in zip(labs, winners[0]):
        grid[lab] = {columns[p]: v for p, v in zip(pos, sparse[lab])}
    return grid, None


def parse_afr(path, fy):
    """Parse one AFR: the two campus-facts pages (proven by column-sum)
    plus the audited statement figures. Returns a dict or raises."""
    import pypdf
    r = pypdf.PdfReader(str(path))
    texts = [(p.extract_text() or "") for p in r.pages]

    facts_pages = [i for i, t in enumerate(texts) if "Campus Financial Facts" in t]
    if len(facts_pages) != 2:
        raise SystemExit(f"UC {fy}: expected 2 Campus Financial Facts pages, "
                         f"found {len(facts_pages)} — nothing written")
    grids, totals = {}, {}
    for pageidx, columns in zip(facts_pages, (PAGE1, PAGE2)):
        # the column order is verified against the table's own printed
        # header line ("Description Berkeley Davis irvine …") — never
        # assumed. A reordered column would pass the sum-based gate and
        # the (positional) column-sum check while mis-attributing every
        # figure, so a header mismatch is a hard gate failure.
        mh = re.search(r"Description\s+([^\n]+)", texts[pageidx])
        hdr = (mh.group(1) if mh else "").lower()
        pos = [hdr.find(c.lower()) for c in columns]
        if not mh or -1 in pos or pos != sorted(pos):
            raise SystemExit(f"UC {fy}: campus column header does not match the expected "
                             f"order {columns} (header: {hdr!r}) — nothing written")
        rows, tot = _parse_facts_page(texts[pageidx], columns)
        if rows is None:
            raise SystemExit(f"UC {fy}: campus-facts table did not parse "
                             f"(page idx {pageidx}) — nothing written")
        grid, err = _prove_assignment(rows, tot, columns)
        if grid is None:
            raise SystemExit(f"UC {fy}: {err} — nothing written")
        for lab, m in grid.items():
            grids.setdefault(lab, {}).update(m)
        for c, t in zip(columns, tot):
            totals[c] = t

    # audited statement page: has all three anchor labels
    st = next((t for t in texts if "Total operating expenses" in t
               and "State educational appropriations" in t
               and "Medical centers, net" in t), None)
    if st is None:
        raise SystemExit(f"UC {fy}: audited statement page not found — nothing written")

    def first2(label):
        m = re.search(re.escape(label) + r"[\s$]*([\d,]{6,})\s+([\d,]{6,})", st)
        return (_num(m.group(1)), _num(m.group(2))) if m else (None, None)

    audited_total = first2("Total operating expenses")[0]
    state_appr = first2("State educational appropriations")[0]
    m = re.search(r"Total operating revenues[\s$]*([\d,]{6,})", st)
    op_rev = _num(m.group(1)) if m else None
    doe_lines = [_num(x) for x in
                 re.findall(r"Department of Energy laboratories\s+\$?([\d,]{6,})", st)]
    if audited_total is None:
        raise SystemExit(f"UC {fy}: audited total not parsed — nothing written")

    # fall headcount (page-2 row is sparse: Systemwide has no enrollment —
    # structural, and cross-check data only, not a gated figure)
    heads = {}
    for pageidx, columns in zip(facts_pages, (PAGE1, PAGE2)):
        m = re.search(r"Total fall enrollment\s+([\d, ]+)", texts[pageidx])
        if m:
            vals = _row_values(m.group(1))
            names = [c for c in columns if c != "Systemwide"]
            if len(vals) == len(names):
                heads.update(dict(zip(names, vals)))

    return {"grid": grids, "totals": totals, "auditedTotal": audited_total,
            "stateAppr": state_appr, "opRev": op_rev, "doeStatement": doe_lines,
            "fallHeadcount": heads}


def parse_fte(path):
    """UCOP actual-FTE PDF: p1 general-campus totals, p2 health-sciences
    (Undergraduate/Graduate/Resident/Total) per campus."""
    import pypdf
    r = pypdf.PdfReader(str(path))
    t1, t2 = r.pages[0].extract_text(), r.pages[1].extract_text()
    gen, hs = {}, {}
    for name in CAMPUSES + ["University"]:
        # the campus label is a line of its own ("University of California" in
        # the page header must not match the "University" summary row)
        m = re.search(re.escape(name) + r"\s*\n.*?Total\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", t1, re.S)
        if m:
            gen[name] = _num(m.group(3))          # annual total (summer + fall-spring)
        m = re.search(re.escape(name)
                      + r"\s+Undergraduate\s+([\d,]+|-)\s+Graduate\s+([\d,]+)"
                      + r"\s+Resident\s+([\d,]+)\s+Total\s+([\d,]+)", t2)
        if m:
            hs[name] = {"grad": _num(m.group(2)) + (0 if m.group(1) == "-" else _num(m.group(1))),
                        "resident": _num(m.group(3)), "total": _num(m.group(4))}
    return gen, hs


# ── build + gate ─────────────────────────────────────────────────────
def build(refresh):
    fail = []
    afr = {}
    for fy, (name, url) in AFR.items():
        afr[fy] = parse_afr(_cached(name, url, refresh), fy)
    gen_fte, hs_fte = parse_fte(_cached(*FTE_PDF, refresh))

    # ── GATE 1 (both years): Σ campuses + printed Systemwide == audited
    gate_years = {}
    for fy, a in afr.items():
        camp_sum = sum(a["totals"][c] for c in CAMPUSES)
        sw = a["totals"]["Systemwide"]
        residual = camp_sum + sw - a["auditedTotal"]
        gate_years[fy] = {"campusSumK": camp_sum, "systemwideColK": sw,
                          "auditedTotalK": a["auditedTotal"], "residualK": residual}
        if residual != 0:
            fail.append(f"{fy}: 10 campuses ({camp_sum:,}) + Systemwide ({sw:,}) "
                        f"!= audited total ({a['auditedTotal']:,}); residual {residual:+,}K")
    # (GATE 2, the column-sum check, already ran inside _prove_assignment —
    #  a non-unique or failed assignment raised before reaching here.)

    A = afr[FY_DISPLAY]
    # DOE tie: campus-table DOE (Systemwide cell) == audited statement expense line
    doe_k = A["grid"].get("Department of Energy laboratories", {}).get("Systemwide")
    if doe_k is None:
        fail.append("no Department of Energy laboratories line found")
    elif doe_k not in A["doeStatement"]:
        fail.append(f"DOE campus-table line {doe_k:,}K not among the audited statement's "
                    f"DOE lines {A['doeStatement']}")

    # med-center roster is proven by the column-sum check; a change (a new
    # hospital campus) must fail loudly for review, not slip through
    med = A["grid"].get("Medical centers", {})
    med_campuses = sorted(c for c in med if c != "Systemwide")
    if med_campuses != ["Davis", "Irvine", "Los Angeles", "San Diego", "San Francisco"]:
        fail.append(f"medical-center campus set changed: {med_campuses} — review required")

    # strip (UC's own three lines; construction re-asserted)
    med_k = sum(med.values())
    aux_k = sum(A["grid"].get("Auxiliary enterprises", {}).values())
    core_k = A["auditedTotal"] - med_k - aux_k - doe_k
    if med_k + aux_k + doe_k + core_k != A["auditedTotal"]:
        fail.append("strip identity broken (med + aux + DOE + core != audited total)")

    # FTE self-reconciliation: University row == Σ campuses, both pages
    if sum(gen_fte.get(c, 0) for c in CAMPUSES) != gen_fte.get("University"):
        fail.append("general-campus FTE: campus sum != University total")
    if sum(hs_fte[c]["total"] for c in CAMPUSES if c in hs_fte) != hs_fte["University"]["total"]:
        fail.append("health-sciences FTE: campus sum != University total")

    # med-center AFR corroboration (different measure; scale check only)
    if abs(med_k / MEDCTR_AFR_TOTAL_K - 1) > 0.15:
        fail.append(f"medical-center scale check: AFR functional line {med_k:,}K vs "
                    f"separately-audited med-center total {MEDCTR_AFR_TOTAL_K:,}K")

    # overlap shares, computed live
    share_opex = A["stateAppr"] / A["auditedTotal"]
    share_oprev = A["stateAppr"] / A["opRev"] if A["opRev"] else None
    if not (0.05 < share_opex < 0.15):
        fail.append(f"state share of operating expenses {share_opex:.1%} outside sanity band")

    if fail:
        for f in fail[:12]:
            print("  UC GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"{len(fail)} gate failure(s) — nothing written")

    # ── assemble campuses ────────────────────────────────────────────
    aux = A["grid"].get("Auxiliary enterprises", {})
    research = A["grid"].get("Research", {})
    research_core_sw = (sum(research.get(c, 0) for c in CAMPUSES)
                        + research.get("Systemwide", 0)) / core_k
    campuses = []
    for c in CAMPUSES:
        total = A["totals"][c]
        m_ = med.get(c, 0)
        x_ = aux.get(c, 0)
        core = total - m_ - x_
        g = gen_fte.get(c, 0)
        h = hs_fte.get(c)
        hs_students = (h["total"] - h["resident"]) if h else 0
        fte_students = g + hs_students          # residents EXCLUDED, explicitly
        rec = {
            "name": c, "totalK": total, "medK": m_, "auxK": x_, "coreK": core,
            "functions": {lab: A["grid"][lab][c] for lab in A["grid"] if c in A["grid"][lab]},
            "fteGeneral": g, "fteHealthStudents": hs_students,
            "fteResidents": h["resident"] if h else 0,
            "fteStudents": fte_students,
            "fallHeadcount": A["fallHeadcount"].get(c),
            "corePerFte": round(core * 1000 / fte_students) if fte_students else None,
        }
        rec["flags"] = {
            "medCenter": c in med,
            "healthOnly": g == 0,                                    # UCSF: no general campus
            "researchIntensive": core > 0 and (research.get(c, 0) / core) >= 1.25 * research_core_sw,
            "smallScale": 0 < fte_students < 10000,
        }
        campuses.append(rec)

    sw_total = A["totals"]["Systemwide"]
    sw_core = (sw_total - med.get("Systemwide", 0) - aux.get("Systemwide", 0) - doe_k)
    fte_univ_students = gen_fte["University"] + hs_fte["University"]["total"] - hs_fte["University"]["resident"]

    payload = {
        "meta": {
            "source": "ucop.edu",
            "sourceLabel": "University of California Annual Financial Report (audited by "
                           "PricewaterhouseCoopers LLP; the per-campus Campus Financial Facts "
                           "table is the report's own auditor-read front matter) and the UCOP "
                           "actual-FTE series",
            "generated": date.today().isoformat(),
            "year": FY_DISPLAY,
            "unit": "thousands of dollars (the finest resolution UC publishes)",
            "basis": "GAAP / GASB full-accrual, as audited. This is NOT the state budget "
                     "page's enacted, Budgetary-Legal basis; the two are measured "
                     "differently, are never reconciled to each other, and are never summed.",
            "gate": "EXACT TO THE THOUSAND, not to the cent — UC's statements are "
                    "denominated in thousands, the finest unit UC publishes. Two identities "
                    "hold exactly, with no write on failure: (1) the ten campuses plus UC's "
                    "own PRINTED Systemwide column equal the audited total operating "
                    "expenses — proven for FY 2024-25 AND FY 2023-24 at zero residual; "
                    "(2) the column-sum check: every campus column's function lines sum "
                    "exactly to that column's printed total, with the sparse rows' "
                    "column assignment proven unique by exhaustion.",
            "unauditedStatus": "The per-campus table is headed \"Campus Facts in Brief "
                    "(Unaudited)\" and is the auditor's \"other information\": PwC's report "
                    "states \"The other information comprises pages 4 through 7, but does "
                    "not include the basic financial statements,\" on which they \"do not "
                    "express an opinion\" — while their stated responsibility is \"to read "
                    "the other information and consider whether a material inconsistency "
                    "exists between the other information and the basic financial "
                    "statements.\" The audited figure the table reconciles to — the "
                    "systemwide total — carries PwC's unmodified opinion. The campus detail "
                    "does NOT carry that audit status; the reconciliation is the check.",
            "reproducibility": "AUTO-REPRODUCIBLE. Every source is a public ucop.edu URL "
                    "fetched by plain scripted GET — the Annual Financial Reports and the "
                    "UCOP actual-FTE PDFs. Run `python3 pipeline/fetch_uc_data.py --refresh` "
                    "to rebuild from the live sources. No manual-cache exception — that "
                    "remains CSU's alone (see docs/SCOPE.md).",
            "strip": {
                "definition": "The strip is defined ENTIRELY by UC's own published "
                    "functional lines — \"Medical centers\", \"Auxiliary enterprises\", and "
                    "\"Department of Energy laboratories\" — never by our judgment about "
                    "what counts as education. The stripped components are shown "
                    "separately, never deleted.",
                "limit": "UC's segmentation strips the hospital ENTERPRISES, not the "
                    "schools of medicine. Health-sciences instruction, research, and "
                    "academic support remain inside the core — UC publishes no per-campus "
                    "separation of them, and this record does not invent one. A campus "
                    "with medical and health-sciences schools therefore carries a "
                    "structurally higher core than one without; the per-student figures "
                    "are NOT comparable across that divide and are flagged, never ranked.",
                "medNote": "Corroboration: UC separately publishes an audited Medical "
                    "Centers Annual Financial Report (PwC opinion on each of the five "
                    "medical centers; FY 2024-25 combined operating expenses "
                    f"${MEDCTR_AFR_TOTAL_K:,}K, \"Total (memorandum only)\"). That is a "
                    "different measure (standalone-department statements) from the AFR's "
                    "post-elimination functional line stripped here; the two are never "
                    "summed or substituted.",
                "labsNote": "The Department of Energy laboratories line is Lawrence "
                    "Berkeley National Laboratory, which UC's Note 1 states is included "
                    "in the statements — stripped here on UC's own line. Los Alamos "
                    "(Triad National Security, LLC) and Lawrence Livermore (Lawrence "
                    "Livermore National Security, LLC) are equity-method investments "
                    "ALREADY OUTSIDE the total; UC does not disclose the equity income "
                    "amount, so no figure is shown for them (not because it is zero).",
            },
            "denominator": "Per-student uses STUDENT FTE from UCOP's actual-FTE series "
                    "(general campus plus health sciences), fiscal-year-aligned. Medical "
                    "residents are on UC's own labeled \"Resident\" line and are EXCLUDED "
                    "from the denominator — they are employees-in-training, not enrolled "
                    "students; the resident counts are carried in this file so the choice "
                    "is auditable. This is FTE, not headcount (UC also publishes fall "
                    "headcount, campus-reported, which differs at health-science campuses "
                    "by roughly the resident count — carried as a cross-check field, "
                    "never mixed into the denominator).",
            "comparabilityNote": "Campuses differ in ways that make per-FTE core a measure "
                    "of MISSION and STRUCTURE, not performance: five run hospital "
                    "enterprises and medical schools, five do not; UCSF is "
                    "health-sciences-only with no undergraduates; research intensity "
                    "spans an order of magnitude. The Ledger shows the figures, flags "
                    "the differences, and never ranks campuses.",
            "overlap": {
                "stateApprK": A["stateAppr"],
                "auditedTotalK": A["auditedTotal"],
                "opRevK": A["opRev"],
                "shareOfOpex": round(share_opex, 4),
                "shareOfOpRev": round(share_oprev, 4),
                "statement": "The state's appropriation to UC is state money already "
                    "inside the spending shown here — a portion of it, not an amount to "
                    f"add. In FY {FY_DISPLAY} UC recognized "
                    f"${A['stateAppr']:,}K of state educational appropriations: about "
                    f"{share_opex*100:.1f}% of its operating expenses and "
                    f"{share_oprev*100:.1f}% of its operating revenues — the least "
                    "state-funded of the three public systems. State money also reaches "
                    "UC as state grants and contracts (operating revenue) and state "
                    "capital appropriations — three different statement sections. The "
                    "state budget page's enacted UC line is Budgetary-Legal; these "
                    "figures are audited GAAP accrual. Do not sum them, and do not treat "
                    "one as reconciling to the other.",
            },
            "gateHistory": gate_years,
        },
        "systemwide": {
            "auditedTotalK": A["auditedTotal"],
            "systemwideColK": sw_total,
            "systemwideColLabel": "Systemwide (UCOP, DOE laboratory & eliminations)",
            "medK": med_k, "auxK": aux_k, "doeK": doe_k, "coreK": core_k,
            "systemwideCoreK": sw_core,
            "medSystemwideElimK": med.get("Systemwide", 0),
            "auxSystemwideElimK": aux.get("Systemwide", 0),
            "fteStudents": fte_univ_students,
            "fteResidents": hs_fte["University"]["resident"],
            "researchCoreShare": round(research_core_sw, 4),
        },
        "campuses": campuses,
    }
    stamp(payload)
    return payload, gate_years


def main():
    ap = argparse.ArgumentParser(description="Rebuild uc-data.js")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch of all live sources (ignore the local cache)")
    args = ap.parse_args()

    payload, gate_years = build(args.refresh)
    sw = payload["systemwide"]
    for fy, g in sorted(gate_years.items(), reverse=True):
        print(f"FY {fy}: GATE PASSED — 10 campuses ({g['campusSumK']:,}K) + printed "
              f"Systemwide ({g['systemwideColK']:,}K) == audited total "
              f"{g['auditedTotalK']:,}K (exact, thousands; residual {g['residualK']}K)",
              file=sys.stderr)
    print(f"  column-sum check: every campus column ties to its printed total; "
          f"sparse-row assignment proven unique by exhaustion (both years)", file=sys.stderr)
    print(f"  strip (UC's own lines): med ${sw['medK']:,}K ({sw['medK']/sw['auditedTotalK']:.1%}) "
          f"· aux ${sw['auxK']:,}K ({sw['auxK']/sw['auditedTotalK']:.1%}) "
          f"· DOE ${sw['doeK']:,}K ({sw['doeK']/sw['auditedTotalK']:.1%}) "
          f"→ core ${sw['coreK']:,}K ({sw['coreK']/sw['auditedTotalK']:.1%})", file=sys.stderr)

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"  payload {len(body)/1024:.0f} KB", file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_uc_data.py on "
              f"{date.today().isoformat()} from the UC Annual Financial Reports and the "
              "UCOP actual-FTE series (public ucop.edu URLs; auto-reproducible with "
              "--refresh). Figures in thousands; ten campuses plus UC's own printed "
              "Systemwide column reproduce the audited total exactly, both years; every "
              "campus column proven by the column-sum check. (No equals sign may appear "
              "in this comment: the loader slices from the first one.) */\n")
    OUT_PATH.write_text(header + "window.CA_UC_DATA = " + body + ";\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
