#!/usr/bin/env python3
"""Exact scorer for reviewed observations; never infers truth from Docling output."""

import argparse
import csv
import json
from pathlib import Path

from harness import StopGate, canonical_json, truth_rows


KEYS = ("document_id", "page", "table", "row", "column")


def key(row):
    return tuple(row[name] for name in KEYS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    truth = truth_rows(args.truth)
    with args.observations.open(newline="", encoding="utf-8") as stream:
        observations = list(csv.DictReader(stream))
    if not observations:
        raise StopGate("observation set is empty")
    observed = {key(row): row for row in observations}
    if len(observed) != len(observations):
        raise StopGate("duplicate observation coordinates")
    details = []
    for expected in truth:
        actual = observed.get(key(expected))
        exact = bool(actual and actual.get("observed_normalized_value") == expected["normalized_value"])
        page_found = bool(actual and actual.get("page_found", "").lower() == "true")
        details.append({"key": key(expected), "exact": exact, "page_found": page_found,
                        "expected": expected["normalized_value"],
                        "observed": actual.get("observed_normalized_value") if actual else None,
                        "confidence_grade": actual.get("confidence_grade") if actual else None})
    incorrect = [row for row in details if not row["exact"]]
    confident_incorrect = [row for row in incorrect
                           if (row["confidence_grade"] or "").upper() in {"GOOD", "EXCELLENT"}]
    result = {
        "truth_cells": len(details),
        "exact_cells": len(details) - len(incorrect),
        "exact_cell_accuracy": (len(details) - len(incorrect)) / len(details),
        "page_recall": sum(row["page_found"] for row in details) / len(details),
        "incorrect_cells": len(incorrect),
        "confident_incorrect_cells": len(confident_incorrect),
        "false_confidence_rate": len(confident_incorrect) / len(incorrect) if incorrect else 0,
        "details": details,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(result), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
