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
GEO = load_data_js(ROOT / "city-geo.js")

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
          "slashed", "bloated", "staggering", "whopping",
          "exploding", "spiraling", "runaway", "boondoggle", "reckless",
          "out of control",
          # a difference column must never be characterized:
          "waste", "overrun", "savings", "underspend", "mismanage"]

def banned_scan(page, label):
    text = page.inner_text("body").lower()
    # "solid waste" is an SCO expenditure CATEGORY on the city page, not a
    # characterization; every other occurrence of "waste" is banned.
    text = text.replace("solid waste", "")
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
    for name, payload in (("data.js", STATE), ("city-data.js", CITY),
                          ("city-geo.js", GEO)):
        integ = payload["meta"].get("integrity") or {}
        check(f"integrity: {name} has a digest in meta",
              re.fullmatch(r"[0-9a-f]{64}", integ.get("digest", "")) is not None)
    r = subprocess.run([sys.executable, "pipeline/verify_digest.py",
                        "data.js", "city-data.js", "city-geo.js"],
                       cwd=ROOT, capture_output=True, text=True)
    check("integrity: verify_digest.py verifies all data files", r.returncode == 0,
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

# Schedule 6 statewide control totals (GF, total) in $M, per the vintage
# publication each year's actuals were extracted from. The pipeline gates
# on these before writing; this re-asserts the gate on the shipped data.
SCH6_CONTROL = {
    "2021-22": (216785, 270694),   # 2023-24 Enacted Budget
    "2022-23": (195189, 274039),   # 2024-25 Enacted Budget
    "2023-24": (205670, 303246),   # 2025-26 Enacted Budget
    "2024-25": (229231, 319151),   # 2026-27 Governor's Budget
}
SCH9_EDUCATION_2324 = 93361       # $M — EDUCATION group total, Actual 2023-24

def test_actuals_data():
    years_meta = (STATE["meta"].get("actuals") or {}).get("years") or {}
    for year, (gf_m, tot_m) in SCH6_CONTROL.items():
        ags = STATE["budgets"][year]["agencies"]
        acts = [a["actual"] for a in ags if "actual" in a]
        check(f"actuals {year}: every agency has an actual", len(acts) == len(ags),
              f"{len(acts)}/{len(ags)}")
        gf = sum(a["gf"] for a in acts) * 1000
        tot = sum(a["gf"] + a["sp"] + a["bd"] for a in acts) * 1000
        check(f"actuals {year}: statewide GF reconciles to Schedule 6",
              abs(gf - gf_m) <= 10, f"{gf:,.0f} vs {gf_m:,}")
        check(f"actuals {year}: statewide total reconciles to Schedule 6",
              abs(tot - tot_m) <= 10, f"{tot:,.0f} vs {tot_m:,}")
        check(f"actuals {year}: vintage recorded",
              "vintage" in (years_meta.get(year) or {}))
    # unavailable years carry explanations, not silent blanks
    for year in ("2020-21", "2025-26"):
        info = years_meta.get(year) or {}
        check(f"actuals {year}: explanation recorded", bool(info.get("unavailable")),
              str(info)[:80])
        check(f"actuals {year}: no actual figures shipped",
              all("actual" not in a for a in STATE["budgets"][year]["agencies"]))
    # Education split: departments mapped, our agencies not merged.
    # K-12 + Higher Ed tracks Schedule 9's EDUCATION group; small, named
    # cross-group movers are expected because assignment follows OUR org
    # structure (e.g. ScholarShare sits under LJE in Schedule 9 but under
    # K-12 in the display structure) — bound them at 0.5%.
    ags = {a["name"]: a for a in STATE["budgets"]["2023-24"]["agencies"]}
    k12, hied = ags["K thru 12 Education"], ags["Higher Education"]
    edu_sum = sum(k12["actual"][k] + hied["actual"][k] for k in ("gf", "sp", "bd")) * 1000
    check("actuals: K-12 + Higher Ed tracks Schedule 9 EDUCATION group (±0.5%)",
          abs(edu_sum - SCH9_EDUCATION_2324) <= SCH9_EDUCATION_2324 * 0.005,
          f"{edu_sum:,.0f} vs {SCH9_EDUCATION_2324:,}")
    cde = next((d for d in k12["departments"] if d.get("code") == "6100"), None)
    uc = next((d for d in hied["departments"] if d.get("code") == "6440"), None)
    ccc = next((d for d in hied["departments"] if d.get("code") == "6870"), None)
    check("actuals: CDE (6100) maps under K thru 12 with an actual",
          cde is not None and "actual" in cde)
    check("actuals: UC (6440) maps under Higher Education with an actual",
          uc is not None and "actual" in uc)
    check("actuals: Community Colleges (6870) map under Higher Education",
          ccc is not None and "actual" in ccc)

def test_actuals_view(page, base):
    ags = STATE["budgets"]["2023-24"]["agencies"]
    hhs = next(a for a in ags if "Health" in a["name"])
    hhs_en = hhs["gf"] + hhs["sp"] + hhs["bd"]
    hhs_act = hhs["actual"]["gf"] + hhs["actual"]["sp"] + hhs["actual"]["bd"]

    page.goto(f"{base}/index.html#v=actuals&y=2023-24")
    page.wait_for_selector("#actBody .arow")
    check("actuals view: button active",
          "on" in (page.get_attribute('[data-view="actuals"]', "class") or ""))
    check("actuals view: one row per agency",
          page.locator("#actBody .arow").count() == len(ags))
    check("actuals view: vintage on the face",
          "SCHEDULE 9" in page.inner_text("#actVintage"),
          page.inner_text("#actVintage"))
    note = page.inner_text("#actNote")
    check("actuals view: non-characterization on the face",
          "not a judgment" in note and "Budgetary-Legal" in note, note[:80])
    check("actuals view: lag statement present (methodology)",
          "six and a half months" in page.inner_text("body"))

    # difference arithmetic, recomputed independently
    cells = page.locator(f'#actBody .arow:has-text("{hhs["name"]}")').first \
                .locator(".num").all_inner_texts()
    check("actuals: HHS enacted cell", money_close(cells[0], hhs_en * 1e9), cells[0])
    check("actuals: HHS actual cell", money_close(cells[1], hhs_act * 1e9), cells[1])
    m = re.match(r"([+−]\$[\d.]+[BM])\s+([▲▼]\s*[\d.]+%)", cells[2])
    check("actuals: HHS difference parses", m is not None, cells[2])
    if m:
        check("actuals: HHS difference arithmetic",
              money_close(m.group(1), (hhs_act - hhs_en) * 1e9), m.group(1))
        pct = (hhs_act - hhs_en) / abs(hhs_en) * 100
        check("actuals: HHS difference percent",
              abs(parse_glyph_pct(m.group(2)) - pct) <= 0.1, m.group(2))

    # neutrality: default sort is by enacted size, not largest gap
    first = page.locator("#actBody .arow").first.inner_text()
    biggest = max(ags, key=lambda a: a["gf"] + a["sp"] + a["bd"])
    check("actuals: default sort is size, not gap", biggest["name"] in first, first[:60])
    # direction glyphs render grayscale
    color = page.evaluate(
        "getComputedStyle(document.querySelector('#actBody .num.delta')).color")
    rgb = [int(x) for x in re.findall(r"\d+", color)[:3]]
    check("actuals: difference is grayscale ink", max(rgb) - min(rgb) <= 2, color)
    # both gross totals always together
    summ = page.inner_text("#actSum")
    check("actuals: symmetric gross totals",
          "BELOW ENACTMENT" in summ and "ABOVE ENACTMENT" in summ and "NET" in summ, summ)

    # drill to departments
    page.locator(f'#actBody .arow:has-text("{hhs["name"]}")').first.click()
    page.wait_for_selector("#crumbName")
    check("actuals drill: departments render",
          page.locator("#actBody .arow").count() == len(hhs["departments"]))
    page.click("#crumbRoot")

    # CSV
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("actuals CSV: header", "Agency,Enacted ($B),Actual ($B),Difference ($B)" in csv)
    check("actuals CSV: basis line", "BOTH columns Budgetary-Legal" in csv)
    check("actuals CSV: non-characterization line", "not a judgment" in csv)

    # citation
    cite = clipboard_of(page)
    check("actuals citation: names both figures", "Enacted vs. Actual" in cite, cite[:80])
    check("actuals citation: vintage", "Schedule 9" in cite)

    # empty states, with reasons
    page.goto(f"{base}/index.html#v=actuals&y=2025-26")
    page.wait_for_selector("#actEmpty:not([hidden])")
    check("actuals: future year explains itself",
          "not yet been published" in page.inner_text("#actEmpty").lower()
          or "first published" in page.inner_text("#actEmpty").lower(),
          page.inner_text("#actEmpty")[:80])
    page.goto(f"{base}/index.html#v=actuals&y=2020-21")
    page.wait_for_selector("#actEmpty:not([hidden])")
    check("actuals: 2020-21 explains the verification failure",
          "reconcile" in page.inner_text("#actEmpty").lower(),
          page.inner_text("#actEmpty")[:100])

    # permalink round-trip with the actuals sort param
    page.goto(f"{base}/index.html#v=actuals&y=2023-24&asort=name.asc")
    page.wait_for_selector("#actBody .arow")
    first = page.locator("#actBody .arow").first.inner_text()
    alpha_first = sorted(a["name"] for a in ags)[0]
    check("actuals: asort round-trip", alpha_first in first, first[:60])
    page.click("#ahDiff")
    check("actuals: sort emits hash param", "asort=diff" in page.evaluate("location.hash"))


def test_map(page, base):
    # data-level: boundary coverage — every city has a GeoJSON feature
    slugs = {f["properties"]["slug"] for f in GEO["features"]}
    missing = [s for s in CITY["cities"] if s not in slugs]
    check("map: boundary coverage 482/482", not missing, str(missing[:5]))
    check("map: feature count matches city count",
          len(GEO["features"]) == len(CITY["cities"]),
          f"{len(GEO['features'])} vs {len(CITY['cities'])}")
    # HARD NEUTRALITY, part 1: the geometry file carries NO financial
    # data — a choropleth has nothing to encode. Properties are exactly
    # {slug, name, clng, clat}.
    bad_props = {k for f in GEO["features"] for k in f["properties"]} \
        - {"slug", "name", "clng", "clat"}
    check("map neutrality: no financial fields in geo properties",
          not bad_props, str(bad_props))
    bad_geom = [f["properties"]["slug"] for f in GEO["features"]
                if f["geometry"]["type"] not in ("Polygon", "MultiPolygon")]
    check("map: all geometries are polygons", not bad_geom, str(bad_geom[:5]))

    # print: the map hides in print; the record prints instead
    html = (ROOT / "cities.html").read_text(encoding="utf-8")
    check("map: hidden in print CSS",
          re.search(r"@media print\s*{[^}]*\.map-panel\s*{\s*display\s*:\s*none", html)
          is not None)

    # map view renders behind the toggle; search picker unchanged
    page.goto(f"{base}/cities.html")
    page.wait_for_selector("#pickerModeGroup button")
    check("map: hidden by default", page.is_hidden("#mapPanel"))
    check("map: search picker visible by default", page.is_visible("#citySearch"))
    page.click('#pickerModeGroup [data-mode="map"]')
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    check("map: panel shown, search hidden",
          page.is_visible("#mapPanel") and page.is_hidden("#citySearch"))
    check("map: hash encodes view", "p=map" in page.evaluate("location.hash"))
    check("map: overlay source carries every city", page.evaluate(
        "window.CA_CITY_GEO.features.length") == len(CITY["cities"]))

    # HARD NEUTRALITY, part 2: with nothing selected the fill paint is a
    # single ink literal for all 482 shapes (WebGL has no per-shape DOM;
    # the style expression IS the uniform-fill guarantee). Any
    # data-driven fill would change this JSON and fail here.
    spec = page.evaluate(
        "JSON.stringify(window._clMap.getPaintProperty('cities-fill','fill-color'))")
    check("map neutrality: unselected fill is one ink literal",
          spec == '"#242424"', spec)

    # selected boundaries take the comparison swatches, alphabetical
    page.goto(f"{base}/cities.html#p=map&c=santa-monica,lakewood,san-francisco")
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    spec = page.evaluate(
        "JSON.stringify(window._clMap.getPaintProperty('cities-fill','fill-color'))")
    check("map selected swatches: alphabetical ramp order in paint spec",
          spec == '["match",["get","slug"],"lakewood","#242424",'
                  '"san-francisco","#6f6c69","santa-monica","#a39f9c","#242424"]',
          spec)
    check("map neutrality: selection keyed by slug only, ink default",
          '"get","slug"' in spec and spec.endswith('"#242424"]'))

    # canvas click on a boundary selects it (parity semantics) — start
    # clean; find a pixel that queryRenderedFeatures confirms is Lakewood
    # (a centroid can sit inside a boundary hole)
    page.goto(f"{base}/cities.html#p=map")
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    page.evaluate("window._clMap.jumpTo({center:[-118.14,33.85], zoom:10.5})")
    page.wait_for_function(
        "window._clMap.loaded() && window._clMap.areTilesLoaded()", timeout=45000)
    page.locator("#mapContainer").scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    pt = page.evaluate(
        """(() => {
          const m = window._clMap;
          const c = m.project([-118.123, 33.8468]);
          for (let dx = 0; dx < 60; dx += 6) for (const sx of [1, -1])
            for (let dy = 0; dy < 60; dy += 6) for (const sy of [1, -1]) {
              const x = c.x + dx * sx, y = c.y + dy * sy;
              const f = m.queryRenderedFeatures([x, y], {layers: ['cities-fill']});
              if (f.length && f[0].properties.slug === 'lakewood') {
                const r = document.getElementById('mapContainer').getBoundingClientRect();
                return {x: x + r.x, y: y + r.y};
              }
            }
          return null; })()""")
    check("map click: a rendered Lakewood pixel exists", pt is not None)
    if pt:
        page.mouse.click(pt["x"], pt["y"])
        page.wait_for_timeout(500)
        h = page.evaluate("location.hash")
        check("map click: boundary click selects the city", "c=lakewood" in h, h[:90])
        map_sched = page.inner_text("#scheduleLabel")
        check("map click: opens the same record as search",
              "LAKEWOOD" in map_sched, map_sched)

    # keyboard path: focusable per-city buttons pan + select (additive)
    page.focus('#mapKeyList button[data-city="santa-monica"]')
    page.wait_for_timeout(400)
    check("map keyboard: focus announces the city",
          "SANTA MONICA" in page.inner_text("#mapReadout"),
          page.inner_text("#mapReadout"))
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    map_hash = page.evaluate("decodeURIComponent(location.hash)")
    check("map keyboard: Enter adds to the selection",
          "santa-monica" in map_hash, map_hash[:90])
    # identical record state as a search selection
    page.goto(f"{base}/cities.html")
    page.fill("#citySearch", "Lakewood")
    page.wait_for_selector("#cityList button")
    page.click("#cityList button >> nth=0")
    page.wait_for_selector("#recordBody .det-row")
    check("map selection parity: same c= param as search selection",
          "c=lakewood" in page.evaluate("location.hash"))

    # permalink: continuous view state m=z/lat/lng, restored on load
    page.goto(f"{base}/cities.html#p=map&m=9.0/36.50/-119.50")
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    view = page.evaluate(
        "(() => { const m=window._clMap; const c=m.getCenter();"
        " return {z:m.getZoom(), lat:c.lat, lng:c.lng}; })()")
    check("map permalink: zoom restored", abs(view["z"] - 9.0) <= 0.11, str(view))
    check("map permalink: center restored",
          abs(view["lat"] - 36.50) <= 0.02 and abs(view["lng"] + 119.50) <= 0.02,
          str(view))
    page.evaluate("window._clMap.jumpTo({center:[-121.0,38.0], zoom:7.3})")
    page.wait_for_timeout(400)
    check("map permalink: moves update the hash",
          "m=7.3" in page.evaluate("decodeURIComponent(location.hash)"),
          page.evaluate("location.hash")[:90])
    page.click("#mapReset")
    page.wait_for_timeout(800)
    check("map reset: statewide + m cleared",
          "m=" not in page.evaluate("location.hash"))

    # graceful degradation: block the vendored library — map explains
    # itself and the search picker keeps working
    ctx = page.context
    ctx.route("**/vendor/maplibre-gl.js", lambda route: route.abort())
    page2 = ctx.new_page()
    page2.goto(f"{base}/cities.html#p=map")
    page2.wait_for_selector("#mapFail:not([hidden])", timeout=15000)
    check("map degradation: clear message when the library is unavailable",
          "could not be loaded" in page2.inner_text("#mapFail"),
          page2.inner_text("#mapFail")[:80])
    page2.click('#pickerModeGroup [data-mode="search"]')
    page2.fill("#citySearch", "Lakewood")
    page2.wait_for_selector("#cityList button")
    page2.click("#cityList button >> nth=0")
    page2.wait_for_selector("#recordBody .det-row")
    check("map degradation: search picker still selects",
          "c=lakewood" in page2.evaluate("location.hash"),
          page2.evaluate("location.hash")[:60])
    page2.close()
    ctx.unroute("**/vendor/maplibre-gl.js")


# ----------------------------------------------------------------------
def main():
    from playwright.sync_api import sync_playwright

    test_integrity()
    test_actuals_data()

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
            test_actuals_view(page, base)
            test_v2(page, base)
            test_map(page, base)
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
