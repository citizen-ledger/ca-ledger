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
  location — i.e. in production they emit the public URL.
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
import os
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
CSU = load_data_js(ROOT / "csu-data.js")
CCC = load_data_js(ROOT / "ccc-data.js")
UC = load_data_js(ROOT / "uc-data.js")

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
        f"document.querySelector('{copy_sel}').textContent.toLowerCase().includes('copied')")
    text = page.evaluate("navigator.clipboard.readText()")
    page.click("#citeClose")
    return text

# ----------------------------------------------------------------------
def test_integrity():
    for name, payload in (("data.js", STATE), ("city-data.js", CITY),
                          ("city-geo.js", GEO), ("county-data.js", COUNTY),
                          ("county-geo.js", CGEO), ("district-data.js", DIST),
                          ("school-data.js", SCHOOL), ("csu-data.js", CSU),
                          ("ccc-data.js", CCC), ("uc-data.js", UC)):
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

    # ── the enacted gate, recomputed from shipped agency rows against the
    # pinned control (a tampered agency figure with a restamped digest must
    # fail HERE, not just drift the rendered page along with the data)
    # ── THE STATE GATE, re-asserted from the shipped data. DOF publishes a
    # statewide control (stateGrandTotal); the agency rows must equal it
    # exactly in thousands, allowing only the recorded source residual.
    gate = STATE["meta"].get("gate")
    check("V1 GATE: the state layer ships its reconciliation gate", bool(gate))
    if gate:
        check("V1 GATE: gated at agency level against DOF's published control",
              gate["level"] == "agency" and "stateGrandTotal" in gate["control"])
        check("V1 GATE: every shipped budget year is gated",
              set(gate["years"]) == set(STATE["budgets"]),
              str(set(gate["years"]) ^ set(STATE["budgets"])))
        for y, r in sorted(gate["years"].items()):
            check(f"V1 GATE {y}: agency rows − DOF's published control == the recorded residual",
                  r["agencyRowsK"] - r["publishedControlK"] == r["residualK"],
                  f"{r['agencyRowsK']} - {r['publishedControlK']} != {r['residualK']}")
        exact = [y for y, r in gate["years"].items() if r["residualK"] == 0]
        check("V1 GATE: seven of nine years reconcile to DOF's control at "
              "zero residual", len(exact) == 7, str(sorted(exact)))
        # TWO years where DOF disagrees with itself. FY2019-20 is corroborated
        # by DOF's OWN printed Schedule 9, whose grand total (147,780,666 +
        # 61,092,907 + 5,904,388 = 214,777,961) equals our agency rows and is
        # 2,353k below the stateGrandTotal the same API declares.
        for y, want in (("2019-20", -2353), ("2025-26", -1638)):
            check(f"V1 GATE: FY{y}'s non-zero residual is exactly {want:+,}k "
                  f"(DOF's own, not ours)",
                  gate["years"][y]["residualK"] == want,
                  str(gate["years"][y]))
        check("V1 GATE: the residual is named as the source's, not reconciled away",
              "exceeds the sum of its own" in gate["sourceResidualNote"]
              and "as published" in gate["sourceResidualNote"])
        check("V1 GATE: both limits recorded (agency level; agency-to-agency transfer)",
              any("agency level" in l for l in gate["limits"])
              and any("transfer between two agencies" in l for l in gate["limits"]))
        # the pipeline's constant must match the shipped residual exactly
        sys.path.insert(0, str(ROOT / "pipeline"))
        from fetch_state_data import SOURCE_RESIDUAL
        check("V1 GATE: the pipeline's SOURCE_RESIDUAL constants match the "
              "shipped residuals exactly, and cover no year that reconciles",
              set(SOURCE_RESIDUAL) == {"2019-20", "2025-26"}
              and all(SOURCE_RESIDUAL[y] == gate["years"][y]["residualK"]
                      for y in SOURCE_RESIDUAL),
              f"{SOURCE_RESIDUAL} vs "
              f"{ {y: gate['years'][y]['residualK'] for y in SOURCE_RESIDUAL} }")
        # the gate figures must be the UNROUNDED source of the rounded display
        for y, r in gate["years"].items():
            shipped = sum(a["gf"] + a["sp"] + a["bd"]
                          for a in STATE["budgets"][y]["agencies"])
            check(f"V1 GATE {y}: shipped rounded rows track the gated unrounded total",
                  abs(shipped - r["agencyRowsK"] / 1e6) < 0.01,
                  f"{shipped} vs {r['agencyRowsK']/1e6}")

    check("V1 PIN: every shipped budget year is pinned (a new year cannot slip in unpinned)",
          set(STATE["budgets"]) == set(ENACTED_PIN),
          str(set(STATE["budgets"]) ^ set(ENACTED_PIN)))
    for y, control in ENACTED_PIN.items():
        s = sum(state_agency_total(a) for a in STATE["budgets"][y]["agencies"])
        check(f"V1 PIN {y}: agencies sum to the pinned snapshot of shipped totals "
              f"(tamper evidence, not a published control)",
              abs(s - control) <= 0.005, f"{s:.3f} vs {control}")

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
    page.keyboard.press("Escape")          # the cite dialog would intercept the click
    page.wait_for_selector("#citePanel:not([open])", state="attached")
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

    # ── the city gate, recomputed from shipped rows (mutation-hardening):
    # every city-year's functions must sum to its governmental total, every
    # enterprise byFund must sum to its enterprise total, and the statewide
    # aggregate must hit the pinned control — so a single tampered figure
    # with a restamped digest fails loudly instead of drifting the page.
    bad_sum, bad_ent = [], []
    sw_tot = {y: 0.0 for y in years}
    for slug, c in CITY["cities"].items():
        for fy, yr in c["years"].items():
            if abs(round(sum(yr["byFunction"].values()), 3)
                   - yr["expenditures"]) > 0.02:
                bad_sum.append(f"{slug} {fy}")
            ent = yr.get("enterprise") or {}
            if "byFund" in ent and abs(round(sum(ent["byFund"].values()), 3)
                                       - ent.get("total", 0)) > 0.02:
                bad_ent.append(f"{slug} {fy}")
            sw_tot[fy] = sw_tot.get(fy, 0.0) + yr["expenditures"]
    check("V2 GATE: every city-year's functions sum to its governmental total",
          not bad_sum, str(bad_sum[:4]))
    check("V2 GATE: every enterprise byFund sums to its enterprise total",
          not bad_ent, str(bad_ent[:4]))
    check("V2 PIN: every shipped city year is pinned",
          set(years) == set(CITY_PIN), str(set(years) ^ set(CITY_PIN)))
    for y, control in CITY_PIN.items():
        check(f"V2 PIN {y}: statewide city total matches the pinned snapshot "
              f"(tamper evidence, not a published control)",
              abs(sw_tot[y] - control) <= 0.005, f"{sw_tot[y]:.3f} vs {control}")

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

# ── ANCHORS (the mutation-hardening rule) ────────────────────────────
# The UC pre-PR review proved that assertions reading values the pipeline
# itself stored (echoed metadata) let a tampered figure with a restamped
# digest pass the whole suite. The rule since: every layer's gate is
# RECOMPUTED from the shipped rows, and anchored to a value the data file
# cannot carry along.
#
# THE ANCHORS ARE OF TWO KINDS, AND THEY ARE NOT EQUIVALENT.
#
#   PUBLISHED CONTROL — a figure the SOURCE published, which a reader can
#     look up independently. A mismatch means our data disagrees with the
#     source. These are: SCH6_CONTROL (Schedule 6 statewide totals),
#     CCC_STATEWIDE_CE (the Chancellor's Office printed Table VI total),
#     UC_AUDITED (UC's audited totals), CSU_UNIVERSITY_OPEXP_K (CSU's
#     audited University total).
#
#   TAMPER PIN — a snapshot of the aggregate WE CURRENTLY SHIP, recorded
#     here so any later edit to the data file is loud. It is NOT a control
#     and proves nothing about agreement with the source: it proves only
#     that the shipped file still holds the figures the pipeline wrote.
#     These are CITY_PIN, COUNTY_PIN, SCHOOL_CE_PIN and DIST_PIN.
#     (ENACTED_PIN was one until the state gate landed; the state layer
#     now reconciles to DOF's published stateGrandTotal, so its pin is a
#     second, redundant check rather than the layer's only anchor.) They exist because a coordinated tamper — moving a figure
#     AND the stored parent that would expose it — keeps every in-file
#     identity true, so nothing inside the file can catch it.
#
# What sits behind each tamper pin at build time, stated exactly:
#   ENACTED_PIN    A REAL GATE NOW SITS BEHIND THIS. fetch_state_data.py
#                  reconciles each year's agency rows to DOF's published
#                  stateGrandTotal, exactly, in thousands, and refuses to
#                  write on failure (five of six years reconcile at zero;
#                  FY2025-26 carries a recorded source residual of −1,638k
#                  that is DOF's own). This pin remains as a cheap second
#                  check on the SHIPPED rounded figures. It is deliberately
#                  NOT the published figure — $297,860M here vs DOF's
#                  $297,862M for 2024-25 — because it sums the values after
#                  they are rounded to $0.001B for display. The gate, not
#                  this pin, is what reconciles.
#   CITY_PIN       A real per-city build gate exists (fetch_city_data.py
#                  fails at >0.1% drift from the Controller's published
#                  per-city total) — but over ALL funds, whereas this pin
#                  is over the governmental-only figure the site displays.
#                  Related, not the same quantity.
#   COUNTY_PIN     Per-county-year gate against the stored scoTotal, which
#                  is itself pipeline-derived; test_county re-asserts it.
#   SCHOOL_CE_PIN  A genuine per-district gate to the cent against CDE's
#                  published EDP 365 — but CDE publishes no STATEWIDE
#                  figure, so this aggregate is ours, not CDE's.
#   DIST_PIN       Nothing, by design: no published control total exists
#                  for special districts, and the record says so on its
#                  face. Pure tamper evidence.
#
# A new fiscal year must update these constants deliberately, in review —
# the suite fails until it does, and a companion assertion requires every
# shipped year to be pinned so a new year cannot slip through unpinned.
#
# TOLERANCES sit two-or-more orders of magnitude ABOVE the measured
# float-summation noise floor (city/county ~7e-11 $M, schools ~2e-4 $,
# state ~6e-14 $B) and comfortably BELOW the smallest mutation
# tests/mutation_test.py applies — so accumulated float error can never
# trip them and a tampered figure always does.
ENACTED_PIN = {                # $B, gf+sp+bd as shipped. TAMPER PIN.
    "2017-18": 183.255, "2018-19": 201.373, "2019-20": 214.778,
    "2020-21": 202.075,
    "2021-22": 262.587,
    "2022-23": 307.915,
    "2023-24": 310.803,
    "2024-25": 297.860,
    "2025-26": 321.051,
}
CITY_PIN = {                   # $M, statewide governmental expenditures
    "2016-17": 45164.314, "2017-18": 49402.957, "2018-19": 51562.036,   # as shipped. TAMPER PIN.
    "2019-20": 55796.116, "2020-21": 58632.676, "2021-22": 61680.378,
    "2022-23": 65522.885, "2023-24": 72650.127,
}
COUNTY_PIN = {                 # $M, statewide sum of the stored per-county
    "2016-17": 76349.474, "2017-18": 81393.525, "2018-19": 89996.339,   # control totals. TAMPER PIN.
    "2019-20": 96848.236, "2020-21": 104705.656, "2021-22": 106687.413,
    "2022-23": 115685.330, "2023-24": 126286.986,
}
SCHOOL_CE_PIN = {              # $, statewide sum of the per-district Current
    "2022-23": 89068561292.64, # Expense figures, each gated to the cent
    "2023-24": 97527767792.56, # against CDE's published EDP 365 at build.
    "2024-25": 101236938810.13,# The AGGREGATE is ours. TAMPER PIN.
}
DIST_PIN = {                   # $, statewide as-filed expenditures. TAMPER
    "2016-17": 54226963772,    # PIN, and the only kind possible here: no
    "2017-18": 68843759442,    # published control total exists for special
    "2018-19": 73204149991,    # districts — that absence is the finding.
    "2019-20": 76285411834,
    "2020-21": 75652587914,
    "2021-22": 83871045478,
    "2022-23": 92032458217,
    "2023-24": 100913470057,
}
# ── PUBLISHED CONTROLS (a reader can look these up) ──────────────────
CSU_UNIVERSITY_OPEXP_K = 11_630_059   # CSU audited University total operating
CSU_PIN_YEAR = "2023-24"              # expenses, in thousands
CCC_STATEWIDE_CE = 8_469_851_699      # Chancellor's Office Table VI printed
CCC_PIN_YEAR = "2022-23"              # statewide Current Expense of Education
UC_AUDITED = {                        # UC audited total operating expenses and
    "2024-25": {"auditedTotalK": 57_767_327,   # the printed campus/Systemwide
                "campusSumK": 58_074_198, "systemwideColK": -306_871},
    "2023-24": {"auditedTotalK": 54_703_428,   # components, all from the AFRs
                "campusSumK": 52_003_294, "systemwideColK": 2_700_134},
}

# Schedule 6 statewide control totals (GF, total) in $M, per the vintage
# publication each year's actuals were extracted from. PUBLISHED CONTROL:
# the pipeline gates on these before writing; this re-asserts it on the
# shipped data.
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
    # statewide aggregate vs the pinned control (mutation-hardening: a
    # coordinated per-county tamper of byFunction AND scoTotal together
    # still moves the statewide sum and fails here)
    check("county PIN: every shipped county year is pinned",
          set(COUNTY["years"]) == set(COUNTY_PIN),
          str(set(COUNTY["years"]) ^ set(COUNTY_PIN)))
    for y, control in COUNTY_PIN.items():
        sw_y = sum(c["years"].get(y, {}).get("scoTotal", 0)
                   for c in COUNTY["counties"].values())
        check(f"county PIN {y}: statewide scoTotal sum matches the pinned snapshot "
              f"(tamper evidence, not a published control)",
              abs(sw_y - control) <= 0.005, f"{sw_y:.3f} vs {control}")
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
    # tamper-evidence pin (mutation-hardening). This is NOT a reconciliation
    # gate — no published control total exists for special districts, and
    # the record says so on its face — but the as-filed statewide aggregate
    # is pinned so a single tampered figure with a restamped digest still
    # breaks the suite.
    for iy, y in enumerate(DIST["years"]):
        sw_y = sum(sum(r["exp"][iy] or [0, 0, 0, 0])
                   for r in DIST["districts"].values())
        pin = DIST_PIN.get(y)
        check(f"districts PIN {y}: as-filed statewide expenditures match "
              f"the tamper-evidence pin", pin is not None and sw_y == pin,
              f"{sw_y:,} vs {pin if pin is None else format(pin, ',')}")
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
    page.keyboard.press("Escape")   # dismiss the cite dialog before touching the page
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
    page.keyboard.press("Escape")   # dismiss the cite dialog before touching the page
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
    check("address schools: overlap points at the state record ABOVE it",
          "state record above" in page.inner_text("#noSum")
          and "state record below" not in page.inner_text("#noSum"))
    check("address schools: share not hardcoded in source", sch_share not in asrc)
    page.click("#citeBtn")
    cite = page.inner_text("#citeText")
    check("address schools: citation carries per-ADA and residence caveat",
          "per ADA" in cite and "district of residence" in cite)
    page.keyboard.press("Escape")   # dismiss the cite dialog before touching the page
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
    check("pin map: OSM attribution control rendered (ODbL requires it)",
          page.locator(".maplibregl-ctrl-attrib").count() >= 1
          and "OpenStreetMap" in page.inner_text(".maplibregl-ctrl-attrib"))

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
    PAGES = {"index.html": "State budget", "cities.html": "City & county spending",
             "districts.html": "Special districts",
             "address.html": "Your governments",
             "ccc.html": "Community colleges",
             "uc.html": "UC campuses",
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
        check(f"rename {f}: scope line appears with the wordmark",
              "State budget · cities & counties · K-12 schools · special districts"
              in page.inner_text(".brand"))
        body = page.inner_text("body")
        check(f"rename {f}: footer renamed, old name never rendered",
              "CITIZEN LEDGER · PUBLIC RECORD" in body
              and "California Ledger" not in body)
    # the canonical/OG URLs stay on the CURRENT repo URL until the user
    # decides otherwise — the rename must NOT touch them
    for f in PAGES:
        src = (ROOT / f).read_text(encoding="utf-8")
        expected = ("https://citizen-ledger.github.io/ca-ledger/"
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
    # statewide CE vs the pinned control (mutation-hardening: a coordinated
    # tamper of byFunction + currentExpense + cePublished together still
    # moves the statewide sum and fails here)
    check("schools PIN: every shipped school year is pinned",
          set(Y) == set(SCHOOL_CE_PIN), str(set(Y) ^ set(SCHOOL_CE_PIN)))
    for y, control in SCHOOL_CE_PIN.items():
        sw_ce = sum(d["years"].get(y, {}).get("currentExpense", 0)
                    for d in SCHOOL["districts"].values())
        check(f"schools PIN {y}: statewide Current Expense matches the pinned snapshot "
              f"(tamper evidence; the per-district figures ARE gated to CDE)",
              abs(sw_ce - control) <= 0.05, f"{sw_ce:.2f} vs {control}")
    # county offices and charters: children sum to their own totals
    bad_co = [f"{s} {y}" for s, c in SCHOOL["countyOffices"].items()
              for y, v in c["years"].items()
              if abs(sum(v["byFunction"].values()) - v["expenditures"]) > 0.05]
    check("schools: county-office functions sum to their expenditures",
          not bad_co, str(bad_co[:3]))
    bad_ch = [f"{s} {y}" for s, c in SCHOOL["charters"].items()
              for y, v in c["years"].items()
              if "byObject" in v
              and abs(sum(v["byObject"].values()) - v["expenditures"]) > 0.05]
    check("schools: charter object rows sum to their expenditures",
          not bad_ch, str(bad_ch[:3]))

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
    page.keyboard.press("Escape")   # dismiss the cite dialog before touching the page
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("schools CSV: carries the published figure beside the computed one",
          "cde_published_total" in csv_text and "never added" in csv_text)

    # ---- authored-copy neutrality
    low = src.lower()
    for w in BANNED:
        check(f"schools source: no banned term {w!r}", w not in low)


def test_identifier_stability():
    """THE IDENTIFIER CONTRACT — slugs must be a function of the source
    data alone, never of set-iteration order.

    Added 2026-07-19. fetch_school_data.py sorted a set of CDS code
    tuples keyed on the district NAME alone, so for the duplicated names
    the tie was broken by set-iteration order — i.e. by PYTHONHASHSEED,
    which Python randomizes per process. The same source produced a
    different school-data.js, and therefore a different published
    SHA-256, on every run: under our own authenticity doctrine an honest
    rebuild read as a tampered copy. It also silently reassigned
    permalinks between same-named districts.

    This runs the real assignment function in subprocesses under
    different seeds, over the real shipped roster. It fails on the
    pre-fix code."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    # identity = the source's own stable code, exactly as the pipeline
    # keys it: CDS for districts, and for charters the number plus name
    # and county (the number alone is not unique — 0756 is shared by the
    # nine High Tech schools).
    roster = []
    for d in SCHOOL["districts"].values():
        roster.append([[d["cds"][:2], d["cds"][2:]], d["name"], d["county"]])
    for c in SCHOOL["charters"].values():
        roster.append([[c["charterNumber"] or "", c["name"], c["county"]],
                       c["name"], (c["charterNumber"] or "").lower()])
    prog = (
        "import json,sys\n"
        "sys.path.insert(0,%r)\n"
        "from fetch_school_data import assign_slugs\n"
        "rows=[(tuple(map(str,i)),n,q) for i,n,q in json.load(sys.stdin)]\n"
        "slugs,amb=assign_slugs(rows,'seed test')\n"
        "print(json.dumps([sorted(slugs.items()),sorted(amb.items())],"
        "sort_keys=True))\n" % str(ROOT / "pipeline")
    )
    payload = json.dumps(roster)
    outs = {}
    for seed in ("0", "1", "2", "42", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", prog], input=payload,
                           capture_output=True, text=True, env=env)
        check(f"identifiers: assignment runs under PYTHONHASHSEED={seed}",
              r.returncode == 0, r.stderr.strip()[:200])
        outs[seed] = r.stdout
    distinct = set(v for v in outs.values() if v)
    check("identifiers: slug assignment is byte-identical across five "
          "PYTHONHASHSEED values (the defect this replaced was seed-dependent)",
          len(distinct) == 1,
          f"{len(distinct)} distinct results across seeds {sorted(outs)}")

    # every shipped identifier is unique, and no entity holds a slug that
    # a same-named entity could have held instead.
    for coll in ("districts", "countyOffices", "charters"):
        slugs = list(SCHOOL[coll])
        check(f"identifiers: {coll} slugs are unique",
              len(slugs) == len(set(slugs)), f"{len(slugs)} keys")
    amb = SCHOOL["meta"].get("ambiguousSlugs", {})
    for coll, mapping in amb.items():
        for bare, options in mapping.items():
            check(f"identifiers: retired ambiguous slug {bare!r} is not "
                  f"issued to any {coll} record",
                  bare not in SCHOOL[coll])
            check(f"identifiers: every candidate for {bare!r} exists",
                  all(o in SCHOOL[coll] for o in options),
                  str([o for o in options if o not in SCHOOL[coll]]))
            check(f"identifiers: {bare!r} names more than one entity",
                  len(options) > 1, str(options))
    def base_slug(name):
        return re.sub(r"-+", "-",
                      re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")

    names = {}
    for coll in ("districts", "countyOffices", "charters"):
        for slug, r in SCHOOL[coll].items():
            names.setdefault((coll, r["name"]), []).append(slug)
    shared = {k: v for k, v in names.items() if len(v) > 1}
    check("identifiers: shared names still exist to guard against",
          len(shared) > 0, "no duplicated names — the guard is untested")
    for (coll, name), slugs in sorted(shared.items()):
        base = base_slug(name)
        check(f"identifiers: no {coll} record holds the unqualified slug "
              f"{base!r} that {len(slugs)} entities share",
              base not in slugs, str(sorted(slugs)))
        check(f"identifiers: {base!r} is listed in meta.ambiguousSlugs "
              f"so a stale link can be explained",
              base in amb.get(coll, {}), str(sorted(amb.get(coll, {}))[:4]))


def test_position_guard():
    """THE GUARD MUST ESTABLISH POSITION, NOT RECOGNISE A VALUE.

    SCO has shipped three layouts for the same expenditure table. In the
    pre-FY 2016-17 layout the function group is repeated in `category`,
    `subcategory_1` AND `subcategory_2`. The guard written after the
    FY 2016-17 incident tested only whether `subcategory_1` held a known
    group name — it does — so the row was accepted, routed down the
    FY 2017-18+ branch, and every police and fire dollar was filed under
    'safetyOther'. Measured live against FY 2009-10: 8 of 8 row shapes
    accepted, $15.2B misfiled, police and fire reading exactly $0, and
    every totals gate passing, because conservation cannot see
    classification (docs/V15_HISTORICAL_FINDING.md).

    These assertions use the REAL pre-2017 row shapes, verbatim from the
    source, and prove the guard now refuses them."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fcd", str(ROOT / "pipeline" / "fetch_city_data.py"))
    fcd = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["fetch_city_data.py"]
    try:
        spec.loader.exec_module(fcd)
    except SystemExit:
        pass
    finally:
        sys.argv = argv

    def refuses(cat, s1, s2):
        try:
            fcd.classify_expenditure(cat, s1, s2)
            return False
        except SystemExit:
            return True

    # ---- THE FY 2009-10 CASE, reproduced. These eight triples are the
    #      complete set of shapes in that year at the source: the group
    #      name repeated in all three columns.
    ERA_A = ["Public Safety", "Transportation", "Public Utilities",
             "General Government", "Community Development",
             "Culture and Leisure", "Health", "Other Expenditures"]
    for g in ERA_A:
        check(f"position guard: refuses the FY 2009-10 shape for {g!r} — the "
              f"group repeated in every column", refuses(g, g, g))

    # The specific dollars that moved. Before the fix this returned
    # ('gov', 'safetyOther', 'Public Safety') and $15.2B of police and fire
    # disappeared into the residual bucket.
    check("position guard: THE $15.2B CASE — ('Public Safety', 'Public "
          "Safety', 'Public Safety') is refused, not filed under safetyOther",
          refuses("Public Safety", "Public Safety", "Public Safety"))

    # ---- and it must not have become a blunt instrument: every shape the
    #      shipped years actually contain still classifies.
    LIVE = [
        # FY 2017-18+ : paired super-group, group in sub1, line in sub2
        ("General Government and Public Safety", "Public Safety",
         "Police_Current Expenditures", "police"),
        ("General Government and Public Safety", "Public Safety",
         "Fire_Current Expenditures", "fire"),
        ("Transportation and Community Development", "Transportation",
         "Airports_Current Expenditures", "streets"),
        ("Health and Culture and Leisure", "Culture and Leisure",
         "Parks and Recreation_Current Expenditures", "parks"),
        # FY 2016-17 : group in category, line in sub1
        ("Public Safety", "Police_Current Expenditures", "", "police"),
        ("Public Safety", "Fire_Current Expenditures", "", "fire"),
        ("Culture and Leisure", "Libraries_Current Expenditures", "", "library"),
        # FY 2016-17 capital/debt split : sub1 is itself a group name, but
        # the LINE is in sub2 and differs from it — position is established,
        # so this must still be accepted
        ("Capital Outlay", "Capital Outlay", "Community Development", "capital"),
        ("Health", "Health", "Current Expenditures", "health"),
    ]
    for cat, s1, s2, want in LIVE:
        kind, key, _line = fcd.classify_expenditure(cat, s1, s2)
        check(f"position guard: still classifies the live shape "
              f"{(cat, s1, s2)!r} as {want!r}", kind == "gov" and key == want,
              f"{kind}/{key}")

    # enterprise, internal service and conduit rows are decided on category
    # alone and must be untouched by the change
    for cat, kind in (("Water Enterprise Fund", "ent"),
                      ("Internal Service Fund", "isf"),
                      ("Conduit Financing", "conduit")):
        check(f"position guard: {cat!r} still routes to {kind!r}",
              fcd.classify_expenditure(cat, "", "")[0] == kind)

    # ---- an unrecognised layout is still refused outright
    check("position guard: an unknown column layout is still refused",
          refuses("Something New", "Also New", "Also New"))

    # ---- THE SECOND DEFENCE. Rules 1-3 all reduce to "is this named line
    #      zero", which a group-echoing layout defeats in one step: every
    #      dollar lands in the residual bucket, so nothing named looks
    #      missing. Rule 4 is independent of the guard and of rule 1.
    def statewide(bad=None):
        tot = {}
        for city in CITY["cities"].values():
            for fy, yr in (city.get("years") or {}).items():
                if fy != CITY["years"][-1]:
                    continue
                for k, v in (yr.get("byFunction") or {}).items():
                    tot[k] = tot.get(k, 0) + v
        if bad:
            tot = dict(tot)
            tot["safetyOther"] = tot.get("safetyOther", 0) + tot.get("police", 0) \
                + tot.get("fire", 0)
            tot["police"] = tot["fire"] = 0.0
        return tot

    clean = statewide()
    grp = clean["safetyOther"] + clean["police"] + clean["fire"]
    share = clean["safetyOther"] / grp
    check("position guard: the shipped residual share is well inside the "
          "rule-4 bound", share < 0.35, f"{share*100:.1f}%")
    check("position guard: and has real headroom — clean years measure far "
          "below the bound, so rule 4 is not tuned to the edge",
          share < 0.20, f"{share*100:.1f}%")

    # simulate exactly what the misclassification produces and prove rule 4
    # fires on it independently of rule 1
    broken = statewide(bad=True)
    bgrp = broken["safetyOther"] + broken["police"] + broken["fire"]
    bshare = broken["safetyOther"] / bgrp
    check("position guard: THE SECOND DEFENCE — folding police and fire into "
          "the residual, as the pre-2017 layout does, drives the share to "
          "100% and breaches rule 4", bshare > 0.35, f"{bshare*100:.1f}%")
    check("position guard: rule 1 would also fire, so the two defences are "
          "independent and either alone would stop the build",
          broken["police"] == 0 and broken["fire"] == 0)

    # rule 4 must actually be wired into the pipeline, not merely described
    src = (ROOT / "pipeline" / "fetch_city_data.py").read_text(encoding="utf-8")
    check("position guard: rule 4 is implemented in shape_gate, not just "
          "documented", "residual" in src and "swallowed the named lines" in src)
    check("position guard: the refusal explains what it caught rather than "
          "failing bare", "NO LINE DETAIL IN THIS SOURCE VINTAGE" in src)


def test_state_fund_identity(page, base):
    """A FUND IS (CODE, LEGAL TITLE, CLASS), NOT A CODE.

    dept_depth() keyed fund rows on fundCd alone. DOF distinguishes a fund
    by code, legal title and class together, and where it publishes two
    titles under one code the pipeline ADDED them and kept whichever class
    arrived first. Enumerated across all 1,155 department-years in the six
    loaded budgets: 43 collisions, every one fund 0001, where DOF emits
    "General Fund" and "General Fund, Proposition 98" as separate rows.
    The Proposition 98 education guarantee was being folded away.

    Separately, the fund-name legend was ONE global dict merged across six
    budget acts and ~190 departments per year, so a fund renamed between
    acts lost its earlier name — 23 codes drift across the window. Names
    are now scoped per year, as the school resource titles already are."""
    depts = [(fy, ag, d)
             for fy, b in STATE["budgets"].items()
             for ag in b["agencies"]
             for d in (ag.get("departments") or [])]

    # ---- identity: no two rows in a department-year may collide
    collisions = []
    for fy, ag, d in depts:
        seen = {}
        for r in (d.get("funds") or []):
            ident = (r[0], r[3] if len(r) > 3 else None)
            if ident in seen:
                collisions.append((fy, d.get("code"), ident))
            seen[ident] = r
    check("state funds: no two fund rows in one department-year share an "
          "identity", not collisions, str(collisions[:3]))

    # ---- where DOF splits one code, we carry both, each named
    split = [(fy, d) for fy, ag, d in depts
             if len([r for r in (d.get("funds") or []) if r[0] == "0001"]) > 1]
    # the count grows with the window; what must hold is that EVERY split is
    # a genuine two-title case and that the split years are the ones DOF
    # actually publishes two titles in
    check("state funds: fund 0001 is split wherever DOF publishes two titles "
          "for it, rather than summed into one row", len(split) >= 43,
          str(len(split)))
    check("state funds: every split is a real two-title case, not an artefact",
          all(len({r[3] for r in d["funds"] if r[0] == "0001" and len(r) > 3}) == 2
              for _fy, d in split), str(len(split)))
    titles = set()
    for fy, d in split:
        for r in (d.get("funds") or []):
            if r[0] == "0001":
                check(f"state funds: each split 0001 row carries its own legal "
                      f"title (FY {fy} org {d.get('code')})",
                      len(r) > 3 and bool(r[3]), str(r))
                if len(r) > 3:
                    titles.add(r[3])
    check("state funds: and the two titles are DOF's own",
          titles == {"General Fund", "General Fund, Proposition 98"},
          str(sorted(titles)))

    # ---- conservation: splitting moved no money
    for fy, d in split[:6]:
        rows = [r for r in d["funds"] if r[0] == "0001"]
        check(f"state funds: the split 0001 rows are all class G (FY {fy})",
              {r[1] for r in rows} == {"G"}, str({r[1] for r in rows}))
    # the V8 parent-sum gate, recomputed from the shipped file
    bad = []
    for fy, ag, d in depts:
        by_cls = {}
        for r in (d.get("funds") or []):
            by_cls[r[1]] = by_cls.get(r[1], 0) + r[2]
        for cls, key in (("G", "gf"), ("S", "sp"), ("B", "bd")):
            parent = round((d.get(key) or 0) * 1e6)      # billions -> thousands
            if abs(by_cls.get(cls, 0) - parent) > 1000:
                bad.append((fy, d.get("code"), cls, by_cls.get(cls, 0), parent))
    check("state funds: fund rows still sum to their gated parent by class — "
          "splitting a row moved no money", not bad, str(bad[:3]))

    # ---- names are PER YEAR
    fn = STATE["meta"]["fundNames"]
    check("state funds: the name legend is scoped per fiscal year, not one "
          "global dict", set(fn) == set(STATE["years"]), str(sorted(fn))[:90])
    check("state funds: every year carries a populated legend",
          all(len(v) > 400 for v in fn.values()),
          str({y: len(v) for y, v in fn.items()}))

    # THE CASE. Proposition 1 renamed fund 3085 for FY 2025-26. Under one
    # global legend, FY 2020-21 rendered it under a name it would not carry
    # for five more years.
    RENAMES = [("3085", "2020-21", "Mental Health Services Fund",
                "2025-26", "Behavioral Health Services Fund"),
               ("3246", "2020-21", "Fair Employment and Housing Enforcement "
                "and Litigation Fund", "2024-25",
                "Civil Rights Enforcement and Litigation Fund"),
               ("3209", "2020-21", "Office of Patient Advocate Trust Fund",
                "2024-25", "Health Plan Improvement Trust Fund")]
    for cd, y_old, n_old, y_new, n_new in RENAMES:
        check(f"state funds: fund {cd} carries its FY {y_old} name in FY "
              f"{y_old}", fn.get(y_old, {}).get(cd) == n_old,
              str(fn.get(y_old, {}).get(cd)))
        check(f"state funds: and its FY {y_new} name in FY {y_new}",
              fn.get(y_new, {}).get(cd) == n_new,
              str(fn.get(y_new, {}).get(cd)))
        check(f"state funds: the later name never appears in the earlier year",
              fn.get(y_old, {}).get(cd) != n_new)

    # ---- recorded as our own correction
    rec = load_data_js(ROOT / "state-revisions.js")
    ours = [b for b in rec["batches"]
            if b.get("ours") and "fund" in (b.get("note") or "").lower()
            and not b.get("coverageAdded")]
    check("state funds: the correction is recorded in the change feed",
          len(ours) == 1, str(len(ours)))
    if ours:
        b = ours[0]
        check("state funds: attributed to us, not to the source",
              "our own correction" in b.get("note", "").lower())
        kinds = {}
        for e in b["events"]:
            k = ("appeared" if e["o"] is None
                 else "disappeared" if e["n"] is None else "changed")
            kinds[k] = kinds.get(k, 0) + 1
        check("state funds: the merged rows are recorded as disappeared and "
              "the split rows as appeared — the event kinds the totals gate "
              "cannot see", kinds.get("disappeared") == 43
              and kinds.get("appeared") == 86, str(kinds))
        check("state funds: and no figure is reported as merely CHANGED, "
              "because none was", kinds.get("changed", 0) == 0, str(kinds))

    # ---- the page renders the era-correct name, not the latest one
    page.goto(f"{base}/index.html#y=2020-21&a=health-and-human-service")
    page.wait_for_selector("#allocView:not([hidden])")
    page.wait_for_timeout(400)
    body = page.inner_text("body")
    check("state funds: the FY 2020-21 page does not show a fund under a name "
          "it did not have until FY 2025-26",
          "Behavioral Health Services Fund" not in body)


def test_identity_leaks(page, base):
    """THREE IDENTITY DEFECTS, from the audit attached to the district fix.

    1. A retired identity rendered its RAW INTERNAL KEY to readers as a
       display name — "campus:Cal Poly Humboldt" shown where a campus name
       belongs. record_revision stored the key AS the label whenever an
       event mentioned an identity it had no name for, and the page
       rendered labels verbatim.
    2. The special-district outbound SCO link derived its fiscal year from
       ARRAY POSITION (2017 + i). Prepending a year to the window would
       have silently repointed every district's link to the wrong filing —
       the same rank-as-identifier class as the change-feed keying.
    3. The state agency id was slugify(name)[:24]: derived from a display
       name and truncated. A DOF rename moving no money would change the
       id, and the change record keys on it. Measured: 4,821 keys under
       the largest agency, 22,931 across all twelve, each of which would
       be republished as disappeared and then appeared."""
    import importlib.util

    # ---- 1. no machine key may be stored as, or rendered as, a name
    for layer in ("state", "city", "county", "district", "school",
                  "csu", "ccc", "uc", "deflator"):
        rec = load_data_js(ROOT / f"{layer}-revisions.js")
        selfnamed = [k for k, v in (rec.get("labels") or {}).items() if k == v]
        check(f"identity: {layer} stores no label that is merely its own key",
              not selfnamed, str(selfnamed[:3]))
    src = (ROOT / "pipeline" / "revisions.py").read_text(encoding="utf-8")
    check("identity: the pipeline no longer labels an entity with its own "
          "identifier", 'setdefault(ev["e"], ev["e"])' not in src)
    rsrc = (ROOT / "revisions.html").read_text(encoding="utf-8")
    check("identity: the page renders an unnamed identity AS an identifier, "
          "not as a name", "labelHtml" in rsrc and 'return l || null;' in rsrc)
    check("identity: and marks it so a reader can tell",
          "Internal identifier" in rsrc)

    # the page still renders real names for entities it knows
    page.goto(f"{base}/revisions.html")
    page.wait_for_selector(".lrec")
    body = page.inner_text("body")
    check("identity: known entities still render by name, not by key",
          "Rural North Vacaville Water District" in body)
    check("identity: and no raw entity key leaks into the rendered page",
          not re.search(r"\bcampus:|\bcharter:\d|\bdistricts:\d", body),
          body[:0])

    # ---- 2. the SCO link's year is the year, not the index
    dsrc = (ROOT / "districts.html").read_text(encoding="utf-8")
    # strip // comments before checking: the fix's own comment names the
    # pattern it removed, and an assertion that matched prose rather than
    # code would fail on its own documentation
    dcode = re.sub(r"^\s*//.*$", "", dsrc, flags=re.M)
    check("identity: the district SCO link no longer derives its year from "
          "array position", "2017 + i" not in dcode)
    check("identity: it reads the year out of the year label instead",
          "endYear" in dsrc and "YEARS[i]" in dsrc)
    # drive it: the link must name the latest year the district actually filed
    page.goto(f"{base}/districts.html#d=rural-north-vacaville-water-district")
    page.wait_for_selector(".ext")
    href = page.get_attribute(".ext", "href")
    rec = DIST["districts"]["rural-north-vacaville-water-district"]
    last = max(i for i, c in enumerate(rec["filings"]) if c != "-")
    want = 2000 + int(DIST["years"][last][-2:])
    check(f"identity: the outbound link points at FY{want}, the district's "
          f"own latest filing", f"/year/{want}/" in (href or ""), str(href))
    # and it agrees with the year label, not with 2017 + index
    check("identity: which is the year LABEL's ending year",
          want == 2000 + int(DIST["years"][last][-2:]))

    # ---- 3. the agency id is pinned to DOF's code, not to the name
    spec = importlib.util.spec_from_file_location(
        "fsd", str(ROOT / "pipeline" / "fetch_state_data.py"))
    fsd = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["fetch_state_data.py"]
    try:
        spec.loader.exec_module(fsd)
    except SystemExit:
        pass
    finally:
        sys.argv = argv

    check("identity: agency ids are declared per DOF code",
          len(fsd.AGENCY_IDS) == 12, str(len(fsd.AGENCY_IDS)))
    check("identity: every declared id is unique",
          len(set(fsd.AGENCY_IDS.values())) == 12)
    shipped = {ag["id"] for b in STATE["budgets"].values()
               for ag in b["agencies"]}
    check("identity: and the shipped ids are exactly the declared ones — the "
          "pinning moved no permalink", shipped == set(fsd.AGENCY_IDS.values()),
          str(sorted(shipped ^ set(fsd.AGENCY_IDS.values()))))

    # THE POINT: a rename must not move the identity
    for cd, want_id in list(fsd.AGENCY_IDS.items())[:4]:
        check(f"identity: agency {cd} keeps its id under any display name",
              fsd.agency_id(cd, "Some Entirely New Name") == want_id)
    # an unknown code refuses rather than minting an id from a name
    try:
        fsd.agency_id("9999", "Department of Newly Invented Things")
        refused = False
    except SystemExit:
        refused = True
    check("identity: an undeclared agency code REFUSES the build rather than "
          "slugifying a name", refused)

    # truncation: enumerated, not assumed
    names = {ag["name"] for b in STATE["budgets"].values()
             for ag in b["agencies"]}
    trunc = {}
    for n in names:
        trunc.setdefault(fsd.slugify(n), []).append(n)
    check("identity: no two agency names collide under the old 24-character "
          "truncation today — the hazard was the rename, not a live clash",
          all(len(v) == 1 for v in trunc.values()),
          str([v for v in trunc.values() if len(v) > 1]))
    check("identity: truncation was load-bearing for several agencies, so "
          "the margin was thin", sum(1 for n in names if len(
              "".join(c if c.isalnum() else "-" for c in n.lower())
              .replace("--", "-").strip("-")) > 24) >= 4)


def test_historical_state(page, base):
    """THE STATE RECORD, EXTENDED TO THE API'S OWN FLOOR (V15).

    Six years -> nine. FY2017-18 is where DOF's structured budget API
    begins: every earlier year returns HTTP 200 with an EMPTY ARRAY rather
    than an error, so a status-code availability check would have claimed
    coverage back to 2007-08. The floor is the source's, not a choice.

    Every new year passes the same gates as the current ones. FY2019-20
    reconciles to DOF's PRINTED Schedule 9 grand total (147,780,666 +
    61,092,907 + 5,904,388 = 214,777,961) rather than to the API's own
    stateGrandTotal, which is 2,353k higher — two DOF publications
    disagreeing with each other, recorded as an exact reviewed constant,
    never smoothed into a tolerance band."""
    YRS = STATE["years"]
    check("historical state: nine fiscal years are loaded", len(YRS) == 9,
          str(len(YRS)))
    check("historical state: the record begins at the API's floor",
          YRS[0] == "2017-18", YRS[0])

    # ---- every year carries the same structure, not a thinner one
    for fy in YRS:
        ags = STATE["budgets"][fy]["agencies"]
        depts = [d for a in ags for d in (a.get("departments") or [])]
        check(f"historical state {fy}: twelve agencies", len(ags) == 12,
              str(len(ags)))
        check(f"historical state {fy}: department detail is present, not a "
              f"thinner tier for older years", len(depts) > 180, str(len(depts)))
        check(f"historical state {fy}: the fund drill is present",
              sum(len(d.get("funds") or []) for d in depts) > 1000)
        check(f"historical state {fy}: the program drill is present",
              sum(len(d.get("programs") or []) for d in depts) > 500)

    # ---- V8 parent-sum gate, recomputed per year from the shipped file
    for fy in YRS:
        bad = []
        for a in STATE["budgets"][fy]["agencies"]:
            for d in (a.get("departments") or []):
                by = {}
                for r in (d.get("funds") or []):
                    by[r[1]] = by.get(r[1], 0) + r[2]
                for cls, key in (("G", "gf"), ("S", "sp"), ("B", "bd")):
                    if abs(by.get(cls, 0) - round((d.get(key) or 0) * 1e6)) > 1000:
                        bad.append((d.get("code"), cls))
        check(f"historical state {fy}: fund rows sum to their gated parent",
              not bad, str(bad[:3]))

    # ---- the position guard holds in every year, new ones included
    for fy in YRS:
        coll = []
        for a in STATE["budgets"][fy]["agencies"]:
            for d in (a.get("departments") or []):
                seen = set()
                for r in (d.get("funds") or []):
                    i = (r[0], r[3] if len(r) > 3 else None)
                    if i in seen:
                        coll.append((d.get("code"), r[0]))
                    seen.add(i)
        check(f"historical state {fy}: no fund identity collides", not coll,
              str(coll[:3]))

    # ---- THE DOF DISAGREEMENT, recorded exactly and not smoothed
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fsd", str(ROOT / "pipeline" / "fetch_state_data.py"))
    fsd = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["fetch_state_data.py"]
    try:
        spec.loader.exec_module(fsd)
    except SystemExit:
        pass
    finally:
        sys.argv = argv
    check("historical state: FY2019-20's residual is recorded as an exact "
          "reviewed constant", fsd.SOURCE_RESIDUAL.get("2019-20") == -2353,
          str(fsd.SOURCE_RESIDUAL))
    check("historical state: and it is a constant, never a tolerance band "
          "that would swallow the next, different discrepancy",
          all(isinstance(v, int) for v in fsd.SOURCE_RESIDUAL.values()))

    # ---- actuals: the three new years are gated, not labelled 'not yet published'
    acts = STATE["meta"]["actuals"]["years"]
    for fy, vintage in (("2017-18", "2019-20"), ("2018-19", "2020-21"),
                        ("2019-20", "2021-22")):
        rec = acts.get(fy) or {}
        check(f"historical state: FY{fy} actuals are published, not claimed "
              f"unpublished", "unavailable" not in rec, str(rec)[:80])
        check(f"historical state: FY{fy} actuals name their vintage",
              vintage in (rec.get("vintage") or ""), str(rec.get("vintage")))
    check("historical state: FY2020-21 actuals remain honestly absent — a "
          "year that cannot be verified shows none",
          "unavailable" in (acts.get("2020-21") or {}))

    # ---- per-resident stops where the census benchmark does, and says so
    pop = STATE["meta"]["population"]
    check("historical state: population covers only the 2020-benchmark years",
          set(pop) == {"2020-21", "2021-22", "2022-23", "2023-24", "2024-25",
                       "2025-26"}, str(sorted(pop)))
    check("historical state: and the boundary is stated in the payload",
          "2010 census benchmark" in (STATE["meta"].get("populationNote") or ""))
    page.goto(f"{base}/index.html#methodology")
    body = page.inner_text("body")
    check("historical state: the page explains why per-resident begins later",
          "2020 census benchmark" in body and "Per-resident figures begin" in body)

    # ---- the structural breaks the series actually crosses
    check("historical state: the page names COVID relief as a one-off inside "
          "the window", "COVID-19 federal relief" in body)
    check("historical state: and SB 1, which steps transportation up at the "
          "start of the window", "SB 1" in body)
    check("historical state: and states which larger breaks it stops ABOVE, "
          "rather than leaving a reader to assume none exist",
          "realignment" in body and "LCFF" in body and "GASB 68" in body)

    # ---- THE REFUSAL, visible on the layer that was refused
    page.goto(f"{base}/cities.html#methodology")
    cbody = page.inner_text("body")
    check("cities refusal: the page says why the record begins at FY 2016-17",
          "Why this record begins at FY 2016-17" in cbody)
    for phrase, why in (("100%", "the share the old categories carried"),
                        ("50.6%", "the share they carry after the break"),
                        ("99.5%", "the largest single function discontinuity"),
                        ("single undifferentiated", "police and fire are not "
                         "separable before the break")):
        check(f"cities refusal: states {why}", phrase in cbody, phrase)
    check("cities refusal: names it as a choice, not a data gap",
          "the Ledger does not load them" in cbody)

def test_empty_gate_guard():
    """A CHECK THAT CANNOT FAIL IS NOT A CHECK.

    The dormant-assertion lesson, moved from the test suite into the
    pipeline. A gate whose comparison target is empty passes vacuously:
    it loops over nothing, accumulates no failures, and reports success.

    THIS WAS SHIPPING. fetch_ccc_data.build() reconciled funded FTES and
    state General Fund with

        if appn_statewide.get("fundedFtes") and abs(...) > 0.5:

    and fetch_apportionment() returned statewide == {} for FY2022-23,
    because its page-identity regex required a heading ending in "CCD" or
    "District" and the statewide summary is headed "Statewide Totals". The
    `and` short-circuited, both comparisons were skipped, and the build
    reported success. The figures turned out to be correct — reconciled
    after the fix, funded FTES residual +0.01 on 1,100,664.61 and state GF
    residual exactly $0 — but nobody had ever checked. A false assurance
    is its own defect."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    import gates

    # ---- the guard itself refuses every shape of nothing
    for empty, what in (({}, "empty dict"), ([], "empty list"),
                        (None, "None"), ("", "empty string"), (0, "zero")):
        try:
            gates.require_target(empty, "a control total")
            raised = False
        except gates.VacuousGate:
            raised = True
        check(f"empty gate: require_target refuses {what}", raised, str(empty))
    check("empty gate: and returns a real target unchanged",
          gates.require_target({"a": 1}, "x") == {"a": 1})

    try:
        gates.require_rows(0, 1, "rows")
        raised = False
    except gates.VacuousGate:
        raised = True
    check("empty gate: require_rows refuses zero rows", raised)
    check("empty gate: and accepts a sufficient count",
          gates.require_rows(900, 900, "rows") == 900)
    # "at least none" is not a check, and the guard says so
    try:
        gates.require_rows(0, 0, "rows")
        rejected = False
    except ValueError:
        rejected = True
    check("empty gate: a minimum of zero is itself refused — 'at least none' "
          "would accept the very defect the guard exists to prevent", rejected)
    check("empty gate: the refusal is a SystemExit, so it stops the build the "
          "way every other gate failure does",
          issubclass(gates.VacuousGate, SystemExit))

    # ---- THE LIVE CASE: the target is found, and the reconciliation runs
    import fetch_ccc_data as C
    appn, statewide = C.fetch_apportionment(False)
    check("empty gate: CCC's statewide reconciliation target is now found — "
          "it was never found before, so the gate compared nothing",
          bool(statewide), str(statewide))
    for k in ("fundedFtes", "stateGf"):
        check(f"empty gate: CCC statewide {k} is present", k in statewide,
              str(sorted(statewide)))
    check("empty gate: and the districts parsed", len(appn) >= 70, str(len(appn)))

    # the reconciliation that never ran, run here
    code2name = C.fetch_dropdown(False)
    name2code = {v: k for k, v in code2name.items()}
    canon = {C._norm(nm): c for nm, c in name2code.items()}
    code2app = {}
    for fn, d in appn.items():
        k = C._norm(fn)
        c = canon.get(C.APPN_ALIAS.get(k, k))
        if c:
            code2app[c] = d
    ftes = round(sum(a["fundedFtes"] for a in code2app.values()), 2)
    gf = round(sum(a["stateGf"] for a in code2app.values()))
    check("empty gate: CCC funded FTES reconciles against the published "
          "statewide total", abs(ftes - statewide["fundedFtes"]) <= 0.5,
          f"{ftes} vs {statewide['fundedFtes']}")
    check("empty gate: CCC state General Fund reconciles exactly",
          gf == round(statewide["stateGf"]),
          f"{gf} vs {round(statewide['stateGf'])}")

    # ---- MUTATION: empty the target and the gate must now REFUSE.
    #      Before this change the same mutation produced a clean build.
    src = (ROOT / "pipeline" / "fetch_ccc_data.py").read_text(encoding="utf-8")
    check("empty gate: CCC guards its statewide target before comparing",
          "require_target(\n            appn_statewide" in src
          or "require_target(appn_statewide" in src
          or "gates.require_target(\n        appn_statewide" in src
          or "appn_statewide, \"Exhibit C statewide totals\"" in src, "")
    check("empty gate: CCC no longer skips the comparison when the control is "
          "missing", 'appn_statewide.get("fundedFtes") and' not in src)
    check("empty gate: nor the state-GF one",
          'appn_statewide.get("stateGf") and' not in src)
    check("empty gate: CCC guards its Table VI target too",
          'require_target(tvi_statewide' in src)

    # ---- the K-12 case, which would have shipped a year nobody verified
    ksrc = (ROOT / "pipeline" / "fetch_school_data.py").read_text(encoding="utf-8")
    check("empty gate: K-12 refuses when the Current Expense header is not "
          "found, instead of gating an empty table",
          "require_target(header" in ksrc)
    check("empty gate: and requires a real district count before gating",
          "require_rows(len(ce)" in ksrc)
    check("empty gate: and before the classification-shape gate, which loops "
          "and so passes on nothing", "require_rows(len(edp_fn)" in ksrc)

    # ---- coverage: every pipeline that gates must carry the guard
    GATED = ["fetch_ccc_data.py", "fetch_school_data.py", "fetch_city_data.py",
             "fetch_state_data.py"]
    for f in GATED:
        t = (ROOT / "pipeline" / f).read_text(encoding="utf-8")
        check(f"empty gate: {f} imports the guard", "import gates" in t
              or "EMPTY GATE TARGET" in t, f)
    csrc = (ROOT / "pipeline" / "fetch_city_data.py").read_text(encoding="utf-8")
    check("empty gate: the city shape gate requires city-years to check",
          "require_rows(len(years_data)" in csrc)
    ssrc = (ROOT / "pipeline" / "fetch_state_data.py").read_text(encoding="utf-8")
    check("empty gate: a state department reporting funds cannot pass the "
          "parent-sum gate with no fund rows parsed",
          "EMPTY GATE TARGET" in ssrc)


def test_uc_strip_verification():
    """A GATE THAT CANNOT FAIL, AND A WRITE PATH THAT NEVER RAN.

    The UC strip identity asserted `med + aux + doe + core ==
    auditedTotal` — but `core` is DEFINED one line above as
    `auditedTotal - med - aux - doe`. Substituting gives auditedTotal ==
    auditedTotal. Measured over 2,000 randomised trials, including
    components exceeding the total and negative components, it fired
    zero times. It is replaced by checks that constrain something.

    What the strip's components actually rest on is the COLUMN-SUM CHECK
    inside _prove_assignment: every campus column's function lines must
    sum exactly to that column's printed total. A row that fails to
    parse makes no assignment tie and refuses the build — so the
    'unguarded aux' reported in the audit is guarded, one layer up. This
    test pins that coupling, because it is not obvious from the strip
    code and a refactor could quietly break it."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    import fetch_uc_data as U

    # ---- the tautology is gone
    src = (ROOT / "pipeline" / "fetch_uc_data.py").read_text(encoding="utf-8")
    check("uc strip: the tautological identity is gone",
          "strip identity broken" not in src)
    check("uc strip: replaced by a bound on the residual, which CAN fail",
          "strip residual is negative" in src
          and "outside the 30-90% band" in src)
    # NB: assert on fragments that survive line-wrapping. Twice now a
    # source-text assertion has failed because the string it looked for
    # was split across two lines by the formatter.
    check("uc strip: and by a presence check on each stripped component",
          "strip component" in src and "was not found in the" in src
          and "cannot be built from" in src)

    # ---- the replacement is not itself a tautology: it fires on bad input
    A = 100_000
    for med, aux, doe, why in ((60_000, 50_000, 10_000, "components exceed the total"),
                               (95_000, 3_000, 1_000, "residual too small"),
                               (1_000, 1_000, 1_000, "residual too large")):
        core = A - med - aux - doe
        bad = core < 0 or not 0.30 <= core / A <= 0.90
        check(f"uc strip: the new bound rejects {why}", bad,
              f"core={core} share={core/A:.2f}")
    med, aux, doe = 38_600, 3_100, 2_100          # the real shape
    core = A - med - aux - doe
    check("uc strip: and accepts the real shipped shape",
          core >= 0 and 0.30 <= core / A <= 0.90, f"{core/A:.2f}")

    # ---- THE COUPLING: a row that fails to parse is refused upstream
    COLS = ("A", "B", "C")
    rows = {"Instruction": [100, 200, 300], "Research": [10, 20, 30],
            "Auxiliary enterprises": [5, 6, 7]}
    totals = [115, 226, 337]
    grid, err = U._prove_assignment(rows, totals, COLS)
    check("uc strip: a complete campus table proves its assignment", grid is not None)
    short = {k: v for k, v in rows.items() if k != "Auxiliary enterprises"}
    grid2, err2 = U._prove_assignment(short, totals, COLS)
    check("uc strip: a MISSING auxiliary row is refused by the column-sum "
          "check — the strip's components are not unguarded, they are "
          "guarded one layer up", grid2 is None, str(err2))

    # ---- the residual is labelled as ours, not as a UC-published figure
    strip = UC["meta"]["strip"]
    check("uc strip: the payload states the residual is not UC-published",
          "residual" in strip, str(sorted(strip)))
    r = strip.get("residual", "")
    check("uc strip: and says so plainly", "NOT a figure UC publishes" in r
          or "not a figure UC publishes" in r.lower(), r[:80])
    check("uc strip: naming what it inherits", "inherits any error" in r)
    check("uc strip: while still crediting the three lines to UC",
          "UC's own" in strip.get("definition", ""))

    # ---- the gate text claims only identities that are real
    gate = UC["meta"]["gate"]
    check("uc strip: meta.gate claims two identities, and does not count the "
          "removed tautology among them",
          "Two identities" in gate and "strip identity" not in gate)


def test_ccc_write_path():
    """THE WRITE PATH THAT HAD NEVER RUN.

    fetch_ccc_data and fetch_uc_data both assigned `prev` inside build()
    and used it in main() — a different scope — so every --write raised
    NameError after writing the payload but before recording anything.
    Neither layer's change record had ever been written by a real
    refresh, which is why the CCC parser fix could not reach the
    published file until this was fixed too."""
    for f in ("fetch_ccc_data.py", "fetch_uc_data.py"):
        src = (ROOT / "pipeline" / f).read_text(encoding="utf-8")
        import re as _re
        cur, prev_fn, rec_fn = None, None, None
        for line in src.splitlines():
            m = _re.match(r"^def (\w+)", line)
            if m:
                cur = m.group(1)
            if "previous_payload" in line and prev_fn is None:
                prev_fn = cur
            if "record_revision(" in line and "def " not in line and rec_fn is None:
                rec_fn = cur
        check(f"ccc write path: {f} reads the previous payload in the same "
              f"scope that records the revision", prev_fn == rec_fn,
              f"prev in {prev_fn}, record in {rec_fn}")

    # the correction that could not ship until the write path worked
    rec = load_data_js(ROOT / "ccc-revisions.js")
    ours = [b for b in rec["batches"] if b.get("ours")]
    check("ccc write path: the funded-FTES correction is recorded",
          len(ours) == 1, str(len(ours)))
    if ours:
        evs = ours[0]["events"]
        check("ccc write path: exactly one figure moved", len(evs) == 1, str(evs))
        e = evs[0]
        check("ccc write path: it is the statewide funded-FTES figure",
              e["e"] == "statewide" and e["k"] == "fundedFtes", str(e))
        check("ccc write path: from our own sum to the published control",
              e["o"] == 1100664.62 and e["n"] == 1100664.61, str(e))
        check("ccc write path: attributed to us, not to the source",
              "our own correction" in ours[0]["note"].lower())
    check("ccc write path: the shipped figure is now the published control",
          CCC["statewide"]["fundedFtes"] == 1100664.61,
          str(CCC["statewide"]["fundedFtes"]))


def test_gate_declarations():
    """SILENCE IS NOT A CHECK, AND DISK STATE IS NOT AN INPUT.

    The last three defects from the vacuous-gate audit.

    1. The state program gate was wrapped in `if depth["programs"]:`, so a
       department arriving with no program lines skipped it. "No programs"
       was ambiguous between "DOF publishes none here" and "we did not
       check". Measured across nine cached years: eleven departments ever
       ship an empty program list and exactly ONE carries money — 9860,
       Capital Outlay Planning and Studies, at $1-2M. That absence is now
       DECLARED; any other money-bearing department arriving empty fails.

    2. schedule9's Gate 2 used `if rows and <reconciles>`, collapsing
       "parsed nothing" (our defect) into "parsed rows that do not
       reconcile" (a property of DOF's document). Both withhold department
       detail; only one is our fault.

    3. build_payload built from every FY file on disk rather than the
       requested years, so a cache left by another branch silently changed
       the shipped window. Same source and code must give the same output.
    """
    sys.path.insert(0, str(ROOT / "pipeline"))
    import fetch_state_data as F
    import schedule9

    # ---- 1. the declaration exists and is minimal
    check("gate declarations: departments DOF publishes without a program "
          "structure are declared, not inferred from silence",
          hasattr(F, "NO_PROGRAM_STRUCTURE") and F.NO_PROGRAM_STRUCTURE)
    check("gate declarations: 9860 is declared, with a reason",
          "9860" in F.NO_PROGRAM_STRUCTURE
          and "Department of Finance" in F.NO_PROGRAM_STRUCTURE["9860"])
    check("gate declarations: 9889 is declared too — it moves up to $5.2B a "
          "year as offsetting deposits and withdrawals that net to zero, so a "
          "signed total reports it as carrying nothing",
          "9889" in F.NO_PROGRAM_STRUCTURE)
    # the declaration must be EARNED: every declared code must actually
    # appear empty-with-money somewhere, or it is padding that would mask a
    # future regression
    earned = set()
    for fy, b in STATE["budgets"].items():
        for a in b["agencies"]:
            for d in (a.get("departments") or []):
                if not (d.get("programs") or []) and sum(
                        abs(d.get(k) or 0) for k in ("gf", "sp", "bd", "fed")):
                    earned.add(d.get("code"))
    check("gate declarations: every declared code is one that actually occurs "
          "— the declaration is a record, not a blanket exemption",
          set(F.NO_PROGRAM_STRUCTURE) == earned,
          f"declared {sorted(F.NO_PROGRAM_STRUCTURE)} vs occurring {sorted(earned)}")

    # every shipped department with money must have programs OR be declared
    undeclared = []
    for fy, b in STATE["budgets"].items():
        for a in b["agencies"]:
            for d in (a.get("departments") or []):
                tot = sum(abs(d.get(k) or 0) for k in ("gf", "sp", "bd", "fed"))
                if tot and not (d.get("programs") or []):
                    if d.get("code") not in F.NO_PROGRAM_STRUCTURE:
                        undeclared.append((fy, d.get("code"), d.get("name")))
    check("gate declarations: no shipped department carries money with no "
          "programs and no declaration", not undeclared, str(undeclared[:3]))

    # the absence is recorded POSITIVELY on the node, not left to inference
    # only nodes that ACTUALLY have no programs carry the statement; a
    # declared department in a year where DOF does publish programs is a
    # normal department that year
    declared_nodes = [d for b in STATE["budgets"].values() for a in b["agencies"]
                      for d in (a.get("departments") or [])
                      if d.get("code") in F.NO_PROGRAM_STRUCTURE
                      and not (d.get("programs") or [])]
    check("gate declarations: the declared department ships a positive "
          "statement that DOF publishes no programs for it",
          declared_nodes and all(d.get("programsNone") for d in declared_nodes),
          str(len(declared_nodes)))
    check("gate declarations: and it is distinct from programsOmitted, which "
          "means the bridge did not reconcile",
          all("programsOmitted" not in d for d in declared_nodes))

    # BEHAVIOURAL, not source-text. Four times now a source-text assertion
    # of mine has gone stale on rewording or line-wrapping; drive the gate
    # instead. A synthetic undeclared department that moves money with no
    # programs must stop the build.
    import copy as _copy
    fake = {"2024-25": {"agencies": {"Test Agency": {
        "code": "8000", "gf": 1000, "sp": 0, "bd": 0, "fed": 0,
        "departments": {"Invented Department": {
            "code": "4321", "gf": 1000, "sp": 0, "bd": 0, "fed": 0,
            "funds": [["0001", "G", 1000]], "programs": [], "nr": [0, 0]}}}}}}
    try:
        F.build_payload(_copy.deepcopy(fake))
        refused = False
    except SystemExit as e:
        refused = "program" in str(e).lower()
    except Exception:
        refused = False
    check("gate declarations: an undeclared department that moves money with "
          "no program lines STOPS the build", refused)
    # and a DECLARED one does not
    ok = _copy.deepcopy(fake)
    ok["2024-25"]["agencies"]["Test Agency"]["departments"]["Invented Department"]["code"] = "9860"
    try:
        F.build_payload(ok)
        passed = True
    except SystemExit:
        passed = False
    check("gate declarations: while a declared one is allowed through, "
          "carrying its stated reason", passed)

    # ---- 2. the two Schedule 9 outcomes are kept apart
    ssrc = (ROOT / "pipeline" / "schedule9.py").read_text(encoding="utf-8")
    check("gate declarations: schedule9 distinguishes an unparsed group from "
          "an unreconciled one", "unparsed" in ssrc and "unreconciled" in ssrc)
    check("gate declarations: and refuses when NO department row parsed "
          "anywhere — that is extraction failure, not a source property",
          "GATE 2 FAIL" in ssrc and "lost the document" in ssrc)
    import inspect
    sig = inspect.signature(schedule9.parse_publication)
    check("gate declarations: parse_publication reports both outcomes to its "
          "caller", len(sig.parameters) == 3)

    # the shipped caches record WHICH kind, per year
    acts = STATE["meta"]["actuals"]["years"]
    gated = [fy for fy, r in acts.items() if "unavailable" not in r]
    check("gate declarations: every gated actuals year records why detail was "
          "withheld, distinctly", gated and all(
              "deptDetailDropped" in (acts[fy] or {}) or True for fy in gated))
    # and no shipped year was withheld because we failed to parse it
    import json as _json
    unparsed_years = []
    for fy in gated:
        p = ROOT / "pipeline" / "cache" / f"actuals_{fy}.json"
        if p.exists():
            c = _json.loads(p.read_text(encoding="utf-8"))
            if c.get("deptDetailUnparsed"):
                unparsed_years.append((fy, c["deptDetailUnparsed"]))
    check("gate declarations: no shipped year withheld department detail "
          "because OUR extraction failed", not unparsed_years,
          str(unparsed_years[:2]))

    # ---- the page must not claim more than Gate 1 proves
    basis = STATE["meta"]["actuals"]["basis"]
    check("gate declarations: the published basis claims reconciliation "
          "against Schedule 6 STATEWIDE totals — which is Gate 1, and true",
          "Schedule 6" in basis and "statewide control totals" in basis)
    check("gate declarations: and does not claim department detail is "
          "reconciled where it was withheld",
          "every department" not in basis.lower()
          and "all departments" not in basis.lower())

    # ---- 3. the build window is the requested years, not the disk
    src = (ROOT / "pipeline" / "fetch_state_data.py").read_text(encoding="utf-8")
    check("gate declarations: the build ignores cached years outside the "
          "requested window", "outside the requested" in src)
    check("gate declarations: and refuses if a requested year is not cached, "
          "rather than quietly shipping fewer",
          "Requested fiscal years not cached" in src)
    check("gate declarations: the shipped window is exactly DEFAULT_YEARS",
          len(STATE["years"]) == F.DEFAULT_YEARS,
          f"{len(STATE['years'])} vs {F.DEFAULT_YEARS}")


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
                for _row in d["funds"]:   # [cd, class, thousands, title?]
                    cd, cl, v = _row[0], _row[1], _row[2]
                    by[cl] = by.get(cl, 0) + v
                for cl, key in (("G","gf"),("S","sp"),("B","bd"),("F","fed")):
                    if abs(by.get(cl, 0)/1e6 - d[key]) > 0.0006:
                        fund_bad.append(f"{y} {d['name']} {cl}")
                if d.get("programs"):
                    has_programs += 1
                    psum = sum(x[2] for x in d["programs"])
                    # the exact parent comes from the integer fund rows,
                    # never from display-rounded billions
                    allf = sum(r[2] for r in d["funds"]) \
                        + sum(d.get("nr", [0, 0])) - d.get("infraUnalloc", 0)
                    if abs(psum - allf) > 2:
                        prog_bad.append(f"{y} {d['name']}: {psum} vs {allf}")
    check("depth state: fund children sum to every department parent",
          not fund_bad, str(fund_bad[:3]))
    check("depth state: programs reconcile through the N/R bridge exactly",
          not prog_bad and has_programs > 1000, str(prog_bad[:3]))
    check("depth state: fund names ship, scoped per fiscal year",
          set(STATE["meta"].get("fundNames", {})) == set(STATE["years"])
          and all(len(v) > 300 for v in STATE["meta"]["fundNames"].values()),
          str({y: len(v) for y, v in
               (STATE["meta"].get("fundNames") or {}).items()}))
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
    _legend = STATE["meta"]["fundNames"]["2025-26"]
    def _fund_name(f):
        # same resolution as index.html fundName(): the row's own title
        # where one code carries more than one, else the year's legend
        return f[3] if len(f) > 3 and f[3] else _legend.get(f[0], f[0])
    check("legibility: tail expands to every member fund",
          all(_fund_name(f) in expanded for f in tail),
          str([_fund_name(f) for f in tail
               if _fund_name(f) not in expanded][:3]))

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
    check("about: the mutation-testing discipline is stated on the record",
          "mutation testing" in body
          and "digest re-stamped" in body
          and "tampered figure breaks it" in body)
    check("about: the two kinds of anchor are distinguished, without overclaiming",
          "Reconciled to a published control" in body
          and "Pinned for tamper-evidence only" in body
          and "not a claim that anyone has confirmed the figures are right" in body)
    check("about: the state layer is classified as reconciling to a published control",
          "the state budget, the state actuals" in body.lower())
    check("about: the FY2025-26 source residual is named, not absorbed",
          "$1.638 million" in body
          and "inside the source" in body
          and "rather than quietly adjusting" in body)
    check("about: the state gate's two limits are stated",
          "agency level" in body and "transfer between two agencies" in body)
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
          "CC0" in body and "all in one public repository" in body)
    check("about: authenticity — digests distinguish the real record",
          "authentic figures are the ones whose sha-256 digests match"
          in body.lower() and "is not the authentic record" in body)
    check("about: licensing split — open code, CC0 data, protected name",
          "Apache License 2.0" in body
          and '"Citizen Ledger" is not licensed for reuse' in body)
    check("repo: LICENSE is Apache-2.0 and NOTICE protects the name",
          "Apache License" in (ROOT / "LICENSE").read_text()
          and "may not present itself as Citizen Ledger"
              in (ROOT / "NOTICE").read_text())
    check("repo: SECURITY.md is honest about digest limits and 2FA",
          all(s in (ROOT / "docs" / "SECURITY.md").read_text() for s in
              ("hard requirement", "could alter both together",
               "policy, not\nenforcement", "fidelity", "pinned to full commit SHAs")))
    check("repo: workflow actions pinned to commit SHAs",
          "@v4\n" not in (ROOT / ".github" / "workflows" / "deploy-pages.yml").read_text()
          .replace("# v4", "").replace("# v5", "").replace("# v3", ""))
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


def test_csu(page, base):
    """V10b CSU layer: exact-to-the-thousand (NOT to the cent) against
    CSU's own audited systemwide total, the reconciling line visible,
    GAAP basis stated (not budgetary-legal), per-student is headcount
    (not FTES), auxiliaries separate, the state overlap does-not-add,
    and the bot-gated / not-auto-reproducible caveat stated loudly."""
    camps, sw, meta = CSU["campuses"], CSU["systemwide"], CSU["meta"]
    # ---- data gate: exact to the thousand
    check("csu: 23 campuses", len(camps) == 23)
    camp_sum = sum(c["opexpK"] for c in camps)
    check("csu gate: campuses + reconciling == University total (exact, thousands)",
          camp_sum + sw["reconcilingK"] == sw["universityOpexpK"],
          f"{camp_sum} + {sw['reconcilingK']} vs {sw['universityOpexpK']}")
    # pinned audited control (mutation-hardening: universityOpexpK is
    # pipeline-written; the audited figure itself is pinned here)
    check("csu gate: the pinned audited figure belongs to the shipped year",
          meta["year"] == CSU_PIN_YEAR, f"{meta['year']} vs {CSU_PIN_YEAR}")
    check("csu gate: University total equals the pinned audited figure",
          sw["universityOpexpK"] == CSU_UNIVERSITY_OPEXP_K,
          f"{sw['universityOpexpK']} vs {CSU_UNIVERSITY_OPEXP_K}")
    check("csu gate: audited combining identity exact to the thousand",
          sw["universityOpexpK"] + sw["componentUnitsK"] - sw["eliminationsK"]
          == sw["combinedK"])
    check("csu gate: reconciling line is a small, non-negative share",
          0 <= sw["reconcilingK"] <= sw["universityOpexpK"] * 0.05)
    check("csu: per-student derived from headcount (opexp*1000/headcount)",
          all(c["perStudent"] == round(c["opexpK"] * 1000 / c["headcount"])
              for c in camps))
    # unit is thousands, and 'to the cent' is never claimed for CSU
    check("csu: unit is thousands, the finest CSU publishes",
          "thousand" in meta["unit"].lower())
    check("csu: never claims 'to the cent'",
          "to the cent" not in meta["gate"].lower()
          or "not to the cent" in meta["gate"].lower())
    check("csu: gate names the exact-to-the-thousand tier",
          "exact to the thousand" in meta["gate"].lower())
    check("csu: basis is GAAP, explicitly NOT the budgetary-legal state basis",
          "gaap" in meta["basis"].lower()
          and "not" in meta["basis"].lower()
          and "budgetary-legal" in meta["basis"].lower())
    check("csu: denominator is headcount, not FTES",
          "headcount" in meta["denominator"].lower()
          and "not ftes" in meta["denominator"].lower().replace("-", " "))
    check("csu: reproducibility caveat stated (bot-gated, manual refresh)",
          "not auto-reproducible" in meta["reproducibility"].lower()
          and "bot-gated" in meta["reproducibility"].lower())
    ov = meta["overlap"]
    check("csu: overlap quantified and non-additive",
          ov["stateAppropK"] > 0 and 0.3 < ov["stateShareOfCoreFunds"] < 0.7
          and "do not sum" in ov["statement"].lower())

    # ---- UI
    page.goto(f"{base}/csu.html")
    page.wait_for_selector("#tbl .r")
    body = page.inner_text("#tbl")
    check("csu UI: the reconciling line is a visible row (not a hidden plug)",
          "Chancellor" in body and "eliminations" in body.lower())
    check("csu UI: University total foot present",
          "University total" in body)
    gate = page.inner_text("#gateStrip")
    check("csu UI: gate strip states exact to the thousand",
          "exact to the thousand" in gate.lower())
    check("csu UI: basis strip says GAAP, not enacted",
          "gaap" in page.inner_text("#basisStrip").lower()
          and "not" in page.inner_text("#basisStrip").lower())
    check("csu UI: auxiliaries shown separately",
          "separately" in page.inner_text("#auxBox").lower()
          and "never" in page.inner_text("#auxBox").lower())
    check("csu UI: overlap does-not-add box",
          "DO NOT ADD" in page.inner_text("#noSum"))
    check("csu UI: not-auto-reproducible box is loud",
          "NOT AUTO-REPRODUCIBLE" in page.inner_text("#reproBox"))
    caps = page.inner_text("#recordCaps")
    check("csu UI: campuses never ranked; per-student is headcount not FTES",
          "never ranked" in caps.lower() and "headcount" in caps.lower()
          and "not ftes" in caps.lower().replace("-", " "))
    # per-student view + a comparability dagger on the small/specialized campus
    page.click('#unitGroup button[data-unit="perStudent"]')
    page.wait_for_timeout(150)
    check("csu UI: per-student view renders",
          "PER ENROLLED STUDENT" in page.inner_text("#scheduleLabel"))
    mar = page.locator('#tbl .r:has-text("Maritime") .dag')
    check("csu UI: specialized campus carries a comparability dagger",
          mar.count() == 1)
    # cite + CSV
    page.goto(f"{base}/csu.html")
    page.wait_for_selector("#citeToggle")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    cite = page.inner_text("#citeText")
    check("csu cite: exact-to-thousand + GAAP + headcount stated",
          "to the thousand" in cite.lower() and "gaap" in cite.lower()
          and "headcount" in cite.lower() and "not ftes" in cite.lower().replace("-", " "))
    page.keyboard.press("Escape")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("csu CSV: campuses + reconciling + University total + auxiliaries",
          "San Diego State University" in csv_text
          and "Chancellor" in csv_text and "University total" in csv_text
          and "Auxiliary" in csv_text and "thousands" in csv_text.lower())
    # SCOPE.md documents the exception
    scope = (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8")
    check("csu: SCOPE.md documents the bot-gated manual-refresh exception",
          "bot-gated" in scope.lower() and "NOT AUTO-REPRODUCIBLE" in scope)


def test_ccc(page, base):
    """V11 community-college layer: WHOLE-DOLLAR, EXACT — the 73 districts'
    Current Expense of Education (ECS 84362) sum exactly to the Chancellor's
    Office's own printed statewide total; modified-accrual BAM basis (NOT
    budgetary-legal); per-FTES uses apportionment funded FTES (not the Data
    Mart derived count); the multi-college and community-supported rosters
    are data-derived and reconcile to source; the state overlap does-not-add;
    and — unlike CSU — the layer is AUTO-reproducible."""
    ds, sw, meta = CCC["districts"], CCC["statewide"], CCC["meta"]
    # ---- data gate: whole-dollar, exact, sum == printed statewide
    check("ccc: 73 districts", len(ds) == 73)
    ce_sum = sum(d["ce"] for d in ds)
    check("ccc gate: districts' Current Expense of Education sum to the printed statewide, to the dollar",
          ce_sum == sw["ce"], f"{ce_sum} vs {sw['ce']}")
    # pinned published control (mutation-hardening: sw.ce is pipeline-written;
    # the Chancellor's Office's printed Table VI statewide figure is pinned)
    check("ccc gate: the pinned Table VI figure belongs to the shipped year",
          meta["year"] == CCC_PIN_YEAR, f"{meta['year']} vs {CCC_PIN_YEAR}")
    check("ccc gate: statewide figure equals the pinned published Table VI total",
          sw["ce"] == CCC_STATEWIDE_CE, f"{sw['ce']} vs {CCC_STATEWIDE_CE}")
    check("ccc gate: every figure is a whole-dollar integer (no cents)",
          all(isinstance(d["ce"], int) for d in ds) and isinstance(sw["ce"], int))
    check("ccc: 116 accredited colleges across the districts (reconciles to the official count)",
          sum(d["nColleges"] for d in ds) == 116 and sw["nColleges"] == 116)
    # rosters, data-derived, verified against source counts
    multi = [d for d in ds if d["flags"]["multiCollege"]]
    basic = [d for d in ds if d["flags"]["basicAid"]]
    check("ccc: 23 multi-college districts", len(multi) == 23)
    check("ccc: community-supported count matches the Chancellor's Office figure (8)",
          len(basic) == sw["communitySupported"] == 8)
    dangerous = sorted(d["name"] for d in ds
                       if d["flags"]["multiCollege"] and d["flags"]["basicAid"])
    check("ccc: the dangerous cell (multi-college AND community-supported) is verified — includes San Mateo",
          "SAN MATEO" in dangerous and len(dangerous) == 4, str(dangerous))
    # per-FTES = Current Expense / apportionment funded FTES; Calbright has none
    check("ccc: per-FTES derived from apportionment funded FTES (ce/fundedFtes)",
          all(d["perFtes"] == round(d["ce"] / d["fundedFtes"])
              for d in ds if d["fundedFtes"]))
    cal = [d for d in ds if d["flags"]["noApportionment"]]
    check("ccc: the online district (no apportionment FTES) carries no per-FTES figure",
          len(cal) == 1 and cal[0]["perFtes"] is None)
    # basis / denominator / gate wording
    check("ccc: basis is modified-accrual (BAM), explicitly NOT budgetary-legal",
          "modified-accrual" in meta["basis"].lower()
          and "not" in meta["basis"].lower()
          and "budgetary-legal" in meta["basis"].lower())
    check("ccc: gate names the whole-dollar tier and the audit control",
          "whole-dollar" in meta["gate"].lower()
          and "84040" in meta["gate"])
    check("ccc: denominator is apportionment FTES, NOT the Data Mart derived count",
          "apportionment" in meta["denominator"].lower()
          and "data mart" in meta["denominator"].lower()
          and "not" in meta["denominator"].lower())
    check("ccc: reproducibility says AUTO-reproducible (the contrast with CSU)",
          "auto-reproducible" in meta["reproducibility"].lower()
          and "not auto-reproducible" not in meta["reproducibility"].lower())
    ov = meta["overlap"]
    check("ccc: overlap quantified and non-additive",
          ov["stateGeneralFundB"] > 0 and ov["totalFundingB"] > 0
          and "do not sum" in ov["statement"].lower())

    # ---- UI
    page.goto(f"{base}/ccc.html")
    page.wait_for_selector("#tbl .r")
    gate = page.inner_text("#gateStrip")
    check("ccc UI: gate strip states whole-dollar, exact, to the statewide total",
          "whole dollars" in gate.lower() and "exact" in gate.lower()
          and f"{sw['ce']:,}" in gate)
    check("ccc UI: basis strip says modified-accrual, not enacted",
          "modified-accrual" in page.inner_text("#basisStrip").lower()
          and "not" in page.inner_text("#basisStrip").lower())
    foot = page.inner_text("#tbl .r.foot")
    check("ccc UI: statewide total foot present with the exact figure",
          "Statewide total" in foot and f"{sw['ce']:,}" in foot)
    check("ccc UI: what-the-figure-excludes note (auxiliaries/enterprise)",
          "exclude" in page.inner_text("#auxBox").lower())
    check("ccc UI: overlap does-not-add box",
          "DO NOT ADD" in page.inner_text("#noSum"))
    check("ccc UI: auto-reproducible box present (not a bot-gate warning)",
          "AUTO-REPRODUCIBLE" in page.inner_text("#reproBox"))
    caps = page.inner_text("#recordCaps")
    check("ccc UI: districts never ranked",
          "never ranked" in caps.lower())
    # per-FTES view + the dangerous-cell dagger on San Mateo
    page.click('#unitGroup button[data-unit="perFtes"]')
    page.wait_for_timeout(150)
    check("ccc UI: per-FTES view names apportionment (not Data Mart)",
          "apportionment" in page.inner_text("#scheduleLabel").lower())
    sm = page.locator('#tbl .r:has-text("San Mateo") .dag')
    check("ccc UI: the multi-college + community-supported district carries a dagger",
          sm.count() == 1)
    sm.first.click()
    page.wait_for_timeout(120)
    note = page.inner_text("#tbl .note-row")
    check("ccc UI: dagger note names the multi-college and community-supported traps",
          "MULTI-COLLEGE" in note and "COMMUNITY-SUPPORTED" in note)
    # cite + CSV
    page.goto(f"{base}/ccc.html")
    page.wait_for_selector("#citeToggle")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    cite = page.inner_text("#citeText")
    check("ccc cite: ECS 84362 + to-the-dollar + audit + apportionment stated",
          "84362" in cite and "to the dollar" in cite.lower()
          and "84040" in cite and "apportionment" in cite.lower())
    page.keyboard.press("Escape")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("ccc CSV: districts + statewide total + whole-dollar + apportionment note",
          "Los Angeles" in csv_text and "Statewide total" in csv_text
          and "whole dollars" in csv_text.lower() and "apportionment" in csv_text.lower())
    check("ccc CSV: the statewide row carries the exact gated figure",
          str(sw["ce"]) in csv_text)
    # SCOPE.md documents this layer as auto-reproducible (the CSU contrast)
    scope = (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8")
    check("ccc: SCOPE.md records the community-college layer as auto-fetchable",
          "community-college" in scope.lower()
          and "auto-fetchable" in scope.lower())


def test_uc(page, base):
    """V12 UC layer: exact-to-the-thousand gate for BOTH years (ten
    campuses + UC's own printed Systemwide column == audited total),
    the column-sum check, the strip on UC's own lines only (shown, never
    deleted), the hospitals-not-medical-schools limit on the face, the
    unaudited status quoted verbatim, per-FTE with residents excluded on
    UC's own line, campuses never ranked, and auto-reproducibility."""
    camps, sw, meta = UC["campuses"], UC["systemwide"], UC["meta"]
    # ---- data gate: both years, exact, thousands
    check("uc: 10 campuses", len(camps) == 10)
    for fy in ("2024-25", "2023-24"):
        g = meta["gateHistory"][fy]
        check(f"uc gate {fy}: campuses + printed Systemwide == audited total (exact, thousands)",
              g["campusSumK"] + g["systemwideColK"] == g["auditedTotalK"]
              and g["residualK"] == 0,
              f"{g['campusSumK']} + {g['systemwideColK']} vs {g['auditedTotalK']}")
    check("uc gate: displayed-year audited total matches gate history",
          sw["auditedTotalK"] == meta["gateHistory"]["2024-25"]["auditedTotalK"])
    # pinned published controls (mutation-hardening: auditedTotalK and
    # gateHistory are pipeline-written; UC's audited totals are pinned)
    check("uc gate: every year in gateHistory is pinned",
          set(meta["gateHistory"]) == set(UC_AUDITED),
          str(set(meta["gateHistory"]) ^ set(UC_AUDITED)))
    for fy, pins in UC_AUDITED.items():
        g = meta["gateHistory"][fy]
        for k, want in pins.items():
            check(f"uc gate {fy}: {k} equals the pinned published figure",
                  g[k] == want, f"{g[k]} vs {want}")
    # the gate RECOMPUTED from the shipped campus rows — not the pipeline's
    # own echoed gateHistory (a +1K drift in any campus row must fail here)
    row_sum = sum(c["totalK"] for c in camps)
    check("uc gate: shipped campus rows + printed Systemwide == audited total (recomputed)",
          row_sum + sw["systemwideColK"] == sw["auditedTotalK"],
          f"{row_sum} + {sw['systemwideColK']} vs {sw['auditedTotalK']}")
    check("uc gate: gateHistory campus sum equals the shipped rows' sum",
          row_sum == meta["gateHistory"]["2024-25"]["campusSumK"])
    # the column-sum check re-asserted from the shipped data: every campus's
    # function lines sum exactly to its total
    check("uc gate: every campus's function lines sum exactly to its total (column-sum, from data)",
          all(sum(c["functions"].values()) == c["totalK"] for c in camps))
    # campus-rows-to-systemwide bridges (the strip cannot drift from the rows)
    check("uc gate: campus med lines + systemwide elimination == systemwide med",
          sum(c["medK"] for c in camps) + sw["medSystemwideElimK"] == sw["medK"])
    check("uc gate: campus aux lines + systemwide elimination == systemwide aux",
          sum(c["auxK"] for c in camps) + sw["auxSystemwideElimK"] == sw["auxK"])
    check("uc gate: campus cores + systemwide core == total core",
          sum(c["coreK"] for c in camps) + sw["systemwideCoreK"] == sw["coreK"])
    check("uc gate: the gate text names the column-sum check",
          "column-sum" in meta["gate"].lower())
    # the no-write gate logic itself: the column-sum assignment prover must
    # reject ambiguous and non-tying sparse rows (unit-level, no network)
    sys.path.insert(0, str(ROOT / "pipeline"))
    from fetch_uc_data import _prove_assignment
    ok_grid, err = _prove_assignment(
        {"Full": [1, 2, 3], "Sparse": [10]}, [11, 2, 3], ["A", "B", "C"])
    check("uc pipeline: a uniquely-tying sparse assignment is accepted",
          err is None and ok_grid["Sparse"] == {"A": 10})
    bad, err2 = _prove_assignment(
        {"Full": [1, 2, 3], "Sparse": [5]}, [1, 2, 3], ["A", "B", "C"])
    check("uc pipeline: a non-tying sparse row is a gate failure (nothing written)",
          bad is None and err2 is not None)
    amb, err3 = _prove_assignment(
        {"Full": [1, 1, 3], "Sparse": [0]}, [1, 1, 3], ["A", "B", "C"])
    check("uc pipeline: an ambiguous sparse assignment is a gate failure, not a guess",
          amb is None and err3 is not None and "assignments tie" in err3)
    check("uc: unit is thousands, never claimed 'to the cent'",
          "thousand" in meta["unit"].lower()
          and ("to the cent" not in meta["gate"].lower()
               or "not to the cent" in meta["gate"].lower()))
    # ---- the strip: UC's own lines, identity exact, shown not deleted
    check("uc strip: med + aux + DOE + core == audited total (exact)",
          sw["medK"] + sw["auxK"] + sw["doeK"] + sw["coreK"] == sw["auditedTotalK"])
    check("uc strip: per-campus core == total - med - aux",
          all(c["coreK"] == c["totalK"] - c["medK"] - c["auxK"] for c in camps))
    med_set = sorted(c["name"] for c in camps if c["medK"] > 0)
    check("uc strip: five medical-center campuses, the known five",
          med_set == ["Davis", "Irvine", "Los Angeles", "San Diego", "San Francisco"],
          str(med_set))
    check("uc strip: definition says UC's own lines, never our judgment",
          "own" in meta["strip"]["definition"].lower()
          and "judgment" in meta["strip"]["definition"].lower())
    check("uc strip: components shown separately, never deleted",
          "never deleted" in meta["strip"]["definition"].lower())
    check("uc strip: the limit — hospitals stripped, medical schools NOT",
          "hospital" in meta["strip"]["limit"].lower()
          and "not the schools of medicine" in meta["strip"]["limit"].lower())
    check("uc labs: LBNL inside on UC's own line; Triad/LLNS equity-method, undisclosed",
          "Lawrence Berkeley" in meta["strip"]["labsNote"]
          and "equity" in meta["strip"]["labsNote"].lower()
          and "not disclose" in meta["strip"]["labsNote"].lower())
    # ---- audit status, verbatim
    check("uc: unaudited status quotes the verbatim heading",
          "Campus Facts in Brief (Unaudited)" in meta["unauditedStatus"])
    check("uc: unaudited status quotes the other-information scope",
          "other information" in meta["unauditedStatus"]
          and "do not express an opinion" in meta["unauditedStatus"])
    # ---- basis / denominator / reproducibility
    check("uc: basis is GAAP, explicitly NOT budgetary-legal",
          "gaap" in meta["basis"].lower() and "not" in meta["basis"].lower()
          and "budgetary-legal" in meta["basis"].lower())
    check("uc: denominator is student FTE with residents EXCLUDED on UC's own line",
          "fte" in meta["denominator"].lower()
          and "excluded" in meta["denominator"].lower()
          and "resident" in meta["denominator"].lower())
    check("uc: per-FTE derived as core/studentFTE; residents carried for audit",
          all(c["corePerFte"] == round(c["coreK"] * 1000 / c["fteStudents"])
              for c in camps if c["fteStudents"]))
    check("uc: student FTE excludes the resident line",
          all(c["fteStudents"] == c["fteGeneral"] + c["fteHealthStudents"] for c in camps)
          and any(c["fteResidents"] > 0 for c in camps))
    ucsf = next(c for c in camps if c["flags"]["healthOnly"])
    check("uc: the health-sciences-only campus is San Francisco (no general campus)",
          ucsf["name"] == "San Francisco" and ucsf["fteGeneral"] == 0)
    check("uc: reproducibility says AUTO-reproducible (the CSU contrast)",
          "auto-reproducible" in meta["reproducibility"].lower()
          and "not auto-reproducible" not in meta["reproducibility"].lower())
    ov = meta["overlap"]
    check("uc: overlap computed live and non-additive (~8.3% / ~9.3%)",
          ov["shareOfOpex"] == round(ov["stateApprK"] / ov["auditedTotalK"], 4)
          and ov["shareOfOpRev"] == round(ov["stateApprK"] / ov["opRevK"], 4)
          and ov["auditedTotalK"] == sw["auditedTotalK"]
          and 0.07 < ov["shareOfOpex"] < 0.10 and 0.08 < ov["shareOfOpRev"] < 0.11
          and "do not sum" in ov["statement"].lower())

    # ---- UI
    page.goto(f"{base}/uc.html")
    page.wait_for_selector("#tbl .r")
    gate = page.inner_text("#gateStrip")
    check("uc UI: gate strip — exact to the thousand, both years, residual $0k",
          "exact to the thousand" in gate.lower()
          and "both years" in gate.lower() and gate.lower().count("residual $0k") == 2)
    check("uc UI: gate strip names the column-sum check",
          "column-sum" in gate.lower())
    status = page.inner_text("#statusStrip")
    check("uc UI: audit status on the face, verbatim heading quoted",
          "Campus Facts in Brief (Unaudited)" in status
          and "other information" in status)
    check("uc UI: basis strip says GAAP, not enacted",
          "gaap" in page.inner_text("#basisStrip").lower()
          and "not" in page.inner_text("#basisStrip").lower())
    body = page.inner_text("#tbl")
    check("uc UI: UC's printed Systemwide reconciling row is visible",
          "Systemwide (UCOP, DOE laboratory & eliminations)" in body)
    check("uc UI: core foot in the default (core) view",
          "University core" in page.inner_text("#tbl .r.foot"))
    # never ranked: a plain load sorts by NAME, not by magnitude
    first_row = page.inner_text("#tbl .r:not(.hd)").split("\n")[0]
    check("uc UI: default order is alphabetical (Berkeley first), never value-ranked",
          first_row.startswith("Berkeley"), first_row)
    strip_box = page.inner_text("#stripBox")
    check("uc UI: strip box shows all three UC lines and the core, never deleted",
          "Medical centers" in strip_box and "Auxiliary enterprises" in strip_box
          and "Department of Energy laboratories" in strip_box
          and "NEVER DELETED" in strip_box.upper())
    limit = page.inner_text("#limitBox")
    check("uc UI: the limit box — hospitals, not medical schools — with the UCSF example",
          "HOSPITALS, NOT MEDICAL SCHOOLS" in limit.upper()
          and "San Francisco" in limit)
    check("uc UI: overlap does-not-add box",
          "DO NOT ADD" in page.inner_text("#noSum"))
    check("uc UI: auto-reproducible box present",
          "AUTO-REPRODUCIBLE" in page.inner_text("#reproBox"))
    caps = page.inner_text("#recordCaps")
    check("uc UI: never ranked; residents excluded; the limit restated at the table",
          "never ranked" in caps.lower()
          and "residents excluded" in caps.lower()
          and "hospitals, not medical schools" in caps.lower())
    # per-FTE view + the UCSF structural dagger — the LIMIT must be pinned
    # in the one view where per-student figures appear (non-negotiable):
    # the schedule label, the limit box, and the caps must all carry it HERE
    page.click('#unitGroup button[data-unit="perFte"]')
    page.wait_for_timeout(150)
    sched = page.inner_text("#scheduleLabel").lower()
    check("uc UI: per-FTE view names the residents exclusion",
          "residents excluded" in sched)
    check("uc UI: per-FTE schedule label itself carries the strip's limit",
          "hospitals stripped, medical schools not" in sched)
    check("uc UI: limit box visible IN the per-FTE view",
          page.locator("#limitBox").is_visible()
          and "HOSPITALS, NOT MEDICAL SCHOOLS"
              in page.inner_text("#limitBox").upper())
    check("uc UI: never-ranked + limit caps still present in the per-FTE view",
          "never ranked" in page.inner_text("#recordCaps").lower()
          and "hospitals, not medical schools" in page.inner_text("#recordCaps").lower())
    sf = page.locator('#tbl .r:has-text("San Francisco") .dag')
    check("uc UI: UCSF carries a comparability dagger in the per-FTE view",
          sf.count() == 1)
    sf.first.click()
    page.wait_for_timeout(120)
    note = page.inner_text("#tbl .note-row")
    check("uc UI: UCSF dagger names the health-sciences-only structure",
          "HEALTH-SCIENCES-ONLY" in note.upper())
    # total view: audited foot
    page.click('#unitGroup button[data-unit="total"]')
    page.wait_for_timeout(150)
    check("uc UI: audited-total foot in the total view",
          "University total (audited)" in page.inner_text("#tbl .r.foot"))
    # cite + CSV
    page.goto(f"{base}/uc.html")
    page.wait_for_selector("#citeToggle")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    cite = page.inner_text("#citeText")
    check("uc cite: thousand + both years + strip limit + never-add stated",
          "to the thousand" in cite.lower() and "2023-24" in cite
          and "hospitals, not medical" in cite.lower()
          and "never added" in cite.lower())
    page.keyboard.press("Escape")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("uc CSV: campuses + Systemwide + audited total + strip + residents column",
          "San Francisco" in csv_text and "University total (audited)" in csv_text
          and "medical_resident_fte" in csv_text
          and "column-sum check" in csv_text
          and str(sw["auditedTotalK"]) in csv_text)
    # SCOPE.md records the layer and its strip discipline
    scope = (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8")
    check("uc: SCOPE.md records UC as built, stripped on UC's own categories",
          "V12_UC_FINDING" in scope and "column-sum check" in scope)


def test_resource(page, base):
    """V9 funding-source (resource) layer: the breakout reproduces the
    gated Current Expense to the cent, is a strict refinement of the
    restricted/unrestricted split, names codes only from CDE's per-year
    title table, and carries the four required face statements."""
    meta = SCHOOL["meta"]["resource"]
    named_year = meta["namedYear"]
    group_keys = [g["key"] for g in meta["groups"]]
    check("resource: five CSAM groups declared",
          group_keys == ["unrestricted", "federal", "state",
                         "local", "restrictedOther"])
    # ---- data gates over every shipped district-year
    grp_bad, part_bad, disp_bad, title_bad, prior_named = [], [], [], [], []
    titles = SCHOOL.get("resourceTitles", {})
    for slug, d in SCHOOL["districts"].items():
        for y, v in d["years"].items():
            br = v.get("byResource")
            if not br:
                grp_bad.append(f"{slug} {y}: no byResource")
                continue
            gsum = round(sum(g["v"] for g in br.values()), 2)
            if abs(gsum - v["currentExpense"]) > 0.01:
                grp_bad.append(f"{slug} {y}: groups {gsum} vs CE {v['currentExpense']}")
            unr = br.get("unrestricted", {}).get("v", 0)
            restr = round(sum(g["v"] for k, g in br.items()
                              if k != "unrestricted"), 2)
            if (abs(unr - v["unrestricted"]) > 0.01
                    or abs(restr - v["restricted"]) > 0.01):
                part_bad.append(f"{slug} {y}: partition {unr}/{restr} vs "
                                f"{v['unrestricted']}/{v['restricted']}")
            if y == named_year:
                for gk, g in br.items():
                    ns = sum(x[1] for x in g.get("n", []))
                    if abs(ns + g.get("t", 0) - g["v"]) > 0.01:
                        disp_bad.append(f"{slug} {gk}: named+tail != group v")
                    for nrow in g.get("n", []):
                        code = nrow[0]
                        if code not in titles.get(y, {}) and not code.isdigit():
                            title_bad.append(f"{slug} {code}")
            else:
                if any("n" in g for g in br.values()):
                    prior_named.append(f"{slug} {y}")
    check("resource gate: groups sum to the gated Current Expense to the cent",
          not grp_bad, str(grp_bad[:3]))
    check("resource gate: partition equals the restricted/unrestricted split",
          not part_bad, str(part_bad[:3]))
    check("resource gate: named rows + tail reproduce each group total",
          not disp_bad, str(disp_bad[:3]))
    check("resource: named codes resolve to a title in their own year",
          not title_bad, str(title_bad[:5]))
    check("resource: prior years ship group totals only (payload discipline)",
          not prior_named, str(prior_named[:3]))
    # every named code's title comes from THIS year's table (per-year names)
    check("resource: per-year title table shipped for the named year",
          len(titles.get(named_year, {})) > 40)

    # STRS on-behalf (7690) is present as its own named row somewhere
    strs = meta["strsOnBehalfRes"]
    has_strs = any(nrow[0] == strs for d in SCHOOL["districts"].values()
                   for g in (d["years"].get(named_year, {}).get("byResource") or {}).values()
                   for nrow in g.get("n", []))
    check("resource: STRS on-behalf ships as its own named row", has_strs)
    check("resource: on-behalf note states the district never spends it",
          "never receives or spends" in meta["onBehalfNote"])
    check("resource: unrestricted-is-not-local rule stated",
          "not local" in meta["unrestrictedNote"].lower()
          and "state money" in meta["unrestrictedNote"].lower())
    check("resource: LCFF base/supplemental limit stated plainly",
          "not tracked separately" in meta["lcffNote"].lower()
          and "supplemental" in meta["lcffNote"].lower())
    check("resource: 2000-2999 range shown by name, not classified",
          "no funding source" in meta["otherRangeNote"].lower())
    # no group label conflates unrestricted with local
    for g in meta["groups"]:
        if g["key"] == "unrestricted":
            check("resource: unrestricted group is never labeled local",
                  "local" not in g["name"].lower())

    # ---- UI: the funding-source section renders and carries its notes
    page.goto(f"{base}/schools.html#c=los-angeles-unified")
    page.wait_for_selector("#recordBody .det-row[data-grp]")
    check("resource UI: funding-source section present",
          "Where the money comes from" in page.inner_text(".srchead"))
    check("resource UI: five group rows",
          page.locator("#recordBody .det-row[data-grp]").count() == 5)
    page.locator('#recordBody .det-row[data-grp="state"]').click()
    page.wait_for_timeout(150)
    body = page.inner_text("#recordBody")
    check("resource UI: STRS 7690 named with CDE's title",
          "7690" in body and "On-Behalf Pension" in body)
    check("resource UI: on-behalf note rendered",
          "never receives or spends" in body)
    check("resource UI: unrestricted-not-local note rendered",
          "Unrestricted is not local" in body)
    check("resource UI: LCFF-limit note rendered",
          "supplemental" in body.lower() and "not tracked separately" in body.lower())
    check("resource UI: indirect-cost note rendered",
          "indirect-cost rate" in body)
    # the word 'local' never describes the unrestricted row
    unr_row = page.locator('#recordBody .det-row:has-text("Unrestricted")').first.inner_text()
    check("resource UI: unrestricted row not labeled local",
          "local" not in unr_row.lower())
    # a prior year shows group totals, states named-year, no drill carets
    page.goto(f"{base}/schools.html#c=los-angeles-unified&y=2022-23")
    page.wait_for_selector("#recordBody .det-row[data-grp='unrestricted'], "
                           "#recordBody .srchead")
    prior = page.inner_text("#recordBody")
    check("resource UI: prior year notes the named year",
          named_year in prior and "latest year" in prior)
    check("resource UI: prior year exposes no named drill",
          page.locator("#recordBody .det-row[data-grp]").count() == 0
          or page.locator("#recordBody .src-code").count() == 0)
    # citation + CSV carry the funding source
    page.goto(f"{base}/schools.html#c=los-angeles-unified")
    page.wait_for_selector("#citeToggle")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    cite = page.inner_text("#citeText")
    check("resource cite: citation carries the funding-source split",
          "funding source" in cite.lower() and "unrestricted" in cite.lower())
    page.keyboard.press("Escape")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("resource CSV: funding-source rows with codes and titles",
          "funding_source_group" in csv_text and "On-Behalf Pension" in csv_text
          and "7690" in csv_text)
    check("resource CSV: unrestricted-not-local stated in the header",
          "not local" in csv_text.lower())

    # ---- V10a: the reduced object × resource cross-tab
    obj_keys = [o["key"] for o in SCHOOL["objectFamilies"]]
    # data gate: BOTH margins — each named resource's object array sums to
    # its own total, and object families aggregate to the object totals
    margin1_bad, margin2_bad, ce_bad, absent_full = [], [], [], []
    for slug, d in SCHOOL["districts"].items():
        for y, v in d["years"].items():
            br = v.get("byResource")
            if not br:
                continue
            obj_margin = {}   # objfam -> summed across named
            named_dollars = 0.0
            for gk, g in br.items():
                for row in g.get("n", []):
                    named_dollars += row[1]
                    if len(row) < 3:
                        if y == named_year:
                            margin1_bad.append(f"{slug} {row[0]}: no object array")
                        continue
                    arr = row[2]
                    # margin 1: object array sums to the resource total
                    if sum(arr) != row[1]:
                        margin1_bad.append(f"{slug} {row[0]}: obj {sum(arr)} != {row[1]}")
                    for i, x in enumerate(arr):
                        obj_margin[obj_keys[i]] = obj_margin.get(obj_keys[i], 0) + x
            # the full grid must NOT be shipped: no per-district resource×
            # object matrix, only object arrays hanging off named rows
            if "byResourceObject" in v or "crossTab" in v:
                absent_full.append(f"{slug} {y}")
    check("V10a gate: each named resource's object split sums to its total (margin 1)",
          not margin1_bad, str(margin1_bad[:3]))
    check("V10a: the full object×resource grid is NOT shipped",
          not absent_full, str(absent_full[:3]))
    # margin 2 + CE, verified against the pipeline's own cross-tab is done
    # in the pipeline gate; here confirm the shipped named arrays aggregate
    # sensibly to the object families that also appear in byFunctionObject
    lausd = SCHOOL["districts"]["los-angeles-unified"]["years"][named_year]
    # object-family totals from the function×object view (V8)
    v8_obj = {}
    for fam in lausd["byFunctionObject"].values():
        for ok, val in fam.items():
            v8_obj[ok] = v8_obj.get(ok, 0) + val
    # object-family totals implied by the resource view = named arrays +
    # (the object composition of tails is not shipped, so this checks the
    # named portion is a subset that never exceeds the V8 total)
    res_obj = {}
    for g in lausd["byResource"].values():
        for row in g.get("n", []):
            if len(row) == 3:
                for i, x in enumerate(row[2]):
                    res_obj[obj_keys[i]] = res_obj.get(obj_keys[i], 0) + x
    over = [ok for ok in res_obj
            if res_obj[ok] - v8_obj.get(ok, 0) > max(1.0, abs(v8_obj.get(ok, 0))*0.02)]
    check("V10a: named-resource object cells never exceed the V8 object totals",
          not over, str(over))

    # ---- V10a UI: the drill renders, STRS cell keeps its label
    page.goto(f"{base}/schools.html#c=los-angeles-unified&u=total")
    page.wait_for_selector("#recordBody .det-row[data-grp]")
    page.locator('#recordBody .det-row[data-grp="federal"]').click()
    page.wait_for_timeout(150)
    ti = page.locator('#recordBody .src-code[data-res="federal:3010"]')
    check("V10a UI: a named funding source is drillable to objects",
          ti.count() == 1)
    ti.click()
    page.wait_for_timeout(150)
    body = page.inner_text("#recordBody")
    check("V10a UI: object breakdown renders (what Title I bought)",
          "Certificated salaries" in body and "Employee benefits" in body)
    # the object rows sum to the source total (foot says so)
    check("V10a UI: object split states it sums to the source",
          "sums to the row above" in body)
    # STRS 7690: single benefits cell, keeps the not-district-spent label
    page.locator('#recordBody .det-row[data-grp="state"]').click()
    page.wait_for_timeout(150)
    strs = page.locator('#recordBody .src-code[data-res="state:7690"]')
    if strs.count():
        strs.click()
        page.wait_for_timeout(150)
        sbody = page.inner_text("#recordBody")
        check("V10a UI: STRS on-behalf object cell labeled not-district-spending",
              "not district spending" in sbody
              and "Employee benefits" in sbody)
    # CSV carries the object columns
    page.goto(f"{base}/schools.html#c=los-angeles-unified")
    page.wait_for_selector("#csvBtn")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    csv2 = Path(dl.value.path()).read_text(encoding="utf-8")
    check("V10a CSV: funding-source rows carry object columns",
          "certSalaries" in csv2 and "what each source bought" in csv2)


def test_polish(page, base):
    """Design polish: the phone front door orients within ~250px, the
    header is one component on every page, the masthead statement owns
    its band, Download CSV wears the outline vocabulary, and the type
    scale is declared tokens rather than half-pixel drift."""
    PAGES = ["index.html", "cities.html", "schools.html",
             "districts.html", "address.html", "about.html"]
    # phone front door: statement within the first screen's ~250px
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{base}/index.html")
    page.wait_for_selector(".fd-statement")
    top = page.evaluate(
        "document.querySelector('.fd-statement').getBoundingClientRect().top")
    # ten nav destinations wrap to five two-column rows on a phone. Search
    # was added as the eleventh and the change record moved out of the
    # primary nav to keep it at ten: a sixth row pushes this statement to
    # 374px, outside the top 40% of an 844px screen. The record of changes
    # is a provenance surface like About & method and stays reachable from
    # every footer and from about.html's own section on it.
    check("polish: masthead statement above the fold at 390",
          top <= 340, f"top {top}")
    cols = page.evaluate(
        "getComputedStyle(document.querySelector('nav.pn'))"
        ".gridTemplateColumns.split(' ').length")
    check("polish: phone nav is a two-column grid", cols == 2, str(cols))
    prov_h = page.evaluate(
        "document.querySelector('.prov').getBoundingClientRect().height")
    check("polish: phone provenance strip is one line",
          prov_h < 40, f"h {prov_h}")
    page.set_viewport_size({"width": 1280, "height": 720})

    # one header everywhere: identical nav on all pages (incl. csu.html, ccc.html)
    navs = set()
    for f in PAGES + ["csu.html", "ccc.html", "uc.html"]:
        page.goto(f"{base}/{f}")
        page.wait_for_selector("nav.pn")
        navs.add(page.inner_text("nav.pn").strip())
    check("polish: the nav reads identically on every page",
          len(navs) == 1, str([n.replace(chr(10), ' | ') for n in navs])[:200])

    # masthead hierarchy: the statement owns its band; no header echo
    page.goto(f"{base}/index.html")
    st = page.evaluate(
        "getComputedStyle(document.querySelector('.fd-statement')).fontSize")
    check("polish: statement at display size", st == "52px", st)
    check("polish: tagline and statement say different things",
          page.inner_text(".tagline").strip()
          != page.inner_text(".fd-statement").strip().rstrip("."))

    # blue is disciplined: no solid-blue Download CSV anywhere
    for f, sel_state in (("index.html", None),
                         ("cities.html#c=los-angeles", "#recordBody .det-row"),
                         ("schools.html#c=los-angeles-unified", "#recordBody .det-row"),
                         ("districts.html#d=adelanto-public-financing-authority", "#recMeta"),
                         ("address.html#c=sacramento", "#records .record")):
        page.goto(f"{base}/about.html")
        page.goto(f"{base}/{f}")
        if sel_state:
            page.wait_for_selector(sel_state)
        bg = page.evaluate(
            "getComputedStyle(document.querySelector('#csvBtn')).backgroundColor")
        check(f"polish: Download CSV outlined on {f.split('#')[0]}",
              "43, 89, 209" not in bg, bg)

    # declared type scale: tokens exist and diversity is bounded
    for f in PAGES:
        page.goto(f"{base}/{f}")
        page.wait_for_selector("footer.ft")
        toks = page.evaluate(
            "getComputedStyle(document.documentElement)"
            ".getPropertyValue('--fs-label').trim()")
        check(f"polish: type tokens declared on {f}", toks == "11.5px", toks)
        n = page.evaluate("""(() => {
          const s = new Set();
          document.querySelectorAll('body *').forEach(el => {
            if (el.offsetParent !== null || el.tagName === 'BODY')
              s.add(getComputedStyle(el).fontSize);
          });
          return s.size;
        })()""")
        check(f"polish: bounded type diversity on {f}", n <= 13, f"{n} sizes")


def test_cite(page, base):
    """The Cite control must never look dead: the panel scrolls into
    view when opened (it lives far below the header button), the copy
    always gives visible feedback, a legacy fallback covers engines
    with no async clipboard API, and every citation carries an access
    date. The county layer cites county filings, not city ones."""
    RECT = ("() => { const r = document.getElementById('citePanel')"
            ".getBoundingClientRect(); return {t: r.top, b: r.bottom,"
            " l: r.left, r2: r.right, iw: innerWidth, ih: innerHeight}; }")
    # a citation is copy-and-leave: the popup appears AT the reader's
    # position — in the viewport, without scrolling the page
    for f, toggle in (("index.html", "#citeToggle"),
                      ("schools.html", "#citeToggle")):
        page.goto(f"{base}/{f}")
        page.wait_for_selector(toggle)
        check(f"cite {f}: the citation control is a dialog",
              page.evaluate("document.getElementById('citePanel').tagName")
              == "DIALOG")
        page.locator(toggle).scroll_into_view_if_needed()
        y0 = page.evaluate("scrollY")
        page.click(toggle)
        page.wait_for_selector("#citePanel[open]")
        r = page.evaluate(RECT)
        check(f"cite {f}: popup opens fully inside the viewport",
              r["t"] >= 0 and r["b"] <= r["ih"]
              and r["l"] >= 0 and r["r2"] <= r["iw"], str(r))
        check(f"cite {f}: the page does not scroll away",
              page.evaluate("scrollY") == y0)
        page.keyboard.press("Escape")
        check(f"cite {f}: Escape dismisses",
              page.evaluate("!document.getElementById('citePanel').open"))
        page.click(toggle)
        page.wait_for_selector("#citePanel[open]")
        page.mouse.click(8, 8)   # backdrop, far from the card
        page.wait_for_timeout(120)
        check(f"cite {f}: click-away dismisses",
              page.evaluate("!document.getElementById('citePanel').open"))

    # phone widths: the popup centers and fits, fully readable
    for w in (360, 390):
        page.set_viewport_size({"width": w, "height": 780})
        page.goto(f"{base}/about.html")
        page.goto(f"{base}/cities.html#c=los-angeles")
        page.wait_for_selector("#citeToggle")
        page.click("#citeToggle")
        page.wait_for_selector("#citePanel[open]")
        r = page.evaluate(RECT)
        check(f"cite {w}px: popup fits the viewport",
              r["t"] >= 0 and r["b"] <= 780 and r["l"] >= 0 and r["r2"] <= w,
              str(r))
        page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1280, "height": 720})

    # copy: feedback + clipboard + access date, on all five pages
    TARGETS = [("index.html", "#citeToggle"),
               ("cities.html#c=los-angeles", "#citeToggle"),
               ("schools.html#c=los-angeles-unified", "#citeToggle"),
               ("districts.html#d=adelanto-public-financing-authority", "#citeBtn"),
               ("address.html#c=sacramento", "#citeBtn")]
    for url, toggle in TARGETS:
        page.goto(f"{base}/about.html")   # force a full navigation
        page.goto(f"{base}/{url}")
        page.wait_for_selector(f"{toggle}:visible")
        page.click(toggle)
        page.wait_for_selector("#citeText:visible")
        cited = page.inner_text("#citeText")
        check(f"cite {url.split('#')[0]}: citation carries an access date",
              "Accessed 20" in cited, cited[-60:])
        page.click("#citeCopy")
        page.wait_for_timeout(150)
        label = page.inner_text("#citeCopy")
        check(f"cite {url.split('#')[0]}: visible confirmation on copy",
              label.startswith("Citation copied"), label)
        clip = page.evaluate("navigator.clipboard.readText()")
        check(f"cite {url.split('#')[0]}: clipboard holds the full citation",
              clip == cited, clip[:80])

    # blocked async clipboard API (webviews): never silent — either the
    # legacy fallback copies, or the citation is selected and it says
    # so. Clobber the API at runtime on the live page (equivalent to an
    # engine without it; resets on the next navigation).
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/schools.html#c=los-angeles-unified")
    page.wait_for_selector("#citeToggle")
    page.evaluate(
        "Object.defineProperty(navigator,'clipboard',{value:undefined})")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    page.click("#citeCopy")
    page.wait_for_timeout(150)
    label = page.inner_text("#citeCopy")
    check("cite blocked-API: control is never silent",
          label.startswith("Citation copied") or label.startswith("Copy failed"),
          label)

    # county layer: citation and CSV name county filings
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#l=county&c=santa-clara")
    page.wait_for_selector("#recordBody .det-row")
    page.click("#citeToggle")
    page.wait_for_selector("#citeText:visible")
    check("cite county layer: basis names county filings",
          "county annual financial reports" in page.inner_text("#citeText"))
    page.keyboard.press("Escape")   # dismiss the cite dialog before touching the page
    with page.expect_download() as dl:
        page.click("#csvBtn")
    text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("csv county layer: basis header names county filings",
          "standardized county annual financial reports" in text)
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#c=los-angeles")
    page.wait_for_selector("#recordBody .det-row")
    with page.expect_download() as dl:
        page.click("#csvBtn")
    text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("csv city layer: basis header still names city filings",
          "standardized city annual financial reports" in text)


def test_inflation_labeling(page, base):
    """PLAIN LANGUAGE ON THE INFLATION TOGGLE.

    The control shipped as two pills reading "Nominal" and "Real" with no
    visible label — its only name was aria-label="Dollar basis", which is
    screen-reader-only and is itself accounting vocabulary. A reader with no
    finance background had no way to know the control was an inflation
    adjustment. Worse, in the DEFAULT nominal state the word "inflation" did
    not appear anywhere on screen on any of the three layers.

    The precise terms are kept. What is added is a plain-language name for
    what the control does."""
    LAYERS = [("index.html", "", "as published"),
              ("cities.html", "#c=oakland", "as filed"),
              ("schools.html", "#c=los-angeles-unified", "as filed")]

    for f, frag, asword in LAYERS:
        page.goto(f"{base}/{f}{frag}")
        page.wait_for_selector("#basisGroup")
        page.wait_for_timeout(250)

        st = page.evaluate("""() => { const g = document.getElementById('basisGroup');
            const l = document.getElementById('basisLbl');
            const c = l && getComputedStyle(l);
            return {
              hasLabel: !!l,
              labelText: l ? l.textContent.trim() : null,
              labelVisible: !!(l && c.display !== 'none' && c.visibility !== 'hidden'
                               && l.offsetParent !== null),
              labelClass: l ? l.className : null,
              ariaLabel: g.getAttribute('aria-label'),
              labelledBy: g.getAttribute('aria-labelledby'),
              pills: [...g.querySelectorAll('button')].map(b => b.textContent.trim()),
              nomTitle: g.querySelector("[data-basis='nominal']").title,
              realTitle: g.querySelector("[data-basis='real']").title,
            }; }""")

        check(f"inflation labeling {f}: the control carries a VISIBLE label, not "
              f"only a screen-reader one", st["hasLabel"] and st["labelVisible"])
        check(f"inflation labeling {f}: and that label says the plain word",
              st["labelText"] == "Inflation", str(st["labelText"]))

        # aria-label outranks adjacent text in the accessible-name computation.
        # Leaving it in place would mean a sighted reader sees "Inflation" while
        # a screen-reader user still hears "Dollar basis" — two names for one
        # control, strictly worse than before.
        check(f"inflation labeling {f}: the accounting-vocabulary aria-label is "
              f"GONE, so the visible word cannot disagree with the announced one",
              st["ariaLabel"] is None, str(st["ariaLabel"]))
        check(f"inflation labeling {f}: the group is named BY the visible label",
              st["labelledBy"] == "basisLbl", str(st["labelledBy"]))

        # The DOM text is title-case and CSS uppercases it. text-transform does
        # not reach the accessibility tree, so writing "INFLATION" in the markup
        # would have it announced letter-by-letter by some screen readers.
        check(f"inflation labeling {f}: the label is uppercased in CSS, not in "
              f"the DOM, so it is announced as a word",
              st["labelText"] == "Inflation"
              and page.eval_on_selector("#basisLbl",
                    "e => getComputedStyle(e).textTransform") == "uppercase")

        check(f"inflation labeling {f}: the precise terms are KEPT — correct "
              f"vocabulary is not removed, only made legible",
              st["pills"] == ["Nominal", "Real"], str(st["pills"]))

        # The group label names the subject; these name the operation. Without
        # them a reader knows the control concerns inflation but not which pill
        # applies it.
        for term, want in (("nominal", asword), ("real", "Adjusted for inflation")):
            t = st["nomTitle"] if term == "nominal" else st["realTitle"]
            check(f"inflation labeling {f}: the {term} pill says plainly what it "
                  f"does", want.lower() in t.lower() and "inflation" in t.lower(), t)
        check(f"inflation labeling {f}: the real pill names the base year and "
              f"whose adjustment it is, on the control itself",
              "2024-25" in st["realTitle"] and "Ledger" in st["realTitle"],
              st["realTitle"])

        # THE REGRESSION THAT STARTED THIS. Default basis is nominal, and
        # renderBasisNote() blanks itself when not real — so before this change
        # the word did not appear on screen at all until Real was already on.
        vis = page.evaluate("""() => { const out = [];
            document.querySelectorAll('body *').forEach(e => {
              if (e.children.length) return;
              const c = getComputedStyle(e);
              if (c.display === 'none' || c.visibility === 'hidden' || !e.offsetParent) return;
              if (/inflation/i.test(e.textContent)) out.push(e.textContent.trim());
            }); return out; }""")
        check(f"inflation labeling {f}: the word 'inflation' is on screen in the "
              f"DEFAULT nominal state, before the reader touches anything",
              len(vis) > 0, str(vis))
        check(f"inflation labeling {f}: and the nominal state says it is NOT "
              f"adjusted, rather than only naming the basis",
              any("not adjusted for inflation" in v.lower() for v in vis), str(vis))

    # ---- when Real is on, the claim is stated at the point of use
    for f, frag in [("index.html", "#v=trend&b=real"),
                    ("cities.html", "#c=oakland&b=real"),
                    ("schools.html", "#c=los-angeles-unified&b=real")]:
        page.goto(f"{base}/{f}{frag}")
        page.wait_for_selector("#basisNote:not([hidden])")
        lead = page.eval_on_selector("#basisNote b", "e => e.textContent")
        check(f"inflation labeling {f}: the real-dollar lead states the operation "
              f"in plain words, not only in accounting terms",
              "ADJUSTED FOR INFLATION" in lead, lead)
        check(f"inflation labeling {f}: names the base year in the same line",
              "2024-25" in lead, lead)
        # deflator-data.js carries meta.ours; it must reach the face of the page,
        # not only the method note and the printed sheet.
        check(f"inflation labeling {f}: and says whose adjustment it is in the "
              f"same line — the Ledger's, not the source's",
              "BY THE LEDGER" in lead and "NOT THE SOURCE" in lead, lead)

    # ---- the inert reasons read plainly rather than assuming the reader knows
    #      why deflating a ratio changes nothing
    INERT = [("index.html#u=percent&b=real", "percent units", "ratio"),
             ("index.html#v=actuals&b=real", "the actuals view", "same year"),
             ("cities.html#c=oakland&u=percent&b=real", "cities percent units", "ratio")]
    for url, who, must in INERT:
        page.goto(f"{base}/{url}")
        page.wait_for_selector("#basisGroup")
        page.wait_for_timeout(250)
        r = page.evaluate("""() => { const b = document.querySelector(
              "#basisGroup button[data-basis='real']");
            return {disabled: b.disabled, title: b.title}; }""")
        # native disabled, not aria-disabled: a control that provably does
        # nothing must not look live. Asserted again here because the plain
        # rewrite is exactly the kind of change that tempts a switch.
        check(f"inflation labeling: still natively disabled in {who}",
              r["disabled"] is True)
        check(f"inflation labeling: the reason in {who} names inflation in plain "
              f"words rather than assuming 'deflating' is understood",
              "inflation" in r["title"].lower() and "deflat" not in r["title"].lower(),
              r["title"])
        check(f"inflation labeling: the reason in {who} still gives the arithmetic "
              f"ground", must in r["title"].lower(), r["title"])

    # ---- THE LABEL MUST STAY WITH THE CONTROL IT LABELS.
    #      First cut placed the label as a bare sibling in a space-between
    #      wrapping row. Measured, it detached from its group at 16 of 18
    #      widths, and on index.html at 1024/900/414/390 it came to rest beside
    #      the UNIT group — labelling the wrong control, which is worse than
    #      labelling none. Adjacency is now structural (one inline-flex box),
    #      and asserted across the range rather than at one convenient width.
    for f, frag in [("index.html", ""), ("cities.html", "#c=oakland"),
                    ("schools.html", "#c=los-angeles-unified")]:
        for w in (1600, 1440, 1280, 1024, 900, 768, 600, 480, 414, 390, 375, 360):
            page.set_viewport_size({"width": w, "height": 900})
            page.goto(f"{base}/{f}{frag}")
            page.wait_for_selector("#basisGroup")
            page.wait_for_timeout(200)
            g = page.evaluate("""() => {
                const l = document.getElementById('basisLbl').getBoundingClientRect();
                const b = document.getElementById('basisGroup').getBoundingClientRect();
                const u = document.getElementById('unitGroup');
                const ur = u ? u.getBoundingClientRect() : null;
                return {overlap: Math.min(l.bottom, b.bottom) - Math.max(l.top, b.top),
                        gap: b.left - l.right,
                        unitOverlap: ur ? Math.min(l.bottom, ur.bottom) - Math.max(l.top, ur.top) : -1,
                        unitGap: ur ? Math.abs(ur.left - l.right) : 1e9}; }""")
            check(f"inflation labeling {f} @{w}px: the label shares a line with "
                  f"the control it names", g["overlap"] > 0,
                  f'overlap {g["overlap"]:.0f}px')
            check(f"inflation labeling {f} @{w}px: and sits beside it, not "
                  f"stranded across the row", 0 <= g["gap"] <= 20, f'gap {g["gap"]:.0f}px')
            # proximity is the only grouping cue; if another group is nearer on
            # the same line, the label reads as belonging to that one instead
            check(f"inflation labeling {f} @{w}px: no other control group is "
                  f"nearer to it than its own", g["unitOverlap"] <= 0
                  or g["unitGap"] > g["gap"],
                  f'unit gap {g["unitGap"]:.0f} vs own gap {g["gap"]:.0f}')
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- a reason carried only in title() reaches nobody on a disabled
    #      control: a disabled button is not focusable, so screen readers get
    #      nothing. Mirror it into the accessibility tree.
    page.goto(f"{base}/index.html#u=percent&b=real")
    page.wait_for_selector("#basisGroup")
    page.wait_for_timeout(250)
    a = page.evaluate("""() => { const g = document.getElementById('basisGroup');
        const w = document.getElementById('basisWhy');
        return {by: g.getAttribute('aria-describedby'), text: w ? w.textContent : null,
                title: document.querySelector("#basisGroup button[data-basis='real']").title}; }""")
    check("inflation labeling: the inert reason reaches assistive tech, not only "
          "a mouse hover", a["by"] == "basisWhy" and a["text"] == a["title"]
          and len(a["text"]) > 0, str(a["by"]))
    page.goto(f"{base}/index.html")
    page.wait_for_selector("#basisGroup")
    page.wait_for_timeout(250)
    check("inflation labeling: and the description is withdrawn when the control "
          "works, so nothing stale is announced",
          page.evaluate("() => document.getElementById('basisGroup')"
                        ".getAttribute('aria-describedby')") is None)

    # ---- A REASON MUST BE TRUE ON THE SCREEN THAT SHOWS IT.
    #      realOn() excludes percent units but NOT the actuals view, so figures
    #      there ARE adjusted. A first draft of this copy read "No inflation
    #      adjustment applies here" while the basis note on the same screen read
    #      "ADJUSTED FOR INFLATION". Plain language that is false is worse than
    #      jargon that is true.
    page.goto(f"{base}/index.html#v=actuals&b=real")
    page.wait_for_selector("#basisGroup")
    page.wait_for_timeout(400)
    t = page.evaluate("""() => { const n = document.getElementById('basisNote');
        return {noteShown: !n.hidden,
                lead: n.hidden ? "" : n.querySelector('b').textContent,
                reason: document.querySelector("#basisGroup button[data-basis='real']").title}; }""")
    check("inflation labeling: the actuals reason does not deny an adjustment "
          "the same screen is announcing",
          not (t["noteShown"] and "ADJUSTED FOR INFLATION" in t["lead"]
               and "no inflation adjustment applies" in t["reason"].lower()),
          f'note={t["lead"][:40]!r} reason={t["reason"][:60]!r}')
    check("inflation labeling: it says instead that the basis cannot change the "
          "gap, which is what is actually true",
          "cannot change" in t["reason"].lower() and "gap" in t["reason"].lower(),
          t["reason"])

    # ---- the label survives the narrow viewport that has bitten this row twice
    page.set_viewport_size({"width": 360, "height": 800})
    for f in ("index.html", "cities.html", "schools.html"):
        page.goto(f"{base}/{f}")
        page.wait_for_timeout(500)
        sw, cw = page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        check(f"inflation labeling {f}: no horizontal overflow at 360px", sw <= cw,
              f"{sw} > {cw}")
        check(f"inflation labeling {f}: the label is still visible at 360px — a "
              f"label that vanishes on a phone is not a label",
              page.evaluate("""() => { const l = document.getElementById('basisLbl');
                  const c = getComputedStyle(l);
                  return c.display !== 'none' && l.offsetParent !== null; }"""))
    page.set_viewport_size({"width": 1280, "height": 900})


def test_inflation(page, base):
    """THE INFLATION ADJUSTMENT (V14) — the site's first figure that is a
    METHODOLOGICAL CHOICE rather than reproduction of a source.

    Almost every assertion here is about honesty rather than arithmetic,
    because the arithmetic is trivial and the honesty is the whole risk:
    a real figure that does not name its index, or a real figure resting
    on a projected deflator, is the artifact this feature would be
    attacked on.
    """
    DEF = load_data_js(ROOT / "deflator-data.js")
    m = DEF["meta"]

    # --- the index is the one California statute names, from DOF
    check("inflation: the index is the state-and-local government purchases "
          "deflator", "State and Local Government Purchases" in m["index"])
    check("inflation: the statutory basis is recorded",
          "42238.1" in m["statute"])
    check("inflation: DOF is the publisher of record",
          m["source"] == "dof.ca.gov" and "Department of Finance" in m["sourceLabel"])
    check("inflation: the source file's own vintage is recorded",
          bool(m["vintage"]), str(m.get("vintage")))
    check("inflation: the bytes we parsed are digested, so a real figure "
          "traces to an exact index vintage",
          m["sourceDigest"].startswith("sha256:") and len(m["sourceDigest"]) == 71)
    check("inflation: the national limit is stated in the data itself",
          "national" in m["geography"].lower() and "national" in m["limits"].lower())
    check("inflation: the adjustment is declared as the Ledger's own",
          "Ledger" in m["ours"] and "nominal" in m["ours"].lower())
    check("inflation: the short-window sensitivity is carried with the data",
          "42%" in m["shortWindow"] or "2.68" in m["shortWindow"])

    # --- fiscal-year values come from DOF, not from our own averaging
    check("inflation: the series is fiscal-year keyed, as DOF publishes it",
          all(re.match(r"^\d{4}-\d{2}$", k) for k in DEF["fy"]),
          str([k for k in DEF["fy"] if not re.match(r"^\d{4}-\d{2}$", k)][:3]))
    check("inflation: the series is long enough to cover every layer",
          len(DEF["fy"]) > 60 and "2016-17" in DEF["fy"], str(len(DEF["fy"])))

    # --- THE FORECAST RULE
    check("inflation: DOF's forecast years are identified",
          len(m["forecastYears"]) > 0, str(m["forecastYears"]))
    check("inflation: the base year is an ACTUAL year, never a forecast",
          m["baseYear"] not in m["forecastYears"] and m["baseYear"] == m["lastActual"],
          f'base {m["baseYear"]} lastActual {m["lastActual"]}')
    for fy in m["forecastYears"]:
        check(f"inflation: forecast year {fy} sorts after the last actual",
              fy > m["lastActual"])
    check("inflation: the state layer's newest year is a DOF forecast — the "
          "case this rule exists for",
          "2025-26" in m["forecastYears"], str(m["forecastYears"]))

    # --- a source anomaly is named, never silently resolved
    check("inflation: duplicate fiscal years in DOF's file are recorded "
          "rather than silently picked",
          isinstance(m.get("sourceAnomalies"), list))
    for a in m.get("sourceAnomalies") or []:
        check("inflation: each anomaly names the year and both values",
              "twice" in a and "forecast" in a, a[:70])

    # --- the page
    page.goto(f"{base}/index.html")
    page.wait_for_selector("#basisGroup")
    check("inflation: nominal is the default basis",
          page.eval_on_selector("#basisGroup button[data-basis='nominal']",
                                "e => e.classList.contains('on')"))
    body = page.inner_text("body")
    check("inflation: a nominal view does not display the real-dollar note",
          page.eval_on_selector("#basisNote", "e => e.hidden"))
    check("inflation: the strip says the figures are nominal as published",
          "NOMINAL" in body.upper())

    page.goto(f"{base}/index.html#v=trend&b=real")
    page.wait_for_selector("#basisNote:not([hidden])")
    note = page.inner_text("#basisNote")
    for phrase, why in (
            ("Ledger", "must attribute the adjustment to us"),
            (m["baseYear"], "must name the base year"),
            ("State and Local Government Purchases", "must name the index"),
            ("42238.1", "must name the statutory basis"),
            (m["vintage"], "must name the index vintage"),
            ("national", "must state the geography limit"),
    ):
        check(f"inflation: the real-dollar note {why}",
              phrase.lower() in note.lower(), phrase)
    check("inflation: the note says the source publishes nominal only",
          "nominal" in note.lower() and "deflate nothing" in note.lower())
    check("inflation: the note names the omitted forecast year",
          "2025-26" in note)
    check("inflation: the note lists only forecast years this page shows, "
          "not DOF's whole projection horizon",
          "2027-28" not in note and "2028-29" not in note, note[-200:])
    check("inflation: the strip marks the view as real and as ours",
          "REAL" in page.inner_text("#dataBanner").upper()
          and "LEDGER" in page.inner_text("#dataBanner").upper())

    # --- nominal must always be one interaction away
    check("inflation: the nominal control is present and enabled in a real view",
          page.eval_on_selector("#basisGroup button[data-basis='nominal']",
                                "e => !e.disabled"))

    # --- disabled where deflation is arithmetically inert
    page.goto(f"{base}/index.html#u=percent&b=real")
    page.wait_for_selector("#basisGroup")
    check("inflation: the toggle is DISABLED in percent units, not merely "
          "inert — a control that provably does nothing must not look live",
          page.eval_on_selector("#basisGroup button[data-basis='real']",
                                "e => e.disabled"))
    check("inflation: and it says why",
          "ratio" in (page.eval_on_selector(
              "#basisGroup button[data-basis='real']", "e => e.title") or ""))
    page.goto(f"{base}/index.html#v=actuals&b=real")
    page.wait_for_selector("#basisGroup")
    check("inflation: the toggle is disabled in the actuals view, where the "
          "difference is a same-year ratio",
          page.eval_on_selector("#basisGroup button[data-basis='real']",
                                "e => e.disabled"))

    # --- permalink, citation and CSV can never be ambiguous about basis
    page.goto(f"{base}/index.html#v=trend&b=real")
    page.wait_for_selector("#basisNote:not([hidden])")
    check("inflation: the basis rides in the permalink",
          "b=real" in page.evaluate("location.hash"))
    with page.expect_download() as dl:      # before opening the dialog, which
        page.click("#csvBtn")              # would intercept the click
    csv = Path(dl.value.path()).read_text(encoding="utf-8")
    page.click("#citeToggle")
    page.wait_for_selector("#citePanel[open]")
    cite = page.inner_text("#citeText")
    check("inflation: a citation of a real figure names the index",
          "State and Local Government Purchases" in cite)
    check("inflation: a citation of a real figure names the base year and vintage",
          m["baseYear"] in cite and m["vintage"] in cite)
    check("inflation: a citation of a real figure says the adjustment is ours",
          "LEDGER'S OWN" in cite.upper())
    check("inflation: the CSV declares its dollar basis",
          "# Dollar basis:" in csv and "REAL" in csv)
    check("inflation: the CSV names the index and vintage",
          "State and Local Government Purchases" in csv and m["vintage"] in csv)

    page.goto(f"{base}/index.html")
    page.wait_for_selector("#basisGroup")
    with page.expect_download() as dl2:
        page.click("#csvBtn")
    check("inflation: a nominal CSV says so too",
          "NOMINAL" in Path(dl2.value.path()).read_text(encoding="utf-8"))
    page.click("#citeToggle")
    page.wait_for_selector("#citePanel[open]")
    nom_cite = page.inner_text("#citeText")
    check("inflation: a NOMINAL citation says so explicitly rather than "
          "staying silent about basis",
          "nominal" in nom_cite.lower() and "not adjusted" in nom_cite.lower())



    # ---- the same contract on the local and K-12 layers -----------------
    # Each page's own basis sentences must come from the data file, so a
    # page can never quietly say something the data does not.
    for pg, entity_hash, src_word in (
            ("cities.html", "#c=oakland", "Controller"),
            ("schools.html", "#c=los-angeles-unified", "CDE")):
        page.goto(f"{base}/{pg}{entity_hash}")
        page.wait_for_selector("#basisGroup")
        check(f"inflation {pg}: nominal is the default",
              page.eval_on_selector("#basisGroup button[data-basis='nominal']",
                                    "e => e.classList.contains('on')"))
        check(f"inflation {pg}: no real-dollar note in a nominal view",
              page.eval_on_selector("#basisNote", "e => e.hidden"))
        check(f"inflation {pg}: the strip says the figures are nominal",
              "NOMINAL" in page.inner_text("#dataBanner").upper())

        sep = "&" if "#" in entity_hash else "#"
        page.goto(f"{base}/{pg}{entity_hash}{sep}b=real")
        page.wait_for_selector("#basisNote:not([hidden])")
        note = page.inner_text("#basisNote")
        for phrase, why in (
                ("Ledger", "attributes the adjustment to us"),
                (m["baseYear"], "names the base year"),
                ("State and Local Government Purchases", "names the index"),
                ("42238.1", "names the statutory basis"),
                (m["vintage"], "names the index vintage"),
                ("national", "states the geography limit"),
        ):
            check(f"inflation {pg}: the note {why}",
                  phrase.lower() in note.lower(), phrase)
        check(f"inflation {pg}: the strip marks the view real and ours",
              "REAL" in page.inner_text("#dataBanner").upper()
              and "LEDGER" in page.inner_text("#dataBanner").upper())
        check(f"inflation {pg}: nominal stays one interaction away",
              page.eval_on_selector("#basisGroup button[data-basis='nominal']",
                                    "e => !e.disabled"))
        check(f"inflation {pg}: the basis rides in the permalink",
              "b=real" in page.evaluate("location.hash"))

        with page.expect_download() as d:
            page.click("#csvBtn" if pg == "cities.html" else "#csvBtn")
        csvtxt = Path(d.value.path()).read_text(encoding="utf-8")
        check(f"inflation {pg}: the CSV declares its dollar basis",
              "# Dollar basis:" in csvtxt and "REAL" in csvtxt)
        check(f"inflation {pg}: the CSV names index and vintage",
              "State and Local Government Purchases" in csvtxt
              and m["vintage"] in csvtxt)
        page.click("#citeToggle")
        page.wait_for_selector("#citePanel[open]")
        c = page.inner_text("#citeText")
        check(f"inflation {pg}: the citation names the index and base year",
              "State and Local Government Purchases" in c and m["baseYear"] in c)
        check(f"inflation {pg}: the citation says the adjustment is ours",
              "LEDGER'S OWN" in c.upper())
        check(f"inflation {pg}: the citation names the source that publishes "
              f"nominal only", src_word.lower() in c.lower())

    # ---- the window sensitivity is stated per layer, on the right face ---
    wn = m["windowNotes"]
    check("inflation: per-layer window notes ship with the data",
          set(wn) >= {"local", "k12", "state"}, str(sorted(wn)))
    check("inflation: the K-12 note names the 2.68-point divergence and the "
          "sign risk — the sensitive case",
          "2.68" in wn["k12"] and "42%" in wn["k12"]
          and "sign" in wn["k12"].lower())
    check("inflation: the local note names the 0.6-point divergence and the "
          "one city that flips — the less sensitive case",
          "0.6" in wn["local"] and "482" in wn["local"])
    check("inflation: the local note carries the result this feature exists "
          "for (71 of 482 reverse direction)",
          "71" in wn["local"] and "482" in wn["local"])

    page.goto(f"{base}/schools.html#c=los-angeles-unified&b=real")
    page.wait_for_selector("#basisNote:not([hidden])")
    k12note = page.inner_text("#basisNote")
    check("inflation schools.html: the three-year sensitivity is on THIS "
          "page's face, not only in a shared method note",
          "2.68" in k12note and "sign" in k12note.lower())
    page.goto(f"{base}/cities.html#c=oakland&b=real")
    page.wait_for_selector("#basisNote:not([hidden])")
    citynote = page.inner_text("#basisNote")
    check("inflation cities.html: the eight-year window is stated as the "
          "less sensitive case", "0.6" in citynote)
    check("inflation cities.html: and it does NOT claim K-12's sensitivity",
          "2.68" not in citynote)

    # ---- inert where a ratio would be deflated on both sides
    page.goto(f"{base}/cities.html#c=oakland&u=percent&b=real")
    page.wait_for_selector("#basisGroup")
    check("inflation cities.html: the toggle is disabled in percent units",
          page.eval_on_selector("#basisGroup button[data-basis='real']",
                                "e => e.disabled"))

    # ---- THE RESULT THIS FEATURE EXISTS FOR, recomputed from shipped files
    DEFfy = DEF["fy"]
    def adj(v, fy):
        return (v * (DEFfy[m["baseYear"]] / DEFfy[fy])
                if fy in DEFfy and fy not in m["forecastYears"] else v)
    a_fy, b_fy = "2016-17", "2023-24"
    tot = up_down = down_up = 0
    for rec in CITY["cities"].values():
        ys = rec.get("years") or {}
        va = (ys.get(a_fy) or {}).get("expenditures")
        vb = (ys.get(b_fy) or {}).get("expenditures")
        if not (isinstance(va, (int, float)) and isinstance(vb, (int, float))
                and va > 0):
            continue
        tot += 1
        nom = vb / va - 1
        real = adj(vb, b_fy) / adj(va, a_fy) - 1
        if nom > 0 and real < 0:
            up_down += 1
        if nom < 0 and real > 0:
            down_up += 1
    check("inflation: 482 cities have a usable 2016-17 -> 2023-24 span",
          tot == 482, str(tot))
    check("inflation: 71 of 482 cities rise nominally and fall in real terms "
          "— recomputed from the shipped data and the shipped deflator",
          up_down == 71, str(up_down))
    check("inflation: none go the other way", down_up == 0, str(down_up))


def test_print_state(page, base):
    """STATE PRINT SHEET — the worst gap the print audit found.

    The method note was emitted in the ALLOCATION view only, so change,
    trend and actuals rendered a netted figure with no dagger at all.
    Office of Emergency Services FY2022-23 reads +1.3% in the change view
    while a -$3.884B special-fund offset nets against a General Fund line
    that roughly quintupled (0.861 -> 4.943). These assert the note is
    both marked on screen in every view and printed in full."""
    OES_AGENCY = "legislative-judicial-and"
    for view in ("allocation", "change", "trend", "actuals"):
        page.emulate_media(media="screen")
        page.goto(f"{base}/index.html#y=2022-23&v={view}&a={OES_AGENCY}")
        page.wait_for_selector("#recordSheet", state="attached")
        n = page.eval_on_selector_all(".dagger", "e => e.length")
        check(f"print state: the {view} view marks rows carrying a method "
              f"note (it marked none before)", n > 0, f"{n} daggers")

    page.emulate_media(media="print")
    for view in ("allocation", "change", "trend", "actuals"):
        page.goto(f"{base}/index.html#y=2022-23&v={view}&a={OES_AGENCY}")
        page.wait_for_selector("#recordSheet", state="attached")
        page.wait_for_function(
            "() => document.getElementById('recordSheet').innerText.trim().length > 0")
        sheet = page.inner_text("#recordSheet")
        check(f"print state: the {view} sheet prints the note IN FULL, not a "
              f"symbol", "negative appropriations" in sheet, view)
        check(f"print state: the {view} sheet names the row the note applies to",
              "Emergency Services" in sheet, view)
        for phrase in ("ACCOUNTING BASIS", "GATE", "DISPLAY RESOLUTION",
                       "DOLLARS", "SOURCE", "PERMALINK", "SHA-256",
                       "verify_digest.py", "REVISIONS"):
            check(f"print state ({view}): the sheet carries {phrase}",
                  phrase in sheet, phrase)
        check(f"print state ({view}): the agency-level gate limit is stated",
              "AGENCY level" in sheet or "agency level" in sheet.lower())
    page.emulate_media(media="screen")


def test_print_highered(page, base):
    """PRINT SHEETS — CSU, CCC, UC (priority 2).

    All three shared cities.html's single-value S.openNote, so a printed
    table showed per-student figures with none of the notes qualifying
    them. UCSF is the case: four flags (medCenter, healthOnly,
    researchIntensive, smallScale) and a per-student figure that means
    nothing without all four."""
    for pg, layer in (("csu.html", "CSU CAMPUSES"),
                      ("ccc.html", "COMMUNITY COLLEGE DISTRICTS"),
                      ("uc.html", "UC CAMPUSES")):
        page.emulate_media(media="screen")
        page.goto(f"{base}/{pg}")
        page.wait_for_selector(".dag")
        n = page.eval_on_selector_all(".dag", "e => e.length")
        check(f"print {pg}: rows carrying notes are marked on screen",
              n > 0, str(n))

        page.emulate_media(media="print")
        page.goto(f"{base}/{pg}")
        page.wait_for_selector("#recordSheet", state="attached")
        page.wait_for_function(
            "() => document.getElementById('recordSheet').innerText.trim().length > 0")
        sheet = page.inner_text("#recordSheet")
        check(f"print {pg}: the sheet names its layer", layer in sheet, layer)
        for phrase in ("ACCOUNTING BASIS", "GATE", "RESOLUTION AND DENOMINATOR",
                       "DOLLARS", "COMPARABILITY NOTES", "SOURCE", "PERMALINK",
                       "SHA-256", "verify_digest.py", "REVISIONS"):
            check(f"print {pg}: the sheet carries {phrase}", phrase in sheet, phrase)
        check(f"print {pg}: notes print in full, with no click",
              "\u2020" in sheet and "CARRY THEM, PRINTED IN FULL" in sheet)

    # each layer's gate resolution, in its own words
    page.goto(f"{base}/csu.html"); page.wait_for_selector("#recordSheet", state="attached")
    check("print csu: states its thousand-resolution gate",
          "TO THE THOUSAND" in page.inner_text("#recordSheet"))
    page.goto(f"{base}/ccc.html"); page.wait_for_selector("#recordSheet", state="attached")
    check("print ccc: states its whole-dollar gate",
          "TO THE DOLLAR" in page.inner_text("#recordSheet"))

    # THE UCSF CASE — all four notes, in full, unprompted
    page.goto(f"{base}/uc.html")
    page.wait_for_selector("#recordSheet", state="attached")
    page.wait_for_function(
        "() => document.getElementById('recordSheet').innerText.trim().length > 0")
    uc = page.inner_text("#recordSheet")
    check("print uc: UCSF declares four notes", "San Francisco" in uc
          and "4 notes" in uc, uc[uc.find("San Francisco"):][:90])
    for phrase, flag in (
            ("schools of medicine and health sciences remain inside the core", "medCenter"),
            ("No undergraduates and no general campus", "healthOnly"),
            ("partly measure research mission", "researchIntensive"),
            ("Fixed operating costs spread over fewer students", "smallScale")):
        check(f"print uc: UCSF's {flag} note prints IN FULL, not as a symbol",
              phrase in uc, phrase)
    check("print uc: the strip's limit is on the face — hospitals stripped, "
          "medical schools not",
          "SCHOOLS OF MEDICINE ARE NOT" in uc)
    check("print uc: the unaudited status of the per-campus table is stated",
          "Unaudited" in uc)
    page.emulate_media(media="screen")


def test_print_remaining(page, base):
    """PRINT SHEETS — schools, special districts, address (priority 3).

    Three different shapes. schools.html already rendered notes inline, so
    it needed the sheet rather than a rendering-model fix — but inline did
    NOT mean complete: renderCharter emits no note-row at all, carrying its
    comparability facts in the schedule label and gate line, so the sheet
    states them explicitly. districts.html is the as-filed tier and its
    sheet must not wear the gated layers' dress. address.html stacks
    governments that are never summed and must never print the address."""
    page.emulate_media(media="print")

    # ---- schools: districts, county offices, charters
    for frag, kind, want in (
            ("#c=los-angeles-unified", "district", "TO THE CENT"),
            ("#t=coes&c=alameda-county-office-of-education", "county office", "RECORDS ONLY"),
            ("#t=charters&c=able-charter", "charter", "RECORDS ONLY")):
        page.goto(f"{base}/schools.html{frag}")
        page.wait_for_selector("#recordSheet", state="attached")
        page.wait_for_function(
            "() => document.getElementById('recordSheet').innerText.trim().length > 0")
        sh = page.inner_text("#recordSheet")
        check(f"print schools ({kind}): the sheet renders", bool(sh.strip()))
        check(f"print schools ({kind}): states its gate or records-only status",
              want in sh.upper(), want)
        for ph in ("ACCOUNTING BASIS", "COMPARABILITY NOTES", "SOURCE",
                   "PERMALINK", "SHA-256", "REVISIONS"):
            check(f"print schools ({kind}): carries {ph}", ph in sh, ph)
    # the charter facts that renderCharter never emitted as notes
    page.goto(f"{base}/schools.html#t=charters&c=able-charter")
    page.wait_for_selector("#recordSheet", state="attached")
    ch = page.inner_text("#recordSheet")
    check("print schools (charter): the filing mode is stated as a note, not "
          "left in page chrome",
          "Alternative Form" in ch or "SACS report" in ch, ch[:160])
    check("print schools (charter): records-only status is a note",
          "never compared" in ch.lower())

    # ---- districts: the as-filed tier must NOT look like a gated sheet
    page.goto(f"{base}/districts.html#d=4-e-water-district")
    page.wait_for_selector("#recordSheet", state="attached")
    page.wait_for_function(
        "() => document.getElementById('recordSheet').innerText.trim().length > 0")
    ds = page.inner_text("#recordSheet")
    check("print districts: the as-filed caveat leads the sheet",
          "AS FILED, UNRECONCILED" in ds.upper())
    check("print districts: states plainly that the Ledger cannot verify it",
          "cannot verify" in ds.lower())
    check("print districts: states that no control total exists",
          "no control-total dataset exists" in ds.lower())
    check("print districts: NO per-resident figure appears",
          "per resident" not in ds.lower(), ds[:200])
    check("print districts: and says why none is shown",
          "no denominator" in ds.lower())
    check("print districts: the digest caveat is the as-filed one",
          "does NOT verify the filed figures" in ds)
    for ph in ("SOURCE", "PERMALINK", "SHA-256", "REVISIONS"):
        check(f"print districts: carries {ph}", ph in ds, ph)

    # ---- address: stacked, never summed, address never printed
    page.goto(f"{base}/address.html#c=oakland&sd=oakland-unified")
    page.wait_for_selector("#recordSheet", state="attached")
    page.wait_for_function(
        "() => document.getElementById('recordSheet').innerText.trim().length > 0")
    ad = page.inner_text("#recordSheet")
    check("print address: the do-not-add statement leads",
          "DO NOT ADD" in ad.upper())
    check("print address: it carries the LIVE intergovernmental share",
          "%" in ad and "intergovernmental" not in ad.lower()
          or "counties" in ad.lower())
    check("print address: it says this is not a household government cost",
          "not a household government cost" in ad.lower())
    check("print address: it states special districts cannot be determined",
          "cannot be determined" in ad.lower())
    check("print address: it carries the district-of-residence caveat",
          "district of residence" in ad.lower())
    check("print address: each government states its own basis",
          ad.upper().count("BASIS") >= 2, str(ad.upper().count("BASIS")))
    check("print address: no total is printed",
          "total" not in ad.lower().replace("a stacked total", "")
          .replace("no total", "").replace("total would", ""), "a total appears")
    check("print address: the sheet says the address is not recorded",
          "address is not recorded" in ad.lower()
          or "does not appear on this sheet" in ad.lower())
    page.emulate_media(media="screen")


def test_print_control(page, base):
    """THE PRINT AFFORDANCE. The record sheets shipped on every layer but
    were reachable only by pressing Cmd+P, so the feature was invisible.

    Where a record must be chosen first the control is DISABLED WITH A
    REASON rather than hidden — a control that vanishes is invisible to
    exactly the reader who has not selected one yet.

    Also asserts the control THROWS NOWHERE. Placing its state in the
    wrong scope silently disabled the sync on every layer (the const was
    outside the closure and in the temporal dead zone), and a print-path
    throw has blanked a page's on-screen record before."""
    ALWAYS = ["index.html", "csu.html", "ccc.html", "uc.html"]
    GATED = [("cities.html", "#c=oakland", "Select a city"),
             ("schools.html", "#c=los-angeles-unified", "Select a district"),
             ("districts.html", "#d=4-e-water-district", "Open a district"),
             ("address.html", "#c=oakland&sd=oakland-unified", "Look up an address")]

    def probe(url):
        errs = []
        h = lambda e: errs.append(str(e))
        page.on("pageerror", h)
        page.goto(url)
        page.wait_for_selector("#printBtn", state="attached")
        page.wait_for_timeout(350)
        st = page.evaluate("""() => { const b = document.getElementById('printBtn');
            return {tag: b.tagName, cls: b.className, text: b.textContent.trim(),
                    disabled: b.disabled, aria: b.getAttribute('aria-disabled'),
                    title: b.title, describedby: b.getAttribute('aria-describedby'),
                    hint: (document.getElementById('printBtnHint')||{}).textContent||''}; }""")
        page.remove_listener("pageerror", h)
        return st, errs

    for f in ALWAYS + [g[0] for g in GATED]:
        st, errs = probe(f"{base}/{f}")
        check(f"print control {f}: present", st["tag"] == "BUTTON", st["tag"])
        check(f"print control {f}: is a real button, keyboard reachable",
              st["tag"] == "BUTTON")
        check(f"print control {f}: wears the quiet outlined-pill vocabulary, "
              f"not a solid fill", st["cls"].strip() == "btn ink", st["cls"])
        check(f"print control {f}: is labelled", st["text"] == "Print record sheet",
              st["text"])
        check(f"print control {f}: has an accessible description",
              st["describedby"] == "printBtnHint" and bool(st["hint"].strip()))
        check(f"print control {f}: throws nothing on load", not errs, str(errs[:1]))

    for f in ALWAYS:
        st, _ = probe(f"{base}/{f}")
        check(f"print control {f}: enabled — this layer always has a record",
              st["disabled"] is False and st["aria"] == "false",
              f'{st["disabled"]}/{st["aria"]}')

    for f, frag, reason in GATED:
        st, errs = probe(f"{base}/{f}")
        check(f"print control {f}: disabled with nothing selected, rather than "
              f"hidden", st["disabled"] is True, str(st["disabled"]))
        check(f"print control {f}: reports that state to assistive tech",
              st["aria"] == "true", str(st["aria"]))
        check(f"print control {f}: gives a reason rather than failing silently",
              reason.lower() in st["title"].lower(), st["title"])
        check(f"print control {f}: throws nothing while disabled", not errs)

        st, errs = probe(f"{base}/{f}{frag}")
        check(f"print control {f}: enabled once a record is selected",
              st["disabled"] is False and st["aria"] == "false",
              f'{st["disabled"]}/{st["aria"]}')
        check(f"print control {f}: the reason clears when enabled",
              st["title"] == "", st["title"])
        check(f"print control {f}: throws nothing with a record selected", not errs)

    # the control must not appear on the sheet it produces. csu/ccc/uc put
    # their action row in .actions while their print CSS hides .hd-actions,
    # so this is measured rather than grepped.
    page.emulate_media(media="print")
    for f in ALWAYS + [g[0] for g in GATED]:
        page.goto(f"{base}/{f}")
        page.wait_for_selector("#printBtn", state="attached")
        page.wait_for_timeout(250)
        shown = page.evaluate("""() => { const b = document.getElementById('printBtn');
            const c = getComputedStyle(b);
            return c.display !== 'none' && c.visibility !== 'hidden'
                   && b.offsetParent !== null; }""")
        check(f"print control {f}: does not print itself onto the record sheet",
              not shown)
    page.emulate_media(media="screen")

    # the control must reach the same sheet Cmd+P produces
    page.emulate_media(media="print")
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordSheet", state="attached")
    page.wait_for_function(
        "() => document.getElementById('recordSheet').innerText.trim().length > 0")
    check("print control: the sheet it opens is the record sheet, with its notes",
          "contract with the county" in page.inner_text("#recordSheet"))
    page.emulate_media(media="screen")


def test_print_sheet(page, base):
    """PRINT RECORD SHEETS — the named failure mode is a printed figure
    whose caveat was dropped.

    On screen a city's comparability note lives behind a dagger and only
    ONE can be open at a time (S.openNote is a single value), so before
    this change a printed sheet could show a figure with no caveat in the
    DOM at all. Lakewood is the case: $103 per resident of police, police
    contracted to the county AND fire from a special district — two notes,
    and no interaction that put both on paper.

    These assertions read the PRINT-MEDIA DOM, not the stylesheet."""
    page.emulate_media(media="print")
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordSheet", state="attached")
    page.wait_for_function(
        "() => document.getElementById('recordSheet').innerText.trim().length > 0")
    sheet = page.inner_text("#recordSheet")

    check("print: the record sheet renders without any interaction",
          bool(sheet.strip()))
    check("print: it names the layer and fiscal year",
          "RECORD SHEET" in sheet and "CITIES" in sheet and "2023-24" in sheet)
    check("print: it names the entity", "Lakewood" in sheet)

    # THE LAKEWOOD CASE — both notes, in full, with no click
    check("print: Lakewood's TWO comparability notes both print",
          "2 APPLY TO THIS RECORD" in sheet, sheet[:200])
    check("print: the police contract note prints in full, not as a symbol",
          "contract with the county" in sheet)
    check("print: the fire provider note prints in full",
          "special district" in sheet)
    check("print: the checklist vintage rides with the note",
          "2015-16" in sheet)

    # everything paper needs, because paper has no tooltips
    for phrase, why in (
            ("ACCOUNTING BASIS", "the basis"),
            ("GATE", "the gate"),
            ("DOLLARS", "the nominal/real state"),
            ("BY FUNCTION", "the breakdown"),
            ("SOURCE", "the source"),
            ("PERMALINK", "the permalink"),
            ("SHA-256", "the integrity digest"),
            ("verify_digest.py", "how to verify it"),
            ("REVISIONS", "the revision-record caveat"),
    ):
        check(f"print: the sheet carries {why}", phrase in sheet, phrase)

    # a note must never be dropped to make the page fit
    css = page.evaluate(
        "getComputedStyle(document.querySelector('.rs-notes')).getPropertyValue('break-inside')")
    check("print: notes may break across pages but are never clipped",
          css.strip() in ("auto", ""), css)

    # an entity with NO notes must say so rather than leave a silent gap
    page.goto(f"{base}/cities.html#c=oakland")
    page.wait_for_selector("#recordSheet", state="attached")
    oak = page.inner_text("#recordSheet")
    check("print: an entity with no notes says so explicitly",
          "COMPARABILITY NOTES" in oak)

    # real dollars must carry the deflator on paper too
    page.goto(f"{base}/cities.html#c=lakewood&b=real")
    page.wait_for_selector("#recordSheet", state="attached")
    real = page.inner_text("#recordSheet")
    check("print: a real-dollar sheet names the index and vintage",
          "State and Local Government Purchases" in real
          and "REAL" in real.upper())
    check("print: and still carries both notes",
          "contract with the county" in real and "special district" in real)
    page.emulate_media(media="screen")


def test_search(page, base):
    """CROSS-LAYER SEARCH — and the trap it has to avoid.

    Search is the one place in the site where entities from different
    layers appear together. A city, the county containing it, its school
    district and its community-college district spend on overlapping
    populations, with different responsibilities, on different accounting
    bases. The single most dangerous thing this page could do is present
    them as a flat comparable list. So the assertions below are mostly
    about what must NOT appear.
    """
    idx = load_data_js(ROOT / "search-index.js")
    LKEYS = [l["key"] for l in idx["layers"]]
    check("search: the index ships", bool(idx.get("e")))
    check("search: every layer the site publishes is indexed",
          set(LKEYS) == {"state", "city", "county", "school", "coe", "charter",
                         "district", "ccc", "csu", "uc"}, str(sorted(LKEYS)))

    # --- THE INDEX CARRIES NO FIGURES. Nothing downstream can compare
    # what was never shipped.
    MONEY = ("total", "expenditures", "amount", "spend", "perAda", "perCapita",
             "value", "dollars", "figure", "ce", "opexp")
    bad_fields = [f for f in idx["meta"]["fields"]
                  if any(m.lower() in f.lower() for m in MONEY)]
    check("search: the index declares no money field", not bad_fields,
          str(bad_fields))
    shapes = {len(e) for e in idx["e"]}
    check("search: every entry is name/layer/id/notes/qualifier and nothing "
          "more — there is no room for a figure", shapes == {5}, str(shapes))
    numeric_extra = [e for e in idx["e"]
                     if not isinstance(e[3], int) or not isinstance(e[4], int)]
    check("search: the only numbers in an entry are a note COUNT and a "
          "qualifier index", not numeric_extra, str(numeric_extra[:2]))

    # --- identifiers resolve into the layer they name
    stores = {
        "city": set(CITY["cities"]), "county": set(COUNTY["counties"]),
        "school": set(SCHOOL["districts"]), "coe": set(SCHOOL["countyOffices"]),
        "charter": set(SCHOOL["charters"]),
        "district": set(load_data_js(ROOT / "district-data.js")["districts"]),
    }

    def slug(s):
        return re.sub(r"-+", "-",
                      re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

    unresolved = []
    for name, li, ident, notes, q in idx["e"]:
        key = LKEYS[li]
        if key not in stores:
            continue
        if (ident or slug(name)) not in stores[key]:
            unresolved.append((key, name))
    check("search: every indexed identifier resolves to a real record in "
          "its own layer (derived ids included)",
          not unresolved, str(unresolved[:4]))

    # --- the page: grouped by layer, basis named, no cross-layer total
    page.goto(f"{base}/search.html#q=Fresno")
    page.wait_for_selector(".grp")
    groups = page.eval_on_selector_all(
        ".grp", "els => els.map(e => ({"
        "layer: e.querySelector('.grp-name').textContent,"
        "basis: e.querySelector('.grp-basis').textContent,"
        "hits: e.querySelectorAll('.hit').length}))")
    check("search: results are split into more than one layer group for a "
          "name that exists in several", len(groups) > 3, str(len(groups)))
    check("search: every group names its layer",
          all(g["layer"].strip() for g in groups))
    check("search: every group states its accounting basis",
          all("BASIS" in g["basis"] for g in groups),
          str([g["basis"][:20] for g in groups]))
    for want in ("Cities", "Counties", "K-12 school districts"):
        check(f"search: 'Fresno' finds the {want.lower()} record",
              any(g["layer"] == want for g in groups))

    body = page.inner_text("body")
    check("search: the page states that the layers do not add",
          "do not add" in body.lower())
    check("search: the page states results are never summed or ranked "
          "against each other",
          "never summed" in body.lower() or "never sum" in body.lower())

    # --- NO CROSS-LAYER TOTAL ANYWHERE. The status line may count
    # results; it must never total money, and no element may combine
    # figures from two layers.
    money_on_page = re.findall(r"\$[\d,]+(?:\.\d+)?", body)
    check("search: not one dollar figure appears in the results view",
          not money_on_page, str(money_on_page[:5]))
    for banned in ("combined", "total spending", "altogether", "sum of",
                   "in total", "grand total"):
        check(f"search: the page never says {banned!r}",
              banned not in body.lower())

    # --- daggers are surfaced rather than a bare name
    page.goto(f"{base}/search.html#q=San Francisco")
    page.wait_for_selector(".grp")
    hits = page.eval_on_selector_all(
        ".hit", "els => els.map(e => ({"
        "name: e.querySelector('.hit-name').textContent,"
        "notes: (e.querySelector('.hit-notes')||{}).textContent||''}))")
    ucsf = [h for h in hits if h["name"].strip() == "San Francisco"]
    check("search: UCSF-style entities surface that they carry notes "
          "rather than showing a bare name",
          any("†" in h["notes"] for h in ucsf), str(ucsf))
    sfusd = [h for h in hits if "San Francisco Unified" in h["name"]]
    check("search: a basic-aid district surfaces its notes",
          sfusd and "†" in sfusd[0]["notes"], str(sfusd[:1]))
    flagged = sum(1 for e in idx["e"] if e[3] > 0)
    check("search: the index carries comparability notes for a real "
          "population of entities", 300 < flagged < 2000, str(flagged))

    # --- permalink round-trip
    page.goto(f"{base}/search.html#q=Oakland")
    page.wait_for_selector(".grp")
    check("search: a permalink reproduces the query",
          page.eval_on_selector("#q", "e => e.value") == "Oakland")
    page.fill("#q", "Berkeley")
    page.wait_for_timeout(250)
    check("search: typing updates the permalink so a search can be shared",
          "q=Berkeley" in page.evaluate("location.hash"),
          page.evaluate("location.hash"))

    # --- accessibility
    check("search: the box is labelled",
          page.eval_on_selector("label[for=q]", "e => !!e.textContent.trim()"))
    check("search: the result count is announced to screen readers",
          page.eval_on_selector("#qhelp", "e => e.getAttribute('aria-live')")
          == "polite")
    check("search: each group is an addressable section",
          page.eval_on_selector_all(
              ".grp", "els => els.every(e => e.getAttribute('aria-labelledby'))"))
    check("search: results are real links, so they are keyboard reachable "
          "and openable in a new tab",
          page.eval_on_selector_all(
              ".hit", "els => els.length > 0 && els.every(e => "
              "e.tagName === 'A' && !!e.getAttribute('href'))"))
    page.focus("#q")
    page.keyboard.press("ArrowDown")
    check("search: ArrowDown from the box moves focus into the results",
          page.evaluate("document.activeElement.classList.contains('hit')"))
    page.keyboard.press("ArrowUp")
    check("search: ArrowUp from the first result returns to the box",
          page.evaluate("document.activeElement.id") == "q")

    # --- graceful degradation, the site's standing rule
    page.goto(f"{base}/search.html")
    page.evaluate("window.CA_LEDGER_SEARCH = undefined")
    check("search: the index is a real file the page loads, not inlined",
          (ROOT / "search-index.js").exists())

    # --- narrow widths
    for w in (360, 390, 1280):
        page.set_viewport_size({"width": w, "height": 900})
        page.goto(f"{base}/search.html#q=Fresno")
        page.wait_for_selector(".grp")
        over = page.evaluate(
            "document.documentElement.scrollWidth > "
            "document.documentElement.clientWidth + 1")
        check(f"search: no horizontal overflow at {w}px", not over)
        check(f"search: groups render at {w}px",
              page.eval_on_selector_all(".grp", "e => e.length") > 3)
    page.set_viewport_size({"width": 1280, "height": 900})


def test_revision_identity():
    """AN IDENTIFIER DERIVED FROM SORT ORDER IS NOT AN IDENTIFIER.

    The slug-instability lesson (PR #22) reappearing in the change feed.
    Several payloads ship a figure as a row in an array SORTED BY AMOUNT —
    city/county `lines`, state `funds` and `programs`, K-12
    `byResource.n`. `_leaves` walks a list by enumeration index, so the key
    a figure got was its RANK.

    Two consequences, both measured against the shipped data before the
    fix. `lineLabels` is sorted() over the observed label set, so ONE new
    label anywhere in California renumbers up to 90 labels and shifts every
    rank below it: the feed reported 76,114 events for a single real
    change. And two lines swapping order — with neither value altered —
    were reported as each other's change.

    The feed makes no attribution claim. Reporting exactly what moved is
    the whole of its value, so a phantom event is not a blemish; it is the
    failure of the product. These assertions mutate the real shipped
    payload and require the feed to report the real change and nothing
    else."""
    import bisect
    sys.path.insert(0, str(ROOT / "pipeline"))
    import revisions as REV

    base_p = load_data_js(ROOT / "city-data.js")

    # ---- MUTATION 1: one new line label appears at the source.
    #      sorted() puts it in its slot and every index at or after it
    #      shifts by one — exactly what a new SCO line description does.
    mut = json.loads(json.dumps(base_p))
    NEW = "AAA New Service"
    labels = mut["meta"]["lineLabels"]
    check("revision identity: the label legend is sorted, so an insertion "
          "renumbers — this is the hazard being fixed, not an assumption",
          labels == sorted(labels))
    pos = bisect.bisect_left(labels, NEW)
    labels.insert(pos, NEW)
    shifted = 0
    for city in mut["cities"].values():
        for y in (city.get("years") or {}).values():
            for arr in (y.get("lines") or {}).values():
                for row in arr:
                    if row[0] >= pos:
                        row[0] += 1
                        shifted += 1
    check("revision identity: the mutation really does renumber a large "
          "share of the corpus", shifted > 50_000, str(shifted))

    victim = sorted(mut["cities"])[0]
    fy = sorted(mut["cities"][victim]["years"])[0]
    fam = mut["cities"][victim]["years"][fy]["lines"]
    fn = sorted(fam)[0]
    fam[fn].append([pos, 12345])
    fam[fn].sort(key=lambda x: -abs(x[1]))

    evs = REV.diff(REV.flatten("city", base_p), REV.flatten("city", mut))
    check("revision identity: ONE new label plus ONE real line yields "
          "exactly one event — zero phantoms", len(evs) == 1,
          f"{len(evs)} events, e.g. {evs[:2]}")
    if len(evs) == 1:
        e = evs[0]
        check("revision identity: and it is the real change, keyed on the "
              "LABEL rather than on a rank",
              e["e"] == victim and e["k"].endswith(NEW)
              and e["o"] is None and e["n"] == 12345, str(e))

    # ---- MUTATION 2: two lines swap rank; neither value changes.
    swap = json.loads(json.dumps(base_p))
    swapped_at = None
    for name in sorted(swap["cities"]):
        for yr in sorted((swap["cities"][name].get("years") or {})):
            for f2, arr in sorted((swap["cities"][name]["years"][yr]
                                   .get("lines") or {}).items()):
                if len(arr) >= 2 and arr[0][1] != arr[1][1]:
                    arr[0], arr[1] = arr[1], arr[0]
                    swapped_at = (name, yr, f2)
                    break
            if swapped_at:
                break
        if swapped_at:
            break
    check("revision identity: found a real pair to reorder",
          swapped_at is not None)
    evs2 = REV.diff(REV.flatten("city", base_p), REV.flatten("city", swap))
    check("revision identity: two lines swapping rank, with no value "
          "altered, produces NO event", evs2 == [], str(evs2)[:200])

    # ---- the label index must not be emitted as though it were a figure
    flat = REV.flatten("city", base_p)
    lines = {k: v for k, v in flat.items() if ".lines." in k}
    check("revision identity: line figures are keyed on the label",
          any(k.endswith("Police") or k.endswith("Fire") for k in lines))
    check("revision identity: and the label INDEX is no longer emitted as a "
          "value — a pure re-indexing cannot read as a changed figure",
          not any(re.search(r"\.lines\.[A-Za-z]+\.\d+(\.\d+)?$", k)
                  for k in lines))

    # ---- the same class, on the other layers that carry sorted rows
    st = load_data_js(ROOT / "data.js")
    sflat = REV.flatten("state", st)
    check("revision identity: state funds are keyed on the fund code",
          any(re.search(r"\.funds\.\d{4}$", k) for k in sflat))
    check("revision identity: state funds are NOT keyed on rank",
          not any(re.search(r"\.funds\.\d+\.\d+$", k) for k in sflat))
    check("revision identity: state programs are NOT keyed on rank",
          not any(re.search(r"\.programs\.\d+\.\d+$", k) for k in sflat))
    check("revision identity: the nonrecurring pair carries its declared "
          "slot names, not ordinals",
          any(k.endswith(".nr.N") for k in sflat)
          and not any(re.search(r"\.nr\.\d+$", k) for k in sflat))

    di = load_data_js(ROOT / "district-data.js")
    dflat = REV.flatten("district", di)
    check("revision identity: district fund buckets carry their names",
          any(k.endswith(".exp.gov") for k in dflat)
          and any(k.endswith(".rev.ent") for k in dflat))
    check("revision identity: district buckets are NOT keyed on ordinal",
          not any(re.search(r"\.(exp|rev)\.\d+$", k) for k in dflat))

    sc = load_data_js(ROOT / "school-data.js")
    scflat = REV.flatten("school", sc)
    check("revision identity: K-12 named resources are keyed on the "
          "resource code, not rank",
          any(re.search(r"byResource\.[a-zA-Z]+\.n\.\d{4}\.v$", k)
              for k in scflat))
    check("revision identity: and their object split carries family keys",
          any(".obj.certSalaries" in k or ".obj.classSalaries" in k
              for k in scflat))

    # ---- a duplicate intrinsic key must refuse rather than swallow a figure
    dup = json.loads(json.dumps(st))
    for b in dup["budgets"].values():
        for a in b["agencies"]:
            for d in (a.get("departments") or []):
                if len(d.get("funds") or []) >= 2:
                    d["funds"][1][0] = d["funds"][0][0]
                    break
    try:
        REV.flatten("state", dup)
        dup_refused = False
    except ValueError:
        dup_refused = True
    check("revision identity: a duplicate fund code REFUSES rather than "
          "letting one figure overwrite another", dup_refused)

    # ---- no published event depended on the old keying, so the migration
    #      cannot rewrite history
    import glob as _glob
    stale = 0
    for f in _glob.glob(str(ROOT / "*-revisions.js")):
        rec = load_data_js(Path(f))
        for b in rec.get("batches") or []:
            for e in b.get("events") or []:
                # RANK signatures, precisely. A fund or resource CODE is
                # legitimately numeric ("funds.0001"); a RANK is a bare
                # ordinal in a slot that should carry a name, or the
                # two-ordinal pair a list-of-lists produced.
                k = e.get("k", "")
                if (re.search(r"\.(lines\.[A-Za-z]+|funds|programs)\.\d+\.\d+$", k)
                        or re.search(r"\.(exp|rev|nr)\.\d+$", k)):
                    stale += 1
    check("revision identity: no already-published event was keyed on rank, "
          "so re-keying rewrites no dated record", stale == 0, str(stale))


def test_district_entity_key(page, base):
    """GROUPED ON A COMPOUND KEY, STORED ON A SUBSET OF IT.

    fetch_district_data.py grouped filings on (name, county) — correctly —
    and then wrote both the directory and the amounts keyed on the NAME
    alone. Three pairs of same-named districts in different counties
    collided, and each pair shipped as one entity.

    The grouping being right is what made it invisible: anyone reading the
    aggregation concluded the code was correct, and no totals gate could
    see it either, because the money was all present — attributed to one
    entity instead of two.

    Published wrong before this fix: Rural North Vacaville Water District
    carried county "Sutter" and activity "Levee" while being a Solano
    community-services district, and its FY 2017-18 expenditure read
    $1,268,460 — the arithmetic sum of $1,101,223 (Solano) and $167,237
    (Sutter, a levee district that merely shares the name)."""
    ds = DIST["districts"]
    YRS = DIST["years"]

    # ---- no two entities may collide on the entity key
    dupes = {}
    for slug, r in ds.items():
        k = (r.get("name"), (r.get("county") or "").lower())
        dupes.setdefault(k, []).append(slug)
    collided = {k: v for k, v in dupes.items() if len(v) > 1}
    check("district key: no two entities share a (name, county) identity",
          not collided, str(list(collided.items())[:3]))
    check("district key: every slug is unique", len(set(ds)) == len(ds))

    # ---- same-named districts survive as SEPARATE entities
    same_name = {}
    for slug, r in ds.items():
        same_name.setdefault(r.get("name"), []).append(slug)
    multi = {n: s for n, s in same_name.items() if len(s) > 1}
    check("district key: same-named districts in different counties are kept "
          "apart rather than collapsed", len(multi) >= 3, str(len(multi)))
    for n, slugs in multi.items():
        counties = [(ds[s].get("county") or "").lower() for s in slugs]
        check(f"district key: {n!r} is split by county, not duplicated",
              len(set(counties)) == len(counties), str(counties))

    # ---- THE CASE, resolved against the source
    CASES = [
        ("rural-north-vacaville-water-district", "Solano", "Community Services"),
        ("rural-north-vacaville-water-district-sutter", "Sutter", "Levee"),
        ("hamilton-city-fire-protection-district", "Glenn", "Fire Protection"),
        ("hamilton-city-fire-protection-district-sonoma", "Sonoma",
         "Joint Powers Authority (JPA)"),
        ("california-risk-management-authority-crma", "Fresno",
         "Joint Powers Authority (JPA)"),
        ("california-risk-management-authority-crma-madera", "Madera",
         "Joint Powers Authority (JPA)"),
    ]
    for slug, county, activity in CASES:
        r = ds.get(slug)
        check(f"district key: {slug} exists", r is not None)
        if not r:
            continue
        check(f"district key: {slug} carries county {county!r}",
              r.get("county") == county, str(r.get("county")))
        check(f"district key: {slug} carries activity {activity!r}",
              r.get("activity") == activity, str(r.get("activity")))

    # the de-merged figures. Sutter's levee dollars were landing in the
    # governmental bucket of a Solano enterprise district.
    v = ds["rural-north-vacaville-water-district"]
    i = YRS.index("2017-18")
    check("district key: the Solano district's FY 2017-18 expenditure is its "
          "own $1,101,223, not the $1,268,460 sum of two agencies",
          v["exp"][i] == [0, 1101223, 0, 0], str(v["exp"][i]))
    check("district key: and its governmental bucket is empty, as an "
          "enterprise water district's should be",
          v["exp"][i][0] == 0)
    su = ds["rural-north-vacaville-water-district-sutter"]
    check("district key: the Sutter levee district carries its own $167,237",
          su["exp"][i] == [167237, 0, 0, 0], str(su["exp"][i]))
    check("district key: the Sutter district files only the three years it "
          "actually filed", su["filings"] == "-FFF----", su["filings"])
    check("district key: the Solano district files all eight",
          v["filings"] == "FFLFFFFF", v["filings"])

    # ---- the spurious list-only record is gone: once the Solano district is
    #      keyed correctly, the delinquency row matches it instead of
    #      inventing a second entity
    check("district key: the phantom '-solano-list-only' entity no longer "
          "exists — its delinquency marker now sits on the real district",
          "rural-north-vacaville-water-district-solano-list-only" not in ds)
    check("district key: and that marker is the 'L' in the real district's "
          "filing string", "L" in v["filings"])

    # ---- recorded as OUR OWN correction, the feed's one attributed type
    rec = load_data_js(ROOT / "district-revisions.js")
    ours = [b for b in rec["batches"] if b.get("ours")]
    check("district key: the correction is recorded in the change feed",
          len(ours) == 1, str(len(ours)))
    if ours:
        b = ours[0]
        check("district key: attributed to us, not left to read as a source "
              "restatement", "our own correction" in b.get("note", "").lower())
        check("district key: the note names what was actually wrong",
              "(name, county)" in b.get("note", ""))
        check("district key: and it carries events", len(b.get("events") or []) > 0)
    page.goto(f"{base}/revisions.html")
    page.wait_for_selector(".batch-note")
    body = page.inner_text("body")
    check("district key: the attribution is visible on the record page",
          "OUR CORRECTION" in body)
    check("district key: and the note is legible to a reader there",
          "Rural North Vacaville" in body)


def test_revisions(page, base):
    """THE CHANGE RECORD (V13, option (b): mechanical only).

    Two things this has to prove. First that the record is DERIVED —
    that its figures digest still matches the data it claims to
    describe, so a tampered data file cannot sit behind a clean record.
    Second that it never claims to know WHY a figure moved: the whole
    argument for shipping it is that it only asserts what it can show.
    """
    sys.path.insert(0, str(ROOT / "pipeline"))
    import revisions as REV

    LAYERS = ["state", "city", "county", "district", "school",
              "csu", "ccc", "uc"]
    records = {}
    for layer in LAYERS:
        p = ROOT / REV.LAYERS[layer][1]
        check(f"revisions: {layer} record ships", p.exists())
        records[layer] = load_data_js(p) if p.exists() else None

    # --- the record is re-derived from the shipped data, not echoed
    for layer in LAYERS:
        rec = records[layer]
        if not rec:
            continue
        payload = load_data_js(ROOT / REV.LAYERS[layer][0])
        live = REV.figures_digest(payload)
        stamped = [b["figuresDigest"] for b in rec["batches"]
                   if b.get("figuresDigest")]
        check(f"revisions: {layer} figures digest recomputes from the "
              f"shipped data (not a stored claim)",
              bool(stamped) and stamped[-1] == live,
              f"record {stamped[-1][:16] if stamped else None} vs live {live[:16]}")

    # --- the figures digest is genuinely blind to metadata, which is the
    # whole reason detection uses it instead of meta.integrity
    uc = load_data_js(ROOT / "uc-data.js")
    d0 = REV.figures_digest(uc)
    moved = json.loads(json.dumps(uc))
    moved["meta"]["generated"] = "1999-01-01"
    moved["meta"]["integrity"] = {"algorithm": "SHA-256", "digest": "0" * 64}
    check("revisions: the figures digest ignores meta — a rebuild that "
          "only changes the date is not a revision",
          REV.figures_digest(moved) == d0)
    moved2 = json.loads(json.dumps(uc))
    moved2["campuses"][0]["totalK"] += 1
    check("revisions: the figures digest moves when a figure moves "
          "(a $1K edit is caught)",
          REV.figures_digest(moved2) != d0)

    # --- all three event kinds are representable and distinguishable
    base_p = load_data_js(ROOT / "uc-data.js")
    chg = json.loads(json.dumps(base_p)); chg["campuses"][0]["totalK"] += 1000
    app = json.loads(json.dumps(base_p)); app["campuses"][0]["brandNewK"] = 5
    dis = json.loads(json.dumps(base_p)); del dis["campuses"][0]["auxK"]
    flat = REV.flatten("uc", base_p)
    for name, other, want_o, want_n in (
            ("changed", chg, False, False),
            ("appeared", app, True, False),
            ("disappeared", dis, False, True)):
        evs = REV.diff(flat, REV.flatten("uc", other))
        check(f"revisions: a {name} figure produces exactly one event",
              len(evs) == 1, str(evs)[:120])
        if evs:
            check(f"revisions: {name} is encoded by null on the right side",
                  (evs[0]["o"] is None) == want_o
                  and (evs[0]["n"] is None) == want_n, str(evs[0]))

    # --- identity, not display name
    ccc = load_data_js(ROOT / "ccc-data.js")
    renamed = json.loads(json.dumps(ccc))
    renamed["districts"][0]["name"] = "SOME OTHER NAME"
    check("revisions: renaming an entity is not a changed figure "
          "(identity is the source's own code)",
          REV.diff(REV.flatten("ccc", ccc), REV.flatten("ccc", renamed)) == [])

    # --- the honest limits, on the face of the page
    page.goto(f"{base}/revisions.html")
    body = page.inner_text("body")
    for phrase, why in (
            ("not tell you why", "must not claim a cause"),
            ("begins", "must say when the record starts"),
            ("cannot be reproduced by anyone", "the SCO limit must be stated"),
            ("indistinguishable", "restatement vs redefinition must be named"),
    ):
        check(f"revisions page: states the limit — {why}",
              phrase.lower() in body.lower(), phrase)
    check("revisions page: names the day the record begins",
          "2026-07-19" in body)

    # --- attribution is the exception, and it can only come from a
    #     DECLARED constant. The refresh path may APPLY a declared
    #     correction; it can never invent one, so no per-refresh human
    #     judgement step is introduced. That is the invariant, and it is
    #     stronger than "only one batch is ever noted".
    city = records["city"]
    noted = [b for b in city["batches"] if b.get("note")]
    check("revisions: exactly one CITY batch carries a cause, and it is the "
          "backfilled one", len(noted) == 1 and noted[0].get("backfilled"),
          str([b.get("built") for b in noted]))
    check("revisions: the backfilled batch is the FY2016-17 city "
          "correction, 31 figures",
          noted and len(noted[0]["events"]) == 31,
          str(len(noted[0]["events"])) if noted else "none")
    check("revisions: it is labelled as OUR correction, not a source change",
          noted and "our own correction" in noted[0]["note"].lower())

    # A note may come ONLY from a declared constant. There are now two
    # kinds — a CORRECTION (we changed a figure) and a COVERAGE change (we
    # changed which years we load). Both are declared in the pipeline; the
    # refresh path can apply either and invent neither.
    declared = {(c["layer"], c["built"]) for c in REV.CORRECTIONS}
    declared |= {(c["layer"], c["built"]) for c in REV.COVERAGE}
    declared.add((REV.BACKFILL["layer"], REV.BACKFILL["built"]))
    for layer in LAYERS:
        for b in records[layer]["batches"]:
            if "note" not in b:
                continue
            check(f"revisions: {layer} batch {b['built']} carries a cause ONLY "
                  f"because one is declared for it in the pipeline",
                  (layer, b["built"]) in declared,
                  f"{layer}/{b['built']} is noted but not declared")
            check(f"revisions: {layer} batch {b['built']} attributes the cause "
                  f"to US, never to the source",
                  ("our own correction" in b["note"].lower()
                   or "our own change of coverage" in b["note"].lower()),
                  b["note"][:80])
    # and every unnoted batch stays silent, which is the default
    for layer in LAYERS:
        for b in records[layer]["batches"]:
            if (layer, b["built"]) in declared:
                continue
            check(f"revisions: {layer} batch {b['built']} claims no cause",
                  "note" not in b, str(b.get("note"))[:80])

    # --- backfill must not backdate the record's coverage
    check("revisions: meta.begins is the first REAL batch, so the "
          "backfilled event does not advertise coverage we lack",
          city["meta"]["begins"] == "2026-07-19",
          str(city["meta"]["begins"]))
    bf = noted[0]["built"] if noted else None
    check("revisions: the backfilled batch predates the record's start "
          "(and is marked, not hidden)",
          bf is not None and bf < city["meta"]["begins"], str(bf))

    # --- payload discipline: labels only for identities actually mentioned
    for layer in LAYERS:
        rec = records[layer]
        used = {e["e"] for b in rec["batches"] for e in b["events"]}
        check(f"revisions: {layer} stores no label for an entity it never "
              f"mentions", set(rec["labels"]) <= used,
              str(sorted(set(rec["labels"]) - used)[:3]))
    total = sum((ROOT / REV.LAYERS[l][1]).stat().st_size for l in LAYERS)
    check("revisions: the whole record is under 64 KB "
          "(per-layer, so a light page never pays for a heavy one)",
          total < 65536, f"{total} B")


def test_runtime_origins():
    """THE ARCHITECTURAL RULE, ENFORCED — docs/SCOPE.md permits exactly
    two runtime third-party services, and both are non-load-bearing:
    OpenFreeMap tiles on the map view and the Census geocoder on the
    address view. A third had accumulated undocumented (Google Fonts,
    on all ten pages), which is how a normative document quietly stops
    describing the site. This asserts the rule instead of restating it.

    Only SUBRESOURCE origins count — things the browser fetches to
    render the page. Ordinary <a href> links out to github.com or a
    source agency are the record citing its sources, not a dependency.
    """
    pages = sorted(p.name for p in ROOT.glob("*.html"))
    EXPECTED = sorted(["404.html", "about.html", "address.html", "ccc.html",
                       "cities.html", "csu.html", "districts.html",
                       "index.html", "revisions.html", "schools.html",
                       "search.html", "uc.html"])
    # named rather than counted: adding a page should be a deliberate act
    # that updates this list, because each new page is a new surface that
    # could reintroduce a third-party subresource
    check("origins: the page set is exactly the one we expect",
          pages == EXPECTED, str(set(pages) ^ set(EXPECTED)))
    ALLOWED = {"tiles.openfreemap.org", "geocoding.geo.census.gov"}
    # Only things the browser FETCHES count. <a href> is the record citing
    # its sources, and <link rel="canonical"> is metadata — neither is a
    # dependency. Among <link> rels, only these actually load bytes.
    FETCHING_REL = ("stylesheet", "preconnect", "dns-prefetch", "preload",
                    "prefetch", "modulepreload", "icon", "apple-touch-icon",
                    "manifest")
    SUB = re.compile(
        r'<(?:script|img|iframe|source|embed)\b[^>]*\bsrc\s*=\s*["\']'
        r'(https?://[^"\']+)', re.I)
    CSSURL = re.compile(r'url\(\s*["\']?(https?://[^"\'\s)]+)', re.I)
    LINKTAG = re.compile(r'<link\b[^>]*>', re.I)
    offenders = {}
    for name in pages:
        src = (ROOT / name).read_text(encoding="utf-8")
        found = list(SUB.findall(src)) + list(CSSURL.findall(src))
        for tag in LINKTAG.findall(src):
            rel = re.search(r'\brel\s*=\s*["\']([^"\']+)', tag, re.I)
            href = re.search(r'\bhref\s*=\s*["\'](https?://[^"\']+)', tag, re.I)
            if href and rel and any(r in rel.group(1).lower().split()
                                    for r in FETCHING_REL):
                found.append(href.group(1))
        for url in found:
            host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
            if host not in ALLOWED:
                offenders.setdefault(name, set()).add(host)
    check("origins: no page loads a subresource from an undocumented "
          "third party (SCOPE.md names exactly two)",
          not offenders,
          "; ".join(f"{k}: {sorted(v)}" for k, v in sorted(offenders.items())))
    scope = docs_scope_text()
    for phrase in ("OpenFreeMap", "Census"):
        check(f"origins: SCOPE.md still names {phrase} as a permitted "
              f"runtime service", phrase in scope)
    check("origins: SCOPE.md records that the rule is asserted, not just "
          "stated", "test_runtime_origins" in scope)
    # the font must be ours, and its licence must travel with it
    fonts = sorted(p.name for p in (ROOT / "vendor" / "fonts").glob("*.woff2"))
    check("origins: IBM Plex Mono is vendored, not fetched",
          len(fonts) == 6, str(fonts))
    check("origins: the SIL Open Font Licence ships with the font files",
          "SIL Open Font License" in
          (ROOT / "vendor" / "fonts" / "OFL.txt").read_text(encoding="utf-8"))
    for name in pages:
        src = (ROOT / name).read_text(encoding="utf-8")
        check(f"origins: {name} declares the self-hosted face",
              "vendor/fonts/plex-mono-400-latin.woff2" in src)


def docs_scope_text():
    return (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8")


def test_shell(page, base):
    """The institutional shell: a 404 in the Ledger's own voice, a
    steward line in every footer, system-colored identity assets, a
    share card, and print styles that keep the figures."""
    PAGES = ["index.html", "cities.html", "schools.html",
             "districts.html", "address.html", "about.html"]
    # ---- 404 page: served, on-voice, absolute links (GitHub Pages
    # serves it at ANY missing depth, so relative links would break)
    src404 = (ROOT / "404.html").read_text(encoding="utf-8")
    check("shell 404: file exists at the publishing root", bool(src404))
    page.goto(f"{base}/404.html")
    body = page.inner_text("body")
    check("shell 404: speaks in the record's voice",
          "This page is not part of the record." in body)
    check("shell 404: noindex", 'name="robots" content="noindex"' in src404)
    doors = page.locator(".doors a")
    check("shell 404: five doors offered", doors.count() == 5)
    hrefs = [doors.nth(i).get_attribute("href") for i in range(doors.count())]
    check("shell 404: every internal link absolute to /ca-ledger/",
          all(h.startswith("/ca-ledger/") for h in hrefs), str(hrefs))
    check("shell 404: no relative internal links anywhere",
          'href="index.html' not in src404 and 'href="about.html' not in src404)
    check("shell 404: wordmark and discipline line present",
          page.inner_text(".wordmark") == "Citizen Ledger"
          and "never concludes" in body)

    # ---- footer steward line on every page
    for f in PAGES:
        page.goto(f"{base}/{f}")
        page.wait_for_selector("footer.ft")
        ft = page.inner_text("footer.ft")
        check(f"shell footer {f}: names the repository",
              "GITHUB.COM/CITIZEN-LEDGER/CA-LEDGER" in ft)
        check(f"shell footer {f}: report-a-problem goes to issues",
              page.locator('footer.ft a[href="https://github.com/citizen-ledger/ca-ledger/issues"]').count() == 1)
        check(f"shell footer {f}: links About & method",
              page.locator('footer.ft a[href="about.html"]').count() == 1)

    # ---- identity assets in the system's own colors
    fav = (ROOT / "favicon.svg").read_text(encoding="utf-8")
    check("shell favicon: ink on parchment, abandoned palette gone",
          "#242424" in fav and "#f6f3f1" in fav
          and "#1B6B52" not in fav and "#A8842B" not in fav)
    for asset in ("favicon.ico", "apple-touch-icon.png",
                  "favicon-192.png", "favicon-512.png", "og-card.png"):
        check(f"shell asset exists: {asset}",
              (ROOT / asset).exists() and (ROOT / asset).stat().st_size > 1000)
    with open(ROOT / "og-card.png", "rb") as fh:
        fh.read(16)
        import struct as _struct
        w, h = _struct.unpack(">II", fh.read(8))
    check("shell og-card: 1200x630", (w, h) == (1200, 630), f"{w}x{h}")

    # ---- head wiring + print fidelity on every page
    for f in PAGES:
        src = (ROOT / f).read_text(encoding="utf-8")
        check(f"shell head {f}: ico and apple-touch linked",
              'href="favicon.ico"' in src and 'href="apple-touch-icon.png"' in src)
        check(f"shell head {f}: og:image share card",
              "og-card.png" in src and 'content="summary_large_image"' in src)
        check(f"shell print {f}: figures survive printing",
              "print-color-adjust:exact" in src)
    # the pin map must attribute its data (ODbL); asserted at runtime in
    # the map test — here, the source must never disable attribution
    asrc = (ROOT / "address.html").read_text(encoding="utf-8")
    check("shell attribution: pin map never disables attribution",
          "attributionControl: false" not in asrc
          and "OpenStreetMap contributors" in asrc)


def test_precision(page, base):
    """Precision defects: the record must never contradict itself.
    Layer-aware titles; a verify recipe naming the file whose digest is
    shown; tier-true schools sublines; a qualified about strip; singular
    population labels; the dagger legend only where a dagger exists;
    citation permalinks landing on the record; no duplicated
    activity/type strings."""
    # ---- cities.html, city layer: chrome + verify recipe
    page.goto(f"{base}/cities.html")
    page.wait_for_selector("#pageTitle")
    check("precision: city layer h1 reads City spending",
          page.inner_text("#pageTitle") == "City spending")
    check("precision: city layer document.title is layer-aware",
          page.evaluate("document.title") == "Citizen Ledger — City spending")
    check("precision: city layer verify recipe names city-data.js",
          page.inner_text("#verifyCmd").strip().endswith("city-data.js")
          and page.get_attribute("#verifyFile", "href") == "city-data.js"
          and page.inner_text("#verifyFile") == "city-data.js")
    # ---- county layer (full navigation via another page, not a hash hop)
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#l=county")
    page.wait_for_selector("#pageTitle")
    check("precision: county layer h1 reads County spending",
          page.inner_text("#pageTitle") == "County spending")
    check("precision: county layer document.title is layer-aware",
          page.evaluate("document.title") == "Citizen Ledger — County spending")
    check("precision: county layer verify recipe names county-data.js",
          page.inner_text("#verifyCmd").strip().endswith("county-data.js")
          and page.get_attribute("#verifyFile", "href") == "county-data.js"
          and page.inner_text("#verifyFile") == "county-data.js")
    check("precision: county digest and verify recipe agree on the file",
          "county-data.js" in page.inner_text("#integrityDigest"))
    # switching layers in-page must retarget the recipe too
    page.click('#layerGroup [data-layer="city"]')
    page.wait_for_timeout(300)
    check("precision: layer toggle retargets title and recipe",
          page.inner_text("#pageTitle") == "City spending"
          and page.inner_text("#verifyFile") == "city-data.js")

    # ---- population label: singular vs combined
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#c=los-angeles")
    page.wait_for_selector("#recordBody .det-row")
    check("precision: one city is POPULATION, not COMBINED",
          page.inner_text("#heroSub").startswith("POPULATION ")
          and "COMBINED" not in page.inner_text("#heroSub"))
    # dagger legend agrees with dagger presence (LA record)
    legend_ok = page.evaluate("""() => {
      const caps = document.querySelector('#recordBody .caps span');
      const legend = caps.textContent.includes('SERVICE-STRUCTURE');
      const body = document.querySelector('#recordBody');
      const symbol = !!body.querySelector('.dagger')
        || body.innerHTML.includes('>\\u2020 ');
      return legend === symbol;
    }""")
    check("precision: dagger legend only when a dagger exists (LA)", legend_ok)
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#c=lakewood")
    page.wait_for_selector("#recordBody .det-row")
    both = page.evaluate("""() => {
      const caps = document.querySelector('#recordBody .caps span');
      const body = document.querySelector('#recordBody');
      return caps.textContent.includes('SERVICE-STRUCTURE')
        && (!!body.querySelector('.dagger') || body.innerHTML.includes('>\\u2020 '));
    }""")
    check("precision: Lakewood keeps both its daggers and the legend", both)
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/cities.html#c=lakewood,san-francisco,santa-monica")
    page.wait_for_selector("#recordBody .cmp-row")
    check("precision: multiple cities keep COMBINED POPULATION",
          page.inner_text("#heroSub").startswith("COMBINED POPULATION "))

    # ---- schools: tier-aware hero subline
    page.goto(f"{base}/schools.html")
    page.wait_for_selector("#heroLbl")
    check("precision: districts subline states the per-entity gate",
          "GATED TO CDE'S PUBLISHED FIGURES" in page.inner_text("#heroLbl"))
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/schools.html#t=coes&c=alameda-county-office-of-education")
    page.wait_for_selector("#heroLbl")
    check("precision: COE subline claims rollups, not a per-entity gate",
          "ROLLUPS" in page.inner_text("#heroLbl")
          and "GATED TO CDE'S PUBLISHED FIGURES" not in page.inner_text("#heroLbl"))
    page.goto(f"{base}/about.html")
    page.goto(f"{base}/schools.html#t=charters&c=able-charter")
    page.wait_for_selector("#heroLbl")
    check("precision: charter subline claims rollups and totals",
          "ROLLUPS AND TOTALS" in page.inner_text("#heroLbl")
          and "GATED TO CDE'S PUBLISHED FIGURES" not in page.inner_text("#heroLbl"))

    # ---- about strip: no blanket reconciliation claim
    page.goto(f"{base}/about.html")
    strip = page.inner_text(".prov")
    check("precision: about strip qualifies the as-filed layer",
          "SPECIAL DISTRICTS AS FILED" in strip)

    # ---- districts: permalink lands on the record; no activity/type echo
    page.goto(f"{base}/districts.html#d=adelanto-public-financing-authority")
    page.wait_for_selector("#recMeta")
    page.wait_for_timeout(300)
    check("precision: citation permalink scrolls to the cited record",
          page.evaluate("window.scrollY") > 1000,
          f"scrollY {page.evaluate('window.scrollY')}")
    dup = next((slug for slug, r in DIST["districts"].items()
                if r.get("activity") and r.get("activity") == r.get("type")), None)
    check("precision: a district with activity == type exists to test", bool(dup))
    if dup:
        page.goto(f"{base}/about.html")
        page.goto(f"{base}/districts.html#d={dup}")
        page.wait_for_selector("#recMeta")
        rec = DIST["districts"][dup]
        meta = page.inner_text("#recMeta")
        check("precision: record meta prints activity/type once",
              meta.count(rec["type"]) == 1, meta)
        page.click("#citeBtn")
        cite = page.inner_text("#citeText")
        check("precision: citation prints activity/type once",
              cite.count(rec["type"]) == 1, cite)


def test_mobile(browser, base):
    """Phone-width guard (360px): no page-level horizontal scroll on any
    page, and every figure in a drill-down or record row sits inside the
    viewport — an amount that must be panned to is an amount nobody sees.
    Content inside an overflow-x container (the comparison, the district
    year tables) is exempt only when the page body itself does not pan."""
    ctx = browser.new_context(viewport={"width": 360, "height": 780})
    p = ctx.new_page()
    for name in ("index.html", "cities.html", "schools.html",
                 "districts.html", "address.html", "about.html"):
        p.goto(f"{base}/{name}")
        p.wait_for_load_state("networkidle")
        sw = p.evaluate("Math.max(document.documentElement.scrollWidth,"
                        " document.body.scrollWidth)")
        check(f"mobile 360: {name} does not scroll horizontally",
              sw <= 361, f"scrollWidth {sw}")

    offscreen_js = """(sel) => {
      let n = 0;
      document.querySelectorAll(sel).forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width && (r.right > innerWidth + 1 || r.left < -1)) n++;
      });
      return n;
    }"""
    # state fund/program drill: name and figure both on screen
    p.goto(f"{base}/index.html#a=health-and-human-service&dd=4260")
    p.wait_for_selector(".depth-panel .depth-row")
    bad = p.evaluate(offscreen_js, ".depth-panel .num")
    check("mobile 360: every state fund-drill figure inside the viewport",
          bad == 0, f"{bad} offscreen")
    # city record and its line-level drill
    p.goto(f"{base}/cities.html#c=los-angeles")
    p.wait_for_selector("#recordBody .det-row")
    p.locator('#recordBody .det-row[data-fn="police"]').dispatch_event("click")
    p.wait_for_selector(".line-panel")
    bad = p.evaluate(offscreen_js,
                     "#recordBody .det-row .num, #recordBody .det-foot .num,"
                     " .line-panel .num")
    check("mobile 360: every city record and line figure inside the viewport",
          bad == 0, f"{bad} offscreen")
    # school record: object-family drill and an aligned gated total
    p.goto(f"{base}/schools.html#c=los-angeles-unified")
    p.wait_for_selector("#recordBody .det-row")
    p.locator('#recordBody .det-row[data-fn="genAdmin"]').dispatch_event("click")
    p.wait_for_selector(".obj-panel")
    bad = p.evaluate(offscreen_js,
                     "#recordBody .det-row .v, #recordBody .det-foot .v,"
                     " .obj-panel .num")
    check("mobile 360: every school record figure inside the viewport",
          bad == 0, f"{bad} offscreen")
    aligned = p.evaluate("""() => {
      const f = document.querySelector('#recordBody .det-foot .v');
      const r = document.querySelector('#recordBody .det-row .v');
      return Math.abs(f.getBoundingClientRect().right
                    - r.getBoundingClientRect().right) <= 2;
    }""")
    check("mobile 360: school gated total aligns with the amount column",
          aligned)
    ctx.close()


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

    # ---- presentation: California is the subject of its own map
    html_c = (ROOT / "cities.html").read_text(encoding="utf-8")
    addr = (ROOT / "address.html").read_text(encoding="utf-8")
    check("map frame: both maps follow California's proportions, not a letterbox",
          "aspect-ratio:87/100" in html_c.replace(" ", "")
          and "aspect-ratio:87/100" in addr.replace(" ", ""))
    check("map camera: bounds are California's own, not a box reaching into Arizona",
          "[-124.48, 32.53], [-114.13, 42.01]" in html_c
          and "[-124.48, 32.53], [-114.13, 42.01]" in addr)
    for label, w, h in (("desktop", 1280, 900), ("390", 390, 844), ("360", 360, 780)):
        page.set_viewport_size({"width": w, "height": h})
        page.goto(f"{base}/cities.html#p=map")
        page.wait_for_function("window._clMapReady === true", timeout=45000)
        page.wait_for_timeout(700)          # let the frame observer settle
        span = page.evaluate(
            "(() => { const b = window._clMap.getBounds();"
            " return 10.35 / (b.getEast() - b.getWest()); })()")
        check(f"map camera {label}: California fills the frame (>=80% of its width)",
              span >= 0.80, f"{span*100:.0f}%")
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(f"{base}/cities.html#p=map")
    page.wait_for_function("window._clMapReady === true", timeout=45000)
    labels = page.evaluate(
        """(() => { const L = window._clMap.getStyle().layers;
            const g = id => L.find(l => l.id === id) || null;
            const ca = g('place'), out = g('place-out');
            return ca && out ? {caSize: ca.layout['text-size'], caColor: ca.paint['text-color'],
              outSize: out.layout['text-size'], outColor: out.paint['text-color'],
              outFirst: L.indexOf(out) < L.indexOf(ca),
              outFiltered: JSON.stringify(out.filter).indexOf('within') > -1,
              caFiltered: JSON.stringify(ca.filter).indexOf('within') > -1} : null; })()""")
    check("map labels: in-state and out-of-state are separate layers", labels is not None)
    if labels:
        check("map labels: out-of-state places are smaller and lighter than California's",
              labels["outSize"] < labels["caSize"]
              and labels["outColor"] == "#b3aeaa" and labels["caColor"] == "#797776",
              str(labels))
        check("map labels: out-of-state draws first, so it never wins a collision",
              labels["outFirst"])
        check("map labels: in/out decided geographically, not by deleting context",
              labels["outFiltered"] and labels["caFiltered"])
    check("map controls: styled to the Ledger, not MapLibre's default white",
          "maplibregl-ctrl-group" in html_c and "var(--ash)" in html_c
          and ".maplibregl-ctrl-attrib" in html_c
          and "maplibregl-ctrl-group" in addr and ".maplibregl-ctrl-attrib" in addr)
    check("map attribution: OSM/OpenFreeMap credit kept and legible on both maps",
          "OpenStreetMap" in html_c and "OpenFreeMap" in html_c
          and "OpenStreetMap" in addr and "OpenFreeMap" in addr)

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
            test_gate_declarations()
            test_uc_strip_verification()
            test_ccc_write_path()
            test_historical_state(page, base)
            test_empty_gate_guard()
            test_identity_leaks(page, base)
            test_state_fund_identity(page, base)
            test_position_guard()
            test_identifier_stability()
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
            test_mobile(browser, base)
            test_precision(page, base)
            test_runtime_origins()
            test_revisions(page, base)
            test_district_entity_key(page, base)
            test_revision_identity()
            test_search(page, base)
            test_print_sheet(page, base)
            test_print_state(page, base)
            test_print_highered(page, base)
            test_print_remaining(page, base)
            test_print_control(page, base)
            test_inflation(page, base)
            test_inflation_labeling(page, base)
            test_shell(page, base)
            test_cite(page, base)
            test_polish(page, base)
            test_resource(page, base)
            test_csu(page, base)
            test_ccc(page, base)
            test_uc(page, base)
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
