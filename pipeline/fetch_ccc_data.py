#!/usr/bin/env python3
"""
Citizen Ledger — California Community College district pipeline (V11).

Rebuilds ../ccc-data.js from the Chancellor's Office CCFS-311 public
reporting portal and two published CCCCO source documents. Unlike the
CSU layer, this layer is FULLY AUTO-REPRODUCIBLE: every source is a
public endpoint this script fetches without credentials. There is no
manual-cache exception here (that exception applies only to the
bot-gated CSU PDFs; see docs/SCOPE.md).

FISCAL YEAR: 2022-23 — the latest year for which the CCFS-311 filings,
the independent district audits, and the SCFF apportionment
recalculation are all final and reconciled.

────────────────────────────────────────────────────────────────────
THE GATE — WHOLE DOLLARS, EXACT (no write on failure)
────────────────────────────────────────────────────────────────────
Every figure the Chancellor's Office publishes on the CCFS-311 portal
is an integer number of dollars (no cents — proven empirically). The
control figure is the Current Expense of Education (ECS 84362), the
community-college analog of K-12's Current Expense of Education (EDP
365). The Chancellor's Office publishes it two ways that must agree to
the dollar:

  • per district, in Table VI ("Summary of Current Expense of
    Education, ECS 84362"), one row per district; and
  • as a printed statewide total on that same Table VI.

GATE: the 73 per-district Current Expense of Education figures this
script extracts must sum to the Chancellor's Office's own printed
Statewide total, EXACTLY, to the dollar. A single mis-extracted,
missing, or duplicated district breaks the sum and nothing is written.
(FY2022-23: 73 districts sum to $8,469,851,699 = the printed Statewide
row.) This is a third, accurately-named resolution tier — exact to the
DOLLAR: finer than CSU's thousand, coarser than K-12's cent.

The figures are independently validated OFF the site by the mandatory
CPA audit each district files under Ed Code 84040 / Title 5: the
CCFS-311 fund balances equal the audited fund balances (the V11
finding read two districts' reconciliation schedules — both "no
adjustments", a $0 residual).

IMPORTANT CORRECTION (this build vs the V11 finding): the finding
quoted Los Angeles CCD's Current Expense of Education as $774,683,675.
That figure is the 50-Percent-Law report's "Total Expenditures Prior
to Exclusions" — a PRE-exclusion line, not ECS 84362. The published
Current Expense of Education (Table VI, after the ECS 84362 exclusions)
is $716,533,122 for Los Angeles. This build uses the Table VI figure,
the one the Chancellor's Office actually publishes as ECS 84362.

────────────────────────────────────────────────────────────────────
BASIS: modified-accrual on the CCC Budget and Accounting Manual (BAM)
uniform chart — the same basis and shape as K-12's SACS. This is NOT
the state budget page's enacted Budgetary-Legal community-college
appropriation; the two are measured differently, are never reconciled
to each other, and are never summed (see the overlap note).

DENOMINATOR: per-FTES uses the APPORTIONMENT funded FTES from the SCFF
Exhibit C (2022-23 Recalculation) — the audited, fiscal-year-aligned
workload measure, NOT the CCCCO Data Mart's derived count (enrollment
hours ÷ 525, which CCCCO itself states is not the apportionment
methodology). Calbright (California Online CCD) is not SCFF-funded and
has no apportionment FTES, so it carries no per-FTES figure.

SOURCES (all public, all fetched by this script):
  1. CCFS-311 portal — Table VI + district dropdown:
     https://fiscalportal.cccco.edu/Reports/AnnualReports
     (ASP.NET SSRS ReportViewer; the statewide report button is
     disabled until a fiscal-year autopostback fires — this script
     scripts that handshake.)
  2. CCCCO District & College Codes (MIS Appendix A):
     https://webdata.cccco.edu/ded/DistrictCollegeCodes.pdf
     → colleges per district; reconciles to the official 116.
  3. CCCCO SCFF 2022-23 Recalculation Exhibit C:
     https://www.cccco.edu/-/media/CCCCO-Website/docs/apportionment/
       2022-23-R1-Exhibit-C-March-2024.pdf
     → apportionment funded FTES, State General Fund allocation,
       property-tax excess (the community-supported / basic-aid
       signal), and credit vs noncredit FTES. Self-reconciles to its
       own printed statewide totals.

Usage:
    python3 fetch_ccc_data.py            # dry run: fetch/parse + gate
    python3 fetch_ccc_data.py --write    # rebuild ../ccc-data.js
    python3 fetch_ccc_data.py --refresh  # force re-fetch (ignore cache)
Requires: pypdf (for the two PDF sources), standard library otherwise.
"""

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "ccc"
OUT_PATH = ROOT / "ccc-data.js"
FY = "2022-23"
FY_PORTAL = "14"  # CCFS-311 FiscalYearDropdown value for 2022-23

PORTAL = "https://fiscalportal.cccco.edu/Reports/AnnualReports"
DCC_URL = "https://webdata.cccco.edu/ded/DistrictCollegeCodes.pdf"
EXHIBITC_URL = ("https://www.cccco.edu/-/media/CCCCO-Website/docs/apportionment/"
                "2022-23-R1-Exhibit-C-March-2024.pdf")
UA = {"User-Agent": "Mozilla/5.0 (Citizen Ledger data pipeline)", "Referer": PORTAL}

# The one district in Table VI that is absent from the report dropdown
# (its individual FY2022-23 50-Percent-Law report was not certified in
# time to appear as a selectable report); Table VI still carries its
# Current Expense of Education. Its MIS district code:
ALLAN_HANCOCK_CODE = "610"

# apportionment-name → portal-canonical-name normalized aliases (the
# three sources spell a handful of merged/renamed districts differently)
APPN_ALIAS = {
    "BUTTEGLENN": "BUTTE",
    "SHASTATEHAMATRINITY": "SHASTATEHTRI",
    "NAPAVALLEY": "NAPA",
    "WESTVALLEYMISSION": "WESTVALLEY",
}
_DROP = {"JOINT", "COUNTY", "AREA", "PENINSULA", "CCD", "DISTRICT",
         "COMMUNITY", "COLLEGE"}
# non-college MIS entries (adult / continuing-ed centers carry their own
# code but are not ACCJC-accredited colleges) — filtered so the roster
# reconciles to the official 116 accredited colleges
_CENTER = re.compile(r"\b(Adult|Continuing|Ctrs|CED|Center)\b", re.I)


def _norm(s):
    s = s.upper().replace("-", " ").replace(".", " ").replace("'", " ")
    return "".join(t for t in s.split() if t not in _DROP)


def _overlap():
    """The state-overlap 'these figures do not add' statement. The dollar
    magnitudes are the LAO systemwide funding structure (the authoritative
    source for how the whole CCC system is funded across all sources, which
    is broader than the SCFF apportionment this pipeline reconciles); the
    share is COMPUTED from them here, not hardcoded, so it stays honest if a
    figure is updated."""
    total_b, state_b, prop98_b, ptax_b = 19.0, 9.7, 13.6, 4.5
    state_pct = round(state_b / total_b * 100)
    prop98_pct = round(prop98_b / total_b * 100)
    return {
        "totalFundingB": total_b, "stateGeneralFundB": state_b,
        "prop98GuaranteeB": prop98_b, "localPropertyTaxB": ptax_b,
        "stateSharePct": state_pct,
        "source": "Legislative Analyst's Office, California Community Colleges budget "
                  "analysis (systemwide funding structure)",
        "statement": "The state's appropriation to the community colleges is state money "
            "already inside the district figures here — a portion of them, not an amount to "
            f"add. Across all sources the community colleges receive about ${total_b:g} billion "
            f"a year; the state General Fund share is roughly ${state_b:g} billion, about "
            f"{state_pct}% of it. The Proposition 98 K-14 guarantee (${prop98_b:g} billion, "
            f"{prop98_pct}%) is a third, distinct number that also counts local property tax "
            f"(${ptax_b:g} billion), so it is neither the state's General Fund contribution nor "
            "total district spending. Do not sum these figures, and do not treat the state "
            "budget page's enacted community-college line as reconciling to the audited "
            "district spending here.",
    }


# ── fetch helpers ────────────────────────────────────────────────────
def _get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read() if binary else r.read().decode("utf-8", "replace")


def _tokens(html):
    def hid(f):
        m = re.search(r'id="' + f + r'"[^>]*value="([^"]*)"', html)
        return m.group(1) if m else ""
    return {"__VIEWSTATE": hid("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": hid("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": hid("__EVENTVALIDATION")}


def _post(tokens, extra):
    data = dict(tokens)
    data.update(extra)
    req = urllib.request.Request(PORTAL, data=urllib.parse.urlencode(data).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def _plain(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.replace("&nbsp;", " "))))


def _cached(name, fetch, refresh, binary=False):
    """Fetch live and cache; reuse cache unless --refresh. Cache is
    gitignored (pipeline/cache/) so a clean checkout always fetches."""
    path = CACHE / name
    if path.exists() and not refresh:
        return path.read_bytes() if binary else path.read_text(encoding="utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    blob = fetch()
    if binary:
        path.write_bytes(blob)
    else:
        path.write_text(blob, encoding="utf-8")
    return blob


# ── source 1: CCFS-311 portal ────────────────────────────────────────
def fetch_dropdown(refresh):
    html = _cached("dropdown.html", lambda: _get(PORTAL), refresh)
    m = re.search(r'id="DistrictDropdown".*?</select>', html, re.S)
    code2name = {}
    for c, raw in re.findall(r'<option value="(\d+)"[^>]*>(.*?)</option>', m.group(0), re.S):
        nm = re.sub(r"-{2,}.*$", "", _plain(raw).strip()).strip()  # drop "-----(Not Certified)"
        code2name[c] = nm
    code2name[ALLAN_HANCOCK_CODE] = "ALLAN HANCOCK"  # present in Table VI, absent from dropdown
    return code2name


def fetch_table_vi(refresh):
    """Table VI = Summary of Current Expense of Education (ECS 84362):
    per-district CE + instructional salaries + 50%-law percent, and a
    printed statewide total row. The Run button is disabled until a
    fiscal-year autopostback fires, so this scripts the handshake."""
    def live():
        html = _get(PORTAL)
        tk = _tokens(html)
        s1 = _post(tk, {"__EVENTTARGET": "ctl00$MainContent$FiscalYearDropdown",
                        "ctl00$MainContent$FiscalYearDropdown": FY_PORTAL,
                        "ctl00$MainContent$StatewideReportDropdown": "40"})
        tk2 = _tokens(s1)
        run = _post(tk2, {"ctl00$MainContent$FiscalYearDropdown": FY_PORTAL,
                          "ctl00$MainContent$StatewideReportDropdown": "40",
                          "ctl00$MainContent$RunStatewideReport": "View Report"})
        return _plain(run)
    text = html.unescape(_cached("tablevi-fy2223.txt", live, refresh))  # idempotent for cached/live
    anchor = "Percent of Instructors' Salaries to Current Expense of Education"
    i = text.find(anchor)
    if i < 0:
        raise SystemExit("CCC: Table VI did not render (portal handshake failed) — nothing written")
    seg = text[i + len(anchor):]
    ms = re.search(r"Statewide\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)%", seg)
    if not ms:
        raise SystemExit("CCC: Table VI statewide total row not found — nothing written")
    statewide = {"ce": int(ms.group(1).replace(",", "")),
                 "instrSal": int(ms.group(2).replace(",", "")),
                 "pct50": float(ms.group(3))}
    rows = re.findall(r"([A-Z][A-Z .&'\-]+?)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)%", seg[:ms.start()])
    tvi = {}
    for nm, ce, sal, pct in rows:
        tvi[nm.strip()] = {"ce": int(ce.replace(",", "")),
                           "instrSal": int(sal.replace(",", "")),
                           "pct50": float(pct)}
    return tvi, statewide


# ── source 2: MIS District & College Codes PDF ───────────────────────
def fetch_roster(refresh):
    import pypdf
    blob = _cached("DistrictCollegeCodes.pdf", lambda: _get(DCC_URL, binary=True), refresh, binary=True)
    (CACHE / "_dcc_tmp.pdf").write_bytes(blob)
    r = pypdf.PdfReader(CACHE / "_dcc_tmp.pdf")
    lines = [l.strip() for l in "\n".join(p.extract_text() for p in r.pages).split("\n") if l.strip()]
    (CACHE / "_dcc_tmp.pdf").unlink(missing_ok=True)
    roster, cur, i = {}, None, 0
    while i < len(lines):
        l = lines[i]
        if re.search(r"\bCCD$", l) and i + 1 < len(lines) and re.fullmatch(r"\d{3}", lines[i + 1]):
            cur = lines[i + 1]
            roster[cur] = {"name": l, "colleges": []}
            i += 2
            continue
        if (cur and i + 1 < len(lines) and re.fullmatch(r"\d{3}", lines[i + 1])
                and not re.search(r"\bCCD$", l) and l not in ("District", "College", "GI01")):
            if not _CENTER.search(l):
                roster[cur]["colleges"].append(l)
            i += 2
            continue
        i += 1
    return roster


# ── source 3: SCFF Exhibit C PDF ─────────────────────────────────────
def fetch_apportionment(refresh):
    import pypdf
    blob = _cached("apportionment-2022-23-R1-ExhibitC.pdf",
                   lambda: _get(EXHIBITC_URL, binary=True), refresh, binary=True)
    (CACHE / "_exc_tmp.pdf").write_bytes(blob)
    r = pypdf.PdfReader(CACHE / "_exc_tmp.pdf")

    def num(s):
        s = s.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
        if s in ("", "-", "—"):
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0

    def lastnum(line):
        n = re.findall(r"[\d,]+\.\d+|[\d,]+", line)
        return float(n[-1].replace(",", "")) if n else 0.0

    appn, statewide = {}, {}
    for pg in range(len(r.pages)):
        t = r.pages[pg].extract_text()
        # WHICH ENTITY THIS PAGE IS ABOUT is the line immediately BEFORE
        # "Exhibit C - Page 1" — line 1 on a district page, line 3 on the
        # statewide summary, which carries two masthead lines first. The
        # previous matcher required the name to end in "CCD"/"District" on
        # the very first line, so the statewide page was excluded BY
        # CONSTRUCTION: the reconciliation target was never found,
        # `statewide` stayed {}, and both comparisons below skipped
        # themselves while the build reported success.
        lines = [ln.strip() for ln in t.splitlines()]
        try:
            hdr = lines.index("Exhibit C - Page 1")
        except ValueError:
            continue
        name = next((lines[k] for k in range(hdr - 1, -1, -1) if lines[k]), "")
        if not name:
            continue
        if "Statewide" in name:  # statewide summary page → reconciliation totals
            mm = re.search(r"Funded FTES:\s+([\d,]+\.\d+)", t)
            if mm:
                statewide["fundedFtes"] = num(mm.group(1))
            mm = re.search(r"State General Fund Allocation\s+([\d,]+)\s*\n", t)
            if mm:
                statewide["stateGf"] = num(mm.group(1))
            mm = re.search(r"(\d+)\s+Fully Community Supported Districts", t)
            if mm:
                statewide["communitySupported"] = int(mm.group(1))
            continue
        d = {}
        for key, pat in [
            ("fundedFtes", r"Funded FTES:\s+([\d,]+\.\d+)"),
            ("stateGf", r"State General Fund Allocation\s+([\d,]+)\s*\n"),
            ("ptaxExcess", r"Less Property Tax Excess\s+(\(?[\d,]*\)?|-)"),
        ]:
            mm = re.search(pat, t)
            d[key] = num(mm.group(1)) if mm else 0.0
        # noncredit share from the Section Ia funded-FTES-by-category block
        sec = t[t.find("Section Ia"):]
        cats = {}
        for cat in ("CDCP", "Noncredit"):
            mm = re.search(r"(?:^|\n)" + re.escape(cat) + r"\s+([\d,.\s()\-]+?)(?:\n[A-Z]|\nTotal)", sec)
            if mm:
                cats[cat] = lastnum(mm.group(1))
        nc = cats.get("Noncredit", 0) + cats.get("CDCP", 0)
        # A missing denominator is not a measurement of zero noncredit.
        d["noncreditShare"] = (round(nc / d["fundedFtes"], 4)
                               if d["fundedFtes"] else None)
        appn[name] = d
    (CACHE / "_exc_tmp.pdf").unlink(missing_ok=True)
    return appn, statewide


# ---------------------------------------------------- declared absences
#
# WHY A DISTRICT HAS NO APPORTIONMENT RECORD, stated per district.
#
# The page used to carry ONE hardcoded sentence for every district whose
# apportionment was missing — Calbright's sentence, about being the state's
# online college. That is true of exactly one district. Rendered for any
# other, it would tell a reader that Los Angeles CCD is the state's online
# community college: a fabricated explanation, which is worse than a blank.
#
# The reason now travels WITH the record, and a district whose absence has
# no declared reason fails the build rather than borrowing someone else's.
NO_APPORTIONMENT = {
    "210": "Calbright is the state\u2019s online community college and is not "
           "funded through the apportionment formula, so it has no "
           "funded-FTES denominator and no per-FTES figure.",
}


# ── join + gate ──────────────────────────────────────────────────────
def build(refresh):
    code2name = fetch_dropdown(refresh)
    tvi, tvi_statewide = fetch_table_vi(refresh)
    roster = fetch_roster(refresh)
    appn, appn_statewide = fetch_apportionment(refresh)

    name2code = {v: k for k, v in code2name.items()}
    canon_n = {_norm(nm): code for nm, code in name2code.items()}
    app2code = {}
    for fn in appn:
        k = _norm(fn)
        app2code[fn] = canon_n.get(APPN_ALIAS.get(k, k))
    code2app = {c: appn[fn] for fn, c in app2code.items() if c}

    # ── structural pre-gate: the three sources must line up ──────────
    fail = []
    tvi_codes = {name2code.get(nm) for nm in tvi}
    if None in tvi_codes:
        fail.append("Table VI has a district name not in the portal dropdown: "
                    + ", ".join(nm for nm in tvi if nm not in name2code))
        tvi_codes.discard(None)
    if len(tvi) != 73:
        fail.append(f"{len(tvi)} Table VI districts (expected 73)")
    missing_roster = tvi_codes - set(roster)
    if missing_roster:
        fail.append(f"districts with no college roster: {sorted(missing_roster)}")
    unmatched_appn = [fn for fn, c in app2code.items() if c is None]
    if unmatched_appn:
        fail.append(f"apportionment districts not matched to a code: {unmatched_appn}")

    n_colleges = sum(len(roster[c]["colleges"]) for c in tvi_codes if c in roster)
    if n_colleges != 116:
        fail.append(f"{n_colleges} accredited colleges across districts (expected 116)")

    # ── THE GATE: sum of per-district CE == printed statewide, exact ──
    gates.require_target(tvi_statewide, "Table VI printed statewide totals",
                         "the whole-dollar gate cannot run.")
    gates.require_rows(len(tvi), 70, "Table VI districts")
    ce_sum = sum(v["ce"] for v in tvi.values())
    if ce_sum != tvi_statewide["ce"]:
        fail.append(f"WHOLE-DOLLAR GATE FAILED: 73 districts sum to {ce_sum:,} "
                    f"but Table VI's printed Statewide total is "
                    f"{tvi_statewide['ce']:,} (residual {ce_sum - tvi_statewide['ce']:+,})")

    # ── apportionment self-reconciliation (funded FTES, state GF) ────
    # The target must EXIST before it is compared against. Guarding each
    # comparison with `if appn_statewide.get(k) and ...` meant a missing
    # control skipped the check and the build reported success — which is
    # what happened for FY2022-23 until the parser above was fixed.
    gates.require_target(
        appn_statewide, "Exhibit C statewide totals",
        "funded FTES and state General Fund would go unreconciled.")
    gates.require_rows(len(code2app), 70,
                       "apportionment districts matched to a district code")
    for key, label in (("fundedFtes", "funded FTES"),
                       ("stateGf", "state General Fund")):
        gates.require_target(
            appn_statewide.get(key), f"Exhibit C statewide {label}",
            f"the {label} reconciliation cannot run.")
    ftes_sum = round(sum(a["fundedFtes"] for a in code2app.values()), 2)
    if abs(ftes_sum - appn_statewide["fundedFtes"]) > 0.5:
        fail.append(f"funded FTES sum {ftes_sum} != Exhibit C statewide "
                    f"{appn_statewide['fundedFtes']}")
    gf_sum = round(sum(a["stateGf"] for a in code2app.values()))
    if gf_sum != round(appn_statewide["stateGf"]):
        fail.append(f"state GF sum {gf_sum:,} != Exhibit C statewide "
                    f"{round(appn_statewide['stateGf']):,}")
    basic_n = sum(1 for a in code2app.values() if a["ptaxExcess"] < -1)
    # The control must EXIST, and a control of ZERO is a real published
    # value — not a reason to skip the comparison. Truthiness conflated
    # the two: a year in which the Chancellor's Office legitimately
    # prints zero community-supported districts would have disabled the
    # check entirely, and a missing control did so silently.
    cs_control = appn_statewide.get("communitySupported")
    if cs_control is None:
        gates.require_target(
            None, "Exhibit C statewide 'Fully Community Supported Districts'",
            "meta.daggers.basicAid claims this count matches the "
            "Chancellor's Office figure, so the claim cannot be made.")
    if basic_n != cs_control:
        fail.append(f"{basic_n} community-supported districts derived but Exhibit C "
                    f"states {appn_statewide['communitySupported']}")

    if fail:
        for f in fail[:12]:
            print("  CCC GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"FY {FY}: {len(fail)} gate failure(s) — nothing written")

    # statewide noncredit share → the data-derived "noncredit-heavy" threshold (2× statewide)
    sw_nc_num = sum((code2app[c]["noncreditShare"]) * code2app[c]["fundedFtes"]
                    for c in code2app)
    sw_nc_share = sw_nc_num / ftes_sum
    nc_threshold = round(2 * sw_nc_share, 4)

    # ── assemble districts ───────────────────────────────────────────
    districts = []
    for nm, cev in tvi.items():
        code = name2code[nm]
        colleges = roster[code]["colleges"]
        a = code2app.get(code)
        rec = {
            "name": nm, "code": code,
            "ce": cev["ce"], "instrSal": cev["instrSal"], "pct50": cev["pct50"],
            "colleges": colleges, "nColleges": len(colleges),
        }
        if a:
            rec["fundedFtes"] = round(a["fundedFtes"], 2)
            rec["stateGf"] = round(a["stateGf"])
            rec["perFtes"] = round(cev["ce"] / a["fundedFtes"]) if a["fundedFtes"] else None
            rec["noncreditShare"] = a["noncreditShare"]
            rec["basicAid"] = a["ptaxExcess"] < -1
        else:
            # ABSENCE MARKS ABSENCE. `basicAid = False` used to publish
            # "we checked the property-tax-excess schedule and this is not
            # a community-supported district" about a district whose
            # apportionment we never had. Unknown is None, like its four
            # siblings, and the reason travels with the record.
            reason = NO_APPORTIONMENT.get(rec["code"])
            if not reason:
                raise SystemExit(
                    f"CCC: {rec['name']} ({rec['code']}) has no apportionment "
                    "record and no declared reason. An unexplained absence is "
                    "a parse failure until it is shown otherwise; declare it "
                    "in NO_APPORTIONMENT deliberately. Nothing written.")
            rec["fundedFtes"] = None
            rec["stateGf"] = None
            rec["perFtes"] = None
            rec["noncreditShare"] = None
            rec["basicAid"] = None
            rec["noApportionmentReason"] = reason
        rec["flags"] = {
            "multiCollege": rec["nColleges"] > 1,
            "basicAid": rec["basicAid"],
            # None (unknown) is distinct from False (measured, and it isn't)
            "noncreditHeavy": (None if rec["noncreditShare"] is None
                               else rec["noncreditShare"] >= nc_threshold),
            "noApportionment": a is None,
        }
        districts.append(rec)
    districts.sort(key=lambda r: r["name"])

    dangerous = sorted(r["name"] for r in districts
                       if r["flags"]["multiCollege"] and r["flags"]["basicAid"])

    payload = {
        "meta": {
            "source": "fiscalportal.cccco.edu",
            "sourceLabel": "California Community Colleges Chancellor's Office — CCFS-311 "
                           "Annual Financial and Budget Report (Table VI, Current Expense of "
                           "Education, ECS 84362); SCFF 2022-23 Recalculation Exhibit C; MIS "
                           "District & College Codes",
            "generated": date.today().isoformat(),
            "year": FY,
            "unit": "whole dollars (the resolution the CCFS-311 portal publishes — no cents)",
            "basis": "modified-accrual on the CCC Budget and Accounting Manual (BAM) uniform "
                     "chart — the same basis and shape as K-12's SACS. This is NOT the state "
                     "budget page's enacted, budgetary-legal community-college appropriation; "
                     "the two are measured differently, are never reconciled to each other, "
                     "and are never summed.",
            "gate": "WHOLE-DOLLAR, EXACT — no write on failure. The 73 districts' Current "
                    "Expense of Education (ECS 84362) sum to the Chancellor's Office's own "
                    "printed Table VI Statewide total, exactly, to the dollar "
                    f"(${tvi_statewide['ce']:,}). A third, accurately-named resolution tier: "
                    "exact to the dollar — finer than CSU's thousand, coarser than K-12's "
                    "cent. The figures are independently validated off the portal by the "
                    "mandatory CPA audit each district files under Ed Code 84040 (the CCFS-311 "
                    "fund balances equal the audited fund balances).",
            "reproducibility": "AUTO-REPRODUCIBLE. Every source is a public endpoint this "
                    "pipeline fetches without credentials: the CCFS-311 reporting portal "
                    "(a public POST; no login — only the separate filing route is gated), the "
                    "MIS District & College Codes PDF, and the SCFF Exhibit C PDF. Run "
                    "`python3 pipeline/fetch_ccc_data.py --refresh` to rebuild from the live "
                    "sources. This layer has NO manual-cache exception — that exception is "
                    "CSU's alone (its source site is bot-gated); see docs/SCOPE.md.",
            "denominator": "per-FTES uses the APPORTIONMENT funded FTES from the SCFF 2022-23 "
                    "Recalculation Exhibit C — the audited, fiscal-year-aligned workload "
                    "measure that drives the funding formula. It is NOT the CCCCO Data Mart's "
                    "derived count (enrollment hours ÷ 525), which CCCCO itself states is not "
                    "the apportionment methodology. Calbright (California Online CCD) is not "
                    "SCFF-funded and carries no apportionment FTES, so it has no per-FTES figure.",
            "comparabilityNote": "Districts differ in ways that make per-FTES a measure of "
                    "MISSION and STRUCTURE, not performance: some run one college, some run "
                    "nine; some are funded off local property tax rather than state "
                    "apportionment; some carry heavy noncredit and adult-education loads funded "
                    "at different rates. The Ledger shows the figures, flags these differences, "
                    "and never ranks districts.",
            "daggers": {
                "multiCollege": "The district is the fiscal filer, but 23 of the 73 districts "
                    "run more than one college — from Los Angeles CCD's nine to two-college "
                    "districts — while 50 run a single college. Per-district-per-FTES mixes "
                    "very different structures.",
                "basicAid": "Community-supported (“basic aid”) districts are funded off "
                    "local property tax in excess of their state formula entitlement, so state "
                    "funding per FTES is not a meaningful comparison for them, and their total "
                    "spending per FTES runs high for reasons of local wealth, not choice. "
                    "Derived from each district's SCFF property-tax-excess (Exhibit C); the "
                    "count matches the Chancellor's Office's own “Fully Community Supported "
                    "Districts” figure.",
                "noncreditHeavy": "Noncredit and adult-education FTES are funded at different "
                    "rates than credit FTES and are highly concentrated; a district with a "
                    "large noncredit share (here, at least double the statewide average) has a "
                    "per-FTES figure that is not comparable to a credit-dominated district. "
                    "Derived from Exhibit C funded FTES by category.",
                "dangerousCell": "Districts that are BOTH multi-college AND community-supported "
                    "are where per-FTES is most misleading — a high figure that reflects local "
                    "property wealth spread across several colleges, not spending choices. "
                    "This build verifies the multi-college roster against the Chancellor's "
                    "Office MIS codes (reconciling to the official 116 accredited colleges) and "
                    "the community-supported roster against the SCFF Exhibit C: "
                    + ", ".join(dangerous) + ".",
                "auxiliary": "The Current Expense of Education (ECS 84362) already EXCLUDES "
                    "community-service, enterprise (bookstores, cafeterias, parking), and "
                    "capital-outlay objects. Auxiliary organizations and district foundations "
                    "are separate legal entities outside the CCFS-311 General Fund entirely. "
                    "None of them are inside the figures shown here.",
            },
            "overlap": _overlap(),
        },
        "statewide": {
            "ce": tvi_statewide["ce"],
            "instrSal": tvi_statewide["instrSal"],
            "pct50": tvi_statewide["pct50"],
            # THE PUBLISHED CONTROL, NEVER OUR OWN SUM. These used to fall
            # back to ftes_sum / gf_sum — the pipeline's own totals — if the
            # Chancellor's Office control was missing, which is exactly how
            # 1,100,664.62 came to be published where the printed control
            # says 1,100,664.61 (corrected 2026-07-21). The gate above now
            # requires the control to exist, so the fallback can only ever
            # have masked its absence.
            "fundedFtes": round(appn_statewide["fundedFtes"], 2),
            "stateGf": round(appn_statewide["stateGf"]),
            "nDistricts": len(districts),
            "nColleges": n_colleges,
            "communitySupported": basic_n,
            "noncreditThreshold": nc_threshold,
            "statewideNoncreditShare": round(sw_nc_share, 4),
        },
        "districts": districts,
    }
    stamp(payload)
    return payload, tvi_statewide, ce_sum


def main():
    ap = argparse.ArgumentParser(description="Rebuild ccc-data.js")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch of all live sources (ignore the local cache)")
    args = ap.parse_args()

    payload, sw, ce_sum = build(args.refresh)
    d = payload["districts"]
    print(f"FY {FY}: WHOLE-DOLLAR GATE PASSED — {len(d)} districts' Current Expense of "
          f"Education sum to ${ce_sum:,} = the Chancellor's Office printed Statewide total "
          f"(exact, to the dollar).", file=sys.stderr)
    print(f"  {payload['statewide']['nColleges']} accredited colleges · "
          f"{sum(1 for r in d if r['flags']['multiCollege'])} multi-college · "
          f"{payload['statewide']['communitySupported']} community-supported · "
          f"{sum(1 for r in d if r['flags']['noncreditHeavy'])} noncredit-heavy · "
          f"funded FTES {payload['statewide']['fundedFtes']:,.0f}", file=sys.stderr)

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"  payload {len(body) / 1024:.0f} KB", file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_ccc_data.py on "
              f"{date.today().isoformat()} from the Chancellor's Office CCFS-311 public "
              "portal (Table VI, ECS 84362), the SCFF Exhibit C, and the MIS District & "
              "College Codes. Whole dollars; the 73 districts sum exactly to the printed "
              "statewide Current Expense of Education. Auto-reproducible: --refresh. */\n")
    # The previous payload must be read BEFORE the new one overwrites
    # it. This was assigned inside build() and used here, in a
    # different scope, so every --write raised NameError before it
    # could record anything: this layer's change record has never
    # been written by a real refresh.
    prev = revisions.previous_payload(OUT_PATH)
    OUT_PATH.write_text(header + "window.CA_CCC_DATA = " + body + ";\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")

    revisions.record_revision('ccc', prev, payload)


if __name__ == "__main__":
    main()
