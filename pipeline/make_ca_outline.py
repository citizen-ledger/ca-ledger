#!/usr/bin/env python3
"""
Generate the California outline embedded in cities.html.

    python3 pipeline/make_ca_outline.py

Downloads the U.S. Census Bureau cartographic boundary shapefile
(cb_2023_us_state_20m — public domain, 1:20,000,000 simplified),
extracts the California polygons with a dependency-free .shp/.dbf
reader, projects them with a plain equirectangular projection
(x scaled by cos of the mid-latitude), and prints:

  1. an SVG path string for the state outline, and
  2. the exact JS projection constants cities.html must use so that
     city dots (projected at runtime from lat/lng) land on the same
     canvas.

The output is pasted into cities.html — the page never fetches
anything at runtime. Re-run only if the source vintage changes.
"""

import io
import math
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip"
VIEW_W = 600.0          # SVG viewBox width; height derives from geometry
DECIMALS = 1            # path coordinate precision


def read_dbf_records(data):
    """Minimal dBASE III reader -> list of dicts (character fields)."""
    n_records = struct.unpack("<I", data[4:8])[0]
    header_size, record_size = struct.unpack("<HH", data[8:12])
    fields = []
    pos = 32
    while data[pos] != 0x0D:
        name = data[pos:pos + 11].split(b"\0")[0].decode("ascii")
        length = data[pos + 16]
        fields.append((name, length))
        pos += 32
    out = []
    for i in range(n_records):
        rec = data[header_size + i * record_size: header_size + (i + 1) * record_size]
        row, p = {}, 1   # first byte = deletion flag
        for name, length in fields:
            row[name] = rec[p:p + length].decode("latin-1").strip()
            p += length
        out.append(row)
    return out


def read_shp_polygons(data):
    """Minimal .shp reader -> list of records; each record is a list of
    rings; each ring a list of (lon, lat)."""
    records, pos = [], 100
    while pos < len(data):
        length = struct.unpack(">i", data[pos + 4:pos + 8])[0] * 2
        content = data[pos + 8: pos + 8 + length]
        shape_type = struct.unpack("<i", content[:4])[0]
        rings = []
        if shape_type in (5, 15, 25):        # Polygon variants
            num_parts, num_points = struct.unpack("<ii", content[36:44])
            parts = struct.unpack("<%di" % num_parts, content[44:44 + 4 * num_parts])
            pts_off = 44 + 4 * num_parts
            pts = struct.unpack("<%dd" % (num_points * 2),
                                content[pts_off: pts_off + 16 * num_points])
            coords = list(zip(pts[0::2], pts[1::2]))
            for i, start in enumerate(parts):
                end = parts[i + 1] if i + 1 < num_parts else num_points
                rings.append(coords[start:end])
        records.append(rings)
        pos += 8 + length
    return records


def main():
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "cb.zip"
        print("Downloading " + URL, file=sys.stderr)
        req = urllib.request.Request(URL, headers={"User-Agent": "ca-ledger-pipeline/1.0"})
        zpath.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        z = zipfile.ZipFile(zpath)
        shp = z.read([n for n in z.namelist() if n.endswith(".shp")][0])
        dbf = z.read([n for n in z.namelist() if n.endswith(".dbf")][0])

    rows = read_dbf_records(dbf)
    shapes = read_shp_polygons(shp)
    idx = next(i for i, r in enumerate(rows) if r.get("STATEFP") == "06")
    rings = shapes[idx]
    print(f"California: {len(rings)} ring(s), "
          f"{sum(len(r) for r in rings)} points", file=sys.stderr)

    lons = [p[0] for ring in rings for p in ring]
    lats = [p[1] for ring in rings for p in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    mid_lat = (min_lat + max_lat) / 2
    k = math.cos(math.radians(mid_lat))
    scale = VIEW_W / ((max_lon - min_lon) * k)
    view_h = (max_lat - min_lat) * scale

    def proj(lon, lat):
        return ((lon - min_lon) * k * scale, (max_lat - lat) * scale)

    d = []
    for ring in rings:
        pts = [proj(lon, lat) for lon, lat in ring]
        d.append("M" + " L".join(f"{x:.{DECIMALS}f} {y:.{DECIMALS}f}" for x, y in pts) + " Z")
    path = " ".join(d)

    print("<!-- Source: U.S. Census Bureau cartographic boundary file "
          "cb_2023_us_state_20m (public domain), California, "
          "equirectangular projection -->")
    print(f'viewBox="0 0 {VIEW_W:.0f} {view_h:.1f}"')
    print("JS constants:")
    print(f"  const GEO = {{ minLon: {min_lon}, maxLat: {max_lat}, "
          f"k: {k:.6f}, scale: {scale:.6f}, w: {VIEW_W:.0f}, h: {view_h:.1f} }};")
    print("Path:")
    print(path)


if __name__ == "__main__":
    main()
