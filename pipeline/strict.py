#!/usr/bin/env python3
"""
Citizen Ledger — StrictRow, the absent-column guard.

A source row that REFUSES an absent column instead of returning None.

FOUR CONFIDENT WRONG NUMBERS motivated this. The first three were in the
K-12 pipeline, where it originally lived:

  CharterNum  vs CharterNumber   the charter qualifier fell back to the
                                 school code and under-counted the
                                 collisions 40 -> 32 (#65)
  LEAName     vs Dname           reported nine phantom key collisions,
                                 all with empty names (#63)
  SchoolCode  vs SchoolID        the Alternative Form's vintage rename,
                                 which at least raised (#61)

The fourth is why this module exists as a shared file rather than a
class inside one pipeline. THE SAME PUBLISHER NAMES THE SAME COLUMN TWO
WAYS: SCO's city revenue dataset (rrtv-rsj9) calls its amount column
`value`; the county revenue dataset (emxv-k8xv) calls it `values`.
Reading `value` against the county set is not a typo an author would
catch by inspection — it is the source disagreeing with itself between
two datasets loaded by the same code path in the same run.

That miss happens to be loud at Socrata (a SoQL error naming the column)
but silent in Python once the JSON is in hand: `row.get("value")` on a
county row returns None, `float(None or 0)` is 0.0, and the pipeline
reports a county that raised no revenue. StrictRow makes the second half
loud too.

An absent column and an empty column are indistinguishable through
`.get()`, and the empty one produces an answer rather than an error. So
the miss is made loud: `row["Nope"]` raises KeyError as a plain dict
does, and `row.get("Nope")` — the form that used to be silent — raises
too. A caller that genuinely wants "absent is acceptable" must say so
with `row.optional("Nope")`, which is greppable and rare.

This does not protect against a column that exists and holds the wrong
thing. It protects against the failure mode that has actually occurred
four times: a name that is not there at all.
"""


class StrictRow(dict):
    """A dict whose missing keys raise instead of reading as empty."""

    __slots__ = ("_table",)

    def __init__(self, mapping, table):
        super().__init__(mapping)
        self._table = table

    def _missing(self, key):
        return KeyError(
            f"COLUMN {key!r} DOES NOT EXIST in {self._table}. Its columns "
            f"are: {', '.join(sorted(k for k in self if k))}. An absent "
            "column reads as empty and produces a confident wrong answer; "
            "use the real name, or row.optional() if absence is expected.")

    def __getitem__(self, key):
        if key not in self:
            raise self._missing(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        """Deliberately NOT dict.get: a typo must not read as an empty
        value. Use optional() where absence is a real possibility."""
        if key not in self:
            raise self._missing(key)
        return super().__getitem__(key)

    def optional(self, key, default=None):
        """The declared escape hatch: this column may legitimately be
        absent in some vintage, and the caller has decided what that
        means."""
        return super().get(key, default)


def amount_column(row, *candidates):
    """Return the FIRST candidate column this row actually has.

    The declared way to handle a publisher that names one quantity two
    ways across datasets. It is deliberately explicit — the caller lists
    the names it will accept — rather than a sniff over whatever numeric
    column happens to be present.

    Raises if NONE of the candidates exists, because summing a column
    that is not there is the failure this module exists to prevent.
    """
    for name in candidates:
        if name in row:
            return name
    raise KeyError(
        f"NONE OF THE AMOUNT COLUMNS {candidates!r} EXISTS in "
        f"{row._table if isinstance(row, StrictRow) else 'row'}. Its columns "
        f"are: {', '.join(sorted(k for k in row if k))}. Summing an absent "
        "column would report zero dollars for every row, which reads as a "
        "government that raised no revenue rather than as a bug.")
