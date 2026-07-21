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
import re
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
    # Not a spending layer — the price index the inflation adjustment
    # uses. Recorded because a republished index moves every real figure
    # derived from it while no nominal figure changes, which is exactly
    # the movement this record exists to make visible.
    "deflator": ("deflator-data.js", "deflator-revisions.js", "Price deflator"),
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


# ------------------------------------------------- positional -> intrinsic
#
# THE SLUG-INSTABILITY LESSON, IN A SECOND SUBSYSTEM.
#
# Several payloads ship a figure as a row in an array that is SORTED BY
# AMOUNT: city and county `lines`, state `funds` and `programs`, K-12
# `byResource.n`. `_leaves` walks a list by enumeration index, so the key
# a figure got was its RANK. Rank is not identity:
#
#   - two lines swapping order between builds are reported as each
#     other's change, twice, with both figures wrong;
#   - `lineLabels` is sorted() over the OBSERVED label set, so one new
#     label anywhere in California renumbers up to 90 labels and shifts
#     every rank below it — the feed would publish tens of thousands of
#     phantom events;
#   - city and county rows carry [labelIndex, dollars], and the label
#     INDEX is itself numeric, so `_leaves` emitted the index as though
#     it were a figure. A pure re-indexing read as a changed value.
#
# Measured before the fix: 576,953 of 825,331 keys (69.9%) were
# rank-derived; the districts layer was 100%.
#
# The feed makes no attribution claim. Reporting exactly what moved is
# the whole of its value, so a phantom event is not a blemish on it —
# it is the failure of the entire product. Every figure is therefore
# keyed on something intrinsic: the label, the fund code, the program
# code, the resource code, or a NAMED fixed slot.

def _intrinsic(rows, key_at, val_at, what):
    """[[key, ..., value], ...] -> {str(key): value}, keyed on the row's
    own identifier rather than on where it happens to sit. Refuses on a
    duplicate rather than letting one figure silently overwrite another
    (measured: no duplicate exists in any shipped payload)."""
    out = {}
    for r in rows or []:
        if not isinstance(r, (list, tuple)) or len(r) <= max(key_at, val_at):
            continue
        k = str(r[key_at])
        if k in out:
            raise ValueError(
                f"revisions: duplicate {what} key {k!r} — the identifier is "
                "not unique in its scope, so keying on it would drop a "
                "figure. Resolve deliberately; do not fall back to rank.")
        out[k] = r[val_at]
    return out


def _slots(seq, names):
    """A FIXED-LENGTH tuple whose positions have declared meanings ->
    {name: value}. Position is meaning here, not rank, but naming it
    means a future length change cannot silently re-point a key."""
    return {n: seq[i] for i, n in enumerate(names)
            if seq is not None and i < len(seq)}


def _city_years(years, line_labels):
    """city/county year records, with `lines` re-keyed from rank to the
    line LABEL. The label is the intrinsic thing; its index is an
    artefact of a sorted legend and is not emitted at all."""
    out = {}
    for fy, y in (years or {}).items():
        if not isinstance(y, dict):
            out[fy] = y
            continue
        rec = {k: v for k, v in y.items() if k != "lines"}
        lines = {}
        for fn, arr in (y.get("lines") or {}).items():
            fam = {}
            for row in arr or []:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                idx = row[0]
                lbl = (line_labels[idx]
                       if isinstance(idx, int) and 0 <= idx < len(line_labels)
                       else str(idx))
                if lbl in fam:
                    raise ValueError(
                        f"revisions: duplicate line label {lbl!r} in {fn!r}")
                fam[lbl] = row[1]
            if fam:
                lines[fn] = fam
        if lines:
            rec["lines"] = lines
        out[fy] = rec
    return out


def _school_years(years, fams):
    """K-12 year records, with byResource named rows re-keyed from rank to
    the RESOURCE CODE, and each row's object split re-keyed from position
    to the object-family key. OBJ order is a fixed constant, so position
    there is meaning; naming it keeps it that way."""
    out = {}
    for fy, y in (years or {}).items():
        if not isinstance(y, dict):
            out[fy] = y
            continue
        rec = {k: v for k, v in y.items() if k != "byResource"}
        by = {}
        for grp, blk in (y.get("byResource") or {}).items():
            if not isinstance(blk, dict):
                continue
            nb = {k: v for k, v in blk.items() if k != "n"}
            named = {}
            for row in blk.get("n") or []:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                code = str(row[0])
                if code in named:
                    raise ValueError(
                        f"revisions: duplicate resource code {code!r} in {grp!r}")
                cell = {"v": row[1]}
                if len(row) > 2 and isinstance(row[2], (list, tuple)):
                    cell["obj"] = _slots(row[2], fams)
                named[code] = cell
            if named:
                nb["n"] = named
            by[grp] = nb
        if by:
            rec["byResource"] = by
        out[fy] = rec
    return out


def _state_dept(d):
    """A department record with funds/programs re-keyed on their own
    codes and `nr` given its declared slot names."""
    o = {x: d[x] for x in d
         if x not in ("name", "code", "funds", "programs", "nr")}
    if d.get("funds"):
        # A fund row is [cd, class, thousands, legal title?]. The title is
        # present only where DOF publishes more than one fund under one
        # code, so the identity is the code alone where the code is
        # unique and code|title where it is not — the same tuple the
        # source distinguishes by.
        o["funds"] = _intrinsic(
            [[(r[0] if len(r) < 4 or not r[3] else f"{r[0]}|{r[3]}"), r[1], r[2]]
             for r in d["funds"]], 0, 2, "fund")
    if d.get("programs"):
        o["programs"] = _intrinsic(d["programs"], 0, 2, "program")
    if d.get("nr"):
        o["nr"] = _slots(d["nr"], ("N", "R"))
    return o


DISTRICT_SLOTS = ("gov", "ent", "isf", "cf")


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
                    for k, v in _leaves(_state_dept(d), "", {}).items():
                        out[f"agency:{aid}/dept:{code}\t{fy}.{k}"] = v
    elif layer in ("city", "county"):
        coll = "cities" if layer == "city" else "counties"
        lbls = ((payload.get("meta") or {}).get("lineLabels")) or []
        for slug, rec in (payload.get(coll) or {}).items():
            years = _city_years(rec.get("years") or {}, lbls)
            for k, v in _leaves(years, "", {}).items():
                out[f"{slug}\t{k}"] = v
    elif layer == "district":
        years = payload.get("years") or []
        for slug, rec in (payload.get("districts") or {}).items():
            for field in ("exp", "rev"):
                for i, slot in enumerate(rec.get(field) or []):
                    fy = years[i] if i < len(years) else str(i)
                    if slot is None:
                        continue
                    for nm, val in _slots(slot, DISTRICT_SLOTS).items():
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            out[f"{slug}\t{fy}.{field}.{nm}"] = val
    elif layer == "school":
        fams = [f.get("key") for f in (payload.get("objectFamilies") or [])]
        for coll, idf in (("districts", "cds"), ("countyOffices", "cds")):
            for rec in (payload.get(coll) or {}).values():
                ident = f"{coll}:{rec.get(idf)}"
                years = _school_years(rec.get("years") or {}, fams)
                for k, v in _leaves(years, "", {}).items():
                    out[f"{ident}\t{k}"] = v
        for rec in (payload.get("charters") or {}).values():
            ident = ("charter:" + str(rec.get("charterNumber")) + "|"
                     + str(rec.get("name")) + "|" + str(rec.get("county")))
            years = _school_years(rec.get("years") or {}, fams)
            for k, v in _leaves(years, "", {}).items():
                out[f"{ident}\t{k}"] = v
    elif layer in ("csu", "uc"):
        top = "systemwide"
        for k, v in _leaves(payload.get(top) or {}, "", {}).items():
            out[f"systemwide\t{k}"] = v
        for c in payload.get("campuses") or []:
            ident = f"campus:{c.get('name')}"
            for k, v in _leaves({x: c[x] for x in c if x != "name"}, "", {}).items():
                out[f"{ident}\t{k}"] = v
    elif layer == "deflator":
        for fy, v in (payload.get("fy") or {}).items():
            out[f"index\t{fy}"] = v
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
    elif layer == "deflator":
        out["index"] = "Deflator index value"
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
    # A batch counts as carrying a correction if it has its id OR its exact
    # note. Batches written before ids existed have only the note, and
    # stamping an id onto a dated record afterwards would be editing the
    # record to suit the code.
    prior = rec.get("batches") or []
    applied = {b.get("correctionId") for b in prior if b.get("correctionId")}
    applied |= {c["id"] for c in CORRECTIONS
                if any(b.get("note") == c["note"] for b in prior)}
    corr = correction_for(layer, batch["built"], applied)
    if corr:
        batch["ours"] = True
        batch["correctionId"] = corr["id"]
        batch["note"] = corr["note"]
    cov = coverage_for(layer, batch["built"])
    if cov and any(b.get("coverageAdded") == cov["added"]
                   for b in (rec.get("batches") or [])):
        # A coverage change is a one-time fact, not a per-build one. Running
        # the pipeline twice on the same day would otherwise declare the same
        # extension twice.
        cov = None
    if cov:
        added = set(cov["added"])
        entered = [e for e in batch["events"]
                   if e["o"] is None and _fy_of(e["k"]) in added]
        batch["events"] = [e for e in batch["events"] if e not in entered]
        batch["ours"] = True
        batch["coverageAdded"] = cov["added"]
        batch["figuresEntered"] = len(entered)
        batch["note"] = cov["note"]
    if source_signal:
        batch["sourceUpdated"] = source_signal
    rec["batches"].append(batch)
    # keep labels for every identity the record mentions, current or retired
    # Carry forward every label already known — a RETIRED identity keeps the
    # name it had, which is the whole point of labelling separately from
    # keying. What must never happen is storing the machine key AS the
    # label: revisions.html renders labels verbatim, so an identity with no
    # known name was being shown to readers as "campus:Cal Poly Humboldt".
    # An unknown identity has no name; the page says so rather than
    # inventing one from the key.
    merged = dict(rec.get("labels") or {})
    merged.update({k: v for k, v in lab.items() if v})
    rec["labels"] = merged
    write_record(layer, rec)
    return batch


# ------------------------------------------------------- coverage changes
#
# EXTENDING THE WINDOW IS NOT A SET OF FIGURE CHANGES.
#
# When the Ledger loads years it did not load before, every figure in those
# years is new to the record — but nothing MOVED. The source published them
# all along; our coverage changed. Emitting one "appeared" event per figure
# would bury any real change under thousands of entries that report no
# change at all, which is the phantom-event failure the rank-keying fix
# removed, in a different guise. Measured on the V15 state extension: three
# added years produced 12,646 events and a 1.1 MB record against a 64 KB
# budget.
#
# So a declared coverage change records ONE stated fact — which years
# entered the record and how many figures came with them — and suppresses
# the per-figure appearances for those years only. Changes to figures in
# years the record ALREADY covered are unaffected and still reported one by
# one, so a real restatement can never hide inside an extension.
COVERAGE = [
    {
        "layer": "state",
        "built": "2026-07-21",
        "added": ["2017-18", "2018-19", "2019-20"],
        "note": "Our own change of coverage, not a change at the source. The "
                "record now begins at FY 2017-18, the earliest year the "
                "Department of Finance's structured budget API serves: every "
                "earlier year returns an empty result rather than an error. "
                "The figures for these three years are newly IN the record, "
                "but none of them moved \u2014 they were published all along "
                "and the Ledger had not loaded them. They are counted here "
                "rather than listed as thousands of individual appearances, "
                "which would bury any real change. Every added year passes "
                "the same gates as the years already shipped, including "
                "FY 2019-20, whose agency rows reconcile to DOF's printed "
                "Schedule 9 grand total rather than to the differing "
                "stateGrandTotal the same API declares.",
    },
]


def coverage_for(layer, built):
    for c in COVERAGE:
        if c["layer"] == layer and c["built"] == built:
            return c
    return None


def _fy_of(key):
    """The fiscal year a figure path begins with, or None."""
    path = key.split("\t", 1)[1] if "\t" in key else key
    head = path.split(".", 1)[0]
    return head if re.match(r"^\d{4}-\d{2}$", head) else None


# ------------------------------------------------------------ corrections

# OUR OWN CORRECTIONS — the feed's one attributed event type.
#
# A changed figure normally gets no cause: telling a source restatement
# from a source redefinition requires reading release notes, which is a
# human act (see the module docstring). The exception is a change WE
# caused, where the cause is known rather than inferred because it is our
# own commit.
#
# The invariant that keeps this honest: a note can only come from a
# constant declared here. The refresh path may APPLY a declared
# correction, but it can never invent one, so no per-refresh judgement
# step is introduced.
CORRECTIONS = [
    {
        "id": "ccc-absence-not-negative",
        "layer": "ccc",
        "built": "2026-07-21",
        "note": "Our own correction, not a change at the source. A district "
                "whose apportionment record is absent was published with "
                "basicAid FALSE \u2014 the claim that its property-tax "
                "position had been checked against the SCFF schedule and it "
                "is not community-supported. It had not been checked. "
                "Calbright is the live case: it is not apportionment-funded "
                "at all, so the fact does not exist for it. Absence is now "
                "marked as absence, alongside the four sibling fields that "
                "already were, and the reason travels with the record "
                "instead of the page carrying one institution's explanation "
                "for every case. No figure moved: every Current Expense, "
                "instructional-salary and 50-Percent-Law value is "
                "unchanged, and the statewide totals are identical.",
    },
    {
        "id": "ccc-statewide-funded-ftes",
        "layer": "ccc",
        "built": "2026-07-21",
        "note": "Our own correction, not a change at the source. The statewide "
                "funded-FTES figure was the pipeline's OWN SUM of the 72 "
                "district pages (1,100,664.62), not the Chancellor's Office's "
                "printed statewide control (1,100,664.61). The reconciliation "
                "meant to catch that difference had never run: the Exhibit C "
                "page matcher required a heading ending in \"CCD\" or "
                "\"District\", the statewide summary page is headed "
                "\"Statewide Totals\", so the comparison target was never "
                "found and the gate skipped itself. The parser and the gate "
                "were fixed on 2026-07-21, but the correction could not reach "
                "the published file until a second defect was fixed the same "
                "day \u2014 this layer's --write path raised NameError before "
                "it could record anything, so no CCC refresh had ever written "
                "a change. The figure now shown is the published control. "
                "Nothing else moved: all 72 districts and every Table VI "
                "figure are unchanged.",
    },
    {
        "id": "state-fund-identity",
        "layer": "state",
        "built": "2026-07-20",
        "note": "Our own correction, not a change at the source. Department "
                "fund rows were keyed on the fund CODE alone, where the "
                "Department of Finance distinguishes a fund by code, legal "
                "title and class together. Enumerated across all 1,155 "
                "department-years in the six loaded budgets: 43 collisions, "
                "every one of them fund 0001, where DOF publishes \"General "
                "Fund\" and \"General Fund, Proposition 98\" as separate "
                "rows. Those two were being added together and shown as one "
                "line, folding away the Proposition 98 education guarantee. "
                "Separately, the fund-name legend was one global dictionary "
                "merged across six budget acts, so a fund renamed between "
                "acts lost its earlier name: 23 codes drift across the "
                "window, and FY 2020-21 was rendering fund 3085 as the "
                "\"Behavioral Health Services Fund\" \u2014 a name it did "
                "not carry until FY 2025-26. Fund names are now scoped per "
                "year. No gated total moved: every agency and department "
                "figure is identical, and the V8 parent-sum gate passes "
                "unchanged. What changed is which rows the fund drill shows "
                "and what they are called.",
    },
    {
        "id": "district-name-county-key",
        "layer": "district",
        "built": "2026-07-20",
        "note": "Our own correction, not a change at the source. The special "
                "district pipeline grouped filings on (name, county) — "
                "correctly — but then wrote the directory and the amounts "
                "keyed on the NAME alone, so three pairs of same-named "
                "districts in different counties collided and each pair was "
                "published as one entity. Rural North Vacaville Water "
                "District carried Sutter County and a levee activity while "
                "being a Solano community-services district, and its "
                "FY 2017-18 expenditure read $1,268,460 — the arithmetic sum "
                "of two independent agencies. Hamilton City Fire Protection "
                "District carried Sonoma County; it is in Glenn. California "
                "Risk Management Authority (CRMA) merged its Fresno and "
                "Madera filings. Every totals gate passed throughout: the "
                "money was all present, attributed to one entity instead of "
                "two. The six records now match the source's county, "
                "activity and filing years exactly.",
    },
]


def correction_for(layer, built, already):
    """The declared correction for this layer and build date that has NOT
    already been recorded.

    Keyed on a stable `id`, not on (layer, built): two corrections can land
    on one layer on one day, and a rebuild on the same day must not attach
    a note a second time. Both happened — a rebuild re-applied the
    statewide funded-FTES note to a later, empty batch.
    """
    for c in CORRECTIONS:
        if (c["layer"] == layer and c["built"] == built
                and c["id"] not in already):
            return c
    return None


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
