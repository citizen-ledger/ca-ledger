#!/usr/bin/env python3
"""
Generate city-geo.js — real boundaries for all 482 California cities.

    python3 pipeline/make_city_boundaries.py [--tolerance 0.35]

Source: U.S. Census Bureau cartographic boundary file
cb_2023_06_place_500k (public domain, 1:500,000), filtered to
incorporated places (LSAD 25 city / 43 town) — the same 482-place set
as the gazetteer. Parsing is the stdlib .shp/.dbf reader shared with
make_ca_outline.py; nothing beyond the standard library.

Geometry is projected with the SAME constants as the state outline
embedded in cities.html (so boundaries land on the same canvas), then
simplified with a hand-rolled Douglas-Peucker at --tolerance (in
viewBox units; 1 unit ≈ 1.37 km ground). Rings that collapse below
four points at the chosen tolerance are dropped as sub-tolerance.

MATCHING GATE: every one of the 482 cities in city-data.js must match
a boundary by the same normalization + alias rules proven for the
gazetteer, or this script exits with a named report and writes
nothing. No guesses, no silent drops.

Output: city-geo.js — window.CA_CITY_GEO = { meta, cities: { slug:
{ d: <svg path>, cx, cy, r } } } where cx/cy is the centroid of the
largest ring and r its effective radius (for the map's invisible
minimum hit-targets). meta.integrity carries the standard SHA-256
digest (verify with pipeline/verify_digest.py city-geo.js).
"""

import argparse
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import stamp                                     # noqa: E402
from make_ca_outline import read_dbf_records, read_shp_polygons  # noqa: E402
from fetch_city_data import _norm_place, GAZETTEER_ALIASES       # noqa: E402

URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_06_place_500k.zip"
# Projection constants — MUST match make_ca_outline.py output and the
# GEO object in cities.html.
GEO = dict(minLon=-124.409591, maxLat=42.009247, k=0.795773, scale=73.412348)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "city-geo.js"


def proj(lon, lat):
    return ((lon - GEO["minLon"]) * GEO["k"] * GEO["scale"],
            (GEO["maxLat"] - lat) * GEO["scale"])


def douglas_peucker(points, tolerance):
    """Iterative Douglas-Peucker on an open point list."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        best, best_i = -1.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            if seg2 == 0:
                d2 = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / seg2
                t = 0 if t < 0 else 1 if t > 1 else t
                d2 = (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2
            if d2 > best:
                best, best_i = d2, i
        if best > tolerance * tolerance:
            keep[best_i] = True
            stack.append((a, best_i))
            stack.append((best_i, b))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring, tolerance):
    """Ring comes closed (first == last). Simplify open part, re-close."""
    pts = ring[:-1] if ring[0] == ring[-1] else ring[:]
    out = douglas_peucker(pts, tolerance)
    return out if len(out) >= 4 else None    # sub-tolerance ring: drop


def ring_area_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a /= 2
    if abs(a) < 1e-9:
        x = sum(p[0] for p in ring) / len(ring)
        y = sum(p[1] for p in ring) / len(ring)
        return 0.0, x, y
    return abs(a), cx / (6 * a), cy / (6 * a)


def path_of(rings):
    parts = []
    for ring in rings:
        parts.append("M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in ring) + "Z")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Rebuild city-geo.js")
    ap.add_argument("--tolerance", type=float, default=0.35,
                    help="Douglas-Peucker tolerance in viewBox units "
                         "(1 unit ≈ 1.37 km); default 0.35")
    ap.add_argument("--dry-run", action="store_true",
                    help="report sizes without writing city-geo.js")
    args = ap.parse_args()

    # our 482 cities: name -> slug
    text = (ROOT / "city-data.js").read_text(encoding="utf-8")
    city_data = json.loads(text[text.index("=") + 1: text.rindex(";")])
    name_to_slug = {c["name"]: slug for slug, c in city_data["cities"].items()}

    print("Downloading " + URL, file=sys.stderr)
    req = urllib.request.Request(URL, headers={"User-Agent": "ca-ledger-pipeline/1.0"})
    data = urllib.request.urlopen(req, timeout=180).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    shp = z.read([n for n in z.namelist() if n.endswith(".shp")][0])
    dbf = z.read([n for n in z.namelist() if n.endswith(".dbf")][0])
    rows = read_dbf_records(dbf)
    shapes = read_shp_polygons(shp)

    # boundary lookup by normalized name (+ parenthetical alternates),
    # incorporated places only — the same rules as the gazetteer
    lookup = {}
    for r, s in zip(rows, shapes):
        if r.get("LSAD") not in ("25", "43"):
            continue
        base = r["NAME"].strip()
        try:   # the .dbf is UTF-8 (per its .cpg); the shared reader
               # decodes latin-1 — repair the round-trip (e.g. La Cañada)
            base = base.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        keys = {_norm_place(base)}
        m = re.match(r"^(.*)\((.*)\)\s*$", base)
        if m:
            keys.add(_norm_place(m.group(1)))
            keys.add(_norm_place(m.group(2)))
        for k in keys:
            lookup[k] = s

    unmatched, cities_out, total_pts = [], {}, 0
    for name, slug in sorted(name_to_slug.items()):
        k = _norm_place(name)
        s = lookup.get(GAZETTEER_ALIASES.get(k, k))
        if s is None:
            unmatched.append(name)
            continue
        projected = [[proj(lon, lat) for lon, lat in ring] for ring in s]
        simplified = [sr for sr in (simplify_ring(ring, args.tolerance)
                                    for ring in projected) if sr]
        if not simplified:   # keep at least the largest ring, minimally
            largest = max(projected, key=lambda rg: ring_area_centroid(rg)[0])
            simplified = [douglas_peucker(largest[:-1], 0)[:64]]
        area, cx, cy = max((ring_area_centroid(rg) for rg in simplified),
                           key=lambda t: t[0])
        total_pts += sum(len(rg) for rg in simplified)
        cities_out[slug] = {
            "d": path_of(simplified),
            "cx": round(cx, 1), "cy": round(cy, 1),
            "r": round(math.sqrt(area / math.pi), 1),
        }

    if unmatched:
        sys.exit("BOUNDARY MATCH FAILED for "
                 f"{len(unmatched)} city(ies) — nothing written:\n  "
                 + "\n  ".join(unmatched))

    payload = {
        "meta": {
            "source": "U.S. Census Bureau cartographic boundary file "
                      "cb_2023_06_place_500k (public domain), incorporated "
                      "places, equirectangular projection matching the state "
                      "outline",
            "generated": date.today().isoformat(),
            "toleranceViewboxUnits": args.tolerance,
        },
        "cities": cities_out,
    }
    stamp(payload)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    size = len(body) + 60
    print(f"{len(cities_out)} boundaries · {total_pts:,} points after "
          f"simplification (tolerance {args.tolerance}) · "
          f"payload ≈ {size / 1024:.0f} KB", file=sys.stderr)
    if args.dry_run:
        return
    header = ("/* GENERATED by pipeline/make_city_boundaries.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(header + "window.CA_CITY_GEO = " + body + ";\n",
                        encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
