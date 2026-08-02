# Citizen Ledger Docling benchmark harness

Preparation-only harness for the approved offline document-extraction benchmark.
It is not part of the publication pipeline and must never write to repository
data, `pipeline/`, or generated `*-data.js` files.

## Security boundary

- Run from a disposable copy with no credentials or SSH agent.
- `prepare.py` is the only network-authorized phase. It creates a hashed wheel
  house and model cache; security reviews those artifacts before execution.
- `preflight.py`, `run.py`, and `score.py` require the frozen inputs and reviewed
  manifests. `run.py` refuses unless `DOCLING_BENCHMARK_OFFLINE=1` and proxy
  variables are absent.
- Raw and normalized output goes beneath the explicit quarantine directory.
- The runner uses only local PDF paths, disables remote services, fixes the
  standard PDF pipeline to TableFormer accurate mode, and caps input bytes and
  pages.
- Any input/model/dependency hash drift, attempted output escape, or protected
  repository diff is a stop.

Benchmark execution is not authorized until Edward verifies the preparation
packet. Do not use `run.py` merely because the scripts exist.

## Files

- `config.json`: frozen processing and resource-limit configuration.
- `requirements.in`: direct dependency request; exact lock is produced only on
  the approved Python/platform pair.
- `prepare.py`: controlled online acquisition, hash manifests, SBOM, licenses.
- `preflight.py`: offline corpus/artifact/config validation and clean-diff guard.
- `run.py`: bounded local conversion and normalized output hashing.
- `score.py`: exact truth-cell/page scoring from a reviewed observation CSV.
- `tests.py`: synthetic tests; does not import or execute Docling.
- `docs/`: evidence templates and operating procedures.

## Preparation sequence

1. Provision a disposable Python 3.11 environment. The current workstation
   default is Python 3.9.6 and is intentionally refused because Docling 2.117.0
   requires Python 3.10 or newer.
2. Copy the five approved PDFs and reviewed manifests into the disposable input
   directory. Do not point the harness at the editorial source directory.
3. In a separately approved network-enabled acquisition environment:

   ```sh
   python3.11 benchmarks/docling/prepare.py --workspace /disposable/docling-prep
   ```

4. Review `evidence/DEPENDENCY_LOCK.txt`, `evidence/WHEEL_SHA256SUMS`,
   `evidence/SBOM.json`, `evidence/LICENSES.json`, `evidence/MODEL_MANIFEST.json`,
   and the advisory report. Make the wheelhouse/model cache read-only.
5. Disable network egress at the OS/container boundary, remove all credentials,
   then run `preflight.py`. Edward must approve the resulting packet before any
   corpus execution.

The scripts do not claim that environment variables alone disable the network;
the operator must supply and evidence an OS/container egress control.
