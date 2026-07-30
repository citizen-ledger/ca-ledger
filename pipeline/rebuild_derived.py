#!/usr/bin/env python3
"""
Citizen Ledger — regenerate every DERIVED artefact. One command.

WHY THIS EXISTS. `main` went red between two merges. #117 landed the 34th
finding document; #118 landed the assertion that every document on disk
appears in `findings-manifest.js`. Each branch was green on its own, because
neither contained the other's half — and the manifest was generated before
the merge. Nothing was forgotten: the failure needed no mistake, only two
correct changes landing in an order nobody chose.

There was also no "standard rebuild" to wire anything into. There is no
Makefile, no rebuild script, and `deploy-pages.yml` uploads the repository
root with no build step and no test step. This is that missing command.

THE DISTINCTION THAT MATTERS. A *fetch* pipeline talks to a source and can
be expensive, rate-limited or blocked outright — two of them cannot run
unattended at all. A *build* pipeline reads only files already in this
repository, so it is cheap, offline and safe to run any time. This runs the
second kind and never the first: `--refresh` is a deliberate act, and
nothing here will make a network request.

WHICH BUILDERS, AND WHY IT IS A GLOB. `pipeline/build_*.py` is the naming
convention this project already follows, and the set grows in the ordinary
course of work — `build_findings_manifest.py` is three days old. A hardcoded
list is the defect recorded five times in OPEN.md (the page list, the digest
list, the GATED list, the conditional branch, the document index), so the
builders are discovered rather than enumerated, and the discovery is
asserted non-empty because the failure mode of a glob is silence.

ALL THREE DERIVED ARTEFACTS EMBED A BUILD DATE. So "did it change?" is not
the same question as "is it stale": re-running on a later day rewrites the
date and the digest that covers it while every figure stays identical.
Measured on 2026-07-29: `bulk/compensation.csv` differed from the committed
copy in exactly three lines — `# Data generated`, `# Exported`, and a
vintage `ageDaysAtBuild` of 3 against 7 — and was byte-identical on the
other 4,144. That is why the suite's freshness checks compare SUBSTANCE and
not bytes, and why this script reports substantive changes separately from
date-only churn.

Usage:
    python3 pipeline/rebuild_derived.py            # rebuild, report what moved
    python3 pipeline/rebuild_derived.py --check    # report only, write nothing
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"

# Lines whose only content is when the build ran. Removing them before
# comparing is what separates "this artefact is out of date" from "this
# artefact was built on a different day".
DATE_LINE = re.compile(
    r"^#\s*(Data generated|Exported|Vintage)\b|\"generated\"\s*:\s*\"[\d-]+\"")

# A DIGEST CARRIES NO INFORMATION THE COMPARED CONTENT DOES NOT ALREADY CARRY,
# so it is excluded when classifying churn. This is not a weakening: if the
# file a digest covers changed substantively, that file is itself compared and
# will say so. Without this the classification cries wolf every day —
# measured 2026-07-29, `bulk/compensation.csv` changed only its build date,
# which changed its sha256, which changed `bulk-manifest.js` and
# `bulk/SCHEMA.md`, and all three were reported as substantive. A rebuild
# report that is red every morning is a rebuild report nobody reads, which is
# the same failure this script exists to prevent.
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def builders():
    """Every build_*.py, discovered by the convention the project uses."""
    found = sorted(p for p in PIPE.glob("build_*.py"))
    if not found:
        raise SystemExit(
            "no pipeline/build_*.py found — refusing to report success. A glob "
            "that matches nothing looks exactly like a tree with nothing to "
            "rebuild, and this script exists because that kind of silence is "
            "what let main go red.")
    return found


def snapshot():
    """Every tracked file's bytes, so a rebuild's effect can be measured."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split("\0")
    snap = {}
    for f in (x for x in out if x):
        p = ROOT / f
        try:
            snap[f] = p.read_bytes()
        except OSError:
            pass
    return snap


def substantive(before, after):
    """True when the change is more than a build date."""
    def strip(b):
        try:
            txt = b.decode("utf-8")
        except UnicodeDecodeError:
            return b
        kept = [l for l in txt.split("\n") if not DATE_LINE.search(l)]
        return HEX64.sub("<digest>", "\n".join(kept))
    return strip(before) != strip(after)


def main():
    check_only = "--check" in sys.argv
    bs = builders()
    print(f"{len(bs)} derived-artefact builders discovered under pipeline/:")
    for b in bs:
        print(f"    {b.name}")
    print()

    before = snapshot()
    failed = []
    for b in bs:
        # --write is this project's convention for "actually write"; a builder
        # without it writes by default (build_bulk.py). Passing an unknown
        # flag would be worse than not passing one, so it is only added where
        # the builder declares it.
        argv = [sys.executable, str(b)]
        if "--write" in b.read_text(encoding="utf-8"):
            argv.append("--write")
        if check_only:
            print(f"  --check: would run {' '.join(argv[1:])}")
            continue
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout or r.stderr or "").strip().split("\n")[-1][:96]
        print(f"  {'ok ' if r.returncode == 0 else 'FAIL'} {b.name:34} {tail}")
        if r.returncode != 0:
            failed.append((b.name, (r.stderr or r.stdout)[-400:]))

    if failed:
        print()
        for n, err in failed:
            print(f"!! {n} failed:\n{err}")
        raise SystemExit(f"{len(failed)} builder(s) failed; nothing is claimed "
                         "to be up to date")
    if check_only:
        return

    after = snapshot()
    subs = [f for f in sorted(set(before) | set(after))
            if before.get(f) != after.get(f) and substantive(
                before.get(f, b""), after.get(f, b""))]
    dates = [f for f in sorted(set(before) | set(after))
             if before.get(f) != after.get(f) and f not in subs]
    print()
    print(f"SUBSTANTIVE changes: {len(subs)}")
    for f in subs:
        print(f"    {f}")
    print(f"date-stamp-only churn: {len(dates)}")
    for f in dates:
        print(f"    {f}")
    if subs:
        print("\nA derived artefact was out of date. Commit these; the suite "
              "asserts them against their sources and would have failed.")
    elif dates:
        print("\nNothing substantive moved. These differ only in when they "
              "were built, so committing them is optional churn.")
    else:
        print("\nEvery derived artefact was already up to date.")


if __name__ == "__main__":
    main()
