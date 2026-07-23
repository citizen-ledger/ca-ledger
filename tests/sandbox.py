#!/usr/bin/env python3
"""
A SANDBOX FOR MUTATION TESTING THAT CANNOT REACH THE REAL SOURCES.

Ad-hoc harnesses kept being hand-rolled like this:

    rsync -a --exclude='pipeline/cache' repo/ "$D"/
    ln -s repo/pipeline/cache "$D"/pipeline/cache     # <- the hazard

The symlink is there because the pipelines need the cached sources and
the cache is 4 GB, too big to copy per run. But it means a mutation
written into what looks like a throwaway tree lands on the original. In
PR #59 exactly that happened: a corrupted statewide control was written
into pipeline/cache/ccc/tablevi-2014-15.txt.

Two defences, and the second is the one that matters:

  1. sandbox() below gives the copy a cache view built from symlinks, so
     reads work and the 4 GB is not duplicated.
  2. pipeline/cache_guard.py has already made every real cached file
     mode 0o444, so a write THROUGH that view fails with PermissionError.

Defence 2 holds whether or not anyone uses this helper — which is the
point. This module exists so the safe pattern is also the convenient
one, not so that safety depends on remembering it.

    from sandbox import sandbox
    with sandbox() as sb:
        (sb / "ccc-data.js").write_text(mutated)     # fine, it is a copy
        subprocess.run([sys.executable, "tests/run_tests.py"], cwd=sb)
"""

import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "pipeline" / "cache"


@contextmanager
def sandbox(link_cache=True):
    """A throwaway copy of the working tree.

    The copy is writable; the cached sources it can see are not. Yields
    the sandbox path and removes it on the way out.
    """
    tmp = Path(tempfile.mkdtemp(prefix="ca-ledger-sandbox-"))
    try:
        sb = tmp / "tree"
        subprocess.run(
            ["rsync", "-a", "--exclude=.git", "--exclude=pipeline/cache",
             "--exclude=__pycache__", f"{ROOT}/", f"{sb}/"],
            check=True, capture_output=True)
        if link_cache and CACHE.exists():
            (sb / "pipeline" / "cache").symlink_to(CACHE, target_is_directory=True)
        yield sb
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cache_is_reachable_for_write(sb: Path, relative: str) -> bool:
    """Try to write a cached source THROUGH the sandbox view.

    Returns True if the write succeeded — which is a failure of the
    guard, and is what the suite asserts against.
    """
    target = sb / "pipeline" / "cache" / relative
    if not target.exists():
        return False
    original = target.read_bytes()
    try:
        target.write_bytes(b"MUTATION-TEST-PROBE")
    except (PermissionError, OSError):
        return False
    # it let us write: put it back immediately, then report the failure
    try:
        os.chmod(target, 0o644)
        target.write_bytes(original)
        os.chmod(target, 0o444)
    except OSError:
        pass
    return True


if __name__ == "__main__":
    with sandbox() as sb:
        print("sandbox:", sb)
        probe = "ccc/tablevi-fy2223.txt"
        print("cache writable through the view:",
              cache_is_reachable_for_write(sb, probe))
