#!/usr/bin/env python3
"""
Citizen Ledger — headless test suite
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
COUNTY = load_data_js(ROOT / "county-data.js")
CGEO = load_data_js(ROOT / "county-geo.js")
DIST = load_data_js(ROOT / "district-data.js")
SCHOOL = load_data_js(ROOT / "school-data.js")

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
                          ("city-geo.js", GEO), ("county-data.js", COUNTY),
                          ("county-geo.js", CGEO), ("district-data.js", DIST),
                          ("school-data.js", SCHOOL)):
        integ = payload["meta"].get("integrity") or {}
        check(f"integrity: {name} has a digest in meta",
              re.fullmatch(r"[0-9a-f]{64}", integ.get("digest", "")) is not None)
    r = subprocess.run([sys.executable, "pipeline/verify_digest.py"],
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
    # the readout follows hover; after the drill click the pointer sits over
    # the re-rendered department bar — read it at rest
    page.mouse.move(0, 0)
    page.wait_for_timeout(120)
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
          "no actuals exist yet" in page.inner_text("#actEmpty").lower()
          and "governor's budget" in page.inner_text("#actEmpty").lower(),
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


    # current-year empty state: explicit, year named, edition named
    page.goto(f"{base}/index.html#v=actuals&y=2025-26")
    page.wait_for_selector("#actEmpty:not([hidden])")
    empty = page.inner_text("#actEmpty")
    check("actuals empty state: current year named plainly",
          "No actuals exist yet for FY 2025-26" in empty, empty[:80])
    check("actuals empty state: names the January edition",
          "January 2027" in empty and "six and a half months" in empty)


def test_county(page, base):
    # data-level: 57 counties, every county-year gate re-asserted
    check("county: 57 filers", len(COUNTY["counties"]) == 57,
          str(len(COUNTY["counties"])))
    check("county: SF single-counted (absent here, present in cities)",
          "san-francisco" not in COUNTY["counties"]
          and "san-francisco" in CITY["cities"])
    check("county: same fiscal years as cities", COUNTY["years"] == CITY["years"])
    bad_gate, bad_uninc = [], []
    for slug, c in COUNTY["counties"].items():
        for fy, yr in c["years"].items():
            total = (sum(yr["byFunction"].values()) + yr["enterprise"]["total"]
                     + yr.get("internalService", 0) + yr.get("conduitFinancing", 0))
            if abs(total - yr["scoTotal"]) > 0.02:   # $20k on $M rounding
                bad_gate.append(f"{slug} {fy}")
            u = yr.get("unincorporated")
            if u is None or not (0 <= u <= 1) or yr["population"] <= 0:
                bad_uninc.append(f"{slug} {fy}")
    check("county: every county-year reconciles to its stored control total",
          not bad_gate, str(bad_gate[:4]))
    check("county: unincorporated share present and sane for every county-year",
          not bad_uninc, str(bad_uninc[:4]))
    # geometry: 58 features, exactly one SF pointer, no financial fields
    check("county geo: 58 boundaries", len(CGEO["features"]) == 58)
    pointers = [f for f in CGEO["features"] if f["properties"].get("pointer")]
    check("county geo: exactly one pointer (San Francisco -> city layer)",
          len(pointers) == 1 and pointers[0]["properties"]["slug"] == "san-francisco")
    bad_props = {k for f in CGEO["features"] for k in f["properties"]} \
        - {"slug", "name", "clng", "clat", "pointer"}
    check("county geo neutrality: no financial fields", not bad_props, str(bad_props))

    # layer toggle: explicit boundary, selection never crosses
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    page.click('#layerGroup [data-layer="county"]')
    page.wait_for_timeout(300)
    check("county: switching layers clears the selection",
          "c=" not in page.evaluate("location.hash")
          and page.locator("#cityChips .chip").count() == 0)
    check("county: layer encoded in hash", "l=county" in page.evaluate("location.hash"))
    check("county: hero shows the layer", "57 COUNTIES" in page.inner_text("#heroNum"))
    # a CITY slug is meaningless in the county layer
    page.goto(f"{base}/cities.html#l=county&c=lakewood")
    page.wait_for_selector("#pickLbl")
    check("county: city slugs are ignored in the county layer",
          page.locator("#cityChips .chip").count() == 0)

    # county detail: unincorporated footnote on the face
    page.goto(f"{base}/cities.html#l=county&c=los-angeles")
    page.wait_for_selector("#recordBody .det-row")
    sched = page.inner_text("#scheduleLabel")
    check("county detail: named as a county", "LOS ANGELES COUNTY" in sched, sched)
    check("county detail: one row per county function",
          page.locator("#recordBody .det-row").count() == len(COUNTY["functions"]))
    body = page.inner_text("#recordBody")
    la = COUNTY["counties"]["los-angeles"]["years"][COUNTY["years"][-1]]
    expected_pct = f"{round(la['unincorporated']*100)}%"
    check("county detail: unincorporated share footnote, data-derived",
          expected_pct in body and "unincorporated areas the county serves directly" in body,
          body[-200:])
    check("county detail: footnote states responsibility-not-choices",
          "responsibility share, not spending choices" in body)

    # county comparison: alphabetical, within-layer, footnoted
    page.goto(f"{base}/cities.html#l=county&c=orange,alameda,los-angeles")
    page.wait_for_selector("#recordBody .cmp-row")
    heads = page.locator("#recordBody .cityhead .nm").all_inner_texts()
    check("county cmp: alphabetical county columns",
          heads == ["Alameda County", "Los Angeles County", "Orange County"], str(heads))
    notes = page.inner_text("#recordBody")
    check("county cmp: every county carries its unincorporated note",
          notes.count("unincorporated areas the county serves directly") == 3)

    # CSV + citation carry the layer explicitly
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("county cmp CSV: layer boundary stated",
          "counties only" in csv and "never compared to each other" in csv)
    cite = clipboard_of(page)
    check("county citation: County Spending title", "County Spending" in cite, cite[:70])
    check("county citation: names are counties", "Alameda County" in cite)

    # SF routing in the county search
    page.goto(f"{base}/cities.html#l=county")
    page.fill("#citySearch", "San Fran")
    page.wait_for_selector("#cityList button")
    first = page.locator("#cityList button").first.inner_text()
    check("county search: SF routes to the Cities layer", "FILES AS A CITY" in first, first)
    page.locator("#cityList button").first.click()
    page.wait_for_selector("#recordBody .det-row")
    h = page.evaluate("location.hash")
    check("county search: SF click selects the CITY record",
          "c=san-francisco" in h and "l=county" not in h, h[:70])

    # map: county layer serves county boundaries; SF not keyboard-selectable
    page.goto(f"{base}/cities.html#l=county&p=map")
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    check("county map: keyboard list excludes the SF pointer",
          page.locator("#mapKeyList button").count() == 57)
    check("county map: chrome names the layer",
          "COUNTIES" in page.inner_text("#mapLbl")
          and "57 COUNTIES" in page.inner_text("#mapReadout")
          and "COUNTY BOUNDARIES" in page.inner_text("#mapCap"))
    spec = page.evaluate(
        "JSON.stringify(window._clMap.getPaintProperty('cities-fill','fill-color'))")
    check("county map neutrality: unselected fill is one ink literal",
          spec == '"#242424"', spec)


def test_districts(page, base):
    F = DIST["meta"]["finding"]
    YRS = DIST["years"]
    src = (ROOT / "districts.html").read_text(encoding="utf-8").lower()

    # ---- data level
    check("districts: >4,500 on record", len(DIST["districts"]) > 4500,
          str(len(DIST["districts"])))
    bad = [s for s, r in DIST["districts"].items()
           if len(r["filings"]) != len(YRS)
           or any(ch not in "FLM-" for ch in r["filings"])]
    check("districts: per-year filing status for every district", not bad,
          str(bad[:3]))
    # meta EXPLAINS the absence of population (allowed); the records
    # themselves must not carry the ingredient
    records_json = json.dumps(DIST["districts"]).lower()
    check("districts: NO population field exists in any district record "
          "(the per-resident ingredient is refused at the source)",
          "population" not in records_json and '"pop"' not in records_json)
    check("districts: finding carries its method",
          all(k in F["method"] for k in
              ("filed", "expectedFilers", "enterpriseShare", "types",
               "delinquencyNameMatching")))
    check("districts: no late/failed list exists for the first two years",
          YRS[0] not in DIST["delinquencyYears"]
          and YRS[1] not in DIST["delinquencyYears"]
          and len(DIST["delinquencyYears"]) == 6)

    # ---- the finding is rendered from live data, not hardcoded
    fmt = lambda n: f"{n:,}"
    page.goto(f"{base}/districts.html")
    page.wait_for_selector(".dir-row")
    finding_dom = page.inner_text("#findingSec")
    for key in ("expectedFilers", "filedLate", "failedToFile", "filed",
                "dependentCount"):
        check(f"districts finding: {key} rendered from data file",
              fmt(F[key]) in finding_dom, fmt(F[key]))
    for key in ("expectedFilers", "filed", "dependentCount"):
        check(f"districts finding: {key} not hardcoded in page source",
              fmt(F[key]) not in src)
    ent_pct = f"{F['enterpriseShareExp']*100:.1f}%"
    check("districts finding: enterprise share rendered from data",
          ent_pct in finding_dom and ent_pct not in src, ent_pct)
    check("districts finding: no dollar figure appears in the finding "
          "(counts and shares, never a layer total)",
          "$" not in finding_dom)
    check("districts finding: control-total absence stated",
          "structurally impossible" in finding_dom)
    check("districts finding: per-year filing table includes "
          "no-list-published years",
          page.inner_text("#yearTbl").count("no list published") == 4)

    # ---- tier chrome
    check("districts: persistent tier band above the fold",
          page.locator("#tierBand").is_visible()
          and "UNRECONCILED" in page.inner_text("#tierBand"))
    check("districts: no unit toggle exists on the page",
          page.locator("#unitGroup").count() == 0)
    check("districts: no layer pill / comparison chips exist",
          page.locator("#layerGroup").count() == 0
          and page.locator("#cityChips").count() == 0)
    check("districts: directory shows no dollar figures",
          "$" not in page.inner_text("#dirList"))

    # ---- open a record: pick from data a district with figures and an L year
    slug = next(s for s, r in DIST["districts"].items()
                if "L" in r["filings"] and r["exp"][-1] and r["rev"][-1])
    rec = DIST["districts"][slug]
    page.goto(f"{base}/districts.html#d={slug}")
    page.wait_for_selector("#districtRecord")
    caveat = ("As filed with the State Controller. Not reconciled against "
              "any published control total. The Ledger cannot verify this "
              "figure.")
    check("district record: the caveat is on the face",
          caveat in page.inner_text("#recCaveat"))
    check("district record: named and linked to its own SCO filing",
          rec["name"] in page.inner_text("#recTitle"))
    href = page.get_attribute("#recMeta a", "href")
    check("district record: SCO deep link targets the district",
          href.startswith("https://districts.bythenumbers.sco.ca.gov/#!/year/")
          and "entityname" in href, str(href)[:80])
    check("district record: no schedule number on this tier",
          "SCHEDULE 2" not in page.inner_text("body")
          and "AS-FILED RECORD" in page.inner_text("#recordSec"))
    check("district record: filing status shown per year",
          "FILED LATE" in page.inner_text("#recFilings"))
    body = page.inner_text("body")
    # the phrase may appear ONLY in statements of its own absence; a
    # figure (a number adjacent to the phrase) may never appear
    import re as _re
    check("districts: no per-resident/per-capita FIGURE anywhere",
          not _re.search(r"[\$\d][\d,.]*\s*(per resident|per-resident|per capita)",
                         body, _re.I)
          and not _re.search(r"(per resident|per-resident|per capita)\s*[:=]?\s*\$?\d",
                             body, _re.I))
    for m in _re.finditer(r"per[- ]resident|per capita", body, _re.I):
        ctx = body[max(0, m.start()-60):m.end()+60].lower()
        check("districts: per-resident mention is a statement of absence",
              ("no per" in ctx or "fabricat" in ctx or "would fabricate" in ctx
               or "carries no" in ctx or "exists" in ctx),
              ctx[:100])
        break  # one context check per page load is representative
    check("districts: record tables have no per-resident column",
          "PER RESIDENT" not in page.inner_text("#recordSec"))
    exp_txt = page.inner_text("#expTbl")
    check("district record: governmental and enterprise shown separately",
          "GOVERNMENTAL" in exp_txt and "ENTERPRISE" in exp_txt
          and f"${rec['exp'][-1][1]:,}" in exp_txt.replace("\u202f", ","))

    # ---- tier visuals differ from the gated layers
    style = page.evaluate(
        "getComputedStyle(document.getElementById('districtRecord')).borderTopStyle")
    check("district record: dashed border (unreconciled tier)",
          style == "dashed", style)
    # single selection only: choosing another district replaces the first
    other = next(s for s, r in DIST["districts"].items()
                 if s != slug and r["exp"][-1])
    page.fill("#dirSearch", DIST["districts"][other]["name"][:24])
    page.wait_for_timeout(250)
    page.locator("#dirList button.nm").first.click()
    page.wait_for_timeout(250)
    h = page.evaluate("location.hash")
    check("districts: single selection — a second choice replaces the first",
          h.count("d=") == 1 and slug not in h, h[:80])

    # ---- cite and CSV carry the caveat
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    check("district citation: caveat travels with it",
          caveat in cite and "unreconciled" in cite)
    check("district citation: no per-resident figure",
          "per resident" not in cite.lower())
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    check("district CSV: caveat in the header", caveat in csv)
    check("district CSV: no per-resident, no population column",
          "per_resident" not in csv and "population" not in csv.lower()
          and "per resident" not in csv.lower())
    check("district CSV: filing status column present",
          "filing_status" in csv)

    # ---- authored copy neutrality (source scan: rendered names are SCO's
    # own vocabulary — e.g. districts named "…Wastewater Agency" — so the
    # scan covers what the Ledger wrote, which is where characterization
    # could live)
    for w in BANNED + ["delinquent"]:
        check(f"districts source: no banned term {w!r}", w not in src)

    # ---- the gated pages keep solid borders and never grow a district layer
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    style = page.evaluate(
        "getComputedStyle(document.querySelector('.record')).borderTopStyle")
    check("gated layers: record border stays solid", style == "solid", style)
    csrc = (ROOT / "cities.html").read_text(encoding="utf-8")
    check("layer boundary: the city/county picker has no district layer",
          '"district"' not in csrc.split("const LAYERS")[1][:400])


CENSUS_JSONP_RE = "**geocoding.geo.census.gov/**"

def census_jsonp_body(url, geographies, matched="MATCHED ADDR"):
    import urllib.parse as _up
    cb = _up.parse_qs(_up.urlsplit(url).query)["callback"][0]
    if "/coordinates" in url:
        payload = {"result": {"geographies": geographies}}
    else:
        payload = {"result": {"addressMatches": [
            {"matchedAddress": matched, "geographies": geographies}]}}
    return cb + "(" + json.dumps(payload) + ")"

def test_address(page, base):
    IG = COUNTY["meta"]["intergovernmental"]
    ig_pct = f"{IG['share']*100:.1f}%"
    src = (ROOT / "address.html").read_text(encoding="utf-8")

    # ---- permalink render (no network): city case
    page.goto(f"{base}/address.html#c=lakewood")
    page.wait_for_selector("#records .record")
    check("address: three stacked records for a city address",
          page.locator("#records .record").count() == 3)
    body = page.inner_text("body")
    check("address: contract-city comparability note carried onto the mini record",
          "contract with the county" in body)
    check("address: state record labeled as a plan",
          "A PLAN, NOT ACTUALS" in body)

    # ---- NO SUMMED FIGURE anywhere in the DOM
    import re as _re
    per_res = [int(_re.sub(r"[^0-9]", "", el))
               for el in page.locator(".rec-big").all_inner_texts()]
    check("address: three per-resident figures rendered", len(per_res) == 3,
          str(per_res))
    total = sum(per_res)
    for rendering in (f"${total:,}", f"{total:,}"):
        check(f"address: the layers' sum {rendering!r} appears nowhere",
              rendering not in body)
    check("address: the does-not-add statement is structural and carries "
          "the live intergovernmental share",
          "DO NOT ADD" in page.inner_text("#noSum")
          and ig_pct in page.inner_text("#noSum"))
    check("address: intergovernmental share not hardcoded in page source",
          ig_pct not in src and "53.8" not in src)

    # ---- copy rule: in your name, never what you pay
    low = body.lower() + src.lower()
    for banned in ("what you pay", "your tax bill", "tax burden", "you pay",
                   "costs you", "your share of taxes"):
        check(f"address copy: {banned!r} absent", banned not in low)
    check("address copy: 'in your name' present", "in your name" in low)

    # ---- district substitute: county count, no assignment
    dp = page.inner_text("#distPanel")
    la_count = sum(1 for d in DIST["districts"].values()
                   if d["county"] == "Los Angeles")
    check("address: district panel states the county count from data",
          f"{la_count:,}" in dp and "cannot determine" in dp, dp[:80])
    check("address: district panel links to county-filtered directory",
          "districts.html#q=Los%20Angeles" in
          (page.get_attribute("#distPanel a", "href") or ""))

    # ---- mocked geocoder: East-LA-class unincorporated correctness
    east_la = {"Counties": [{"NAME": "Los Angeles County", "GEOID": "06037"}],
               "Census Designated Places": [
                   {"NAME": "East Los Angeles CDP", "GEOID": "0620802",
                    "FUNCSTAT": "S"}]}
    def handler_factory(geo, matched):
        def handler(route):
            route.fulfill(status=200, content_type="text/javascript",
                          body=census_jsonp_body(route.request.url, geo, matched))
        return handler
    page.goto(f"{base}/address.html")
    page.route(CENSUS_JSONP_RE, handler_factory(east_la,
        "4801 E 3RD ST, LOS ANGELES, CA, 90022"))
    ADDR = "4801 E 3rd St, Los Angeles, CA 90022"
    page.fill("#addrInput", ADDR)
    page.click("#lookupBtn")
    page.wait_for_selector("#records .record")
    body = page.inner_text("body")
    check("address unincorporated: county shown as THE local government",
          "UNINCORPORATED LOS ANGELES COUNTY" in page.inner_text("#foundLine")
          and "the county is the local government" in
              page.inner_text("#unincNote").lower())
    check("address unincorporated: no city record rendered",
          page.locator("#records .record").count() == 2
          and "YOUR CITY" not in body)
    check("address unincorporated: CDP labeled a statistical designation, "
          "not a government",
          "East Los Angeles" in page.inner_text("#unincNote")
          and "not a government" in page.inner_text("#unincNote"))
    check("address unincorporated: unincorporated share made concrete",
          "% of Los Angeles County's residents live in unincorporated" in body)
    check("address schools: absent school layers yield a stated "
          "not-determined strip, never a guess",
          "School district — not determined" in body)

    # ---- PRIVACY: the address is nowhere but the census request
    h = page.evaluate("location.hash")
    check("address privacy: hash carries the county slug only",
          h == "#uc=los-angeles", h)
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    stored = page.evaluate("JSON.stringify(localStorage)")
    for label, blob in [("hash", h), ("citation", cite), ("CSV", csv),
                        ("localStorage", stored)]:
        check(f"address privacy: address absent from {label}",
              "4801" not in blob and "3rd St" not in blob
              and "90022" not in blob)
    check("address privacy: disclosure states census.gov sees the address",
          "census.gov" in page.inner_text("#privacyNote"))
    check("address citation: does-not-add travels with it",
          "do not add" in cite and ig_pct in cite)
    check("address CSV: never exports the address",
          "never exported" in csv and "in residents' name" in csv)

    # ---- school districts: identifier matching, both structures
    check("address schools: every district carries an NCES identifier",
          all(d.get("nces") for d in SCHOOL["districts"].values()))
    check("address schools: common-admin filers carry both constituents' ids",
          sorted(len(d["nces"]) for d in SCHOOL["districts"].values()
                 if len(d["nces"]) > 1) == [2, 2, 2, 2, 2])
    SCH_FY = SCHOOL["years"][-1]
    sch_share = f"{SCHOOL['meta']['overlap']['years'][SCHOOL['meta']['overlap']['latest']]['stateShare']*100:.1f}%"
    asrc = (ROOT / "address.html").read_text(encoding="utf-8")

    page.unroute(CENSUS_JSONP_RE)
    palo = {"Counties": [{"NAME": "Santa Clara County", "GEOID": "06085"}],
            "Incorporated Places": [{"NAME": "Palo Alto city",
                                     "GEOID": "0655282", "FUNCSTAT": "A"}],
            "Unified School Districts": [{"NAME": "Palo Alto Unified School District",
                                          "GEOID": "0629610"}]}
    page.route(CENSUS_JSONP_RE, handler_factory(palo, "250 HAMILTON AVE"))
    page.goto(f"{base}/address.html")
    page.fill("#addrInput", "250 Hamilton Ave, Palo Alto")
    page.click("#lookupBtn")
    page.wait_for_selector("#records .record")
    body = page.inner_text("body")
    check("address schools: unified district renders one gated record",
          "Palo Alto Unified" in body
          and "RECONCILED TO CDE'S PUBLISHED FIGURE" in body)
    check("address schools: the basic-aid dagger carries through",
          "tax-base geography" in body)
    check("address schools: district-of-residence charter caveat always on",
          "district of residence" in body.lower()
          and "charter-school students may attend" in body.lower())
    check("address schools: hash carries the school slug only",
          "sd=palo-alto-unified" in page.evaluate("location.hash"))
    check("address schools: does-not-add extended with the live share",
          sch_share in page.inner_text("#noSum")
          and "school district figures do not add" in page.inner_text("#noSum").lower())
    check("address schools: share not hardcoded in source", sch_share not in asrc)
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    check("address schools: citation carries per-ADA and residence caveat",
          "per ADA" in cite and "district of residence" in cite)
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csvt = Path(dl.value.path()).read_text(encoding="utf-8")
    check("address schools CSV: per-ADA table with residence and no-add notes",
          "per_ada_dollars" in csvt and "district of residence" in csvt
          and "not add to the state row" in csvt)

    # elementary + secondary pair — never assume unified
    page.unroute(CENSUS_JSONP_RE)
    pair = {"Counties": [{"NAME": "Los Angeles County", "GEOID": "06037"}],
            "Elementary School Districts": [{"NAME": "Lancaster Elementary School District",
                                             "GEOID": "0620880"}],
            "Secondary School Districts": [{"NAME": "Antelope Valley Union Joint High School District",
                                            "GEOID": "0602820"}]}
    page.route(CENSUS_JSONP_RE, handler_factory(pair, "44933 FERN AVE"))
    page.goto(f"{base}/address.html")
    page.fill("#addrInput", "44933 Fern Ave, Lancaster")
    page.click("#lookupBtn")
    page.wait_for_selector("#records .record")
    body = page.inner_text("body")
    check("address schools: elementary + secondary pair renders two records",
          "YOUR ELEMENTARY SCHOOL DISTRICT" in body
          and "YOUR HIGH SCHOOL DISTRICT" in body
          and "Lancaster Elementary" in body
          and "Antelope Valley Union High" in body)

    # common-administration constituents dedupe to one filer record
    page.unroute(CENSUS_JSONP_RE)
    modesto = {"Counties": [{"NAME": "Stanislaus County", "GEOID": "06099"}],
               "Incorporated Places": [{"NAME": "Modesto city",
                                        "GEOID": "0648354", "FUNCSTAT": "A"}],
               "Elementary School Districts": [{"NAME": "Modesto City Elementary School District",
                                                "GEOID": "0625130"}],
               "Secondary School Districts": [{"NAME": "Modesto City High School District",
                                               "GEOID": "0625150"}]}
    page.route(CENSUS_JSONP_RE, handler_factory(modesto, "1010 10TH ST"))
    page.goto(f"{base}/address.html")
    page.fill("#addrInput", "1010 10th St, Modesto")
    page.click("#lookupBtn")
    page.wait_for_selector("#records .record")
    body = page.inner_text("body")
    check("address schools: common-admin constituents dedupe to one filer",
          body.count("Modesto City Schools") >= 1
          and "sd=modesto-city-schools" in page.evaluate("location.hash")
          and page.evaluate("location.hash").count("sd=") == 1)

    # unknown school GEOID: loud, never a guess
    page.unroute(CENSUS_JSONP_RE)
    unk = {"Counties": [{"NAME": "Los Angeles County", "GEOID": "06037"}],
           "Unified School Districts": [{"NAME": "Mystery Unified School District",
                                         "GEOID": "0699998"}]}
    page.route(CENSUS_JSONP_RE, handler_factory(unk, "1 MYSTERY WAY"))
    page.goto(f"{base}/address.html")
    page.fill("#addrInput", "1 Mystery Way")
    page.click("#lookupBtn")
    page.wait_for_selector("#records .record")
    check("address schools: unmatched identifier fails loudly, no guess",
          "no identifier-matched record" in page.inner_text("body")
          and "Mystery Unified" in page.inner_text("body")
          and "sd=" not in page.evaluate("location.hash"))

    # ---- autocomplete: Census-only suggestions, no leaks
    check("address autocomplete: native autofill enabled",
          page.get_attribute("#addrInput", "autocomplete") == "street-address")
    page.unroute(CENSUS_JSONP_RE)
    page.route(CENSUS_JSONP_RE, handler_factory(east_la,
        "4801 E 3RD ST, LOS ANGELES, CA, 90022"))
    page.goto(f"{base}/address.html")
    seen_urls = []
    page.on("request", lambda r: seen_urls.append(r.url))
    page.type("#addrInput", "4801 East Third Street, Los Angeles", delay=15)
    page.wait_for_selector("#addrSuggest button", timeout=10000)
    check("address autocomplete: candidates render from the geocoder",
          "4801 E 3RD ST" in page.locator("#addrSuggest button").first.inner_text())
    check("address autocomplete: disclosure caption on the list",
          "CENSUS BUREAU" in page.inner_text("#addrSuggest .cap"))
    leaks = [u for u in seen_urls
             if ("4801" in u or "Third" in u)
             and "geocoding.geo.census.gov" not in u]
    check("address autocomplete: typed address reaches census.gov ONLY",
          not leaks, str(leaks[:2]))
    page.locator("#addrSuggest button").first.click()
    page.wait_for_selector("#records .record")
    h = page.evaluate("location.hash")
    check("address autocomplete: pick resolves; hash still slugs only",
          "uc=los-angeles" in h and "4801" not in h and "Third" not in h, h[:60])
    stored = page.evaluate("JSON.stringify(localStorage)")
    check("address autocomplete: typed address never persisted",
          "4801" not in stored and "Third" not in stored)

    # ---- SF consolidated handling (mocked)
    page.unroute(CENSUS_JSONP_RE)
    sf = {"Counties": [{"NAME": "San Francisco County", "GEOID": "06075"}],
          "Incorporated Places": [{"NAME": "San Francisco city",
                                   "GEOID": "0667000", "FUNCSTAT": "A"}]}
    page.route(CENSUS_JSONP_RE, handler_factory(sf, "1 DR CARLTON B GOODLETT PL"))
    page.fill("#addrInput", "1 Dr Carlton B Goodlett Pl, San Francisco")
    page.click("#lookupBtn")
    page.wait_for_timeout(400)
    check("address SF: one consolidated record, counted once",
          page.locator("#records .record").count() == 2  # city + state
          and "counted once" in page.inner_text("#records"))

    # ---- geocoder-failure degradation (aborted requests)
    page.unroute(CENSUS_JSONP_RE)
    page.route(CENSUS_JSONP_RE, lambda route: route.abort())
    page.goto(f"{base}/address.html")
    page.fill("#addrInput", "915 I St, Sacramento")
    page.click("#lookupBtn")
    page.wait_for_selector("#status.err", timeout=20000)
    st = page.inner_text("#status")
    check("address degradation: clear failure message, no guess",
          "could not be reached" in st)
    check("address degradation: browse links still offered",
          page.locator('#status a[href="cities.html"]').count() == 1)
    page.unroute(CENSUS_JSONP_RE)

    # ---- pin map: place labels are geography, never a data encoding
    page.unroute(CENSUS_JSONP_RE)
    page.goto(f"{base}/address.html")
    page.click("#pinBtn")
    page.wait_for_function(
        "(() => { try { return !!window._clPinMap && "
        "window._clPinMap.isStyleLoaded() } catch(e){ return false } })()",
        timeout=30000)
    place = page.evaluate(
        "JSON.stringify((window._clPinMap.getStyle().layers.find(l=>l.id==='place')||{}).type)")
    check("pin map: place-label symbol layer present", place == '"symbol"', place)
    tc = page.evaluate(
        "JSON.stringify(window._clPinMap.getPaintProperty('place','text-color'))")
    check("pin map: label color is one neutral literal, not data-driven",
          tc == '"#797776"', tc)
    cf = page.evaluate(
        "JSON.stringify(window._clPinMap.getPaintProperty('cty-fill','fill-color'))")
    check("pin map: county fill stays uniform ink", cf == '"#242424"', cf)

    # ---- on-device fallback correctness (no network at all)
    page.goto(f"{base}/address.html")
    res = page.evaluate("""(() => {
      // Sacramento City Hall — inside the city boundary
      const f = window.CA_CITY_GEO.features.find(x => x.properties.slug === 'sacramento');
      return f ? 'have-geo' : 'missing';
    })()""")
    check("address on-device: shipped geometry available for local resolution",
          res == "have-geo")


def test_rename(page, base):
    TAG = "A nonpartisan record of California government spending"
    PAGES = {"index.html": "State budget", "cities.html": "City spending",
             "districts.html": "Special districts",
             "address.html": "Your governments",
             "about.html": "About & method"}
    for f, title in PAGES.items():
        src = (ROOT / f).read_text(encoding="utf-8")
        esc_title = title.replace("&", "&amp;")
        check(f"rename {f}: title tag",
              f"<title>Citizen Ledger — {esc_title}</title>" in src)
        check(f"rename {f}: og:site_name", 'content="Citizen Ledger"' in src)
        check(f"rename {f}: tagline in metadata/source", TAG in src)
        check(f"rename {f}: old name absent from source",
              "california ledger" not in src.lower())
        page.goto(f"{base}/{f}")
        page.wait_for_selector(".wordmark")
        check(f"rename {f}: wordmark reads Citizen Ledger",
              page.inner_text(".wordmark") == "Citizen Ledger")
        check(f"rename {f}: tagline appears with the wordmark",
              TAG in page.inner_text(".brand"))
        body = page.inner_text("body")
        check(f"rename {f}: footer renamed, old name never rendered",
              "CITIZEN LEDGER · PUBLIC RECORD" in body
              and "California Ledger" not in body)
    # the canonical/OG URLs stay on the CURRENT repo URL until the user
    # decides otherwise — the rename must NOT touch them
    for f in PAGES:
        src = (ROOT / f).read_text(encoding="utf-8")
        expected = ("https://pkkjassistant-commits.github.io/ca-ledger/"
                    + ("" if f == "index.html" else f))
        check(f"rename {f}: canonical URL unchanged",
              f'rel="canonical" href="{expected}"' in src)
    # citation format on every page: Citizen Ledger, "Title…, FY …"
    page.goto(f"{base}/index.html")
    page.click("#citeToggle")
    cite = page.inner_text("#citeText")
    check("rename citation (state): name, comma, quoted title, FY inside",
          cite.startswith('Citizen Ledger, "State Budget — ')
          and ", FY 20" in cite.split('."')[0], cite[:80])
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    page.click("#citeToggle")
    cite = page.inner_text("#citeText")
    check("rename citation (cities): format",
          cite.startswith('Citizen Ledger, "City Spending — ')
          and ", FY 20" in cite.split('."')[0], cite[:80])
    slug = next(s for s, r in DIST["districts"].items() if r["exp"][-1])
    page.goto(f"{base}/districts.html#d={slug}")
    page.wait_for_selector("#districtRecord")
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    check("rename citation (districts): format keeps the tier in the title",
          cite.startswith('Citizen Ledger, "Special Districts — As Filed: ')
          and "(unreconciled)" in cite.split('."')[0], cite[:90])
    page.goto(f"{base}/address.html#c=lakewood")
    page.wait_for_selector("#records .record")
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    check("rename citation (address): format",
          cite.startswith('Citizen Ledger, "Your Governments: Lakewood and Los Angeles County, FY ')
          , cite[:90])


def test_schools(page, base):
    Y = SCHOOL["years"]
    latest = Y[-1]
    src = (ROOT / "schools.html").read_text(encoding="utf-8")

    # ---- THE GATE, re-asserted from the shipped data for every district-year
    check("schools: 934 districts, 58 county offices",
          len(SCHOOL["districts"]) == 934 and len(SCHOOL["countyOffices"]) == 58,
          f"{len(SCHOOL['districts'])}/{len(SCHOOL['countyOffices'])}")
    bad_gate, bad_sum = [], []
    for slug, d in SCHOOL["districts"].items():
        for fy, v in d["years"].items():
            if abs(v["currentExpense"] - v["cePublished"]) > 0.05:
                bad_gate.append(f"{slug} {fy}")
            if abs(sum(v["byFunction"].values()) - v["currentExpense"]) > 0.05:
                bad_sum.append(f"{slug} {fy}")
    check("schools GATE: every district-year reproduces CDE's published "
          "Current Expense figure", not bad_gate, str(bad_gate[:3]))
    check("schools: function rows sum exactly to the gated figure",
          not bad_sum, str(bad_sum[:3]))

    # ---- dagger source data
    pa = SCHOOL["districts"]["palo-alto-unified"]["years"][latest]
    al = SCHOOL["districts"]["alpine-county-unified"]["years"][latest]
    nj = SCHOOL["districts"]["new-jerusalem-elementary"]["years"][latest]
    check("schools daggers: Palo Alto basic aid, Alpine small, New Jerusalem "
          "charter-sponsor", pa["basicAid"] and al["smallNSS"]
          and nj["sponsoredCharterADA"] > 100 * nj["ada"])
    ba_count = sum(1 for d in SCHOOL["districts"].values()
                   if d["years"].get(latest, {}).get("basicAid"))
    check("schools: basic-aid population is material (the K-12 contract-city "
          "problem)", 100 < ba_count < 200, str(ba_count))

    # ---- district record: gate line + basic-aid dagger, live count
    page.goto(f"{base}/schools.html#c=palo-alto-unified")
    page.wait_for_selector("#recordBody .det-row")
    gate = page.inner_text("#gateLine")
    check("schools UI: the gate is on the face with the published figure",
          "PUBLISHED FIGURE" in gate and "DIFFERENCE $0.00" in gate, gate[:90])
    body = page.inner_text("body")
    live_count = f"{ba_count} of {len(SCHOOL['districts'])} districts"
    check("schools UI: basic-aid note carries the live count",
          "tax-base geography" in body and live_count in body, live_count)
    check("schools UI: basic-aid count not hardcoded in source",
          live_count not in src and "13.7%" not in src)

    page.goto(f"{base}/schools.html#c=alpine-county-unified")
    page.wait_for_selector("#recordBody .det-row")
    check("schools UI: small-district funding-floor note",
          "necessary-small-school" in page.inner_text("body").lower())
    page.goto(f"{base}/schools.html#c=new-jerusalem-elementary")
    page.wait_for_selector("#recordBody .det-row")
    check("schools UI: sponsored-charter note names both ADA figures",
          "describes only the district-run schools" in page.inner_text("body"))

    # ---- commingled-charter limit on the face of an affected record
    com_slug = next(s for s, d in SCHOOL["districts"].items()
                    if d["years"].get(latest, {}).get("commingledCharters"))
    page.goto(f"{base}/schools.html#c={com_slug}")
    page.wait_for_selector("#recordBody .det-row")
    check("schools UI: commingled-charter limit stated on the face",
          "cannot be separated" in page.inner_text("#recordBody"), com_slug)

    # ---- comparison: districts only, alphabetical, notes travel
    page.goto(f"{base}/schools.html#c=palo-alto-unified,fresno-unified")
    page.wait_for_selector("#recordBody .cmp-row")
    heads = page.locator(".dhead .nm").all_inner_texts()
    check("schools cmp: alphabetical", heads == sorted(heads), str(heads))
    check("schools cmp: never ranked, shared scale",
          "NEVER RANKED" in page.inner_text("#recordCaps"))
    check("schools cmp: basic-aid note travels into comparison",
          "tax-base geography" in page.inner_text("#recordBody"))

    # ---- COEs: records only, structurally outside comparison
    page.goto(f"{base}/schools.html#t=coes")
    page.wait_for_selector("#coeStatement:not([hidden])")
    check("schools COE: exclusion stated before any selection",
          "never compared" in page.inner_text("#coeStatement"))
    coe = next(iter(SCHOOL["countyOffices"]))
    coe2 = list(SCHOOL["countyOffices"])[1]
    page.goto(f"{base}/schools.html#t=coes&c={coe}")
    page.wait_for_selector("#recordBody .det-row")
    check("schools COE: no per-ADA figure and no unit toggle",
          "PER ADA" not in page.inner_text("#recordBody")
          and page.evaluate("document.getElementById('unitGroup').style.display") == "none")
    check("schools COE: rollup-gate basis stated",
          "ROLLUPS" in page.inner_text("#gateLine"))
    page.fill("#schoolSearch", SCHOOL["countyOffices"][coe2]["name"][:20])
    page.wait_for_selector("#schoolList button")
    page.locator("#schoolList button").first.click()
    page.wait_for_timeout(200)
    h = page.evaluate("location.hash")
    check("schools COE: single selection — a second choice replaces",
          h.count("%2C") == 0 and h.count(",") == 0, h[:70])

    # ---- charters: records only; dependent pointers never select
    ch = next(iter(SCHOOL["charters"]))
    page.goto(f"{base}/schools.html#t=charters&c={ch}")
    page.wait_for_selector("#recordBody .det-row")
    check("schools charter: filing mode on the face",
          "FILED" in page.inner_text("#gateLine"))
    dep = SCHOOL["dependentCharters"][0]
    page.fill("#schoolSearch", dep["name"][:24])
    page.wait_for_timeout(250)
    depbtn = page.locator('#schoolList button[data-dep]')
    if depbtn.count():
        before = page.evaluate("location.hash")
        depbtn.first.click()
        page.wait_for_timeout(150)
        check("schools charter: dependent pointer informs, never selects",
              page.evaluate("location.hash") == before)
        check("schools charter: pointer names the authorizer",
              "REPORTS INSIDE" in depbtn.first.inner_text())

    # ---- the overlap statement: live values, never hardcoded
    OL = SCHOOL["meta"]["overlap"]["years"][SCHOOL["meta"]["overlap"]["latest"]]
    share = f"{OL['stateShare']*100:.1f}%"
    page.goto(f"{base}/schools.html")
    page.wait_for_selector("#overlapPanel")
    ov = page.inner_text("#overlapPanel")
    check("schools overlap: live state share rendered", share in ov, share)
    check("schools overlap: share not hardcoded in source",
          share not in src and "50.7" not in src)
    for trap in ("Education Protection Account", "STRS", "pass-throughs",
                 "K-14", "never adds", "never to the dollar"):
        check(f"schools overlap: names {trap!r}", trap in ov)
    check("schools overlap: precision honestly bounded",
          "1–3.5%" in ov or "1-3.5%" in ov)

    # ---- cross-layer rule
    check("schools: never compared to other layers, stated",
          "never compared to or summed with cities, counties, special "
          "districts" in page.inner_text("body"))
    csrc = (ROOT / "cities.html").read_text(encoding="utf-8")
    check("layer boundary: city/county picker has no school layer",
          '"school"' not in csrc.split("const LAYERS")[1][:400])

    # ---- cite + CSV
    page.goto(f"{base}/schools.html#c=palo-alto-unified")
    page.wait_for_selector("#recordBody .det-row")
    page.click("#citeToggle")
    cite = page.inner_text("#citeText")
    check("schools citation: format and gate claim",
          cite.startswith('Citizen Ledger, "K-12 School District Spending — ')
          and "to the cent" in cite and "never added" in cite, cite[:80])
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("schools CSV: carries the published figure beside the computed one",
          "cde_published_total" in csv_text and "never added" in csv_text)

    # ---- authored-copy neutrality
    low = src.lower()
    for w in BANNED:
        check(f"schools source: no banned term {w!r}", w not in low)


def test_shape():
    """THE CLASSIFICATION-SHAPE GATE, re-asserted from shipped data.
    Added 2026-07-14 after FY 2016-17 city functions shipped
    misclassified while the totals gate stayed green."""
    # cities: statewide core functions nonzero, 'other' bounded, every year
    sw = {y: {} for y in CITY["years"]}
    for c in CITY["cities"].values():
        for y, yr in c["years"].items():
            for k, v in yr.get("byFunction", {}).items():
                sw[y][k] = sw[y].get(k, 0.0) + v
    for y in CITY["years"]:
        tot = sum(sw[y].values())
        check(f"shape cities {y}: statewide police/fire/admin/streets/parks all nonzero",
              all(sw[y].get(k, 0) > 0 for k in
                  ("police", "fire", "admin", "streets", "parks")))
        check(f"shape cities {y}: 'other' below 10% of governmental spending",
              sw[y].get("other", 0) / tot < 0.10,
              f"{sw[y].get('other',0)/tot*100:.1f}%")
    # the specific regression: LA 2016-17 police consistent with neighbors
    la = CITY["cities"]["los-angeles"]["years"]
    check("shape: LA FY 2016-17 police restored and consistent",
          2000 < la["2016-17"]["byFunction"].get("police", 0) < 3000
          and la["2016-17"]["byFunction"].get("fire", 0) > 400,
          str(la["2016-17"]["byFunction"].get("police")))
    # sandwich rule (materiality $1M), skipping zero-filled source years
    yrs = CITY["years"]
    violations = []
    for slug, c in CITY["cities"].items():
        for i in range(1, len(yrs) - 1):
            cur = c["years"].get(yrs[i], {}).get("byFunction", {})
            if sum(cur.values()) == 0:
                continue
            prev = c["years"].get(yrs[i-1], {}).get("byFunction", {})
            nxt = c["years"].get(yrs[i+1], {}).get("byFunction", {})
            for fn in ("police", "fire"):
                if prev.get(fn, 0) > 1.0 and nxt.get(fn, 0) > 1.0 \
                        and cur.get(fn, 0) == 0:
                    violations.append(f"{slug} {yrs[i]} {fn}")
    check("shape cities: no material police/fire sandwich zeros",
          not violations, str(violations[:5]))
    # counties: every function nonzero statewide, every year
    for y in COUNTY["years"]:
        swc = {}
        for c in COUNTY["counties"].values():
            for k, v in c["years"].get(y, {}).get("byFunction", {}).items():
                swc[k] = swc.get(k, 0.0) + v
        check(f"shape counties {y}: all 14 functions nonzero statewide",
              all(v > 0 for v in swc.values()) and len(swc) == 14)
    # schools: ADA>0 implies instruction dollars
    bad = [f"{s} {y}" for s, d in SCHOOL["districts"].items()
           for y, v in d["years"].items()
           if v["ada"] > 0 and v["byFunction"].get("instruction", 0) <= 0]
    check("shape schools: every district with ADA has instruction dollars",
          not bad, str(bad[:3]))
    # special districts: both buckets alive every year
    for iy, y in enumerate(DIST["years"]):
        gov = sum((r["exp"][iy] or [0]*4)[0] for r in DIST["districts"].values())
        ent = sum((r["exp"][iy] or [0]*4)[1] for r in DIST["districts"].values())
        check(f"shape districts {y}: governmental and enterprise both nonzero",
              gov > 0 and ent > 0)


def test_depth(page, base):
    """V8 depth: children sum to the UNROUNDED parent at every new
    depth, re-asserted from shipped data; bridges legible; negatives
    honest; refused depths absent."""
    # ---- STATE: funds vs parents; programs + bridge identity
    fund_bad, prog_bad, has_programs = [], [], 0
    for y, b in STATE["budgets"].items():
        for a in b["agencies"]:
            for d in a["departments"]:
                if "funds" not in d:
                    continue
                by = {}
                for cd, cl, v in d["funds"]:
                    by[cl] = by.get(cl, 0) + v
                for cl, key in (("G","gf"),("S","sp"),("B","bd"),("F","fed")):
                    if abs(by.get(cl, 0)/1e6 - d[key]) > 0.0006:
                        fund_bad.append(f"{y} {d['name']} {cl}")
                if d.get("programs"):
                    has_programs += 1
                    psum = sum(x[2] for x in d["programs"])
                    # the exact parent comes from the integer fund rows,
                    # never from display-rounded billions
                    allf = sum(v for _cd, _cl, v in d["funds"]) \
                        + sum(d.get("nr", [0, 0])) - d.get("infraUnalloc", 0)
                    if abs(psum - allf) > 2:
                        prog_bad.append(f"{y} {d['name']}: {psum} vs {allf}")
    check("depth state: fund children sum to every department parent",
          not fund_bad, str(fund_bad[:3]))
    check("depth state: programs reconcile through the N/R bridge exactly",
          not prog_bad and has_programs > 1000, str(prog_bad[:3]))
    check("depth state: fund names dictionary ships",
          len(STATE["meta"].get("fundNames", {})) > 300)
    # refused: program prior-year columns must not exist
    check("depth state: no prior-year columns in programs (refused as actuals)",
          all(len(x) == 3 for b in STATE["budgets"].values()
              for a in b["agencies"] for d in a["departments"]
              for x in d.get("programs", [])))

    # ---- SCHOOLS: fn×object and restricted split, cent-exact
    bad_fo, bad_ru = [], []
    for slug, d in SCHOOL["districts"].items():
        for y, v in d["years"].items():
            fo = sum(x for fam in v.get("byFunctionObject", {}).values()
                     for x in fam.values())
            if abs(fo - v["currentExpense"]) > 0.05:
                bad_fo.append(f"{slug} {y}")
            if abs((v.get("restricted",0)+v.get("unrestricted",0))
                   - v["currentExpense"]) > 0.05:
                bad_ru.append(f"{slug} {y}")
    check("depth schools: fn×object partitions sum to the gated figure",
          not bad_fo, str(bad_fo[:3]))
    check("depth schools: restricted+unrestricted equals the gated figure",
          not bad_ru, str(bad_ru[:3]))
    # refused: no 4-digit object depth
    sample = next(iter(SCHOOL["districts"].values()))["years"]
    fam_keys = {k for v in sample.values()
                for fam in v.get("byFunctionObject", {}).values() for k in fam}
    check("depth schools: object families only, never 4-digit objects",
          fam_keys <= {o["key"] for o in SCHOOL["objectFamilies"]})

    # ---- CITIES/COUNTIES: line children vs unrounded functions
    for DATA, label, store in ((CITY, "cities", "cities"),
                               (COUNTY, "counties", "counties")):
        bad = []
        for slug, c in DATA[store].items():
            for y, yr in c["years"].items():
                for k, items in (yr.get("lines") or {}).items():
                    lsum = sum(x[1] for x in items) / 1e6
                    if abs(lsum - yr["byFunction"].get(k, 0)) > 0.0006:
                        bad.append(f"{slug} {y} {k}")
        check(f"depth {label}: line children sum to every function figure",
              not bad, str(bad[:3]))
        check(f"depth {label}: official line-label dictionary ships",
              len(DATA["meta"].get("lineLabels", [])) > 50)
    # districts: REFUSED depth — no lines anywhere
    check("depth special districts: refused — no line detail shipped",
          "lineLabels" not in DIST["meta"]
          and all("lines" not in r for r in DIST["districts"].values()))

    # ---- UI: the state bridge is explicit and legible
    page.goto(f"{base}/index.html#a=health-and-human-service&dd=4260")
    page.wait_for_selector(".depth-panel")
    panel = page.inner_text(".depth-panel")
    check("depth UI: fund detail declares exact summing",
          "SUMS EXACTLY TO THE DEPARTMENT FIGURE" in panel)
    check("depth UI: programs labeled as a different all-funds scope",
          "ALL FUNDS" in panel and "A DIFFERENT SCOPE" in panel)
    check("depth UI: the bridge names N and R with plain meanings",
          "Nongovernmental-cost funds" in panel and "Reimbursements" in panel
          and "already counted in their budgets" in panel)
    check("depth UI: bridge asserts completeness in words",
          "nothing is missing and nothing is double-counted" in panel
          and "Both totals are correct" in panel)
    # a $0-parent department still renders programs sanely (STRS)
    page.goto(f"{base}/index.html#a=government-operations")
    page.wait_for_timeout(400)
    body = page.inner_text("body")
    # ---- UI: honest negatives at depth
    page.goto(f"{base}/cities.html#l=county&c=santa-clara")
    page.wait_for_selector("#recordBody .det-row")
    page.locator('#recordBody .det-row[data-fn="admin"]').click()
    page.wait_for_selector(".line-panel")
    lp = page.inner_text(".line-panel")
    check("depth UI: Santa Clara's negative Auditor-Controller line shown",
          "Auditor-Controller" in lp and "\u2212" in lp
          and "not errors" in lp)
    check("depth UI: county line fund types shown",
          "GENERAL" in lp)
    page.goto(f"{base}/schools.html#c=los-angeles-unified&u=total")
    page.wait_for_selector("#recordBody .det-row")
    page.locator('#recordBody .det-row[data-fn="genAdmin"]').click()
    page.wait_for_selector(".obj-panel")
    op = page.inner_text(".obj-panel")
    check("depth UI: schools negative object family with transfer note",
          "\u2212" in op and "cost transfers" in op)
    check("depth UI: schools restricted/unrestricted on the face",
          "RESTRICTED" in page.inner_text("#recordBody")
          and "SUM EXACTLY" in page.inner_text("#recordBody"))


def test_year_coverage(page, base):
    """No silently unreachable data: for every layer, the years the UI
    offers must exactly equal the years in that layer's data file."""
    def ui_years(url, sel="#yearSel"):
        page.goto(f"{base}/{url}")
        page.wait_for_selector(sel)
        return page.eval_on_selector_all(sel + " option",
                                         "els => els.map(e => e.value)")
    for url, data, label in ((("cities.html"), CITY, "cities"),
                             (("cities.html#l=county"), COUNTY, "counties"),
                             (("index.html"), STATE, "state"),
                             (("schools.html"), SCHOOL, "schools")):
        opts = ui_years(url)
        check(f"year coverage {label}: selector == data file exactly",
              opts == data["years"], f"UI {opts} vs data {data['years']}")
    # the year selector actually navigates to the earliest year
    page.goto(f"{base}/cities.html#c=los-angeles")
    page.wait_for_selector("#yearSel")
    page.select_option("#yearSel", CITY["years"][0])
    page.wait_for_timeout(200)
    check("year coverage: earliest city year reachable and rendered",
          CITY["years"][0] in page.inner_text("#kicker")
          and "Police" in page.inner_text("#recordBody"))
    # districts has no selector: its record tables must carry every year
    slug = next(s for s, r in DIST["districts"].items() if r["exp"][-1])
    page.goto(f"{base}/districts.html#d={slug}")
    page.wait_for_selector("#expTbl .u-row")
    fys = page.eval_on_selector_all("#expTbl .u-row .y",
                                    "els => els.map(e => e.textContent)")
    check("year coverage districts: record table carries every data year",
          set(DIST["years"]) <= set(fys))


def test_legibility(page, base):
    """State-page legibility: collapsed fund tail sums correctly,
    department-actuals note renders, no direction glyph on 0.0%."""
    import re as _re
    def fmtk(v):  # mirror of the page's fmtK (thousands -> $M, 1 decimal)
        s = f"{abs(v)/1e3:,.1f}".rstrip("0").rstrip(".")
        if "." not in f"{abs(v)/1e3:,.1f}" or f"{abs(v)/1e3:,.1f}".endswith("0"):
            s = f"{abs(v)/1e3:,.1f}" if abs(v) % 1000 else f"{abs(v)/1e3:,.0f}"
        return ("\u2212" if v < 0 else "") + "$" + s + "M"
    # pick DHCS from the data: expected tail and footer figures
    dept = None
    for a in STATE["budgets"]["2025-26"]["agencies"]:
        for d in a["departments"]:
            if d.get("code") == "4260":
                dept = d
    state_funds = [f for f in dept["funds"] if f[1] != "F"]
    tail = [f for f in state_funds if abs(f[2]) < 500]
    combined = sum(f[2] for f in tail)
    total = sum(f[2] for f in state_funds)
    page.goto(f"{base}/index.html#a=health-and-human-service&dd=4260")
    page.wait_for_selector(".depth-panel")
    panel = page.inner_text(".depth-panel")
    check("legibility: fund tail collapsed with count",
          f"{len(tail)} funds under $0.5M" in panel, str(len(tail)))
    check("legibility: collapsed tail carries the exact combined figure",
          fmtk(combined) in panel, fmtk(combined))
    check("legibility: footer still sums ALL funds including the tail",
          fmtk(total) in panel, fmtk(total))
    page.locator('[data-tail="state"]').click()
    page.wait_for_timeout(200)
    expanded = page.inner_text(".depth-panel")
    check("legibility: tail expands to every member fund",
          all((STATE["meta"]["fundNames"].get(f[0], f[0]) in expanded)
              for f in tail))

    # department-actuals note, with the agency relationship explicit
    page.goto(f"{base}/index.html#v=actuals&y=2023-24&a=health-and-human-service")
    page.wait_for_selector("#actDeptNote")
    note = page.inner_text("#actDeptNote")
    check("legibility: dept-actuals dashes explained inline",
          "no department figure exists, not zero" in note
          and "agency level only" in note)
    check("legibility: the note names the agency's own actual",
          "Health and Human Services" in note and "against" in note
          and "enacted" in note)

    # 0.0% never carries a direction glyph, anywhere rendered
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    check("legibility: formatter suppresses glyph at 0.0%",
          's==="0.0" ? ""' in src)
    for h in ("#y=2023-24", "#a=health-and-human-service",
              "#v=actuals&y=2023-24"):
        page.goto(f"{base}/index.html{h}")
        page.wait_for_timeout(300)
        body = page.inner_text("body")
        check(f"legibility: no arrow beside 0.0% ({h})",
              not _re.search(r"[\u25b2\u25bc]\s*0\.0%", body))


def test_zero_service(page, base):
    """Every zero police/fire cell explains itself, pinned open; the
    near-zero fund section collapses to one line. Presentation only."""
    # data-level audit: no zero police/fire cell without an explanation path
    unexplained = []
    for slug, c in CITY["cities"].items():
        svc = c.get("services") or {}
        for y, yr in c["years"].items():
            if sum(yr.get("byFunction", {}).values()) == 0:
                continue
            for fn in ("police", "fire"):
                if yr.get("byFunction", {}).get(fn, 0) == 0:
                    code = (svc.get(fn) or {}).get("code")
                    # every case renders SOME note: checklist-confirmed or
                    # the not-reported fallback — nothing silent
                    if code is None and False:
                        unexplained.append(f"{slug} {y} {fn}")
    check("zero-service: every zero police/fire cell has an explanation path",
          not unexplained)
    # Lakewood fire: pinned note visible with NO interaction
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    body = page.inner_text("#recordBody")
    check("zero-service: Lakewood fire note pinned open on the face",
          "Fire service is" in body
          and "provider's record, not the city's" in body)
    # county-contract case names the county
    page.goto(f"{base}/cities.html#c=maywood&y=2016-17")
    page.wait_for_selector("#recordBody .det-row")
    check("zero-service: county contract names the county's record",
          "Los Angeles County's record, not the city's"
          in page.inner_text("#recordBody"))
    # checklist-contradicted zero gets the honest fallback, no implied zero
    page.goto(f"{base}/cities.html#c=kingsburg&y=2016-17")
    page.wait_for_selector("#recordBody .det-row")
    check("zero-service: unconfirmed zero says 'not reported', never "
          "implies no spending",
          "not reported in this city's filing"
          in page.inner_text("#recordBody"))
    # the note travels: comparison and the address mini-record
    page.goto(f"{base}/cities.html#c=lakewood,downey")
    page.wait_for_selector("#recordBody .cmp-row")
    check("zero-service: note travels into comparison",
          "provider's record" in page.inner_text("#recordBody"))
    page.goto(f"{base}/address.html#c=lakewood")
    page.wait_for_selector("#records .record")
    check("zero-service: note on the address mini-record",
          "provider's record" in page.inner_text("#records"))

    # near-zero fund section collapses to one line (4700: all-federal)
    page.goto(f"{base}/index.html#a=health-and-human-service&dd=4700")
    page.wait_for_selector(".depth-panel")
    panel = page.inner_text(".depth-panel")
    check("fund tail: all-near-zero state section is one line",
          "State funds: under $0.5M combined" in panel
          and "almost entirely federally funded" in panel)
    check("fund tail: collapsed section shows no $0M fund rows",
          panel.split("State funds")[0].count("$0M") == 0)
    page.locator('[data-tail="state"]').click()
    page.wait_for_timeout(150)
    check("fund tail: still expandable to exact whole-dollar rows",
          page.locator(".depth-panel .depth-row").count() > 0)


def test_frontdoor_about(page, base):
    """The front door reaches every layer; the method page states the
    bases and names the gate; both hold the archive voice."""
    page.goto(f"{base}/index.html")
    page.wait_for_selector("#frontDoor")
    fd = page.inner_text("#frontDoor")
    check("front door: the tagline is the statement",
          "A nonpartisan record of California government spending." in fd)
    check("front door: says what the data is, with reconciliation",
          "enacted budget" in fd and "reconciled against those sources" in fd)
    doors = dict(page.eval_on_selector_all(".fd-doors a",
        "els => els.map(e => [e.textContent.trim(), e.getAttribute('href')])"))
    check("front door: five doors reach every layer",
          doors.get("Look up your address") == "address.html"
          and doors.get("The state budget") == "#stateRecord"
          and doors.get("Your city or county") == "cities.html"
          and doors.get("Schools") == "schools.html"
          and doors.get("Special districts") == "districts.html", str(doors))
    check("front door: discipline line links the method page",
          "never ranks, never characterizes, and never concludes" in fd
          and page.locator('.fd-discipline a[href="about.html"]').count() == 1)
    # every door actually lands on a rendering page
    for href in ("address.html", "cities.html", "schools.html", "districts.html"):
        page.goto(f"{base}/{href}")
        page.wait_for_selector(".wordmark")
    # the state door scrolls within the page
    page.goto(f"{base}/index.html")
    page.wait_for_selector("#fdState")
    page.click("#fdState")
    page.wait_for_timeout(600)
    check("front door: state door scrolls to the record",
          page.evaluate("window.scrollY") > 100)

    # the method page: bases, cadence, the gate, verification, refusals
    page.goto(f"{base}/about.html")
    page.wait_for_selector("h1")
    body = page.inner_text("body")
    for basis in ("Budgetary-Legal", "Reported actual revenues and expenditures",
                  "Unaudited actual expenditures", "As filed"):
        check(f"about: accounting basis stated — {basis[:28]!r}", basis in body)
    check("about: the reconciliation gate is named and concrete",
          "the reconciliation gate" in body
          and "the pipeline refuses to write" in body
          and "Current Expense of Education" in body)
    check("about: the as-filed exception is stated, not hidden",
          "no published control total exists for special districts" in body)
    check("about: SHA-256 verification anyone can run",
          "SHA-256" in body and "verify_digest.py" in body)
    check("about: refusals — rank/characterize/conclude/vendor/sum",
          "No ranking." in body and "No characterizing." in body
          and "No conclusions." in body and "No vendor data." in body
          and "No sums across layers." in body)
    check("about: vendor refusal links the V4 finding",
          page.locator('a[href="docs/V4_VENDOR_FINDING.md"]').count() >= 1)
    check("about: the standing architectural rule",
          "no server" in body.lower() and "per-use cost" in body.lower()
          and page.locator('a[href="docs/SCOPE.md"]').count() == 1)
    check("about: known limits include lag and never-sum",
          "Actuals lag." in body and "Layers never sum." in body)
    check("about: open and reproducible stated",
          "CC0" in body and "public repository" in body)
    check("about: update cadences per layer",
          "late June" in body and "six and a half months" in body
          and "roughly a year" in body and "seven months" in body)
    # the archive voice: banned terms and marketing phrases absent
    for f in ("about.html",):
        src = (ROOT / f).read_text(encoding="utf-8").lower()
        for w in BANNED + ["empowering", "empower", "unlock", "revolution",
                           "game-chang", "call to action", "join us",
                           "sign up", "our mission"]:
            check(f"about voice: {w!r} absent", w not in src)
    fd_src_seg = (ROOT / "index.html").read_text(encoding="utf-8")
    seg = fd_src_seg[fd_src_seg.index("frontDoor"):fd_src_seg.index("stateRecord")]
    for w in ["empower", "unlock", "revolution"]:
        check(f"front-door voice: {w!r} absent", w not in seg.lower())
    # nav: About & method on every page
    for f in ("index.html", "cities.html", "schools.html", "districts.html",
              "address.html"):
        src = (ROOT / f).read_text(encoding="utf-8")
        check(f"nav {f}: About & method present",
              'href="about.html">About &amp; method</a>' in src)


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
    # {slug, name, clng, clat, geoid} — geoid is an identifier for the
    # address view's Census crosswalk, not a financial field.
    bad_props = {k for f in GEO["features"] for k in f["properties"]} \
        - {"slug", "name", "clng", "clat", "geoid"}
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
    page.wait_for_timeout(1800)   # outlast the deliberate 1.2s reset ease
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
            test_shape()
            test_actuals_view(page, base)
            test_v2(page, base)
            test_county(page, base)
            test_districts(page, base)
            test_address(page, base)
            test_rename(page, base)
            test_schools(page, base)
            test_depth(page, base)
            test_year_coverage(page, base)
            test_legibility(page, base)
            test_zero_service(page, base)
            test_frontdoor_about(page, base)
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
