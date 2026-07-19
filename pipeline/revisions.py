#!/usr/bin/env python3
"""
Citizen Ledger — the change record (V13, option (b): MECHANICAL ONLY).

Every refresh compares the payload it is about to write against the one
already shipped, per figure, and appends what moved to a per-layer
record. The record says THAT a figure changed and BY HOW MUCH. It never
says WHY.

WHY IT NEVER SAYS WHY — this is the design, not a gap:

  A changed figure has at least five possible causes: the source
  restated its own published data; the source redefined it; we fixed an
  extraction bug; we deliberately changed method or scope; or an
  upstream Ledger layer we consume was refreshed. Two of those are
  observationally identical — a restatement and a redefinition both
  look like "old code, new source, different number" — and telling them
  apart requires reading the source's release notes, which is a human
  act no amount of engineering removes. On the SCO layers it is worse
  than un-automatable: nothing caches the raw rows (the pipeline asks
  SCO to aggregate server-side), so once SCO revises, the prior figure
  cannot be reproduced by anyone, including us.

  docs/V13_CHANGEFEED_FINDING.md §3 works this through. The conclusion
  taken here is that a feed which guesses at cause would be exactly the
  kind of unearned claim the rest of this project exists to avoid, and
  that a per-refresh human labelling step would put friction on the one
  process that must stay frictionless — refreshing the data. So the
  record is mechanical, automatic, and silent about cause.

  The single exception is historical and explicitly hand-entered:
  BACKFILL below carries the FY2016-17 city classifier fix, where the
  cause is KNOWN rather than inferred because it is our own commit.
  Nothing in the refresh path can ever write a note; only this constant
  can.

WHAT COUNTS AS AN EVENT. Three kinds, all first-class:

  changed      a figure both builds carry, with different values
  appeared     a figure the new build carries and the old one did not
  disappeared  a figure the old build carried and the new one does not

  The last two matter more than they look. The one real correction in
  this project's history — the FY2016-17 city misclassification — moved
  $36B between keys that did not previously exist, and expressed as
  value-changes alone it is 31 events out of a 482-city correction.
  A feed that only reported changed values would systematically
  under-report exactly the class of error the totals gate cannot see.

IDENTITY. Every figure is keyed on the source's own stable code, never
on a display name or a slug that a rebuild could reassign — CDS for
K-12 districts and county offices, the MIS code for community-college
districts, agency id and department code for the state, the charter
number with name and county for charters. See the 2026-07-19 entry in
STATUS.md for what happens when that discipline is missing.

Usage:
    from revisions import record_revision
    record_revision("city", old_payload, new_payload, OUT_PATH)

    python3 pipeline/revisions.py --verify        # re-derive every record
    python3 pipeline/revisions.py --backfill      # (re)write the one
                                                  # known historical batch
"""

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# layer -> (data file, record file, window title)
LAYERS = {
    "state":    ("data.js",          "state-revisions.js",    "State budget"),
    "city":     ("city-data.js",     "city-revisions.js",     "Cities"),
    "county":   ("county-data.js",   "county-revisions.js",   "Counties"),
    "district": ("district-data.js", "district-revisions.js", "Special districts"),
    "school":   ("school-data.js",   "school-revisions.js",   "K-12 schools"),
    "csu":      ("csu-data.js",      "csu-revisions.js",      "CSU"),
    "ccc":      ("ccc-data.js",      "ccc-revisions.js",      "Community colleges"),
    "uc":       ("uc-data.js",       "uc-revisions.js",       "UC"),
}

GLOBAL_NAME = {"state": "CA_LEDGER_REVISIONS_STATE"}


# ---------------------------------------------------------------- payloads

def load_data_js(path):
    """Same slice-from-the-first-equals the site's own loader uses."""
    text = Path(path).read_text(encoding="utf-8")
    i = text.find("=")
    if i < 0:
        raise ValueError(f"{path}: no assignment found")
    return json.loads(text[i + 1:].strip().rstrip(";"))


def figures_digest(payload):
    """SHA-256 over the payload with the WHOLE meta block removed.

    Distinct from meta.integrity, which covers meta too and therefore
    moves when only the build date moves. This one answers the question
    the integrity digest cannot: did any figure actually change? Two
    builds on the same day with identical figures share this digest and
    differ in the other one — measured, and the reason detection here
    diffs figures rather than digests.
    """
    clean = copy.deepcopy(payload)
    clean.pop("meta", None)
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def pipeline_commit():
    """The commit the pipeline was at. Excludes 'we changed the method'
    from the causes a reader has to guess between, without asking a
    human anything."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10)
        if out.returncode:
            return None
        sha = out.stdout.strip()[:12]
        return sha + ("+dirty" if dirty.stdout.strip() else "")
    except Exception:
        return None


# ------------------------------------------------------------- flattening

def _leaves(obj, prefix, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _leaves(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _leaves(v, f"{prefix}.{i}" if prefix else str(i), out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = obj
    return out


def _entity(out, ident, label, years_obj):
    for path, val in _leaves(years_obj, "", {}).items():
        out[f"{ident}\t{path}"] = val
    if years_obj is not None:
        out.setdefault(f"{ident}\t__label__", None)


def flatten(layer, payload):
    """payload -> {stable_key: numeric value}. Keys are
    '<identity>\\t<figure path>'; the identity half is the source's own
    code, so a display-name change is not a figure change."""
    out = {}
    if layer == "state":
        for fy, tr in (payload.get("trend") or {}).items():
            for k, v in _leaves(tr, "", {}).items():
                out[f"statewide\t{fy}.{k}"] = v
        for fy, b in (payload.get("budgets") or {}).items():
            for a in b.get("agencies", []):
                aid = a.get("id")
                for k, v in _leaves({x: a[x] for x in a
                                     if x not in ("departments", "name", "id")},
                                    "", {}).items():
                    out[f"agency:{aid}\t{fy}.{k}"] = v
                for d in a.get("departments", []) or []:
                    code = d.get("code")
                    for k, v in _leaves({x: d[x] for x in d
                                         if x not in ("name", "code")},
                                        "", {}).items():
                        out[f"agency:{aid}/dept:{code}\t{fy}.{k}"] = v
    elif layer in ("city", "county"):
        coll = "cities" if layer == "city" else "counties"
        for slug, rec in (payload.get(coll) or {}).items():
            for k, v in _leaves(rec.get("years") or {}, "", {}).items():
                out[f"{slug}\t{k}"] = v
    elif layer == "district":
        years = payload.get("years") or []
        for slug, rec in (payload.get("districts") or {}).items():
            for field in ("exp", "rev"):
                for i, slot in enumerate(rec.get(field) or []):
                    fy = years[i] if i < len(years) else str(i)
                    if slot is None:
                        continue
                    for j, val in enumerate(slot):
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            out[f"{slug}\t{fy}.{field}.{j}"] = val
    elif layer == "school":
        for coll, idf in (("districts", "cds"), ("countyOffices", "cds")):
            for rec in (payload.get(coll) or {}).values():
                ident = f"{coll}:{rec.get(idf)}"
                for k, v in _leaves(rec.get("years") or {}, "", {}).items():
                    out[f"{ident}\t{k}"] = v
        for rec in (payload.get("charters") or {}).values():
            ident = ("charter:" + str(rec.get("charterNumber")) + "|"
                     + str(rec.get("name")) + "|" + str(rec.get("county")))
            for k, v in _leaves(rec.get("years") or {}, "", {}).items():
                out[f"{ident}\t{k}"] = v
    elif layer in ("csu", "uc"):
        top = "systemwide"
        for k, v in _leaves(payload.get(top) or {}, "", {}).items():
            out[f"systemwide\t{k}"] = v
        for c in payload.get("campuses") or []:
            ident = f"campus:{c.get('name')}"
            for k, v in _leaves({x: c[x] for x in c if x != "name"}, "", {}).items():
                out[f"{ident}\t{k}"] = v
    elif layer == "ccc":
        for k, v in _leaves(payload.get("statewide") or {}, "", {}).items():
            out[f"statewide\t{k}"] = v
        for d in payload.get("districts") or []:
            ident = f"district:{d.get('code')}"
            for k, v in _leaves({x: d[x] for x in d
                                 if x not in ("name", "code", "colleges")},
                                "", {}).items():
                out[f"{ident}\t{k}"] = v
    else:
        raise ValueError(f"unknown layer {layer!r}")
    return {k: v for k, v in out.items() if v is not None}


def labels(layer, payload):
    """identity -> the display name, so the record can name an entity
    without keying on the name."""
    out = {}
    if layer == "state":
        for b in (payload.get("budgets") or {}).values():
            for a in b.get("agencies", []):
                out[f"agency:{a.get('id')}"] = a.get("name")
                for d in a.get("departments", []) or []:
                    out[f"agency:{a.get('id')}/dept:{d.get('code')}"] = d.get("name")
        out["statewide"] = "Statewide total"
    elif layer in ("city", "county"):
        coll = "cities" if layer == "city" else "counties"
        for slug, rec in (payload.get(coll) or {}).items():
            out[slug] = rec.get("name")
    elif layer == "district":
        for slug, rec in (payload.get("districts") or {}).items():
            out[slug] = rec.get("name")
    elif layer == "school":
        for coll, idf in (("districts", "cds"), ("countyOffices", "cds")):
            for rec in (payload.get(coll) or {}).values():
                out[f"{coll}:{rec.get(idf)}"] = rec.get("name")
        for rec in (payload.get("charters") or {}).values():
            out["charter:" + str(rec.get("charterNumber")) + "|"
                + str(rec.get("name")) + "|" + str(rec.get("county"))] = rec.get("name")
    elif layer in ("csu", "uc"):
        out["systemwide"] = "Systemwide"
        for c in payload.get("campuses") or []:
            out[f"campus:{c.get('name')}"] = c.get("name")
    elif layer == "ccc":
        out["statewide"] = "Statewide"
        for d in payload.get("districts") or []:
            out[f"district:{d.get('code')}"] = d.get("name")
    return out


# ------------------------------------------------------------------ diff

def diff(old_flat, new_flat):
    """Three kinds of event, all first-class. Ordered for a stable file."""
    events = []
    for key in sorted(set(old_flat) | set(new_flat)):
        o, n = old_flat.get(key), new_flat.get(key)
        if o == n:
            continue
        ident, _, path = key.partition("\t")
        events.append({"e": ident, "k": path, "o": o, "n": n})
    return events


# ---------------------------------------------------------------- records

def previous_payload(out_path):
    """The payload currently shipped, read BEFORE the pipeline overwrites
    it. Returns None when there is nothing to compare against — a first
    build, or a file this module cannot parse — and the record then
    states a baseline rather than inventing a history."""
    p = Path(out_path)
    if not p.exists():
        return None
    try:
        return load_data_js(p)
    except Exception:
        return None


def socrata_updated(dataset_ids, host="bythenumbers.sco.ca.gov", timeout=15):
    """The source's own 'rows last updated' stamp, where the source
    publishes one. Best-effort by design: a refresh must never fail, or
    even slow down noticeably, because a metadata endpoint was down.
    Returns {dataset_id: iso8601} for whatever answered.

    This is a source signal, NOT an attribution. It says when SCO last
    touched the table; it does not say whether a figure moved, or why.
    """
    import urllib.request
    from datetime import datetime, timezone
    out = {}
    for ds in dataset_ids:
        try:
            req = urllib.request.Request(
                f"https://{host}/api/views/{ds}.json",
                headers={"User-Agent": "ca-ledger-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                meta = json.loads(r.read().decode("utf-8"))
            ts = meta.get("rowsUpdatedAt")
            if ts:
                out[ds] = (datetime.fromtimestamp(int(ts), timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ"))
        except Exception:
            continue
    return out or None


def set_begins(rec):
    """meta.begins is the day the record STARTED OPERATING — the first
    batch written by an actual refresh. A backfilled batch carries the
    date of the historical event it describes, which is earlier, and
    letting it set `begins` would advertise retroactive coverage the
    record does not have. docs/V13_CHANGEFEED_FINDING.md §4 is explicit
    that backfill yields one event and the record otherwise starts empty;
    this keeps the file honest about that."""
    real = [b["built"] for b in rec.get("batches") or []
            if not b.get("backfilled")]
    rec["meta"]["begins"] = min(real) if real else None
    return rec


def prune_labels(rec):
    """Keep a display name only for identities the record actually
    mentions. Storing one per entity is the dense-for-a-sparse-fact trap
    docs/V13_CHANGEFEED_FINDING.md §6 rejects: the district layer alone
    has 5,239 entities and, at the time of writing, zero events."""
    used = {ev["e"] for b in rec.get("batches") or [] for ev in b.get("events") or []}
    rec["labels"] = {k: v for k, v in (rec.get("labels") or {}).items()
                     if k in used and v}
    return rec


def blank_record(layer):
    return {"meta": {"layer": layer,
                     "note": "Mechanical record. It reports THAT a figure "
                             "changed and by how much, never why.",
                     "begins": None},
            "labels": {}, "batches": []}


def record_path(layer):
    return ROOT / LAYERS[layer][1]


def load_record(layer):
    p = record_path(layer)
    if not p.exists():
        return blank_record(layer)
    try:
        return load_data_js(p)
    except Exception:
        return blank_record(layer)


def global_name(layer):
    return GLOBAL_NAME.get(layer, "CA_LEDGER_REVISIONS_" + layer.upper())


def write_record(layer, record):
    p = record_path(layer)
    set_begins(record)
    prune_labels(record)
    body = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    header = (f"/* GENERATED by pipeline/revisions.py — the {LAYERS[layer][2]} "
              f"change record. Mechanical: it reports THAT a figure moved and "
              f"by how much, never why. Do not edit by hand. */\n")
    p.write_text(f"{header}window.{global_name(layer)} = {body};\n",
                 encoding="utf-8")
    return p


def record_revision(layer, old_payload, new_payload, source_signal=None):
    """Append one batch for this refresh. Silent when nothing moved, so a
    no-op rebuild does not litter the record with empty entries.

    Returns the batch that was appended, or None."""
    rec = load_record(layer)
    new_flat = flatten(layer, new_payload)
    lab = labels(layer, new_payload)

    fdigest = figures_digest(new_payload)
    prev_digest = None
    for b in reversed(rec.get("batches") or []):
        if b.get("figuresDigest"):
            prev_digest = b["figuresDigest"]
            break

    if old_payload is None:
        # first sighting of this layer — establish the baseline, claim
        # nothing about what came before it
        batch = {"built": date.today().isoformat(), "events": [],
                 "baseline": True, "figuresDigest": fdigest,
                 "pipelineCommit": pipeline_commit(),
                 "cells": len(new_flat)}
        if source_signal:
            batch["sourceUpdated"] = source_signal
        rec["batches"].append(batch)
        rec["labels"] = lab
        write_record(layer, rec)
        return batch

    old_flat = flatten(layer, old_payload)
    events = diff(old_flat, new_flat)
    if not events and fdigest == (prev_digest or fdigest):
        rec["labels"].update({k: v for k, v in lab.items() if v})
        write_record(layer, rec)
        return None

    batch = {"built": date.today().isoformat(), "events": events,
             "figuresDigest": fdigest, "pipelineCommit": pipeline_commit(),
             "cells": len(new_flat)}
    if source_signal:
        batch["sourceUpdated"] = source_signal
    rec["batches"].append(batch)
    # keep labels for every identity the record mentions, current or retired
    merged = dict(rec.get("labels") or {})
    merged.update({k: v for k, v in lab.items() if v})
    for ev in events:
        merged.setdefault(ev["e"], ev["e"])
    rec["labels"] = merged
    write_record(layer, rec)
    return batch


# --------------------------------------------------------------- backfill

# The ONE historical event whose cause is known rather than inferred:
# our own classifier fix, recorded in STATUS.md and in commit 342a042.
# This is the only place in the whole system where a note is attached to
# an event, and it is a constant — the refresh path cannot write one.
BACKFILL = {
    "layer": "city",
    "built": "2026-07-14",
    "from": "491218c",
    "to": "342a042",
    "note": "Our own correction, not a change at the source. The FY 2016-17 "
            "city function classifier read the wrong SCO column, so nearly "
            "every city's spending landed in 'other'. Fixing it moved money "
            "between function keys for all 482 cities; the 31 events below "
            "are the figures that existed both before and after. The rest of "
            "that correction appears as keys that appeared and disappeared, "
            "which this record could not observe retroactively because the "
            "shipped file was replaced, not diffed, at the time.",
}


def build_backfill():
    """Re-derive the known historical batch from git. Deterministic."""
    def at(rev, path):
        out = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"],
                             capture_output=True, text=True)
        if out.returncode:
            return None
        i = out.stdout.find("=")
        return json.loads(out.stdout[i + 1:].strip().rstrip(";"))

    old = at(BACKFILL["from"], "city-data.js")
    new = at(BACKFILL["to"], "city-data.js")
    if old is None or new is None:
        return None
    of, nf = flatten("city", old), flatten("city", new)
    # value changes only: the vintages either side of this commit are the
    # only evidence that survives, and a key that appeared here cannot be
    # distinguished from one the depth layers added later
    events = [e for e in diff(of, nf) if e["o"] is not None and e["n"] is not None]
    return {"built": BACKFILL["built"], "events": events,
            "backfilled": True, "note": BACKFILL["note"],
            "fromCommit": BACKFILL["from"], "toCommit": BACKFILL["to"],
            "cells": len(nf)}


# ------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true",
                    help="re-derive each record's figures digest from the "
                         "shipped data and report agreement")
    ap.add_argument("--backfill", action="store_true",
                    help="(re)write the one known historical batch")
    ap.add_argument("--init", action="store_true",
                    help="create a baseline record for any layer lacking one")
    args = ap.parse_args()

    if args.backfill:
        b = build_backfill()
        if b is None:
            sys.exit("backfill: the historical commits are not in this clone")
        rec = load_record("city")
        rec["batches"] = [x for x in rec["batches"] if not x.get("backfilled")]
        rec["batches"].insert(0, b)
        rec["batches"].sort(key=lambda x: (x["built"], bool(x.get("baseline"))))
        payload = load_data_js(ROOT / "city-data.js")
        lab = dict(rec.get("labels") or {})
        lab.update({k: v for k, v in labels("city", payload).items() if v})
        for ev in b["events"]:
            lab.setdefault(ev["e"], ev["e"])
        rec["labels"] = lab
        write_record("city", rec)
        print(f"backfill: {len(b['events'])} events "
              f"({BACKFILL['from']}..{BACKFILL['to']})")

    if args.init:
        for layer, (data_file, _, _) in LAYERS.items():
            p = ROOT / data_file
            if not p.exists():
                continue
            rec = load_record(layer)
            if rec.get("batches"):
                continue
            record_revision(layer, None, load_data_js(p))
            print(f"init: {layer} baseline recorded")

    if args.verify:
        bad = 0
        for layer, (data_file, rec_file, _) in LAYERS.items():
            p, r = ROOT / data_file, ROOT / rec_file
            if not (p.exists() and r.exists()):
                print(f"  {layer:9} MISSING")
                bad += 1
                continue
            payload = load_data_js(p)
            rec = load_data_js(r)
            live = figures_digest(payload)
            batches = [b for b in rec["batches"] if b.get("figuresDigest")]
            latest = batches[-1]["figuresDigest"] if batches else None
            ok = latest == live
            n = sum(len(b["events"]) for b in rec["batches"])
            print(f"  {layer:9} {'OK ' if ok else 'STALE'} "
                  f"{n:5} events  figures {live[:12]}")
            bad += 0 if ok else 1
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
