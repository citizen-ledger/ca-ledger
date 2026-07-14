#!/usr/bin/env python3
"""
Generate district-data.js — the special districts layer of the
California Ledger, built per the V5 finding, option (b): a finding, a
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

WHY THERE IS NO RECONCILIATION GATE HERE. Every other layer of the
Ledger refuses to publish unless each entity-year reproduces an
independently published control total (Schedule 6 for the state,
per-capita totals datasets for cities and counties). No such dataset
exists for special districts — there is nothing to reconcile against.
That absence is reported on the page itself; figures are published
as filed, and labeled so.

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
from integrity import stamp  # noqa: E402

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
    """entity -> year label -> {gov, ent, isf, cf} in as-filed dollars."""
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    where = f"{year_f} >= '2017' and {year_f} <= '2024'"
    rows = soda(dataset, **{
        "$select": f"{name_f} as n, {year_f} as y, {cat_f} as c, sum({val_f}) as v",
        "$where": f"{where} and {cat_f} != '{TRANSPORT_CAT}'",
        "$group": f"{name_f}, {year_f}, {cat_f}"})
    collapse = lambda s: re.sub(r"\s+", " ", s).strip()
    for r in rows:
        out[collapse(r["n"])][YEARS[r["y"]]][classify(r["c"], None)] += float(r["v"] or 0)
    rows = soda(dataset, **{
        "$select": f"{name_f} as n, {year_f} as y, {sub_f} as s, sum({val_f}) as v",
        "$where": f"{where} and {cat_f} = '{TRANSPORT_CAT}'",
        "$group": f"{name_f}, {year_f}, {sub_f}"})
    for r in rows:
        out[collapse(r["n"])][YEARS[r["y"]]][classify(TRANSPORT_CAT, r.get("s"))] += float(r["v"] or 0)
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
        ents[canonical] = {
            "county": e["county"], "activity": e["activity"],
            "type": e["type"], "filedYears": e["filedYears"],
            "variants": sorted(n2 for n2 in e["names"] if n2 != canonical),
        }

    # re-key amounts by canonical spelling (variant years are disjoint,
    # so this is a union, not an addition across filers)
    for canonical, e in ents.items():
        for v in e["variants"]:
            for src in (exp, rev):
                if v in src:
                    for y, vals in src.pop(v).items():
                        for k, amt in vals.items():
                            src[canonical][y][k] += amt

    # ---- delinquency lists: normalized-prefix + county matching,
    # counted honestly, never guessed.
    by_norm_county = defaultdict(list)
    for name, e in ents.items():
        by_norm_county[(e["county"] or "").lower()].append((norm(name), name))
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
            cands = [full for n, full in by_norm_county[county.lower()]
                     if n.startswith(key)]
            exact = [c for c in cands if norm(c) == key]
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
    for name in sorted(ents, key=lambda n: n.lower()):
        e = ents[name]
        slug = slugify(name)
        if slug in taken:                      # same name, different county
            slug = slugify(name + "-" + (e["county"] or "x"))
        taken.add(slug)
        f = "".join(
            (late.get(name, {}).get(y) or
             ("F" if y in e["filedYears"] else "-"))
            for y in YEAR_LABELS)
        def series(src, keys):
            byy = src.get(name, {})
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
    for name, e in ents.items():
        if latest not in e["filedYears"]:
            continue
        type_counts[e["type"] or "Not stated in filings"] += 1
        activity_counts[e["activity"] or "(none stated)"] += 1
        for k, v in exp.get(name, {}).get(latest, {}).items():
            dollars[k] += v
        for k, v in rev.get(name, {}).get(latest, {}).items():
            rev_dollars[k] += v
    filed_latest = filers_by_year[latest]
    failed_latest = per_year_lists[latest]["failed"]
    # expected filers = every district with latest-year rows, plus every
    # entry on SCO's latest failed-to-file list that did NOT end up
    # filing for that year (matched-but-unfiled or matched nothing)
    failed_not_filed = sum(
        1 for name, ys in late.items()
        if ys.get(latest) == "M" and latest not in ents[name]["filedYears"])
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

    payload = {
        "meta": {
            "source": "bythenumbers.sco.ca.gov",
            "sourceLabel": "California State Controller — special "
                           "districts financial transactions reports, "
                           "as filed",
            "datasets": {"expenditures": EXP, "revenues": REV,
                         "lateOrFailedLists": DELINQUENCY},
            "basis": "REPORTED AS FILED — UNRECONCILED. No control-total "
                     "dataset exists for special districts, so no figure "
                     "in this file can be verified against an "
                     "independently published total. This is the only "
                     "Ledger layer where the reconciliation gate is "
                     "structurally impossible.",
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
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1048576:.2f} MB)")


if __name__ == "__main__":
    main()
