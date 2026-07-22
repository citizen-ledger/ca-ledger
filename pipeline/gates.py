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


def check_rows(n, minimum, what, consequence=""):
    """The floor test itself, returning a message instead of raising.

    TWO DISPOSITIONS, ONE RULE. Some pipelines refuse at the first bad
    thing they see; others COLLECT every failure and print them together
    before exiting, so an operator learns all of what broke in one run
    rather than one item per attempt. Both are legitimate, and the
    difference is disposition, not semantics.

    Before this existed the collecting pipelines could not use
    require_rows — it raises — so each hand-rolled its own floor inline.
    Those floors were then invisible to the coverage test, which is how
    the county's floor came to sit outside the guard the repo built for
    exactly this. Callers that batch use check_rows and append; callers
    that stop use require_rows. Same rule, same message, both visible.

    Returns the failure message, or None when the floor is met.
    """
    if minimum < 1:
        raise ValueError(
            "check_rows: a minimum of zero would accept an empty gate, "
            "which is the defect this guard exists to prevent")
    if n >= minimum:
        return None
    tail = f" {consequence}" if consequence else ""
    return (f"EMPTY GATE TARGET — refusing to report a pass: {what} yielded "
            f"{n:,} row(s), below the {minimum:,} this source must produce. A "
            f"gate that iterates nothing accumulates no failures and reports "
            f"success.{tail}")


def require_rows(n, minimum, what, consequence=""):
    """A gate must actually check rows. `n` is how many it will check and
    `minimum` the fewest that can be legitimate for this source.

    A minimum of zero is not accepted: 'at least none' is not a check.
    Callers state the real floor, so a vintage that parses to a handful
    of rows fails as loudly as one that parses to none.

    The stopping disposition of check_rows.
    """
    msg = check_rows(n, minimum, what, consequence)
    if msg is None:
        return n
    raise VacuousGate(msg + " Nothing written.")


def check_exact(n, expected, what, consequence=""):
    """An entity count the source publishes as a FIXED number — 57
    counties, 23 CSU campuses, 73 CCC districts — is a stronger statement
    than a floor, and is stated as one.

    Not a floor with the bar set high: 58 counties is as wrong as 56, and
    a floor would accept it silently. Where a layer knows its own roster
    size, saying 'at least' throws away a fact.

    An expected of zero is refused for the same reason require_rows
    refuses a minimum of zero: a gate expecting nothing cannot fail.

    Returns the failure message, or None when the count matches.
    """
    if expected < 1:
        raise ValueError(
            "check_exact: an expected count of zero would accept an empty "
            "gate, which is the defect this guard exists to prevent")
    if n == expected:
        return None
    tail = f" {consequence}" if consequence else ""
    return (f"ENTITY COUNT WRONG — refusing to report a pass: {what} yielded "
            f"{n:,}, and this source publishes exactly {expected:,}. A count "
            f"that has moved means the roster changed or the parse did; "
            f"either way the figures beneath it are not the ones the gate "
            f"was written against.{tail}")


def require_exact(n, expected, what, consequence=""):
    """The stopping disposition of check_exact."""
    msg = check_exact(n, expected, what, consequence)
    if msg is None:
        return n
    raise VacuousGate(msg + " Nothing written.")
