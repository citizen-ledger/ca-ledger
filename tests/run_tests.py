#!/usr/bin/env python3
"""
The California Ledger — headless test suite
===========================================

Single command:

    python3 tests/run_tests.py

Requirements: Python 3.9+, playwright (`pip install playwright`), and
either system Google Chrome or `playwright install chromium`.

What it does
------------
- Serves the repository over HTTP under a **/ca-ledger/ subpath** (a
  temp dir with a symlink), mirroring the GitHub Pages layout, so the
  permalink/citation assertions prove URLs are derived from the served
  location — i.e. they will emit the public URL when deployed.
- Loads data.js and city-data.js in Python and recomputes every
  expected number independently; assertions never trust the page's own
  arithmetic.
- Covers: V1 and V2 rendering on the real data, permalink hash
  round-trips, CSV export contents, citation output, the change-view
  arithmetic, a banned-adjective scan, the city comparability
  footnotes (services-checklist vintage, consolidated city-county,
  low-service heuristic), and the enterprise-fund block.

Exit code 0 = all assertions passed.
"""

import http.server
import json
import re
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBPATH = "ca-ledger"

# ----------------------------------------------------------------------
# Load the real data files the same way the pages do
# ----------------------------------------------------------------------
def load_data_js(path):
    text = Path(path).read_text(encoding="utf-8")
    start = text.index("=") + 1
    end = text.rindex(";")
    return json.loads(text[start:end])

STATE = load_data_js(ROOT / "data.js")
CITY = load_data_js(ROOT / "city-data.js")

# ----------------------------------------------------------------------
# Format replicas (only where exact text is asserted)
# ----------------------------------------------------------------------
MINUS = "−"

def fmt_b(v):  # index.html fmtB — v in billions
    sign = MINUS if v < 0 else ""
    a = abs(v)
    if a >= 100:
        return f"{sign}${a:.0f}B"
    if a >= 1:
        return f"{sign}${a:.1f}B"
    return f"{sign}${round(a * 1000)}M"

def fmt_m(v):  # cities.html fmtM — v in millions
    sign = MINUS if v < 0 else ""
    a = abs(v)
    if a >= 1000:
        return f"{sign}${a / 1000:.2f}B"
    if a >= 100:
        return f"{sign}${a:.0f}M"
    return f"{sign}${a:.1f}M"

def parse_money(s):
    """'$321.1B' / '−$563M' / '+$23.2B' -> dollars (float)."""
    s = s.strip().replace(",", "").replace(MINUS, "-")
    m = re.match(r"^([+-]?)\$?([0-9.]+)\s*([BMK]?)$", s)
    if not m:
        raise ValueError(f"cannot parse money: {s!r}")
    v = float(m.group(2)) * {"B": 1e9, "M": 1e6, "K": 1e3, "": 1}[m.group(3)]
    return -v if m.group(1) == "-" else v

def state_agency_total(a, fed=False):
    return a["gf"] + a["sp"] + a["bd"] + (a["fed"] if fed else 0)

# ----------------------------------------------------------------------
# Tiny assertion framework
# ----------------------------------------------------------------------
PASS, FAIL = 0, []

def check(desc, cond, detail=""):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(f"{desc}" + (f" — {detail}" if detail else ""))
        print(f"  FAIL: {desc} {detail}", file=sys.stderr)

def close(a, b, tol):
    return abs(a - b) <= tol

def money_close(shown, expected_dollars):
    """Displayed money matches the expectation within its own display
    precision: >= $100B renders as whole billions, $1-100B to 0.1B,
    below $1B to whole millions."""
    v = parse_money(shown)
    a = abs(expected_dollars)
    tol = 0.51e9 if a >= 100e9 else (0.051e9 if a >= 1e9 else 0.51e6)
    return abs(v - expected_dollars) <= tol

# ----------------------------------------------------------------------
# HTTP server under /ca-ledger/
# ----------------------------------------------------------------------
def start_server(tmp):
    (Path(tmp) / SUBPATH).symlink_to(ROOT, target_is_directory=True)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=tmp, **kw)
        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/{SUBPATH}"

# ----------------------------------------------------------------------
# Test groups
# ----------------------------------------------------------------------
BANNED = ["ballooning", "skyrocket", "soaring", "surging", "plummet",
          "slashed", "bloated", "wasteful", "staggering", "whopping",
          "exploding", "spiraling", "runaway", "boondoggle", "reckless",
          "out of control"]

def banned_scan(page, label):
    text = page.inner_text("body").lower()
    for w in BANNED:
        check(f"{label}: no banned term {w!r}", w not in text)

def test_v1(page, base):
    years = sorted(STATE["budgets"].keys())
    latest, prev = years[-1], years[-2]
    ags = STATE["budgets"][latest]["agencies"]
    total = sum(state_agency_total(a) for a in ags)
    prev_total = sum(state_agency_total(a) for a in STATE["budgets"][prev]["agencies"])
    pop = STATE["meta"]["population"][latest]

    page.goto(f"{base}/index.html")
    page.wait_for_selector("#appropBar .seg")

    # rendering
    banner = page.inner_text("#dataBanner")
    check("V1 banner cites source", "ebudget.ca.gov" in banner, banner)
    check("V1 banner is not sample", "Sample" not in banner)
    check("V1 header total", close(parse_money(page.inner_text("#totalNum")), total * 1e9, 0.05e9),
          page.inner_text("#totalNum"))
    per_cap = round(total * 1000 / pop)
    shown_cap = int(page.inner_text("#perCapNum").replace("$", "").replace(",", ""))
    check("V1 per-resident", abs(shown_cap - per_cap) <= 1, f"{shown_cap} vs {per_cap}")
    yoy = (total - prev_total) / prev_total * 100
    check("V1 YoY", page.inner_text("#yoyNum") == f"+{yoy:.1f}%", page.inner_text("#yoyNum"))
    check("V1 bar segment count", page.locator("#appropBar .seg").count() == len(ags))
    check("V1 legend chip count", page.locator("#legend .chip").count() == len(ags))
    check("V1 trend has one point per year",
          page.locator("#trendSvg circle").count() == len(STATE["years"]))
    check("V1 fund rows (fed off)", page.locator("#funds .fund").count() == 3)

    # drilldown
    biggest = max(ags, key=state_agency_total)
    page.click("#appropBar .seg >> nth=0")
    page.wait_for_selector("#detail.open")
    check("V1 drilldown opens largest agency", page.inner_text("#dName") == biggest["name"],
          page.inner_text("#dName"))
    check("V1 detail total", fmt_b(state_agency_total(biggest)) in page.inner_text("#dTotal"),
          page.inner_text("#dTotal"))

    # citation (clipboard)
    page.click("#dCite")
    page.wait_for_function("document.getElementById('dCite').textContent.includes('Copied')")
    cite = page.evaluate("navigator.clipboard.readText()")
    check("V1 citation names agency + FY", biggest["name"] in cite and f"FY {latest}" in cite, cite[:90])
    check("V1 citation states basis", "Budgetary-Legal" in cite and "not actual expenditures" in cite)
    check("V1 citation permalink uses served (public) URL", f"/{SUBPATH}/" in cite,
          cite[cite.find("Permalink"):][:80])

    # federal toggle recomputes (the input is visually hidden; click its label)
    page.click("label.switch")
    check("V1 fed toggle checked", page.is_checked("#fedToggle"))
    total_fed = sum(state_agency_total(a, True) for a in ags)
    check("V1 fed toggle total", close(parse_money(page.inner_text("#totalNum")), total_fed * 1e9, 0.05e9),
          page.inner_text("#totalNum"))
    check("V1 fund rows (fed on)", page.locator("#funds .fund").count() == 4)
    page.click("label.switch")
    check("V1 fed toggle unchecked", not page.is_checked("#fedToggle"))

    # change view arithmetic (recomputed independently)
    hhs = next(a for a in ags if "Health" in a["name"])
    hhs_prev = next(a for a in STATE["budgets"][prev]["agencies"] if a["id"] == hhs["id"])
    row = page.locator(f'#chgBody tr:has-text("{hhs["name"]}")').first
    cells = row.locator("td").all_inner_texts()
    check("V1 change row: prior year value",
          money_close(cells[1], state_agency_total(hhs_prev) * 1e9), cells[1])
    check("V1 change row: current value",
          money_close(cells[2], state_agency_total(hhs) * 1e9), cells[2])
    delta = state_agency_total(hhs) - state_agency_total(hhs_prev)
    check("V1 change row: dollar change",
          money_close(cells[3], delta * 1e9), cells[3])
    pct = delta / state_agency_total(hhs_prev) * 100
    shown_pct = float(cells[4].replace("%", "").replace("+", "").replace(MINUS, "-"))
    check("V1 change row: percent change", abs(shown_pct - pct) <= 0.1, cells[4])
    tot_cells = page.locator("#chgBody tr.total-row td").all_inner_texts()
    check("V1 change totals row: dollar change",
          money_close(tot_cells[3], (total - prev_total) * 1e9), tot_cells[3])

    # table filter
    page.fill("#search", "Health")
    check("V1 filter to one row", page.locator("#tblBody tr").count() == 1)
    page.fill("#search", "")

    # CSV export
    with page.expect_download() as dl:
        page.click("#csvBtn")
    lines = Path(dl.value.path()).read_text(encoding="utf-8").splitlines()
    csv = "\n".join(lines)
    check("V1 CSV cites source", "ebudget.ca.gov" in csv)
    check("V1 CSV states basis", "enacted appropriations, Budgetary-Legal basis" in csv)
    data_lines = [l for l in lines if l and not l.startswith("#")]
    top = max(ags, key=state_agency_total)
    check("V1 CSV header row", data_lines[0].startswith("Agency,General Fund ($B)"), data_lines[0])
    check("V1 CSV first data row is largest agency", data_lines[1].startswith(top["name"]),
          data_lines[1][:50])
    check("V1 CSV totals row value", f",{total:.3f}," in data_lines[-1], data_lines[-1])

    # permalink round-trip
    hhs_id = hhs["id"]
    page.goto(f"{base}/index.html#y={prev}&fed=1&a={hhs_id}")
    page.wait_for_selector("#detail.open")
    check("V1 hash restore: year", page.input_value("#yearSel") == prev)
    check("V1 hash restore: fed", page.is_checked("#fedToggle"))
    check("V1 hash restore: agency", page.inner_text("#dName") == hhs["name"])
    page.select_option("#yearSel", latest)
    check("V1 hash emit: year param", f"y={latest}" in page.evaluate("location.hash")
          or latest == sorted(STATE['budgets'])[-1] and "y=" not in page.evaluate("location.hash"))

    # methodology statements (checklist vintage caveat is on both pages)
    page.goto(f"{base}/index.html")
    body = page.inner_text("body")
    check("V1 methodology: checklist vintage", "FY 2015-16" in body)
    check("V1 methodology: arrangements may have changed", "may have changed" in body)
    check("V1 methodology: heuristic backstop wording",
          "heuristic backstop" in body and "not a current-year survey" in body)
    banned_scan(page, "V1")

def test_v2(page, base):
    years = CITY["years"]
    latest = years[-1]
    lk = CITY["cities"]["lakewood"]
    la = CITY["cities"]["los-angeles"]
    sf = CITY["cities"]["san-francisco"]
    lk_y = lk["years"][latest]
    la_y = la["years"][latest]

    page.goto(f"{base}/cities.html")
    page.wait_for_selector(".city-btn")

    banner = page.inner_text("#dataBanner")
    check("V2 banner cites SCO", "bythenumbers.sco.ca.gov" in banner, banner)
    check("V2 banner is not sample", "Sample" not in banner)
    check("V2 picker lists every city",
          page.locator("#cityList li").count() == len(CITY["cities"]))

    # Lakewood detail: figures, footnotes, enterprise
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#detail.open")
    check("V2 detail labels governmental", "governmental expenditures" in page.inner_text("#dTotal"),
          page.inner_text("#dTotal"))
    check("V2 detail total", fmt_m(lk_y["expenditures"]) in page.inner_text("#dTotal"))
    foot = page.inner_text("#dFoot")
    check("V2 footnote: police contract (checklist)", "contract with the county" in foot, foot[:120])
    check("V2 footnote: fire via district", "special district" in foot)
    check("V2 footnote: states checklist vintage", "FY 2015-16" in foot)
    per_cap_police = round(lk_y["byFunction"]["police"] * 1e6 / lk_y["population"])
    row = page.locator('#funcBody tr:has-text("Police")').first.locator("td").all_inner_texts()
    shown = int(row[2].replace("$", "").replace(",", ""))
    check("V2 police per-resident arithmetic", abs(shown - per_cap_police) <= 1,
          f"{shown} vs {per_cap_police}")

    # citation
    page.click("#dCite")
    page.wait_for_function("document.getElementById('dCite').textContent.includes('Copied')")
    cite = page.evaluate("navigator.clipboard.readText()")
    check("V2 citation: governmental scope", "million governmental expenditures" in cite, cite[:100])
    check("V2 citation: enterprise excluded", "enterprise activities excluded" in cite)
    check("V2 citation: carries service notes", "contract with the county" in cite)
    check("V2 citation permalink uses served (public) URL", f"/{SUBPATH}/" in cite)

    # city CSV
    with page.expect_download() as dl:
        page.click("#cityCsvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("V2 city CSV: scope line", "# Scope: governmental activities" in csv)
    check("V2 city CSV: total row", f"All governmental functions,{lk_y['expenditures']:.1f}," in csv)
    check("V2 city CSV: note lines present", csv.count("# Note:") >= 2)

    # LA enterprise block
    page.goto(f"{base}/cities.html#c=los-angeles")
    page.wait_for_selector("#detail.open")
    ent = page.inner_text("#dEnterprise")
    check("V2 enterprise block renders", "Enterprise activities (ratepayer-funded)" in ent)
    check("V2 enterprise total", fmt_m(la_y["enterprise"]["total"]) in ent,
          f"expected {fmt_m(la_y['enterprise']['total'])}")
    check("V2 enterprise airport row", "Airports" in ent)
    check("V2 enterprise excluded from function table",
          fmt_m(la_y["expenditures"]) in page.inner_text("#dTotal"))

    # comparison: values, notes, footnotes
    page.goto(f"{base}/cities.html#cmp=lakewood,santa-monica,san-francisco")
    page.wait_for_selector("#cmpBody tr")
    check("V2 cmp: governmental-only note", "governmental activities only" in page.inner_text("#cmpNote"))
    n_funcs = len(CITY["functions"])
    check("V2 cmp: one row per function + total",
          page.locator("#cmpBody tr").count() == n_funcs + 1)
    cmp_foot = page.inner_text("#cmpFoot")
    check("V2 cmp footnote: SF consolidated", "consolidated city and county" in cmp_foot)
    check("V2 cmp footnote: Lakewood police", "Lakewood" in cmp_foot and "contract with the county" in cmp_foot)
    pol_cells = page.locator('#cmpBody tr:has-text("Police")').first.locator("td .num").all_inner_texts()
    exp_lk = round(lk_y["byFunction"]["police"] * 1e6 / lk_y["population"])
    got_lk = int(pol_cells[0].replace("$", "").replace(",", ""))
    check("V2 cmp police per-capita (Lakewood)", abs(got_lk - exp_lk) <= 1, f"{got_lk} vs {exp_lk}")

    # comparison CSV
    with page.expect_download() as dl:
        page.click("#cmpCsvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("V2 cmp CSV: per-resident governmental units line",
          "dollars per resident · governmental activities only" in csv)
    check("V2 cmp CSV: SF note", "# Note (San Francisco)" in csv and "consolidated" in csv)

    # permalink round-trip
    early = years[0]
    page.goto(f"{base}/cities.html#y={early}&c=lakewood&cmp=lakewood,santa-monica")
    page.wait_for_selector("#detail.open")
    check("V2 hash restore: year", page.input_value("#yearSel") == early)
    check("V2 hash restore: city", page.inner_text("#dName") == "Lakewood")
    sels = page.locator("#cmpControls select").all_inner_texts()
    check("V2 hash restore: cmp selects", page.locator("#cmpControls select >> nth=0").input_value() == "lakewood")
    page.select_option("#yearSel", latest)
    check("V2 hash emit keeps city", "c=lakewood" in page.evaluate("location.hash"))

    # methodology statements
    page.goto(f"{base}/cities.html")
    body = page.inner_text("body")
    check("V2 methodology: checklist vintage", "FY 2015-16" in body)
    check("V2 methodology: arrangements may have changed", "may have changed" in body)
    check("V2 methodology: heuristic backstop wording",
          "heuristic backstop" in body and "not a current-year survey" in body)
    check("V2 methodology: reconciliation stated", "reconciled against" in body)
    banned_scan(page, "V2")

# ----------------------------------------------------------------------
def main():
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp:
        httpd, base = start_server(tmp)
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(accept_downloads=True)
            ctx.grant_permissions(["clipboard-read", "clipboard-write"])
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            test_v1(page, base)
            test_v2(page, base)
            check("no uncaught page errors", not errors, "; ".join(errors[:3]))
            browser.close()
        httpd.shutdown()

    total = PASS + len(FAIL)
    if FAIL:
        print(f"\n{len(FAIL)} of {total} assertions FAILED", file=sys.stderr)
        sys.exit(1)
    print(f"All {total} assertions passed (V1 + V2, real data).")

if __name__ == "__main__":
    main()
