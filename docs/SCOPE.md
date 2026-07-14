# Scope decisions — standing

_This document records scope decisions that are permanent, with their
reasoning, so no future session re-proposes them. It is normative, not
historical; the dated history lives in STATUS.md._

## The architectural rule

**Citizen Ledger has no server, no API keys, no per-use costs, and no
runtime third-party services. Any proposed feature that requires one
is out of scope by default.**

The site is static files: open them and they work, today and in ten
years, at zero runtime cost and zero maintenance. That is not a
technical preference — it is the project's main defense against the
failure mode documented in docs/LANDSCAPE_FINDING.md: every serious
California fiscal-transparency precedent (California Common Sense,
Stanford's Pension Tracker, the State Auditor's own dashboard,
ClearGov's universal profiles) died when its builder's attention,
funding, or staffing moved on. **Survivability is the scarce resource
in this landscape**, and every key, bill, and server is a way to die.

Precision about the two existing runtime enhancements, so the rule is
applied correctly rather than argued around:

- the map view loads vendored MapLibre and keyless OpenFreeMap tiles;
- the address view sends the typed address to the U.S. Census
  Bureau's public geocoder.

Both are **keyless, unmetered, free, and non-load-bearing**: when
they fail, the record still works (test-asserted degradation). That
is the boundary. An enhancement may use a runtime service only if it
requires no key, no account, no billing relationship, and its failure
breaks nothing. Anything requiring an API key, a server, or per-use
cost does not qualify — by default, without a new finding.

## "Ask the Ledger" — permanently out of scope

A natural-language query interface ("ask a question about California
spending, get an answer") is **permanently out of scope**. Decided
2026-07-14 by the project owner.

Reasoning, recorded so it does not get re-litigated:

1. Answering a free-form question requires an LLM API call per
   question. An API call requires an API key. A key cannot live in a
   static page, so it requires a server — and with it billing,
   secrets, rate limits, abuse handling, and a monthly reason to
   exist. That breaks the static, zero-runtime-cost, zero-maintenance
   architecture, which is the survivability defense above.
2. The Ledger is already queryable: search across every layer,
   filters, side-by-side comparison, per-entity records, CSV export,
   and permalinks that reproduce any view exactly. A conversational
   layer would add convenience, not capability.
3. Convenience priced in survivability is a bad trade here. The
   landscape finding's graveyard is full of more convenient tools.

There is also a neutrality cost worth noting: a model paraphrasing
the record would reintroduce exactly the editorial voice the Ledger
bans — adjectives, emphasis, implied comparison — between the reader
and the figures. The record speaks in numbers with stated bases;
that is the product.

No reference to this feature existed in the repository when this
decision was recorded (verified by search of all pages, docs, and
pipeline files). This document exists so none is ever added.
