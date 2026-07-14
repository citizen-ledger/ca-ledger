"""Shared record-integrity helper for the Citizen Ledger pipelines.

The digest is the SHA-256 of the JSON payload in canonical form
(sorted keys, compact separators, UTF-8, ensure_ascii=False) with the
meta.integrity field removed — so the digest can live inside the file
it certifies and still be independently recomputable.
"""

import copy
import hashlib
import json


def canonical_digest(payload: dict) -> str:
    clean = copy.deepcopy(payload)
    clean.get("meta", {}).pop("integrity", None)
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def stamp(payload: dict) -> dict:
    """Adds meta.integrity in place and returns the payload."""
    payload["meta"]["integrity"] = {
        "algorithm": "SHA-256",
        "digest": canonical_digest(payload),
        "verify": "python3 pipeline/verify_digest.py",
    }
    return payload
