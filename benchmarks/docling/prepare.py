#!/usr/bin/env python3
"""Controlled network-enabled acquisition phase; never processes corpus PDFs."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from harness import StopGate, canonical_json, hash_tree, sha256_file


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, check=True, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        raise StopGate(f"controlled acquisition requires Python 3.11, got {platform.python_version()}")
    workspace = args.workspace.resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise StopGate("workspace must be absent or empty")
    workspace.mkdir(parents=True, exist_ok=True)
    venv_path, wheelhouse = workspace / "venv", workspace / "wheelhouse"
    models, evidence = workspace / "models", workspace / "evidence"
    wheelhouse.mkdir(); models.mkdir(); evidence.mkdir()
    venv.EnvBuilder(with_pip=True, clear=True).create(venv_path)
    python = venv_path / "bin" / "python"
    requirements = Path(__file__).with_name("requirements.in").resolve()

    run([str(python), "-m", "pip", "download", "--only-binary=:all:",
         "--dest", str(wheelhouse), "-r", str(requirements)])
    wheels = hash_tree(wheelhouse)
    (evidence / "WHEEL_SHA256SUMS").write_text("".join(
        f"{item['sha256']}  {item['path']}\n" for item in wheels), encoding="utf-8")
    run([str(python), "-m", "pip", "install", "--no-index",
         "--find-links", str(wheelhouse), "-r", str(requirements)])
    freeze = run([str(python), "-m", "pip", "freeze", "--all"],
                 capture_output=True).stdout
    (evidence / "DEPENDENCY_LOCK.txt").write_text(freeze, encoding="utf-8")

    run([str(venv_path / "bin" / "docling-tools"), "models", "download",
         "layout", "tableformer", "rapidocr", "--output-dir", str(models)])
    model_files = hash_tree(models)
    model_manifest = {
        "acquired_by": "docling-tools models download layout tableformer rapidocr",
        "docling_version": "2.117.0",
        "files": model_files,
        "status": "license-and-revision-review-required",
    }
    (evidence / "MODEL_MANIFEST.json").write_text(canonical_json(model_manifest), encoding="utf-8")

    sbom_path = evidence / "SBOM.json"
    run([str(venv_path / "bin" / "cyclonedx-py"), "environment", str(python),
         "--output-format", "JSON", "--output-file", str(sbom_path)])
    audit = subprocess.run([str(python), "-m", "pip_audit", "--format", "json"],
                           text=True, capture_output=True)
    (evidence / "ADVISORY_REPORT.json").write_text(audit.stdout or canonical_json({
        "error": audit.stderr, "exit_code": audit.returncode}), encoding="utf-8")

    distributions = []
    script = (
        "import importlib.metadata,json; "
        "print(json.dumps([{'name':d.metadata.get('Name'),'version':d.version,"
        "'license':d.metadata.get('License'),'license_expression':"
        "d.metadata.get('License-Expression'),'home_page':d.metadata.get('Home-page')} "
        "for d in importlib.metadata.distributions()],sort_keys=True))"
    )
    distributions = json.loads(run([str(python), "-c", script], capture_output=True).stdout)
    (evidence / "LICENSES.json").write_text(canonical_json({
        "packages": distributions,
        "review_status": "incomplete-until-security-disposes-every-package-and-model",
    }), encoding="utf-8")
    (evidence / "ACQUISITION.json").write_text(canonical_json({
        "python": platform.python_version(), "platform": platform.platform(),
        "requirements_sha256": sha256_file(requirements),
        "wheel_count": len(wheels), "model_file_count": len(model_files),
        "audit_exit_code": audit.returncode,
        "network_phase": "controlled-acquisition-only",
    }), encoding="utf-8")
    print(json.dumps({"workspace": str(workspace), "status": "review-required"}, indent=2))


if __name__ == "__main__":
    main()
