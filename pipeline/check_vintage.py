#!/usr/bin/env python3
"""
Staleness check for the site's two manual-cache layers.

    python3 pipeline/check_vintage.py            # report, exit 0/1
    python3 pipeline/check_vintage.py --json     # machine-readable

WHY THIS EXISTS AS A SCHEDULED JOB RATHER THAN A TEST.

Two layers on this site cannot refresh themselves — CSU, whose audited
statements are bot-gated, and compensation, whose source expressly
excludes automated retrieval. Both therefore go stale silently: the page
keeps rendering, every figure stays exactly as published, and nothing
anywhere says the record has stopped being current. A test in the suite
catches that only when somebody runs the suite, which is precisely the
moment a forgotten layer is least likely to reach.

So staleness is checked on a schedule and announced twice:

  - to the MAINTAINER, by a GitHub Actions job that opens an issue
    (.github/workflows/vintage-check.yml);
  - to the READER, by the vintage band on each layer's own page, which
    computes the same age in the browser and turns conspicuous past the
    same threshold.

Staleness is a fact about the record, not only a maintenance task, so
the reader learns it at the same moment the maintainer does.

THIS SCRIPT NEVER FETCHES EITHER SOURCE. It reads dates already in the
repository. Fetching would defeat the point for compensation, whose
source excludes exactly this kind of automated access.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Declared per layer: the payload, where its vintage date lives, and how
# many months may pass before it is stale. The thresholds differ because
# the publication rhythms do: SCO publishes compensation once a year;
# CSU's audited statements land a few months after each fiscal year.
LAYERS = {
    "compensation": {
        "file": "compensation-data.js",
        "path": ("meta", "vintage", "latest"),
        "months": 14,
        "page": "compensation.html",
        "why": "gcc.sco.ca.gov expressly excludes automated retrieval "
               "(robots.txt names ClaudeBot, GPTBot and others)",
        "how": "download the reporting-year exports by hand from "
               "https://gcc.sco.ca.gov/Reports/RawExport.aspx into "
               "pipeline/cache/compensation/, then run "
               "python3 pipeline/fetch_compensation_data.py --write",
    },
    "csu": {
        "file": "csu-data.js",
        # meta.year, NOT meta.generated. `generated` is the day the
        # pipeline last ran, so checking it would measure our own
        # activity and never go stale while anyone rebuilt for any
        # reason — the layer could sit three years behind its source and
        # still report OK. `year` is the fiscal year of the audited
        # statements themselves, which is the thing that ages.
        "path": ("meta", "year"),
        "fiscalYear": True,
        "months": 30,
        "page": "csu.html",
        "why": "the CSU audited financial statements are bot-gated",
        "how": "download the audited statements by hand as "
               "pipeline/fetch_csu_data.py documents, then rebuild",
    },
}


def load(name):
    txt = (ROOT / name).read_text()
    i = txt.find("{")
    return json.loads(txt[i:txt.rfind("}") + 1])


def dig(obj, path):
    for k in path:
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def check(today=None):
    today = today or date.today()
    out = []
    for layer, cfg in LAYERS.items():
        f = ROOT / cfg["file"]
        if not f.exists():
            out.append({"layer": layer, "status": "missing",
                        "detail": f"{cfg['file']} not found"})
            continue
        raw = dig(load(cfg["file"]), cfg["path"])
        if not raw:
            out.append({"layer": layer, "status": "no-vintage",
                        "detail": f"{'.'.join(cfg['path'])} absent"})
            continue
        if cfg.get("fiscalYear"):
            fy = re.match(r"(\d{4})-(\d{2})$", str(raw).strip())
            if not fy:
                out.append({"layer": layer, "status": "unparseable",
                            "detail": str(raw)[:40]})
                continue
            # a California fiscal year ends 30 June of its second half
            raw = f"{int(fy.group(1)) + 1}-06-30"
        m = re.search(r"\d{4}-\d{2}-\d{2}", str(raw))
        if not m:
            out.append({"layer": layer, "status": "unparseable",
                        "detail": str(raw)[:40]})
            continue
        d = datetime.strptime(m.group(0), "%Y-%m-%d").date()
        age = (today - d).days
        limit = cfg["months"] * 31
        out.append({
            "layer": layer, "status": "stale" if age > limit else "current",
            "vintage": d.isoformat(), "ageDays": age, "limitDays": limit,
            "months": cfg["months"], "page": cfg["page"],
            "why": cfg["why"], "how": cfg["how"],
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = check()
    if args.json:
        print(json.dumps(res, indent=1))
    else:
        for r in res:
            if r["status"] == "current":
                print(f"OK    {r['layer']:14} vintage {r['vintage']} "
                      f"({r['ageDays']} days, limit {r['limitDays']})")
            elif r["status"] == "stale":
                print(f"STALE {r['layer']:14} vintage {r['vintage']} "
                      f"({r['ageDays']} days, limit {r['limitDays']})")
                print(f"      cannot self-refresh: {r['why']}")
                print(f"      to refresh: {r['how']}")
            else:
                print(f"ERROR {r['layer']:14} {r['status']}: {r.get('detail')}")
    bad = [r for r in res if r["status"] != "current"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
