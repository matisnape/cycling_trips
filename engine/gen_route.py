# -*- coding: utf-8 -*-
"""Generate trips/<slug>/assets/route-data.js from a GPX/KML track + a CSV of points.

Usage (from the repo root):
    python engine/gen_route.py albania-2026

Input, inside trips/<slug>/:
    route.gpx or route.kml    the track (GPX: <trkpt>; KML: <LineString>/<coordinates>)
    pois.csv                  map points, header on the first line:
                              day,name,lat,lon,blurb
                              Extra columns (e.g. "type") are tolerated and end up
                              on the point under their own name.

Output: trips/<slug>/assets/route-data.js  (window.TRIP = {route, pois})
"""
import csv, json, math, os, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPS = os.path.join(ROOT, "trips")
TOL = 0.0006  # ~60 m — line simplification (Ramer-Douglas-Peucker, in degrees)
REQUIRED = ("day", "name", "lat", "lon", "blurb")


def die(msg):
    sys.exit("ERROR: " + msg)


def local(tag):
    """Tag name without its namespace ('{ns}trkpt' -> 'trkpt')."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# --- track: GPX / KML -----------------------------------------------------

def load_gpx(path):
    root = ET.parse(path).getroot()
    pts = [(float(e.get("lat")), float(e.get("lon"))) for e in root.iter() if local(e.tag) == "trkpt"]
    if not pts:  # a route file instead of a track
        pts = [(float(e.get("lat")), float(e.get("lon"))) for e in root.iter() if local(e.tag) == "rtept"]
    return pts


def load_kml(path):
    """Points from <LineString> ('lon,lat[,ele]' coordinates separated by whitespace)
    and from <gx:Track> (<gx:coord> 'lon lat ele'). Standalone <Point> markers are skipped."""
    root = ET.parse(path).getroot()
    pts = []
    for el in root.iter():
        name = local(el.tag)
        if name == "LineString":
            for c in el.iter():
                if local(c.tag) == "coordinates" and c.text:
                    for tok in c.text.split():
                        parts = tok.split(",")
                        if len(parts) >= 2:
                            pts.append((float(parts[1]), float(parts[0])))
        elif name == "coord" and el.text:  # gx:coord
            parts = el.text.split()
            if len(parts) >= 2:
                pts.append((float(parts[1]), float(parts[0])))
    return pts


def find_route(tdir, slug):
    for fname, loader in (("route.gpx", load_gpx), ("route.kml", load_kml)):
        p = os.path.join(tdir, fname)
        if os.path.exists(p):
            return p, loader
    out = os.path.join(tdir, "assets", "route-data.js")
    if os.path.exists(out):
        die("trips/%s/ has neither route.gpx nor route.kml, but assets/route-data.js already exists.\n"
            "  That is probably the ONLY copy of this trip's route — refusing to regenerate it so it\n"
            "  is not overwritten. If you really do have the track, put it at trips/%s/route.gpx\n"
            "  (or .kml) and back up route-data.js before running this." % (slug, slug))
    die("no track: put trips/%s/route.gpx or trips/%s/route.kml in place." % (slug, slug))


# --- line simplification --------------------------------------------------

def rdp(pts, tol):
    if len(pts) < 3:
        return pts

    def d(p, a, b):
        (y0, x0), (y1, x1), (y2, x2) = p, a, b
        dy, dx = y2 - y1, x2 - x1
        if dy == 0 and dx == 0:
            return math.hypot(y0 - y1, x0 - x1)
        t = max(0, min(1, ((y0 - y1) * dy + (x0 - x1) * dx) / (dy * dy + dx * dx)))
        return math.hypot(y0 - (y1 + t * dy), x0 - (x1 + t * dx))

    stack, keep = [(0, len(pts) - 1)], {0, len(pts) - 1}
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        k, best = None, tol
        for m in range(i + 1, j):
            dd = d(pts[m], pts[i], pts[j])
            if dd > best:
                best, k = dd, m
        if k:
            keep.add(k)
            stack += [(i, k), (k, j)]
    return [pts[i] for i in sorted(keep)]


# --- points: CSV ----------------------------------------------------------

def num(s, what, line):
    try:
        return float(s.strip().replace(",", "."))  # Excel in a comma-decimal locale writes commas
    except ValueError:
        die("pois.csv, line %d: %s = %r is not a number." % (line, what, s))


def load_pois(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        die("pois.csv is empty — the first line must be the header: " + ",".join(REQUIRED))
    head = lines[0]
    delim = ";" if head.count(";") > head.count(",") else ","  # some locales make Excel write semicolons
    rdr = csv.DictReader(lines, delimiter=delim)
    cols = [c.strip().lower() for c in (rdr.fieldnames or [])]
    rdr.fieldnames = cols
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        die("pois.csv: missing columns %s. The header must be: %s (extra columns are allowed)."
            % (", ".join(missing), ",".join(REQUIRED)))
    extras = [c for c in cols if c and c not in REQUIRED and c != "url"]
    pois = []
    for row in rdr:
        line = rdr.line_num
        if None in row:
            die("pois.csv, line %d: too many fields in the row (a comma inside the blurb? quote the blurb)." % line)
        row = {k: (v or "").strip() for k, v in row.items()}
        if not any(row.values()):
            continue  # blank line
        if not row["name"]:
            die("pois.csv, line %d: the point has no name." % line)
        try:
            day = int(row["day"])
        except ValueError:
            die("pois.csv, line %d (%s): day = %r — a day number (integer) is expected."
                % (line, row["name"], row["day"]))
        lat, lon = num(row["lat"], "lat", line), num(row["lon"], "lon", line)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            die("pois.csv, line %d (%s): coordinates out of range (lat=%s, lon=%s) — columns swapped?"
                % (line, row["name"], lat, lon))
        p = {"day": day, "name": row["name"], "lat": lat, "lon": lon, "blurb": row["blurb"]}
        for c in extras:  # extra columns (e.g. "type") are copied onto the POI
            if row.get(c):
                p[c] = row[c]
        p["url"] = row.get("url") or "dzien-%d.html" % day
        pois.append(p)
    if not pois:
        die("pois.csv has a header but no points.")
    return pois


# --- main -----------------------------------------------------------------

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 1 or any(a in ("-h", "--help") for a in sys.argv[1:]):
        avail = sorted(d for d in os.listdir(TRIPS)
                       if not d.startswith("_") and os.path.isdir(os.path.join(TRIPS, d))) if os.path.isdir(TRIPS) else []
        sys.exit("Usage: python engine/gen_route.py <slug>\n"
                 "Available trips: %s" % (", ".join(avail) or "(none)"))
    slug = args[0]
    tdir = os.path.join(TRIPS, slug)
    if not os.path.isdir(tdir):
        die("there is no trips/%s/ directory." % slug)

    route_path, loader = find_route(tdir, slug)
    pois_path = os.path.join(tdir, "pois.csv")
    if not os.path.exists(pois_path):
        die("no trips/%s/pois.csv (columns: %s). Template: trips/_template/pois.csv."
            % (slug, ",".join(REQUIRED)))

    try:
        pts = loader(route_path)
    except (ET.ParseError, ValueError, TypeError) as e:
        die("cannot read %s: %s" % (os.path.relpath(route_path, ROOT), e))
    if len(pts) < 2:
        die("found no track in %s (at least 2 points are needed: GPX <trkpt> or "
            "KML <LineString>)." % os.path.relpath(route_path, ROOT))

    line = rdp(pts, TOL)
    pois = load_pois(pois_path)

    src = os.path.basename(route_path)
    js = ("// Route and points — generated from %s by gen_route.py.\n"
          "// Line: %d points (simplified from %d). Points: %d.\n" % (src, len(line), len(pts), len(pois))
          + "window.TRIP = " + json.dumps({"route": [[round(a, 5), round(b, 5)] for a, b in line],
                                           "pois": pois}, ensure_ascii=False, indent=1) + ";\n")
    out = os.path.join(tdir, "assets", "route-data.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    print("written: %s  (line %d pts, POIs %d, %.0f kB)"
          % (os.path.relpath(out, ROOT), len(line), len(pois), len(js) / 1024))


if __name__ == "__main__":
    main()
