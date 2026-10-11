# -*- coding: utf-8 -*-
"""Generuje trips/<slug>/assets/route-data.js ze śladu GPX/KML + tabeli punktów CSV.

Użycie (z korzenia repo):
    python engine/gen_route.py albania-2026

Wejście, w katalogu trips/<slug>/:
    route.gpx lub route.kml   ślad trasy (GPX: <trkpt>; KML: <LineString>/<coordinates>)
    pois.csv                  punkty na mapie, nagłówek w pierwszej linii:
                              day,name,lat,lon,blurb
                              Dodatkowe kolumny (np. "type") są tolerowane i trafiają
                              do punktu pod własną nazwą.

Wyjście: trips/<slug>/assets/route-data.js  (window.TRIP = {route, pois})
"""
import csv, json, math, os, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPS = os.path.join(ROOT, "trips")
TOL = 0.0006  # ~60 m — upraszczanie linii (Ramer–Douglas–Peucker, w stopniach)
REQUIRED = ("day", "name", "lat", "lon", "blurb")


def die(msg):
    sys.exit("BŁĄD: " + msg)


def local(tag):
    """Nazwa taga bez przestrzeni nazw ('{ns}trkpt' -> 'trkpt')."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# --- ślad: GPX / KML ------------------------------------------------------

def load_gpx(path):
    root = ET.parse(path).getroot()
    pts = [(float(e.get("lat")), float(e.get("lon"))) for e in root.iter() if local(e.tag) == "trkpt"]
    if not pts:  # plik z trasą zamiast śladu
        pts = [(float(e.get("lat")), float(e.get("lon"))) for e in root.iter() if local(e.tag) == "rtept"]
    return pts


def load_kml(path):
    """Punkty z <LineString> (współrzędne 'lon,lat[,ele]' rozdzielone białymi znakami)
    oraz z <gx:Track> (<gx:coord> 'lon lat ele'). Pojedyncze <Point> (znaczniki) pomijamy."""
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
        die("w trips/%s/ nie ma route.gpx ani route.kml, ale istnieje już assets/route-data.js.\n"
            "  To prawdopodobnie JEDYNA kopia trasy tej wyprawy — nie regeneruję jej, żeby jej nie\n"
            "  nadpisać. Jeśli naprawdę masz ślad, połóż go jako trips/%s/route.gpx (lub .kml)\n"
            "  i zrób kopię route-data.js przed uruchomieniem." % (slug, slug))
    die("brak śladu: połóż trips/%s/route.gpx albo trips/%s/route.kml." % (slug, slug))


# --- upraszczanie linii ---------------------------------------------------

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


# --- punkty: CSV ----------------------------------------------------------

def num(s, what, line):
    try:
        return float(s.strip().replace(",", "."))  # Excel z polskim regionem daje przecinek
    except ValueError:
        die("pois.csv, linia %d: %s = %r nie jest liczbą." % (line, what, s))


def load_pois(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        die("pois.csv jest pusty — pierwsza linia musi być nagłówkiem: " + ",".join(REQUIRED))
    head = lines[0]
    delim = ";" if head.count(";") > head.count(",") else ","  # Excel (PL) zapisuje średniki
    rdr = csv.DictReader(lines, delimiter=delim)
    cols = [c.strip().lower() for c in (rdr.fieldnames or [])]
    rdr.fieldnames = cols
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        die("pois.csv: brak kolumn %s. Nagłówek ma być: %s (kolumny dodatkowe są dozwolone)."
            % (", ".join(missing), ",".join(REQUIRED)))
    extras = [c for c in cols if c and c not in REQUIRED and c != "url"]
    pois = []
    for row in rdr:
        line = rdr.line_num
        if None in row:
            die("pois.csv, linia %d: za dużo pól w wierszu (przecinek w opisie? ujmij opis w cudzysłów)." % line)
        row = {k: (v or "").strip() for k, v in row.items()}
        if not any(row.values()):
            continue  # pusta linia
        if not row["name"]:
            die("pois.csv, linia %d: pusta nazwa punktu." % line)
        try:
            day = int(row["day"])
        except ValueError:
            die("pois.csv, linia %d (%s): day = %r — oczekiwany numer dnia (liczba całkowita)."
                % (line, row["name"], row["day"]))
        lat, lon = num(row["lat"], "lat", line), num(row["lon"], "lon", line)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            die("pois.csv, linia %d (%s): współrzędne poza zakresem (lat=%s, lon=%s) — zamienione kolumny?"
                % (line, row["name"], lat, lon))
        p = {"day": day, "name": row["name"], "lat": lat, "lon": lon, "blurb": row["blurb"]}
        for c in extras:  # nadmiarowe kolumny (np. "type") przepisujemy do POI
            if row.get(c):
                p[c] = row[c]
        p["url"] = row.get("url") or "dzien-%d.html" % day
        pois.append(p)
    if not pois:
        die("pois.csv ma nagłówek, ale żadnego punktu.")
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
        sys.exit("Użycie: python engine/gen_route.py <slug>\n"
                 "Dostępne wyprawy: %s" % (", ".join(avail) or "(brak)"))
    slug = args[0]
    tdir = os.path.join(TRIPS, slug)
    if not os.path.isdir(tdir):
        die("nie ma katalogu trips/%s/." % slug)

    route_path, loader = find_route(tdir, slug)
    pois_path = os.path.join(tdir, "pois.csv")
    if not os.path.exists(pois_path):
        die("brak trips/%s/pois.csv (kolumny: %s). Wzór: trips/_szablon/pois.csv."
            % (slug, ",".join(REQUIRED)))

    try:
        pts = loader(route_path)
    except (ET.ParseError, ValueError, TypeError) as e:
        die("nie umiem odczytać %s: %s" % (os.path.relpath(route_path, ROOT), e))
    if len(pts) < 2:
        die("w %s nie znalazłem śladu (potrzebne co najmniej 2 punkty: GPX <trkpt> albo "
            "KML <LineString>)." % os.path.relpath(route_path, ROOT))

    line = rdp(pts, TOL)
    pois = load_pois(pois_path)

    src = os.path.basename(route_path)
    js = ("// Trasa i punkty — generowane z %s skryptem gen_route.py.\n"
          "// Linia: %d punktów (uproszczone z %d). Punkty: %d.\n" % (src, len(line), len(pts), len(pois))
          + "window.TRIP = " + json.dumps({"route": [[round(a, 5), round(b, 5)] for a, b in line],
                                           "pois": pois}, ensure_ascii=False, indent=1) + ";\n")
    out = os.path.join(tdir, "assets", "route-data.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    print("zapisane: %s  (linia %d pkt, POI %d, %.0f kB)"
          % (os.path.relpath(out, ROOT), len(line), len(pois), len(js) / 1024))


if __name__ == "__main__":
    main()
