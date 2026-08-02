#!/usr/bin/env python3

import csv
import tempfile
import unittest
from pathlib import Path

from harness import (StopGate, protected_status_lines, resolve_beneath,
                     sha256_file, truth_rows, verify_manifest)


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
        status = " M pipeline/gates.py\nR  old.js -> data.js\n?? benchmarks/docling/\n"
        self.assertEqual(len(protected_status_lines(status)), 2)


if __name__ == "__main__":
    unittest.main()
