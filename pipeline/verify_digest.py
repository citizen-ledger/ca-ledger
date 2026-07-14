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


def main():
    files = sys.argv[1:] or ["data.js", "city-data.js", "city-geo.js", "county-data.js", "county-geo.js", "district-data.js"]
    root = Path(__file__).resolve().parent.parent
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
