#!/usr/bin/env python3
"""
Generate district-data.js — the special districts layer of
Citizen Ledger, built per the V5 finding, option (b): a finding, a
directory, and as-filed figures that are deliberately NOT the same
evidentiary tier as the state, city, and county layers.

    python3 pipeline/fetch_district_data.py            # dry run, report only
    python3 pipeline/fetch_district_data.py --write    # write district-data.js

Sources (SCO "By the Numbers", Socrata SODA API):
  m9u3-wdam   Special Districts - Expenditures
  nkv3-m73r   Special Districts - Revenues
  and one "filed late or failed to file" list per fiscal year where
  SCO published one (FY 2018-19 through 2023-24; none exists for
  FY 2016-17 or 2017-18):
    uiun-snc7 (2018-19)  rbwh-942r (2019-20)  fbdc-d5ib (2020-21)
    udxr-rcgh (2021-22)  en47-vkkk (2022-23)  9whd-sig6 (2023-24)

WHY THIS LAYER IS STILL AS FILED — MEASURED, NOT ASSUMED.

Every other layer refuses to publish unless each entity-year reproduces
an independently published control total. This layer does not, and the
reason has been re-measured (V21 follow-up, 2026-07-25). The earlier
wording — "no control-total dataset exists for special districts" — was
WRONG, and is corrected here and everywhere it appeared.

WHAT SCO ACTUALLY PUBLISHES. The Financial Transactions Report raw
workbooks (Socrata blobby view dp5e-7wm8) carry, on sheet
"16 SD_GOV_FUNDS_REV_EXP", a per-filer TOTAL GOVERNMENTAL FUNDS column
for both revenues and expenditures. That is a real control and it is the
same accounting object as this layer's `gov` bucket.

WHY THE LAYER STILL CANNOT BE GATED AS A WHOLE. Of the four buckets this
page publishes, only `gov` has such a control:

  gov  published total exists (sheet 16, plus sheet 15 for the
       Transportation filers, so it is a cross-sheet sum)
  ent  NO published total. Each of the ten enterprise sheets prints
       "Total Operating Expenses" and "Total Nonoperating Expenses" as
       two SEPARATE columns — 22 columns across 11 sheets — and never
       their sum. Gating against a figure we add up ourselves is not a
       gate, it is our own arithmetic wearing a gate's clothes. The unit
       differs too: accrual expenses including depreciation, not
       modified-accrual expenditures.
  isf  NO published total, same shape, and only 19 entities — too thin
       to call tested either way.
  cf   NO published total, and this one is a trap. Reconciling the
       site's cf bucket against sheet 14 alone passes 14/14 — but only
       because the site's bucket is conduit-financing-only while SCO
       also declares FIDUCIARY-FUND activity on sheet 15 that the
       Socrata feed never publishes at all. See FIDUCIARY_GAP below: a
       cf gate defined to pass is a gate defined around the hole.

TWO MORE REASONS ANY FUTURE GATE MUST BE BUILT CAREFULLY, both measured:
201 of 7,158 governmental control cells are the literal STRING "NULL" —
not blank, not zero — so a gate that coerces them to 0.0 would pass
silently on cells where nothing was published; and the control is
per-ROW, not per-entity (293 entity-years carry 2 to 7 rows), so an
entity-level control is itself a sum the reader has to trust us to make.

So: figures are still published as filed and labeled so. What changed is
that the label now states a measured limit instead of an absence that
was never true.

WHAT IS STILL GATED (structurally, in this script):
  - slug uniqueness across the directory (write fails on collision);
  - every fiscal year in the window present for both datasets;
  - every delinquency-list row either matched to a filer or carried
    into the directory as an unmatched "Failed to File" entry —
    truncated names (the lists cut names at ~40 characters) are
    matched by normalized prefix + county and NEVER guessed: ambiguous
    or unmatched "Filed Late" rows are counted and reported in
    meta.finding.matching rather than attached to a district.

FINDING FIGURES ARE COMPUTED HERE, NOT COPIED. Everything the finding
page states — expected filers, late and failed-to-file counts per
year, district counts by legal type, the largest activity types, the
enterprise share of as-filed dollars — is recomputed from the live
API on every run and stored in meta.finding. districts.html renders
those values; it hardcodes none of them (test-asserted).

NO POPULATION FIELD EXISTS IN THE OUTPUT, on purpose. Special
districts have no resident denominator — they serve connections,
parcels, service areas. Any per-resident figure would be fabricated,
so the data file refuses to carry the ingredient.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates                                     # noqa: E402
from integrity import stamp  # noqa: E402
import revisions  # noqa: E402

# THE FIDUCIARY GAP, DECLARED PER ENTITY-YEAR.
#
# SCO's own Financial Transactions Report workbook (Socrata blobby view
# dp5e-7wm8, sheet "15 SD_TRANSPORTATION", column "Total Expenditures/
# Operating Expenses/Deductions_Fiduciary Fund") declares fiduciary-fund
# activity for a handful of transportation filers. THE SOCRATA FEED THIS
# PIPELINE READS PUBLISHES NONE OF IT: measured, m9u3-wdam contains zero
# rows with "Fiduciary" in category, subcategory1, subcategory2 or
# linedescription, in any year.
#
# So those districts' figures on this site are UNDERSTATED, and by a lot:
# Western Riverside COG's whole published FY2024 expenditure is
# $13,532,565 while the workbook declares $385,428,678 of fiduciary
# deductions beside it. That is not a reconciliation failure — there is
# nothing on the Socrata side to fail — it is a hole in what SCO makes
# available through the feed, and the affected records say so on their
# face rather than showing a small number without comment.
#
# DECLARED, never sniffed: read from the workbook by hand, stated here,
# and asserted against the roster on every run. Amounts are whole dollars
# as the workbook prints them.
FIDUCIARY_GAP = {
    ("Western Riverside Council of Governments", "Riverside"): {
        "2022-23": 122253037, "2023-24": 385428678},
    ("Santa Clara Valley Transportation Authority", "Santa Clara"): {
        "2022-23": 71169000, "2023-24": 72360000},
    ("Fresno County Transportation Authority", "Fresno"): {
        "2022-23": 67677678, "2023-24": 63417754},
    ("Madera County Transportation Authority", "Madera"): {
        "2022-23": 8114034, "2023-24": 8150678},
}
# THE SCO MISLABEL — this project's own hazard, inverted.
#
# fetch_amounts() records a real hazard: "Rural North Vacaville Water
# District" resolves to TWO agencies, a Solano community-services district
# and a Sutter levee district, and grouping by name alone silently added
# them together. Keying on (name, county) fixed that.
#
# The Sutter agency is not called that at all. Measured: SCO publishes
# Levee District No. 9 (Sutter) — Entity ID 4599, Yuba City — for FY2003
# through FY2017 and again FY2021 through FY2024, and publishes nothing
# for it in FY2018, FY2019, FY2020. In exactly those three years, and only
# those, a "Rural North Vacaville Water District" appears in SUTTER county
# with activity "Levee" and a Yuba City address, 100 miles from Vacaville.
# The two series are exactly complementary and never overlap, and of all
# 68 Sutter filers LD9 is the only one with a hole in those years.
#
# So the name in the Socrata feed is SCO's own error, and the Entity ID —
# which the feed does not expose — is the truth. The Ledger keeps the
# name as filed, because that is what the record says, and states the
# correction on the record rather than silently renaming an entity on the
# strength of its own inference.
MISLABELS = {
    ("Rural North Vacaville Water District", "Sutter"): {
        "years": ["2018-19", "2019-20"],
        "trueName": "Levee District No. 9 (Sutter)",
        "entityId": "4599",
        "note": "The State Controller published this district's filings for "
                "these years under the wrong name. Entity ID 4599 is Levee "
                "District No. 9 (Sutter), of Yuba City; the Controller's own "
                "series for that district stops and resumes exactly around "
                "these years, and no other Sutter filer has such a gap. The "
                "name here is left as the Controller filed it, and the "
                "correction is stated rather than applied \u2014 a name is "
                "evidence, and the Ledger does not quietly rewrite it. Not to "
                "be confused with the Solano County community services "
                "district that genuinely bears this name.",
    },
}

FIDUCIARY_GAP_SOURCE = ("California State Controller, Financial Transactions "
                        "Report raw workbook (Socrata view dp5e-7wm8), sheet "
                        "\u201c15 SD_TRANSPORTATION\u201d, column \u201cTotal "
                        "Expenditures/Operating Expenses/Deductions_Fiduciary "
                        "Fund\u201d.")

BASE = "https://bythenumbers.sco.ca.gov/resource"
EXP, REV = "m9u3-wdam", "nkv3-m73r"
DELINQUENCY = {  # fiscal year label -> dataset id (only years SCO published)
    "2018-19": "uiun-snc7",
    "2019-20": "rbwh-942r",
    "2020-21": "fbdc-d5ib",
    "2021-22": "udxr-rcgh",
    "2022-23": "en47-vkkk",
    "2023-24": "9whd-sig6",
}
# SODA fiscalyear value -> Ledger fiscal-year label (same window as the
# city and county layers)
YEARS = {str(y): f"{y - 1}-{str(y)[-2:]}" for y in range(2017, 2025)}
YEAR_LABELS = [YEARS[k] for k in sorted(YEARS)]

ENTERPRISE_CATS = {
    "Airport Enterprise Fund", "Electric Enterprise Fund",
    "Gas Enterprise Fund", "Harbor and Port Enterprise Fund",
    "Hospital Enterprise Fund", "Other Enterprise Fund",
    "Sewer Enterprise Fund", "Solid Waste Enterprise Fund",
    "Transit Enterprise Fund", "Water Enterprise Fund",
}
GOV_CAT = "Governmental Funds"
ISF_CAT = "Internal Service Fund"
CONDUIT_CAT = "Conduit Financing"
# "Transportation" rows carry the fund in subcategory: split there.
TRANSPORT_CAT = "Transportation"

OUT_PATH = Path(__file__).resolve().parent.parent / "district-data.js"


def soda(dataset, **params):
    rows, offset = [], 0
    while True:
        p = dict(params)
        p.setdefault("$limit", 50000)
        p["$offset"] = offset
        url = f"{BASE}/{dataset}.json?" + urllib.parse.urlencode(p)
        req = urllib.request.Request(
            url, headers={"User-Agent": "ca-ledger-pipeline/1.0"})
        page = json.loads(urllib.request.urlopen(req, timeout=300).read())
        rows.extend(page)
        if len(page) < int(p["$limit"]):
            return rows
        offset += len(page)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def classify(category, subcat):
    """Return one of gov / ent / isf / cf, or None to skip."""
    c = re.sub(r"\s+", " ", category).strip()
    if c in ENTERPRISE_CATS:
        return "ent"
    if c == GOV_CAT:
        return "gov"
    if c == ISF_CAT:
        return "isf"
    if c == CONDUIT_CAT:
        return "cf"
    if c == TRANSPORT_CAT:
        s = re.sub(r"\s+", " ", subcat or "").strip()
        if "Enterprise" in s:
            return "ent"
        if "Governmental" in s:
            return "gov"
        return "ent"  # transit filings; residue is enterprise-form
    raise SystemExit(f"UNMAPPED CATEGORY {category!r} — refusing to guess")


def fetch_amounts(dataset, name_f, year_f, cat_f, sub_f, val_f):
    """(entity, county) -> year label -> {gov, ent, isf, cf} as filed.

    KEYED ON THE SAME PAIR THE DIRECTORY GROUPS ON. Grouping these by
    name alone silently ADDED two independent agencies that share a
    name: measured, "Rural North Vacaville Water District" is both a
    Solano community-services district and a Sutter LEVEE district, and
    the shipped FY 2017-18 figure was $1,268,460 — the arithmetic sum of
    $1,101,223 and $167,237. No totals gate could see it; the money was
    all present, attributed to one entity instead of two."""
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    where = f"{year_f} >= '2017' and {year_f} <= '2024'"
    rows = soda(dataset, **{
        "$select": f"{name_f} as n, county as co, {year_f} as y, "
                   f"{cat_f} as c, sum({val_f}) as v",
        "$where": f"{where} and {cat_f} != '{TRANSPORT_CAT}'",
        "$group": f"{name_f}, county, {year_f}, {cat_f}"})
    collapse = lambda s: re.sub(r"\s+", " ", s).strip()
    ident = lambda r: (collapse(r["n"]), (r.get("co") or "").strip().lower())
    for r in rows:
        out[ident(r)][YEARS[r["y"]]][classify(r["c"], None)] += float(r["v"] or 0)
    rows = soda(dataset, **{
        "$select": f"{name_f} as n, county as co, {year_f} as y, "
                   f"{sub_f} as s, sum({val_f}) as v",
        "$where": f"{where} and {cat_f} = '{TRANSPORT_CAT}'",
        "$group": f"{name_f}, county, {year_f}, {sub_f}"})
    for r in rows:
        out[ident(r)][YEARS[r["y"]]][classify(TRANSPORT_CAT, r.get("s"))] += float(r["v"] or 0)
    return out


def main():
    ap = argparse.ArgumentParser(description="Rebuild district-data.js")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    # The two datasets do not cover the same universe: some districts
    # file only revenue line items, some only expenditures (measured:
    # ~60 revenue-only, ~16 expenditure-only in this window). The
    # directory is the union of both.
    print("Fetching directory attributes…", file=sys.stderr)
    attr_rows = soda(EXP, **{
        "$select": "entityname as n, fiscalyear as y, county as c, "
                   "activity as a, districttype2 as t, count(*)",
        "$where": "fiscalyear >= '2017' and fiscalyear <= '2024'",
        "$group": "entityname, fiscalyear, county, activity, districttype2"})
    attr_rows += soda(REV, **{
        "$select": "entity_name as n, fiscal_year as y, county as c, "
                   "activity as a, district_type as t, count(*)",
        "$where": "fiscal_year >= '2017' and fiscal_year <= '2024'",
        "$group": "entity_name, fiscal_year, county, activity, district_type"})

    print("Fetching as-filed expenditures…", file=sys.stderr)
    exp = fetch_amounts(EXP, "entityname", "fiscalyear",
                        "category", "subcategory2", "value")
    print("Fetching as-filed revenues…", file=sys.stderr)
    rev = fetch_amounts(REV, "entity_name", "fiscal_year",
                        "category", "subcategory_2", "value")

    # ---- directory: latest-year attributes; FY 2020-21 filings carry
    # no district type ("All Special Districts"), so type falls back to
    # the nearest year that states one.
    #
    # Name variants: some districts are spelled differently across
    # vintages (e.g. "Antelope Valley - East Kern…" in FY 2016-17,
    # "Antelope Valley-East Kern…" after). Spellings are merged ONLY
    # when they are identical after punctuation/whitespace
    # normalization AND in the same county AND never co-occur in a
    # fiscal year — that is a re-spelling, not a resolution guess. The
    # canonical name is the most recent spelling; the others are kept
    # in nameVariants. Anything stronger than that (abbreviations,
    # word changes) is NOT merged, per the V4 entity-resolution
    # finding. Overlapping years under one normalized name stop the
    # write: that would be two distinct filers we cannot tell apart.
    groups = {}
    for r in sorted(attr_rows, key=lambda r: r["y"]):
        name = re.sub(r"\s+", " ", r["n"]).strip()
        county = (r.get("c") or "").strip()
        key = (norm(name), county.lower())
        e = groups.setdefault(key, {"county": county, "activity": None,
                                    "type": None, "filedYears": set(),
                                    "names": {}, "yearsOfName": defaultdict(set)})
        y = YEARS[r["y"]]
        e["filedYears"].add(y)
        e["names"][name] = r["y"]          # latest SODA year seen per spelling
        e["yearsOfName"][name].add(y)
        e["activity"] = (r.get("a") or "").strip() or e["activity"]
        t = (r.get("t") or "").strip()
        if t and t != "All Special Districts":
            e["type"] = t
    merged_variants = 0
    ents = {}
    for (nk, ck), e in groups.items():
        if len(e["names"]) > 1:
            years_seen = set()
            for n2, ys in e["yearsOfName"].items():
                if years_seen & ys:
                    raise SystemExit(
                        "NAME VARIANTS CO-OCCUR IN ONE YEAR — cannot "
                        f"distinguish two filers under {sorted(e['names'])!r} "
                        f"({e['county']}); nothing written")
                years_seen |= ys
            merged_variants += len(e["names"]) - 1
        canonical = max(e["names"], key=lambda n2: e["names"][n2])
        # KEYED ON (name, county) — THE SAME PAIR THE GROUPING ABOVE USES.
        # Writing to ents[canonical] grouped correctly and then stored on a
        # subset of the key, so two districts differing only by county
        # collided and the second silently overwrote the first. The
        # aggregation was right, which is what made it invisible.
        ident = (canonical, (e["county"] or "").strip().lower())
        if ident in ents:
            raise SystemExit(
                f"ENTITY KEY COLLISION {ident!r} — two groups resolve to one "
                "directory key; nothing written")
        ents[ident] = {
            "name": canonical,
            "county": e["county"], "activity": e["activity"],
            "type": e["type"], "filedYears": e["filedYears"],
            "variants": sorted(n2 for n2 in e["names"] if n2 != canonical),
        }

    # re-key amounts by canonical spelling (variant years are disjoint,
    # so this is a union, not an addition across filers)
    for (canonical, ckey), e in ents.items():
        for v in e["variants"]:
            for src in (exp, rev):
                if (v, ckey) in src:
                    for y, vals in src.pop((v, ckey)).items():
                        for k, amt in vals.items():
                            src[(canonical, ckey)][y][k] += amt

    # ---- delinquency lists: normalized-prefix + county matching,
    # counted honestly, never guessed.
    by_norm_county = defaultdict(list)
    for ident, e in ents.items():
        by_norm_county[(e["county"] or "").lower()].append((norm(ident[0]), ident))
    late = defaultdict(dict)          # name -> {year label: "L"|"M"}
    matching = {"lateMatched": 0, "lateStandalone": 0, "lateAmbiguous": 0,
                "failedMatched": 0, "failedStandalone": 0,
                "respellingsMerged": merged_variants}
    standalone = {}                   # unmatched Failed-to-File rows
    per_year_lists = {}
    for fy, ds in DELINQUENCY.items():
        rows = soda(ds)
        per_year_lists[fy] = {
            "late": sum(1 for r in rows if r["status"] == "Filed Late"),
            "failed": sum(1 for r in rows if r["status"] == "Failed to File")}
        for r in rows:
            nm, county = r["special_district"].strip(), r["county"].strip()
            key = norm(nm)
            cands = [ident for n, ident in by_norm_county[county.lower()]
                     if n.startswith(key)]
            exact = [c for c in cands if norm(c[0]) == key]
            target = exact[0] if len(exact) == 1 else (
                cands[0] if len(cands) == 1 else None)
            code = "L" if r["status"] == "Filed Late" else "M"
            if target:
                late[target][fy] = code
                matching["lateMatched" if code == "L" else "failedMatched"] += 1
            elif len(cands) > 1:
                matching["lateAmbiguous"] += 1
            else:
                # no line items in either dataset for any window year:
                # a no-activity filing (late) or a genuinely absent one
                # (failed to file). Carried into the directory under the
                # name exactly as SCO printed it.
                st = standalone.setdefault(nm + "|" + county, {
                    "name": nm, "county": county, "years": {}})
                st["years"][fy] = code
                matching["failedStandalone" if code == "M"
                         else "lateStandalone"] += 1

    # ---- assemble districts
    districts = {}
    def add(slug, entry):
        if slug in districts:
            raise SystemExit(f"SLUG COLLISION {slug!r} — nothing written")
        districts[slug] = entry

    taken = set()
    # sorted on the WHOLE identity, so which of two same-named districts
    # takes the bare slug is deterministic rather than a property of dict
    # ordering
    for ident in sorted(ents, key=lambda i: (i[0].lower(), i[1])):
        name, _ck = ident
        e = ents[ident]
        slug = slugify(name)
        if slug in taken:                      # same name, different county
            slug = slugify(name + "-" + (e["county"] or "x"))
        taken.add(slug)
        f = "".join(
            (late.get(ident, {}).get(y) or
             ("F" if y in e["filedYears"] else "-"))
            for y in YEAR_LABELS)
        def series(src, keys, _id=ident):
            byy = src.get(_id, {})
            return [[round(byy[y].get(k, 0)) for k in keys]
                    if y in byy else None for y in YEAR_LABELS]
        entry = {
            "name": name,
            "county": e["county"] or "",
            "activity": e["activity"] or "",
            "type": e["type"] or "Not stated in filings",
            "filings": f,
            "exp": series(exp, ("gov", "ent", "isf", "cf")),
            "rev": series(rev, ("gov", "ent", "isf", "cf")),
        }
        if e["variants"]:
            entry["nameVariants"] = e["variants"]
        add(slug, entry)
    for st in standalone.values():
        slug = slugify(st["name"] + "-" + st["county"]) + "-list-only"
        add(slug, {
            "name": st["name"], "county": st["county"],
            "activity": "", "type": "Not stated in filings",
            "filings": "".join(st["years"].get(y, "-") for y in YEAR_LABELS),
            "exp": [None] * len(YEAR_LABELS),
            "rev": [None] * len(YEAR_LABELS),
            "listOnly": True,
        })

    # ---- the finding, computed live
    latest = YEAR_LABELS[-1]
    latest_soda = "2024"
    filers_by_year = defaultdict(int)
    for e in ents.values():
        for y in e["filedYears"]:
            filers_by_year[y] += 1
    type_counts = defaultdict(int)
    activity_counts = defaultdict(int)
    dollars = defaultdict(float)
    rev_dollars = defaultdict(float)
    for ident, e in ents.items():
        if latest not in e["filedYears"]:
            continue
        type_counts[e["type"] or "Not stated in filings"] += 1
        activity_counts[e["activity"] or "(none stated)"] += 1
        for k, v in exp.get(ident, {}).get(latest, {}).items():
            dollars[k] += v
        for k, v in rev.get(ident, {}).get(latest, {}).items():
            rev_dollars[k] += v
    filed_latest = filers_by_year[latest]
    failed_latest = per_year_lists[latest]["failed"]
    # expected filers = every district with latest-year rows, plus every
    # entry on SCO's latest failed-to-file list that did NOT end up
    # filing for that year (matched-but-unfiled or matched nothing)
    failed_not_filed = sum(
        1 for ident, ys in late.items()
        if ys.get(latest) == "M" and latest not in ents[ident]["filedYears"])
    failed_not_filed += sum(1 for st in standalone.values()
                            if latest in st["years"])
    finding = {
        "year": latest,
        "filed": filed_latest,
        "failedToFile": failed_latest,
        "filedLate": per_year_lists[latest]["late"],
        "expectedFilers": filed_latest + failed_not_filed,
        "lateOrMissing": per_year_lists[latest]["late"] + failed_latest,
        "typeCounts": dict(sorted(type_counts.items(),
                                  key=lambda kv: -kv[1])),
        "dependentCount": type_counts.get("Dependent", 0),
        "topActivities": sorted(activity_counts.items(),
                                key=lambda kv: -kv[1])[:6],
        "enterpriseShareExp": round(
            dollars["ent"] / (dollars["ent"] + dollars["gov"]), 4),
        "enterpriseShareRev": round(
            rev_dollars["ent"] / (rev_dollars["ent"] + rev_dollars["gov"]), 4),
        "filersByYear": {y: filers_by_year[y] for y in YEAR_LABELS},
        "listsByYear": per_year_lists,
        "matching": matching,
        "method": {
            "filed": "count of distinct districts with line items in "
                     f"either {EXP} or {REV} for the fiscal year "
                     "(the two datasets do not cover identical "
                     "universes; the directory is their union)",
            "listOnly": "districts on an SCO late/failed list with no "
                     "line items in either dataset in any window year — "
                     "shown in the directory as SCO printed them, with "
                     "no figures",
            "expectedFilers": "filed + list entries for the year that "
                              "have no line items in the datasets: "
                              "no-activity late filers and every "
                              "Failed-to-File entry",
            "enterpriseShare": "sum of as-filed enterprise-fund dollars ÷ "
                               "(enterprise + governmental), FY "
                               f"{latest}, {EXP}/{REV}; internal service "
                               "and conduit excluded from both sides",
            "types": "districttype2 as stated in each district's most "
                     "recent filing that states one (the FY 2020-21 "
                     "vintage states none)",
            "delinquencyNameMatching": "SCO's late/failed lists truncate "
                     "names at ~40 characters; matched by normalized "
                     "prefix + county, ambiguous rows counted here and "
                     "never attached to a district",
        },
    }

    # AN ENTITY FLOOR. This is a NEW guard, not a moved one: the district
    # layer had none, while both its siblings did. The shape gate below
    # cannot stand in for it — it sums over districts.values(), so it
    # fires on an EMPTY roster but passes on a truncated one. Five
    # districts with nonzero governmental and enterprise buckets satisfy
    # it exactly as 5,241 do.
    gates.require_rows(len(districts), 4000, "special districts loaded",
                       "SCO publishes upward of five thousand.")

    # ---- attach the declared fiduciary gap, and ASSERT it lands.
    # A declaration that matches nothing is a declaration describing some
    # other build (docs/OPEN.md 2d, the dormant-declaration failure), so a
    # key that finds no district stops the write rather than sitting
    # quietly in the file forever.
    for (nm, county), info in MISLABELS.items():
        hit = [r for r in districts.values()
               if r["name"] == nm and r.get("county") == county]
        if not hit:
            raise SystemExit(
                f"MISLABELS declares {nm} ({county}) but no such district is "
                "in the roster; nothing written")
        hit[0]["mislabel"] = dict(info)

    for (nm, county), by_year in FIDUCIARY_GAP.items():
        hit = [r for r in districts.values()
               if r["name"] == nm and r.get("county") == county]
        if not hit:
            raise SystemExit(
                f"FIDUCIARY_GAP declares {nm} ({county}) but no such district "
                "is in the roster — the declaration is stale or the name "
                "changed at the source; nothing written")
        bad = [fy for fy in by_year if fy not in YEAR_LABELS]
        if bad:
            raise SystemExit(f"FIDUCIARY_GAP {nm}: year(s) {bad} outside the "
                             "published window; nothing written")
        hit[0]["fiduciaryGap"] = dict(by_year)

    # THE CLASSIFICATION-SHAPE GATE (hard): statewide, governmental and
    # enterprise buckets must both be nonzero in every year (unknown
    # categories already stop the write via classify()).
    for fy_l in YEAR_LABELS:
        iy = YEAR_LABELS.index(fy_l)
        gov = sum((r["exp"][iy] or [0, 0, 0, 0])[0] for r in districts.values())
        ent = sum((r["exp"][iy] or [0, 0, 0, 0])[1] for r in districts.values())
        if gov <= 0 or ent <= 0:
            raise SystemExit(f"SHAPE FY {fy_l}: statewide gov=${gov:,.0f} "
                             f"ent=${ent:,.0f} — classification broke; "
                             "nothing written")

    payload = {
        "meta": {
            "source": "bythenumbers.sco.ca.gov",
            "sourceLabel": "California State Controller — special "
                           "districts financial transactions reports, "
                           "as filed",
            # WHAT A CONTROL WOULD LOOK LIKE, measured 2026-07-25, so the
            # tier statement on the page is renderable from data rather
            # than written into the markup.
            "control": {
                "govBucketHasPublishedTotal": True,
                "otherBucketsHavePublishedTotal": False,
                "where": "State Controller Financial Transactions Report raw "
                         "workbook (Socrata view dp5e-7wm8), sheet "
                         "\u201c16 SD_GOV_FUNDS_REV_EXP\u201d.",
                "whyNotGated": "For enterprise, internal-service and "
                               "conduit-financing funds the Controller "
                               "publishes operating and nonoperating "
                               "components and never their sum, so three of "
                               "the four buckets on this page have no "
                               "published total. Gating only the fourth "
                               "would put two evidentiary tiers inside one "
                               "row of figures; the Ledger has not done that "
                               "here.",
                "nullControlCells": 201,
                "nullControlCellsOf": 7158,
                "nullNote": "201 of the 7,158 governmental control cells are "
                            "the literal string \u201cNULL\u201d \u2014 not "
                            "blank and not zero. Any future gate must abstain "
                            "on those rather than read them as $0.",
            },
            "fiduciaryGapSource": FIDUCIARY_GAP_SOURCE,
            "datasets": {"expenditures": EXP, "revenues": REV,
                         "lateOrFailedLists": DELINQUENCY},
            "basis": "REPORTED AS FILED — UNRECONCILED. Three of the "
                     "four fund-class buckets on this page have no "
                     "published total to check against: for enterprise, "
                     "internal-service and conduit funds the State "
                     "Controller publishes operating and nonoperating "
                     "components and never their sum. A control DOES "
                     "exist for the governmental-funds bucket, in the "
                     "Controller's own Financial Transactions Report "
                     "workbook, and the Ledger does not yet gate on it. "
                     "So no figure in this file has been verified "
                     "against an independently published total.",
            "units": "as-filed dollars",
            "generated": date.today().isoformat(),
            "noPopulationByDesign": "special districts have no resident "
                     "denominator; this file carries no population field "
                     "so no per-resident figure can be computed from it",
            "boundaries": "no statewide special-district boundary file "
                     "is published by the Census Bureau or the State of "
                     "California; this layer ships without a map rather "
                     "than approximating",
            "scoExplorerPattern": "https://districts.bythenumbers.sco."
                     "ca.gov/#!/year/{yyyy}/operating/0/entityname/"
                     "{encoded name}/0/districttype2?vis=barChart",
            "finding": finding,
        },
        "years": YEAR_LABELS,
        "delinquencyYears": sorted(DELINQUENCY),
        "districts": districts,
    }
    prev = revisions.previous_payload(OUT_PATH)
    stamp(payload)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"{len(districts):,} districts ({len(standalone)} on SCO lists "
          f"with no line items in either dataset) · {len(YEAR_LABELS)} "
          f"years · payload ≈ {len(body) / 1048576:.2f} MB", file=sys.stderr)
    print("finding:", json.dumps({k: finding[k] for k in
          ("year", "filed", "expectedFilers", "filedLate", "failedToFile",
           "dependentCount", "enterpriseShareExp")}), file=sys.stderr)
    print("matching:", json.dumps(matching), file=sys.stderr)
    if not args.write:
        print("Dry run — nothing written. Use --write.", file=sys.stderr)
        return
    header = ("/* GENERATED by pipeline/fetch_district_data.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(header + "window.CA_DISTRICT_DATA = " + body + ";\n",
                        encoding="utf-8")

    revisions.record_revision('district', prev, payload,
                              source_signal=revisions.socrata_updated(
                                  ["m9u3-wdam","nkv3-m73r","uiun-snc7","rbwh-942r","fbdc-d5ib","udxr-rcgh","en47-vkkk","9whd-sig6"]))
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1048576:.2f} MB)")


if __name__ == "__main__":
    main()
