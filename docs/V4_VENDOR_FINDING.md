# V4 finding: can vendor and contract search be published honestly?

_Investigated 2026-07-13. No UI was built; this document is the deliverable._

## Recommendation, up front

**(c) DON'T SHIP.** California does not publish vendor payment data
that can be honestly reconciled to its budget — or even honestly
totaled per vendor. That sentence is itself the finding, and it is
worth publishing as one: no source the state offers can tell a reader
what a company actually received from the state, and the gaps are
largest precisely where scrutiny would go (no stable identifiers,
truncated free-text names, whole departments absent, 6.7% of
vendor-named dollars masked, and award data locked behind a
bot-gated search UI with no bulk access).

The measured centerpiece: in the most recent published month
(FI$Cal FY25 P10, April 2026), payments carrying a vendor name total
**$4.807B against $40.897B of recorded spending in the same month —
11.8%**. And that denominator is itself the FI$Cal subset of the
state (≈85% of statewide actuals; CDCR, Caltrans, DOJ, DWR, UC are
absent entirely). A vendor search built on this would answer "what did
X receive?" with a number that is, structurally, an unlabeled floor —
roughly a tenth of the real universe, with the missing nine-tenths
distributed unknowably per vendor. For the one feature where the
governing rule is that names attract mobs, publishing per-vendor
floors with unknowable gaps is the worst available failure mode:
it would be precise-looking, citable, and wrong.

## 1. Sources evaluated

### A. Open FI$Cal Monthly Vendor Transaction Files — the only payments source

Monthly CSVs on the same Azure blob storage as the spending files
(`MonthlyVendorTransactionPointer.csv`), ~105–130 MB/month, FY 2017 →
present, ~60-day lag. Row = accounting transaction with a
`VENDOR_NAME` column appended; otherwise the same schema as the
spending files (fund, program, account, dollars).

- **Contains:** PAYMENTS (accounts-payable transactions), not awards,
  not contracts. There is no contract or PO number column — payments
  cannot be joined to any award record.
- **Coverage (measured, April 2026):** 315,191 rows, **$4.807B**,
  vs **$40.897B** in the same month's full spending file (3,930,969
  rows) = **11.8% of recorded spending carries a vendor name.** Per
  Open FI$Cal's own FAQ, the excluded balance is bulk beneficiary
  payments, payroll, non-AP-module transactions, and everything from
  departments that do not use FI$Cal (CDCR, Caltrans, DOJ, DWR, UC…).
  Grants/subventions appear only partially (e.g. a $487k
  Home-Delivered Nutrition grant to the City of Los Angeles appears;
  bulk subventions do not).
- **Masking (measured):** `CONFIDENTIAL` on 45,209 rows (14.3%) —
  **$320M, 6.7% of vendor-named dollars in the month** — covering all
  employee-linked payments and department-specific confidential
  categories.
- **Identifiers: none.** `VENDOR_NAME` is the only vendor field —
  free text, upper-cased, and **truncated at ~30 characters** (12,709
  rows sit at exactly 30 chars: "STATE COMPENSATION INSURNCE FD",
  "SONOMA CNTY COMMUNITY DEV COMM", "YOUNG MENS CHRISTIAN ASSN OF" —
  the last cut mid-phrase). FI$Cal's PeopleSoft core has supplier IDs;
  they are not published.
- **Amounts (measured):** clean — 0 unparsable, 0 zero-amount rows;
  7.2% negative (reversals, consistent with the accounting basis).
- **Basis:** modified accrual / cash — the same basis that made
  Open FI$Cal unusable for V1 (see STATUS.md), plus interagency
  double-counting per its own FAQ.

### B. Cal eProcure / SCPRS (DGS) — the only awards source, effectively closed

The State Contract and Procurement Registration System, searchable at
caleprocure.ca.gov.

- **Contains:** contract and purchase-order AWARDS (what was promised,
  incl. maximum values), over $5,000.
- **Machine access: none.** The site returns 403 to any non-browser
  client — including `robots.txt` (a WAF fingerprint gate; a browser
  user-agent gets HTTP 200). No documented API, no bulk export.
  Scraping a bot-gated PeopleSoft UI is not a legitimate or stable
  pipeline for a public record.
- **The public extract is dead:** data.ca.gov's "Purchase Order Data"
  (the official SCPRS extract) covers **FY 2012-13 through 2014-15
  only** and was last modified in **2019**. California has not
  published a bulk procurement extract for over a decade of awards.
- Even with access, awards ≠ payments, and no published key joins the
  two universes.

### C. Everything else — nothing systematic

- **SCO:** publishes no state vendor payments ("By the Numbers" is
  local government only).
- **data.ca.gov:** beyond the dead SCPRS extract, only niche DGS
  datasets (PPE purchases, a non-competitive-bids list, advertising
  purchases) — narrow, irregular, not a payments or awards system.
- **Department-level disclosures:** scattered PDFs (consulting
  contract reports, Caltrans award lists) — not systematic, not
  machine-readable, not consolidated.
- **FI$Cal "Department Vendor Transaction Files":** the same vendor
  data as (A), cut per department — adds nothing.

## 2. Data quality, measured

One full month tested end-to-end (Vendor_FY25P10.csv, 131 MB):

| Measure | Result |
|---|---|
| Rows / distinct names | 315,191 / 14,873 |
| Total dollars | $4.807B |
| Vendor-named share of same-month recorded spending | **11.8%** ($4.807B / $40.897B) |
| CONFIDENTIAL share | 14.3% of rows, **6.7% of dollars** |
| Unparsable / zero amounts | 0 / 0 |
| Negative amounts (reversals) | 7.2% of rows |
| Name truncation | hard cap ≈30 chars (max 40); 12,709 rows at exactly 30 |

Name-variant test on large, obvious vendors (same month):

- **AT&T — 8 distinct strings.** Some are format noise ("AT & T LONG
  DISTANCE"), but most are **different legal entities**: AT&T
  Enterprises LLC ($5.4M), AT&T Global Services Inc ($1.3M), AT&T
  Mobility ($0.3M)…
- **Kaiser — 3 strings**, again mixing legal entities (Foundation
  Hospitals vs Fdn Health Plan) with a brand name ("KAISER
  PERMANENTE") used inconsistently.
- **Deloitte — 2** (Consulting LLP $35.0M; & Touche LLP $0.1M).
- **PG&E, Accenture, Oracle — 1 each** (clean this month).

The variant problem is therefore not primarily misspelling — it is
**legal-entity ambiguity plus truncation**, which no string-similarity
merge can resolve correctly: merging AT&T Mobility into AT&T Global
Services is factually wrong (different subsidiaries, different
contracts); refusing to merge means a search for "AT&T" must present
eight fragments and let the reader decide — while a 30-char truncation
like "YOUNG MENS CHRISTIAN ASSN OF" cannot even display a correct
name, let alone anchor a merge.

## 3. The comparability question

Our published figures are enacted appropriations and Schedule 9
actuals — Budgetary-Legal basis, full statewide universe, $321.1B for
2025-26. A vendor number from source (A) would be:

- a **different basis** (modified accrual/cash AP transactions);
- a **different universe** — ~12% of FI$Cal-recorded spending, which
  is itself ~85% of statewide actuals: call it on the order of a
  tenth of real spending, before masking;
- **not reconcilable in either direction** — no bridge exists from
  vendor payments to any agency, fund, or statewide figure we show,
  and Open FI$Cal's own FAQ says its totals will not match official
  statements;
- and, fatally for a *search* product: **per-vendor completeness is
  unknowable.** A reader searching a construction firm paid mostly by
  Caltrans would see near-zero. A reader searching a consultancy paid
  through FI$Cal AP would see most of it. The Ledger could not tell
  the two cases apart, and neither could the reader. "What does this
  $40M mean?" has a precise answer — "payments recorded in FI$Cal's
  AP module by participating departments, excluding masked rows" —
  but "is that all of it?" does not, per vendor, and that is the
  question every user is actually asking.

V3 shipped because DOF publishes both sides of the comparison on one
basis and the extraction could be gated to the dollar. Nothing here
can be gated to anything: there is no control total for "what vendor X
received from California."

## 4. Entity resolution

There is no stable identifier anywhere in the published data — not in
the FI$Cal vendor files (name only, truncated), not in the dead SCPRS
extract (free-text supplier names), not in anything reachable on
Cal eProcure. The honest options were assessed:

1. **Merge by algorithm** — indefensible. The measured variants are
   substantively different legal entities as often as they are
   spelling noise; a wrong merge misattributes public money to a named
   company, which is the exact harm the SEARCH-not-SPOTLIGHT rule
   exists to prevent.
2. **Show raw, unmerged strings** (group only by exact string, present
   "similar names" side by side unmerged, let the reader judge) — the
   only defensible presentation, and the one we would use if the
   underlying numbers were publishable. But it does not cure the
   truncated names, and it cannot cure the floor-with-unknowable-gaps
   semantics of §3. Honest resolution presentation cannot rescue
   dishonest coverage.

## 5. What would have to change

Any one of these would reopen the question:

- **FI$Cal publishes supplier IDs** (they exist internally) and a
  per-department AP-coverage statement, so per-vendor totals could
  carry an honest completeness label;
- **Full department onboarding** (or inclusion of non-FI$Cal
  departments' vendor payments) so the universe approaches actual
  spending;
- **DGS restores a bulk SCPRS/eProcure extract** with award
  identifiers and current data — awards-only search ("what was
  promised") with an explicit not-payments disclosure could qualify
  for (b) SHIP NARROWED on its own terms, but no such extract has
  existed since the FY 2014-15 file;
- a statutory checkbook-style portal, as several other states operate.

Until then, the transparent statement is the finding itself:
**California cannot currently tell its public, in machine-readable
form, what any given vendor was actually paid.**

## Appendix — reproducibility

- Vendor sample: `Vendor_FY25P10.csv` (131 MB, April 2026 accounting
  period, published 2026-07-04) from
  `adwoutputfilesadlsstore.blob.core.windows.net/transparency/MonthlyVendorTransactionFiles/`;
  coverage denominator: `Spending_FY25P10.csv` (same store), full
  stream-sum of `monetary_amount` (3,930,969 rows).
- SCPRS extract: data.ca.gov package `purchase-order-data`
  (metadata_modified 2019-10-23; resource "Purchase Order Data
  2012-2015").
- Cal eProcure probes: HTTP 403 for non-browser clients on all paths
  including robots.txt; HTTP 200 with a browser user-agent.
- All measurements are single-month; the structural findings (no IDs,
  truncation, masking policy, coverage design) are properties of the
  published format, not of the month chosen.
