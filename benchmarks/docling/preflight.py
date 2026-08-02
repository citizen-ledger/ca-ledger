#!/usr/bin/env python3
"""Validate frozen inputs and reviewed preparation artifacts without Docling."""

import argparse
import json
import subprocess
from pathlib import Path

from harness import (StopGate, canonical_json, hash_tree, protected_status_lines,
                     sha256_file, truth_rows, verify_manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    inputs = verify_manifest(args.input.resolve(), args.manifest.resolve(), 5)
    truth = truth_rows(args.truth.resolve())
    required = ["DEPENDENCY_LOCK.txt", "WHEEL_SHA256SUMS", "SBOM.json",
                "LICENSES.json", "MODEL_MANIFEST.json", "ADVISORY_REPORT.json"]
    missing = [name for name in required if not (args.artifacts / name).is_file()]
    if missing:
        raise StopGate("missing reviewed preparation artifacts: " + ", ".join(missing))

    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            text=True, capture_output=True, check=True).stdout
    protected = protected_status_lines(status)
    if protected:
        raise StopGate("protected repository changes present: " + " | ".join(protected))

    payload = {
        "status": "prepared-not-authorized-for-execution",
        "inputs": inputs,
        "truth_sha256": sha256_file(args.truth),
        "truth_rows": len(truth),
        "artifact_manifest": hash_tree(args.artifacts),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                                   text=True, capture_output=True, check=True).stdout.strip(),
        "git_status": status.splitlines(),
    }
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / "PREFLIGHT.json").write_text(canonical_json(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
