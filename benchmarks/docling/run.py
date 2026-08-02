#!/usr/bin/env python3
"""Offline-only bounded Docling conversion. Execution requires Security approval."""

from __future__ import annotations

import argparse
import json
import platform
import signal
import subprocess
import time
from pathlib import Path

from harness import (StopGate, assert_offline_environment, canonical_json,
                     hash_tree, protected_status_lines, resolve_beneath,
                     sha256_file, verify_manifest)


def timeout_handler(_signum, _frame):
    raise StopGate("per-document conversion timeout exceeded")


def normalize(document: object) -> object:
    """Remove only known volatile metadata; all semantic content remains."""
    if isinstance(document, dict):
        return {key: normalize(value) for key, value in sorted(document.items())
                if key not in {"created_at", "createdAt", "timestamp", "file_path"}}
    if isinstance(document, list):
        return [normalize(item) for item in document]
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    assert_offline_environment()
    if platform.python_version_tuple()[:2] != ("3", "11"):
        raise StopGate("benchmark requires the reviewed Python 3.11 environment")
    config_path = Path(__file__).with_name("config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    repo = Path(__file__).parents[2]
    status_before = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                                   text=True, capture_output=True, check=True).stdout
    if protected_status_lines(status_before):
        raise StopGate("protected repository changes exist before execution")
    inputs = verify_manifest(args.input.resolve(), args.manifest.resolve(), config["max_documents"])
    recorded_models = json.loads(args.model_manifest.read_text(encoding="utf-8"))
    if hash_tree(args.models.resolve()) != recorded_models.get("files"):
        raise StopGate("model artifact hash drift")
    run_root = resolve_beneath(args.quarantine.resolve(), args.run_id)
    if run_root.exists():
        raise StopGate("run directory already exists")
    raw_dir, normalized_dir = run_root / "raw", run_root / "normalized"
    raw_dir.mkdir(parents=True); normalized_dir.mkdir()

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(artifacts_path=args.models.resolve(),
                                 enable_remote_services=False,
                                 do_table_structure=True)
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    options.table_structure_options.do_cell_matching = True
    converter = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=options)
    })
    results = []
    for item in inputs:
        source = resolve_beneath(args.input.resolve(), item["path"])
        if item["bytes"] > config["max_file_size_bytes"]:
            raise StopGate(f"input exceeds byte limit: {item['path']}")
        started = time.monotonic()
        prior_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(config["timeout_seconds_per_document"])
        try:
            converted = converter.convert(source,
                                          max_num_pages=config["max_num_pages"],
                                          max_file_size=config["max_file_size_bytes"])
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prior_handler)
        elapsed = time.monotonic() - started
        raw = converted.document.export_to_dict()
        normalized = normalize(raw)
        stem = source.stem
        raw_path, normalized_path = raw_dir / f"{stem}.json", normalized_dir / f"{stem}.json"
        raw_path.write_text(canonical_json(raw), encoding="utf-8")
        normalized_path.write_text(canonical_json(normalized), encoding="utf-8")
        if raw_path.stat().st_size + normalized_path.stat().st_size > config["max_output_bytes_per_document"]:
            raise StopGate(f"output exceeds byte limit: {item['path']}")
        results.append({"input": item, "elapsed_seconds": elapsed,
                        "raw_sha256": sha256_file(raw_path),
                        "normalized_sha256": sha256_file(normalized_path)})
    manifest = {
        "status": "quarantined-draft-output",
        "run_id": args.run_id, "config_sha256": sha256_file(config_path),
        "model_manifest_sha256": sha256_file(args.model_manifest),
        "results": results,
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                                   text=True, capture_output=True, check=True).stdout.strip(),
    }
    status_after = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                                  text=True, capture_output=True, check=True).stdout
    if protected_status_lines(status_after):
        raise StopGate("protected repository changes appeared during execution")
    manifest["git_status_before"] = status_before.splitlines()
    manifest["git_status_after"] = status_after.splitlines()
    (run_root / "RUN_MANIFEST.json").write_text(canonical_json(manifest), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
