# Reading the Ledger

A plain-language guide to what the record is and how to read it. The
[about &amp; method page](../about.html) states the sources and the checks;
this goes a step deeper into the ideas a reader needs to hold to use the
figures without misreading them. It is written to be read once and
referred back to, not to persuade.

---

## What this is

Citizen Ledger is a record of what California governments budgeted and
spent, assembled from those governments' own published figures and checked
against those governments' own published totals before anything appears.
It is not an analysis. It reports what was budgeted, what was spent, and by
whom — not whether any of it was wise. That question is left to the reader,
on purpose, and the record avoids the adjectives and scores that would
answer it for you.

It is built as plain files that open in any browser, with no server, no
account, and no login. The reasons for that are practical and are set out
in the [scope document](SCOPE.md); the short version is that the tools this
one is modelled on mostly died when their funding or their maintainer moved
on, and a record that is only files has less to lose.

## The layers, and what each one is

The site is organised into **layers**, one per kind of government or
report. They are not slices of a single dataset; each comes from a
different source, on a different accounting basis, at a different
resolution. That is why they are kept apart and never added together.

- **State budget** — what the Legislature *enacted*: a spending plan, fixed
  when each year's Budget Act is signed, to the department, fund, and
  program. This is a plan, not a record of spending.
- **State actuals** — what was *actually spent*, on the same
  Budgetary-Legal basis as the plan it sits beside, drawn from the state's
  own Schedule 9. Actuals arrive late — the following January for a year
  that ended in June — so the newest budget year has enacted figures only,
  and the page says so rather than showing a blank.
- **Cities &amp; counties** — the annual financial reports every city and
  county files with the State Controller: retrospective actuals, as filed,
  to the state form line.
- **K-12 schools** — the unaudited general ledgers every district, county
  office, and charter files under the state's Standardized Account Code
  Structure, compared per pupil (per ADA, education's standard
  denominator).
- **Higher education** — three systems, each on audited or
  official-workload figures and each stated on its own terms: **CSU**
  campuses, the **community-college** districts, and the **UC** campuses
  (whose raw figure is nearly two-fifths hospital ledger, so its medical
  centers, auxiliaries, and DOE laboratory are separated out on UC's own
  published lines and shown beside the teaching-and-research remainder,
  never deleted).
- **Special districts** — the thousands of single-purpose local
  governments (water, fire, transit, and the rest), published *as filed*.
  This is the one layer with no published total to check against, and it
  says so on every record.

## Why the layers do not add up

The most common way to misread a set of government figures is to sum them.
On this site the layers deliberately never sum, for a simple reason: **the
same dollar appears in more than one of them.** Roughly half of what
counties and school districts report *receiving* is money the state budget
already shows *sending*. A number that added the state budget to county
revenues to school spending would count that dollar two or three times and
call the result a total.

So wherever two layers meet — on the address view, on each higher-education
page — the site states that the figures do not add, gives the measured
overlap, and never prints a combined total. The right question is never
"what is the sum," it is "what did *this* government, on *this* basis,
budget or spend."

Accounting bases differ too, and are never mixed: an *enacted appropriation*
(a plan) is not an *actual expenditure* (a record), and neither is an
*audited GAAP figure* (a third thing again). Each page names its basis.

## The gate, and its tiers

Before any figure is published it is recomputed from the raw source and
must reproduce a total the source itself published. If it does not, nothing
is written and the previous data stays. That check is called the
**reconciliation gate**, and it is the site's central discipline.

What the gate reconciles *to* is not the same kind of thing on every layer,
and the resolution is named accurately rather than rounded up to a tidy
claim of uniformity:

- **To the cent** — K-12 districts, against CDE's published Current Expense
  of Education.
- **To the dollar** — community-college districts, against the Chancellor's
  Office's printed statewide total (and independently validated off the
  portal by each district's mandatory CPA audit).
- **To the thousand** — CSU and UC, against their audited statement totals.
  "Exact to the thousand" is not a looser check; it is exact fidelity at
  the *source's own* resolution, because those statements are denominated in
  thousands. It is a different tier from the cent, named as one.
- **Exact, in thousands** — the state budget, against the Department of
  Finance's own statewide total.
- **Pinned, not reconciled** — special districts, which have no published
  control total. Their figures carry a tamper-evident pin, which proves the
  file has not been altered since it was built but is *not* a claim that
  anyone confirmed the figures are right. That distinction is stated on
  every special-district record.

A total can be correct while its parts are mislabelled, so a second family
of checks — **shape gates** — verifies that the classification is sane: a
police department cannot silently vanish for a year, a catch-all bucket
cannot absorb a city's spending. A reconciled total and a sane shape are
different guarantees, and the site keeps both.

## "Not published" is not zero

This is the distinction most worth carrying away. Across the record you
will meet three different things that a careless system would render
identically, and this one keeps apart:

- **A real zero** — the government reported this figure, and it is zero. A
  city that contracts its fire service to the county files a fire line of
  $0, and that zero is a true statement about the filing.
- **Not published** — the source does not provide this figure, so the
  Ledger does not have it and will not derive one. It is shown as "not
  published", with the reason, and it is never counted as zero. A number
  that is unknown is left *absent* (so an attempt to use it yields not-a-
  number, which is loud, rather than 0, which is silent and wrong); a
  yes/no that is unknown is shown as a third value, because "no" is a real
  answer that has no room left to also mean "we don't know."
- **A rendering gap** — a genuine display error, which the site treats as a
  bug, not a value.

Examples you will actually encounter: UC's FY2019-20 is **held** — its
unaudited campus table cannot be reconciled to the audited total, off by a
stubborn 351 thousand where every other year ties exactly, so it is shown
as a held, not-published point rather than published at a lower standard.
Several community-college years publish Current Expense of Education but not
the apportionment-derived figures, because the document that would carry
them either does not exist for that year or prints a value that cannot be
reconciled. In every such case the site would rather show a labelled
absence than a confident wrong number.

## When a figure changes

Published figures are not permanent — a source can restate, redefine, or
file late, and the Ledger can find an error in its own extraction. Every
refresh compares the figures it is about to publish against the ones
already published and records what moved, in the [record of
changes](../revisions.html) — including figures that *appear* and
*disappear*, not only those whose value changes, because a reclassification
moves money between categories that did not previously exist.

That record says *what* changed and *by how much*. It does not say *why*,
and that is deliberate: a source restating a figure and a source redefining
what the figure counts look identical from outside, differing only in the
source's intent, which lives in its release notes rather than in its
numbers. Guessing at a cause would be exactly the kind of unearned claim
the rest of the record avoids. The one exception is a change the Ledger
itself made, where the cause is known because it is its own commit, and
those are labelled as such.

## How to check any figure yourself

Nothing here asks to be taken on trust. Every figure carries its source,
its accounting basis, and a permalink that reproduces the exact view. Every
data file carries a SHA-256 digest shown on its page; download the file,
run the one-line verifier in the repository, and the recomputed digest must
match. The pipelines that build each file, and the investigation documents
that decided what to publish and what to refuse, are all in the same public
repository — so any number can be traced from the page back to the official
source that produced it, and the reasoning can be checked alongside the
arithmetic.
