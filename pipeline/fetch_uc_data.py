#!/usr/bin/env python3
"""
Citizen Ledger — University of California pipeline (V18: six-year window).

Rebuilds ../uc-data.js from UC's own published Annual Financial Reports
and the UCOP actual-FTE series. Like CCC (and unlike CSU), this layer is
FULLY AUTO-REPRODUCIBLE: every source is a public ucop.edu URL that
answers a plain scripted GET — no login, no bot-gate, no manual cache
(that exception remains CSU's alone; see docs/SCOPE.md).

FISCAL YEARS SHIPPED: FY2020-21 … FY2024-25 (five years). FY2019-20 is
HELD — declared, not silently dropped — because its UNAUDITED campus
table does not reconcile to the audited total at the source's own
resolution (measured residual ≈ −351K after UC's own DOE add-back; every
other year ties to the thousand). The build re-measures that residual on
every run and FAILS LOUDLY if it ever closes, so a future restatement is
reviewed by a human rather than shipped silently. See
docs/V18B_UC_SIX_YEAR_BUILD.md.

────────────────────────────────────────────────────────────────────
DECLARED, NEVER SNIFFED — the per-vintage tables
────────────────────────────────────────────────────────────────────
UC changed its presentation across these years in four measured ways,
and each is DECLARED per vintage in VINTAGE below, never inferred from
whether a row happens to parse:

  1. ANCHORS. The four older AFRs print the section headers in CAPITALS
     ("CAMPUS FINANCIAL FACTS", "OPERATING EXPENSES BY FUNCTION"); the
     two newest use mixed case. The ROW LABELS are mixed case in every
     vintage, so only the two headers need a per-vintage form. A
     case-insensitive match is the widened detector this repo has twice
     refused, and it is not used.

  2. ROWS. FY2019-20/FY2020-21 print "Impairment of capital assets" as a
     separate function row; FY2021-22 COMBINES it with "Other" into one
     line ("Other and Impairment of capital assets"); FY2022-23 relabels
     the DOE line "DOE Labs Expenses". Each is a declared extraRows
     entry. The combined FY2021-22 line begins with "Other" — itself a
     declared row — so rows are matched LONGEST-LABEL-FIRST; matched
     shortest-first the combined quantity would bind to "Other" and
     produce a wrong number that parses cleanly (see
     tests test_uc_longest_label_first).

  3. DOE. UC publishes the Department of Energy laboratories line in two
     shapes across the window (doeForm below):
       • "excluded"   — absent from the campus table, which carries a
                        printed "Excludes DOE laboratories" footnote. The
                        table therefore reconciles to the audited total
                        only when the statement's DOE OPERATING-EXPENSE
                        line is added back. (FY2020-21; also held FY2019-20)
       • "systemwide" — present in the campus table's Systemwide cell, so
                        campuses + Systemwide already includes it.
                        (FY2021-22 … FY2024-25)
     The core strip subtracts the same DOE quantity either way, so the
     six-year core line is comparably defined; the two assembly forms are
     stated as a comparability fact WHERE THE SERIES CROSSES THEM, on the
     trend and the record, never characterised.

────────────────────────────────────────────────────────────────────
THE GATE — per year, no write on any failure
────────────────────────────────────────────────────────────────────
UC's statements are denominated in THOUSANDS — the finest resolution UC
publishes — so the gate tier is exact fidelity at the source's own
resolution. For EACH shipped year:

  GATE 1 — RECONCILIATION. Ten campuses + UC's own printed Systemwide
     column (+ the statement DOE line for "excluded" vintages) equal the
     audited total operating expenses, to the thousand.

  GATE 2 — COLUMN-SUM. Every campus column's function lines sum to that
     column's printed total. Sparse rows (Medical centers, DOE, Other,
     Impairment) are assigned to columns by EXHAUSTING every
     order-preserving placement; EXACTLY ONE combined assignment must
     tie every column. Because UC rounds each printed figure
     independently, a column total need not equal the sum of its rounded
     components, so the tie is required only to ±1 thousand — but the
     tolerance is not what carries the proof: at ±10 thousand (ten times
     wider) the assignment is STILL unique, and the build asserts that,
     so a genuinely ambiguous future vintage fails rather than being
     absorbed.

  GATE 3 — PRINTED-HEADER ORDER. The campus columns are assigned
     positionally, so a reordered column would tie Gate 2 while
     mis-attributing every figure. The printed header line naming the
     campuses is located and required to list them in the same order.

AUDIT STATUS, per vintage. The per-campus table is UC's "Campus Facts in
Brief (Unaudited)". From FY2021-22 the auditor's report carries the
"other information" language (PwC "do not express an opinion" on it); the
two oldest reports predate the standard that added that section, so the
sentence is NOT carried back onto years where the auditor did not write
it. The audited figure the campuses reconcile to — the systemwide total —
carries PwC's unmodified opinion in every year.

────────────────────────────────────────────────────────────────────
THE STRIP — UC's own published lines ONLY, shown, never deleted
────────────────────────────────────────────────────────────────────
The medical/laboratory/auxiliary separation is defined ENTIRELY by UC's
own functional lines — "Medical centers", "Auxiliary enterprises",
"Department of Energy laboratories" — never by our judgment about what
counts as "education". CORE is the arithmetic remainder (audited total
less the three strips); UC publishes no "core" line, and meta.strip says
so. The DOE line is Lawrence Berkeley National Laboratory; Los Alamos and
Livermore are equity-method LLCs already outside the total. THE LIMIT, on
the face of the page: UC strips the hospital ENTERPRISES, not the schools
of medicine — health-sciences instruction/research stays in the core.

DENOMINATOR: per-campus student FTE from UCOP's stable-URL actual-FTE
PDFs (general campus + health sciences; medical residents on UC's own
"Resident" line are EXCLUDED and carried separately so the choice is
auditable). Now fetched per year, so per-student figures span the window.

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
import gates                                     # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "uc"
OUT_PATH = ROOT / "uc-data.js"

AFR_BASE = ("https://www.ucop.edu/uc-controller/financial-reports/systemwide-reports/"
            "annual-financial-reports/")
FTE_BASE = "https://www.ucop.edu/operating-budget/_files/documents/"

CAMPUSES = ["Berkeley", "Davis", "Irvine", "Los Angeles", "Merced",
            "Riverside", "San Diego", "San Francisco", "Santa Barbara", "Santa Cruz"]
PAGE1 = CAMPUSES[:5]                    # Berkeley … Merced
PAGE2 = CAMPUSES[5:] + ["Systemwide"]   # Riverside … Santa Cruz + printed Systemwide col
MED_CAMPUSES = ["Davis", "Irvine", "Los Angeles", "San Diego", "San Francisco"]

# Function rows shared by every vintage. Per-vintage additions are in
# VINTAGE[fy]["extraRows"]. Order here is irrelevant to correctness: the
# parser matches LONGEST-LABEL-FIRST regardless of this list's order.
BASE_ROWS = [
    "Instruction", "Research", "Public service", "Academic support",
    "Student services", "Institutional support",
    "Operation and maintenance of plant", "Student financial aid",
    "Medical centers", "Auxiliary enterprises",
    "Depreciation and amortization", "Department of Energy laboratories",
    "Other",
]
STRIP_LINES = ["Medical centers", "Auxiliary enterprises",
               "Department of Energy laboratories"]

CAPS = dict(page="CAMPUS FINANCIAL FACTS", section="OPERATING EXPENSES BY FUNCTION")
MIXED = dict(page="Campus Financial Facts", section="Operating expenses by function")

# ── the per-vintage declaration table — DECLARED, never sniffed ──────
#   afr        (filename, URL)         cached source
#   anchors    CAPS or MIXED           per-vintage section/page headers
#   extraRows  list                    rows beyond BASE_ROWS this vintage prints
#   doeForm    "excluded"/"systemwide" how DOE enters Gate 1 and the strip
#   doeLabel   str                     the row label carrying DOE (systemwide form)
#   fte        (filename, URL)|None    per-year UCOP actual-FTE PDF (None = held year)
#   fullOtherInfo bool                 the auditors' report carries the full "other
#                                      information" statement ("read the other
#                                      information and consider whether a material
#                                      inconsistency exists"). FALSE for FY2020-21,
#                                      whose report predates that standard — measured,
#                                      so the sentence is not carried back onto it.
#   held       reason|None             None ships; a string HOLDS the year
def _afr(yy, yyyy):
    return (f"afr-{yyyy}.pdf", f"{AFR_BASE}{yy}/annual-financial-report-{yyyy}.pdf")
def _fte(fy):
    return (f"fte-{fy}.pdf", f"{FTE_BASE}{fy}.pdf")

VINTAGE = {
    "2024-25": dict(afr=_afr("24-25", "2025"), anchors=MIXED, extraRows=[],
                    doeForm="systemwide", doeLabel="Department of Energy laboratories",
                    fte=_fte("2024-25"), fullOtherInfo=True, held=None),
    "2023-24": dict(afr=_afr("23-24", "2024"), anchors=MIXED, extraRows=[],
                    doeForm="systemwide", doeLabel="Department of Energy laboratories",
                    fte=_fte("2023-24"), fullOtherInfo=True, held=None),
    "2022-23": dict(afr=_afr("22-23", "2023"), anchors=CAPS,
                    extraRows=["DOE Labs Expenses"],
                    doeForm="systemwide", doeLabel="DOE Labs Expenses",
                    fte=_fte("2022-23"), fullOtherInfo=True, held=None),
    "2021-22": dict(afr=_afr("21-22", "2022"), anchors=CAPS,
                    extraRows=["Other and Impairment of capital assets"],
                    doeForm="systemwide", doeLabel="Department of Energy laboratories",
                    fte=_fte("2021-22"), fullOtherInfo=True, held=None),
    "2020-21": dict(afr=_afr("20-21", "2021"), anchors=CAPS,
                    extraRows=["Impairment of capital assets"],
                    doeForm="excluded", doeLabel="Department of Energy laboratories",
                    fte=_fte("2020-21"), fullOtherInfo=False, held=None),
    "2019-20": dict(afr=_afr("19-20", "2020"), anchors=CAPS,
                    extraRows=["Impairment of capital assets"],
                    doeForm="excluded", doeLabel="Department of Energy laboratories",
                    fte=None, fullOtherInfo=False,
                    held="The FY2019-20 Campus Facts in Brief (Unaudited) does not "
                         "reconcile to the audited total operating expenses at the "
                         "thousand: campuses + Systemwide + UC's own added-back DOE "
                         "line miss by ~351K, where every later year ties exactly. "
                         "Held rather than shipped at a lower tier; re-measured every "
                         "build."),
}
FY_SHIPPED = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]  # oldest→newest
FY_LATEST = "2024-25"
FY_HELD = "2019-20"
HELD_RESIDUAL_BAND = (-500, -200)   # the ~-351K anomaly must persist in this band

TOL_K = 1        # column-sum tie tolerance (thousands) — UC's own rounding
TOL_WIDE_K = 10  # the uniqueness self-guard: still exactly one at 10× the width

# Corroboration only (never part of the gate): the separately-audited UC
# Medical Centers AFR FY2024-25 combining statement, PwC per-center
# opinions — a DIFFERENT measure (standalone-department basis) from the
# AFR's post-elimination functional line. Scale sanity check only.
MEDCTR_AFR_TOTAL_K = 23_914_031
MEDCTR_AFR_URL = ("https://www.ucop.edu/uc-controller/financial-reports/systemwide-reports/"
                  "medical-center-reports/24-25/medical-center-report-2025.pdf")


# ── fetch helpers ────────────────────────────────────────────────────
def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Citizen Ledger data pipeline"})
    with urllib.request.urlopen(req, timeout=180) as r:
        ctype = r.headers.get("Content-Type", "")
        return r.read(), ctype


def _cached(name, url, refresh):
    path = CACHE / name
    if path.exists() and not refresh:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    blob, ctype = _fetch(url)
    # Existence is proven on the bytes and the content-type, never on
    # status: %PDF- magic AND application/pdf. A soft-404 that answers
    # 200 with an HTML error page is refused here.
    if not blob.startswith(b"%PDF") or "application/pdf" not in ctype.lower():
        raise SystemExit(f"UC: {url} did not return a PDF "
                         f"(content-type {ctype!r}) — nothing written")
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


def _row_values(line):
    return [_num(m) for m in re.findall(r"\(?\$?[\d][\d,]*\)?", line)]


# ── the campus-facts parser with the column-sum proof ────────────────
def _parse_facts_page(text, columns, rowset, section):
    """Extract the function rows between the (per-vintage) section header
    and the campus-totals row. Rows are matched LONGEST-LABEL-FIRST so a
    combined label ("Other and Impairment…") wins over its prefix
    ("Other"). Returns ({label: [values-in-order]}, totals)."""
    i = text.find(section)
    if i < 0:
        return None, None
    # strip only footnote markers — "*", "[1]", or a bare single digit
    # ("Other6 …" / a wrapped "2 (26,039) …" continuation) — never value
    # digits (values in this table are always multi-digit)
    marker = re.compile(r"^\s*(?:\*|\[\d\]|\d(?=\s))*\s*")
    order = sorted(rowset, key=len, reverse=True)   # longest label first
    lines = [ln.strip() for ln in text[i:].split("\n")[1:]]
    rows, totals = {}, None
    for j, line in enumerate(lines):
        if line.startswith("Total"):
            totals = _row_values(line)
            break
        for lab in order:
            if line.startswith(lab):
                vals = _row_values(marker.sub("", line[len(lab):]))
                if not vals and j + 1 < len(lines):
                    # the row wrapped: label alone, values on the next line
                    nxt = lines[j + 1]
                    if not nxt.startswith("Total") and \
                       not any(nxt.startswith(o) for o in order):
                        vals = _row_values(marker.sub("", nxt))
                if vals:
                    rows[lab] = vals
                break
    if totals is None or len(totals) != len(columns):
        return None, None
    return rows, totals


def _assignments(rows, totals, columns, tol):
    """Count/return order-preserving assignments of every sparse row's
    values to columns under which every column's function lines sum to
    its printed total within `tol` thousand. Returns (winners, err) where
    winners is a list of combos (capped at 2 — we only care whether the
    count is 0, 1, or >1)."""
    n = len(columns)
    full, sparse = {}, {}
    for lab, vals in rows.items():
        if len(vals) == n:
            full[lab] = vals
        elif len(vals) < n:
            sparse[lab] = vals
        else:
            return None, f"row '{lab}' has {len(vals)} values for {n} columns"
    labs = sorted(sparse)
    options = [list(itertools.combinations(range(n), len(sparse[lab]))) for lab in labs]
    base = [sum(full[lab][c] for lab in full) for c in range(n)]
    winners = []
    for combo in itertools.product(*options):
        cols = list(base)
        for lab, pos in zip(labs, combo):
            for p, v in zip(pos, sparse[lab]):
                cols[p] += v
        if all(abs(cols[c] - totals[c]) <= tol for c in range(n)):
            winners.append(combo)
            if len(winners) > 1:
                break
    return (labs, sparse, full, winners), None


def _prove_assignment(rows, totals, columns):
    """Require EXACTLY ONE assignment at ±TOL_K, and — the uniqueness
    self-guard — still exactly one at ±TOL_WIDE_K, so the tolerance is
    proven not to be what makes the assignment unique. Returns
    ({label: {column: value}}, None) or (None, err)."""
    got, err = _assignments(rows, totals, columns, TOL_K)
    if err:
        return None, err
    labs, sparse, full, winners = got
    if len(winners) != 1:
        return None, (f"column-sum check: {len(winners)} sparse-row assignments tie "
                      f"at ±{TOL_K}K (need exactly 1) for sparse rows {labs}")
    wide, err = _assignments(rows, totals, columns, TOL_WIDE_K)
    if err:
        return None, err
    if len(wide[3]) != 1:
        return None, (f"uniqueness self-guard: {len(wide[3])} assignments tie at the "
                      f"wider ±{TOL_WIDE_K}K — the ±{TOL_K}K tie is only tolerance-deep "
                      f"and this vintage is genuinely ambiguous for {labs}")
    grid = {lab: dict(zip(columns, vals)) for lab, vals in full.items()}
    for lab, pos in zip(labs, winners[0]):
        grid[lab] = {columns[p]: v for p, v in zip(pos, sparse[lab])}
    return grid, None


def _header_order_ok(text, columns):
    """The printed campus-column header must list the columns in the same
    left-to-right order this pipeline assigns them positionally. Locate
    the header line — the one naming every column — and require ascending,
    distinct printed positions. A reordered column, which would tie the
    column-sum check while mis-attributing every figure, fails here. The
    comparison is case-folded because the campus names are printed CAPS in
    the older vintages and mixed in the newer; this verifies ORDER of
    already-named columns, not the presence of a section anchor, so it is
    not the case-insensitive anchor match this repo refuses."""
    want = [c.lower() for c in columns]
    for line in text.split("\n"):
        low = line.lower()
        pos = [low.find(w) for w in want]
        if -1 not in pos and pos == sorted(pos) and len(set(pos)) == len(pos):
            return True
    return False


def _statement_page(texts):
    return next((t for t in texts if "Total operating expenses" in t
                 and "State educational appropriations" in t
                 and "Medical centers, net" in t), None)


def _doe_opex_current(statement):
    """The Department of Energy laboratories OPERATING-EXPENSE line,
    current-year column — the figure the 'excluded' vintages add back to
    reconcile, and the cross-check for the 'systemwide' ones. The DOE line
    appears once in OPERATING REVENUES and once in OPERATING EXPENSES; the
    section headers do not survive text extraction in the newer vintages,
    but "Total operating revenues" always does and the expense-side DOE
    always follows it — so anchor there, never on the section header."""
    i = statement.find("Total operating revenues")
    seg = statement[i:] if i >= 0 else statement
    m = re.search(r"Department of Energy laboratories\s+\$?([\d,]{6,})", seg)
    return _num(m.group(1)) if m else None


def parse_afr(path, fy, v):
    """Parse one AFR: the two campus-facts pages (proven by column-sum and
    header order) plus the audited statement figures. Returns a dict or
    raises. `v` is the VINTAGE[fy] declaration."""
    import pypdf
    r = pypdf.PdfReader(str(path))
    texts = [(p.extract_text() or "") for p in r.pages]
    rowset = BASE_ROWS + v["extraRows"]
    anchors = v["anchors"]

    facts_pages = [i for i, t in enumerate(texts) if anchors["page"] in t]
    gates.require_exact(len(facts_pages), 2,
                        f"UC {fy} '{anchors['page']}' pages")
    grids, totals = {}, {}
    for pageidx, columns in zip(facts_pages, (PAGE1, PAGE2)):
        if not _header_order_ok(texts[pageidx], columns):
            raise SystemExit(f"UC {fy}: printed campus-column header not found in the "
                             f"expected order {columns} (page idx {pageidx}) — nothing written")
        rows, tot = _parse_facts_page(texts[pageidx], columns, rowset, anchors["section"])
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

    st = _statement_page(texts)
    if st is None:
        raise SystemExit(f"UC {fy}: audited statement page not found — nothing written")

    def first1(label):
        m = re.search(re.escape(label) + r"[\s$]*([\d,]{6,})", st)
        return _num(m.group(1)) if m else None

    audited_total = first1("Total operating expenses")
    state_appr = first1("State educational appropriations")
    op_rev = first1("Total operating revenues")
    doe_stmt = _doe_opex_current(st)
    if audited_total is None:
        raise SystemExit(f"UC {fy}: audited total not parsed — nothing written")

    # fall headcount (page-2 row is sparse: Systemwide has no enrollment)
    heads = {}
    for pageidx, columns in zip(facts_pages, (PAGE1, PAGE2)):
        m = re.search(r"Total fall enrollment\s+([\d, ]+)", texts[pageidx])
        if m:
            vals = _row_values(m.group(1))
            names = [c for c in columns if c != "Systemwide"]
            if len(vals) == len(names):
                heads.update(dict(zip(names, vals)))

    return {"grid": grids, "totals": totals, "auditedTotal": audited_total,
            "stateAppr": state_appr, "opRev": op_rev, "doeStatement": doe_stmt,
            "fallHeadcount": heads}


def parse_fte(path):
    """UCOP actual-FTE PDF: p1 general-campus totals, p2 health-sciences
    (Undergraduate/Graduate/Resident/Total) per campus."""
    import pypdf
    r = pypdf.PdfReader(str(path))
    t1, t2 = r.pages[0].extract_text(), r.pages[1].extract_text()
    gen, hs = {}, {}
    for name in CAMPUSES + ["University"]:
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


# ── strip + per-year assembly ────────────────────────────────────────
def _strip_amounts(a, v):
    """med / aux / doe totals for one year's parsed AFR, and the DOE
    source. DOE is taken from the campus Systemwide cell ("systemwide"
    vintages) or the statement's DOE operating-expense line ("excluded"
    vintages) — DECLARED by v["doeForm"], never inferred from parsing."""
    med = a["grid"].get("Medical centers", {})
    aux = a["grid"].get("Auxiliary enterprises", {})
    if v["doeForm"] == "systemwide":
        doe_k = a["grid"].get(v["doeLabel"], {}).get("Systemwide")
        doe_src = "campus-table Systemwide cell"
    else:  # excluded
        doe_k = a["doeStatement"]
        doe_src = "audited statement DOE operating-expense line"
    return med, aux, doe_k, doe_src


def _reconcile(a, med, aux, doe_k, v):
    """Gate 1 residual (thousands). For "excluded" vintages the campus
    table omits DOE, so the reconciling identity adds it back."""
    camp_sum = sum(a["totals"][c] for c in CAMPUSES)
    sw = a["totals"]["Systemwide"]
    lhs = camp_sum + sw + (doe_k if v["doeForm"] == "excluded" and doe_k else 0)
    return camp_sum, sw, lhs - a["auditedTotal"]


def build(refresh):
    fail = []
    parsed, strips, fte = {}, {}, {}
    for fy, v in VINTAGE.items():
        a = parse_afr(_cached(*v["afr"], refresh), fy, v)
        med, aux, doe_k, doe_src = _strip_amounts(a, v)
        parsed[fy] = a
        strips[fy] = dict(med=med, aux=aux, doe=doe_k, doeSrc=doe_src)
        if v["fte"]:
            fte[fy] = parse_fte(_cached(*v["fte"], refresh))

    # ── GATE 1, per year ─────────────────────────────────────────────
    gate_years = {}
    for fy, v in VINTAGE.items():
        a, s = parsed[fy], strips[fy]
        if s["doe"] is None:
            fail.append(f"{fy}: DOE amount not found via declared {v['doeForm']} form")
            continue
        camp_sum, sw, residual = _reconcile(a, s["med"], s["aux"], s["doe"], v)
        gate_years[fy] = {"campusSumK": camp_sum, "systemwideColK": sw,
                          "auditedTotalK": a["auditedTotal"], "residualK": residual,
                          "doeForm": v["doeForm"], "doeK": s["doe"]}
        if v["held"] is None:
            if abs(residual) > TOL_K:
                fail.append(f"{fy}: reconciliation residual {residual:+,}K exceeds "
                            f"±{TOL_K}K — nothing written")
        else:  # the held year: its anomaly must PERSIST, or a human re-decides
            if not (HELD_RESIDUAL_BAND[0] <= residual <= HELD_RESIDUAL_BAND[1]):
                fail.append(f"{FY_HELD}: held-year residual {residual:+,}K left its "
                            f"declared band {HELD_RESIDUAL_BAND} — it may now reconcile; "
                            f"a human must decide whether to ship it (do not auto-ship)")

    # cross-check: where DOE sits in the campus table, it must match the
    # statement DOE operating-expense line (a second, independent read)
    for fy, v in VINTAGE.items():
        if v["doeForm"] == "systemwide":
            s, a = strips[fy], parsed[fy]
            if a["doeStatement"] is not None and s["doe"] != a["doeStatement"]:
                fail.append(f"{fy}: campus DOE {s['doe']:,}K != statement DOE "
                            f"{a['doeStatement']:,}K — review required")

    # med-center roster: the five hospital campuses, every shipped year
    for fy in FY_SHIPPED:
        med_campuses = sorted(c for c in strips[fy]["med"] if c != "Systemwide")
        if med_campuses != MED_CAMPUSES:
            fail.append(f"{fy}: medical-center campus set changed: {med_campuses} — review required")

    # strip presence + core bounds, every shipped year
    for fy in FY_SHIPPED:
        a, s = parsed[fy], strips[fy]
        for label, val in (("Medical centers", s["med"]),
                           ("Auxiliary enterprises", s["aux"]),
                           ("Department of Energy laboratories", s["doe"])):
            if not val and val != 0:
                fail.append(f"{fy}: strip component {label!r} was not found in the "
                            "campus table — the strip cannot be built from UC's own lines")
        med_k = sum(s["med"].values())
        aux_k = sum(s["aux"].values())
        core_k = a["auditedTotal"] - med_k - aux_k - (s["doe"] or 0)
        if core_k < 0:
            fail.append(f"{fy}: strip residual is negative ({core_k:,}K) — the three "
                        "stripped lines exceed the audited total")
        if not 0.30 <= core_k / a["auditedTotal"] <= 0.90:
            fail.append(f"{fy}: core {core_k / a['auditedTotal']:.1%} of the audited total, "
                        "outside the 30-90% band")

    # FTE self-reconciliation, every shipped year (±2 FTE: UCOP rounds each
    # campus independently, so the University total need not equal the sum
    # of rounded campuses to the person; measured max discrepancy is 1 FTE)
    for fy in FY_SHIPPED:
        g, h = fte[fy]
        gen_res = sum(g.get(c, 0) for c in CAMPUSES) - g.get("University", 0)
        if abs(gen_res) > 2:
            fail.append(f"{fy}: general-campus FTE campus sum off University total by {gen_res}")
        hs_res = sum(h[c]["total"] for c in CAMPUSES if c in h) - h["University"]["total"]
        if abs(hs_res) > 2:
            fail.append(f"{fy}: health-sciences FTE campus sum off University total by {hs_res}")

    # med-center AFR corroboration (latest year; different measure, scale only)
    med_latest = sum(strips[FY_LATEST]["med"].values())
    if abs(med_latest / MEDCTR_AFR_TOTAL_K - 1) > 0.15:
        fail.append(f"medical-center scale check: AFR line {med_latest:,}K vs "
                    f"separately-audited med-center total {MEDCTR_AFR_TOTAL_K:,}K")

    # state share sanity, latest year
    A = parsed[FY_LATEST]
    share_opex = A["stateAppr"] / A["auditedTotal"]
    if not (0.05 < share_opex < 0.15):
        fail.append(f"state share of operating expenses {share_opex:.1%} outside sanity band")

    if fail:
        for f in fail[:16]:
            print("  UC GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"{len(fail)} gate failure(s) — nothing written")

    payload = _assemble(parsed, strips, fte, gate_years)
    stamp(payload)
    return payload, gate_years


def _assemble(parsed, strips, fte, gate_years):
    """Build the multi-year payload in the shape cities/counties/K-12/CCC
    already publish: identity at the entity, everything that varies by
    year inside a `years` map keyed by fiscal-year label. `systemwide` is
    a map keyed by FY (the mirror of CCC's `statewide`); `campuses` is a
    list of {name, years:{FY:{...}}}. The held year rides under `held`,
    encoded not-published — never a zero, never silently dropped.

    Only NUMERIC leaves under `systemwide[fy]` and `campus.years[fy]`
    enter the change record (revisions.flatten reads those two keys), so
    per-year overlap figures live in meta (unflattened) to keep the
    FY2024-25 re-addressing a no-op in the record."""
    systemwide, campus_years = {}, {c: {} for c in CAMPUSES}
    research_share, overlap_by_year = {}, {}
    for fy in FY_SHIPPED:
        a, s = parsed[fy], strips[fy]
        med, aux, doe_k = s["med"], s["aux"], s["doe"]
        med_k, aux_k = sum(med.values()), sum(aux.values())
        core_k = a["auditedTotal"] - med_k - aux_k - doe_k
        research = a["grid"].get("Research", {})
        research_core_sw = (sum(research.get(c, 0) for c in CAMPUSES)
                            + research.get("Systemwide", 0)) / core_k
        research_share[fy] = round(research_core_sw, 4)
        g, h = fte[fy]

        for c in CAMPUSES:
            total = a["totals"][c]
            m_, x_ = med.get(c, 0), aux.get(c, 0)
            core = total - m_ - x_
            gg = g.get(c, 0)
            hh = h.get(c)
            hs_students = (hh["total"] - hh["resident"]) if hh else 0
            fte_students = gg + hs_students          # residents EXCLUDED, explicitly
            campus_years[c][fy] = {
                "totalK": total, "medK": m_, "auxK": x_, "coreK": core,
                "functions": {lab: a["grid"][lab][c] for lab in a["grid"] if c in a["grid"][lab]},
                "fteGeneral": gg, "fteHealthStudents": hs_students,
                "fteResidents": hh["resident"] if hh else 0,
                "fteStudents": fte_students,
                "fallHeadcount": a["fallHeadcount"].get(c),
                "corePerFte": round(core * 1000 / fte_students) if fte_students else None,
                "flags": {
                    "medCenter": c in med,
                    "healthOnly": gg == 0,
                    "researchIntensive": core > 0 and (research.get(c, 0) / core) >= 1.25 * research_core_sw,
                    "smallScale": 0 < fte_students < 10000,
                },
            }

        sw_total = a["totals"]["Systemwide"]
        # DOE is subtracted from the systemwide reconciling column ONLY when it
        # actually sits in that column (the 'systemwide' vintages). In an
        # 'excluded' vintage DOE is not in sw_total at all — it is added back
        # separately to reconcile — so subtracting it here would double-count it
        # and break the decomposition (campus cores + systemwide core == core_k).
        doe_in_sw = doe_k if VINTAGE[fy]["doeForm"] == "systemwide" else 0
        sw_core = sw_total - med.get("Systemwide", 0) - aux.get("Systemwide", 0) - doe_in_sw
        fte_univ_students = g["University"] + h["University"]["total"] - h["University"]["resident"]
        systemwide[fy] = {
            "auditedTotalK": a["auditedTotal"], "systemwideColK": sw_total,
            "systemwideColLabel": "Systemwide (UCOP, DOE laboratory & eliminations)",
            "medK": med_k, "auxK": aux_k, "doeK": doe_k, "coreK": core_k,
            "systemwideCoreK": sw_core,
            "medSystemwideElimK": med.get("Systemwide", 0),
            "auxSystemwideElimK": aux.get("Systemwide", 0),
            "fteStudents": fte_univ_students,
            "fteResidents": h["University"]["resident"],
            "researchCoreShare": round(research_core_sw, 4),
            # strings/bools — not flattened into the change record; for the page
            "doeForm": VINTAGE[fy]["doeForm"], "doeSource": s["doeSrc"],
            "auditFullOtherInfo": VINTAGE[fy]["fullOtherInfo"],
        }
        share_opex = a["stateAppr"] / a["auditedTotal"]
        share_oprev = a["stateAppr"] / a["opRev"] if a["opRev"] else None
        overlap_by_year[fy] = {"stateApprK": a["stateAppr"], "opRevK": a["opRev"],
                               "shareOfOpex": round(share_opex, 4),
                               "shareOfOpRev": round(share_oprev, 4) if share_oprev else None}

    campuses = [{"name": c, "years": campus_years[c]} for c in CAMPUSES]
    return {
        "meta": _meta(overlap_by_year, gate_years, research_share),
        "years": FY_SHIPPED,
        "systemwide": systemwide,
        "campuses": campuses,
        "held": {FY_HELD: {
            "published": False,
            "status": "held-not-reconciled",
            "residualK": gate_years[FY_HELD]["residualK"],
            "reason": VINTAGE[FY_HELD]["held"],
        }},
    }


def _meta(overlap_by_year, gate_years, research_share):
    ov = overlap_by_year[FY_LATEST]
    share_opex, share_oprev = ov["shareOfOpex"], ov["shareOfOpRev"]
    return {
        "source": "ucop.edu",
        "sourceLabel": "University of California Annual Financial Report (audited by "
                       "PricewaterhouseCoopers LLP; the per-campus Campus Financial Facts "
                       "table is the report's own auditor-read front matter) and the UCOP "
                       "actual-FTE series",
        "generated": date.today().isoformat(),
        "year": FY_LATEST,          # the default/latest fiscal year (CCC convention)
        "years": FY_SHIPPED,
        "latest": FY_LATEST,
        "held": {FY_HELD: VINTAGE[FY_HELD]["held"]},
        "unit": "thousands of dollars (the finest resolution UC publishes)",
        "basis": "GAAP / GASB full-accrual, as audited. This is NOT the state budget "
                 "page's enacted, Budgetary-Legal basis; the two are measured "
                 "differently, are never reconciled to each other, and are never summed.",
        "gate": "EXACT TO THE THOUSAND, not to the cent — UC's statements are denominated "
                "in thousands. For each shipped year, with no write on failure: (1) the ten "
                "campuses plus UC's own printed Systemwide column (plus the audited "
                "statement's own DOE line where the campus table excludes it) equal the "
                "audited total operating expenses; (2) the column-sum check: every campus "
                "column's function lines sum to that column's printed total, with the sparse "
                "rows' assignment proven unique by exhaustion — and still unique at ten times "
                "the rounding tolerance, "
                "so the tolerance is not what makes it unique; (3) the printed campus-column "
                "header lists the columns in the assigned order.",
        "window": "FY2020-21 through FY2024-25 ship (five years). FY2019-20 is HELD: its "
                  "unaudited Campus Facts in Brief does not reconcile to the audited total "
                  "at the thousand (it misses by ~351K where every later year ties), so it "
                  "is not shipped rather than shipped at a lower tier. The build re-measures "
                  "that residual every run and fails if it ever closes.",
        "doeBreak": "UC publishes the Department of Energy laboratories line two ways across "
                    "this window, and the six-year core line is assembled accordingly. Through "
                    "FY2020-21 the campus table EXCLUDES the DOE laboratory (UC's own printed "
                    "\"Excludes DOE laboratories\" footnote), so the audited DOE line is added "
                    "back to reconcile; from FY2021-22 the DOE laboratory sits inside UC's "
                    "printed Systemwide column. The core strip removes the same DOE quantity "
                    "either way, so the figures are comparable — but they are assembled from "
                    "differently-presented source tables, which is stated where the series "
                    "crosses that boundary, not only here.",
        "unauditedStatus": "The per-campus table is UC's \"Campus Facts in Brief "
                    "(Unaudited)\" — the auditor's \"other information\", the part of the "
                    "annual report management, not the auditor, is responsible for. PwC "
                    "\"do not express an opinion\" on it, while their stated responsibility "
                    "is \"to read the other information and consider whether a material "
                    "inconsistency exists\" between the other information and the basic "
                    "financial statements. (The auditors' report identifies that other "
                    "information by page range, and the range differs between reports, so it "
                    "is not quoted here.) The audited figure the table reconciles to — the "
                    "systemwide total — carries PwC's unmodified opinion. The campus detail "
                    "does NOT carry that audit status; the reconciliation is the check.",
        # FY2020-21 predates the standard that added the "read the other information …
        # material inconsistency" language (measured: that report has "do not express
        # an opinion" but not the read/inconsistency sentence), so it is NOT quoted onto
        # that year — the page shows this reduced form there instead.
        "unauditedStatusReduced": "The FY2020-21 per-campus table is headed \"Campus Facts "
                    "in Brief (Unaudited)\", and PwC \"do not express an opinion\" on it. That "
                    "vintage's auditors' report predates the standard that added the formal "
                    "\"other information\" section with the auditor's read-and-consider "
                    "responsibility later reports carry, so that fuller language is not "
                    "attributed to it here. As in every year, the systemwide total the table "
                    "reconciles to carries PwC's unmodified opinion; the campus detail does NOT "
                    "carry that audit status, and the reconciliation is the check.",
        "reproducibility": "AUTO-REPRODUCIBLE. Every source is a public ucop.edu URL fetched "
                    "by plain scripted GET — the Annual Financial Reports and the UCOP "
                    "actual-FTE PDFs, one of each per fiscal year. Run "
                    "`python3 pipeline/fetch_uc_data.py --refresh` to rebuild from the live "
                    "sources. No manual-cache exception — that remains CSU's alone.",
        "strip": {
            "definition": "The strip is defined ENTIRELY by UC's own published functional "
                "lines — \"Medical centers\", \"Auxiliary enterprises\", and \"Department of "
                "Energy laboratories\" — never by our judgment about what counts as education. "
                "The stripped components are shown separately, never deleted.",
            "residual": "The three stripped lines are UC's own, and their values are proven "
                "by the column-sum check. What is left after them — the core — is NOT a figure "
                "UC publishes; it is the arithmetic remainder of the audited total less the "
                "three strips, computed by the Ledger, bounded and sanity-checked but a "
                "residual, not a published number, and it inherits any error in the three "
                "lines subtracted from it.",
            "limit": "UC's segmentation strips the hospital ENTERPRISES, not the schools of "
                "medicine. Health-sciences instruction, research, and academic support remain "
                "inside the core — UC publishes no per-campus separation of them, and this "
                "record does not invent one. A campus with medical and health-sciences schools "
                "therefore carries a structurally higher core than one without; the per-student "
                "figures are NOT comparable across that divide and are flagged, never ranked.",
            "medNote": "Corroboration: UC separately publishes an audited Medical Centers "
                "Annual Financial Report (PwC opinion on each of the five medical centers; "
                f"FY2024-25 combined operating expenses ${MEDCTR_AFR_TOTAL_K:,}K, \"Total "
                "(memorandum only)\"). That is a different measure (standalone-department "
                "statements) from the AFR's post-elimination functional line stripped here; "
                "the two are never summed or substituted.",
            "labsNote": "The Department of Energy laboratories line is Lawrence Berkeley "
                "National Laboratory, which UC's Note 1 states is included in the statements. "
                "Los Alamos (Triad National Security, LLC) and Lawrence Livermore (Lawrence "
                "Livermore National Security, LLC) are equity-method investments ALREADY "
                "OUTSIDE the total; UC does not disclose the equity income amount, so no figure "
                "is shown for them (not because it is zero).",
        },
        "denominator": "Per-student uses STUDENT FTE from UCOP's actual-FTE series (general "
                "campus plus health sciences), one PDF per fiscal year, fiscal-year-aligned. "
                "Medical residents are on UC's own labeled \"Resident\" line and are EXCLUDED "
                "from the denominator — employees-in-training, not enrolled students; the "
                "resident counts are carried so the choice is auditable. This is FTE, not "
                "headcount (fall headcount is carried as a cross-check field, never mixed in).",
        "comparabilityNote": "Campuses differ in ways that make per-FTE core a measure of "
                "MISSION and STRUCTURE, not performance: five run hospital enterprises and "
                "medical schools, five do not; UCSF is health-sciences-only with no "
                "undergraduates; research intensity spans an order of magnitude. The Ledger "
                "shows the figures, flags the differences, and never ranks campuses.",
        "overlap": {
            "stateApprK": ov["stateApprK"], "auditedTotalK": gate_years[FY_LATEST]["auditedTotalK"],
            "opRevK": ov["opRevK"],
            "shareOfOpex": share_opex,
            "shareOfOpRev": share_oprev,
            "statement": "The state's appropriation to UC is state money already inside the "
                "spending shown here — a portion of it, not an amount to add. In the latest "
                f"year UC recognized about {share_opex*100:.1f}% of its operating expenses "
                "and " + (f"{share_oprev*100:.1f}%" if share_oprev else "a similar share") +
                " of its operating revenues as state educational appropriations — the least "
                "state-funded of the three public systems. The state budget page's enacted UC "
                "line is Budgetary-Legal; these figures are audited GAAP accrual. Do not sum "
                "them, and do not treat one as reconciling to the other.",
        },
        "overlapByYear": overlap_by_year,
        "researchCoreShareByYear": research_share,
        "gateHistory": gate_years,
    }


def main():
    ap = argparse.ArgumentParser(description="Rebuild uc-data.js")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch of all live sources (ignore the local cache)")
    args = ap.parse_args()

    payload, gate_years = build(args.refresh)
    for fy in reversed(FY_SHIPPED):
        g = gate_years[fy]
        print(f"FY {fy}: GATE PASSED — 10 campuses ({g['campusSumK']:,}K) + Systemwide "
              f"({g['systemwideColK']:,}K){' + DOE add-back' if g['doeForm']=='excluded' else ''} "
              f"== audited {g['auditedTotalK']:,}K (residual {g['residualK']}K; DOE {g['doeForm']})",
              file=sys.stderr)
    h = gate_years[FY_HELD]
    print(f"FY {FY_HELD}: HELD — reconciliation residual {h['residualK']:,}K "
          f"(band {HELD_RESIDUAL_BAND}); not shipped.", file=sys.stderr)
    print("  column-sum check: unique at ±1K AND ±10K, every shipped year; printed-header "
          "order verified.", file=sys.stderr)

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"  payload {len(body)/1024:.0f} KB", file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_uc_data.py from the UC Annual Financial "
              "Reports and the UCOP actual-FTE series (public ucop.edu URLs; "
              "auto-reproducible with --refresh). Five fiscal years FY2020-21..FY2024-25; "
              "FY2019-20 held (does not reconcile). Figures in thousands. (No equals sign "
              "may appear in this comment: the loader slices from the first one.) */\n")
    prev = revisions.previous_payload(OUT_PATH)
    OUT_PATH.write_text(header + "window.CA_UC_DATA = " + body + ";\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size/1024:.0f} KB)")
    revisions.record_revision('uc', prev, payload)


if __name__ == "__main__":
    main()
