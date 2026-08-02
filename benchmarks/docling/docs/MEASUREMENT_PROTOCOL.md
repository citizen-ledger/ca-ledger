# Measurement protocol

Report two comparisons separately. They answer different questions and must not
be blended.

## Fixed-target transcription

Measure active time to extract the already named 25 targets from already named
pages/tables, plus machine time. Zoe's 42-second row is a lower bound with
declared memory contamination. Preserve it as such; it cannot support the 30%
workflow-time gate.

## End-to-end workflow

Use the independent blinded pass as the primary baseline. Capture active minutes
separately for:

1. document/page/table discovery;
2. extraction of the 25 targets;
3. verification of units and publish/hold treatment.

For the assisted arm, capture the same three categories, machine runtime, and any
rework caused by missing, misaligned, or confidently wrong output. The 30% gate
uses end-to-end active time, not fixed-target transcription alone. Report median
and p75 only after the expanded corpus is large enough for those summaries to be
meaningful; for five documents, retain all per-document values.
