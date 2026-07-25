#!/usr/bin/env python3
"""
Schedule 8 revenue extraction for Citizen Ledger (V21).

Extracts prior-year ACTUAL REVENUES from the Department of Finance's
Schedule 8 — "Comparative Statement of Revenues" — published as a PDF
in every budget publication, alongside the Schedule 9 expenditure table
this module deliberately mirrors.

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
The state layer's other figures are ENACTED APPROPRIATIONS (a plan) and
Schedule 9 ACTUAL EXPENDITURES (a record of spending). This is the third
thing: what the state actually COLLECTED, on the same Budgetary-Legal
basis, from the state's own comparative statement.

ONLY THE "ACTUALS" COLUMN MAY EVER BE PUBLISHED. Schedule 8 prints three
column groups side by side — one Actuals and two Estimated — each with
General Fund / Special Funds / Total. The Estimated columns are
forecasts and they move enormously before settling: FY2022-23's General
Fund was estimated at 219,707, then 205,134, and came in at 178,557
($M) — a revision of -$41.2B, -18.7%. Publishing an Estimated column as
an actual would be publishing a forecast as a fact, so the actuals
column is IDENTIFIED FROM THE HEADER AND ASSERTED, never assumed to be
first (see _actuals_offset).

FOUR GATES, all of which must pass or the year is not published:
  G1  the coded revenue lines sum to the schedule's own printed
      "TOTALS, REVENUES" — General Fund, Special Funds and Total, each
      independently
  G2  the schedule's own internal footing: majors + minors == totals
  G3  Schedule 1's "Revenues and transfers" row, whose printed
      Reference-to-Schedule column says 8, equals Schedule 8's
      "TOTALS, REVENUES, TRANSFERS AND LOANS"
  G4  Schedule 6 — THE SAME DOCUMENT THE EXPENDITURE SIDE ALREADY GATES
      AGAINST — carries revenue columns in MILLIONS; they must match

That is one more cross-document tie than the spending side has, and on
every published year the residual is exactly zero (docs/V21_REVENUE_FINDING.md §2.2).

THE ASYMMETRY WITH SCHEDULE 9, WHICH THE PAGE STATES RATHER THAN HIDES:
FY2020-21 revenue extracts and gates cleanly here, while FY2020-21
EXPENDITURE actuals are not published at all — the Schedule 9 PDFs for
that year interleave text in a way no extraction mode orders correctly
(see schedule9.py). So the revenue series is one year longer than the
spending series, and a reader stepping through the years meets a
year with revenue and no spending. That is a fact about two different
PDFs, not about California, and the page says so.

Requires pypdf, as schedule9.py does.
"""

import io
import json
import re
import sys
import urllib.request
from pathlib import Path

import cache_guard

CACHE_DIR = Path(__file__).resolve().parent / "cache"

# actuals fiscal year -> (publication label, sch8, sch1, sch6)
#
# DECLARED PER VINTAGE, never discovered. Each year's actuals appear two
# publications later, the same relationship schedule9.py uses; the
# newest year comes from the Governor's Budget, which publishes at a
# different path (no "Enacted" segment).
_E = "https://ebudget.ca.gov/{fy}/pdf/Enacted/BudgetSummary/BS_SCH{n}.pdf"
_G = "https://ebudget.ca.gov/{fy}/pdf/BudgetSummary/BS_SCH{n}.pdf"


def _pub(fy, enacted=True):
    t = _E if enacted else _G
    return (t.format(fy=fy, n=8), t.format(fy=fy, n=1), t.format(fy=fy, n=6))


SOURCES = {
    "2015-16": ("2017-18 Enacted Budget",) + _pub("2017-18"),
    "2016-17": ("2018-19 Enacted Budget",) + _pub("2018-19"),
    "2017-18": ("2019-20 Enacted Budget",) + _pub("2019-20"),
    "2018-19": ("2020-21 Enacted Budget",) + _pub("2020-21"),
    "2019-20": ("2021-22 Enacted Budget",) + _pub("2021-22"),
    # FY2020-21 revenue DOES extract and gate, unlike its expenditure
    # counterpart. The difference is the document, not the year.
    "2020-21": ("2022-23 Enacted Budget",) + _pub("2022-23"),
    "2021-22": ("2023-24 Enacted Budget",) + _pub("2023-24"),
    "2022-23": ("2024-25 Enacted Budget",) + _pub("2024-25"),
    "2023-24": ("2025-26 Enacted Budget",) + _pub("2025-26"),
    "2024-25": ("2026-27 Governor's Budget",) + _pub("2026-27", enacted=False),
}

# Schedule 8 and Schedule 1 are in thousands; Schedule 6 rounds to whole
# millions. The Schedule 6 tolerance covers only that rounding.
GATE_EXACT = 0            # G1/G2 are footings of the same table: exact
GATE_SCH1 = 1             # $1K, for a printed-total transcription
GATE_SCH6 = 1_500         # covers Schedule 6's rounding to millions

# A printed value is one of: 1,234 | -1,234 | $ 1,234 | -- | $ --
# THE '$ --' FORM IS NOT DECORATIVE. The first row of each section
# carries dollar signs, so its zeros print as '$ --'. A token pattern
# that cannot match that does not merely skip the row: the nine-value
# window slides forward and captures numbers belonging to the NEXT
# row, which is a wrong figure rather than a missing one. G1 caught it
# as a $6.4B General Fund residual.
# A MINUS SIGN BINDS TO ITS DIGITS. "Investment Income - 2,892,323" is a
# line NAME ending in a hyphen, not a negative value: the schedule wraps
# long names and prints the tail after the numbers ("... Pooled Money
# Investments"). Allowing "- " to start a value turned ten positive
# General Fund figures negative and broke the row identity. A real
# negative prints closed up, "-899,011", so the sign may precede a dollar
# sign or digits but never a space.
# A VALUE MUST BEGIN WITH A DIGIT. '[\d,]+' also matches a bare comma,
# so the value run chained straight through the commas in wrapped
# line names ("... Revenue, Cities, and Counties") and swallowed
# dozens of rows per match — 136 parsed lines collapsed to 3.
# A minus can sit on EITHER side of the dollar sign: totals print
# negative transfers as "$ -7,533,537". A pattern that only allowed
# "-$" stopped the totals run after four tokens and the printed
# TRANSFERS AND LOANS total went missing.
_N = r'(?:-?\$\s*)?-?(?:\d[\d,]*|--)'
# The value run is captured MAXIMALLY and the LAST NINE are taken, because
# a line name can itself contain a number: "Oil and Gas Leases - 1 Percent
# Revenue, Cities, and Counties" wraps as "Oil and Gas Leases - 1" before
# its nine values. A fixed nine-token window starting at the name grabs
# the "1" and shifts every figure one place left — a wrong number, not a
# missing one, which is why _row() asserts the printed identity instead of
# trusting the window.
# A VALUE ENDS AT A WHITESPACE BOUNDARY. Without this the run matches a
# PREFIX of the next row's account code — "411025" of "4110250-Cigarette"
# — because the digits are legal value characters and only the final "0"
# would have tripped a "not followed by -letter" test. finditer then
# resumes mid-code and that row is never seen: 136 lines parsed as 71.
_NV = _N + r'(?=\s|$)'
# The run must be at least NINE tokens. Allowing a shorter one let an
# INLINE wrapped fragment satisfy the match by itself — "Retail Sales and
# Use Tax - 2011 Realignment -- 9,306,026 ..." parsed as a name plus the
# single value "2011" and the row was refused. Requiring nine forces the
# non-greedy name to absorb the fragment, which is where it belongs.
CODED_RE = re.compile(
    r'(\d{4,7})-([A-Za-z](?:(?!\d{4,7}-[A-Za-z])[^$]){0,95}?)\s+'
    r'((?:' + _NV + r'\s+){8,}' + _NV + r')')
# 95, not 70: the schedule itself truncates long line names at about
# 76 characters ("...Motor Vehicle Fuel Tax License D", "...Penalties
# and Inte"), and a tighter bound silently dropped exactly those two
# lines — $123M-$142M of Special Funds revenue a year, which G1 then
# refused. The gate caught it; the bound is what was wrong.
TOTALS_RE = re.compile(
    r'TOTALS,\s+((?:(?!TOTALS)[A-Z ,&\'\-])+?)\s+((?:' + _NV + r'\s+){8,}' + _NV + r')')


class GateError(RuntimeError):
    """A year that cannot be proven is not published."""


def _num(s):
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    # A token that is only dashes is the schedule's zero marker in any of
    # its renderings; anything else must parse as an integer or the row is
    # not what this parser thinks it is.
    if not s or set(s) <= {'-'}:
        return 0
    return int(s)


def _fetch_text(url, cache_key=None):
    """PDF text, cached. Existence is proven by CONTENT — a soft-404
    serving an HTML error page is a failure here, not a document."""
    if cache_key:
        p = CACHE_DIR / "state" / cache_key
        if p.exists():
            return p.read_text(encoding="utf-8")
    from pypdf import PdfReader
    req = urllib.request.Request(url, headers={"User-Agent": "ca-ledger-pipeline/3.0"})
    data = urllib.request.urlopen(req, timeout=180).read()
    if not data.startswith(b"%PDF"):
        raise GateError(
            f"NOT A PDF: {url} returned {len(data)} bytes beginning "
            f"{data[:16]!r}. A source that answers with something other than "
            "the document is an absence, whatever its status code.")
    text = "\n".join((p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages)
    text = re.sub(r'\s+', ' ', text)
    # "- $" IS GENUINELY AMBIGUOUS IN THIS DOCUMENT, and both readings occur:
    #   a real negative        "Revenue Transfers - $931,165"
    #   a wrapped name's tail  "Alcoholic Beverage Excise Tax - $177,475 …
    #                           … Beer and Wine"
    # Nothing in the text distinguishes them. Dropping this rewrite (to
    # protect the second) loses the first and every year fails G1 with a
    # POSITIVE residual — measured, 136 parsed lines fell to 123. Keeping it
    # mis-signs the second — measured, exactly the $177,475 FY2020-21
    # General Fund residual.
    #
    # So the rewrite stays, the sign is treated as a HYPOTHESIS, and the
    # row's own identity settles it: _triple tries the row as parsed and,
    # only if no nine-value window foots, retries with that leading sign
    # reversed. The document decides, not the parser.
    text = re.sub(r'(?<!-)- \$', '-$', text)
    # THE ZERO MARKER HAS TWO RENDERINGS. Some vintages emit "- -" where
    # others emit "--" (measured: 4180050 Cash Adjustment for
    # Transportation Funds, FY2020-21; 4171300 Donations and 4173100
    # Personal Income Tax Penalties, FY2024-25). Normalised so one token
    # pattern covers both — a row whose zeros do not tokenise is dropped
    # and surfaces as a G1 residual rather than as an error.
    # Both hyphens must be STANDALONE: without excluding a neighbouring
    # hyphen this also fires inside "- --" (a wrapped name's trailing
    # hyphen followed by a real zero marker) and produces "---", which
    # then fails to tokenise and drops the row.
    text = re.sub(r'(?<![-\d,])- -(?![-\d,])', '--', text)
    if cache_key:
        # through cache_guard, which makes cached source read-only: a
        # cached extraction is evidence, and evidence that can be edited
        # in place is not evidence.
        cache_guard.write_cached(CACHE_DIR / "state" / cache_key, text)
    return text


def _actuals_offset(text, year):
    """Which of the three column groups is the ACTUALS one — read from
    the schedule's own header, never assumed.

    THE SINGLE MOST DANGEROUS THING THIS MODULE DOES. Every printed row
    carries nine numbers: three column groups of (General, Special,
    Total). Taking the wrong group publishes a FORECAST as an ACTUAL,
    and the forecast for a settled year has been wrong by -18.7%. So the
    position is derived from the header text and the answer is asserted
    against the year being extracted.
    """
    heads = re.findall(r'(Actuals|Estimated)\s+(\d{4}-\d{2})', text)
    if not heads:
        raise GateError(
            f"NO COLUMN HEADER FOUND in Schedule 8 for {year} — the "
            "Actuals column cannot be identified, so every figure in this "
            "table is unattributable. Nothing published for this year.")
    # collapse the repeated per-page header to one ordered triple
    seen, order = set(), []
    for kind, fy in heads:
        if (kind, fy) not in seen:
            seen.add((kind, fy))
            order.append((kind, fy))
    actual = [i for i, (kind, fy) in enumerate(order) if kind == "Actuals"]
    if len(actual) != 1:
        raise GateError(
            f"EXPECTED EXACTLY ONE 'Actuals' COLUMN in Schedule 8 for "
            f"{year}, found {len(actual)}: {order}. Nothing published.")
    idx = actual[0]
    if order[idx][1] != year:
        raise GateError(
            f"SCHEDULE 8 ACTUALS COLUMN IS {order[idx][1]}, NOT {year} — "
            f"this publication does not carry the year it was declared for "
            f"({order}). Nothing published.")
    return idx * 3


_TOK = re.compile(_N)


def _triple(nums, offset):
    """The three funds of ONE column group, from a printed row.

    Tokenised with the same pattern that matched them, NOT by splitting
    on whitespace: printed totals render as "$ 195,261,190" with a space
    after the dollar sign, so a naive split yields eighteen tokens for a
    nine-value row.

    THE WINDOW IS CHOSEN BY THE ROW'S OWN IDENTITY, not by position.
    A row carries nine values — three column groups of (General,
    Special, Total) — but the captured run can hold ten, because the
    schedule wraps long names and a stray fragment of the name can sit
    on either side of the numbers, and can itself begin with a digit:

        4117400-Retail Sales and Use Tax -  --  9,306,026  9,306,026 …
                                                        … 2011 Realignment
        4152000-Oil and Gas Leases - 1  252  --  252 …
                                                        … Percent Revenue

    In the first the extra token trails the values; in the second it
    leads them. No fixed rule of "take the first nine" or "take the last
    nine" is right for both — the SAME rule gets one of them wrong, and
    getting it wrong shifts every figure one place and produces a
    plausible number rather than an error. So every consecutive
    nine-token window is tested against the identity the schedule
    guarantees (General + Special = Total, in each of the three column
    groups) and exactly one must satisfy it. Ambiguity is refused, not
    guessed; a refused row shows up immediately as a G1 residual.
    """
    v = [_num(x) for x in _TOK.findall(nums)]
    if len(v) < 9:
        raise GateError(f"expected at least 9 values, got {len(v)}: {nums!r}")

    def foots(w):
        return all(w[g * 3] + w[g * 3 + 1] == w[g * 3 + 2] for g in range(3))

    windows = [v[i:i + 9] for i in range(len(v) - 8)]
    good = [w for w in windows if foots(w)]
    if not good and v and v[0] < 0:
        # A BOUNDED REPAIR, PROVEN BY THE IDENTITY RATHER THAN ASSUMED.
        # Some vintages render a wrapped name's trailing hyphen flush
        # against the next value's dollar sign — "Alcoholic Beverage
        # Excise Tax -$177,475 ... Beer and Wine" — so the first value
        # reads negative when it is positive and the row will not foot.
        # The repair is to reinterpret ONLY that leading sign, and it is
        # accepted ONLY if the row then foots in all three column groups.
        # If it still does not, the row is refused as before; nothing is
        # guessed. Measured: this is exactly the $177,475 General Fund
        # residual G1 reported for FY2020-21.
        alt = [-v[0]] + v[1:]
        good = [w for w in (alt[i:i + 9] for i in range(len(alt) - 8)) if foots(w)]
    if len(good) != 1:
        raise GateError(
            f"{'NO' if not good else len(good)} nine-value window(s) satisfy "
            f"the row identity (General + Special = Total in all three column "
            f"groups) among {len(v)} tokens: {nums!r}. A row whose alignment "
            "cannot be established is not read.")
    w = good[0]
    return w[offset], w[offset + 1], w[offset + 2]


def _sch6_revenue(text, year):
    """(gf_revenue, total_revenue) in thousands from Schedule 6's history
    row. Schedule 6 states MILLIONS; its revenue pair sits at indices 4
    and 5 of the row's numeric fields, ahead of the expenditure pair
    schedule9.py reads at 6 and 7."""
    m = re.search(re.escape(year) + r'((?: [\d,\.]+){10,14})', text)
    if not m:
        raise GateError(f"Schedule 6 row for {year} not found")
    f = m.group(1).split()
    if len(f) < 8:
        raise GateError(f"Schedule 6 row for {year} malformed: {f}")
    return _num(f[4]) * 1000, _num(f[5]) * 1000


def _sch1_revenues(text):
    """Schedule 1's 'Revenues and transfers' row (General, Special), in
    thousands. Its printed Reference-to-Schedule column says 8, which is
    what makes this an independent tie rather than a restatement."""
    m = re.search(r'Revenues and transfers\s+8\s+(' + _N + r')\s+(' + _N + r')', text)
    if not m:
        return None
    return _num(m.group(1)), _num(m.group(2))


def _optional_total(totals, prefix):
    """A printed subtotal that some vintages do not render with values.

    FY2016-17 prints "TOTALS, TRANSFERS AND LOANS" immediately followed by
    "TOTALS, REVENUES, TRANSFERS AND LOANS" and gives figures only for the
    second. Transfers are not load-bearing for any of the four gates, so
    the honest handling is to record the absence rather than fail the year
    or invent a zero — absent is not zero.
    """
    for k, v in totals.items():
        if k.startswith(prefix):
            return {"gf": v[0], "sp": v[1], "tot": v[2]}
    return None


def parse_publication(year):
    """Extract and GATE one fiscal year. Returns a dict, or raises
    GateError — a year that cannot be proven is not published."""
    label, u8, u1, u6 = SOURCES[year]
    t8 = _fetch_text(u8, f"sch8-{year}.txt")
    off = _actuals_offset(t8, year)

    lines, seen_codes = [], set()
    for m in CODED_RE.finditer(t8):
        code, name, nums = m.group(1), m.group(2).strip(), m.group(3)
        try:
            gf, sp, tot = _triple(nums, off)
        except GateError:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)
        lines.append({"code": code, "name": re.sub(r'\s+', ' ', name).strip(),
                      "gf": gf, "sp": sp, "tot": tot})
    if len(lines) < 100:
        raise GateError(
            f"ONLY {len(lines)} CODED REVENUE LINES PARSED for {year}; the "
            "schedule publishes on the order of 140. A parse this thin "
            "would foot to a total that is missing money. Nothing published.")

    totals = {}
    for m in TOTALS_RE.finditer(t8):
        key = re.sub(r'\s+', ' ', m.group(1)).strip()
        try:
            totals[key] = _triple(m.group(2), off)
        except GateError:
            continue

    def need(k):
        for cand in totals:
            if cand.startswith(k):
                return totals[cand]
        raise GateError(f"Schedule 8 {year}: printed total {k!r} not found "
                        f"(saw {sorted(totals)[:8]})")

    t_rev = need("REVENUES")
    # ---- G1: the coded lines ARE the printed total, each fund independently
    got = (sum(l["gf"] for l in lines), sum(l["sp"] for l in lines),
           sum(l["tot"] for l in lines))
    for i, fund in enumerate(("General Fund", "Special Funds", "Total")):
        if abs(got[i] - t_rev[i]) > GATE_EXACT:
            raise GateError(
                f"G1 FAIL {year} {fund}: {len(lines)} coded lines sum to "
                f"${got[i]:,}K but the schedule prints ${t_rev[i]:,}K "
                f"(residual ${got[i] - t_rev[i]:,}K). Nothing published.")
    # ---- G2: the schedule's own internal footing
    maj, mino = need("MAJOR TAXES"), need("MINOR REVENUES")
    for i, fund in enumerate(("General Fund", "Special Funds", "Total")):
        if maj[i] + mino[i] != t_rev[i]:
            raise GateError(
                f"G2 FAIL {year} {fund}: majors ${maj[i]:,}K + minors "
                f"${mino[i]:,}K != totals ${t_rev[i]:,}K. Nothing published.")
    # ---- G3: Schedule 1's own reference to Schedule 8
    t_rtl = need("REVENUES, TRANSFERS")
    s1 = _sch1_revenues(_fetch_text(u1, f"sch1-{year}.txt"))
    g3 = "not-located"
    if s1:
        if abs(s1[0] - t_rtl[0]) > GATE_SCH1 or abs(s1[1] - t_rtl[1]) > GATE_SCH1:
            raise GateError(
                f"G3 FAIL {year}: Schedule 1 revenues+transfers "
                f"${s1[0]:,}K/${s1[1]:,}K vs Schedule 8 "
                f"${t_rtl[0]:,}K/${t_rtl[1]:,}K. Nothing published.")
        g3 = "pass"
    # ---- G4: Schedule 6, the document the spending side already uses
    s6gf, s6tot = _sch6_revenue(_fetch_text(u6, f"sch6-{year}.txt"), year)
    if abs(s6gf - t_rtl[0]) > GATE_SCH6 or abs(s6tot - t_rtl[2]) > GATE_SCH6:
        raise GateError(
            f"G4 FAIL {year}: Schedule 6 revenue ${s6gf:,}K/${s6tot:,}K vs "
            f"Schedule 8 ${t_rtl[0]:,}K/${t_rtl[2]:,}K. Nothing published.")

    sections = {}
    for k, v in totals.items():
        if k in ("REVENUES", "MAJOR TAXES AND", "MINOR REVENUES",
                 "TRANSFERS AND LOANS", "REVENUES, TRANSFERS"):
            continue
        sections[k] = v
    return {
        "year": year, "publication": label, "source": u8,
        "lines": lines,
        "revenues": {"gf": t_rev[0], "sp": t_rev[1], "tot": t_rev[2]},
        "transfers": _optional_total(totals, "TRANSFERS AND LOANS"),
        "revenuesTransfers": {"gf": t_rtl[0], "sp": t_rtl[1], "tot": t_rtl[2]},
        "sections": sections,
        "gates": {"G1": "pass", "G2": "pass", "G3": g3, "G4": "pass"},
    }


if __name__ == "__main__":
    which = sys.argv[1:] or sorted(SOURCES)
    ok, bad = [], []
    for y in which:
        try:
            r = parse_publication(y)
            ok.append(y)
            print(f"{y}  {r['publication']:<28} lines={len(r['lines']):>3}  "
                  f"GF ${r['revenues']['gf']:>13,}K  TOT ${r['revenues']['tot']:>13,}K  "
                  f"gates={r['gates']}")
        except (GateError, Exception) as e:      # noqa: BLE001
            bad.append((y, str(e)[:150]))
            print(f"{y}  REFUSED: {str(e)[:150]}", file=sys.stderr)
    print(f"\n{len(ok)} year(s) gated, {len(bad)} refused", file=sys.stderr)
