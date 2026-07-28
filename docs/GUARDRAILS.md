# Guardrails — what this site will not do, and why

*Adopted 2026-07-28 from the §8 guardrails of the July 2026 UI audit, with
the site's own standing refusals folded in. Recorded so the answer exists
before the pressure does.*

Every item below has been proposed, or will be. None is a matter of taste:
each would cost more than it returns, and the reason is stated so a future
maintainer can weigh it rather than re-derive it.

---

## 1. No ranking, in any form

No leaderboards, no "top spenders", no default sort that produces one —
**including in bulk exports, embeds and share cards, where the temptation
is strongest** because a ranked image travels further than an unranked one.

Cities, counties and districts are ordered **alphabetically**, always. A
reader who wants a ranking can sort the CSV; the arithmetic is theirs and
so is the judgement that follows from it.

## 2. No judgment colour

Direction is a **glyph (▲▼) in one ink**. Never red/green, never a
diverging palette, never heat on a figure. A second accent colour is not
available for data, and `#2b59d1` marks only things a reader can operate.

The caveat that the glyphs show direction and nothing more is stated once
per view, derived from whether a glyph actually rendered.

## 3. No derived scores

No anomaly flags, no deviation scores, no efficiency ratios, no per-capita
rankings dressed as analysis. The site has refused specific ratios by
measurement — the reserve ratio (V24), the deficit-beside-spending ratio
(V24a), compensation as a share of spending (V23a) — and the general rule
is the same: **if a reader wants a test, they take the CSV.**

## 4. No personalised tax-bill framing

"Where your taxes go" is refused on the address view and stays refused. The
site cannot know what any individual paid, and the framing invites a
precision the data does not carry.

## 5. No accounts, no logins, no server-side state

Saved views stay device-local. The durability argument — *it is only files,
so it outlives its funding* — depends on this, and so does the security
posture in `docs/SECURITY.md`.

## 6. No analytics

Nothing that would make the privacy statement on the address page less true
than it is now. That statement is load-bearing: the page sends a typed
address to a government geocoder and nowhere else, and a tracker would
make that sentence false.

## 7. No investigative framing

No cases, no exhibits, no watch lists, no "exposed". **The record serves
the auditor and the audited identically**, and the vocabulary has to prove
it. See §9 for where this ban applies and where it does not.

## 8. Do not shorten the method pages for conversion

Length is the proof. Structure it — statement inline, argument at an
anchor — but do not cut it. A method section short enough to skim is a
method section that has stopped doing its job.

## 9. Scope of the banned-terms scan

The scan covers **reader-facing instrument copy**: the data pages, the
front door, and the chrome shared across them. Banned there:

> ballooning · skyrocket · soaring · surging · plummet · slashed · bloated ·
> staggering · whopping · exploding · spiraling · runaway · boondoggle ·
> reckless · out of control · waste · overrun · savings · underspend ·
> mismanage · **expose · wasteful · efficient**

**Three terms the audit proposed are deliberately NOT scanned**, because
measurement showed they are load-bearing method vocabulary rather than
framing:

| term | where it legitimately appears |
|---|---|
| `flag` | *"the Ledger shows the figures, **flags** these differences, and never ranks districts"* (ccc, uc) · *"basic-aid **flag**"*, a source field (schools) · *"a single **flag** per employer"*, the Controller's own column (compensation) |
| `detect` | *"it cannot **detect** a transfer between two agencies"* — a stated limit of the Ledger's own method (index, M-3) |
| `investigate` | the findings register's core noun |

Every one of those marks a caveat on **the Ledger's own figure** or states a
limit of **the Ledger's own method**. None describes a government. A
substring scan cannot express *"the subject must not be a government"*, so
it enforces the part it can and this section carries the rest.

**It does not cover the findings register.** `findings.html` and the
documents under `docs/` use *investigation* as their core noun — the
project's method is to investigate a source and publish what it found,
including refusals. Banning the word there would require renaming the
thing the site is most known for.

The distinction is real rather than a convenience: *investigate* describing
**the Ledger's own work on a source** is accurate; *investigate* describing
**a government** is the framing §7 refuses. The scan enforces the second by
scoping to the surfaces where a government is the subject.

## 10. Two source exceptions, and no third without a finding

`docs/SCOPE.md` records the manual-cache exceptions (CSU, compensation) and
the one architectural exception (compensation's on-demand load). A third
exception needs its own investigation and its own finding, because two
exceptions are a limit and three are a broken claim.

---

## How to use this document

When a change is proposed that touches one of these, the answer is not
"no" — it is **"this was decided, here is the reasoning, and here is what
would have to change for the decision to change."** Every item above is
reversible by measurement. None is reversible by preference.
