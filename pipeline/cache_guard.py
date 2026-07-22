#!/usr/bin/env python3
"""
Citizen Ledger — THE SOURCE CACHE IS READ-ONLY BY DEFAULT.

pipeline/cache/ holds the fetched source documents every gate is measured
against: the SCO extracts, the CDE workbooks and SACS databases, the CCC
portal reports and Exhibit C PDFs. They are the evidence. A figure that
reconciles against a corrupted cache reconciles against nothing.

WHY THIS EXISTS. A mutation test wrote a corrupted statewide control into
pipeline/cache/ccc/tablevi-2014-15.txt. The scratch harness had symlinked
the real cache into its sandbox so the pipeline could find it, so a write
meant to land on a throwaway copy landed on the original. It was noticed
and restored — but only because the next run happened to fail. Had the
mutation been applied and the digest taken afterwards, the run would have
gated clean against a poisoned source and said so.

"The harness is careful" is not a control. The files are made unwritable,
so the harness CANNOT reach them:

    lock(CACHE)                  every file mode 0o444
    with unlocked(path):         the one deliberate exception
        path.write_bytes(...)

A refresh is a deliberate act and unlocks the single file it intends to
rewrite. Everything else — a test, a stray script, a mutation applied to
the wrong tree — fails with PermissionError at the moment of the write,
which is loud and specific, rather than succeeding quietly.

This protects against ACCIDENT, not against an attacker with the same
uid: anything that can chmod can undo it. That is the threat being
addressed — the harness that meant to write somewhere else.
"""

import os
import stat
from contextlib import contextmanager
from pathlib import Path

READ_ONLY = 0o444
WRITABLE = 0o644


def _files(root: Path):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink():
            yield p


def lock(root: Path) -> int:
    """Make every cached source file unwritable. Returns how many."""
    n = 0
    for p in _files(root):
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o222:
            p.chmod(READ_ONLY)
            n += 1
    return n


def unlock(root: Path) -> int:
    """The inverse, for a deliberate refresh of a whole tree."""
    n = 0
    for p in _files(root):
        if not (stat.S_IMODE(p.stat().st_mode) & 0o222):
            p.chmod(WRITABLE)
            n += 1
    return n


def is_locked(path: Path) -> bool:
    """True when the file exists and no write bit is set."""
    return path.exists() and not (stat.S_IMODE(path.stat().st_mode) & 0o222)


@contextmanager
def unlocked(path: Path):
    """Briefly make ONE file writable, then lock it again.

    The only sanctioned way to rewrite a cached source. Re-locks on the
    way out even if the write raises, so a failed refresh cannot leave
    the cache writable behind it.
    """
    path = Path(path)
    existed = path.exists()
    if existed:
        path.chmod(WRITABLE)
    try:
        yield path
    finally:
        if path.exists():
            path.chmod(READ_ONLY)


def write_cached(path: Path, blob, binary=False):
    """Write a cached source file through the guard."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with unlocked(path):
        if binary:
            path.write_bytes(blob)
        else:
            path.write_text(blob, encoding="utf-8")
    return blob


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Lock or unlock the source cache")
    ap.add_argument("action", choices=["lock", "unlock", "status"])
    ap.add_argument("--path", default=str(Path(__file__).resolve().parent / "cache"))
    a = ap.parse_args()
    root = Path(a.path)
    if not root.exists():
        raise SystemExit(f"no cache at {root}")
    if a.action == "lock":
        print(f"locked {lock(root)} file(s) under {root}")
    elif a.action == "unlock":
        print(f"unlocked {unlock(root)} file(s) under {root}")
    else:
        files = list(_files(root))
        locked = [p for p in files if is_locked(p)]
        print(f"{len(locked)}/{len(files)} cached source files are read-only")
        for p in files:
            if not is_locked(p):
                print(f"  WRITABLE: {p.relative_to(root)}")


if __name__ == "__main__":
    main()
