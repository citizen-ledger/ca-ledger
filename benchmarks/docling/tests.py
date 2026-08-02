#!/usr/bin/env python3

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import (StopGate, artifact_identity, assert_offline_environment,
                     canonical_json, hash_tree, installed_packages,
                     protected_status_lines, resolve_beneath, sha256_file,
                     truth_rows, verify_manifest, verify_reviewed_evidence,
                     verify_reviewed_inputs)


class HarnessTests(unittest.TestCase):
    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StopGate):
                resolve_beneath(Path(tmp), "../outside")

    def test_verifies_exact_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_bytes(b"%PDF-synthetic")
            manifest = root / "SHA256SUMS"
            manifest.write_text(f"{sha256_file(root / 'a.pdf')}  a.pdf\n", encoding="utf-8")
            self.assertEqual(verify_manifest(root, manifest, 1)[0]["path"], "a.pdf")
            (root / "a.pdf").write_bytes(b"changed")
            with self.assertRaises(StopGate):
                verify_manifest(root, manifest, 1)

    def test_truth_requires_completed_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "truth.csv"
            fields = ["document_id", "page", "table", "row", "column",
                      "printed_value", "normalized_value", "unit", "expected_gate",
                      "review_status"]
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({name: "x" for name in fields} | {"review_status": "pending"})
            with self.assertRaises(StopGate):
                truth_rows(path)

    def test_protected_diff_detection_handles_rename(self):
        status = (" M pipeline/gates.py\nR  old.js -> data.js\n"
                  "?? nested/new-layer-data.js\n M nested/future-data.js\n"
                  "R  nested/retired-data.js -> nested/readme.txt\n"
                  "?? benchmarks/docling/\n")
        self.assertEqual(len(protected_status_lines(status)), 5)

    def test_environment_allowlist_rejects_named_private_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StopGate) as raised:
                assert_offline_environment({
                    "DOCLING_BENCHMARK_OFFLINE": "1",
                    "PATH": "/usr/bin",
                    "BUZZ_PRIVATE_KEY": "synthetic-secret",
                }, Path(tmp))
            self.assertIn("BUZZ_PRIVATE_KEY", str(raised.exception))
            self.assertNotIn("synthetic-secret", str(raised.exception))

    def test_environment_allowlist_accepts_only_minimal_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert_offline_environment({
                "DOCLING_BENCHMARK_OFFLINE": "1",
                "PATH": "/approved/venv/bin:/usr/bin",
                "PYTHONHASHSEED": "0",
                "TMPDIR": "/disposable/tmp",
            }, Path(tmp))

    def test_environment_rejects_named_credential_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".aws").mkdir()
            (home / ".aws" / "credentials").write_text("synthetic", encoding="utf-8")
            with self.assertRaisesRegex(StopGate, "aws-credentials"):
                assert_offline_environment({
                    "DOCLING_BENCHMARK_OFFLINE": "1", "PATH": "/usr/bin"
                }, home)

    def test_collision_resistant_artifact_identity_uses_full_path(self):
        first = artifact_identity("first/shared.pdf")
        second = artifact_identity("second/shared.pdf")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith("-shared"))

    def test_reviewed_inputs_reject_manifest_and_input_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "SHA256SUMS"
            manifest.write_text("0" * 64 + "  files/a.pdf\n", encoding="utf-8")
            inputs = [{"path": "files/a.pdf", "sha256": "0" * 64, "bytes": 1}]
            reviewed = {"corpus_manifest_sha256": sha256_file(manifest), "inputs": inputs}
            verify_reviewed_inputs(reviewed, manifest, inputs)
            manifest.write_text("1" * 64 + "  files/a.pdf\n", encoding="utf-8")
            with self.assertRaisesRegex(StopGate, "manifest hash drift"):
                verify_reviewed_inputs(reviewed, manifest, inputs)
            manifest.write_text("0" * 64 + "  files/a.pdf\n", encoding="utf-8")
            with self.assertRaisesRegex(StopGate, "differ"):
                verify_reviewed_inputs(reviewed, manifest, inputs + [{"path": "files/b.pdf"}])

    def evidence_fixture(self, root: Path):
        artifacts = root / "artifacts"
        artifacts.mkdir(parents=True)
        config = root / "config.json"
        model = artifacts / "MODEL_MANIFEST.json"
        config.write_text(canonical_json({
            "benchmark_id": "citizen-ledger-docling-five-document-v1",
            "docling_version": "2.117.0",
        }), encoding="utf-8")
        model.write_text("{\"files\":[]}\n", encoding="utf-8")
        packages = [item for item in installed_packages() if item["name"] != "docling"]
        packages.append({"name": "docling", "version": "2.117.0"})
        packages.sort(key=lambda item: item["name"])
        manifest = root / "CANONICAL_EVIDENCE.json"
        manifest.write_text(canonical_json({
            "schema": 1,
            "status": "prepared-for-security-review",
            "benchmark_id": "citizen-ledger-docling-five-document-v1",
            "artifact_manifest": hash_tree(artifacts),
            "config_sha256": sha256_file(config),
            "model_manifest_sha256": sha256_file(model),
            "installed_packages": packages,
        }), encoding="utf-8")
        approval = root / "SECURITY_APPROVAL.json"
        approval.write_text(canonical_json({
            "schema": 1, "status": "approved", "approved_by": "security-reviewer",
            "benchmark_id": "citizen-ledger-docling-five-document-v1",
            "approved_at": "2026-08-02T00:00:00-07:00",
            "canonical_evidence_sha256": sha256_file(manifest),
        }), encoding="utf-8")
        return artifacts, config, model, manifest, approval, packages

    def test_reviewed_evidence_accepts_exact_approved_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.evidence_fixture(Path(tmp))
            with patch("harness.installed_packages", return_value=parts[5]):
                self.assertEqual(verify_reviewed_evidence(parts[3], parts[4], parts[0],
                                                          parts[1], parts[2])["schema"], 1)

    def test_reviewed_evidence_rejects_missing_unapproved_and_changed_packets(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts, config, model, manifest, approval, packages = self.evidence_fixture(Path(tmp))
            with patch("harness.installed_packages", return_value=packages):
                with self.assertRaisesRegex(StopGate, "required"):
                    verify_reviewed_evidence(Path(tmp) / "missing.json", approval,
                                             artifacts, config, model)
            approval.write_text(canonical_json({"schema": 1, "status": "withheld"}),
                                encoding="utf-8")
            with patch("harness.installed_packages", return_value=packages):
                with self.assertRaisesRegex(StopGate, "unapproved"):
                    verify_reviewed_evidence(manifest, approval, artifacts, config, model)
            _, _, _, manifest, approval, packages = self.evidence_fixture(Path(tmp) / "second")
            second_artifacts = manifest.parent / "artifacts"
            (second_artifacts / "SBOM.json").write_text("{}\n", encoding="utf-8")
            with patch("harness.installed_packages", return_value=packages):
                with self.assertRaisesRegex(StopGate, "artifact drift"):
                    verify_reviewed_evidence(manifest, approval, second_artifacts,
                                             manifest.parent / "config.json",
                                             second_artifacts / "MODEL_MANIFEST.json")
            third = self.evidence_fixture(Path(tmp) / "third")
            changed_packages = [dict(item) for item in third[5]]
            next(item for item in changed_packages if item["name"] == "docling")["version"] = "9.9.9"
            with patch("harness.installed_packages", return_value=changed_packages):
                with self.assertRaisesRegex(StopGate, "package/version inventory drift"):
                    verify_reviewed_evidence(third[3], third[4], third[0],
                                             third[1], third[2])


if __name__ == "__main__":
    unittest.main()
