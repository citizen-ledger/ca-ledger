# License and provenance review record

Status: **incomplete / execution blocker** until controlled acquisition creates
the exact SBOM, wheel hashes, model manifest, model cards, and license texts.

Direct package request:

- `docling==2.117.0` — MIT application code; individual models require their own
  license review.
- `cyclonedx-bom==7.2.1` — SBOM tooling; license to be captured from the acquired
  distribution metadata.
- `pip-audit==2.9.0` — advisory tooling; license to be captured from the acquired
  distribution metadata.

Intended minimal model scope: standard PDF layout + TableFormer accurate mode and
the locally selected OCR backend. Picture classification, code/formula extraction,
VLM conversion, remote services, and hosted APIs are disabled/out of scope.

Official references:

- https://docling-project.github.io/docling/usage/advanced_options/
- https://docling-project.github.io/docling/usage/model_catalog/
- https://github.com/docling-project/docling
