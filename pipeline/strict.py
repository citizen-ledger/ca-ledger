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

# ---------------------------------------------------------------- headers
#
# THE SAME DEFECT, IN EVERY OTHER FORMAT.
#
# StrictRow above guards a row that already HAS names — an .mdb table, a
# Socrata JSON object, a csv.DictReader mapping. It cannot help a reader
# that never bound names at all: a spreadsheet row read as `row[2]`, a
# TSV split into `parts[5]`, a fixed-width line indexed by position.
#
# That is not a different defect. It is the same one with the failure
# moved earlier, and it has now happened here: the FY2016-17 city
# workbook puts Entity ID / Name / Fiscal Year in different columns from
# the FY2022-23 one, so a positional read that was correct on the newer
# vintage returned entity ids where the fiscal year belonged on the older
# one — a wrong column producing confident values, silently, exactly what
# StrictRow exists to make loud.
#
# The header was present in the file both times. Nothing read it.
#
# So: bind the header, then read by name. `bind` for a whole row,
# `column` when a caller needs one index (openpyxl streaming, where
# rebinding every row would cost more than it is worth).

def column(header, *aliases, source="source", required=True):
    """Resolve ONE column index by name, refusing ambiguity and absence.

    Aliases are compared on a whitespace- and case-insensitive form,
    because publishers vary "Entity ID" / "EntityID" / "entity id" across
    vintages of the same file. Exactly one column must match: zero means
    the caller would read nothing, and more than one means the caller
    cannot know which it got — both are refusals rather than a pick.
    """
    want = {str(a).replace(" ", "").lower() for a in aliases}
    hits = [i for i, h in enumerate(header)
            if h is not None and str(h).replace(" ", "").lower() in want]
    if len(hits) == 1:
        return hits[0]
    if not hits and not required:
        return None
    names = [str(h) for h in header if h is not None][:40]
    raise KeyError(
        f"COLUMN {sorted(want)!r} MATCHED {len(hits)} COLUMNS in {source}. "
        f"Its headers are: {names}. Reading a column by position instead "
        "would produce a confident wrong value rather than an error.")


def bind(header, row, source="source", strict_width=True):
    """Bind a positional row to its header and return a StrictRow.

    `strict_width` refuses a row that is longer than the header, because
    zip() would silently drop the overflow — the trailing columns of a
    vintage that grew would vanish with no error. A SHORTER row is
    allowed and its missing names simply do not exist, which StrictRow
    then refuses on read: that is the honest representation of a row the
    publisher left ragged.
    """
    if strict_width and len(row) > len(header):
        raise KeyError(
            f"ROW IS WIDER THAN THE HEADER in {source}: {len(row)} values "
            f"against {len(header)} names. zip() would drop the last "
            f"{len(row) - len(header)} silently, so the columns a newer "
            "vintage added would vanish without an error.")
    names = [None if h is None else str(h).strip() for h in header]
    return StrictRow({n: v for n, v in zip(names, row) if n}, source)


def first_present(row, *aliases):
    """The first alias this row actually has, or a refusal.

    Same intent as amount_column above, for the header-bound case: a
    publisher (or our own cache format) may spell one column two ways
    across vintages, and the caller lists the spellings it accepts rather
    than falling back to a position.
    """
    for name in aliases:
        if name in row:
            return name
    raise KeyError(
        f"NONE OF {aliases!r} EXISTS in this row. Its columns are: "
        f"{sorted(k for k in row if k)}.")
