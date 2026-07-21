#!/usr/bin/env python3
"""
Verify the RECORD INTEGRITY digest of a Citizen Ledger data file.

    python3 pipeline/verify_digest.py data.js city-data.js

Each data file's meta.integrity.digest is the SHA-256 of the file's
JSON payload in canonical form — `json.dumps(payload, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8 — with
the meta.integrity field removed. This script recomputes it and
compares. Exit code 0 = every file verifies.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import canonical_digest  # noqa: E402


def load_payload(path: Path):
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("=") + 1: text.rindex(";")])


def discover(root):
    """Every shipped payload that CARRIES a digest.

    This list used to be a hardcoded literal, and it had drifted: it named
    ten files while twelve carried a digest, so deflator-data.js and
    search-index.js were never verified and the run still printed a clean
    sweep. A verifier that silently checks a subset is the empty-gate
    defect wearing a different hat — the check passes, and the two files
    it forgot could have said anything.
    """
    out = []
    for path in sorted(root.glob("*.js")):
        try:
            payload = load_payload(path)
        except Exception:                      # not a payload file
            continue
        if ((payload.get("meta") or {}).get("integrity") or {}).get("digest"):
            out.append(path.name)
    return out


def main():
    root = Path(__file__).resolve().parent.parent
    discovered = discover(root)
    files = sys.argv[1:] or discovered
    if not files:
        sys.exit("EMPTY GATE TARGET — refusing to report a pass: no shipped "
                 "payload carrying a digest was found, so this run would "
                 "verify nothing and exit clean.")
    if not sys.argv[1:]:
        missed = sorted(set(discovered) - set(files))
        if missed:
            sys.exit("EMPTY GATE TARGET — refusing to report a pass: these "
                     f"files carry a digest but would not be checked: {missed}")
    failed = False
    for name in files:
        path = (root / name) if not Path(name).is_absolute() else Path(name)
        payload = load_payload(path)
        recorded = (payload.get("meta", {}).get("integrity") or {}).get("digest")
        if not recorded:
            print(f"{path.name}: NO DIGEST RECORDED in meta.integrity")
            failed = True
            continue
        actual = canonical_digest(payload)
        ok = actual == recorded
        print(f"{path.name}: {'VERIFIED' if ok else 'MISMATCH'}\n"
              f"  recorded  sha256:{recorded}\n"
              f"  computed  sha256:{actual}")
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
