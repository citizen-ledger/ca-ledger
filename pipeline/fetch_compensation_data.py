#!/usr/bin/env python3
"""
Generate compensation-data.js and comp/<slug>.json — the public employee
compensation layer, built per docs/V23A_COMPENSATION_BUILD_FINDING.md.

    python3 pipeline/fetch_compensation_data.py            # dry run
    python3 pipeline/fetch_compensation_data.py --write    # write

THIS PIPELINE CANNOT FETCH ITS OWN SOURCE. That is the point of the
exception below, and it is checked rather than assumed: the inputs must
already be on disk, placed there by a human.

    pipeline/cache/compensation/2024_City.csv
    pipeline/cache/compensation/2024_County.csv
    pipeline/cache/compensation/2024_SpecialDistrict.csv
    pipeline/cache/compensation/2024_K12Education.csv

WHY — THE SECOND MANUAL-CACHE EXCEPTION ON THIS SITE.
gcc.sco.ca.gov (where publicpay.ca.gov redirects) expressly excludes
automated retrieval: its robots.txt carries a Cloudflare managed block
naming ClaudeBot, GPTBot, CCBot, Google-Extended and others, with
Content-Signal "ai-train=no, use=reference". A person with a browser is
welcome to the files; a pipeline is not. So the files are downloaded by
hand, exactly as the CSU audited financial statements are (see
fetch_csu_data.py, which is bot-gated for a different reason).

Two exceptions is a documented limit; two treated as one-offs is how a
rebuild-from-source claim quietly becomes untrue. They are therefore
named TOGETHER wherever the site makes that claim — README, about.html,
reading.html, the layer page — never separately.

WHAT THIS LAYER IS, AND THE THREE THINGS IT MUST NEVER DO.

It is an AS-FILED record of what each employer reported to the State
Controller, position by position. It is not gated, and the reason is
structural rather than a tolerance that could be widened: SCO publishes
an annual press-release total (746,358 positions / ~$67.28B for cities
and counties, 25 June 2025) but the export is a LIVE database whose
LastUpdatedDate here runs to 2026-01-15. Recomputing gives 762,047 and
$68.60B — +2.10% and +1.96% — because eighteen more cities filed after
the announcement. There is no as-of-date total published, so no instant
exists at which the two could be aligned. A per-vintage declaration, the
fix that closed the CCC and CDIAC cases, cannot close this one.

  1. NO AVERAGES. Not mean, not median, not any per-position summary
     statistic. Measured: 89,206 of 345,097 city rows (25.8%) carry
     RegularPay below half the position's own MinPositionSalary — part-
     year or part-time people sitting beside full-time ones — and the
     export has no hours or FTE field to separate them. Any average over
     that population measures the part-time mix. It would be the site's
     own misleading number rather than the source's, which is the one
     failure this project exists to avoid. This module computes sums and
     counts only, and the shape gate below asserts that.
  2. NO RANKING. No top-earners view, no sort by pay in the payload.
     Rows ship in the order the employer filed them.
  3. NO SHARE OF SPENDING. Compensation does not tie to this site's
     expenditure figures — median ratio 0.431 against published city
     expenditure, p10-p90 0.203-0.641 — because the site's figure is
     governmental activities only while this covers every employee the
     employer reports, including enterprise departments, and the export
     carries no fund field to correct it.

Requires nothing but the standard library.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates                                     # noqa: E402
from integrity import stamp                      # noqa: E402
import revisions                                 # noqa: E402
from strict import StrictRow                     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "cache" / "compensation"
OUT = ROOT / "compensation-data.js"
DETAIL_DIR = ROOT / "comp"

YEAR = "2024"

# DECLARED PER LAYER, never discovered from the directory. A file that
# appears without a declaration is not read; a declaration whose file is
# missing stops the build with the manual-download instruction.
SOURCES = {
    "city":     ("2024_City.csv",           "Cities",            "mandated"),
    "county":   ("2024_County.csv",         "Counties",          "mandated"),
    "district": ("2024_SpecialDistrict.csv", "Special districts", "mandated"),
    "k12":      ("2024_K12Education.csv",   "K-12 education",    "voluntary"),
}

# The export is not UTF-8. It is Windows-1252 — 0x96 (en dash) appears in
# position titles and decodes as an invalid start byte under utf-8. Named
# here rather than passed as a bare string at three call sites.
ENCODING = "cp1252"

# Columns this module reads. Declared so StrictRow refuses a vintage that
# renames one rather than silently reading zero.
NEEDED = ("Year", "EmployerName", "DepartmentOrSubdivision", "Position",
          "ElectedOfficial", "RegularPay", "OvertimePay", "LumpSumPay",
          "OtherPay", "TotalWages", "DefinedBenefitPlanContribution",
          "EmployeesRetirementCostCovered", "DeferredCompensationPlan",
          "HealthDentalVision", "TotalRetirementAndHealthContribution",
          "PensionFormula", "EmployerCounty", "EmployerPopulation",
          "IncludesUnfundedLiability", "LastUpdatedDate")

# SCO's own published totals, transcribed from the press releases. NOT a
# gate — see the module docstring — but recorded so the page can show the
# reader how far the live file has moved from the last announcement, which
# is the only vintage signal the source offers.
PUBLISHED = {
    "citiesCounties": {
        "date": "2025-06-25",
        "url": "https://www.sco.ca.gov/eo_pressrel_26935.html",
        "positions": 746358,
        "wages": 67_280_000_000,
        "cities": 461, "counties": 55,
        "note": "Twenty two cities and two counties failed to file or "
                "provided incomplete information.",
    },
    "k12": {
        "date": "2025-12-05",
        "url": "https://www.sco.ca.gov/eo_pressrel_27224.html",
        "positions": 345184,
        "wages": 18_200_000_000,
        "compliantFilers": 360, "invitedFilers": 1883,
    },
}

# STALENESS. The source publishes one reporting year at a time and the
# next lands roughly a year later; a layer more than this far past its own
# newest LastUpdatedDate is stale on the page while still looking current.
# The test suite asserts this too, so staleness fails CI rather than
# sitting quietly on the page.
STALE_MONTHS = 14


def money(v):
    """Whole dollars. The source publishes cents in some columns and not
    others; nothing here is divided, so rounding at read is safe."""
    s = str(v or "").replace(",", "").replace("$", "").strip()
    if not s:
        return 0
    try:
        return int(round(float(s)))
    except ValueError:
        return 0


def money_cell(v):
    """A DISPLAYED cell: None when the source cell is EMPTY, else dollars.

    money() above maps a blank and a filed "0" to the same 0, which is
    correct for ARITHMETIC — a blank contributes nothing to a sum — and
    wrong for DISPLAY, because the page then cannot tell a measurement from
    a silence. Measured in the Controller's own export:

        overtime filed 0 ............ 763,879   shown as an em dash
        lump+other filed 0 .......... 340,143   shown as an em dash
        regular pay BLANK ............ 17,359   shown as $0

    So the collapse ran in BOTH directions at once: over a million filed
    zeros were rendered as the em dash this site reserves for NOT
    PUBLISHED, and seventeen thousand genuinely absent cells were rendered
    as a filed zero. Every component column carries blanks — regular pay
    included, which had no em-dash branch on the page at all — so this is
    applied per displayed column rather than to the two that were reported.

    TotalWages and TotalRetirementAndHealthContribution have ZERO blanks
    across all 1,407,216 rows, so the totals are always figures and need
    no third state."""
    s = str(v or "").replace(",", "").replace("$", "").strip()
    if not s:
        return None
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def truthy(v):
    return str(v or "").strip().lower() in ("true", "yes", "1", "y")


def slug(layer, name, county=""):
    """Slugs are keyed BY LAYER, and that is not cosmetic.

    Measured: without the layer prefix, 28 employers vanished — "Alameda"
    the county collided with "Alameda" the city, and the county file's 57
    employers collapsed to 33. Two governments with one name is the exact
    shape of the Rural North Vacaville failure the district pipeline
    already records; here it would silently merge a county's payroll into
    a city's. The uniqueness gate below asserts the fix held.
    """
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    if county and layer == "district":
        s += "-" + re.sub(r"[^a-z0-9]+", "-", str(county).lower()).strip("-")
    return f"{layer}-{s}"


def read_rows(path, layer):
    """Stream one export through StrictRow.

    The manual-download instruction lives here because this is where the
    absence is discovered, and a contributor who hits it needs the fix in
    front of them, not in a doc.
    """
    if not path.exists():
        raise SystemExit(
            f"MISSING SOURCE: {path}\n\n"
            "This layer's source cannot be fetched by the pipeline. "
            "gcc.sco.ca.gov expressly excludes automated retrieval "
            "(robots.txt names ClaudeBot, GPTBot, CCBot and others; "
            "Content-Signal ai-train=no). Download the reporting-year "
            f"{YEAR} export by hand from "
            "https://gcc.sco.ca.gov/Reports/RawExport.aspx and place it "
            f"at {path}.\n\n"
            "This is the site's SECOND manual-cache exception, alongside "
            "the CSU audited statements. Both are named together wherever "
            "the rebuild-from-source claim appears; if you add a third, "
            "add it to those places too.")
    with open(path, newline="", encoding=ENCODING) as f:
        rdr = csv.DictReader(f)
        missing = [c for c in NEEDED if c not in (rdr.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"{path.name}: the export is missing column(s) {missing}. "
                "The vintage renamed something; declare the new name in "
                "NEEDED rather than reading around it — nothing written.")
        for raw in rdr:
            yield StrictRow(raw, f"{path.name}:{layer}")


def build(argv=None):
    entities = {}          # slug -> record
    detail = {}            # slug -> [row, ...]
    positions, departments = {}, {}
    vocab_pos, vocab_dep = [], []
    file_hashes = {}
    updated_seen = []
    layer_totals = {}

    def vp(s):
        if s not in positions:
            positions[s] = len(vocab_pos); vocab_pos.append(s)
        return positions[s]

    def vd(s):
        if s not in departments:
            departments[s] = len(vocab_dep); vocab_dep.append(s)
        return departments[s]

    for layer, (fname, label, mandate) in SOURCES.items():
        path = CACHE / fname
        h = hashlib.sha256()
        if path.exists():
            h.update(path.read_bytes())
            file_hashes[fname] = h.hexdigest()

        n_rows = 0
        wages = ret = 0
        # IncludesUnfundedLiability is an EMPLOYER-level property in every
        # file measured (0 of 479 cities, 0 of 3,159 districts and 0 of 437
        # K-12 employers mix values across their own rows). The dagger is
        # only exact if that holds, so it is asserted per employer rather
        # than believed.
        unfunded_seen = defaultdict(set)

        for r in read_rows(path, layer):
            n_rows += 1
            if r["Year"].strip() != YEAR:
                raise SystemExit(
                    f"{fname}: row with Year={r['Year']!r}, expected {YEAR}. "
                    "One export, one reporting year — a mixed file would "
                    "put two vintages behind one label; nothing written.")
            name = r["EmployerName"].strip()
            county = r["EmployerCounty"].strip()
            sl = slug(layer, name, county)
            rec = entities.get(sl)
            if rec is None:
                rec = entities[sl] = {
                    "name": name, "layer": layer, "county": county,
                    "positions": 0, "wages": 0, "retHealth": 0,
                    "population": money(r["EmployerPopulation"]) or None,
                    "unfundedInRetirement": truthy(r["IncludesUnfundedLiability"]),
                    "elected": 0,
                }
                detail[sl] = []
            unfunded_seen[sl].add(truthy(r["IncludesUnfundedLiability"]))

            w = money(r["TotalWages"])
            rh = money(r["TotalRetirementAndHealthContribution"])
            # THE SOURCE'S OWN ROW IDENTITY, asserted per row. Both hold at
            # 100.000% across all 1,407,216 rows; they prove the file is
            # self-consistent, not that any figure is right, and they are
            # checked so a future vintage that breaks them is loud.
            parts = (money(r["RegularPay"]) + money(r["OvertimePay"])
                     + money(r["LumpSumPay"]) + money(r["OtherPay"]))
            if abs(parts - w) > 1:
                raise SystemExit(
                    f"{fname}: {name} / {r['Position']}: pay components sum "
                    f"to {parts:,} but TotalWages is {w:,}. The source's own "
                    "row identity failed; nothing written.")
            bparts = (money(r["DefinedBenefitPlanContribution"])
                      + money(r["EmployeesRetirementCostCovered"])
                      + money(r["DeferredCompensationPlan"])
                      + money(r["HealthDentalVision"]))
            if abs(bparts - rh) > 1:
                raise SystemExit(
                    f"{fname}: {name} / {r['Position']}: benefit components "
                    f"sum to {bparts:,} but the total is {rh:,}; nothing written.")

            rec["positions"] += 1
            rec["wages"] += w
            rec["retHealth"] += rh
            if truthy(r["ElectedOfficial"]):
                rec["elected"] += 1
            wages += w; ret += rh

            # ROWS SHIP AS FILED, IN FILE ORDER. Never sorted by pay — a
            # sorted payload is a ranking whatever the page does with it.
            # LUMP SUM AND OTHER are two source cells shown as one column.
            # It is NOT PUBLISHED only when BOTH are empty; if either
            # carries a figure — including a filed 0 — the column is a
            # figure, and the empty one contributes nothing to it.
            ls_c, op_c = money_cell(r["LumpSumPay"]), money_cell(r["OtherPay"])
            lump = None if (ls_c is None and op_c is None) else (ls_c or 0) + (op_c or 0)
            detail[sl].append([
                vp(r["Position"].strip()),
                vd(r["DepartmentOrSubdivision"].strip()),
                money_cell(r["RegularPay"]), money_cell(r["OvertimePay"]),
                lump,
                rh,
                1 if truthy(r["ElectedOfficial"]) else 0,
            ])
            u = r["LastUpdatedDate"].strip()
            if u:
                updated_seen.append(u)

        mixed = [s for s, v in unfunded_seen.items() if len(v) > 1]
        if mixed:
            raise SystemExit(
                f"{fname}: {len(mixed)} employer(s) report "
                "IncludesUnfundedLiability BOTH ways across their own rows, "
                "so a per-employer dagger would be wrong for some of them. "
                "The flag is no longer an employer-level property and the "
                "dagger must be re-derived per row; nothing written. "
                f"First: {mixed[:3]}")
        gates.require_rows(n_rows, 1000, f"{label} compensation rows",
                           "the export carries hundreds of thousands.")
        layer_totals[layer] = {"label": label, "mandate": mandate,
                               "employers": sum(1 for e in entities.values()
                                                if e["layer"] == layer),
                               "positions": n_rows, "wages": wages,
                               "retHealth": ret}
        print(f"{label:18} {n_rows:>9,} positions  {sum(1 for e in entities.values() if e['layer']==layer):>5} employers  "
              f"${wages:>15,}  +${ret:,} retirement/health", file=sys.stderr)

    # ---- vintage, from the source's own LastUpdatedDate
    def parse_upd(s):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        return None
    dates = sorted(d for d in (parse_upd(u) for u in updated_seen) if d)
    if not dates:
        raise SystemExit("no parseable LastUpdatedDate anywhere in the "
                         "exports — the layer would have no vintage to "
                         "show; nothing written")
    vintage = {"earliest": dates[0].isoformat(), "latest": dates[-1].isoformat(),
               "staleMonths": STALE_MONTHS}
    age_days = (date.today() - dates[-1]).days
    vintage["ageDaysAtBuild"] = age_days
    if age_days > STALE_MONTHS * 31:
        print(f"  WARNING: newest LastUpdatedDate is {dates[-1]} — "
              f"{age_days} days old, past the {STALE_MONTHS}-month mark. "
              "The staleness test will fail.", file=sys.stderr)

    # ---- NOT-PUBLISHED vs ZERO, against the site's own rosters.
    # Nothing in the export marks a non-filer; it is simply absent. The
    # only way to tell "did not file" from "has no employees" is to diff
    # against a roster the site already holds, so that is done here and
    # the answer is published rather than left to a reader's inference.
    def load(p):
        s = (ROOT / p).read_text()
        i = s.find("{")
        return json.loads(s[i:s.rfind("}") + 1])
    nonfilers = {}
    try:
        city = load("city-data.js")
        have = {slug("city", e["name"]) for e in entities.values() if e["layer"] == "city"}
        nonfilers["city"] = sorted(v["name"] for v in city["cities"].values()
                                   if slug("city", v["name"]) not in have)
    except Exception as e:                       # noqa: BLE001
        raise SystemExit(f"could not diff city roster for non-filers: {e}")

    # ---- CONTRACT SERVICES. A city with no police department has no
    # police positions, exactly as it has no police spending. The site
    # already records which services are contracted out; that field is
    # reused so the absence is marked rather than read as a zero.
    contracted = {}
    for v in city["cities"].values():
        sv = v.get("services") or {}
        marks = {k: d.get("label") for k, d in sv.items()
                 if isinstance(d, dict) and d.get("code") not in ("A", "B", None)}
        if marks:
            contracted[slug("city", v["name"])] = marks

    # ---- THE UNIQUENESS GATE. Every employer in every file must have
    # its own slug. A collision does not raise on its own — it merges two
    # payrolls into one record and reports a smaller, wrong number.
    for layer, t in layer_totals.items():
        got = sum(1 for e in entities.values() if e["layer"] == layer)
        if got != t["employers"]:
            raise SystemExit(
                f"{layer}: {t['employers']} employers counted while reading "
                f"but {got} distinct slugs — {t['employers']-got} collided "
                "and their payrolls would be merged; nothing written.")

    # ---- THE SHAPE GATE: this payload must contain no computed average.
    # Asserted structurally rather than trusted, because "no averages" is
    # the single rule most likely to be violated by a well-meaning later
    # edit. Every numeric leaf on an entity is a count or a sum of whole
    # dollars; a mean would not be an integer.
    for sl, e in entities.items():
        for k in ("positions", "wages", "retHealth", "elected"):
            if not isinstance(e[k], int):
                raise SystemExit(
                    f"{sl}.{k} is {type(e[k]).__name__}, not int. Every "
                    "figure in this layer is a count or a whole-dollar sum; "
                    "a non-integer means something was divided, and this "
                    "layer publishes no averages. Nothing written.")

    payload = {
        "meta": {
            "source": "gcc.sco.ca.gov",
            "sourceLabel": "California State Controller — Government "
                           "Compensation in California, reporting year "
                           f"{YEAR}, as filed by each employer",
            "generated": date.today().isoformat(),
            "year": YEAR,
            "units": "whole dollars, as filed",
            "tier": "AS FILED — UNRECONCILED",
            "vintage": vintage,
            "published": PUBLISHED,
            "basis": (
                "REPORTED AS FILED — UNRECONCILED. Each row is one position "
                "as its employer reported it to the State Controller for "
                "calendar " + YEAR + ". The Controller publishes an annual "
                "total in a press release, but the export is a live "
                "database with no as-of-date total, so the two can never be "
                "aligned at any instant and this layer is not gated. It is "
                "not a gate that failed; there is no instant at which a "
                "gate could be applied."),
            "doesNotEqual": (
                "THIS IS NOT A SHARE OF SPENDING AND IS NOT A DRILL-DOWN OF "
                "IT. Compensation reported here does not tie to the "
                "expenditure figures elsewhere on this site: measured "
                "against published city expenditure the ratio has a median "
                "of 0.431 and a 10th-to-90th-percentile range of 0.203 to "
                "0.641. That spread is how much enterprise activity each "
                "city runs, not how labour-intensive it is — the site's "
                "expenditure figure covers governmental activities only, "
                "while this covers every employee the employer reports "
                "including enterprise departments, and the export carries "
                "no fund field to correct it. This is its own record on "
                "its own basis."),
            "noAverages": (
                "This layer publishes no average, median or any other "
                "per-position summary. In the city file 89,206 of 345,097 "
                "rows (25.8%) report regular pay below half the position's "
                "own minimum salary — part-year and part-time positions "
                "sitting beside full-time ones — and the export has no "
                "hours or full-time-equivalent field to separate them. Any "
                "average over that population would measure the part-time "
                "mix, and it would be this site's number rather than the "
                "Controller's."),
            "pensionDagger": (
                "Employers marked here include payments toward unfunded "
                "pension liability inside the retirement figure; employers "
                "not marked exclude it. The Controller collects this as a "
                "single flag per employer and does not publish the unfunded "
                "component separately, so it cannot be netted out. Two "
                "identically-paid positions at two employers can therefore "
                "show different total compensation for a reporting reason "
                "alone. Across the city file 139,863 records carry the flag "
                "and 205,234 do not."),
            "reproducibility": (
                "THIS LAYER CANNOT BE REBUILT WITHOUT A MANUAL DOWNLOAD. "
                "gcc.sco.ca.gov excludes automated retrieval, so the four "
                "source files were fetched by hand. This is one of exactly "
                "two such exceptions on this site — the other is the CSU "
                "audited financial statements — and they are named together "
                "wherever the rebuild claim appears. The digest below "
                "proves the published file matches the sources that were "
                "used; it cannot prove those sources are what the "
                "Controller would serve today."),
            "nonFilers": nonfilers,
            "contractedServices": contracted,
            "layers": layer_totals,
            "sourceFiles": file_hashes,
            "positionsVocab": vocab_pos,
            "departmentsVocab": vocab_dep,
            "detailPath": "comp/{slug}.json",
            "rowFields": ["position", "department", "regularPay", "overtimePay",
                          "lumpSumAndOther", "retirementAndHealth", "elected"],
            # THE THIRD STATE IS DECLARED, so a consumer of these files does
            # not have to infer it. null is NOT PUBLISHED — the Controller's
            # cell is empty. 0 is a REPORTED ZERO — the employer filed that
            # amount. They are different facts and this record keeps them
            # apart. Only these three columns can be null; the two totals
            # have no empty cells in the source.
            "nullableRowFields": ["regularPay", "overtimePay", "lumpSumAndOther"],
            "nullMeans": "NOT PUBLISHED — the State Controller's cell is "
                         "empty for this position. A 0 is a REPORTED ZERO: "
                         "the employer filed that amount. Never read one as "
                         "the other.",
        },
        "entities": entities,
    }
    stamp(payload)
    return payload, detail


def main():
    ap = argparse.ArgumentParser(description="Rebuild compensation-data.js")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    payload, detail = build()

    body = "window.COMPENSATION_DATA = " + json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False) + ";\n"
    n_detail = sum(len(v) for v in detail.values())
    print(f"\nindex {len(body)/1e6:.2f} MB · {len(payload['entities']):,} employers · "
          f"{n_detail:,} position rows in {len(detail):,} detail files",
          file=sys.stderr)
    print(f"vintage {payload['meta']['vintage']['earliest']} .. "
          f"{payload['meta']['vintage']['latest']} "
          f"({payload['meta']['vintage']['ageDaysAtBuild']} days old at build)",
          file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    prev = revisions.previous_payload(OUT)
    OUT.write_text(body)
    DETAIL_DIR.mkdir(exist_ok=True)
    for sl, rows in detail.items():
        (DETAIL_DIR / f"{sl}.json").write_text(
            json.dumps(rows, separators=(",", ":")))
    revisions.record_revision("compensation", prev, payload)
    print(f"Wrote {OUT} and {len(detail):,} files under {DETAIL_DIR}/",
          file=sys.stderr)


if __name__ == "__main__":
    main()
