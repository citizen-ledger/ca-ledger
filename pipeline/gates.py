#!/usr/bin/env python3
"""
Citizen Ledger — the non-empty gate guard.

A GATE WHOSE COMPARISON TARGET IS EMPTY PASSES VACUOUSLY. Reconciling
against nothing is a failure, not a pass.

This is the dormant-assertion lesson moved from the test suite into the
pipeline. A test that is defined but never called reports success while
proving nothing; so does a gate that loops over an empty collection,
sums an empty list to zero and compares it against another zero, or
guards its own comparison behind `if control.get(k) and ...` so that a
missing control silently skips the check.

TWO REAL INSTANCES motivated this module.

  SHIPPED. fetch_ccc_data.build() reconciled funded FTES and state
  General Fund against `appn_statewide`, a dict built by scanning the
  Exhibit C PDF for a page whose heading ends in "CCD" or "District".
  The statewide summary page is headed "Statewide Totals", so it never
  matched, `appn_statewide` was always {}, and both comparisons were
  skipped by their own `and` guard. The build reported success. The
  figures were in fact correct — reconciled after the fix, funded FTES
  residual +0.01 on 1,100,664.61 and state GF residual exactly $0 — but
  nobody had ever checked. A false assurance is its own defect.

  LATENT. fetch_school_data's Current Expense header detector tests
  `str(row[0]) == "CO"`. The FY2018-19 vintage labels that column
  "CO Code", so the header is never found, the control table stays
  empty, and every downstream gate then iterates nothing: measured
  ce_rows=0, gate1_n=0, every gate green on zero districts.

USE
    from gates import require_target, require_rows

    require_target(statewide, "Exhibit C statewide totals",
                   "funded FTES and state GF cannot be reconciled")
    require_rows(len(ce), 900, "Current Expense districts")

Both raise SystemExit, which is this project's established "nothing is
written" signal — the same class as the classifier's refusal and the
control-total gates themselves.
"""


class VacuousGate(SystemExit):
    """Raised when a gate cannot do its job. A subclass of SystemExit so
    it stops the build the same way every other gate failure does, and a
    distinct type so tests can assert the specific refusal."""


def require_target(target, what, consequence=""):
    """The comparison target of a gate must exist and be non-empty.

    `target` is whatever the gate reconciles AGAINST — a published
    control dict, a parsed total, a lookup table. An empty one means the
    gate is about to pass without comparing anything.
    """
    if target:
        return target
    tail = f" {consequence}" if consequence else ""
    raise VacuousGate(
        f"EMPTY GATE TARGET — refusing to report a pass: {what} is empty or "
        f"missing, so the reconciliation that depends on it would be skipped "
        f"and the build would report success without having compared "
        f"anything.{tail} Reconciling against nothing is a failure, not a "
        f"pass; nothing written.")


def require_rows(n, minimum, what, consequence=""):
    """A gate must actually check rows. `n` is how many it will check and
    `minimum` the fewest that can be legitimate for this source.

    A minimum of zero is not accepted: 'at least none' is not a check.
    Callers state the real floor, so a vintage that parses to a handful
    of rows fails as loudly as one that parses to none.
    """
    if minimum < 1:
        raise ValueError(
            "require_rows: a minimum of zero would accept an empty gate, "
            "which is the defect this guard exists to prevent")
    if n >= minimum:
        return n
    tail = f" {consequence}" if consequence else ""
    raise VacuousGate(
        f"EMPTY GATE TARGET — refusing to report a pass: {what} yielded "
        f"{n:,} row(s), below the {minimum:,} this source must produce. A "
        f"gate that iterates nothing accumulates no failures and reports "
        f"success.{tail} Nothing written.")
