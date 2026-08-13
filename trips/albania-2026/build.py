# -*- coding: utf-8 -*-
"""
Builds the "Góry Przeklęte" site from a markdown note.

Usage:
    python build.py            # build once into the ./strona folder
    python build.py --serve    # build and open a preview in the browser
    python build.py --watch    # LIVE PREVIEW: on every save in Obsidian
                               # the site rebuilds and refreshes itself

You only edit the note (./tresc.md by default). Files in strona/assets/ are left as-is.
"""
import os, sys, re, subprocess, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# --- SOURCE ---------------------------------------------------------------
# By default the script reads the tresc.md file next to it.
# If you prefer to keep the note in your Obsidian vault, paste the full path
# to the .md file here (in quotes), e.g.:
#   SRC_OVERRIDE = r"C:\Users\Anks\Obsidian\Sejf\Longinada 2026.md"
#   SRC_OVERRIDE = "/Users/anks/Obsidian/Sejf/Longinada 2026.md"
SRC_OVERRIDE = ""
# -------------------------------------------------------------------------
SRC = SRC_OVERRIDE or os.path.join(HERE, "tresc.md")
OUT = os.path.join(HERE, "strona")
ASSETS = os.path.join(OUT, "assets")

# --- markdown library: install it if missing ---
try:
    import markdown
except ImportError:
    print("Missing 'markdown' library — trying to install it...")
    ok = False
    for args in (["-m", "pip", "install", "markdown"],
                 ["-m", "pip", "install", "--user", "markdown"]):
        try:
            subprocess.check_call([sys.executable] + args); ok = True; break
        except Exception:
            continue
    if not ok:
        sys.exit("Could not install 'markdown'. Run manually: pip install markdown")
    import markdown


def need(match, what):
    if not match:
        raise SystemExit(f"ERROR: section not found in the note: {what}.\n"
                         "Check that the headings were not removed/renamed (see JAK-EDYTOWAC.md).")
    return match


def build():
    if not os.path.exists(SRC):
        raise SystemExit(f"ERROR: source file not found:\n  {SRC}")
    with open(SRC, encoding="utf-8") as f:
        raw = f.read()

    raw = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.DOTALL)  # frontmatter
    # Obsidian links: ![[image]] -> image from assets; [[a|b]] -> b; [[a]] -> a
    raw = re.sub(r"!\[\[([^\]]+?)\]\]", lambda m: f"![](assets/{m.group(1).strip()})", raw)
    raw = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", raw)
    raw = re.sub(r"\[\[([^\]]+)\]\]", r"\1", raw)
    raw = raw.replace("\t", "    ")

    def md(text):
        return markdown.markdown(text, extensions=["extra", "sane_lists"])

    def ensure_list_blanks(text):
        out = []
        for ln in text.split("\n"):
            is_item = re.match(r"^\s*-\s", ln)
            prev = out[-1] if out else ""
            if is_item and prev.strip() and not re.match(r"^\s*-\s", prev) and not prev.lstrip().startswith("#"):
                out.append("")
            out.append(ln)
        return "\n".join(out)

    def linkify_sources(text):
        out = []
        for ln in text.split("\n"):
            m = re.match(r"^(\s*)-\s+(.*):\s*(https?://\S+)\s*$", ln)
            out.append(f"{m.group(1)}- [{m.group(2)}]({m.group(3)})" if m else ln)
        return "\n".join(out)

    def note_html(block):
        lines = [re.sub(r"^>\s?", "", l) for l in block.strip().split("\n")]
        body = "\n".join(lines).replace("[!note] Skąd te notatki", "**Skąd te notatki**")
        return '<div class="note">\n' + md(body) + "\n</div>"

    meta_block = need(re.search(r"# Meta\n(.*?)\n# Klucz do wyjazdu", raw, re.DOTALL), "# Meta / # Klucz do wyjazdu").group(1)
    # "- Nazwa - opis" → a taste pill. Name may be multi-word ("Tavë kosi"), so it is
    # everything up to the " - " separator; lines starting with Opis/Mapa/Szlak are links.
    cuisine = re.findall(r"^- ([^-\n]+?)(?:[ \t]+-[ \t]+(.+?))?[ \t]*$", meta_block, re.MULTILINE)
    cuisine = [(n, g) for (n, g) in cuisine if not n.lower().startswith(("opis", "mapa", "szlak"))]
    gm = re.search(r"Mapa Google:\s*(\S+)", meta_block)
    mc = re.search(r"Mapa mapy\.com:\s*(\S+)", meta_block)
    gmaps = gm.group(1) if gm else "#"
    mapycom = mc.group(1) if mc else "#"

    intro_block = need(re.search(r"# Klucz do wyjazdu — .*?\n(.*?)\n# Plan wyjazdu", raw, re.DOTALL), "# Plan wyjazdu").group(1)
    intro_block = re.sub(r"\s*→\s*$", "", intro_block, flags=re.MULTILINE)
    intro_html = md(intro_block)

    plan = need(re.search(r"# Plan wyjazdu\n(.*?)\n---\n", raw, re.DOTALL), "# Plan wyjazdu (terminated with a --- line)").group(1)
    day_chunks = [c for c in re.split(r"(?=^## Dzień \d+:)", plan, flags=re.MULTILINE) if c.strip().startswith("## Dzień")]
    if not day_chunks:
        raise SystemExit("ERROR: no days found. Each day must start with '## Dzień N: ...'.")

    note_block = need(re.search(r"\n---\n\n(> \[!note\].*?)\n\n---\n", raw, re.DOTALL), "note '> [!note] Skąd te notatki'").group(1)
    sources_block = need(re.search(r"# Źródła i dalsza lektura\n(.*)$", raw, re.DOTALL), "# Źródła i dalsza lektura").group(1)

    # Extra free-form pages. To add one: append a row here AND a matching "# <heading>"
    # section in tresc.md (place it before "# Źródła"). Lines like "- Nazwa: https://…"
    # become links. An empty/missing section → no page and no nav link, no error.
    # ponytail: data-driven so a new category is one line here + one section in the note.
    EXTRA_SPEC = [
        # slug,         nav label,     md heading,                page title,                eyebrow
        ("praktyczne",  "Praktyczne",  "# Praktyczne informacje", "Praktyczne informacje",   "W terenie"),
        ("kulinaria",   "Kulinaria",   "# Kulinaria i pamiątki",  "Kulinaria i pamiątki",    "Co zjeść, co przywieźć"),
        ("ciekawostki", "Ciekawostki", "# Ciekawostki",           "Ciekawostki",             "Drobiazgi po drodze"),
    ]
    EXTRA = []
    for slug, label, heading, title, eyebrow in EXTRA_SPEC:
        m = re.search(rf"\n{re.escape(heading)}\n(.*?)(?=\n# |\Z)", raw, re.DOTALL)
        html = md(linkify_sources(ensure_list_blanks(m.group(1).strip()))) if m and m.group(1).strip() else ""
        EXTRA.append({"slug": slug, "label": label, "title": title, "eyebrow": eyebrow, "html": html})

    src_main, final_note = sources_block, ""
    mfn = re.search(r"\n(>\s?Uwaga:.*)$", sources_block, re.DOTALL)
    if mfn:
        final_note, src_main = mfn.group(1), sources_block[:mfn.start()]

    DAYS = []
    for ch in day_chunks:
        h = re.match(r"## Dzień (\d+):\s*(.+)", ch)
        num, desc = int(h.group(1)), h.group(2).strip()
        m = re.match(r"(\w+),\s*([\d.]+),\s*(.+?)\s*\((\d+)\s*km\)", desc)
        weekday = m.group(1) if m else ""
        date = m.group(2) if m else ""
        route = (m.group(3) if m else desc).replace(" > ", " → ").replace(">", "→")
        km = m.group(4) if m else ""
        rest = ch.split("\n", 1)[1] if "\n" in ch else ""
        if "### Miejsca i historia" in rest:
            summary_md, places_md = rest.split("### Miejsca i historia", 1)
        else:
            summary_md, places_md = rest, ""
        DAYS.append({"num": num, "weekday": weekday, "date": date, "route": route, "km": km,
                     "summary_html": md(summary_md.strip()) if summary_md.strip() else "",
                     "places_html": md(places_md.strip()) if places_md.strip() else ""})

    TOTAL_KM = sum(int(d["km"]) for d in DAYS if d["km"])
    date_year = "2026"

    FONTS = ('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&'
             'family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=Spline+Sans+Mono:wght@400;500&display=swap')
    LCSS = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
    LJS = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'

    # ponytail: no analytics, no cookie banner — nothing collected, nothing to consent to.
    # Want GA4 here? Copy the GA_ID + CookieScript block from longinada-rumunia-2026.
    COOKIE = ""
    GA = ""

    def page(title, desc, body, with_map=False, active="", map_day=None):
        head_extra = LCSS if with_map else ""
        extra_links = "".join(
            f'<a href="{p["slug"]}.html"{" aria-current=page" if active==p["slug"] else ""}>{p["label"]}</a>'
            for p in EXTRA if p["html"])
        nav = ('<nav>'
               f'<a href="index.html"{" aria-current=page" if active=="trasa" else ""}>Trasa</a>'
               + extra_links +
               f'<a href="zrodla.html"{" aria-current=page" if active=="zrodla" else ""}>Źródła</a></nav>')
        foot_extra = "".join(f'<a href="{p["slug"]}.html">{p["label"]}</a>' for p in EXTRA if p["html"])
        scripts = '<script src="assets/site.js" defer></script>'
        if with_map:
            scripts = (LJS + '<script src="assets/route-data.js"></script>'
                       + f'<script>window.MAP_DAY={map_day if map_day else "null"};</script>'
                       + '<script src="assets/map.js" defer></script>' + scripts)
        return f'''<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<meta name="description" content="{desc}"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link rel="stylesheet" href="{FONTS}"/>
<link rel="stylesheet" href="assets/style.css"/>
{head_extra}
{COOKIE}
{GA}
</head>
<body>
<a class="skip" href="#main">Przejdź do treści</a>
<header class="site-head">
  <div class="wrap-w bar">
    <a class="brand" href="index.html"><span class="glyph">△</span>Góry Przeklęte</a>
    {nav}
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap-w">
    <p>Notatki z wyprawy rowerowej wokół Prokletije · Longinada {date_year}</p>
    <div class="links">
      <a href="index.html">Trasa</a>{foot_extra}<a href="zrodla.html">Źródła</a>
      <a href="{gmaps}" rel="noopener" target="_blank">Mapa Google</a>
      <a href="{mapycom}" rel="noopener" target="_blank">mapy.com</a>
    </div>
  </div>
</footer>
{scripts}
</body>
</html>
'''

    os.makedirs(OUT, exist_ok=True)

    rows = []
    for d in DAYS:
        rows.append(f'<a class="day-row" href="dzien-{d["num"]}.html">'
                    f'<span class="dot" aria-hidden="true"></span>'
                    f'<span class="body"><span class="d-where">Dzień {d["num"]} · {d["date"]}</span>'
                    f'<span class="d-title">{d["route"]}</span></span>'
                    f'<span class="km">{d["km"]} km</span></a>')
    itin = '<div class="itin">\n' + "\n".join(rows) + "\n</div>"
    pills = "".join(f"<li><b>{n}</b>{(' · ' + g) if g else ''}</li>" for n, g in cuisine if n)
    taste = f'<section class="taste"><p class="eyebrow">Czego spróbować</p><ul>{pills}</ul></section>'

    home = f'''
<section class="wrap hero">
  <p class="eyebrow">Czarnogóra · Kosowo · Albania — 14–23.08.2026</p>
  <h1>Góry<br>Przeklęte</h1>
  <p class="lede">Dziesięć dni rowerem wokół Prokletije — przez dolinę Cem, Čakor, kanion Rugova, Valbonę i Theth, z powrotem do Podgoricy.</p>
  <div class="facts">
    <span><b>{len(DAYS)}</b> dni</span><span><b>{TOTAL_KM}</b> km</span>
    <span><b>+8394</b> m (pełny ślad 481 km)</span><span>Čakor&nbsp;1840&nbsp;m · Qafa&nbsp;e&nbsp;Valbonës&nbsp;1795&nbsp;m</span>
  </div>
  <hr class="river-rule"/>
</section>
<section class="wrap prose">
  {intro_html}
</section>
<section class="wrap-w map-section">
  <p class="eyebrow">Mapa trasy</p>
  <div id="map"></div>
  <p class="map-cap">Linia — zapisana trasa z mapy „Góry Przeklęte”. Punkty — najważniejsze miejsca (kliknij, by przejść do dnia). Pozycje miast są poglądowe.</p>
</section>
<section class="wrap">
  <p class="eyebrow">Plan dzień po dniu</p>
  {itin}
  {taste}
</section>
'''
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Góry Przeklęte — rowerem wokół Prokletije",
                     "Notatki z 10-dniowej wyprawy rowerowej wokół Gór Przeklętych (Czarnogóra, Kosowo, Albania): 480 km, historia i miejsca dzień po dniu, z interaktywną mapą trasy.",
                     home, with_map=True, active="trasa"))

    for i, d in enumerate(DAYS):
        p, n = (DAYS[i-1] if i > 0 else None), (DAYS[i+1] if i < len(DAYS)-1 else None)
        prev_html = (f'<a class="prev" href="dzien-{p["num"]}.html"><span>← Dzień {p["num"]}</span>{p["route"]}</a>'
                     if p else '<span class="prev disabled"></span>')
        next_html = (f'<a class="next" href="dzien-{n["num"]}.html"><span>Dzień {n["num"]} →</span>{n["route"]}</a>'
                     if n else '<span class="next disabled"></span>')
        summary = f'<div class="logi"><p class="eyebrow">W skrócie</p>{d["summary_html"]}</div>' if d["summary_html"] else ""
        places = f'<div class="prose"><h2>Miejsca i historia</h2>{d["places_html"]}</div>' if d["places_html"] else ""
        body = f'''
<article class="wrap">
  <a class="back-plan" href="index.html">← Plan wyjazdu</a>
  <p class="eyebrow">Dzień {d["num"]} · {d["weekday"]}, {d["date"]} · {d["km"]} km</p>
  <h1>{d["route"]}</h1>
</article>
<section class="wrap-w map-section">
  <div id="map" class="mini"></div>
  <p class="map-cap">Mapa skupiona na punktach tego dnia (na tle całej trasy).</p>
</section>
<article class="wrap">
  {summary}
  {places}
  <nav class="daynav">{prev_html}{next_html}</nav>
</article>
'''
        with open(os.path.join(OUT, f"dzien-{d['num']}.html"), "w", encoding="utf-8") as f:
            f.write(page(f"Dzień {d['num']}: {d['route']} — Góry Przeklęte",
                         f"Dzień {d['num']} wyprawy: {d['route']} ({d['km']} km). Miejsca i historia po drodze.",
                         body, with_map=True, active="trasa", map_day=d["num"]))

    sources_body = f'''
<article class="wrap prose">
  <a class="back-plan" href="index.html">← Plan wyjazdu</a>
  <p class="eyebrow">Metoda i odnośniki</p>
  <h1>Źródła i dalsza lektura</h1>
  {note_html(note_block)}
  {md(linkify_sources(ensure_list_blanks(src_main)))}
  {note_html(final_note) if final_note else ""}
</article>
'''
    with open(os.path.join(OUT, "zrodla.html"), "w", encoding="utf-8") as f:
        f.write(page("Źródła i dalsza lektura — Góry Przeklęte",
                     "Źródła, na których oparte są notatki z wyprawy, pogrupowane wg miejsc.",
                     sources_body, with_map=False, active="zrodla"))

    for p in EXTRA:
        if not p["html"]:
            continue
        body = f'''
<article class="wrap prose">
  <a class="back-plan" href="index.html">← Plan wyjazdu</a>
  <p class="eyebrow">{p["eyebrow"]}</p>
  <h1>{p["title"]}</h1>
  {p["html"]}
</article>
'''
        with open(os.path.join(OUT, f'{p["slug"]}.html'), "w", encoding="utf-8") as f:
            f.write(page(f'{p["title"]} — Góry Przeklęte',
                         f'{p["title"]} — notatki z wyprawy „Góry Przeklęte”.',
                         body, with_map=False, active=p["slug"]))

    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "_buildid.txt"), "w", encoding="utf-8") as f:
        f.write(str(time.time()))

    return {"days": len(DAYS), "km": TOTAL_KM, "cuisine": len([c for c in cuisine if c[0]])}


def snapshot():
    paths = [SRC]
    if os.path.isdir(ASSETS):
        for fn in os.listdir(ASSETS):
            if fn != "_buildid.txt":
                paths.append(os.path.join(ASSETS, fn))
    return tuple(sorted((p, os.path.getmtime(p)) for p in paths if os.path.exists(p)))


def serve_background():
    import http.server, socketserver, threading
    os.chdir(OUT)
    port = 8000
    httpd = None
    while port < 8010:
        try:
            httpd = socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler); break
        except OSError:
            port += 1
    if not httpd:
        raise SystemExit("Could not start the preview (ports 8000-8009 are in use).")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


def main():
    serve = "--serve" in sys.argv
    watch = "--watch" in sys.argv

    stats = None
    try:
        stats = build()
    except SystemExit as e:
        print(e)
        if not (watch or serve):
            raise
        print("Fix the note and save — I'll try again...\n")
    if stats:
        print(f"✓ Built: {OUT}  (days: {stats['days']}, km: {stats['km']}, dishes: {stats['cuisine']})")

    if not (serve or watch):
        return

    port = serve_background()
    url = f"http://localhost:{port}/index.html"
    print(f"\nLive preview: {url}")
    if watch:
        print("Edit the note in Obsidian and save (Ctrl/Cmd+S) — the site will refresh itself.")
    print("Stop: Ctrl+C\n")
    try:
        import webbrowser; webbrowser.open(url)
    except Exception:
        pass

    if not watch:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDone."); return

    last = None
    try:
        while True:
            snap = snapshot()
            if snap != last:
                if last is not None:
                    stamp = datetime.datetime.now().strftime("%H:%M:%S")
                    try:
                        s = build()
                        print(f"[{stamp}] ✓ rebuilt (days: {s['days']}, km: {s['km']})")
                    except SystemExit as e:
                        print(f"[{stamp}] {e}")
                last = snap
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()
