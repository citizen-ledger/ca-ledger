# Security posture

_A factual statement of the threat model, current as of 2026-07-15.
This document names real risks; it does not claim protections the
architecture does not have._

## What the architecture eliminates by construction

Citizen Ledger is static files served as-is. There is, by design:

- **no server we operate** — no remote-execution surface, no patching
  cadence, no runtime to harden;
- **no database** — no injection surface;
- **no authentication** — no accounts, sessions, or credentials to
  steal;
- **no secrets** — no API keys anywhere in the system (a standing
  rule, docs/SCOPE.md), so there is nothing to leak;
- **no collected user data** — the address view sends the typed
  address to the U.S. Census Bureau's geocoder and nowhere else,
  stores nothing, and never puts it in a URL (test-asserted).

These are not mitigations; the surfaces do not exist.

## Residual risks, honestly

The risks that remain are exactly the ones a static architecture
concentrates: the account, the repository, the deploy pipeline, and
what readers trust.

1. **The GitHub account is the crown jewel.** Whoever can push to
   this repository can change the published record. Mitigations:
   two-factor authentication is a **hard requirement** for anyone
   with repository access; collaborators are kept to the minimum.
   (Account-level settings — see "Settings that must be enabled by
   hand" below.)
2. **Push and merge integrity.** Branch protection on `main`, with
   required review before merge and required signed commits, so a
   compromised credential cannot silently rewrite the record and
   authorship is cryptographically attributable. (Repository
   settings; listed below.)
3. **The deploy pipeline.** The Pages workflow runs with minimal
   permissions (`contents: read`, `pages: write`, `id-token: write`)
   and its actions are **pinned to full commit SHAs**, not floating
   tags, so a compromised upstream action tag cannot inject code into
   a deploy. There is no build step: the workflow uploads the
   repository's files as they are.
4. **Third-party runtime services.** Three exist, all keyless and
   none load-bearing: OpenFreeMap map tiles (map view; failure leaves
   boundaries on parchment), the Census Bureau geocoder (address
   view; failure leaves a stated message and the search pickers), and
   Google Fonts (cosmetic; failure falls back to system fonts). All
   degradation paths except fonts are test-asserted. A compromise of
   the tile or font CDN could serve hostile content to those
   features' requests; the record pages themselves work with no
   network at all.
5. **Post-deploy tampering and altered copies.** Every data file
   carries a SHA-256 digest of its canonical payload, recomputable
   with `pipeline/verify_digest.py`. Honest limits of that defense:
   the digests as displayed live on the same site, so an attacker who
   controls the site entirely could alter both together. What the
   digests do provide: (a) any *copy or fork* whose data cannot
   reproduce the published digests is detectably not the authentic
   record; (b) any tampering with data files alone is detectable; and
   (c) full verification is always available by re-running the
   pipelines against the official state sources, which regenerate the
   canonical payloads and their digests from scratch.
6. **Supply chain.** The one runtime library (MapLibre GL JS) is
   vendored into the repository — no CDN fetch, no package manager at
   runtime. Pipeline dependencies (pypdf, openpyxl, mdbtools) run at
   build time on a maintainer machine, not in the serving path; a
   compromise there is equivalent to a maintainer-machine compromise,
   which the reconciliation gates partially bound (figures that stop
   reproducing published totals refuse to publish).
7. **Upstream source integrity — the stated boundary.** The
   reconciliation gates verify fidelity *to* the official sources
   (DOF, SCO, CDE). They cannot verify the sources themselves: if an
   official portal published wrong figures, the Ledger would
   faithfully reproduce them. The Ledger's claim is fidelity to the
   official record, not adjudication of it.

## Reporting a problem

- **A data error** (a figure that looks wrong, a note that misstates
  a fact): open an issue on the repository. Data-error reports are
  treated as potential gate gaps — the fix includes a check that
  would have caught it.
- **A security issue** (anything that could alter what readers see or
  where their queries go): use GitHub's private vulnerability
  reporting on this repository ("Report a vulnerability" under the
  Security tab) rather than a public issue. If that is unavailable,
  open an issue asking for a private channel without including
  details.

## Settings that must be enabled by hand (account level)

These cannot be set from within the repository and are required by
this posture: two-factor authentication on every account with access;
branch protection on `main` (require pull-request review, require
signed commits, no force pushes); and private vulnerability reporting
enabled. Until they are enabled, items 1-2 above are policy, not
enforcement — this document says so rather than pretending otherwise.
