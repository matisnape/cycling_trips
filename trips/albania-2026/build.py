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
import os, sys, re, json, math, hashlib, subprocess, time, datetime

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

    # Auto-switch: on a phone, index.html hands over to the single-page offline
    # version. Never a trap — "?full=1" pins the full version and is remembered,
    # and mobile.html links back. Inline + in <head> so it runs before first paint.
    # Detection is device-based (coarse/touch pointer), not window width, so a
    # narrow desktop window keeps the full site.
    SWITCH = ("<script>(function(){try{"
              "var K='gp-view';"
              "if(/[?&]full=1/.test(location.search)){localStorage.setItem(K,'full');return;}"
              "if(localStorage.getItem(K)==='full')return;"
              "var m=window.matchMedia;"
              "var coarse=m&&m('(pointer:coarse)').matches;"
              "var narrow=m&&m('(max-width:700px)').matches;"
              "if(coarse||(navigator.maxTouchPoints>0&&narrow)){"
              "location.replace('mobile.html'+location.hash);}"
              "}catch(e){}})();</script>")

    def asset(name):
        """assets/<name>?v=<hash>. GitHub Pages serves assets with max-age=600 and a
        phone can hold them much longer — without this a CSS change (e.g. the mobile
        hamburger) keeps losing to a cached style.css. Hash of the file, so the URL
        only changes when the file does."""
        try:
            with open(os.path.join(ASSETS, name), "rb") as f:
                return f'assets/{name}?v={hashlib.md5(f.read()).hexdigest()[:8]}'
        except OSError:
            return f'assets/{name}'

    def page(title, desc, body, with_map=False, active="", map_day=None, switch=False):
        head_extra = LCSS if with_map else ""
        extra_links = "".join(
            f'<a href="{p["slug"]}.html"{" aria-current=page" if active==p["slug"] else ""}>{p["label"]}</a>'
            for p in EXTRA if p["html"])
        # ponytail: hamburger is a CSS-only checkbox toggle — no JS, works offline too.
        # The "📱 Telefon" switch lives in the nav on desktop and in .viewbar (top-left,
        # same spot as in mobile.html) on phones, so it is never hidden behind the menu.
        nav = ('<input type="checkbox" id="menu-toggle" class="menu-toggle"/>'
               '<label class="burger" for="menu-toggle">☰<span class="skip">Menu</span></label>'
               '<nav>'
               f'<a href="index.html"{" aria-current=page" if active=="trasa" else ""}>Trasa</a>'
               + extra_links +
               f'<a href="zrodla.html"{" aria-current=page" if active=="zrodla" else ""}>Źródła</a>'
               '<a class="navphone" href="mobile.html">📱 Telefon</a></nav>')
        foot_extra = "".join(f'<a href="{p["slug"]}.html">{p["label"]}</a>' for p in EXTRA if p["html"])
        scripts = f'<script src="{asset("site.js")}" defer></script>'
        if with_map:
            scripts = (LJS + f'<script src="{asset("route-data.js")}"></script>'
                       + f'<script>window.MAP_DAY={map_day if map_day else "null"};</script>'
                       + f'<script src="{asset("map.js")}" defer></script>' + scripts)
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
<link rel="stylesheet" href="{asset("style.css")}"/>
{head_extra}
{SWITCH if switch else ""}
{COOKIE}
{GA}
</head>
<body>
<a class="skip" href="#main">Przejdź do treści</a>
<header class="site-head">
  <div class="wrap-w viewbar"><a href="mobile.html">📱 Wersja na telefon</a></div>
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
                     home, with_map=True, active="trasa", switch=True))

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

    # --- mobile.html: ONE self-contained page, no external requests at all ------
    # Everything (CSS, route sketch) is inline, so the saved file works offline on
    # a phone. No fonts, no Leaflet, no tiles — the map is an inline SVG sketch.
    # ponytail: the "download" button is a plain <a download> to this same file.
    write_mobile(OUT, DAYS, EXTRA, TOTAL_KM, md, linkify_sources, ensure_list_blanks,
                 sources_block, gmaps, mapycom)

    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "_buildid.txt"), "w", encoding="utf-8") as f:
        f.write(str(time.time()))

    return {"days": len(DAYS), "km": TOTAL_KM, "cuisine": len([c for c in cuisine if c[0]])}


def route_svg(width=680, height=440, pad=14):
    """Inline SVG sketch of the route from strona/assets/route-data.js (no tiles)."""
    path = os.path.join(ASSETS, "route-data.js")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception:
        return ""
    pts = [(float(la), float(lo)) for la, lo in data.get("route", [])]
    if len(pts) < 2:
        return ""
    lats = [p[0] for p in pts]; lons = [p[1] for p in pts]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
    # crude mercator-ish correction so the shape isn't stretched at 42°N
    kx = math.cos(math.radians((la0 + la1) / 2))
    w, h = (lo1 - lo0) * kx, (la1 - la0)
    scale = min((width - 2 * pad) / w, (height - 2 * pad) / h)
    ox = (width - w * scale) / 2
    oy = (height - h * scale) / 2

    def xy(la, lo):
        return (ox + (lo - lo0) * kx * scale, height - oy - (la - la0) * scale)

    line = " ".join("%.1f,%.1f" % xy(la, lo) for la, lo in pts)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3.2"/>' % xy(p["lat"], p["lon"])
                   for p in data.get("pois", []) if p.get("day") != 5)
    return (f'<svg viewBox="0 0 {width} {height}" role="img" '
            'aria-label="Szkic trasy — pętla wokół Gór Przeklętych">'
            f'<polyline points="{line}" fill="none" stroke="currentColor" '
            'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<g class="poi">{dots}</g></svg>')


def write_mobile(out, days, extra, total_km, md, linkify_sources, ensure_list_blanks,
                 sources_block, gmaps, mapycom):
    css = """
:root{--bg:#fbfcfb;--fg:#1c211f;--mut:#5d6763;--acc:#2f6e78;--line:#dfe4e1;--card:#fff}
@media (prefers-color-scheme:dark){
 :root{--bg:#14181a;--fg:#e8ecea;--mut:#9daaa5;--acc:#7fc6cf;--line:#2b3235;--card:#1a1f21}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 -webkit-text-size-adjust:100%;max-width:44rem;margin:0 auto;
 padding:0 16px calc(88px + env(safe-area-inset-bottom))}
h1{font-size:1.9rem;line-height:1.15;margin:24px 0 4px;letter-spacing:-.02em}
h2{font-size:1.15rem;margin:32px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:1rem;margin:18px 0 6px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
p,ul,ol{margin:8px 0}
ul,ol{padding-left:1.2em}
li{margin:5px 0}
a{color:var(--acc);text-underline-offset:2px}
.sub{color:var(--mut);margin:0 0 14px}
.facts{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px;list-style:none;padding:0}
.facts li{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 11px;font-size:.85rem}
.save{display:block;background:var(--acc);color:var(--bg);text-align:center;font-weight:600;
 text-decoration:none;padding:14px;border-radius:12px;margin:18px 0 6px}
.hint{color:var(--mut);font-size:.85rem;margin:0 0 8px}
.map{color:var(--acc);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px;margin:16px 0}
.map svg{display:block;width:100%;height:auto}
.map .poi{fill:currentColor;opacity:.75}
details{border:1px solid var(--line);border-radius:12px;background:var(--card);margin:8px 0;overflow:hidden}
summary{cursor:pointer;padding:13px 14px;font-weight:600;display:flex;gap:10px;align-items:baseline}
summary::-webkit-details-marker{display:none}
summary .n{color:var(--acc);font-variant-numeric:tabular-nums;font-size:.8rem;white-space:nowrap}
summary .km{margin-left:auto;color:var(--mut);font-size:.82rem;white-space:nowrap}
details>div{padding:0 14px 14px}
details[open] summary{border-bottom:1px solid var(--line);margin-bottom:12px}
blockquote{margin:12px 0;padding:10px 14px;border-left:3px solid var(--acc);background:var(--card);color:var(--mut);font-size:.92rem}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em}
table{width:100%;border-collapse:collapse;font-size:.9rem;display:block;overflow-x:auto}
td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut);font-size:.85rem}
.switch{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 0 0;font-size:.85rem;color:var(--mut)}
.switch span{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
/* Switch link first and left-aligned — same corner as the .viewbar link in the full version. */
.switch a{font-weight:600;text-decoration:none;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase}
/* Jump bar pinned to the BOTTOM — that is the thumb zone one-handed, and it keeps
   anchors landing at the true top of the screen (a sticky top bar would cover them).
   env(safe-area-inset-bottom) keeps it clear of the iPhone home indicator. */
.navbar{position:fixed;left:0;right:0;bottom:0;z-index:15;display:flex;gap:8px;
 padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:var(--bg);border-top:1px solid var(--line)}
.navbar>*{background:var(--card);border:1px solid var(--line);border-radius:12px;color:var(--fg);
 font:inherit;padding:12px 8px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.nav-a{flex:0 0 3.5rem;font-size:1.15rem;line-height:1}
.nav-c{flex:1;min-width:0;font-size:.9rem;font-weight:600;text-align:center;
 overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.navbar>*:active{background:var(--acc);color:var(--bg);border-color:var(--acc)}
/* Sheet opens on a checkbox, so the list still works if the JS ever fails. */
.sheet-t{position:absolute;width:0;height:0;opacity:0;pointer-events:none}
.sheet-back{position:fixed;inset:0;z-index:20;background:rgba(0,0,0,.45);
 opacity:0;pointer-events:none;transition:opacity .2s}
.sheet-t:checked~.sheet-back{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;z-index:21;max-height:78vh;overflow-y:auto;
 -webkit-overflow-scrolling:touch;background:var(--card);border-top:1px solid var(--line);
 border-radius:16px 16px 0 0;transform:translateY(101%);transition:transform .25s ease;
 padding-bottom:env(safe-area-inset-bottom)}
.sheet-t:checked~.sheet{transform:translateY(0)}
.sheet-in{padding:0 16px 12px}
.sheet-hd{position:sticky;top:0;background:var(--card);display:flex;align-items:center;
 justify-content:space-between;padding:14px 0 8px;font-weight:600}
.sheet-x{color:var(--mut);font-size:1.25rem;padding:2px 8px;cursor:pointer}
.sheet a{display:flex;gap:10px;align-items:baseline;padding:13px 2px;text-decoration:none;
 color:var(--fg);font-size:.95rem;border-bottom:1px solid var(--line)}
.sheet a:last-child{border-bottom:0}
.s-n{flex:0 0 1.7rem;color:var(--acc);font-weight:600;font-size:.8rem;font-variant-numeric:tabular-nums}
.s-t{flex:1;min-width:0}
.s-k{color:var(--mut);font-size:.8rem;white-space:nowrap}
"""
    blocks = []
    for d in days:
        body = (d["summary_html"] or "") + (d["places_html"] or "")
        blocks.append(
            f'<details id="dzien-{d["num"]}"><summary>'
            f'<span class="n">D{d["num"]} · {d["date"]}</span>'
            f'<span>{d["route"]}</span>'
            f'<span class="km">{d["km"]} km</span></summary><div>{body}</div></details>')
    for p in extra:
        if p["html"]:
            blocks.append(f'<details id="{p["slug"]}"><summary><span>{p["title"]}</span>'
                          f'</summary><div>{p["html"]}</div></details>')
    src = md(linkify_sources(ensure_list_blanks(re.sub(r"^>.*$", "", sources_block, flags=re.MULTILINE))))
    blocks.append(f'<details id="zrodla"><summary><span>Źródła i linki</span></summary><div>{src}</div></details>')

    # Opening this page (not via the "?full=1" link) means "phone version is what I
    # want" — index.html reads the same key and hands over automatically next time.
    # Kept out of the f-string below so the JS braces need no escaping.
    remember = ("<script>(function(){try{"
                "if(!/[?&]full=1/.test(location.search))"
                "localStorage.setItem('gp-view','mobile');"
                "}catch(e){}})();</script>")

    # Bottom jump bar: ← / current section / →. Sections are read in order on the
    # road (day after day), so arrows carry the common case and the middle button
    # opens the full list for the random jumps ("what was in Praktyczne again?").
    # One list drives all three — the sheet links, the arrow order and the label.
    nav_items = [("mapa", "", "Mapa trasy", "")]
    nav_items += [(f'dzien-{d["num"]}', f'D{d["num"]}', d["route"], f'{d["km"]} km') for d in days]
    nav_items += [(p["slug"], "", p["title"], "") for p in extra if p["html"]]
    nav_items.append(("zrodla", "", "Źródła i linki", ""))

    sheet_links = "".join(
        f'<a href="#{i}"><span class="s-n">{n}</span>'
        f'<span class="s-t">{t}</span><span class="s-k">{k}</span></a>'
        for i, n, t, k in nav_items)
    navbar = (
        '<input type="checkbox" id="sheet-t" class="sheet-t"/>'
        '<label class="sheet-back" for="sheet-t" aria-hidden="true"></label>'
        '<nav class="sheet" aria-label="Spis sekcji"><div class="sheet-in">'
        '<div class="sheet-hd">Skocz do sekcji<label class="sheet-x" for="sheet-t">✕</label></div>'
        f'{sheet_links}</div></nav>'
        '<div class="navbar">'
        '<button type="button" class="nav-a" data-go="-1" aria-label="Poprzednia sekcja">←</button>'
        '<button type="button" class="nav-c" id="nav-c">Sekcje ▾</button>'
        '<button type="button" class="nav-a" data-go="1" aria-label="Następna sekcja">→</button>'
        '</div>')

    # Anchors into a <details> only scroll to it, they don't expand it — open it
    # ourselves so a jump actually reveals the section instead of a closed card.
    # The label doubles as a "you are here" readout, updated on scroll.
    ids = json.dumps([i for i, _n, _t, _k in nav_items], ensure_ascii=False)
    labels = json.dumps([(f"{n} · {t}" if n else t) for _i, n, t, _k in nav_items], ensure_ascii=False)
    jumpnav = ("<script>(function(){"
               f"var IDS={ids},LAB={labels};"
               "var cap=document.getElementById('nav-c'),tog=document.getElementById('sheet-t');"
               "function el(id){return document.getElementById(id);}"
               "function open_(id){var e=el(id);if(e&&e.tagName==='DETAILS')e.open=true;return e;}"
               "function cur(){"
               # At the very bottom every remaining section is already on screen,
               # so the "last one scrolled past" rule would read a stale day.
               "var d=document.documentElement;"
               "if(innerHeight+scrollY>=d.scrollHeight-4)return IDS.length-1;"
               "var i,e,n=-1;for(i=0;i<IDS.length;i++){e=el(IDS[i]);"
               "if(e&&e.getBoundingClientRect().top<=96)n=i;}return n;}"
               "function paint(){var i=cur();cap.textContent=(i<0?'Sekcje':LAB[i])+' ▾';}"
               "function go(d){var i=cur()+d;if(i<0)i=0;if(i>=IDS.length)i=IDS.length-1;"
               "var e=open_(IDS[i]);if(e)e.scrollIntoView({behavior:'smooth',block:'start'});}"
               "document.addEventListener('click',function(ev){"
               "var b=ev.target.closest('[data-go]');"
               "if(b){go(+b.getAttribute('data-go'));return;}"
               "if(ev.target.closest('#nav-c')){tog.checked=!tog.checked;return;}"
               "var a=ev.target.closest('.sheet a[href^=\"#\"]');"
               "if(a){tog.checked=false;open_(a.getAttribute('href').slice(1));}"
               "});"
               "var wait=false;addEventListener('scroll',function(){if(wait)return;wait=true;"
               "requestAnimationFrame(function(){paint();wait=false;});},{passive:true});"
               "if(location.hash)open_(location.hash.slice(1));"
               "paint();"
               "})();</script>")

    html = f'''<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Góry Przeklęte — wersja offline</title>
{remember}
<meta name="description" content="Cała wyprawa na jednej stronie, bez internetu: plan dzień po dniu, praktyczne informacje, ciekawostki."/>
<style>{css}</style>
</head>
<body>
{navbar}
<nav class="switch"><a href="index.html?full=1">🗺 Wersja pełna z mapą</a></nav>
<h1 id="top">Góry Przeklęte</h1>
<p class="sub">Czarnogóra · Kosowo · Albania — 14–23.08.2026</p>
<ul class="facts">
  <li><b>{len(days)}</b> dni</li><li><b>{total_km}</b> km</li>
  <li><b>+8394</b> m</li><li>Čakor 1840 m</li><li>Qafa e Valbonës 1795 m</li>
</ul>

<a class="save" href="mobile.html" download="gory-przeklete-offline.html">⬇︎ Zapisz tę stronę offline</a>
<p class="hint"><b>iPhone:</b> dotknij przycisku → „Pobierz". Plik ląduje w <b>Plikach → Pobrane</b> i otwiera się w Safari bez internetu.
Alternatywnie: <b>Udostępnij → Zapisz w Plikach</b>. Cała strona to jeden plik — zero zewnętrznych fontów, skryptów i kafelków mapy, więc offline wygląda tak samo.</p>

<div class="map" id="mapa">{route_svg()}</div>
<p class="hint">Szkic trasy ze śladu GPS (bez podkładu — działa offline). Kropki to punkty z planu; dzień busowy po Kosowie pominięty.
Mapy online: <a href="{gmaps}">Google</a> · <a href="{mapycom}">mapy.com</a></p>

<h2 id="plan">Plan dzień po dniu</h2>
{"".join(blocks[:len(days)])}

<h2>Reszta</h2>
{"".join(blocks[len(days):])}

<footer>Longinada 2026 · <a href="index.html?full=1">wersja pełna z interaktywną mapą</a><br>
Na telefonie strona główna sama przenosi tutaj. Otwarcie wersji pełnej jest pamiętane w tej przeglądarce; wejście na tę stronę wraca do wersji telefonowej.</footer>
{jumpnav}
</body>
</html>
'''
    with open(os.path.join(out, "mobile.html"), "w", encoding="utf-8") as f:
        f.write(html)


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
