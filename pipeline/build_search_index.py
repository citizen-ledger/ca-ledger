#!/usr/bin/env python3
"""
Citizen Ledger — the cross-layer search index.

Builds ../search-index.js from the data files already shipped. It adds
NO new data: every name, identifier and flag in the index is copied from
a file the site already publishes, and the index is rebuilt from those
files rather than maintained by hand.

WHY THE INDEX CARRIES A BASIS AND A DAGGER COUNT, NOT A FIGURE:

  Somebody who types "Fresno" gets a city, a county, school districts and
  a community-college district. Those governments spend on overlapping
  populations, with different responsibilities, measured on different
  accounting bases. Putting four numbers next to each other in one list
  invites exactly the arithmetic the rest of this site refuses — adding
  them, or reading one as larger than another.

  So the index deliberately carries no figure at all. A result names an
  entity, names its layer, names the basis that layer is measured on,
  and says whether that entity carries comparability notes in its own
  layer. To see a number you follow the link into the layer, where the
  figure appears with its own caveats attached. The search box is a way
  in, never a comparison.

THE DAGGER COUNT is a count, not a verdict. It says "this entity has
notes you should read", which is the honest thing a search result can
say about a record it is not showing. Every flag counted here is one the
layer itself already publishes and already displays:

  cities        the Controller's services checklist records police or
                fire delivered other than by paid city employees, so
                some of that spending sits in another government's
                record (the rule cities.html itself uses: any code that
                is not A or B)
  K-12          basic aid, small-district necessary-small-school
                funding, sponsored charter ADA, commingled charters
  community     multi-college district, basic aid, noncredit-heavy, no
    colleges    apportionment
  UC            medical centre, health-sciences-only, research-intensive,
                small-scale
  special       the whole layer is as-filed and unreconciled, which the
    districts   layer states on every record rather than per entity

Usage:
    python3 pipeline/build_search_index.py            # dry run
    python3 pipeline/build_search_index.py --write
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "search-index.js"


def load_data_js(path):
    text = Path(path).read_text(encoding="utf-8")
    i = text.find("=")
    return json.loads(text[i + 1:].strip().rstrip(";"))


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


# Each layer's own words, shortened. `basis` is what a reader sees beside
# every result in that group; `full` is the sentence the layer itself
# publishes, carried so the page can show it without paraphrasing.
#
# `terms` exist only where the system's own published name differs from the
# entity names inside it — "University of California" is how uc-data.js's
# meta.sourceLabel names the system, while its campuses are published as
# "Berkeley", "Davis". Searching the system name is then a search for a
# name the source itself uses, not an alias this file invented.
LAYERS = [
    {"key": "state", "name": "State budget", "page": "index.html",
     "param": "a", "unit": "$ billions",
     "basis": "Enacted appropriations · Budgetary-Legal",
     "full": "Enacted state budgets on California's Budgetary-Legal basis "
             "(Department of Finance). These are appropriations, not actual "
             "expenditures."},
    {"key": "city", "name": "Cities", "page": "cities.html",
     "param": "c", "unit": "$ millions",
     "basis": "Reported actuals · city annual financial reports",
     "full": "Reported actual expenditures from each city's annual financial "
             "report to the State Controller; governmental activities only, "
             "with ratepayer-funded enterprise activities shown separately."},
    {"key": "county", "name": "Counties", "page": "cities.html",
     "param": "c", "extra": "l=county", "unit": "$ millions",
     "basis": "Reported actuals · county annual reports",
     "full": "Reported actual expenditures from each county's annual report "
             "to the State Controller. A county serves the whole county, "
             "including the residents of every city inside it."},
    {"key": "school", "name": "K-12 school districts", "page": "schools.html",
     "param": "c", "unit": "$ per ADA",
     "basis": "Unaudited actuals · SACS · Current Expense of Education",
     "full": "Unaudited actual expenditures as filed under SACS. District "
             "figures are the Current Expense of Education and reproduce "
             "CDE's published figure to the cent."},
    {"key": "coe", "name": "County offices of education", "page": "schools.html",
     "param": "c", "extra": "t=coes", "unit": "records only",
     "basis": "Unaudited actuals · SACS · records only, never compared",
     "full": "County offices run court and community schools, SELPAs and "
             "countywide services no district runs. CDE excludes them from "
             "its per-ADA statistic and so does the Ledger."},
    {"key": "charter", "name": "Charter schools", "page": "schools.html",
     "param": "c", "extra": "t=charters", "unit": "records only",
     "basis": "Unaudited actuals · SACS or Alternative Form · records only",
     "full": "Charters file three different ways and CDE excludes them from "
             "its per-ADA statistic. Each record states how the school filed."},
    {"key": "district", "name": "Special districts", "page": "districts.html",
     "param": "d", "unit": "as filed",
     "basis": "AS FILED · UNRECONCILED · no published control total exists",
     "full": "No control-total dataset exists for special districts, so no "
             "figure in this layer can be verified against an independently "
             "published total. It is published at a visibly different tier."},
    {"key": "ccc", "name": "Community college districts", "page": "ccc.html",
     "param": None, "unit": "$ per FTES",
     "terms": ["California Community Colleges", "community college"],
     "basis": "Modified accrual · CCFS-311 · Current Expense of Education",
     "full": "Modified-accrual spending on the community-college Budget and "
             "Accounting Manual chart, reconciled exactly to the Chancellor's "
             "Office printed statewide total."},
    {"key": "csu", "name": "CSU campuses", "page": "csu.html",
     "param": None, "unit": "$ per student",
     "terms": ["California State University", "Cal State"],
     "basis": "Audited GAAP / GASB full accrual",
     "full": "Audited GAAP accrual from CSU's systemwide financial "
             "statements. This is not the state budget's enacted basis and "
             "the two are never added."},
    {"key": "uc", "name": "UC campuses", "page": "uc.html",
     "param": None, "unit": "$ per student FTE",
     "terms": ["University of California"],
     "basis": "Audited GAAP / GASB · hospitals stripped on UC's own lines",
     "full": "Audited GAAP accrual, with medical centres, auxiliaries and the "
             "DOE laboratory stripped on UC's own published lines. Hospitals "
             "are stripped; medical schools are not."},
]
LAYER_IX = {l["key"]: i for i, l in enumerate(LAYERS)}


def city_daggers(rec):
    """The rule cities.html itself applies: a services-checklist code
    other than A (paid city employees) or B (city volunteers) means the
    service is delivered or financed outside the city budget."""
    n = 0
    for svc in (rec.get("services") or {}).values():
        code = svc.get("code")
        if code and code not in ("A", "B") and svc.get("label"):
            n += 1
    return n


def school_daggers(rec):
    kinds = set()
    for y in (rec.get("years") or {}).values():
        if y.get("basicAid"):
            kinds.add("basicAid")
        if y.get("smallNSS"):
            kinds.add("smallNSS")
        if y.get("commingledCharters"):
            kinds.add("commingled")
        if (y.get("sponsoredCharterADA") or 0) > 0:
            kinds.add("sponsoredCharter")
    return len(kinds)


def ccc_titlecase(s):
    """The CCFS-311 portal publishes district names in upper case; ccc.html
    title-cases them for display. The index must show a name the way its
    own page does, or a search result and the record disagree."""
    out = re.sub(r"\w[^\s\-/]*", lambda m: m.group(0)[0] + m.group(0)[1:].lower(), s)
    out = re.sub(r"\bCcd\b", "CCD", out, count=1)
    return re.sub(r"\bLa\b", "LA", out, count=1)


def flag_count(rec):
    f = rec.get("flags") or {}
    return sum(1 for v in f.values() if v)


def build():
    ents = []          # [name, layerIx, id, daggers, qualifier]

    def add(name, layer, ident, daggers=0, qual=""):
        if not name:
            return
        ents.append([name, LAYER_IX[layer], ident, daggers, qual])

    # ---- state: agencies and departments, from the latest budget year
    st = load_data_js(ROOT / "data.js")
    years = st["years"]
    latest = years[-1]
    seen = set()
    for fy in reversed(years):                      # newest first
        for a in st["budgets"][fy]["agencies"]:
            if ("agency", a["id"]) not in seen:
                seen.add(("agency", a["id"]))
                add(a["name"], "state", a["id"], 0,
                    "Agency" + ("" if fy == latest else f" · last in FY {fy}"))
            for d in a.get("departments") or []:
                key = ("dept", a["id"], d["code"])
                if key in seen:
                    continue
                seen.add(key)
                add(d["name"], "state", f'{a["id"]}|{d["code"]}', 0,
                    a["name"] + ("" if fy == latest else f" · last in FY {fy}"))

    # ---- cities and counties
    city = load_data_js(ROOT / "city-data.js")
    for slug, rec in city["cities"].items():
        add(rec["name"], "city", slug, city_daggers(rec),
            (rec.get("county") or "") + (" County" if rec.get("county") else ""))
    county = load_data_js(ROOT / "county-data.js")
    for slug, rec in county["counties"].items():
        add(rec["name"] + " County", "county", slug, 0, "")

    # ---- K-12
    sch = load_data_js(ROOT / "school-data.js")
    for slug, rec in sch["districts"].items():
        add(rec["name"], "school", slug, school_daggers(rec),
            f'{rec.get("county","")} County · {rec.get("type","")}'.strip(" ·"))
    for slug, rec in sch["countyOffices"].items():
        add(rec["name"], "coe", slug, 0, rec.get("county", "") + " County")
    for slug, rec in sch["charters"].items():
        add(rec["name"], "charter", slug, 0,
            f'{rec.get("county","")} County'
            + (f' · #{rec["charterNumber"]}' if rec.get("charterNumber") else ""))

    # ---- special districts
    dist = load_data_js(ROOT / "district-data.js")
    for slug, rec in dist["districts"].items():
        add(rec["name"], "district", slug, 0,
            f'{rec.get("county","")} County · {rec.get("activity","")}'.strip(" ·"))

    # ---- higher education (no per-entity permalink on these pages, so the
    # identifier is empty and the link goes to the layer's page)
    ccc = load_data_js(ROOT / "ccc-data.js")
    for d in ccc["districts"]:
        add(ccc_titlecase(d["name"]), "ccc", "", flag_count(d),
            f'{d.get("nColleges", 0)} college'
            + ("" if d.get("nColleges") == 1 else "s"))
    csu = load_data_js(ROOT / "csu-data.js")
    for c in csu["campuses"]:
        add(c["name"], "csu", "", 0, "")
    uc = load_data_js(ROOT / "uc-data.js")
    for c in uc["campuses"]:
        add(c["name"], "uc", "", flag_count(c), "")

    ents.sort(key=lambda r: (r[0].lower(), r[1]))

    # --- two lossless compressions, both verified before they are applied.
    # Most identifiers are just the slugified name, so they are stored empty
    # and rebuilt in the page. That is a derived identifier, which is the
    # exact fragility the 2026-07-19 slug work removed from the K-12
    # pipeline — so it is only allowed here on the entities where it round
    # trips EXACTLY, proven one by one, and the rest keep their id verbatim.
    derivable = 0
    for e in ents:
        if e[2] and e[2] == slugify(e[0]):
            e[2] = ""
            derivable += 1
    for e in ents:
        rebuilt = e[2] or slugify(e[0])
        assert rebuilt, f"empty identifier for {e[0]!r}"

    # qualifiers repeat heavily ("Fresno County · Unified"), so they are
    # interned; the page indexes back into this table.
    quals, qtable = {}, []
    for e in ents:
        if e[4]:
            if e[4] not in quals:
                quals[e[4]] = len(qtable)
                qtable.append(e[4])
            e[4] = quals[e[4]]
        else:
            e[4] = -1

    payload = {
        "meta": {
            "generated": date.today().isoformat(),
            "note": "Built from the data files this site already publishes. "
                    "Adds no data. Carries NO FIGURES, deliberately: results "
                    "from different layers are measured on different bases "
                    "and must never be added or compared.",
            "entities": len(ents),
            "fields": ["name", "layer", "id (empty = slugify(name))",
                       "notes", "qualifier index into q, -1 = none"],
            "derivedIds": derivable,
        },
        "layers": LAYERS,
        "q": qtable,
        "e": ents,
    }
    stamp(payload)
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    payload = build()
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    by_layer = {}
    for e in payload["e"]:
        by_layer[LAYERS[e[1]]["key"]] = by_layer.get(LAYERS[e[1]]["key"], 0) + 1
    print(f"{payload['meta']['entities']} entities across {len(LAYERS)} layers")
    for l in LAYERS:
        print(f"  {l['key']:9} {by_layer.get(l['key'], 0):5}")
    dag = sum(1 for e in payload["e"] if e[3])
    print(f"entities carrying comparability notes: {dag}")
    print(f"payload: {len(body.encode('utf-8')):,} B raw")
    if not args.write:
        print("Dry run — nothing written. Use --write.")
        return
    header = ("/* GENERATED by pipeline/build_search_index.py on "
              f"{date.today().isoformat()} from the shipped data files — do "
              "not edit by hand. Adds no data. Carries no figures: results "
              "from different layers are measured differently and are never "
              "compared or added. */\n")
    OUT_PATH.write_text(header + "window.CA_LEDGER_SEARCH = " + body + ";\n",
                        encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
