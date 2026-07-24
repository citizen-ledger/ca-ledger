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
PORTAL_YEARS = [(str(i), f"{2008+i}-{str(2009+i)[-2:]}") for i in range(1, 15)]
YEARS = [fy for _, fy in PORTAL_YEARS]
FY = YEARS[-1]                       # the latest year, still the default
FY_PORTAL = PORTAL_YEARS[-1][0]

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
APPORTIONMENT_AVAILABLE = {
    "2018-19": {"round": "P2", "declares": "2018-19 Second Principal Apportionment"},
    "2019-20": {"round": "R1", "declares": "2019-20 Recalculation Apportionment"},
    "2020-21": {"round": "P1", "declares": "2020-21 First Principal"},
    "2021-22": None,   # no Exhibit C verified — facts are not-published
    "2022-23": {"round": "R1", "declares": "2022-23 Recalculation"},
    "2023-24": {"round": "P2", "declares": "2023-24 Second Principal"},
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
    "2022-23": {"fundedFtes": True, "stateGf": True, "communitySupported": True},
    "2023-24": {"fundedFtes": True, "stateGf": True, "communitySupported": False},
}
APPORTIONMENT_FACT_UNPUBLISHED = {
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
    if fy == FY:
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
    declares = (APPORTIONMENT_AVAILABLE.get(fy) or {}).get("declares")
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
        if "Statewide" in name:  # statewide summary page → reconciliation totals
            if want_ftes:
                mm = re.search(r"Funded FTES:\s+([\d,]+\.\d+)", t)
                if mm:
                    statewide["fundedFtes"] = num(mm.group(1))
            if want_gf:
                mm = re.search(r"State General Fund Allocation\s+([\d,]+)\s*\n", t)
                if mm:
                    statewide["stateGf"] = num(mm.group(1))
            if want_cs:
                mm = re.search(r"(\d+)\s+Fully Community Supported Districts", t)
                if mm:
                    statewide["communitySupported"] = int(mm.group(1))
            continue
        d = {}
        # ptaxExcess exists only to derive community-supported status, so
        # it is read only where that status is publishable.
        specs = [s for s in (
            ("fundedFtes", r"Funded FTES:\s+([\d,]+\.\d+)") if want_ftes else None,
            ("stateGf", r"State General Fund Allocation\s+([\d,]+)\s*\n") if want_gf else None,
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
    bad = gates.check_exact(len(tvi), 73, "Table VI district roster")
    if bad:
        fail.append(bad)
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
    # EACH DECLARED FACT MUST RECONCILE; each undeclared fact must be
    # genuinely ABSENT. The second half matters as much as the first: it
    # is what stops a "not-published" declaration from quietly coexisting
    # with a derived figure nobody reconciled.
    for key, label in (("fundedFtes", "funded FTES"),
                       ("stateGf", "state General Fund")):
        if apportionment_fact_published(FY, key):
            gates.require_target(
                appn_statewide.get(key), f"Exhibit C statewide {label}",
                f"the {label} reconciliation cannot run.")
        else:
            leaked = [c for c, a in code2app.items() if key in a]
            if leaked or key in appn_statewide:
                fail.append(
                    f"{label} is declared not-published for FY {FY} but "
                    f"{len(leaked)} district records carry it — a fact that is "
                    "not published must not be derived.")
    ftes_sum = None
    if apportionment_fact_published(FY, "fundedFtes"):
        ftes_sum = round(sum(a["fundedFtes"] for a in code2app.values()), 2)
        if abs(ftes_sum - appn_statewide["fundedFtes"]) > 0.5:
            fail.append(f"funded FTES sum {ftes_sum} != Exhibit C statewide "
                        f"{appn_statewide['fundedFtes']}")
    if apportionment_fact_published(FY, "stateGf"):
        gf_sum = round(sum(a["stateGf"] for a in code2app.values()))
        if gf_sum != round(appn_statewide["stateGf"]):
            fail.append(f"state GF sum {gf_sum:,} != Exhibit C statewide "
                        f"{round(appn_statewide['stateGf']):,}")
    basic_n = (sum(1 for a in code2app.values() if a["ptaxExcess"] < -1)
               if apportionment_fact_published(FY, "communitySupported") else None)
    # The control must EXIST, and a control of ZERO is a real published
    # value — not a reason to skip the comparison. Truthiness conflated
    # the two: a year in which the Chancellor's Office legitimately
    # prints zero community-supported districts would have disabled the
    # check entirely, and a missing control did so silently.
    if apportionment_fact_published(FY, "communitySupported"):
        cs_control = appn_statewide.get("communitySupported")
        if cs_control is None:
            gates.require_target(
                None, "Exhibit C statewide 'Fully Community Supported Districts'",
                "meta.daggers.basicAid claims this count matches the "
                "Chancellor's Office figure, so the claim cannot be made.")
        if basic_n != cs_control:
            fail.append(f"{basic_n} community-supported districts derived but Exhibit C "
                        f"states {appn_statewide['communitySupported']}")
    else:
        # DECLARED NOT-PUBLISHED. The reason must exist — an undeclared
        # silence is indistinguishable from an oversight — and no
        # community-supported status may have been derived anyway.
        if (FY, "communitySupported") not in APPORTIONMENT_FACT_UNPUBLISHED:
            fail.append(
                f"community-supported status is declared not-published for FY "
                f"{FY} with no reason in APPORTIONMENT_FACT_UNPUBLISHED — an "
                "unexplained silence is not a declaration.")
        leaked = [c for c, a in code2app.items() if "ptaxExcess" in a]
        if leaked:
            fail.append(
                f"community-supported status is declared not-published for FY "
                f"{FY} but {len(leaked)} districts carry a property-tax-excess "
                "figure it would be derived from.")

    if fail:
        for f in fail[:12]:
            print("  CCC GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"FY {FY}: {len(fail)} gate failure(s) — nothing written")

    # statewide noncredit share → the data-derived "noncredit-heavy" threshold (2× statewide)
    # THE THRESHOLD IS DERIVED FROM THE APPORTIONMENT SET, so a year with
    # no apportionment has no threshold to derive — and dividing by an
    # empty set's FTES is a ZeroDivisionError, not a zero. The flag then
    # becomes not-published for every district, which is the truth: it is
    # 2x a statewide share that was never measured.
    if code2app and ftes_sum:
        sw_nc_num = sum((code2app[c]["noncreditShare"]) * code2app[c]["fundedFtes"]
                        for c in code2app)
        sw_nc_share = sw_nc_num / ftes_sum
        nc_threshold = round(2 * sw_nc_share, 4)
    else:
        sw_nc_share = None
        nc_threshold = None

    # ── assemble districts ───────────────────────────────────────────
    districts = []
    for nm, cev in tvi.items():
        code = name2code[nm]
        colleges = roster[code]["colleges"]
        a = code2app.get(code)
        # MULTI-YEAR SHAPE, matching cities, counties and K-12: identity
        # at the entity, everything that varies by year inside `years`,
        # keyed by fiscal-year label. A reader moving between layers meets
        # the same structure, and a maintainer meets one convention.
        #
        # `colleges`/`nColleges` stay at the entity for now because the
        # roster source (DistrictCollegeCodes.pdf) is current-vintage only
        # and is not year-scoped yet — that is the next PR, and putting it
        # here would assert a current roster about older years.
        rec = {
            "name": nm, "code": code,
            "colleges": colleges, "nColleges": len(colleges),
            "years": {},
        }
        yr = {"ce": cev["ce"], "instrSal": cev["instrSal"], "pct50": cev["pct50"]}
        if a:
            # ONLY THE FACTS THIS VINTAGE PUBLISHES ARE EMITTED. A fact the
            # vintage does not publish is ABSENT from the record (a number
            # that is absent yields NaN, never a confident 0), and a status
            # that cannot be derived is the three-valued "not-published"
            # rather than a bare false.
            if "fundedFtes" in a:
                yr["fundedFtes"] = round(a["fundedFtes"], 2)
                # a rate with no denominator is not published, rather than null
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
                yr["basicAidUnpublishedReason"] = APPORTIONMENT_FACT_UNPUBLISHED.get(
                    (FY, "communitySupported"), "")
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
            # THE CONFORMING ENCODING (see fetch_school_data.LCFF_PUBLISHES).
            # These were null. null is falsy and coerces to 0 in a sum, so
            # it is the shape the rule exists to forbid: a consumer doing
            # `if (d.basicAid)` or `total += d.stateGf` gets a confident
            # wrong answer. A number that is not known is ABSENT — absence
            # yields NaN, which is not a valid answer. A boolean that is
            # not known is a THREE-VALUED STATUS, because false is a valid
            # answer and has no room left to mean "unknown".
            yr["basicAidStatus"] = "not-published"
            yr["noApportionmentReason"] = reason
        yr["flags"] = {
            "multiCollege": rec["nColleges"] > 1,
            "basicAidStatus": yr["basicAidStatus"],
            "noncreditHeavyStatus": (
                "not-published" if "noncreditShare" not in yr
                or nc_threshold is None
                else "noncredit-heavy" if yr["noncreditShare"] >= nc_threshold
                else "not-noncredit-heavy"),
            "noApportionment": a is None,
        }
        rec["years"][FY] = yr
        districts.append(rec)
    districts.sort(key=lambda r: r["name"])

    dangerous = sorted(r["name"] for r in districts
                       if r["years"][FY]["flags"]["multiCollege"]
                       and r["years"][FY]["flags"]["basicAidStatus"] == "basic-aid")

    payload = {
        # the year axis every multi-year layer publishes
        "years": [FY],
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
        "statewide": {FY: {
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
            "statewideNoncreditShare": (round(sw_nc_share, 4)
                                            if sw_nc_share is not None else None),
        }},
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
    sw = payload["statewide"][FY]
    fl = [r["years"][FY]["flags"] for r in d]
    print(f"  {sw['nColleges']} accredited colleges · "
          f"{sum(1 for f in fl if f['multiCollege'])} multi-college · "
          f"{sw['communitySupported']} community-supported · "
          f"{sum(1 for f in fl if f['noncreditHeavyStatus'] == 'noncredit-heavy')} noncredit-heavy · "
          f"funded FTES {sw['fundedFtes']:,.0f}", file=sys.stderr)

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
