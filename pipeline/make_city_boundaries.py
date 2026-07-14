#!/usr/bin/env python3
"""
Generate city-geo.js — real boundaries for all 482 California cities,
as GeoJSON for the MapLibre map overlay.

    python3 pipeline/make_city_boundaries.py [--tolerance 0.2]

Source: U.S. Census Bureau cartographic boundary file
cb_2023_06_place_500k (public domain, 1:500,000), filtered to
incorporated places (LSAD 25 city / 43 town) — the same 482-place set
as the gazetteer. Parsing is the stdlib .shp/.dbf reader shared with
make_ca_outline.py; nothing beyond the standard library.

Simplification: hand-rolled Douglas-Peucker run in the same projected
space as before (tolerance in viewBox units; 1 unit ≈ 1.37 km), then
the KEPT vertices are emitted in their original lon/lat (5 decimals,
≈1 m) — identical point selection to the SVG era, library-friendly
output. Rings are grouped into proper MultiPolygons: shapefile outer
rings are clockwise, holes counter-clockwise; each hole is nested
under the outer ring that contains it, so unincorporated islands
inside cities render as holes, not fills.

MATCHING GATE: every one of the 482 cities in city-data.js must match
a boundary by the same normalization + alias rules proven for the
gazetteer, or this script exits with a named report and writes
nothing. No guesses, no silent drops.

Feature properties are ONLY {slug, name, clng, clat, geoid} — no
financial fields, so the map style has no spending data to encode even
by accident (the test suite asserts this).

Output: city-geo.js — window.CA_CITY_GEO = { meta, type:
"FeatureCollection", features: [...] } with the standard SHA-256
integrity digest (verify with pipeline/verify_digest.py city-geo.js).
"""

import argparse
import io
import json
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
# Projection used ONLY for tolerance semantics during simplification —
# identical to the former SVG map, so the same points are kept.
GEO = dict(minLon=-124.409591, maxLat=42.009247, k=0.795773, scale=73.412348)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "city-geo.js"


def proj(lon, lat):
    return ((lon - GEO["minLon"]) * GEO["k"] * GEO["scale"],
            (GEO["maxLat"] - lat) * GEO["scale"])


def douglas_peucker_indices(points, tolerance):
    """Douglas-Peucker over projected points; returns kept INDICES."""
    n = len(points)
    if n < 3:
        return list(range(n))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
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
    return [i for i in range(n) if keep[i]]


def signed_area(ring):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2


def centroid_of(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a /= 2
    if abs(a) < 1e-12:
        return (sum(p[0] for p in ring) / len(ring),
                sum(p[1] for p in ring) / len(ring))
    return cx / (6 * a), cy / (6 * a)


def point_in_ring(pt, ring):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y):
            xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < xin:
                inside = not inside
    return inside


def simplify_city(rings_lonlat, tolerance):
    """Returns (multipolygon coords in lon/lat, largest-outer centroid)."""
    outers, holes = [], []
    for ring in rings_lonlat:
        pts = ring[:-1] if ring[0] == ring[-1] else ring[:]
        projected = [proj(lon, lat) for lon, lat in pts]
        kept = douglas_peucker_indices(projected, tolerance)
        if len(kept) < 4:
            continue
        out = [[round(pts[i][0], 5), round(pts[i][1], 5)] for i in kept]
        out.append(out[0])                       # close (GeoJSON requires it)
        # shapefile winding: outer rings clockwise (negative shoelace
        # area in lon/lat with y up), holes counter-clockwise
        (outers if signed_area(pts) < 0 else holes).append(out)
    if not outers:
        # degenerate at this tolerance: keep the largest raw ring coarsely
        largest = max(rings_lonlat, key=lambda rg: abs(signed_area(rg)))
        pts = largest[:-1] if largest[0] == largest[-1] else largest[:]
        step = max(1, len(pts) // 48)
        out = [[round(lon, 5), round(lat, 5)] for lon, lat in pts[::step]]
        out.append(out[0])
        outers = [out]
        holes = []
    polys = [[o] for o in outers]
    for h in holes:
        probe = tuple(h[0])
        for poly in polys:
            if point_in_ring(probe, [tuple(p) for p in poly[0][:-1]]):
                poly.append(h)
                break
        # a hole whose parent ring was dropped at tolerance is dropped too
    largest_outer = max(outers, key=lambda o: abs(signed_area([tuple(p) for p in o[:-1]])))
    clng, clat = centroid_of([tuple(p) for p in largest_outer[:-1]])
    return polys, round(clng, 4), round(clat, 4)


def main():
    ap = argparse.ArgumentParser(description="Rebuild city-geo.js (GeoJSON)")
    ap.add_argument("--tolerance", type=float, default=0.2,
                    help="Douglas-Peucker tolerance in projected viewBox "
                         "units (1 unit ≈ 1.37 km); default 0.2")
    ap.add_argument("--dry-run", action="store_true",
                    help="report sizes without writing city-geo.js")
    args = ap.parse_args()

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

    lookup = {}
    for r, s in zip(rows, shapes):
        if r.get("LSAD") not in ("25", "43"):
            continue
        # Census GEOID (state+place FIPS) rides along so the address
        # view can match the Census geocoder's place assignment by
        # identifier instead of re-doing name matching at runtime.
        s = {"shape": s, "geoid": (r.get("GEOID") or "").strip()}
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

    unmatched, features, total_pts = [], [], 0
    for name, slug in sorted(name_to_slug.items()):
        k = _norm_place(name)
        ent = lookup.get(GAZETTEER_ALIASES.get(k, k))
        if ent is None:
            unmatched.append(name)
            continue
        if not ent["geoid"]:
            unmatched.append(name + " (no GEOID in source)")
            continue
        polys, clng, clat = simplify_city(ent["shape"], args.tolerance)
        total_pts += sum(len(ring) - 1 for poly in polys for ring in poly)
        geometry = ({"type": "Polygon", "coordinates": polys[0]}
                    if len(polys) == 1 else
                    {"type": "MultiPolygon", "coordinates": polys})
        features.append({
            "type": "Feature",
            "properties": {"slug": slug, "name": name,
                           "clng": clng, "clat": clat,
                           "geoid": ent["geoid"]},
            "geometry": geometry,
        })

    if unmatched:
        sys.exit("BOUNDARY MATCH FAILED for "
                 f"{len(unmatched)} city(ies) — nothing written:\n  "
                 + "\n  ".join(unmatched))

    payload = {
        "meta": {
            "source": "U.S. Census Bureau cartographic boundary file "
                      "cb_2023_06_place_500k (public domain), incorporated "
                      "places, GeoJSON (lon/lat, 5 decimals)",
            "generated": date.today().isoformat(),
            "toleranceViewboxUnits": args.tolerance,
        },
        "type": "FeatureCollection",
        "features": features,
    }
    stamp(payload)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    size = len(body) + 60
    print(f"{len(features)} boundaries · {total_pts:,} points "
          f"(tolerance {args.tolerance}) · payload ≈ {size / 1024:.0f} KB",
          file=sys.stderr)
    if args.dry_run:
        return
    header = ("/* GENERATED by pipeline/make_city_boundaries.py on "
              f"{date.today().isoformat()} — do not edit by hand. */\n")
    OUT_PATH.write_text(header + "window.CA_CITY_GEO = " + body + ";\n",
                        encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
