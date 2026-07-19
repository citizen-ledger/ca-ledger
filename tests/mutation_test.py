#!/usr/bin/env python3
"""
MUTATION TESTING — does the suite verify the DATA, or the pipeline's claims?

    python3 tests/mutation_test.py              # every target
    python3 tests/mutation_test.py ccc school-coord
    python3 tests/mutation_test.py --list

Why this exists
---------------
A test can look rigorous and verify nothing. Before the UC layer shipped, an
adversarial review changed one campus figure by $1,000, re-stamped the
SHA-256 digest so the integrity check still passed, and ran the suite: all
898 assertions passed. The gate assertions were reading `meta.gateHistory` —
values the pipeline itself had written — instead of recomputing the
reconciliation from the shipped rows. The tests were verifying the
pipeline's claims about the data, not the data.

This harness makes that failure mode impossible to reintroduce. For each
target it: creates a throwaway git worktree, changes ONE figure in a shipped
data file, re-stamps the digest to hide the edit, and runs the full suite.
A mutation that the suite does not catch is a hole in the gates.

    EVERY MUTATION MUST FAIL THE SUITE. A surviving mutation is a bug in
    the tests, not in this script.

Two classes of mutation are exercised deliberately:

  single      one figure moved. Caught by a children-sum-to-parent identity.
  coordinated a figure AND every stored parent that would expose it, moved
              together, so every in-file identity still holds. Nothing inside
              the file can catch these; only an anchor held OUTSIDE it can —
              the source's published control where one exists, otherwise a
              pinned snapshot of the statewide totals we currently ship
              (which detects the edit without claiming the source agrees).
              They are the reason the ANCHORS block in run_tests.py exists.

Run sequentially on purpose: concurrent Chromium launches race and hang.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ── mutations ────────────────────────────────────────────────────────
# Each takes the parsed payload and moves exactly one figure (or, for the
# coordinated cases, one figure plus the stored parent that would otherwise
# hide it). Returns a human description of what was changed.

def _bump(container, key, delta):
    v = container[key]
    container[key] = (f"{float(v) + delta:.2f}" if isinstance(v, str)
                      else round(v + delta, 6))


def _last_year(years):
    return years[sorted(years)[-1]]


def m_state(d):
    _bump(d["budgets"]["2025-26"]["agencies"][0], "gf", 0.05)
    return "state enacted: one agency's General Fund +$0.05B"


def m_state_gate(d):
    """Move the gate's recorded residual for the year DOF's own data does not
    reconcile. The shipped agency rows are untouched, so only an assertion
    that pins the residual itself can catch it."""
    d["meta"]["gate"]["years"]["2025-26"]["residualK"] += 100
    return "state gate: the recorded FY2025-26 source residual moved +100k"


def m_state_control(d):
    """Move DOF's published control as recorded in the shipped gate block,
    leaving the agency rows alone — the reconciliation no longer holds."""
    d["meta"]["gate"]["years"]["2024-25"]["publishedControlK"] += 1
    return "state gate: DOF's published control for FY2024-25 moved +1k"


def m_actuals(d):
    ag = next(a for a in d["budgets"]["2022-23"]["agencies"]
              if isinstance(a.get("actual"), dict))
    _bump(ag["actual"], "gf", 0.05)
    return "state actuals: one agency's actual GF +$0.05B"


def m_state_fund(d):
    for a in d["budgets"]["2025-26"]["agencies"]:
        for dep in a["departments"]:
            if dep.get("funds"):
                dep["funds"][0][2] += 1_000_000
                return "state depth: one department fund line +$1B (rows are in thousands)"
    raise SystemExit("no fund rows found")


def m_city(d):
    y = _last_year(d["cities"]["adelanto"]["years"])
    _bump(y["byFunction"], sorted(y["byFunction"])[0], 0.05)
    return "cities: one city-function figure +$0.05M"


def m_city_total(d):
    y = _last_year(d["cities"]["adelanto"]["years"])
    _bump(y, "expenditures", 0.05)
    return "cities: the headline governmental total only +$0.05M"


def m_city_enterprise(d):
    y = _last_year(d["cities"]["los-angeles"]["years"])
    fund = sorted(y["enterprise"]["byFund"])[0]
    _bump(y["enterprise"]["byFund"], fund, 0.05)
    return "cities: one enterprise fund figure +$0.05M"


def m_county(d):
    y = _last_year(d["counties"]["alameda"]["years"])
    _bump(y["byFunction"], sorted(y["byFunction"])[0], 0.05)
    return "counties: one county-function figure +$0.05M"


def m_county_coord(d):
    y = _last_year(d["counties"]["alameda"]["years"])
    _bump(y["byFunction"], sorted(y["byFunction"])[0], 0.05)
    _bump(y, "scoTotal", 0.05)          # move the stored control too
    return "counties COORDINATED: function +$0.05M and its stored control total"


def m_city_deep(d):
    """Fully consistent: line item, its function, and the headline total all
    move together, so EVERY in-file identity still holds. Only the pinned
    statewide aggregate can catch this."""
    y = _last_year(d["cities"]["adelanto"]["years"])
    fn = next(k for k, items in (y.get("lines") or {}).items() if items)
    y["lines"][fn][0][1] += 50_000          # $ (lines are dollars)
    _bump(y["byFunction"], fn, 0.05)        # $M
    _bump(y, "expenditures", 0.05)
    return ("cities FULLY CONSISTENT: line + function + headline total all "
            "+$0.05M — every in-file identity preserved")


def m_county_deep(d):
    """Fully consistent county tamper — see m_city_deep."""
    y = _last_year(d["counties"]["alameda"]["years"])
    fn = next(k for k, items in (y.get("lines") or {}).items() if items)
    y["lines"][fn][0][1] += 50_000
    _bump(y["byFunction"], fn, 0.05)
    _bump(y, "scoTotal", 0.05)
    return ("counties FULLY CONSISTENT: line + function + stored control all "
            "+$0.05M — every in-file identity preserved")


def m_school_deep(d):
    """Fully consistent K-12 tamper: the gate figure, the published figure,
    the function row, the function x object cell, the restricted/unrestricted
    split, the funding-source group and its tail all move together. Every
    identity the suite checks in-file still holds; only the pinned statewide
    Current Expense can catch it."""
    y = _last_year(d["districts"]["abc-unified"]["years"])
    D = 0.10
    _bump(y, "currentExpense", D)
    _bump(y, "cePublished", D)
    _bump(y, "unrestricted", D)
    _bump(y["byFunction"], "instruction", D)
    _bump(y["byFunctionObject"]["instruction"], "certSalaries", D)
    g = y["byResource"]["unrestricted"]
    _bump(g, "v", D)
    if "n" in g:                     # named year: keep named + tail == v
        g["t"] = round(g.get("t", 0) + D, 2)
    return ("K-12 FULLY CONSISTENT: gate figure, published figure, function, "
            "function x object, restricted split and funding source all +$0.10")


def m_district(d):
    slug = next(s for s, r in sorted(d["districts"].items())
                if r["exp"][-1] and any(r["exp"][-1]))
    d["districts"][slug]["exp"][-1][1] += 1000
    return f"special districts: {slug} enterprise expenditure +$1,000"


def m_school_ce(d):
    y = _last_year(d["districts"]["abc-unified"]["years"])
    _bump(y["byFunction"], "instruction", 0.10)
    return "K-12: one district's instruction figure +$0.10"


def m_school_coord(d):
    y = _last_year(d["districts"]["abc-unified"]["years"])
    _bump(y["byFunction"], "instruction", 0.10)
    _bump(y, "currentExpense", 0.10)
    _bump(y, "cePublished", 0.10)       # move the gate figure AND the control
    return ("K-12 COORDINATED: instruction, currentExpense and cePublished "
            "all +$0.10")


def m_school_fnobj(d):
    y = _last_year(d["districts"]["abc-unified"]["years"])
    _bump(y["byFunctionObject"]["instruction"], "certSalaries", 0.10)
    return "K-12 function×object (V8): one cell +$0.10"


def m_school_resource(d):
    y = _last_year(d["districts"]["los-angeles-unified"]["years"])
    _bump(y["byResource"]["federal"], "v", 0.10)
    return "K-12 funding source (V9): one resource group +$0.10"


def m_school_xtab(d):
    y = _last_year(d["districts"]["los-angeles-unified"]["years"])
    y["byResource"]["federal"]["n"][0][2][0] += 1
    return "K-12 resource×object (V10a): one object cell +$1"


def m_school_charter(d):
    for c in d["charters"].values():
        for y in c["years"].values():
            if "byObject" in y and y["byObject"]:
                _bump(y["byObject"], sorted(y["byObject"])[0], 0.10)
                return "K-12 charters: one charter object figure +$0.10"
    raise SystemExit("no charter byObject found")


def m_school_coe(d):
    c = d["countyOffices"]["alameda-county-office-of-education"]
    y = _last_year(c["years"])
    _bump(y["byFunction"], sorted(y["byFunction"])[0], 0.10)
    return "K-12 county offices: one function figure +$0.10"


def m_csu(d):
    _bump(d["campuses"][0], "opexpK", 1)
    return "CSU: one campus operating expense +$1k"


def m_csu_coord(d):
    _bump(d["campuses"][0], "opexpK", 1)
    _bump(d["systemwide"], "universityOpexpK", 1)
    return "CSU COORDINATED: campus +$1k and the University total +$1k"


def m_ccc(d):
    _bump(d["districts"][0], "ce", 1)
    return "CCC: one district's Current Expense of Education +$1"


def m_ccc_coord(d):
    _bump(d["districts"][0], "ce", 1)
    _bump(d["statewide"], "ce", 1)
    return "CCC COORDINATED: district +$1 and the statewide control +$1"


def m_uc(d):
    _bump(d["campuses"][0], "totalK", 1)
    return "UC: one campus total operating expense +$1k"


def m_uc_coord(d):
    _bump(d["campuses"][0], "totalK", 1)
    _bump(d["campuses"][0], "coreK", 1)
    _bump(d["systemwide"], "auditedTotalK", 1)
    d["meta"]["gateHistory"]["2024-25"]["campusSumK"] += 1
    d["meta"]["gateHistory"]["2024-25"]["auditedTotalK"] += 1
    return ("UC COORDINATED: campus row, core, audited total and the whole "
            "gateHistory moved together")


def m_uc_prior_coord(d):
    """Shift value between the two printed FY2023-24 components. Their sum is
    unchanged, so every in-file identity holds; only pinning the components
    themselves catches it."""
    g = d["meta"]["gateHistory"]["2023-24"]
    g["campusSumK"] += 250_000
    g["systemwideColK"] -= 250_000
    return ("UC prior-year COMPENSATING SHIFT: $250M moved between campusSumK "
            "and systemwideColK, their sum unchanged")


TARGETS = {
    "state":           ("data.js", m_state),
    "state-fund":      ("data.js", m_state_fund),
    "state-gate":      ("data.js", m_state_gate),
    "state-control":   ("data.js", m_state_control),
    "actuals":         ("data.js", m_actuals),
    "city":            ("city-data.js", m_city),
    "city-total":      ("city-data.js", m_city_total),
    "city-deep":       ("city-data.js", m_city_deep),
    "city-enterprise": ("city-data.js", m_city_enterprise),
    "county":          ("county-data.js", m_county),
    "county-coord":    ("county-data.js", m_county_coord),
    "county-deep":     ("county-data.js", m_county_deep),
    "district":        ("district-data.js", m_district),
    "school-ce":       ("school-data.js", m_school_ce),
    "school-coord":    ("school-data.js", m_school_coord),
    "school-deep":     ("school-data.js", m_school_deep),
    "school-fnobj":    ("school-data.js", m_school_fnobj),
    "school-resource": ("school-data.js", m_school_resource),
    "school-xtab":     ("school-data.js", m_school_xtab),
    "school-charter":  ("school-data.js", m_school_charter),
    "school-coe":      ("school-data.js", m_school_coe),
    "csu":             ("csu-data.js", m_csu),
    "csu-coord":       ("csu-data.js", m_csu_coord),
    "ccc":             ("ccc-data.js", m_ccc),
    "ccc-coord":       ("ccc-data.js", m_ccc_coord),
    "uc":              ("uc-data.js", m_uc),
    "uc-coord":        ("uc-data.js", m_uc_coord),
    "uc-prior-coord":  ("uc-data.js", m_uc_prior_coord),
}


# ── harness ──────────────────────────────────────────────────────────
def apply_mutation(worktree: Path, target: str) -> str:
    """Mutate one figure and RE-STAMP the digest, so the integrity check
    cannot be the thing that catches it — the gates must."""
    name, fn = TARGETS[target]
    # import the worktree's own integrity helper, evicting any copy cached
    # from a previous target's (now-deleted) worktree
    sys.path.insert(0, str(worktree / "pipeline"))
    import importlib
    sys.modules.pop("integrity", None)
    integrity = importlib.import_module("integrity")

    path = worktree / name
    text = path.read_text(encoding="utf-8")
    head = text[:text.index("=") + 1]
    payload = json.loads(text[text.index("=") + 1:text.rindex(";")])
    what = fn(payload)
    payload["meta"].pop("integrity", None)
    integrity.stamp(payload)
    path.write_text(head + " " + json.dumps(payload, separators=(",", ":"),
                                            ensure_ascii=False) + ";\n",
                    encoding="utf-8")
    sys.path.pop(0)
    return what


def run_target(target: str, ref: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wt = Path(tmp) / "wt"
        add = subprocess.run(["git", "-C", str(ROOT), "worktree", "add",
                              "--detach", str(wt), ref],
                             capture_output=True, text=True)
        if add.returncode != 0:
            return {"error": add.stderr.strip()[-200:]}
        try:
            what = apply_mutation(wt, target)
            t0 = time.time()
            suite = subprocess.run([sys.executable, "tests/run_tests.py"],
                                   cwd=wt, capture_output=True, text=True,
                                   timeout=1800)
            lines = (suite.stdout + suite.stderr).strip().split("\n")
            caught = suite.returncode != 0
            return {
                "what": what,
                "caught": caught,
                "caught_by": next((l for l in lines if l.startswith("FAIL")),
                                  "")[:150],
                "secs": round(time.time() - t0),
            }
        except subprocess.TimeoutExpired:
            return {"error": "suite timeout"}
        except Exception as exc:            # a stale slug/key must not abort
            return {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove",
                            "--force", str(wt)], capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", help="default: all")
    ap.add_argument("--ref", default="HEAD",
                    help="git ref to test (default HEAD; the working tree is "
                         "never touched)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for t, (f, fn) in TARGETS.items():
            print(f"  {t:17} {f:17} {(fn.__doc__ or '').strip()}")
        return

    targets = args.targets or list(TARGETS)
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        raise SystemExit(f"unknown target(s): {unknown}")

    print(f"Mutation testing {len(targets)} target(s) against {args.ref}.\n"
          f"Every mutation MUST fail the suite.\n", flush=True)
    results, survived = {}, []
    for t in targets:
        r = run_target(t, args.ref)
        results[t] = r
        if r.get("error"):
            mark = f"ERROR  {r['error']}"
        elif r["caught"]:
            mark = f"caught ({r['secs']}s)  <- {r['caught_by'][:90]}"
        else:
            mark = f"SURVIVED ({r['secs']}s)  ** the suite did not verify this figure **"
            survived.append(t)
        print(f"  {t:17} {mark}", flush=True)

    print()
    if survived:
        print(f"{len(survived)} mutation(s) SURVIVED: {survived}\n"
              "The gates for these layers are reading the pipeline's claims, "
              "not the shipped data.", file=sys.stderr)
        sys.exit(1)
    errored = [t for t, r in results.items() if r.get("error")]
    if errored:
        print(f"{len(errored)} target(s) errored: {errored}", file=sys.stderr)
        sys.exit(2)
    print(f"All {len(targets)} mutations were caught. The gates verify the "
          "shipped data.")


if __name__ == "__main__":
    main()
