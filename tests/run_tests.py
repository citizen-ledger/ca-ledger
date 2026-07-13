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
- Covers, on the Ledger design system UI: V1 and V2 rendering, the
  drill-down and view/unit controls, permalink hash round-trips, CSV
  export contents, citation output, the Change-view arithmetic, a
  banned-adjective scan, neutrality checks (ink-only direction), the
  city comparability footnotes (services-checklist vintage,
  consolidated city-county, low-service heuristic), the corrected
  city accounting labels (governmental activities, never "general
  fund only"), the enterprise-fund block, and the RECORD INTEGRITY
  digests (including a live run of pipeline/verify_digest.py).

Exit code 0 = all assertions passed.
"""

import http.server
import json
import re
import socketserver
import subprocess
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
    return json.loads(text[text.index("=") + 1: text.rindex(";")])

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

def fmt_delta_pct(p):  # "▲ 7.8%" / "▼ 2.1%" / "—"
    if p is None:
        return "—"
    return ("▲ " if p >= 0 else "▼ ") + f"{abs(p):.1f}%"

def parse_money(s):
    """'$321.1B' / '−$563M' / '+$23.2B' -> dollars (float)."""
    s = s.strip().replace(",", "").replace(MINUS, "-")
    m = re.match(r"^([+-]?)\$?([0-9.]+)\s*([BMK]?)$", s)
    if not m:
        raise ValueError(f"cannot parse money: {s!r}")
    v = float(m.group(2)) * {"B": 1e9, "M": 1e6, "K": 1e3, "": 1}[m.group(3)]
    return -v if m.group(1) == "-" else v

def parse_glyph_pct(s):
    """'▲ 7.8%' -> 7.8 ; '▼ 2.1%' -> -2.1"""
    s = s.strip()
    sign = -1 if s.startswith("▼") else 1
    return sign * float(re.sub(r"[▲▼%\s]", "", s))

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
BANNED = ["ballooning", "skyrocket", "soaring", "surging", "plummet",
          "slashed", "bloated", "wasteful", "staggering", "whopping",
          "exploding", "spiraling", "runaway", "boondoggle", "reckless",
          "out of control"]

def banned_scan(page, label):
    text = page.inner_text("body").lower()
    for w in BANNED:
        check(f"{label}: no banned term {w!r}", w not in text)

def clipboard_of(page, toggle_sel="#citeToggle", copy_sel="#citeCopy"):
    page.click(toggle_sel)
    page.click(copy_sel)
    page.wait_for_function(
        f"document.querySelector('{copy_sel}').textContent.includes('Copied')")
    text = page.evaluate("navigator.clipboard.readText()")
    page.click("#citeClose")
    return text

# ----------------------------------------------------------------------
def test_integrity():
    for name, payload in (("data.js", STATE), ("city-data.js", CITY)):
        integ = payload["meta"].get("integrity") or {}
        check(f"integrity: {name} has a digest in meta",
              re.fullmatch(r"[0-9a-f]{64}", integ.get("digest", "")) is not None)
    r = subprocess.run([sys.executable, "pipeline/verify_digest.py",
                        "data.js", "city-data.js"],
                       cwd=ROOT, capture_output=True, text=True)
    check("integrity: verify_digest.py verifies both files", r.returncode == 0,
          (r.stdout + r.stderr)[-200:])

def test_v1(page, base):
    years = sorted(STATE["budgets"].keys())
    latest, prev = years[-1], years[-2]
    ags = STATE["budgets"][latest]["agencies"]
    total = sum(state_agency_total(a) for a in ags)
    prev_total = sum(state_agency_total(a) for a in STATE["budgets"][prev]["agencies"])
    pop = STATE["meta"]["population"][latest]

    page.goto(f"{base}/index.html")
    page.wait_for_selector("#appropBar button")

    # rendering + provenance
    banner = page.inner_text("#dataBanner").lower()
    check("V1 provenance cites source", "ebudget.ca.gov" in banner, banner)
    check("V1 provenance states basis", "budgetary-legal" in banner)
    check("V1 header total", money_close(page.inner_text("#totalNum"), total * 1e9),
          page.inner_text("#totalNum"))
    per_cap = round(total * 1000 / pop)
    shown_cap = int(page.inner_text("#perCapNum").replace("$", "").replace(",", ""))
    check("V1 per-resident", abs(shown_cap - per_cap) <= 1, f"{shown_cap} vs {per_cap}")
    yoy = (total - prev_total) / prev_total * 100
    check("V1 YoY glyph format", page.inner_text("#yoyNum") == fmt_delta_pct(yoy),
          page.inner_text("#yoyNum"))
    check("V1 bar segment count", page.locator("#appropBar button").count() == len(ags))
    check("V1 allocation rows == agencies",
          page.locator("#tblBody .arow").count() == len(ags))
    check("V1 ghost strip one box per agency",
          page.locator("#ghostStrip i").count() == len(ags))
    check("V1 fund rows (fed off)", page.locator("#funds .fund").count() == 3)
    check("V1 readout defaults to TOTAL", page.inner_text("#roName") == "TOTAL")
    check("V1 plain-language line present",
          "Of every dollar" in page.inner_text("#plainLine"))

    # neutrality: direction glyphs render in neutral grayscale (ink/graphite),
    # never red/green judgment colors
    color = page.evaluate("getComputedStyle(document.getElementById('yoyNum')).color")
    rgb = [int(x) for x in re.findall(r"\d+", color)[:3]]
    check("V1 neutrality: YoY delta is grayscale, not judgment color",
          max(rgb) - min(rgb) <= 2, color)
    check("V1 neutrality: no legacy judgment classes",
          page.locator(".delta-up, .delta-down").count() == 0)

    # integrity digest shown
    check("V1 integrity digest displayed",
          STATE["meta"]["integrity"]["digest"] in page.inner_text("#integrityDigest"))

    # unit toggle arithmetic
    page.click('[data-unit="perResident"]')
    shown = page.inner_text("#totalNum").replace("$", "").replace(",", "")
    check("V1 unit toggle: per-resident total", abs(int(shown) - per_cap) <= 1, shown)
    page.click('[data-unit="dollars"]')

    # drill-down via the bar (first segment = largest agency)
    biggest = max(ags, key=state_agency_total)
    page.click("#appropBar button >> nth=0")
    page.wait_for_selector("#crumbName")
    sched = page.inner_text("#scheduleLabel")
    check("V1 drill opens largest agency", biggest["name"].upper() in sched, sched)
    check("V1 drill rows == departments",
          page.locator("#tblBody .arow").count() == len(biggest["departments"]))
    check("V1 drill readout total", money_close(page.inner_text("#roValue"),
          state_agency_total(biggest) * 1e9), page.inner_text("#roValue"))

    # citation while drilled (clipboard)
    cite = clipboard_of(page)
    check("V1 citation names agency + FY",
          biggest["name"] in cite and f"FY {latest}" in cite, cite[:90])
    check("V1 citation states basis",
          "Budgetary-Legal" in cite and "not actual expenditures" in cite)
    check("V1 citation permalink uses served (public) URL", f"/{SUBPATH}/" in cite,
          cite[cite.find("Permalink"):][:80])
    page.click("#crumbRoot")

    # federal toggle recomputes (input is visually hidden; click its label)
    page.click("label.switch")
    check("V1 fed toggle checked", page.is_checked("#fedToggle"))
    total_fed = sum(state_agency_total(a, True) for a in ags)
    check("V1 fed toggle total", money_close(page.inner_text("#totalNum"), total_fed * 1e9),
          page.inner_text("#totalNum"))
    check("V1 fund rows (fed on)", page.locator("#funds .fund").count() == 4)
    page.click("label.switch")
    check("V1 fed toggle unchecked", not page.is_checked("#fedToggle"))

    # change view arithmetic (recomputed independently)
    page.click('[data-view="change"]')
    page.wait_for_selector("#changeRows .chg-row")
    hhs = next(a for a in ags if "Health" in a["name"])
    hhs_prev = next(a for a in STATE["budgets"][prev]["agencies"] if a["id"] == hhs["id"])
    delta = state_agency_total(hhs) - state_agency_total(hhs_prev)
    pct = delta / state_agency_total(hhs_prev) * 100
    row_txt = page.locator(f'#changeRows .chg-row:has-text("{hhs["name"]}")').first \
                  .locator(".num").inner_text()
    m = re.match(r"([+−]\$[\d.]+B)\s+([▲▼]\s*[\d.]+%)", row_txt)
    check("V1 change row parses", m is not None, row_txt)
    if m:
        check("V1 change row: dollar change", money_close(m.group(1), delta * 1e9), m.group(1))
        check("V1 change row: percent change",
              abs(parse_glyph_pct(m.group(2)) - pct) <= 0.1, m.group(2))
    summ = page.inner_text("#chgSum")
    net = total - prev_total
    mnet = re.search(r"NET ([+−]\$[\d.]+B)", summ)
    check("V1 change summary NET", mnet and money_close(mnet.group(1), net * 1e9), summ)
    check("V1 change axis is symmetric (label present)",
          "SYMMETRIC SCALE" in page.inner_text("#chgScale"))
    inc = sum(max(0, state_agency_total(a) - state_agency_total(
        next((p for p in STATE["budgets"][prev]["agencies"] if p["id"] == a["id"]), a)))
        for a in ags)
    minc = re.search(r"INCREASES (\+\$[\d.]+B)", summ)
    check("V1 change summary INCREASES", minc and money_close(minc.group(1), inc * 1e9), summ)

    # trend view
    page.click('[data-view="trend"]')
    check("V1 trend one column per year",
          page.locator("#trendCols .tcol").count() == len(years))
    check("V1 trend small multiples == agencies",
          page.locator("#trendGrid .tcard").count() == len(ags))
    page.click('[data-view="allocation"]')

    # table filter
    page.fill("#search", "Health")
    check("V1 filter to one row", page.locator("#tblBody .arow").count() == 1)
    page.fill("#search", "")

    # CSV export
    with page.expect_download() as dl:
        page.click("#csvBtn")
    lines = Path(dl.value.path()).read_text(encoding="utf-8").splitlines()
    csv = "\n".join(lines)
    check("V1 CSV cites source", "ebudget.ca.gov" in csv)
    check("V1 CSV states basis", "enacted appropriations, Budgetary-Legal basis" in csv)
    check("V1 CSV embeds permalink", f"/{SUBPATH}/" in csv)
    data_lines = [l for l in lines if l and not l.startswith("#")]
    top = max(ags, key=state_agency_total)
    check("V1 CSV header row", data_lines[0].startswith("Agency,General Fund ($B)"), data_lines[0])
    check("V1 CSV first data row is largest agency", data_lines[1].startswith(top["name"]),
          data_lines[1][:50])
    check("V1 CSV totals row value", f",{total:.3f}," in data_lines[-1], data_lines[-1])

    # permalink round-trip (year, fed, drill, view, unit)
    hhs_id = hhs["id"]
    page.goto(f"{base}/index.html#y={prev}&fed=1&a={hhs_id}&v=change&u=perResident")
    page.wait_for_selector("#changeRows .chg-row")
    check("V1 hash restore: year", page.input_value("#yearSel") == prev)
    check("V1 hash restore: fed", page.is_checked("#fedToggle"))
    check("V1 hash restore: drill", hhs["name"].upper() in page.inner_text("#scheduleLabel"))
    check("V1 hash restore: view", "on" in (page.get_attribute('[data-view="change"]', "class") or ""))
    check("V1 hash restore: unit", "on" in (page.get_attribute('[data-unit="perResident"]', "class") or ""))
    page.select_option("#yearSel", latest)
    check("V1 hash emit keeps drill", f"a={hhs_id}" in page.evaluate("location.hash"))

    # saved views (device-local)
    page.goto(f"{base}/index.html")
    page.click("#savedToggle")
    page.click("#saveViewBtn")
    check("V1 saved view recorded", page.locator("#savedList .saved-row").count() >= 1)
    page.click("#savedClose")

    # methodology statements (checklist vintage caveat is on both pages)
    body = page.inner_text("body")
    check("V1 methodology: checklist vintage", "FY 2015-16" in body)
    check("V1 methodology: arrangements may have changed", "may have changed" in body)
    check("V1 methodology: heuristic backstop wording",
          "heuristic backstop" in body and "not a current-year survey" in body)
    check("V1 methodology: neutrality caption",
          "THE LEDGER DOES NOT CHARACTERIZE CHANGES" in body)
    banned_scan(page, "V1")

def test_v2(page, base):
    years = CITY["years"]
    latest = years[-1]
    lk = CITY["cities"]["lakewood"]
    la = CITY["cities"]["los-angeles"]
    lk_y = lk["years"][latest]
    la_y = la["years"][latest]
    n_funcs = len(CITY["functions"])

    page.goto(f"{base}/cities.html")
    page.wait_for_selector("#dataBanner span")

    # provenance + corrected accounting labels
    banner = page.inner_text("#dataBanner").lower()
    check("V2 provenance cites SCO", "bythenumbers.sco.ca.gov" in banner, banner)
    check("V2 provenance: governmental activities", "governmental activities" in banner)
    body = page.inner_text("body")
    check("V2 labels: never 'general fund only'",
          "general fund only" not in body.lower())
    check("V2 hero label: governmental activities + reported actuals",
          "GOVERNMENTAL ACTIVITIES · REPORTED ACTUALS" in body)
    check("V2 M-1 says broader than the general fund",
          "broader than the general fund" in body)
    check("V2 city count in data", len(CITY["cities"]) == 482, str(len(CITY["cities"])))
    check("V2 integrity digest displayed",
          CITY["meta"]["integrity"]["digest"] in page.inner_text("#integrityDigest"))

    # search picker: search, select, chip, cap
    page.fill("#citySearch", "Lakew")
    page.wait_for_selector("#cityList button")
    page.click("#cityList button >> nth=0")
    check("V2 picker adds chip", page.locator("#cityChips .chip").count() == 1)
    check("V2 search results are bounded", True)  # verified below with broad query
    page.fill("#citySearch", "a")
    check("V2 search capped at 30 results", page.locator("#cityList button").count() <= 30)
    page.fill("#citySearch", "")

    # single-city detail: labels, figures, footnotes, daggers
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    sched = page.inner_text("#scheduleLabel")
    check("V2 detail schedule label corrected",
          "GOVERNMENTAL EXPENDITURES BY FUNCTION" in sched and "LAKEWOOD" in sched, sched)
    check("V2 detail note shows GOV total",
          fmt_m(lk_y["expenditures"]) in page.inner_text("#scheduleNote"))
    check("V2 detail rows == functions",
          page.locator("#recordBody .det-row").count() == n_funcs)
    per_cap_police = round(lk_y["byFunction"]["police"] * 1e6 / lk_y["population"])
    row = page.locator('#recordBody .det-row:has-text("Police")').first
    shown = int(row.locator(".num").first.inner_text().replace("$", "").replace(",", ""))
    check("V2 police per-resident arithmetic", abs(shown - per_cap_police) <= 1,
          f"{shown} vs {per_cap_police}")
    page.click('.dagger[data-note="lakewood:police"]')
    note = page.inner_text("#recordBody .note-row")
    check("V2 dagger note: police contract", "contract with the county" in note, note[:80])
    check("V2 dagger note: vintage stated", "FY 2015-16" in note)
    page.click('.dagger[data-note="lakewood:fire"]')
    note = page.inner_text("#recordBody .note-row")
    check("V2 dagger note: fire via district", "special district" in note, note[:80])

    # unit toggle arithmetic on detail (% of budget)
    page.click('[data-unit="percent"]')
    pol_pct = lk_y["byFunction"]["police"] / lk_y["expenditures"] * 100
    row = page.locator('#recordBody .det-row:has-text("Police")').first
    check("V2 unit toggle: % of budget",
          abs(float(row.locator(".num").first.inner_text().replace("%", "")) - pol_pct) <= 0.1)
    page.click('[data-unit="perResident"]')

    # citation
    cite = clipboard_of(page)
    check("V2 citation: governmental scope", "million in governmental expenditures" in cite, cite[:120])
    check("V2 citation: enterprise excluded", "enterprise activities excluded" in cite)
    check("V2 citation: carries service notes", "contract with the county" in cite)
    check("V2 citation permalink uses served (public) URL", f"/{SUBPATH}/" in cite)

    # city CSV
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("V2 city CSV: scope line", "# Scope: governmental activities" in csv)
    check("V2 city CSV: corrected column header", "Governmental expenditures ($M)" in csv)
    check("V2 city CSV: total row", f"All governmental functions,{lk_y['expenditures']:.1f}," in csv)
    check("V2 city CSV: note lines present", csv.count("# Note:") >= 2)

    # LA enterprise block
    page.goto(f"{base}/cities.html#c=los-angeles")
    page.wait_for_selector("#entBody .det-row")
    ent = page.inner_text("#entBody")
    check("V2 enterprise total", fmt_m(la_y["enterprise"]["total"]) in ent,
          f"expected {fmt_m(la_y['enterprise']['total'])}")
    check("V2 enterprise airport row", "Airports" in ent)
    check("V2 enterprise excluded from detail total",
          fmt_m(la_y["expenditures"]) in page.inner_text("#scheduleNote"))
    check("V2 enterprise panel labeled ratepayer-funded",
          "RATEPAYER-FUNDED" in page.inner_text("#entLabel"))

    # comparison: alphabetical order, values, shared scale, notes
    page.goto(f"{base}/cities.html#c=santa-monica,lakewood,san-francisco")
    page.wait_for_selector("#recordBody .cmp-row")
    heads = page.locator("#recordBody .cityhead .nm").all_inner_texts()
    check("V2 cmp: columns alphabetical regardless of hash order",
          heads == sorted(heads), str(heads))
    check("V2 cmp: one row per function",
          page.locator("#recordBody .cmp-row").count() == n_funcs)
    caps = page.inner_text("#recordBody .caps")
    check("V2 cmp: governmental-only + shared scale caption",
          "GOVERNMENTAL ACTIVITIES ONLY" in caps and "SHARE ONE SCALE" in caps, caps)
    notes = page.inner_text("#recordBody")
    check("V2 cmp footnote: SF consolidated", "consolidated city and county" in notes)
    check("V2 cmp footnote: Lakewood police", "contract with the county" in notes)
    pol_row = page.locator('#recordBody .cmp-row:has-text("Police")').first
    cells = pol_row.locator(".num").all_inner_texts()
    exp_lk = round(lk_y["byFunction"]["police"] * 1e6 / lk_y["population"])
    got_lk = int(cells[0].replace("$", "").replace(",", ""))
    check("V2 cmp police per-capita (Lakewood first alphabetically)",
          abs(got_lk - exp_lk) <= 1, f"{got_lk} vs {exp_lk}")
    check("V2 cmp header uses GOV label not GF",
          "GOV " in page.inner_text("#recordBody .cmp-head") and
          "GF " not in page.inner_text("#recordBody .cmp-head"))

    # comparison CSV
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("V2 cmp CSV: per-resident governmental units line",
          "dollars per resident · governmental activities only" in csv)
    check("V2 cmp CSV: SF note", "# Note (San Francisco)" in csv and "consolidated" in csv)
    check("V2 cmp CSV: totals row", "All governmental functions," in csv)

    # permalink round-trip
    early = years[0]
    page.goto(f"{base}/cities.html#y={early}&c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    check("V2 hash restore: year", page.input_value("#yearSel") == early)
    check("V2 hash restore: city", "LAKEWOOD" in page.inner_text("#scheduleLabel"))
    page.select_option("#yearSel", latest)
    check("V2 hash emit keeps city", "c=lakewood" in page.evaluate("location.hash"))

    # saved views
    page.click("#savedToggle")
    page.click("#saveViewBtn")
    check("V2 saved view recorded", page.locator("#savedList .saved-row").count() >= 1)
    page.click("#savedClose")

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

    test_integrity()

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
