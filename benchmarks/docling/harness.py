#!/usr/bin/env python3
"""Shared fail-closed helpers for the Citizen Ledger Docling benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

PROTECTED_NAMES = {
    "data.js", "city-data.js", "county-data.js", "district-data.js",
    "school-data.js", "csu-data.js", "ccc-data.js", "uc-data.js",
    "compensation-data.js", "deflator-data.js", "search-index.js",
}


class StopGate(RuntimeError):
    """A benchmark condition that must stop preparation or execution."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) + "\n"


def resolve_beneath(root: Path, child: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / child).resolve()
    if candidate != root and root not in candidate.parents:
        raise StopGate(f"path escapes quarantine root: {candidate}")
    return candidate


def read_sha256_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise StopGate(f"invalid SHA-256 manifest line {number}")
        name = parts[1].lstrip("*")
        if name in result:
            raise StopGate(f"duplicate manifest path: {name}")
        result[name] = parts[0].lower()
    if not result:
        raise StopGate("empty SHA-256 manifest")
    return result


def verify_manifest(root: Path, manifest: Path,
                    maximum_files: int | None = None) -> list[dict[str, object]]:
    entries = read_sha256_manifest(manifest)
    if maximum_files is not None and len(entries) > maximum_files:
        raise StopGate(f"manifest has {len(entries)} files; maximum is {maximum_files}")
    verified = []
    for relative, expected in sorted(entries.items()):
        file_path = resolve_beneath(root, relative)
        if not file_path.is_file():
            raise StopGate(f"missing manifested file: {relative}")
        actual = sha256_file(file_path)
        if actual != expected:
            raise StopGate(f"hash mismatch for {relative}: {actual} != {expected}")
        verified.append({"path": relative, "sha256": actual,
                         "bytes": file_path.stat().st_size})
    return verified


def truth_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"document_id", "page", "table", "row", "column",
                "printed_value", "normalized_value", "unit", "expected_gate",
                "review_status"}
    if not rows or not required.issubset(rows[0]):
        raise StopGate("truth set is empty or missing required columns")
    if any("pending" in row["review_status"].lower() for row in rows):
        raise StopGate("truth set still contains a pending review")
    return rows


def hash_tree(root: Path, excluded: Iterable[str] = ()) -> list[dict[str, object]]:
    excluded_set = set(excluded)
    out = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded_set:
            continue
        out.append({"path": relative, "sha256": sha256_file(path),
                    "bytes": path.stat().st_size})
    return out


def assert_offline_environment() -> None:
    if os.environ.get("DOCLING_BENCHMARK_OFFLINE") != "1":
        raise StopGate("DOCLING_BENCHMARK_OFFLINE=1 is required")
    forbidden = [name for name in os.environ
                 if name.upper().endswith(("_TOKEN", "_API_KEY", "_SECRET"))]
    forbidden += [name for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                                    "SSH_AUTH_SOCK") if os.environ.get(name)]
    if forbidden:
        raise StopGate("credential/proxy variables present: " + ", ".join(sorted(set(forbidden))))


def protected_status_lines(status: str) -> list[str]:
    protected = []
    for line in status.splitlines():
        path_text = line[3:].split(" -> ")[-1]
        path = Path(path_text)
        if path_text == "pipeline" or path_text.startswith("pipeline/") or path.name in PROTECTED_NAMES:
            protected.append(line)
    return protected
