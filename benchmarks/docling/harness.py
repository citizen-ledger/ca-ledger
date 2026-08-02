#!/usr/bin/env python3
"""Shared fail-closed helpers for the Citizen Ledger Docling benchmark."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Iterable

PROTECTED_NAMES = {
    "data.js", "city-data.js", "county-data.js", "district-data.js",
    "school-data.js", "csu-data.js", "ccc-data.js", "uc-data.js",
    "compensation-data.js", "deflator-data.js", "search-index.js",
}
ALLOWED_OFFLINE_ENVIRONMENT = {
    "DOCLING_BENCHMARK_OFFLINE", "LANG", "LC_ALL", "PATH", "PYTHONHASHSEED",
    "TMPDIR",
}
KNOWN_CREDENTIAL_FILES = {
    ".aws/credentials": "aws-credentials",
    ".config/gcloud/application_default_credentials.json": "gcloud-application-default",
    ".docker/config.json": "docker-config",
    ".kube/config": "kube-config",
    ".netrc": "netrc",
    ".ssh": "ssh-directory",
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


def installed_packages() -> list[dict[str, str]]:
    packages = {
        (distribution.metadata.get("Name") or "").lower().replace("_", "-"): distribution.version
        for distribution in importlib.metadata.distributions()
    }
    return [{"name": name, "version": packages[name]} for name in sorted(packages) if name]


def package_version(packages: list[dict[str, str]], name: str) -> str | None:
    normalized = name.lower().replace("_", "-")
    return next((item["version"] for item in packages if item["name"] == normalized), None)


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


def hash_code_tree(root: Path) -> list[dict[str, object]]:
    out = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        out.append({"path": relative.as_posix(), "sha256": sha256_file(path),
                    "bytes": path.stat().st_size})
    return out


def assert_offline_environment(environ: dict[str, str] | None = None,
                               home: Path | None = None) -> None:
    environment = dict(os.environ if environ is None else environ)
    if environment.get("DOCLING_BENCHMARK_OFFLINE") != "1":
        raise StopGate("DOCLING_BENCHMARK_OFFLINE=1 is required")
    unexpected = sorted(set(environment) - ALLOWED_OFFLINE_ENVIRONMENT)
    if unexpected:
        raise StopGate("environment names outside allowlist: " + ", ".join(unexpected))
    credential_home = Path.home() if home is None else home
    mounted = [label for relative, label in KNOWN_CREDENTIAL_FILES.items()
               if (credential_home / relative).exists()]
    if mounted:
        raise StopGate("credential file mounts present: " + ", ".join(sorted(mounted)))


def protected_status_lines(status: str) -> list[str]:
    protected = []
    for line in status.splitlines():
        path_texts = line[3:].split(" -> ")
        if any(is_protected_repo_path(path_text) for path_text in path_texts):
            protected.append(line)
    return protected


def is_protected_repo_path(path_text: str) -> bool:
    path_text = path_text.strip('"')
    path = Path(path_text)
    return (path_text == "pipeline" or path_text.startswith("pipeline/")
            or path.name in PROTECTED_NAMES or path.name.endswith("-data.js"))


def artifact_identity(relative_path: str) -> str:
    normalized = Path(relative_path).as_posix()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    basename = Path(normalized).stem
    safe_basename = "".join(character if character.isalnum() or character in "-_"
                            else "_" for character in basename)[:80]
    return f"{digest}-{safe_basename or 'document'}"


def verify_reviewed_evidence(manifest_path: Path, approval_path: Path,
                             artifacts_path: Path, config_path: Path,
                             model_manifest_path: Path, current_git_head: str,
                             code_root: Path,
                             environment_names: list[str]) -> dict[str, object]:
    if not manifest_path.is_file() or not approval_path.is_file():
        raise StopGate("canonical evidence manifest and security approval are required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("status") != "prepared-for-security-review":
        raise StopGate("canonical evidence manifest is incomplete")
    if approval.get("schema") != 1 or approval.get("status") != "approved":
        raise StopGate("security approval is missing or unapproved")
    manifest_hash = sha256_file(manifest_path)
    if approval.get("canonical_evidence_sha256") != manifest_hash:
        raise StopGate("security approval does not bind the canonical evidence manifest")
    if not approval.get("approved_by") or not approval.get("approved_at"):
        raise StopGate("security approval lacks reviewer identity or timestamp")
    if manifest.get("config_sha256") != sha256_file(config_path):
        raise StopGate("reviewed configuration hash drift")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if manifest.get("benchmark_id") != config.get("benchmark_id"):
        raise StopGate("reviewed benchmark identity drift")
    if approval.get("benchmark_id") != config.get("benchmark_id"):
        raise StopGate("security approval does not name the reviewed benchmark")
    if manifest.get("git_head") != current_git_head:
        raise StopGate("current repository HEAD differs from reviewed evidence")
    if manifest.get("code_tree_manifest") != hash_code_tree(code_root):
        raise StopGate("benchmark harness code-tree drift")
    if manifest.get("environment_names") != sorted(environment_names):
        raise StopGate("runtime environment-name set differs from reviewed evidence")
    if manifest.get("model_manifest_sha256") != sha256_file(model_manifest_path):
        raise StopGate("reviewed model manifest hash drift")
    if manifest.get("artifact_manifest") != hash_tree(artifacts_path):
        raise StopGate("reviewed preparation artifact drift")
    if manifest.get("installed_packages") != installed_packages():
        raise StopGate("installed package/version inventory drift")
    if package_version(manifest["installed_packages"], "docling") != config.get("docling_version"):
        raise StopGate("installed Docling version does not match reviewed configuration")
    return manifest


def verify_reviewed_inputs(reviewed_evidence: dict[str, object],
                           input_manifest_path: Path,
                           verified_inputs: list[dict[str, object]]) -> None:
    if reviewed_evidence.get("corpus_manifest_sha256") != sha256_file(input_manifest_path):
        raise StopGate("reviewed corpus manifest hash drift")
    if reviewed_evidence.get("inputs") != verified_inputs:
        raise StopGate("verified corpus inputs differ from reviewed evidence")
