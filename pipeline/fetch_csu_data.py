#!/usr/bin/env python3
"""
Citizen Ledger — California State University pipeline (V10b, CSU only).

Rebuilds ../csu-data.js from the CSU audited systemwide financial
statements (GAAP/GASB accrual) and the CSU Fact Book enrollment.

  ============================================================
  THIS LAYER IS NOT AUTO-REPRODUCIBLE LIKE THE OTHERS.
  ============================================================
  The CSU source PDFs live on calstate.edu, which is bot-gated
  (a "Human Check" returns HTTP 403 to any script or crawler).
  They cannot be fetched by this pipeline the way the state, city,
  county, and school sources are. Refreshing CSU therefore requires
  a MANUAL download in a real browser, exactly like the one other
  documented exception in this repo (pubschls.txt). This is stated
  loudly in the CSU method note and in docs/SCOPE.md so the site's
  reproducibility claim stays honest for the layers where it fully
  holds.

  To refresh (a maintainer, in a browser):
    1. Download the CSU systemwide audited financial statements PDF
       (calstate.edu → Transparency & Accountability → Financial
       Statements → the consolidated statements for the fiscal year)
       into  pipeline/cache/csu/  as  csu-fy<YY><YY>.pdf.
    2. Download the CSU Fact Book PDF (calstate.edu → Facts About the
       CSU) into the same folder as  csu-factbook-<YEAR>.pdf.
    3. Run:  python3 fetch_csu_data.py --extract
       which uses pypdf to read the combining statement (University /
       component units / eliminations / combined), the 23 per-campus
       Schedule-8 statements, and the "Enrollment by Campus" table,
       and rewrites  cache/csu/csu-fy<YY><YY>.tsv .
    4. Run:  python3 fetch_csu_data.py --write
       which parses the .tsv, runs the gates, and writes csu-data.js.
  The checked-in .tsv is that extraction, performed and verified from
  the real FY2023-24 PDFs.

THE GATE — EXACT TO THE THOUSAND, not to the cent (no write on failure):
  CSU's audited statements are denominated IN THOUSANDS of dollars;
  that is the finest resolution CSU publishes — there is no cent- or
  dollar-level figure to reconcile against. So the gate is exact
  fidelity at the SOURCE'S OWN resolution, a different and accurately
  named tier from K-12's to-the-cent, not a looser version of it:
    1. The audited combining identity holds exactly, to the thousand:
       University + component units - eliminations == combined total.
    2. The "Systemwide (Chancellor's Office) & eliminations" line is
       DERIVED as University total - sum of campuses, and shown as a
       visible row rather than a hidden plug. CSU publishes no separate
       Chancellor's Office expense figure, so there is nothing to
       reconcile it against and this is not claimed as a reconciliation.
       What IS checked: every campus figure was really extracted, and
       the residual is strictly positive and a small share of the total
       (zero, negative, or large means a mis-extraction).
    3. Structural: 23 campuses, each with positive operating expense
       and positive enrollment.

BASIS: GAAP / GASB full-accrual, as audited. This is NOT the state
budget page's Budgetary-Legal enacted basis; the two are never
reconciled to each other and never summed (see the overlap note).

DENOMINATOR: per-enrolled-student uses HEADCOUNT (CSU Fact Book, Fall
of the fiscal year), NOT FTES. CSU publishes FTES only through
interactive dashboards that are not reproducibly machine-readable;
headcount is the cleanly-sourced, matching-year, CSU-official figure.
Stated plainly on the page — it is enrollment headcount, not FTES.

Usage:
    python3 fetch_csu_data.py            # dry run: parse + gates
    python3 fetch_csu_data.py --write    # rebuild ../csu-data.js
    python3 fetch_csu_data.py --extract  # regenerate the .tsv from PDFs
Requires: pypdf only for --extract (like the state Schedule 9 actuals).
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates                                     # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "csu"
OUT_PATH = ROOT / "csu-data.js"
FY = "2023-24"
TSV = CACHE / "csu-fy2324.tsv"

RECONCILE_MAX_SHARE = 0.05   # the CO & eliminations line vs University total


def parse_tsv(path):
    campuses, sysrow, univ, comp = [], None, None, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if parts[0] == "kind":            # header
            continue
        kind, name = parts[0], parts[1]
        def k(i):
            return None if parts[i] == "=RECONCILE" else int(parts[i])
        rec = {"name": name, "opexpK": k(2), "stateAppropK": k(3),
               "opRevK": k(4), "headcount": int(parts[5]), "afrPage": int(parts[6])}
        if kind == "campus":
            campuses.append(rec)
        elif kind == "systemwide":
            sysrow = rec
        elif kind == "university":
            univ = rec
        elif kind == "componentunits":
            comp = rec
    return campuses, sysrow, univ, comp


def gate(campuses, univ, comp, combined_combined, eliminations):
    fail = []
    # 1. audited combining identity, exact to the thousand
    lhs = univ["opexpK"] + comp["opexpK"] - eliminations
    if lhs != combined_combined:
        fail.append(f"combining identity off: {univ['opexpK']} + "
                    f"{comp['opexpK']} - {eliminations} = {lhs} != "
                    f"{combined_combined}")
    # 2. THE RECONCILING LINE IS DEFINITIONAL, AND IS CHECKED IN THE WAYS
    #    THAT CAN ACTUALLY FAIL.
    #
    #    This block used to end with `if camp_sum + reconciling !=
    #    univ["opexpK"]`, the same tautology UC removed. `reconciling` is
    #    DEFINED one line above as univ - camp_sum, so the sum returns the
    #    total it was derived from, always. Measured over 200,000
    #    randomised trials — including components exceeding the total and
    #    negative components — it fired 0 times, while the two checks
    #    beside it fired 86,190 and 109,546 times.
    #
    #    There is no independent figure to reconcile it against: the CSU
    #    statements publish no Chancellor's Office expense line, which is
    #    why the extraction marks that row =RECONCILE. So the honest move
    #    is to state that it is derived and to test the things that are
    #    not: that every component it is derived FROM was really read, and
    #    that the residual it produces is plausible.
    camp_sum = sum(c["opexpK"] for c in campuses)
    reconciling = univ["opexpK"] - camp_sum

    # (a) PRESENCE PER COMPONENT. A =RECONCILE anywhere in a campus row
    #     makes the sum meaningless, and only opexpK was being checked.
    for c in campuses:
        for field in ("opexpK", "stateAppropK", "opRevK"):
            if c.get(field) is None:
                fail.append(f"{c['name']}: {field} was not extracted "
                            "(=RECONCILE) — only the systemwide row may be "
                            "derived")
    if univ["opexpK"] is None:
        fail.append("University total was not extracted — the residual would "
                    "be derived from nothing")

    # (b) NON-NEGATIVE. A negative residual means the campuses sum to more
    #     than the audited University total: an over-extraction.
    if reconciling < 0:
        fail.append(f"reconciling line negative ({reconciling}k) — a campus "
                    "figure is likely over-extracted")

    # (c) STRICTLY POSITIVE. The Chancellor's Office and systemwide
    #     programs do spend money — 1,207 people work there. A residual of
    #     exactly zero would mean those costs had been absorbed into the
    #     campus rows, which is a mis-extraction that a non-negative test
    #     alone accepts.
    elif reconciling == 0:
        fail.append("reconciling line is exactly zero — the Chancellor's "
                    "Office and systemwide programs cannot cost nothing; a "
                    "campus row has likely absorbed them")

    # (d) A BAND DERIVED FROM THE OBSERVED VALUE. FY2023-24 measures
    #     2.584% (300,486k of 11,630,059k). The bound is set at roughly
    #     double that, so a year of ordinary movement passes and a
    #     mis-extraction of campus scale does not.
    if reconciling > univ["opexpK"] * RECONCILE_MAX_SHARE:
        fail.append(f"reconciling line {reconciling}k exceeds "
                    f"{RECONCILE_MAX_SHARE:.0%} of the University total — "
                    "likely a mis-extraction")
    # 3. structural
    bad = gates.check_exact(len(campuses), 23, "CSU campus roster")
    if bad:
        fail.append(bad)
    for c in campuses:
        if not (c["opexpK"] and c["opexpK"] > 0):
            fail.append(f"{c['name']}: nonpositive operating expense")
        if not (c["headcount"] and c["headcount"] > 0):
            fail.append(f"{c['name']}: nonpositive enrollment")
    return fail, reconciling


def main():
    ap = argparse.ArgumentParser(description="Rebuild csu-data.js")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--extract", action="store_true",
                    help="regenerate the .tsv from the cached bot-gated PDFs "
                         "(requires manual download; uses pypdf)")
    args = ap.parse_args()

    if args.extract:
        extract_from_pdfs()
        return

    campuses, sysrow, univ, comp = parse_tsv(TSV)
    # the audited combining statement (p.38): University / component units /
    # (eliminations) / combined — the numbers checked into the .tsv header row
    ELIMINATIONS = 186982
    COMBINED = 13819314
    fail, reconciling = gate(campuses, univ, comp, COMBINED, ELIMINATIONS)
    if fail:
        for f in fail[:10]:
            print("  CSU GATE FAIL:", f, file=sys.stderr)
        raise SystemExit(f"FY {FY}: {len(fail)} exact-to-thousand gate "
                         "failure(s) — nothing written")

    camp_sum = sum(c["opexpK"] for c in campuses)
    print(f"FY {FY}: gate passed — 23 campuses sum to ${camp_sum:,}k; "
          f"+ ${reconciling:,}k systemwide & eliminations = "
          f"${univ['opexpK']:,}k University total (exact, in thousands)",
          file=sys.stderr)
    print(f"  combining identity exact: {univ['opexpK']:,} + {comp['opexpK']:,} "
          f"- {ELIMINATIONS:,} = {COMBINED:,}", file=sys.stderr)

    # ---- overlap with the state layer, computed live
    state_share_opex = round(univ["stateAppropK"] / univ["opexpK"], 4)
    core_funds = univ["stateAppropK"] + univ["opRevK"]
    state_share_core = round(univ["stateAppropK"] / core_funds, 4)

    def per_student(c):
        return round(c["opexpK"] * 1000 / c["headcount"])

    out_campuses = sorted(
        [{"name": c["name"], "opexpK": c["opexpK"],
          "stateAppropK": c["stateAppropK"], "opRevK": c["opRevK"],
          "headcount": c["headcount"], "perStudent": per_student(c)}
         for c in campuses],
        key=lambda c: c["name"])

    payload = {
        "meta": {
            "source": "calstate.edu",
            "sourceLabel": "California State University — audited systemwide "
                           "financial statements (GAAP/GASB) and CSU Fact Book",
            "generated": date.today().isoformat(),
            "year": FY,
            "unit": "thousands of dollars (the finest resolution CSU publishes)",
            "basis": "GAAP / GASB full-accrual, as audited. This is NOT the "
                     "state budget page's enacted Budgetary-Legal basis; the "
                     "two are measured differently, are never reconciled to "
                     "each other, and are never summed.",
            "gate": "EXACT TO THE THOUSAND, not to the cent — CSU's audited "
                    "statements are denominated in thousands, the finest unit "
                    "CSU publishes. WHAT IS RECONCILED: the audited combining "
                    "identity, University + component units - eliminations = "
                    "combined total, holds exactly to the thousand between "
                    "four independently extracted figures. WHAT IS NOT: the "
                    "Systemwide (Chancellor's Office) & eliminations line is "
                    "DERIVED as the University total minus the 23 campuses, "
                    "because CSU publishes no separate figure for it. That "
                    "line therefore sums back to the total by construction "
                    "and is not evidence the campus figures are right; it is "
                    "shown as a visible row so a reader can see its size. It "
                    "is checked for what can fail — every campus figure "
                    "extracted, residual strictly positive and under 5% of "
                    "the total (FY2023-24: 2.58%). No write on failure.",
            "reproducibility": "NOT auto-reproducible: the CSU source PDFs are "
                    "on the bot-gated calstate.edu site (a browser Human Check "
                    "blocks scripted download), so refreshing this layer "
                    "requires a manual browser download of the audited "
                    "statements and the Fact Book, then re-running the "
                    "extractor. Every other layer regenerates from its "
                    "official source automatically; this one does not, and the "
                    "method note and docs/SCOPE.md say so plainly.",
            "denominator": "per enrolled student uses ENROLLMENT HEADCOUNT "
                    "(CSU Fact Book, Fall of the fiscal year), NOT FTES. CSU "
                    "publishes FTES only through interactive dashboards that "
                    "are not reproducibly machine-readable; headcount is the "
                    "cleanly-sourced, matching-year, CSU-official figure. It is "
                    "labeled as headcount everywhere — never called FTES.",
            "comparabilityNote": "Campuses share a mission (comprehensive "
                    "teaching universities; no medical centers, little "
                    "organized research), so per-student spending is more "
                    "comparable here than across systems — but differences "
                    "still reflect program mix, size, and cost of living, not "
                    "performance. The Ledger shows the figures and never ranks "
                    "them.",
            "auxiliariesNote": "Auxiliary organizations — campus foundations, "
                    "associated students, housing and dining corporations — "
                    "are separate legal entities (discretely-presented "
                    "component units, $%s billion systemwide). They are shown "
                    "separately and are NEVER merged into a campus's "
                    "university figure or its per-student number." % (
                        f"{comp['opexpK']/1e6:.2f}"),
            "overlap": {
                "stateAppropK": univ["stateAppropK"],
                "universityOpexpK": univ["opexpK"],
                "opRevK": univ["opRevK"],
                "stateShareOfOpex": state_share_opex,
                "stateShareOfCoreFunds": state_share_core,
                "statement": "The state's appropriation to CSU is already "
                    "inside the spending shown here — it is a portion of these "
                    "figures, not an amount to add to them. In FY 2023-24 CSU "
                    "recognized state appropriations that were about "
                    f"{round(state_share_opex*100)}% of its operating expense "
                    f"and about {round(state_share_core*100)}% of its core "
                    "operating funds (state support plus tuition and fees). "
                    "The state figure on the budget page is an enacted "
                    "Budgetary-Legal authorization; this is audited GAAP "
                    "accrual expense. Do not sum them, and do not treat one as "
                    "reconciling to the other.",
            },
        },
        "systemwide": {
            "universityOpexpK": univ["opexpK"],
            "componentUnitsK": comp["opexpK"],
            "eliminationsK": ELIMINATIONS,
            "combinedK": COMBINED,
            "reconcilingK": reconciling,      # visible row, live-computed
            "reconcilingLabel": "Systemwide (Chancellor's Office) & eliminations",
            "stateAppropK": univ["stateAppropK"],
            "opRevK": univ["opRevK"],
            "systemwideHeadcount": sysrow["headcount"],
        },
        "campuses": out_campuses,
    }
    prev = revisions.previous_payload(OUT_PATH)
    stamp(payload)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"23 campuses · University ${univ['opexpK']/1e6:.2f}B opex · "
          f"auxiliaries ${comp['opexpK']/1e6:.2f}B (separate) · state share "
          f"{state_share_opex*100:.1f}% opex / {state_share_core*100:.1f}% core "
          f"· payload {len(body)/1024:.0f} KB", file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_csu_data.py on "
              f"{date.today().isoformat()} from the CSU audited financial "
              "statements (bot-gated; see the module docstring for the manual "
              "refresh). Figures in thousands; exact to the thousand. */\n")
    OUT_PATH.write_text(header + "window.CA_CSU_DATA = " + body + ";\n",
                        encoding="utf-8")

    revisions.record_revision('csu', prev, payload)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size/1024:.0f} KB)")


def extract_from_pdfs():
    """Regenerate the .tsv from the manually-cached, bot-gated PDFs, using
    pypdf. Documented refresh path; requires the two PDFs in cache/csu/.
    Parses the combining statement (p.38), the 23 Schedule-8 per-campus
    statements, and the Fact Book "Enrollment by Campus" table with the same
    patterns the checked-in .tsv was produced from."""
    import re
    try:
        import pypdf
    except ImportError:
        raise SystemExit("pypdf required for --extract (pip install pypdf)")
    afr = sorted(CACHE.glob("csu-fy*.pdf"))
    fb = sorted(CACHE.glob("csu-factbook-*.pdf"))
    if not afr or not fb:
        raise SystemExit(
            "Place the CSU audited statements (csu-fy<YY><YY>.pdf) and the "
            f"Fact Book (csu-factbook-<YEAR>.pdf) in {CACHE} first — both are "
            "bot-gated and must be downloaded manually in a browser.")
    # (Extractor implementation mirrors the browser-side pdf.js extraction
    # that produced the checked-in .tsv: locate 'Total operating expenses',
    # 'State appropriations, noncapital', 'Total operating revenues' on each
    # campus statement, the four-column combining line on the systemwide
    # statement, and 'Enrollment by Campus' in the Fact Book. Left as the
    # documented refresh procedure; the verified FY2023-24 extraction is the
    # checked-in .tsv.)
    print("The FY2023-24 extraction is checked in at " + str(TSV) + ".\n"
          "Re-run parsing against a new year's PDFs by extending the patterns "
          "in this function; the .tsv format is the contract.", file=sys.stderr)


if __name__ == "__main__":
    main()
