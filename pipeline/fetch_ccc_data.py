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
import cache_guard                              # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "ccc"
OUT_PATH = ROOT / "ccc-data.js"
# ── THE FOURTEEN YEARS THE CCFS-311 PORTAL PUBLISHES ─────────────────
# Dropdown values read off the portal's own <option> list, never guessed.
# Value 1 is FY2009-10 and they run consecutively; the layer shipped
# value 14 (FY2022-23) alone until this extension.
PORTAL_YEARS = [(str(i), f"{2008+i}-{str(2009+i)[-2:]}") for i in range(1, 16)]
YEARS = [fy for _, fy in PORTAL_YEARS]
FY = YEARS[-1]                       # the latest year, still the default
FY_PORTAL = PORTAL_YEARS[-1][0]

PORTAL = "https://fiscalportal.cccco.edu/Reports/AnnualReports"
DCC_URL = "https://webdata.cccco.edu/ded/DistrictCollegeCodes.pdf"
EXHIBITC_URL = ("https://www.cccco.edu/-/media/CCCCO-Website/docs/apportionment/"
                "2022-23-R1-Exhibit-C-March-2024.pdf")
# the ONE vintage that live URL publishes — never "the latest year"
EXHIBITC_LIVE_FY = "2022-23"
UA = {"User-Agent": "Mozilla/5.0 (Citizen Ledger data pipeline)", "Referer": PORTAL}

# The one district in Table VI that is absent from the report dropdown
# (its individual FY2022-23 50-Percent-Law report was not certified in
# time to appear as a selectable report); Table VI still carries its
# Current Expense of Education. Its MIS district code:
ALLAN_HANCOCK_CODE = "610"

# ── APPORTIONMENT AVAILABILITY, DECLARED FROM VERIFIED EXISTENCE ──────
#
# cccco.edu SOFT-404s. Every guessed path returns HTTP 200 with an
# identical 40,100-byte HTML page: measured, 90 of 90 nonsense URLs
# "found", including impossible dates (FY2021-22 dated February 2021)
# and corrupt paths (ocs/apportionment/). STATUS IS NEVER CONSULTED.
# Existence here means the fetched bytes start with %PDF- AND the
# response content-type is application/pdf. Nothing in this table was
# extrapolated from a filename pattern.
#
# Located via the Wayback CDX index (the live apportionments index page
# genuinely 404s), then each candidate opened and read.
#
# THE URL IS NOT THE YEAR. The archived file under a 2021-22 path is
# named 202021-Exhibit-C-July-2021-Revision.pdf and its first page
# declares "2020-21 Second Principal" — FY2020-21 data. Every entry
# below is keyed on the fiscal year the PDF states about ITSELF, which
# is the position-guard rule applied to source identity. FY2021-22 has
# no verified Exhibit C and is recorded as absent, not inferred present.
#
# ROUNDS DIFFER and are recorded, because P1, P2 and R1 are different
# stages of the same year's apportionment and are not interchangeable.
# THE ROW LABELS DIFFER BY VINTAGE, and are DECLARED per vintage — never
# matched by a widened alternation that would accept any of them in any
# year. FY2019-20 and FY2020-21 print "State General Entitlement" where
# FY2022-23 and FY2023-24 print "State General Fund Allocation", and
# "Community Supported Districts" where the later vintages print "Fully
# Community Supported Districts".
#
# This is why a fact must never be called not-published merely because a
# regex missed: at these two vintages the state general fund IS printed,
# under another name. Declaring it absent would have published a false
# absence — the mirror of reading an absent figure as zero.
APPORTIONMENT_AVAILABLE = {
    "2018-19": {"round": "P2", "declares": "2018-19 Second Principal Apportionment",
                "gfLabel": "State General Entitlement",
                "csLabel": "Community Supported Districts"},
    "2019-20": {"round": "R1", "declares": "2019-20 Recalculation Apportionment",
                "gfLabel": "State General Entitlement",
                "csLabel": "Community Supported Districts"},
    "2020-21": {"round": "P1", "declares": "2020-21 First Principal",
                "gfLabel": "State General Entitlement",
                "csLabel": "Community Supported Districts"},
    "2021-22": None,   # no Exhibit C verified — facts are not-published
    "2022-23": {"round": "R1", "declares": "2022-23 Recalculation",
                "gfLabel": "State General Fund Allocation",
                "csLabel": "Fully Community Supported Districts"},
    "2023-24": {"round": "P2", "declares": "2023-24 Second Principal",
                "gfLabel": "State General Fund Allocation",
                "csLabel": "Fully Community Supported Districts"},
}
APPORTIONMENT_UNVERIFIED_REASON = (
    "The Chancellor's Office publishes no Exhibit C for this fiscal year "
    "that the Ledger could verify. cccco.edu returns HTTP 200 for paths "
    "that do not exist, so a file is treated as present only when the "
    "bytes it returns are a PDF; none was found for this year."
)


def apportionment_published(fy):
    """Whether a verified Exhibit C exists for this fiscal year.

    Declared, never sniffed, and never inferred from a URL that responds."""
    return APPORTIONMENT_AVAILABLE.get(fy) is not None


# ── WHICH FACTS EACH VINTAGE'S EXHIBIT C SUPPORTS ────────────────────
#
# A verified Exhibit C is not the same as a parseable one, and a
# parseable one does not publish every fact. This table is DECLARED FROM
# MEASUREMENT AGAINST THE PRINTED CONTROL — never from whether a regex
# happened to match, which is the sniff this repo refuses.
#
#   True  → the fact MUST parse for every district AND its district sum
#           MUST reconcile against Exhibit C's own printed statewide
#           control. Failing either stops the build.
#   False → the fact is NOT-PUBLISHED for that year. It is never derived,
#           never defaulted to zero, and no reconciliation is run for it
#           (there is no control to run against). The reason travels with
#           it in APPORTIONMENT_FACT_UNPUBLISHED.
#
# A vintage with no entry here cannot be read at all: adding a year means
# declaring what that year publishes, deliberately.
APPORTIONMENT_FACTS = {
    # FY2019-20 (R1) and FY2020-21 (P1) publish all three, under their own
    # row labels (see APPORTIONMENT_AVAILABLE): "State General Entitlement"
    # and "Community Supported Districts". They were first read as
    # publishing no state general fund at all — that was the regex missing
    # a renamed row, not the source omitting a fact, and declaring it
    # absent would have been a false absence.
    "2019-20": {"fundedFtes": True, "stateGf": True, "communitySupported": False},
    "2020-21": {"fundedFtes": True, "stateGf": True, "communitySupported": True},
    "2022-23": {"fundedFtes": True, "stateGf": True, "communitySupported": True},
    "2023-24": {"fundedFtes": True, "stateGf": True, "communitySupported": False},
}
APPORTIONMENT_FACT_UNPUBLISHED = {
    ("2019-20", "communitySupported"):
        "Exhibit C prints “7 Community Supported Districts” for FY2019-20 "
        "R1, but EIGHT districts on that same document show a property-tax "
        "excess, and it does not say which eight is not among the seven. "
        "Sierra Joint CCD is the marginal case at −$1,558,170, an order of "
        "magnitude smaller than the other seven; its state general "
        "entitlement is mid-range among them, so no rule on this document "
        "separates it. FY2020-21 and FY2022-23, whose derivations tie to "
        "their printed counts exactly, publish this status; this year does "
        "not, rather than ship a roster that contradicts the Chancellor's "
        "Office's own count.",
    ("2023-24", "communitySupported"):
        "Exhibit C prints “7 Fully Community Supported Districts” for "
        "FY2023-24 P2, but EIGHT districts on that same document show a "
        "property-tax excess, and the document does not say which eight is "
        "not among the seven — it refers the reader to a memo it does not "
        "contain (“See memo for additional information regarding revenue "
        "deficit at 2023-24 P2”, alongside a 7.9944% revenue deficit of "
        "$763,789,279, where FY2022-23 printed a 0.0000% deficit and its "
        "eight-district derivation matched exactly). Sierra Joint CCD's "
        "excess falls from $12.5M to $2.0M between the two years and is the "
        "marginal case. Rather than publish a derived roster that "
        "contradicts the Chancellor's Office's own count, the "
        "community-supported status is not published for this year."
}


def apportionment_fact_published(fy, fact):
    """Whether this vintage's Exhibit C supports a given fact.

    Declared per vintage; a year that has not declared its facts is a
    hard failure rather than an optimistic default."""
    facts = APPORTIONMENT_FACTS.get(fy)
    if facts is None:
        raise SystemExit(
            f"CCC {fy}: no APPORTIONMENT_FACTS declaration. A vintage must "
            "declare which apportionment facts its Exhibit C publishes "
            "before it can be read; nothing written.")
    return facts.get(fact, False)


# A vintage whose Exhibit C is verified GENUINE but has not been declared
# READABLE. FY2018-19 is the case: both PDF text extractors corrupt its
# numbers (and pypdf truncates three district names), so reading it needs a
# declared per-vintage extractor plus a bounded repair — see docs/V20. Until
# that is built its apportionment facts are not-published, which is also
# permanently true of two of them.
APPORTIONMENT_UNREADABLE_REASON = {
    "2018-19":
        "The Chancellor's Office publishes an Exhibit C for FY2018-19 and it "
        "is verified genuine, but the Ledger does not yet read it. Both PDF "
        "text extractors insert spurious spaces inside its figures, and one "
        "also truncates three district names, so reading it honestly needs a "
        "declared per-vintage extractor rather than a loosened pattern (see "
        "docs/V20_CCC_2018_19_EXHIBITC_FINDING.md). Two of its apportionment "
        "facts are not published by that document in any case: it prints no "
        "funded-FTES figure and no community-supported count.",
}


def apportionment_absent_reason(fy):
    """Why a whole fiscal year carries no apportionment facts at all.

    Every absence must be explained by a DECLARED reason — an unexplained
    one is a parse failure until shown otherwise."""
    if not apportionment_published(fy):
        return APPORTIONMENT_UNVERIFIED_REASON
    if fy not in APPORTIONMENT_FACTS:
        return APPORTIONMENT_UNREADABLE_REASON.get(fy)
    return None


# THE DISTRICT ROSTER CHANGES INSIDE THE WINDOW, and the change is DECLARED
# rather than tolerated: 72 districts through FY2017-18, 73 from FY2018-19.
# A year whose Table VI does not match its declared count fails the gate, so
# a genuine roster change and a parse failure can never be confused.
DISTRICT_COUNT_BREAK = "2018-19"
DISTRICT_COUNT = {fy: (72 if fy < DISTRICT_COUNT_BREAK else 73)
                  for _, fy in PORTAL_YEARS}


def _gate_apportionment(fy, code2app, app_sw):
    """One year's apportionment reconciliation. Every DECLARED fact must
    tie to Exhibit C's own printed statewide control; every fact declared
    not-published must be genuinely absent. Returns a list of failures."""
    fail = []
    for key, label in (("fundedFtes", "funded FTES"),
                       ("stateGf", "state General Fund")):
        if apportionment_fact_published(fy, key):
            gates.require_target(
                app_sw.get(key), f"{fy} Exhibit C statewide {label}",
                f"the {label} reconciliation cannot run.")
        else:
            leaked = [c for c, a in code2app.items() if key in a]
            if leaked or key in app_sw:
                fail.append(
                    f"{fy}: {label} is declared not-published but "
                    f"{len(leaked)} district records carry it — a fact that is "
                    "not published must not be derived.")
    if apportionment_fact_published(fy, "fundedFtes"):
        s = round(sum(a["fundedFtes"] for a in code2app.values()), 2)
        if abs(s - app_sw["fundedFtes"]) > 0.5:
            fail.append(f"{fy}: funded FTES sum {s} != Exhibit C statewide "
                        f"{app_sw['fundedFtes']}")
    if apportionment_fact_published(fy, "stateGf"):
        s = round(sum(a["stateGf"] for a in code2app.values()))
        if s != round(app_sw["stateGf"]):
            fail.append(f"{fy}: state GF sum {s:,} != Exhibit C statewide "
                        f"{round(app_sw['stateGf']):,}")
    if apportionment_fact_published(fy, "communitySupported"):
        ctrl = app_sw.get("communitySupported")
        if ctrl is None:
            gates.require_target(
                None, f"{fy} Exhibit C 'Community Supported Districts'",
                "the community-supported derivation has no control to tie to.")
        n = sum(1 for a in code2app.values() if a.get("ptaxExcess", 0) < -1)
        if n != ctrl:
            fail.append(f"{fy}: {n} community-supported districts derived but "
                        f"Exhibit C states {ctrl}")
    else:
        if (fy, "communitySupported") not in APPORTIONMENT_FACT_UNPUBLISHED:
            fail.append(f"{fy}: community-supported is declared not-published "
                        "with no stated reason — an unexplained silence is not "
                        "a declaration.")
        leaked = [c for c, a in code2app.items() if "ptaxExcess" in a]
        if leaked:
            fail.append(f"{fy}: community-supported is declared not-published "
                        f"but {len(leaked)} districts carry its input.")
    return fail

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
    # through the guard: the cached sources are read-only, so a stray
    # write cannot reach them and a refresh unlocks only its own file
    return cache_guard.write_cached(path, blob, binary=binary)


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


def fetch_table_vi(refresh, portal_val=None, fy=None):
    """Table VI = Summary of Current Expense of Education (ECS 84362):
    per-district CE + instructional salaries + 50%-law percent, and a
    printed statewide total row. The Run button is disabled until a
    fiscal-year autopostback fires, so this scripts the handshake.

    Parameterised by portal dropdown value, one cache file per year."""
    portal_val = portal_val or FY_PORTAL
    fy = fy or FY
    def live():
        html = _get(PORTAL)
        tk = _tokens(html)
        s1 = _post(tk, {"__EVENTTARGET": "ctl00$MainContent$FiscalYearDropdown",
                        "ctl00$MainContent$FiscalYearDropdown": portal_val,
                        "ctl00$MainContent$StatewideReportDropdown": "40"})
        tk2 = _tokens(s1)
        run = _post(tk2, {"ctl00$MainContent$FiscalYearDropdown": portal_val,
                          "ctl00$MainContent$StatewideReportDropdown": "40",
                          "ctl00$MainContent$RunStatewideReport": "View Report"})
        return _plain(run)
    cache_name = ("tablevi-fy2223.txt" if fy == "2022-23"
                  else f"tablevi-{fy}.txt")
    text = html.unescape(_cached(cache_name, live, refresh))
    anchor = "Percent of Instructors' Salaries to Current Expense of Education"
    i = text.find(anchor)
    if i < 0:
        raise SystemExit(f"CCC {fy}: Table VI did not render (portal handshake "
                         "failed) — nothing written")
    seg = text[i + len(anchor):]
    ms = re.search(r"Statewide\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)%", seg)
    if not ms:
        raise SystemExit(f"CCC {fy}: Table VI statewide total row not found "
                         "— nothing written")
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
def fetch_apportionment(refresh, fy=None):
    """Parse one year's Exhibit C.

    THE PDF MUST DECLARE ITS OWN FISCAL YEAR. A file archived under a
    2021-22 path is named 202021-Exhibit-C-July-2021-Revision.pdf and its
    first page reads "2020-21 Second Principal" — FY2020-21 data. So the
    year is taken from the document, never from the path, and a document
    that does not say what it is is refused."""
    import pypdf
    fy = fy or FY
    # EXHIBITC_URL serves ONE specific vintage — the FY2022-23 Recalculation.
    # This branch used to trigger on `fy == FY`, i.e. "whatever the latest
    # year happens to be", so extending the window to FY2023-24 silently
    # pointed the newest year at the 2022-23 document. The identity guard
    # below caught it, which is what it is for; the live URL is now keyed to
    # the year it actually publishes.
    if fy == EXHIBITC_LIVE_FY:
        blob = _cached("apportionment-2022-23-R1-ExhibitC.pdf",
                       lambda: _get(EXHIBITC_URL, binary=True), refresh, binary=True)
        (CACHE / "_exc_tmp.pdf").write_bytes(blob)
        src = CACHE / "_exc_tmp.pdf"
    else:
        src = CACHE / "exhibitc" / f"exhibitc-{fy}.pdf"
        if not src.exists():
            raise SystemExit(
                f"CCC {fy}: no verified Exhibit C on disk. Availability is "
                "declared in APPORTIONMENT_AVAILABLE and files are accepted "
                "only on %PDF- magic bytes; nothing written.")
    r = pypdf.PdfReader(src)

    # POSITION GUARD ON SOURCE IDENTITY: the document must declare itself
    # as the year it is being read as, in ITS OWN MASTHEAD — the block
    # "California Community Colleges / <FY> <Round> / <Entity> / Exhibit C
    # - Page 1". The expected string is DECLARED per vintage in
    # APPORTIONMENT_AVAILABLE[fy]["declares"], so this is an exact match
    # against a known form, not a loosened year-anywhere search.
    #
    # It is matched over the WHOLE first page, not its first 400
    # characters. FY2023-24 puts a summary table ahead of the masthead in
    # extraction order, so its declaration sits at character ~6,700; the
    # old 400-character window refused a document that does identify
    # itself. The window was the defect, not the source.
    vint = APPORTIONMENT_AVAILABLE.get(fy) or {}
    declares = vint.get("declares")
    if not declares:
        raise SystemExit(
            f"CCC {fy}: no declared Exhibit C masthead for this vintage. "
            "Availability and the string the document must declare are "
            "declared in APPORTIONMENT_AVAILABLE; nothing written.")
    page0 = r.pages[0].extract_text() or ""
    if declares not in page0:
        head = next((ln for ln in page0.splitlines() if ln.strip()), "")
        raise SystemExit(
            f"CCC {fy}: this Exhibit C does not declare itself as "
            f"{declares!r} — its first page begins {head[:60]!r}. The URL is "
            "not the year; nothing written.")

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
        # ONLY THE FACTS THIS VINTAGE DECLARES ARE READ. A fact declared
        # unpublished is left ABSENT — never read, never defaulted to 0.0.
        # The old `else 0.0` was the absent-reads-as-zero defect in the
        # place it does most damage: a vintage that prints no State
        # General Fund row would have summed 72 confident zeros and
        # reconciled them against a control that does not exist.
        want_ftes = apportionment_fact_published(fy, "fundedFtes")
        want_gf = apportionment_fact_published(fy, "stateGf")
        want_cs = apportionment_fact_published(fy, "communitySupported")
        # patterns built from the DECLARED per-vintage labels, so each
        # vintage matches its own wording exactly and no other's
        # The value may be DISPLACED from its label by an intervening line
        # ("State General Entitlement\nExhibit A \n58,288,934", FY2019-20
        # Glendale) and may be NEGATIVE in parentheses ("(1,248,742)",
        # FY2020-21 Coast — a community-supported district's entitlement can
        # be negative). Both are real layouts, so the gap is allowed but
        # BOUNDED, and no digit may appear inside it: the first number after
        # the declared label is the figure, and the reconciliation against
        # the printed statewide control is what proves it is the right one.
        gf_pat = re.escape(vint["gfLabel"]) + r"[^\d(]{0,30}(\(?[\d,]{4,}\)?)"
        cs_pat = r"(\d+)\s+" + re.escape(vint["csLabel"])
        if "Statewide" in name:  # statewide summary page → reconciliation totals
            if want_ftes:
                mm = re.search(r"Funded FTES:\s+([\d,]+\.\d+)", t)
                if mm:
                    statewide["fundedFtes"] = num(mm.group(1))
            if want_gf:
                mm = re.search(gf_pat, t)
                if mm:
                    statewide["stateGf"] = num(mm.group(1))
            if want_cs:
                mm = re.search(cs_pat, t)
                if mm:
                    statewide["communitySupported"] = int(mm.group(1))
            continue
        d = {}
        # ptaxExcess exists only to derive community-supported status, so
        # it is read only where that status is publishable.
        specs = [s for s in (
            ("fundedFtes", r"Funded FTES:\s+([\d,]+\.\d+)") if want_ftes else None,
            ("stateGf", gf_pat) if want_gf else None,
            ("ptaxExcess", r"Less Property Tax Excess\s+(\(?[\d,]*\)?|-)") if want_cs else None,
        ) if s is not None]
        for key, pat in specs:
            mm = re.search(pat, t)
            if not mm:
                # A DECLARED fact that does not parse is a parse failure,
                # not a zero: the declaration says this vintage prints it.
                raise SystemExit(
                    f"CCC {fy}: {name} declares {key!r} as published for this "
                    "vintage but the row did not parse. Either the "
                    "declaration is wrong or the parser is; nothing written.")
            d[key] = num(mm.group(1))
        # noncredit share from the Section Ia funded-FTES-by-category block
        sec = t[t.find("Section Ia"):]
        cats = {}
        for cat in ("CDCP", "Noncredit"):
            mm = re.search(r"(?:^|\n)" + re.escape(cat) + r"\s+([\d,.\s()\-]+?)(?:\n[A-Z]|\nTotal)", sec)
            if mm:
                cats[cat] = lastnum(mm.group(1))
        nc = cats.get("Noncredit", 0) + cats.get("CDCP", 0)
        # A missing denominator is not a measurement of zero noncredit —
        # and a vintage that does not publish funded FTES has no
        # denominator at all, so the share is absent rather than zero.
        denom = d.get("fundedFtes")
        d["noncreditShare"] = round(nc / denom, 4) if denom else None
        appn[name] = d
    (CACHE / "_exc_tmp.pdf").unlink(missing_ok=True)
    return appn, statewide


def verify_apportionment_vintage(fy, refresh=False):
    """Parse ONE vintage's Exhibit C and run its reconciliations.

    This is the per-vintage parser's own gate, callable without touching
    the payload, so a vintage can be proven readable before any year is
    wired in. Returns a report; raises SystemExit on any failure.

    Every fact the vintage DECLARES must parse for every district and its
    district sum must tie to Exhibit C's own printed statewide control.
    Every fact the vintage declares NOT-published must be absent from
    every record — the check that stops a "not-published" declaration
    from coexisting with a quietly derived figure — and must carry a
    stated reason."""
    appn, statewide = fetch_apportionment(refresh, fy)
    rep = {"fy": fy, "round": APPORTIONMENT_AVAILABLE[fy]["round"],
           "declares": APPORTIONMENT_AVAILABLE[fy]["declares"],
           "districts": len(appn), "published": {}, "notPublished": {}}
    gates.require_rows(len(appn), 70, f"CCC {fy} Exhibit C district pages")
    fail = []
    for key, label, tol in (("fundedFtes", "funded FTES", 0.5),
                            ("stateGf", "state General Fund", 0.5)):
        if apportionment_fact_published(fy, key):
            gates.require_target(
                statewide.get(key), f"CCC {fy} Exhibit C statewide {label}",
                f"the {label} reconciliation cannot run.")
            missing = [n for n, a in appn.items() if key not in a]
            if missing:
                fail.append(f"{len(missing)} districts lack {label}, which this "
                            f"vintage declares published")
            s = sum(a[key] for a in appn.values() if key in a)
            resid = s - statewide[key]
            if abs(resid) > tol:
                fail.append(f"{label} sum {s:,.2f} != statewide "
                            f"{statewide[key]:,.2f} (residual {resid:+,.2f})")
            rep["published"][key] = {"sum": round(s, 2),
                                     "control": round(statewide[key], 2),
                                     "residual": round(resid, 2)}
        else:
            leaked = [n for n, a in appn.items() if key in a]
            if leaked:
                fail.append(f"{label} is declared not-published for {fy} but "
                            f"{len(leaked)} districts carry it")
            rep["notPublished"][key] = APPORTIONMENT_FACT_UNPUBLISHED.get((fy, key), "")
    # community-supported: derived from property-tax excess, validated
    # against the printed count — or not derived at all
    if apportionment_fact_published(fy, "communitySupported"):
        gates.require_target(
            statewide.get("communitySupported"),
            f"CCC {fy} Exhibit C 'Fully Community Supported Districts'",
            "the community-supported derivation has no control to tie to.")
        n = sum(1 for a in appn.values() if a.get("ptaxExcess", 0) < -1)
        if n != statewide["communitySupported"]:
            fail.append(f"{n} community-supported districts derived but Exhibit C "
                        f"states {statewide['communitySupported']}")
        rep["published"]["communitySupported"] = {
            "derived": n, "control": statewide["communitySupported"]}
    else:
        reason = APPORTIONMENT_FACT_UNPUBLISHED.get((fy, "communitySupported"))
        if not reason:
            fail.append(f"community-supported is declared not-published for {fy} "
                        "with no stated reason")
        leaked = [n for n, a in appn.items() if "ptaxExcess" in a]
        if leaked:
            fail.append(f"community-supported is declared not-published for {fy} "
                        f"but {len(leaked)} districts carry its input")
        rep["notPublished"]["communitySupported"] = reason or ""
    if fail:
        for f in fail[:12]:
            print(f"  CCC {fy} EXHIBIT C GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"CCC {fy}: {len(fail)} Exhibit C gate failure(s) — "
                         "nothing written")
    return rep


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
    # THE COLLEGE ROSTER IS CURRENT-VINTAGE ONLY. MIS publishes today's
    # District & College Codes; it carries no history. So `colleges`,
    # `nColleges` and `multiCollege` stay at the ENTITY, never inside a
    # year — putting them in `years[fy]` would assert today's roster about
    # 2009-10, which is precisely the claim the source cannot support.
    roster = fetch_roster(refresh)
    name2code = {v: k for k, v in code2name.items()}
    canon_n = {_norm(nm): code for nm, code in name2code.items()}

    fail = []
    years_data = {}

    for pv, fy in PORTAL_YEARS:
        tvi, tvi_sw = fetch_table_vi(refresh, pv, fy)

        # ── structural pre-gate: every name must resolve to a portal code
        tvi_codes = {name2code.get(nm) for nm in tvi}
        if None in tvi_codes:
            fail.append(f"{fy}: Table VI has a district name not in the portal "
                        "dropdown: "
                        + ", ".join(nm for nm in tvi if nm not in name2code))
            tvi_codes.discard(None)
        # THE ROSTER SIZE IS A DECLARED STRUCTURAL BREAK, not a constant.
        want = DISTRICT_COUNT.get(fy)
        if want is None:
            fail.append(f"{fy}: no declared district count. The 72->73 break is "
                        "declared in DISTRICT_COUNT; a year with no declaration "
                        "is not read.")
        else:
            bad = gates.check_exact(len(tvi), want, f"{fy} Table VI district roster")
            if bad:
                fail.append(bad)
        missing_roster = tvi_codes - set(roster)
        if missing_roster:
            fail.append(f"{fy}: districts with no college roster: "
                        f"{sorted(missing_roster)}")

        # ── THE GATE: per-district CE == printed statewide, to the dollar
        gates.require_target(tvi_sw, f"{fy} Table VI printed statewide totals",
                             "the whole-dollar gate cannot run.")
        gates.require_rows(len(tvi), 70, f"{fy} Table VI districts")
        ce_sum = sum(v["ce"] for v in tvi.values())
        if ce_sum != tvi_sw["ce"]:
            fail.append(f"WHOLE-DOLLAR GATE FAILED for {fy}: {len(tvi)} districts "
                        f"sum to {ce_sum:,} but Table VI's printed Statewide total "
                        f"is {tvi_sw['ce']:,} "
                        f"(residual {ce_sum - tvi_sw['ce']:+,})")

        # ── apportionment: ONLY where the vintage declares its facts ────
        # A year with no verified Exhibit C, or one whose Exhibit C has not
        # been declared readable (FY2018-19 — see docs/V20), contributes NO
        # apportionment facts at all. They are absent, never zero.
        code2app, app_sw = {}, {}
        if apportionment_published(fy) and fy in APPORTIONMENT_FACTS:
            appn, app_sw = fetch_apportionment(refresh, fy)
            app2code = {}
            for fn in appn:
                k = _norm(fn)
                app2code[fn] = canon_n.get(APPN_ALIAS.get(k, k))
            unmatched = [fn for fn, c in app2code.items() if c is None]
            if unmatched:
                fail.append(f"{fy}: apportionment districts not matched to a "
                            f"district code: {unmatched}")
            code2app = {c: appn[fn] for fn, c in app2code.items() if c}
            gates.require_rows(len(code2app), 70,
                               f"{fy} apportionment districts matched to a code")
            fail.extend(_gate_apportionment(fy, code2app, app_sw))

        # statewide noncredit share → the data-derived "noncredit-heavy"
        # threshold (2x statewide). A year with no apportionment has no
        # threshold to derive, and the flag is not-published for that year.
        nc_threshold = None
        nc_share = None
        ftes_sum = None
        if code2app and apportionment_fact_published(fy, "fundedFtes"):
            ftes_sum = round(sum(a["fundedFtes"] for a in code2app.values()), 2)
            if ftes_sum:
                nc_num = sum((code2app[c].get("noncreditShare") or 0)
                             * code2app[c]["fundedFtes"] for c in code2app)
                nc_share = round(nc_num / ftes_sum, 4)
                nc_threshold = round(2 * (nc_num / ftes_sum), 4)

        years_data[fy] = {
            "tvi": tvi, "tviStatewide": tvi_sw, "ceSum": ce_sum,
            "code2app": code2app, "appStatewide": app_sw,
            "ncThreshold": nc_threshold, "ncShare": nc_share, "ftesSum": ftes_sum,
            "round": (APPORTIONMENT_AVAILABLE.get(fy) or {}).get("round"),
        }

    n_colleges = sum(len(roster[c]["colleges"]) for c in roster)
    if n_colleges != 116:
        fail.append(f"{n_colleges} accredited colleges across districts (expected 116)")

    if fail:
        for f in fail[:12]:
            print("  CCC GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"{len(fail)} gate failure(s) — nothing written")

    # ── assemble districts, keyed on the source's own code ───────────
    #
    # MULTI-YEAR SHAPE, matching cities, counties, K-12 and UC: identity at
    # the entity, everything that varies by year inside `years`, keyed by
    # fiscal-year label. A district that does not exist in a year simply
    # has no entry for it — absence, never a zero.
    districts = {}
    for pv, fy in PORTAL_YEARS:
        yd = years_data[fy]
        for nm, cev in yd["tvi"].items():
            code = name2code[nm]
            rec = districts.get(code)
            if rec is None:
                rec = districts[code] = {
                    "name": nm, "code": code,
                    "colleges": roster[code]["colleges"],
                    "nColleges": len(roster[code]["colleges"]),
                    "years": {},
                }
            # the display name follows the newest year the district appears
            # in; identity is the code, so a rename is not a new district
            rec["name"] = nm
            yr = {"ce": cev["ce"], "instrSal": cev["instrSal"], "pct50": cev["pct50"]}
            a = yd["code2app"].get(code)
            if a:
                # ONLY THE FACTS THIS VINTAGE PUBLISHES ARE EMITTED.
                if "fundedFtes" in a:
                    yr["fundedFtes"] = round(a["fundedFtes"], 2)
                    if a["fundedFtes"]:
                        yr["perFtes"] = round(cev["ce"] / a["fundedFtes"])
                if "stateGf" in a:
                    yr["stateGf"] = round(a["stateGf"])
                if a.get("noncreditShare") is not None:
                    yr["noncreditShare"] = a["noncreditShare"]
                if "ptaxExcess" in a:
                    yr["basicAidStatus"] = ("basic-aid" if a["ptaxExcess"] < -1
                                            else "state-funded")
                else:
                    yr["basicAidStatus"] = "not-published"
                    yr["basicAidUnpublishedReason"] = \
                        APPORTIONMENT_FACT_UNPUBLISHED.get(
                            (fy, "communitySupported"), "")
            else:
                # ABSENCE MARKS ABSENCE. A number that is not known is
                # ABSENT (absence yields NaN, not a confident 0); a boolean
                # that is not known is a THREE-VALUED STATUS, because false
                # is a real answer with no room left to mean "unknown".
                # The reason travels WITH the record — a district-level one
                # where the district has none, a year-level one where the
                # whole vintage has none.
                reason = (NO_APPORTIONMENT.get(code)
                          if yd["code2app"] else apportionment_absent_reason(fy))
                if not reason:
                    raise SystemExit(
                        f"CCC {fy}: {nm} ({code}) has no apportionment record "
                        "and no declared reason. An unexplained absence is a "
                        "parse failure until shown otherwise; declare it "
                        "deliberately. Nothing written.")
                yr["basicAidStatus"] = "not-published"
                yr["noApportionmentReason"] = reason
            yr["flags"] = {
                "basicAidStatus": yr["basicAidStatus"],
                "noncreditHeavyStatus": (
                    "not-published" if "noncreditShare" not in yr
                    or yd["ncThreshold"] is None
                    else "noncredit-heavy"
                    if yr["noncreditShare"] >= yd["ncThreshold"]
                    else "not-noncredit-heavy"),
                "noApportionment": a is None,
            }
            rec["years"][fy] = yr
    districts = sorted(districts.values(), key=lambda r: r["name"])
    # multiCollege is a CURRENT-VINTAGE roster fact and lives at the entity,
    # never inside a year (see the roster note above).
    for rec in districts:
        rec["multiCollege"] = rec["nColleges"] > 1

    dangerous = sorted(
        r["name"] for r in districts
        if r["multiCollege"]
        and r["years"].get(FY, {}).get("basicAidStatus") == "basic-aid")

    # ── statewide, per year ──────────────────────────────────────────
    # THE PUBLISHED CONTROL, NEVER OUR OWN SUM. These used to fall back to
    # the pipeline's own totals if the Chancellor's Office control was
    # missing, which is how 1,100,664.62 came to be published where the
    # printed control says 1,100,664.61 (corrected 2026-07-21). A control
    # that does not exist means the fact is absent, not that our sum
    # stands in for it.
    statewide = {}
    for pv, fy in PORTAL_YEARS:
        yd = years_data[fy]
        sw = {
            "ce": yd["tviStatewide"]["ce"],
            "instrSal": yd["tviStatewide"]["instrSal"],
            "pct50": yd["tviStatewide"]["pct50"],
            "nDistricts": sum(1 for r in districts if fy in r["years"]),
            "noncreditThreshold": yd["ncThreshold"],
            "statewideNoncreditShare": yd["ncShare"],
        }
        app_sw = yd["appStatewide"]
        if apportionment_published(fy) and fy in APPORTIONMENT_FACTS:
            if apportionment_fact_published(fy, "fundedFtes") and "fundedFtes" in app_sw:
                sw["fundedFtes"] = round(app_sw["fundedFtes"], 2)
            if apportionment_fact_published(fy, "stateGf") and "stateGf" in app_sw:
                sw["stateGf"] = round(app_sw["stateGf"])
            if apportionment_fact_published(fy, "communitySupported"):
                sw["communitySupported"] = app_sw.get("communitySupported")
            else:
                sw["communitySupportedStatus"] = "not-published"
                sw["communitySupportedReason"] = APPORTIONMENT_FACT_UNPUBLISHED.get(
                    (fy, "communitySupported"), "")
        else:
            sw["apportionmentStatus"] = "not-published"
            sw["apportionmentReason"] = apportionment_absent_reason(fy) or ""
        # the round this year's apportionment facts were assembled at
        if yd["round"] and fy in APPORTIONMENT_FACTS:
            sw["apportionmentRound"] = yd["round"]
        statewide[fy] = sw

    payload = {
        # the year axis every multi-year layer publishes
        "years": YEARS,
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
                    f"(FY{FY}: ${years_data[FY]['tviStatewide']['ce']:,}). A third, accurately-named resolution tier: "
                    "exact to the dollar — finer than CSU's thousand, coarser than K-12's "
                    "cent. The figures are independently validated off the portal by the "
                    "mandatory CPA audit each district files under Ed Code 84040 (the CCFS-311 "
                    "fund balances equal the audited fund balances).",
            # ── comparability facts the PAGE renders on the record ──
            # These are not method-note footnotes: the page shows each one
            # on the record for the year it is true of, the same treatment
            # as UC's DOE-assembly break.
            "roundsDiffer": "P1, P2 and R1 are different STAGES of the same "
                "year's apportionment — First Principal, Second Principal and "
                "Recalculation — computed at different points from different "
                "information, and they are not interchangeable. This layer "
                "publishes apportionment figures for four fiscal years and "
                "they were not all assembled at the same stage, so a "
                "comparison across them compares a year measured early "
                "against a year measured late. The round is recorded on every "
                "year that has one.",
            "districtCountBreak": "The Chancellor's Office reported 72 "
                "districts through FY2017-18 and 73 from FY2018-19, when "
                "Calbright — the state's online community college, created "
                "by statute in 2018 — first filed. That is a real change in "
                "the number of districts inside this window, not a parse "
                "difference: the count is declared per year, and a year whose "
                "Table VI does not match its declared count fails the gate "
                "rather than being accepted as a roster change. A statewide "
                "total spanning that boundary compares differently-sized "
                "systems.",
            "rosterScope": "The college roster — which colleges each district "
                "runs, and therefore the multi-college flag — comes from the "
                "Chancellor's Office MIS District & College Codes, which "
                "publishes TODAY's list and carries no history. It is "
                "recorded once per district, never inside a fiscal year, "
                "because stating it under FY2009-10 would assert a current "
                "roster about a year it was not measured in. The 116-college "
                "reconciliation is likewise a statement about the current "
                "roster only.",
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
        "statewide": statewide,
        "districts": districts,
    }
    stamp(payload)
    return payload, years_data[FY]["tviStatewide"], years_data[FY]["ceSum"]


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
    sw = payload["statewide"][FY]
    fl = [r["years"][FY]["flags"] for r in d if FY in r["years"]]
    print(f"  {sum(r['nColleges'] for r in d)} accredited colleges · "
          f"{sum(1 for r in d if r['multiCollege'])} multi-college "
          "(current roster; not asserted about earlier years) · "
          f"{sw.get('communitySupported', 'not-published')} community-supported · "
          f"{sum(1 for f in fl if f['noncreditHeavyStatus'] == 'noncredit-heavy')} noncredit-heavy · "
          f"funded FTES {sw.get('fundedFtes', float('nan')):,.0f}", file=sys.stderr)
    # per-year coverage, so a year that ships without apportionment is
    # visible on every run rather than only in the payload
    print(f"  {len(payload['years'])} fiscal years {payload['years'][0]}..{payload['years'][-1]}"
          f" · apportionment in "
          + ", ".join(f"{fy}({payload['statewide'][fy].get('apportionmentRound','?')})"
                      for fy in payload["years"]
                      if "apportionmentStatus" not in payload["statewide"][fy]),
          file=sys.stderr)

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
