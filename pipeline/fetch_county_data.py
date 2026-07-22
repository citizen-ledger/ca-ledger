#!/usr/bin/env python3
"""
Citizen Ledger — county data pipeline (V5, option (a)).

Rewrites ../county-data.js from the State Controller's "By the
Numbers" portal, in the same schema pattern as city-data.js.

Datasets (verified 2026-07-13): County - Expenditures (uctr-c2j8),
County - Revenues (emxv-k8xv), County Expenditures Per Capita
(miui-wb29 — the reconciliation target). 57 counties file every year;
San Francisco is a consolidated city-county that files as a CITY and
lives in city-data.js with its consolidation footnote — it is
deliberately absent here and must never be double-counted.

HARD GATE (same as cities): every county-year total (governmental +
enterprise + internal service + conduit) must equal the SCO's
published control total to within $1,000, or nothing is written.
Verified before this was built: Alameda FY 2023-24 sums to
$4,244,700,272 — the control value exactly.

THE REQUIRED COMPARABILITY NOTE: counties provide municipal-type
services chiefly to unincorporated areas. The unincorporated-population
share is computed per county-year as
(county population − Σ populations of the county's cities) / county
population, using the SAME SCO filings for both sides (the house rule:
same-vintage denominators, never mixed). It ships with every
county-year as `unincorporated` and the UI must surface it — this is
the county equivalent of the contract-city problem.

Usage:
    python3 fetch_county_data.py          # dry run: fetch + gates
    python3 fetch_county_data.py --write  # rebuild ../county-data.js
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp                      # noqa: E402
from fetch_city_data import soda, norm           # noqa: E402
import revisions                                 # noqa: E402

DS_EXPEND = "uctr-c2j8"
DS_REVEN = "emxv-k8xv"
DS_PERCAP = "miui-wb29"
SOURCE_YEARS = [str(y) for y in range(2017, 2025)]

FUNCTIONS = [
    ("police",          "Police protection (sheriff)"),
    ("detention",       "Detention & correction"),
    ("judicial",        "Judicial"),
    ("fire",            "Fire protection"),
    ("protectionOther", "Other public protection"),
    ("streets",         "Public ways & facilities"),
    ("health",          "Health"),
    ("sanitation",      "Sanitation"),
    ("assistance",      "Public assistance"),
    ("education",       "Education"),
    ("recreation",      "Recreation & cultural"),
    ("admin",           "General government"),
    ("debt",            "Debt service"),
    ("capital",         "Capital outlay"),
]
ENTERPRISE_FUNDS = [
    ("water", "Water"), ("sewer", "Sewer"), ("solidWaste", "Solid waste"),
    ("electric", "Electric"), ("gas", "Gas"), ("airport", "Airports"),
    ("harborPort", "Harbor & port"), ("hospital", "Hospital"),
    ("transit", "Transit"), ("otherEnterprise", "Other enterprise"),
]
ENTERPRISE_BY_CATEGORY = {
    "Water Enterprise Fund": "water",
    "Sewer Enterprise Fund": "sewer",
    "Solid Waste Enterprise Fund": "solidWaste",
    "Electric Enterprise Fund": "electric",
    "Gas Enterprise Fund": "gas",
    "Airport Enterprise Fund": "airport",
    "Harbor and Port Enterprise Fund": "harborPort",
    "Hospital Enterprise Fund": "hospital",
    "Hospital Enterprise Fund Fund": "hospital",   # source quirk, verified
    "Transit Enterprise Fund": "transit",
    "Other Enterprise Fund": "otherEnterprise",
}

OUT_PATH = Path(__file__).resolve().parent.parent / "county-data.js"
CITY_DATA = Path(__file__).resolve().parent.parent / "city-data.js"
GATE_DOLLARS = 1_000


def fy_label(source_year):
    y = int(source_year)
    return f"{y - 1}-{str(y)[-2:]}"


def reads_subgroup(cat):
    """Does classify() DISCRIMINATE on the sub-group for this category?

    Declared once and asserted against behaviour by the test suite, which
    calls classify() with two different sub-groups per category and checks
    that the answer changes exactly for the categories named here. So this
    table cannot silently drift out of step with the branches below."""
    return (cat == "Public Protection"
            or cat.startswith("Public Ways")
            or cat.startswith("Education and Recreation")
            or cat == "Debt Service and Capital Outlay")


def classify(category, sub1):
    """Counties file (category, subcategory_1, line_description): the GROUP
    in `category`, the SUB-GROUP in `subcategory_1`, the line beneath it.

    THE SUB-GROUP'S POSITION MUST BE ESTABLISHED, NOT MERELY ITS VALUE
    RECOGNIZED — the city's guard, ported.

    Testing only the VALUE of subcategory_1 cannot tell a filing that
    carries a real sub-group from one whose sub-group column has collapsed
    into an echo of the category. Both look like strings. Measured against
    this function before the guard existed:

        classify('Public Protection', 'Public Protection')
            -> ('gov', 'protectionOther')
        classify('Public Protection', None)
            -> ('gov', 'protectionOther')
        classify('Education and Recreation…', 'Education and Recreation…')
            -> ('gov', 'education')

    The first two file every police, detention, judicial and fire dollar
    into the residual bucket. The third is worse: startswith('Education')
    is satisfied by the echoed CATEGORY itself, so all recreation and
    cultural spending is misfiled as education. In every case the totals
    gate stays green, because CONSERVATION CANNOT SEE CLASSIFICATION —
    the same blindness that shipped FY 2016-17 city functions wrong.

    So where the sub-group is load-bearing it must be PROVEN to carry a
    sub-group. If it is empty, or is the category over again, position
    carries no information and the row is refused.

    Note the test is exact equality, not a prefix: under
    'Public Ways and Facilities, Health, and Sanitation' the SCO publishes
    a legitimate sub-group 'Public Ways and Facilities', which is a prefix
    of its own category. A startswith test would refuse real data.

    Verified against every published county year: 55 distinct
    (category, subcategory_1) shapes across FY 2016-17..2023-24, zero
    echoes and zero empties, so this refuses nothing that ships today. It
    is the vintage shift it exists for — the county equivalent of the
    column move SCO made to the city files in FY 2016-17."""
    cat = norm(category)
    if cat in ENTERPRISE_BY_CATEGORY:
        return "ent", ENTERPRISE_BY_CATEGORY[cat]
    if cat == "Internal Service Fund":
        return "isf", None
    if cat == "Conduit Financing":
        return "conduit", None
    g = norm(sub1)
    if reads_subgroup(cat) and (not g or g == cat):
        raise SystemExit(
            "NO SUB-GROUP DETAIL IN THIS SOURCE VINTAGE — refusing to "
            f"classify: category={category!r} subcategory_1={sub1!r}. "
            f"The function group {cat!r} occupies the sub-group position "
            "too, so nothing establishes which field the sub-group came "
            "from. Classifying it would file every police, detention, "
            "judicial and fire dollar under 'protectionOther' — and "
            "recreation under 'education' — while every totals gate "
            "passed, because conservation cannot see classification. "
            "This is the county form of the pre-FY 2016-17 city layout. "
            "Extend classify() deliberately if such a vintage is ever to "
            "be loaded.")
    if cat == "Public Protection":
        if g.startswith("Police"):
            return "gov", "police"
        if g.startswith("Detention"):
            return "gov", "detention"
        if g.startswith("Judicial"):
            return "gov", "judicial"
        if g.startswith("Fire"):
            return "gov", "fire"
        return "gov", "protectionOther"
    if cat.startswith("Public Ways"):
        if g.startswith("Health"):
            return "gov", "health"
        if g.startswith("Sanitation"):
            return "gov", "sanitation"
        return "gov", "streets"
    if cat == "Public Assistance":
        return "gov", "assistance"
    if cat.startswith("Education and Recreation"):
        return "gov", "education" if g.startswith("Education") else "recreation"
    if cat == "Debt Service and Capital Outlay":
        return "gov", "debt" if g.startswith("Debt") else "capital"
    if cat == "General Government":
        return "gov", "admin"
    raise SystemExit(
        "UNRECOGNIZED EXPENDITURE SHAPE — refusing to classify: "
        f"category={category!r} sub1={sub1!r}. A source vintage has "
        "shifted; extend classify() deliberately. (The silent catch-all "
        "this replaced is how FY 2016-17 city functions shipped wrong — "
        "see STATUS.md, 2026-07-14.)")


def fetch_year(source_year):
    exp = soda(DS_EXPEND,
               **{"$select": "entity_name,category,subcategory_1,"
                             "line_description,"
                             "sum(values) as v,max(estimated_population) as pop",
                  "$where": f"fiscal_year='{source_year}'",
                  "$group": "entity_name,category,subcategory_1,"
                            "line_description"})
    rev = soda(DS_REVEN,
               **{"$select": "entity_name,category,sum(values) as v",
                  "$where": f"fiscal_year='{source_year}'",
                  "$group": "entity_name,category"})
    out = {}
    for r in exp:
        name = norm(r["entity_name"])
        c = out.setdefault(name, {
            "pop": 0, "byFunction": {}, "enterprise": {},
            "lines": {},
            "isf": 0.0, "conduit": 0.0, "revenues": 0.0,
            "revenuesEnterprise": 0.0})
        c["pop"] = max(c["pop"], int(float(r.get("pop") or 0)))
        v = float(r.get("v") or 0)
        kind, key = classify(r.get("category"), r.get("subcategory_1"))
        if kind == "gov":
            c["byFunction"][key] = c["byFunction"].get(key, 0.0) + v
            if v != 0:
                lbl = norm(r.get("line_description")) or "(unlabeled)"
                fam = c["lines"].setdefault(key, {})
                fam[lbl] = fam.get(lbl, 0.0) + v
        elif kind == "ent":
            c["enterprise"][key] = c["enterprise"].get(key, 0.0) + v
        elif kind == "isf":
            c["isf"] += v
        else:
            c["conduit"] += v
    for r in rev:
        name = norm(r["entity_name"])
        if name not in out:
            continue
        cat = norm(r.get("category"))
        v = float(r.get("v") or 0)
        if cat in ENTERPRISE_BY_CATEGORY:
            out[name]["revenuesEnterprise"] += v
        elif cat not in ("Internal Service Fund", "Conduit Financing"):
            out[name]["revenues"] += v
            if cat.startswith("Intergovernmental"):
                key = ("igState" if "State" in cat else
                       "igFederal" if "Federal" in cat else "igOther")
                out[name][key] = out[name].get(key, 0.0) + v
    print(f"  FY {fy_label(source_year)}: {len(out)} counties, "
          f"{len(exp):,} expenditure lines", file=sys.stderr)
    return out


def city_populations_by_county():
    """{county name: {display fiscal year: Σ city populations}} from the
    SAME SCO filings the city view uses — never a mixed vintage."""
    text = CITY_DATA.read_text(encoding="utf-8")
    d = json.loads(text[text.index("=") + 1: text.rindex(";")])
    out = {}
    for c in d["cities"].values():
        for fy, yr in c["years"].items():
            out.setdefault(c["county"], {}).setdefault(fy, 0)
            out[c["county"]][fy] += yr["population"]
    return out


def main():
    ap = argparse.ArgumentParser(description="Rebuild county-data.js")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    print("Fetching official per-county control totals…", file=sys.stderr)
    official = {(norm(r["entity_name"]), r["fiscal_year"]):
                float(r.get("total_expenditures") or 0)
                for r in soda(DS_PERCAP,
                              **{"$select": "entity_name,fiscal_year,total_expenditures",
                                 "$where": "fiscal_year in("
                                           + ",".join(f"'{y}'" for y in SOURCE_YEARS) + ")"})}
    print(f"  {len(official):,} county-year controls", file=sys.stderr)
    city_pops = city_populations_by_county()

    years_data = {y: fetch_year(y) for y in SOURCE_YEARS}

    errors, notes = [], []
    reconciled, unreconciled = 0, []
    # THE CLASSIFICATION-SHAPE GATE (hard): statewide, every function
    # must be nonzero in every year (measured clean on all 8 shipped
    # vintages); a column shift zeroes whole functions while totals
    # still reconcile.
    for sy, counties in years_data.items():
        sw = {}
        for c in counties.values():
            for k, v in c["byFunction"].items():
                sw[k] = sw.get(k, 0.0) + v
        for key, _label in FUNCTIONS:
            if sw.get(key, 0) <= 0:
                errors.append(f"SHAPE FY {fy_label(sy)}: statewide "
                              f"{key!r} is zero — classification broke")
    for sy, counties in years_data.items():
        if len(counties) != 57:
            errors.append(f"FY {fy_label(sy)}: {len(counties)} counties (expected 57)")
        if "San Francisco" in counties:
            errors.append(f"FY {fy_label(sy)}: San Francisco present in county data "
                          "— it must live only in the city layer")
        for name, c in counties.items():
            ours = (sum(c["byFunction"].values()) + sum(c["enterprise"].values())
                    + c["isf"] + c["conduit"])
            ctrl = official.get((name, sy))
            # A ZERO OR MISSING CONTROL DOES NOT RECONCILE.
            #
            # The city pipeline received this guard; its county sibling did
            # not, and the identical comparison shipped three county-years
            # as "reconciled" on a vacuous test: abs(0 - 0) > max(1000, 0)
            # is false, so a year with nothing filed passed exactly as a
            # year that matched to the dollar. Verified at source - SCO
            # publishes total_expenditures = '0' for Humboldt FY2019-20,
            # Humboldt FY2020-21 and Mendocino FY2021-22 - so the FIGURES
            # are right and the ASSURANCE was never earned. Those years are
            # counted as unreconciled and named, not passed.
            if ctrl is None:
                errors.append(f"{name} FY {fy_label(sy)}: no control total")
                unreconciled.append(f"{name} FY {fy_label(sy)} (no control)")
            elif ctrl == 0:
                unreconciled.append(f"{name} FY {fy_label(sy)} (control is zero)")
                if ours > 0:
                    errors.append(
                        f"{name} FY {fy_label(sy)}: we report ${ours:,.0f} but "
                        "the published control is 0 - the figure cannot be "
                        "reconciled and must not ship as if it were")
            elif abs(ours - ctrl) > max(GATE_DOLLARS, ctrl * 0.001):
                errors.append(f"{name} FY {fy_label(sy)}: ${ours:,.0f} vs control "
                              f"${ctrl:,.0f} (drift ${abs(ours - ctrl):,.0f})")
            else:
                reconciled += 1
            if c["pop"] <= 0:
                errors.append(f"{name} FY {fy_label(sy)}: population 0")
    if reconciled < 440:
        errors.append(
            f"only {reconciled} county-years reconciled against a published "
            f"control ({len(unreconciled)} did not: {unreconciled[:5]}) - a "
            "gate that verified this few has not verified this layer")
    if errors:
        for e in errors[:30]:
            print("  FAIL:", e, file=sys.stderr)
        sys.exit(f"{len(errors)} gate failure(s) — county-data.js left untouched.")
    if unreconciled:
        print(f"  {len(unreconciled)} county-year(s) NOT reconciled - the "
              "Controller publishes no usable control for them: "
              + ", ".join(unreconciled), file=sys.stderr)
    print(f"All gates passed (57 counties × 8 years; {reconciled} county-years "
          f"reconcile against the official SCO control totals, "
          f"{len(unreconciled)} have no usable control and are not claimed "
          f"as reconciled).", file=sys.stderr)

    def slugify(name):
        s = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
        while "--" in s:
            s = s.replace("--", "-")
        return s.strip("-")

    def m(v):
        return round(v / 1e6, 3)

    # V8 line dictionary + PARENT-SUM GATE (per county-year-function)
    line_labels = sorted({lbl for cs in years_data.values()
                          for c in cs.values()
                          for fam in c["lines"].values() for lbl in fam})
    line_idx = {lbl: i for i, lbl in enumerate(line_labels)}
    for sy, cs in years_data.items():
        for cname, c in cs.items():
            for k, total in c["byFunction"].items():
                lsum = sum(c["lines"].get(k, {}).values())
                if abs(lsum - total) > 1:
                    sys.exit(f"V8 GATE {cname} FY {fy_label(sy)} {k}: lines "
                             f"${lsum:,.0f} vs function ${total:,.0f} — "
                             "nothing written")

    counties_out = {}
    unincorporated_unknown = []
    all_names = sorted({n for cs in years_data.values() for n in cs})
    for name in all_names:
        entry = {"name": name, "years": {}}
        prev_gov = None
        for sy in SOURCE_YEARS:
            c = years_data[sy].get(name)
            if not c:
                prev_gov = None
                continue
            fy = fy_label(sy)
            gov = sum(c["byFunction"].values())
            ent = sum(c["enterprise"].values())
            city_pop = (city_pops.get(name) or {}).get(fy, 0)
            # A SHARE OUTSIDE [0,1] IS NOT AN EXTREME VALUE — IT IS PROOF
            # THE INPUTS DISAGREE, and it must not be clamped.
            #
            # `max(0.0, min(1.0, ...))` used to turn an impossible share into
            # a confident 0%. Siskiyou shipped "0% of residents live in
            # unincorporated areas" in five of eight years while the other
            # three carried the true ~55%, so the county flipped between 55%
            # and 0% along its own trend line. The cause is one bad source
            # figure: Mt. Shasta's filing reports ~86,500 residents against a
            # real ~3,200, so the county's cities outnumber the county and
            # the raw share is -1.372.
            #
            # The share is now UNKNOWN when it cannot be computed, and the
            # reason travels with the year. The county's other figures are
            # unaffected — they gate independently — so refusing the whole
            # build over a denominator the source got wrong would withhold
            # correct data to punish an error we do not control.
            uninc, uninc_note = None, None
            if c["pop"]:
                raw = (c["pop"] - city_pop) / c["pop"]
                if 0.0 <= raw <= 1.0:
                    # A share of exactly 1.0 is legitimate for a county with
                    # no incorporated city (Alpine, Mariposa, Trinity) — and
                    # is ALSO what a total join failure produces. The two are
                    # indistinguishable from the number alone, so confirm the
                    # county really has no cities rather than trusting it.
                    if raw == 1.0 and name in city_pops and city_pops[name]:
                        raise SystemExit(
                            f"{name} County FY {fy}: unincorporated share is "
                            "exactly 1.000, but this county HAS cities in the "
                            "city dataset — the join returned no population "
                            "for them rather than the county genuinely having "
                            "none. Nothing written.")
                    uninc = raw
                else:
                    uninc_note = (
                        f"Not computable for this year: the cities inside this "
                        f"county report {city_pop:,} residents between them "
                        f"against the county's own reported {c['pop']:,}, so "
                        f"the unincorporated share works out at {raw:.1%} — "
                        f"impossible, and a sign the filed populations "
                        f"disagree rather than a measurement of the county.")
                    unincorporated_unknown.append((name, fy))
            yr = {
                "population": c["pop"],
                "unincorporated": None if uninc is None else round(uninc, 3),
                **({"unincorporatedUnknown": uninc_note} if uninc_note else {}),
                "revenues": m(c["revenues"]),
                "expenditures": m(gov),
                "byFunction": {k: m(v) for k, v in c["byFunction"].items()
                               if round(v / 1e6, 3) != 0},
                "lines": {k: sorted(
                              ([line_idx[lbl], int(round(v))]
                               for lbl, v in fam.items() if round(v) != 0),
                              key=lambda x: -abs(x[1]))
                          for k, fam in c["lines"].items()
                          if any(round(v) != 0 for v in fam.values())},
                "enterprise": {"total": m(ent),
                               "revenues": m(c["revenuesEnterprise"]),
                               "byFund": {k: m(v) for k, v in c["enterprise"].items()
                                          if round(v / 1e6, 3) != 0}},
                "scoTotal": m(sum(c["byFunction"].values())
                              + sum(c["enterprise"].values()) + c["isf"] + c["conduit"]),
            }
            if round(c["isf"] / 1e6, 3):
                yr["internalService"] = m(c["isf"])
            if round(c["conduit"] / 1e6, 3):
                yr["conduitFinancing"] = m(c["conduit"])
            n = []
            if prev_gov and prev_gov > 0 and (gov / prev_gov > 1.4 or gov / prev_gov < 0.6):
                n.append("bigSwing")
            if n:
                yr["notes"] = n
            entry["years"][fy] = yr
            prev_gov = gov
        counties_out[slugify(name)] = entry

    latest_sy = SOURCE_YEARS[-1]
    ig = {"state": 0.0, "federal": 0.0, "other": 0.0, "governmental": 0.0}
    for c in years_data[latest_sy].values():
        ig["state"] += c.get("igState", 0.0)
        ig["federal"] += c.get("igFederal", 0.0)
        ig["other"] += c.get("igOther", 0.0)
        ig["governmental"] += c["revenues"]
    ig_total = ig["state"] + ig["federal"] + ig["other"]
    intergovernmental = {
        "year": fy_label(latest_sy),
        "stateM": m(ig["state"]),
        "federalM": m(ig["federal"]),
        "otherM": m(ig["other"]),
        "governmentalRevenuesM": m(ig["governmental"]),
        "share": round(ig_total / ig["governmental"], 4),
        "stateShare": round(ig["state"] / ig["governmental"], 4),
        "method": "sum of Intergovernmental – State/Federal/Other revenue "
                  "categories across all 57 counties' governmental funds "
                  f"(enterprise, ISF, conduit excluded), {DS_REVEN}, most "
                  "recent fiscal year. The address view's figures-do-not-add "
                  "statement renders these values; it hardcodes none of them.",
    }

    payload = {
        "meta": {
            "source": "bythenumbers.sco.ca.gov",
            "sourceLabel": "County annual financial reports, State Controller's "
                           "Office “By the Numbers” (bythenumbers.sco.ca.gov) — "
                           "reported actual expenditures and revenues",
            "generated": date.today().isoformat(),
            "units": "millions of dollars",
            "basis": "Reported actual revenues and expenditures from each "
                     "county's annual report to the State Controller. "
                     "Governmental activities by function; ratepayer-funded "
                     "enterprise activities separate; internal service funds "
                     "and conduit financing excluded from both blocks. Each "
                     "county-year reconciles against the Controller's "
                     "published per-capita dataset total (stored per year as "
                     "scoTotal), except where the Controller publishes a total "
                     "of zero because the county did not file: those "
                     "county-years are marked absent and are not claimed as "
                     "reconciled, since reproducing a published zero would "
                     "prove nothing.",
            "sanFrancisco": "San Francisco is a consolidated city and county "
                            "and files as a city; it appears only in the "
                            "Cities layer (with a consolidation footnote) and "
                            "is never counted in this file.",
            "unincorporatedNote": "unincorporated = share of county residents "
                                  "living outside any incorporated city, "
                                  "computed from the same SCO filings' "
                                  "populations (county minus the sum of its "
                                  "cities); counties serve these residents "
                                  "directly as the local government.",
            "intergovernmental": intergovernmental,
            "lineLabels": line_labels,
            "linesNote": "V8 depth: per county-year, lines = {function: "
                         "[[lineLabelIdx, whole dollars]]} — governmental "
                         "activities, official FTR activity_fundtype line "
                         "names, children sum to the unrounded function "
                         "totals exactly (gated).",
            "datasets": {"expenditures": DS_EXPEND, "revenues": DS_REVEN,
                         "perCapita": DS_PERCAP},
        },
        "years": [fy_label(y) for y in SOURCE_YEARS],
        "functions": [{"key": k, "name": n} for k, n in FUNCTIONS],
        "enterpriseFunds": [{"key": k, "name": n} for k, n in ENTERPRISE_FUNDS],
        "counties": counties_out,
    }
    prev = revisions.previous_payload(OUT_PATH)
    stamp(payload)
    if not args.write:
        la = payload["counties"]["los-angeles"]["years"]["2023-24"]
        print(json.dumps({"losAngelesCounty 2023-24": {
            "population": la["population"], "unincorporated": la["unincorporated"],
            "expenditures": la["expenditures"], "scoTotal": la["scoTotal"]}}, indent=2))
        sys.exit("Dry run complete — re-run with --write.")
    header = ("/* GENERATED by pipeline/fetch_county_data.py on "
              f"{date.today().isoformat()} from State Controller's Office "
              "data (bythenumbers.sco.ca.gov) — do not edit by hand. */\n")
    OUT_PATH.write_text(header + "window.CA_COUNTY_DATA = "
                        + json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
                        + ";\n", encoding="utf-8")
    revisions.record_revision("county", prev, payload,
                              source_signal=revisions.socrata_updated(
                                  ["uctr-c2j8", "emxv-k8xv", "miui-wb29"]))
    if unincorporated_unknown:
        print(f"  unincorporated share NOT COMPUTABLE for "
              f"{len(unincorporated_unknown)} county-year(s) — the filed city "
              f"populations exceed the county's own: "
              + ", ".join(f"{n} {fy}" for n, fy in unincorporated_unknown),
              file=sys.stderr)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB, "
          f"{len(counties_out)} counties)")


if __name__ == "__main__":
    main()
