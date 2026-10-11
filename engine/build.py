# -*- coding: utf-8 -*-
"""
Generic trip-site generator: trips/<slug>/tresc.md + trips/<slug>/trip.toml -> _site/<slug>/

Usage:
    python engine/build.py                  # build every trip in trips/ (skips _*) + _site/index.html
    python engine/build.py <slug>           # build one trip
    python engine/build.py <slug> --serve   # build and open a preview in the browser
    python engine/build.py <slug> --watch   # LIVE PREVIEW: every save rebuilds and refreshes the browser
    (--serve / --watch also work without a slug: they serve all of _site/)
    python engine/build.py <slug> --refreeze  # rebuild a FROZEN trip on purpose and overwrite its frozen/

Frozen trips: trip.toml may carry  [freeze] date = "YYYY-MM-DD". From that day on the
generator is NOT run for the trip; trips/<slug>/frozen/ (committed to the repo) is copied
into _site/<slug>/ instead. The first build on/after the date creates frozen/ (commit it!).
Details: PLAYBOOK.md, section 2.

All per-trip text, colours and options live in trips/<slug>/trip.toml; the note
itself (tresc.md) is the only content source. Shared look & behaviour lives in
engine/assets/ (style.css, map.js, site.js) and is copied into every trip.
"""
import os, sys, re, json, math, hashlib, shutil, subprocess, time, datetime, html as htmllib
import tomllib
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRIPS = os.path.join(ROOT, "trips")
SITE = os.path.join(ROOT, "_site")
ENGINE_ASSETS = os.path.join(HERE, "assets")
SHARED_ASSETS = ("style.css", "map.js", "site.js")

# map.js (shared, not edited here) still carries this accent literal. At copy time it is
# swapped for [theme] accent. Once map.js reads window.TRIP_ACCENT (set in every map page)
# this replacement simply matches nothing and can be deleted.
LEGACY_MAP_ACCENT = "#2f6e78"
# localStorage key prefix of the full/mobile switch; the slug is appended per trip.
VIEW_KEY = "gp-view"
RESERVED_PAGE_SLUGS = {"index", "mobile", "zrodla", "assets"}
DEFAULT_SKIP_PREFIXES = ["opis", "mapa", "szlak"]

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
                         "Check that the headings were not removed/renamed (see HOW-TO-EDIT.md).")
    return match


# =========================================================================
# trip.toml
# =========================================================================
_MISSING = object()
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _hex6(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)]


def _mix(color, target, t):
    """Blend `color` towards `target` (0..255) by t — used for derived accent shades."""
    return "#%02x%02x%02x" % tuple(round(v + (target - v) * t) for v in _hex6(color))


def load_config(slug):
    """Read and validate trips/<slug>/trip.toml. Every problem is collected and
    reported together as a readable message (never a KeyError)."""
    rel = f"trips/{slug}/trip.toml"
    path = os.path.join(TRIPS, slug, "trip.toml")
    if not os.path.isfile(path):
        raise SystemExit(f"ERROR: config file {rel} is missing.")
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"ERROR: {rel}: TOML syntax error: {e}")

    errors = []

    def field(table, key, typ=str, default=_MISSING):
        label = f"[{table}] {key}" if table else key
        src = data if table is None else data.get(table, _MISSING)
        if src is _MISSING:
            src = {}
        if not isinstance(src, dict):
            errors.append(f"{table} must be a table ([{table}]), not a value")
            return default if default is not _MISSING else None
        if key not in src:
            if default is _MISSING:
                errors.append(f"required field {label} is missing")
                return None
            return default
        v = src[key]
        ok = isinstance(v, typ) and not (typ is int and isinstance(v, bool))
        if not ok:
            errors.append(f"field {label} has the wrong type (expected: {typ.__name__})")
            return default if default is not _MISSING else None
        if typ is str and default is _MISSING and not v.strip():
            errors.append(f"field {label} is empty")
        return v

    c = SimpleNamespace()
    c.slug = field(None, "slug")
    if c.slug and c.slug != slug:
        errors.append(f"slug = \"{c.slug}\" does not match the directory name trips/{slug}/")
    if c.slug and not _SLUG.match(c.slug):
        errors.append("slug may only contain lowercase letters, digits, '-' and '_'")
    c.lang = field(None, "lang", str, "pl")
    c.source = field(None, "source", str, "tresc.md")
    c.skip_prefixes = field(None, "meta_skip_prefixes", list, DEFAULT_SKIP_PREFIXES)
    if not all(isinstance(x, str) for x in c.skip_prefixes):
        errors.append("meta_skip_prefixes must be a list of strings")
        c.skip_prefixes = DEFAULT_SKIP_PREFIXES
    c.skip_prefixes = tuple(x.lower() for x in c.skip_prefixes)

    for k in ("title", "title_html", "glyph", "eyebrow", "lede", "home_title",
              "home_description", "footer", "map_caption_name", "offline_filename", "offline_aria"):
        setattr(c, k, field("site", k))
    c.footer_short = field("site", "footer_short", str, "") or c.title
    c.facts = field("site", "facts", list, [])
    if not all(isinstance(x, str) for x in c.facts):
        errors.append("[site] facts must be a list of strings")
        c.facts = []
    c.show_total_km = field("site", "show_total_km", bool, True)

    c.pages = []
    pages = data.get("pages", [])
    if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
        errors.append("pages must be a list of tables ([[pages]])")
        pages = []
    seen = set()
    for i, p in enumerate(pages, 1):
        row = {}
        for k in ("slug", "label", "heading", "title", "eyebrow"):
            v = p.get(k)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"required field [[pages]] #{i} {k} is missing")
            row[k] = v
        ps = row["slug"]
        if isinstance(ps, str) and ps:
            if not _SLUG.match(ps) or ps in RESERVED_PAGE_SLUGS or re.match(r"^dzien-\d+$", ps):
                errors.append(f"[[pages]] #{i}: slug \"{ps}\" is not allowed or is reserved")
            if ps in seen:
                errors.append(f"[[pages]] #{i}: slug \"{ps}\" is used twice")
            seen.add(ps)
        c.pages.append(row)

    c.svg_skip_days = field("map", "svg_skip_days", list, [])
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in c.svg_skip_days):
        errors.append("[map] svg_skip_days must be a list of integers")
        c.svg_skip_days = []
    c.svg_min_points = field("map", "svg_min_points", int, 40)
    c.svg_skip_note = field("map", "svg_skip_note", str, "")

    c.accent = field("theme", "accent")
    c.accent_deep = field("theme", "accent_deep", str, "")
    c.accent_dark = field("theme", "accent_dark", str, "")
    for k in ("accent", "accent_deep", "accent_dark"):
        v = getattr(c, k)
        if v and not _HEX.match(v):
            errors.append(f"[theme] {k} = \"{v}\" does not look like a #rgb / #rrggbb colour")
            setattr(c, k, "")
    if c.accent and not c.accent_deep:
        c.accent_deep = _mix(c.accent, 0, 0.37)       # hover / stronger
    if c.accent and not c.accent_dark:
        c.accent_dark = _mix(c.accent, 255, 0.5)      # accent on the dark mobile theme

    c.ga_id = field("analytics", "ga_id", str, "")
    c.cookiescript = field("analytics", "cookiescript", str, "")
    if c.ga_id and not re.match(r"^[A-Za-z0-9-]+$", c.ga_id):
        errors.append("[analytics] ga_id contains disallowed characters")
    if c.cookiescript and not re.match(r"^[\w:/.\-?=&%]+$", c.cookiescript):
        errors.append("[analytics] cookiescript contains disallowed characters")

    if errors:
        raise SystemExit(f"ERROR: {rel}:\n" + "\n".join(f"  - {e}" for e in errors))
    return c


# =========================================================================
# tresc.md  ->  structured note
# =========================================================================
def parse_note(raw, cfg):
    """The tresc.md contract. The body below (between the markers) is the Albania
    parser, unchanged except: dish-prefix filter = cfg.skip_prefixes, EXTRA_SPEC = cfg.pages."""
    # ---- BEGIN parser (1:1 with longinada-albania-2026/build.py l. 59-151) ----
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
    # "- Nazwa - opis" → a taste pill. The name is everything up to the " - " separator,
    # so it may be multi-word ("Tavë kosi") and may itself contain a hyphen ("Hida-gyu") —
    # only a hyphen surrounded by spaces splits name from description. Lines starting with
    # Opis/Mapa/Szlak are links.
    cuisine = re.findall(r"^- (.+?)(?:[ \t]+-[ \t]+(.+?))?[ \t]*$", meta_block, re.MULTILINE)
    cuisine = [(n, g) for (n, g) in cuisine if not n.lower().startswith(cfg.skip_prefixes)]
    gm = re.search(r"Mapa Google:\s*(\S+)", meta_block)
    mc = re.search(r"Mapa mapy\.com:\s*(\S+)", meta_block)
    # No "Mapa Google:" / "Mapa mapy.com:" line in # Meta -> no link at all. "#" would
    # render as a dead link in the footer and under the offline sketch.
    gmaps = gm.group(1) if gm else ""
    mapycom = mc.group(1) if mc else ""

    intro_block = need(re.search(r"# Klucz do wyjazdu — .*?\n(.*?)\n# Plan wyjazdu", raw, re.DOTALL), "# Plan wyjazdu").group(1)
    intro_block = re.sub(r"\s*→\s*$", "", intro_block, flags=re.MULTILINE)
    intro_html = md(intro_block)

    plan = need(re.search(r"# Plan wyjazdu\n(.*?)\n---\n", raw, re.DOTALL), "# Plan wyjazdu (terminated with a --- line)").group(1)
    day_chunks = [c for c in re.split(r"(?=^## Dzień \d+:)", plan, flags=re.MULTILINE) if c.strip().startswith("## Dzień")]
    if not day_chunks:
        raise SystemExit("ERROR: no days found. Each day must start with '## Dzień N: ...'.")

    note_block = need(re.search(r"\n---\n\n(> \[!note\].*?)\n\n---\n", raw, re.DOTALL), "note '> [!note] Skąd te notatki'").group(1)
    sources_block = need(re.search(r"# Źródła i dalsza lektura\n(.*)$", raw, re.DOTALL), "# Źródła i dalsza lektura").group(1)

    # Extra free-form pages come from [[pages]] in trip.toml (was EXTRA_SPEC). Each needs a
    # matching "# <heading>" section in tresc.md (before "# Źródła"). Lines like
    # "- Nazwa: https://…" become links. An empty/missing section → no page, no nav link.
    EXTRA = []
    for pg in cfg.pages:
        slug, label, heading, title, eyebrow = pg["slug"], pg["label"], pg["heading"], pg["title"], pg["eyebrow"]
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
        # "(?km)" = the day is ridden but its distance is unknown; it shows as "? km"
        # and stays out of the total (pair it with show_total_km = false).
        m = re.match(r"(\w+),\s*([\d.]+),\s*(.+?)\s*\((\d+|\?)\s*km\)", desc)
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
    # ---- END parser ----

    return SimpleNamespace(
        md=md, ensure_list_blanks=ensure_list_blanks, linkify_sources=linkify_sources,
        note_html=note_html, cuisine=cuisine, gmaps=gmaps, mapycom=mapycom,
        intro_html=intro_html, note_block=note_block, sources_block=sources_block,
        src_main=src_main, final_note=final_note, EXTRA=EXTRA, DAYS=DAYS,
        total_km=sum(int(d["km"]) for d in DAYS if d["km"].isdigit()))


# =========================================================================
# fact pills (e.g. "+1200 m", "Przełęcz A 1500 m · Przełęcz B 1700 m")
# =========================================================================
_NUM = re.compile(r"^([+~≈-]?\d[\d.,]*)\s+(.*)$")


def _pill_inner(text, nbsp):
    """Leading number is bold, the rest plain. nbsp=True keeps a pill on one line."""
    m = _NUM.match(text)
    rest = lambda s: s.replace(" ", "&nbsp;") if nbsp else s
    if m:
        return f"<b>{m.group(1)}</b> {rest(m.group(2))}"
    return rest(text)


def facts_full(cfg, n_days, total_km):
    out = [f"<span><b>{n_days}</b> dni</span>"]
    if cfg.show_total_km:
        out.append(f"<span><b>{total_km}</b> km</span>")
    for f in cfg.facts:
        # one fact = one span; segments joined by " · " stay unbroken inside
        out.append("<span>" + " · ".join(_pill_inner(s, True) for s in f.split(" · ")) + "</span>")
    return "".join(out)


def facts_mobile(cfg, n_days, total_km):
    out = [f"<li><b>{n_days}</b> dni</li>"]
    if cfg.show_total_km:
        out.append(f"<li><b>{total_km}</b> km</li>")
    for f in cfg.facts:
        for seg in f.split(" · "):             # phone: every segment is its own pill
            out.append(f"<li>{_pill_inner(seg, False)}</li>")
    return "".join(out)


# =========================================================================
# build one trip
# =========================================================================
def asset_dir(slug):
    return os.path.join(SITE, slug, "assets")


def copy_assets(cfg):
    """engine/assets/* then trips/<slug>/assets/* (recursive) -> _site/<slug>/assets/."""
    dst = asset_dir(cfg.slug)
    os.makedirs(dst, exist_ok=True)
    for name in SHARED_ASSETS:
        src = os.path.join(ENGINE_ASSETS, name)
        if not os.path.isfile(src):
            raise SystemExit(f"ERROR: missing shared asset engine/assets/{name}")
        with open(src, "rb") as f:
            data = f.read()
        if name == "map.js":
            data = data.replace(LEGACY_MAP_ACCENT.encode(), cfg.accent.encode())
        with open(os.path.join(dst, name), "wb") as f:
            f.write(data)
    own = os.path.join(TRIPS, cfg.slug, "assets")
    if os.path.isdir(own):
        for base, _dirs, files in os.walk(own):
            rel = os.path.relpath(base, own)
            target = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(target, exist_ok=True)
            for fn in files:
                with open(os.path.join(base, fn), "rb") as fi, open(os.path.join(target, fn), "wb") as fo:
                    fo.write(fi.read())


def build_trip(slug):
    cfg = load_config(slug)
    src = cfg.source if os.path.isabs(cfg.source) else os.path.join(TRIPS, slug, cfg.source)
    if not os.path.exists(src):
        raise SystemExit(f"ERROR: source file not found:\n  {src}")
    with open(src, encoding="utf-8") as f:
        raw = f.read()

    N = parse_note(raw, cfg)
    md, ensure_list_blanks, linkify_sources, note_html = N.md, N.ensure_list_blanks, N.linkify_sources, N.note_html
    DAYS, EXTRA, cuisine = N.DAYS, N.EXTRA, N.cuisine
    TOTAL_KM, gmaps, mapycom = N.total_km, N.gmaps, N.mapycom

    OUT = os.path.join(SITE, slug)
    ASSETS = os.path.join(OUT, "assets")
    os.makedirs(OUT, exist_ok=True)
    for fn in os.listdir(OUT):                 # drop pages of days that no longer exist
        if fn.endswith(".html"):
            os.remove(os.path.join(OUT, fn))
    copy_assets(cfg)

    e = lambda s: htmllib.escape(s, quote=True)
    brand = cfg.title

    FONTS = ('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&'
             'family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=Spline+Sans+Mono:wght@400;500&display=swap')
    LCSS = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
    LJS = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'

    # Analytics are per trip. Empty = nothing is inserted (nothing collected, no consent needed).
    # CookieScript: enable "Google Consent Mode" in its panel so it flips the flags below to
    # 'granted' on accept. GA4 uses Consent Mode v2: everything denied until the user accepts.
    COOKIE = (f'<script type="text/javascript" charset="UTF-8" src="{cfg.cookiescript}"></script>'
              if cfg.cookiescript else "")
    GA = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={cfg.ga_id}"></script>'
          '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
          "gtag('consent','default',{ad_storage:'denied',analytics_storage:'denied',"
          "ad_user_data:'denied',ad_personalization:'denied',wait_for_update:500});"
          f"gtag('js',new Date());gtag('config','{cfg.ga_id}');</script>"
          if cfg.ga_id else "")

    # Accent: one value in trip.toml. CSS variables override the shared style.css; map.js
    # gets it via window.TRIP_ACCENT (and the copy-time replacement, see LEGACY_MAP_ACCENT).
    THEME = f"<style>:root{{--river:{cfg.accent};--river-deep:{cfg.accent_deep}}}</style>"

    # Auto-switch: on a phone, index.html hands over to the single-page offline
    # version. Never a trap — "?full=1" pins the full version and is remembered,
    # and mobile.html links back. Inline + in <head> so it runs before first paint.
    # Detection is device-based (coarse/touch pointer), not window width, so a
    # narrow desktop window keeps the full site.
    # The key is per trip: all trips share one origin, so a shared key would leak the
    # full/mobile choice from one trip into the others.
    view_key = f"{VIEW_KEY}:{slug}"
    SWITCH = ("<script>(function(){try{"
              f"var K='{view_key}';"
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
        # The hamburger is a CSS-only checkbox toggle — no JS, so it works offline too.
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
        # Only linked when # Meta actually carries the address.
        map_links = ("".join(
            f'<a href="{u}" rel="noopener" target="_blank">{lbl}</a>'
            for u, lbl in ((gmaps, "Mapa Google"), (mapycom, "mapy.com")) if u))
        scripts = f'<script src="{asset("site.js")}" defer></script>'
        if with_map:
            scripts = (LJS + f'<script src="{asset("route-data.js")}"></script>'
                       + f'<script>window.MAP_DAY={map_day if map_day else "null"};window.TRIP_ACCENT={json.dumps(cfg.accent)};</script>'
                       + f'<script src="{asset("map.js")}" defer></script>' + scripts)
        return f'''<!doctype html>
<html lang="{cfg.lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link rel="stylesheet" href="{FONTS}"/>
<link rel="stylesheet" href="{asset("style.css")}"/>
{THEME}
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
    <a class="brand" href="index.html"><span class="glyph">{cfg.glyph}</span>{brand}</a>
    {nav}
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap-w">
    <p>{cfg.footer}</p>
    <div class="links">
      <a href="index.html">Trasa</a>{foot_extra}<a href="zrodla.html">Źródła</a>{map_links}
    </div>
  </div>
</footer>
{scripts}
</body>
</html>
'''

    def write(name, text):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)

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

    home_desc = cfg.home_description.replace("{days}", str(len(DAYS))).replace("{km}", str(TOTAL_KM))
    home = f'''
<section class="wrap hero">
  <p class="eyebrow">{cfg.eyebrow}</p>
  <h1>{cfg.title_html}</h1>
  <p class="lede">{cfg.lede}</p>
  <div class="facts">
    {facts_full(cfg, len(DAYS), TOTAL_KM)}
  </div>
  <hr class="river-rule"/>
</section>
<section class="wrap prose">
  {N.intro_html}
</section>
<section class="wrap-w map-section">
  <p class="eyebrow">Mapa trasy</p>
  <div id="map"></div>
  <p class="map-cap">Linia — zapisana trasa z mapy „{cfg.map_caption_name}”. Punkty — najważniejsze miejsca (kliknij, by przejść do dnia). Pozycje miast są poglądowe.</p>
</section>
<section class="wrap">
  <p class="eyebrow">Plan dzień po dniu</p>
  {itin}
  {taste}
</section>
'''
    write("index.html", page(cfg.home_title, home_desc, home, with_map=True, active="trasa", switch=True))

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
        write(f"dzien-{d['num']}.html",
              page(f"Dzień {d['num']}: {d['route']} — {brand}",
                   f"Dzień {d['num']} wyprawy: {d['route']} ({d['km']} km). Miejsca i historia po drodze.",
                   body, with_map=True, active="trasa", map_day=d["num"]))

    sources_body = f'''
<article class="wrap prose">
  <a class="back-plan" href="index.html">← Plan wyjazdu</a>
  <p class="eyebrow">Metoda i odnośniki</p>
  <h1>Źródła i dalsza lektura</h1>
  {note_html(N.note_block)}
  {md(linkify_sources(ensure_list_blanks(N.src_main)))}
  {note_html(N.final_note) if N.final_note else ""}
</article>
'''
    write("zrodla.html",
          page(f"Źródła i dalsza lektura — {brand}",
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
        write(f'{p["slug"]}.html',
              page(f'{p["title"]} — {brand}',
                   f'{p["title"]} — notatki z wyprawy „{brand}”.',
                   body, with_map=False, active=p["slug"]))

    # --- mobile.html: ONE self-contained page, no external requests at all ------
    # Everything (CSS, route sketch) is inline, so the saved file works offline on
    # a phone. No fonts, no Leaflet, no tiles — the map is an inline SVG sketch.
    # ponytail: the "download" button is a plain <a download> to this same file.
    write_mobile(OUT, cfg, N, view_key, route_svg(cfg))

    with open(os.path.join(ASSETS, "_buildid.txt"), "w", encoding="utf-8") as f:
        f.write(str(time.time()))

    pages = 1 + len(DAYS) + 1 + sum(1 for p in EXTRA if p["html"]) + 1   # index, days, zrodla, extras, mobile
    # "card" = everything _site/index.html needs about this trip; it is stored in frozen/
    # too, so a frozen trip is listed without parsing tresc.md or running the generator.
    card = {"accent": cfg.accent, "eyebrow": cfg.eyebrow, "title_html": cfg.title_html,
            "lede": cfg.lede, "show_total_km": cfg.show_total_km, "days": len(DAYS), "km": TOTAL_KM}
    return {"slug": slug, "cfg": cfg, "card": card, "days": len(DAYS), "km": TOTAL_KM,
            "cuisine": len([c for c in cuisine if c[0]]), "pages": pages}


def route_svg(cfg, width=680, height=440, pad=14):
    """Inline SVG sketch of the route from trips/<slug>/assets/route-data.js (no tiles).
    Empty string (= no sketch at all) when the data is missing, or the line has fewer than
    [map] svg_min_points points — a handful of waypoints gives a meaningless zigzag."""
    path = os.path.join(TRIPS, cfg.slug, "assets", "route-data.js")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception:
        return ""
    pts = [(float(la), float(lo)) for la, lo in data.get("route", [])]
    if len(pts) < 2 or len(pts) < cfg.svg_min_points:
        return ""
    lats = [p[0] for p in pts]; lons = [p[1] for p in pts]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
    # crude mercator-ish correction so the shape isn't stretched at higher latitudes
    kx = math.cos(math.radians((la0 + la1) / 2))
    w, h = (lo1 - lo0) * kx, (la1 - la0)
    if w <= 0 or h <= 0:
        return ""
    scale = min((width - 2 * pad) / w, (height - 2 * pad) / h)
    ox = (width - w * scale) / 2
    oy = (height - h * scale) / 2

    def xy(la, lo):
        return (ox + (lo - lo0) * kx * scale, height - oy - (la - la0) * scale)

    line = " ".join("%.1f,%.1f" % xy(la, lo) for la, lo in pts)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3.2"/>' % xy(p["lat"], p["lon"])
                   for p in data.get("pois", [])
                   if "lat" in p and "lon" in p and p.get("day") not in cfg.svg_skip_days)
    return (f'<svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{htmllib.escape(cfg.offline_aria, quote=True)}">'
            f'<polyline points="{line}" fill="none" stroke="currentColor" '
            'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<g class="poi">{dots}</g></svg>')


def write_mobile(out, cfg, N, view_key, svg):
    days, extra = N.DAYS, N.EXTRA
    md, linkify_sources, ensure_list_blanks = N.md, N.linkify_sources, N.ensure_list_blanks
    gmaps, mapycom = N.gmaps, N.mapycom
    css = """
:root{--bg:#fbfcfb;--fg:#1c211f;--mut:#5d6763;--acc:@ACC@;--line:#dfe4e1;--card:#fff}
@media (prefers-color-scheme:dark){
 :root{--bg:#14181a;--fg:#e8ecea;--mut:#9daaa5;--acc:@ACC_DARK@;--line:#2b3235;--card:#1a1f21}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 -webkit-text-size-adjust:100%;max-width:44rem;margin:0 auto;padding:0 16px 28px}
/* Only the JS build gets the fixed bottom bar, so only it needs room underneath. */
.js body{padding-bottom:calc(88px + env(safe-area-inset-bottom))}
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
/* Version link and save pill share one grid cell: link pinned left, pill pinned right.
   The pill's panel is a full-width block inside that same cell, so unfolding pushes the
   page down without ever moving the pill itself. */
.switch{display:grid;align-items:start;padding:18px 0 0;font-size:.85rem;color:var(--mut)}
.switch span{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
/* Switch link first and left-aligned — same corner as the .viewbar link in the full version. */
.switch a{font-weight:600;text-decoration:none;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase}
.switch>a{grid-area:1/1;justify-self:start;align-self:start;padding:6px 0;max-width:60%}
.savebox{grid-area:1/1;justify-self:stretch;text-align:right;
 border:0;background:none;margin:0;border-radius:0;overflow:visible}
/* Filled pill so the download stands out against the plain version-switch link. */
.savebox>summary{display:inline-block;list-style:none;padding:5px 13px;font:inherit;
 font-weight:600;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase;
 background:var(--acc);color:var(--bg);border:1px solid var(--acc);border-radius:999px;
 cursor:pointer;-webkit-tap-highlight-color:transparent}
.savebox-in{text-align:left;margin-top:12px;padding:13px 14px;background:var(--card);
 border:1px solid var(--line);border-radius:12px}
.savebox-in .hint{margin:0 0 11px}
.savebox-in .save{margin:0}
/* Hamburger for the downloaded file. <details> is a native HTML toggle, so it needs
   no JS — and it sits in normal flow, because iOS Quick Look (the Files preview)
   ignores position:fixed. Hidden wherever JS runs: there the bottom bar takes over
   and the live page stays exactly as it was. */
.toc{margin:16px 0 4px}
.js .toc{display:none}
.toc>summary{font-size:.9rem}
/* Two groups: the days, then everything else. Day chips carry their route, so they
   fill the rows and the split reads as grouping rather than as a gap. */
.toc-r{display:flex;flex-wrap:wrap;gap:6px;padding:0 14px}
.toc-r:last-child{padding-bottom:14px}
.toc-r+.toc-r{margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
.toc a{display:inline-flex;align-items:baseline;gap:6px;background:var(--bg);
 border:1px solid var(--line);border-radius:999px;padding:6px 11px;
 font-size:.84rem;font-weight:600;text-decoration:none;color:var(--fg)}
.toc a i{font-style:normal;color:var(--acc);font-variant-numeric:tabular-nums}
.toc a:active{background:var(--acc);color:var(--bg);border-color:var(--acc)}
.toc a:active i{color:var(--bg)}
/* Jump bar pinned to the BOTTOM — thumb zone one-handed. Both it and the sheet rely
   on position:fixed, so they only appear once the inline script marks the page;
   in a preview that ignores fixed they would otherwise sit dead at the very end. */
.navbar{display:none;position:fixed;left:0;right:0;bottom:0;z-index:15;gap:8px;
 padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:var(--bg);border-top:1px solid var(--line)}
.js .navbar{display:flex}
.navbar>*{background:var(--card);border:1px solid var(--line);border-radius:12px;color:var(--fg);
 font:inherit;padding:12px 8px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.nav-a{flex:0 0 3.5rem;font-size:1.15rem;line-height:1}
.nav-c{flex:1;min-width:0;font-size:.9rem;font-weight:600;text-align:center;
 text-decoration:none;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.navbar>*:active{background:var(--acc);color:var(--bg);border-color:var(--acc)}
/* The sheet runs on :target, not on JS — a downloaded file previewed without
   JavaScript (iOS Quick Look does that) still has to navigate. Picking a section
   moves the hash off #sekcje, which closes the sheet and jumps in one tap. */
/* The :target hook is a zero-size marker pinned to the viewport, not the panel
   itself — jumping to a full-screen element makes the browser nudge the page. */
.sheet-anchor{position:fixed;top:0;left:0;width:0;height:0}
.sheet-wrap{display:none;position:fixed;inset:0;z-index:20;pointer-events:none}
.js .sheet-wrap{display:block}
#sekcje:target~.sheet-wrap{pointer-events:auto}
.sheet-back{position:absolute;inset:0;background:rgba(0,0,0,.45);opacity:0;transition:opacity .2s}
#sekcje:target~.sheet-wrap .sheet-back{opacity:1}
.sheet{position:absolute;left:0;right:0;bottom:0;max-height:78vh;overflow-y:auto;
 -webkit-overflow-scrolling:touch;background:var(--card);border-top:1px solid var(--line);
 border-radius:16px 16px 0 0;transform:translateY(101%);transition:transform .25s ease;
 padding-bottom:env(safe-area-inset-bottom)}
#sekcje:target~.sheet-wrap .sheet{transform:translateY(0)}
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
""".replace("@ACC_DARK@", cfg.accent_dark).replace("@ACC@", cfg.accent)
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
    src = md(linkify_sources(ensure_list_blanks(re.sub(r"^>.*$", "", N.sources_block, flags=re.MULTILINE))))
    blocks.append(f'<details id="zrodla"><summary><span>Źródła i linki</span></summary><div>{src}</div></details>')

    # Opening this page (not via the "?full=1" link) means "phone version is what I
    # want" — index.html reads the same key and hands over automatically next time.
    # Kept out of the f-string below so the JS braces need no escaping.
    # The js class gates the arrows (see .nav-a in the CSS). Set in <head> so they
    # never flash in a preview that will not run the rest of the script.
    # Key is per trip (see build_trip): the origin is shared by every trip.
    remember = ("<script>document.documentElement.className+=' js';"
                "(function(){try{"
                "if(!/[?&]full=1/.test(location.search))"
                f"localStorage.setItem('{view_key}','mobile');"
                "}catch(e){}})();</script>")

    # Bottom jump bar: ← / current section / →. Sections are read in order on the
    # road (day after day), so arrows carry the common case and the middle button
    # opens the full list for the random jumps ("what was in Praktyczne again?").
    # One list drives all three — the sheet links, the arrow order and the label.
    # No "mapa" entry when there is no sketch (nothing with id="mapa" to jump to).
    nav_items = [("mapa", "", "Mapa trasy", "")] if svg else []
    nav_items += [(f'dzien-{d["num"]}', f'D{d["num"]}', d["route"], f'{d["km"]} km') for d in days]
    nav_items += [(p["slug"], "", p["title"], "") for p in extra if p["html"]]
    nav_items.append(("zrodla", "", "Źródła i linki", ""))

    sheet_links = "".join(
        f'<a href="#{i}"><span class="s-n">{n}</span>'
        f'<span class="s-t">{t}</span><span class="s-k">{k}</span></a>'
        for i, n, t, k in nav_items)

    # Same targets as the sheet, but as a <details> hamburger in normal flow: the one
    # piece of navigation that survives a preview with no JS and no fixed positioning.
    toc = ('<details class="toc"><summary>☰ Skocz do sekcji</summary><div class="toc-r">'
           + "".join(f'<a href="#dzien-{d["num"]}"><i>{d["num"]}</i>{d["route"]}</a>' for d in days)
           + '</div><div class="toc-r">' + ('<a href="#mapa">Mapa</a>' if svg else "")
           + "".join(f'<a href="#{p["slug"]}">{p["label"]}</a>' for p in extra if p["html"])
           + '<a href="#zrodla">Źródła</a></div></details>')
    # "#zamknij" matches no element on purpose: the hash stops matching #sekcje, so
    # the sheet closes and the page stays exactly where it was.
    navbar = (
        '<div class="navbar">'
        '<button type="button" class="nav-a" data-go="-1" aria-label="Poprzednia sekcja">←</button>'
        '<a class="nav-c" id="nav-c" href="#sekcje">Sekcje ▾</a>'
        '<button type="button" class="nav-a" data-go="1" aria-label="Następna sekcja">→</button>'
        '</div>'
        '<span class="sheet-anchor" id="sekcje" aria-hidden="true"></span>'
        '<div class="sheet-wrap">'
        '<a class="sheet-back" href="#zamknij" aria-label="Zamknij spis"></a>'
        '<nav class="sheet" aria-label="Spis sekcji"><div class="sheet-in">'
        '<div class="sheet-hd">Skocz do sekcji<a class="sheet-x" href="#zamknij">✕</a></div>'
        f'{sheet_links}</div></nav></div>')

    # Anchors into a <details> only scroll to it, they don't expand it — open it
    # ourselves so a jump actually reveals the section instead of a closed card.
    # The label doubles as a "you are here" readout, updated on scroll.
    ids = json.dumps([i for i, _n, _t, _k in nav_items], ensure_ascii=False)
    labels = json.dumps([(f"{n} · {t}" if n else t) for _i, n, t, _k in nav_items], ensure_ascii=False)
    jumpnav = ("<script>(function(){"
               f"var IDS={ids},LAB={labels};"
               "var cap=document.getElementById('nav-c');"
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
               "var a=ev.target.closest('.sheet a[href^=\"#\"],.toc a[href^=\"#\"]');"
               "if(a)open_(a.getAttribute('href').slice(1));"
               "});"
               "var wait=false;addEventListener('scroll',function(){if(wait)return;wait=true;"
               "requestAnimationFrame(function(){paint();wait=false;});},{passive:true});"
               "if(location.hash)open_(location.hash.slice(1));"
               "paint();"
               "})();</script>")

    # Route sketch (inline SVG) + hint. Without a sketch only the online-map links remain.
    om = ([f'<a href="{gmaps}">Google</a>'] if gmaps else []) + \
         ([f'<a href="{mapycom}">mapy.com</a>'] if mapycom else [])
    online = ("Mapy online: " + " · ".join(om)) if om else ""
    if svg:
        note = f"; {cfg.svg_skip_note}" if cfg.svg_skip_note else ""
        mapblock = (f'<div class="map" id="mapa">{svg}</div>\n'
                    f'<p class="hint">Szkic trasy ze śladu GPS (bez podkładu — działa offline). '
                    f'Kropki to punkty z planu{note}.\n{online}</p>')
    else:
        mapblock = f'<p class="hint">{online}</p>'

    e = lambda s: htmllib.escape(s, quote=True)
    html = f'''<!doctype html>
<html lang="{cfg.lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{e(cfg.title)} — wersja offline</title>
{remember}
<meta name="description" content="Cała wyprawa na jednej stronie, bez internetu: plan dzień po dniu, praktyczne informacje, ciekawostki."/>
<style>{css}</style>
</head>
<body>
<nav class="switch"><a href="index.html?full=1">🗺 Wersja pełna</a>
<details class="savebox"><summary>⬇︎ Zapisz</summary><div class="savebox-in">
<p class="hint"><b>iPhone:</b> dotknij przycisku → „Pobierz". Plik ląduje w <b>Plikach → Pobrane</b>;
podgląd w Plikach wystarczy, menu „☰ Skocz do sekcji" jest na górze strony.</p>
<a class="save" href="mobile.html" download="{e(cfg.offline_filename)}">⬇︎ Pobierz</a>
</div></details></nav>
<h1 id="top">{cfg.title}</h1>
<p class="sub">{cfg.eyebrow}</p>
<ul class="facts">
  {facts_mobile(cfg, len(days), N.total_km)}
</ul>

{toc}

{mapblock}

<h2 id="plan">Plan dzień po dniu</h2>
{"".join(blocks[:len(days)])}

<h2>Reszta</h2>
{"".join(blocks[len(days):])}

<footer>{cfg.footer_short} · <a href="index.html?full=1">wersja pełna z interaktywną mapą</a><br>
Na telefonie strona główna sama przenosi tutaj. Otwarcie wersji pełnej jest pamiętane w tej przeglądarce; wejście na tę stronę wraca do wersji telefonowej.</footer>
{navbar}
{jumpnav}
</body>
</html>
'''
    with open(os.path.join(out, "mobile.html"), "w", encoding="utf-8") as f:
        f.write(html)


# =========================================================================
# _site/index.html — list of trips
# =========================================================================
def write_site_index(results):
    items = []
    for r in results:
        c = r["card"]
        km = f' · {c["km"]} km' if c["show_total_km"] else ""
        items.append(
            f'<li style="--acc:{c["accent"]}"><a href="{r["slug"]}/">'
            f'<span class="eb">{c["eyebrow"]}</span>'
            f'<span class="tt">{c["title_html"].replace("<br>", " ")}</span>'
            f'<span class="ld">{c["lede"]}</span>'
            f'<span class="st">{c["days"]} dni{km}</span></a></li>')
    # Self-contained on purpose: system fonts, no external requests.
    page = f'''<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Wyprawy rowerowe</title>
<meta name="description" content="Notatki z wypraw rowerowych."/>
<style>
:root{{--bg:#fbfcfb;--fg:#1b211e;--mut:#69706b;--line:#e3e7e3;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14181a;--fg:#e8ecea;--mut:#9daaa5;--line:#2b3235;--card:#1a1f21}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:44rem;margin:0 auto;padding:0 16px 40px}}
h1{{font-size:1.9rem;line-height:1.15;margin:32px 0 18px;letter-spacing:-.02em}}
ul{{list-style:none;margin:0;padding:0;display:grid;gap:12px}}
li a{{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);
 border-left:4px solid var(--acc);border-radius:12px;padding:14px 16px}}
li a:hover,li a:focus-visible{{border-color:var(--acc)}}
span{{display:block}}
.eb{{color:var(--acc);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase}}
.tt{{font-size:1.25rem;font-weight:700;margin:2px 0 4px}}
.ld{{color:var(--mut);font-size:.95rem}}
.st{{margin-top:8px;font-size:.85rem;font-variant-numeric:tabular-nums}}
</style>
</head>
<body>
<main>
<h1>Wyprawy rowerowe</h1>
<ul>
{chr(10).join(items)}
</ul>
</main>
</body>
</html>
'''
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


# =========================================================================
# discovery, watch, serve
# =========================================================================
def list_trips():
    if not os.path.isdir(TRIPS):
        return []
    out = []
    for name in sorted(os.listdir(TRIPS)):
        p = os.path.join(TRIPS, name)
        if name.startswith(("_", ".")) or not os.path.isdir(p):
            continue
        if not os.path.isfile(os.path.join(p, "trip.toml")):
            print(f"(skipping trips/{name}: no trip.toml)")
            continue
        out.append(name)
    return out


# =========================================================================
# freezing: a finished trip is copied from trips/<slug>/frozen/, never regenerated
# =========================================================================
FROZEN_DIRNAME = "frozen"
FREEZE_META = "_freeze.json"      # sits in frozen/, is never copied into _site/
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def frozen_path(slug):
    return os.path.join(TRIPS, slug, FROZEN_DIRNAME)


def read_freeze_date(slug):
    """[freeze] date from trip.toml as datetime.date, or None when the trip has no [freeze].
    Deliberately NOT part of load_config(): a frozen trip must not depend on the generator's
    config validation. A [freeze] table without a valid date is an error, never a silent
    'not frozen' (a typo would otherwise switch freezing off)."""
    rel = f"trips/{slug}/trip.toml"
    try:
        with open(os.path.join(TRIPS, slug, "trip.toml"), "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None                  # load_config() reports this properly on the normal path
    if "freeze" not in data:
        return None
    fr = data["freeze"]
    v = fr.get("date") if isinstance(fr, dict) else None
    if isinstance(v, datetime.datetime):
        v = v.date()
    if isinstance(v, str) and _ISO_DATE.match(v):
        try:
            v = datetime.date.fromisoformat(v)
        except ValueError:
            v = None
    if not isinstance(v, datetime.date):
        raise SystemExit(f'ERROR: {rel}: [freeze] needs date = "YYYY-MM-DD" (a valid date).')
    return v


def _input_hashes(slug, source):
    """sha256 of everything a trip's page is built from: trip.toml, the note, own assets.
    Content hashes, not mtimes: a git checkout gives every file a fresh mtime, so mtimes
    cannot tell a real edit from a clone."""
    base = os.path.join(TRIPS, slug)
    paths = [os.path.join(base, "trip.toml"),
             source if os.path.isabs(source) else os.path.join(base, source)]
    for root, _dirs, files in os.walk(os.path.join(base, "assets")):
        paths.extend(os.path.join(root, fn) for fn in files)
    out = {}
    for p in paths:
        if os.path.isfile(p):
            with open(p, "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
            out[os.path.relpath(p, base).replace(os.sep, "/")] = hashlib.sha256(data).hexdigest()
    return out


def write_freeze(slug, result):
    """Copy the freshly built _site/<slug>/ to trips/<slug>/frozen/ (+ _freeze.json).
    Written next to the target and swapped in, so a failure never leaves half a frozen/."""
    cfg = result["cfg"]
    dst = frozen_path(slug)
    tmp = dst + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(os.path.join(SITE, slug), tmp)
    meta = {"slug": slug, "frozen_on": datetime.date.today().isoformat(),
            "source": cfg.source, "inputs": _input_hashes(slug, cfg.source), "card": result["card"]}
    with open(os.path.join(tmp, FREEZE_META), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    shutil.rmtree(dst, ignore_errors=True)
    os.rename(tmp, dst)


def restore_frozen(slug):
    """Frozen trip: copy frozen/ -> _site/<slug>/. No config, no parser, no generator."""
    fdir = frozen_path(slug)
    try:
        with open(os.path.join(fdir, FREEZE_META), encoding="utf-8") as f:
            meta = json.load(f)
        card, inputs, source = meta["card"], meta["inputs"], meta["source"]
        if not os.path.isfile(os.path.join(fdir, "index.html")):
            raise KeyError("index.html")
    except (OSError, ValueError, KeyError):
        raise SystemExit(f"ERROR: trips/{slug}/frozen/ is damaged (no index.html or {FREEZE_META}). "
                         f"If this is on purpose: python build.py {slug} --refreeze")
    out = os.path.join(SITE, slug)
    shutil.rmtree(out, ignore_errors=True)         # nothing of a previous (normal) build may survive
    shutil.copytree(fdir, out, ignore=shutil.ignore_patterns(FREEZE_META))
    now = _input_hashes(slug, source)
    changed = sorted(k for k in set(now) | set(inputs) if now.get(k) != inputs.get(k))
    return card, meta.get("frozen_on", "?"), changed


def loud(title, lines):
    """Hard to miss in a terminal; in GitHub Actions also an annotation on the run."""
    bar = "!" * 72
    print("\n".join(["", bar, f"!! {title}"] + [f"!! {l}" for l in lines] + [bar, ""]))
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning title={title}::" + " ".join(lines))


def process_trip(slug, refreeze=False):
    """Decide build vs. frozen copy for one trip. Returns the build_trip-style result dict."""
    fd = read_freeze_date(slug)
    today = datetime.date.today()
    if refreeze and fd is None:
        raise SystemExit(f"ERROR: {slug}: --refreeze makes no sense — the trip has no [freeze] date in trip.toml.")

    if fd is None or today < fd:                              # 1. no freeze / 2. not yet
        s = build_trip(slug)
        s["lines"] = [f"✓ Built: _site/{slug}  (days: {s['days']}, km: {s['km']}, dishes: {s['cuisine']})"]
        if refreeze:
            s["lines"].append(f"(--refreeze: freeze date {fd} has not passed yet — leaving frozen/ alone)")
        return s

    fdir = frozen_path(slug)
    if refreeze or not os.path.isdir(fdir):                   # 6. refreeze / 3. first freeze
        s = build_trip(slug)                                  # on failure frozen/ stays as it was
        write_freeze(slug, s)
        s["lines"] = [f"✓ Built: _site/{slug}  (days: {s['days']}, km: {s['km']}, dishes: {s['cuisine']})"]
        if refreeze:
            s["lines"].append(f"♻ Rebuilt frozen trip {slug} and overwrote trips/{slug}/frozen/ "
                              f"— review the result and COMMIT frozen/.")
        else:
            s["after"] = lambda: loud(f"FROZE TRIP {slug} (freeze date {fd})", [
                f"The finished site is stored in trips/{slug}/frozen/ — that is now the only source of this trip.",
                f"COMMIT it:  git add trips/{slug}/frozen && git commit",
                "Without that, the next build (e.g. GitHub Actions) regenerates the site from scratch and nothing is frozen."])
        return s

    card, frozen_on, changed = restore_frozen(slug)           # 4. frozen: generator is NOT run
    s = {"slug": slug, "card": card, "days": card["days"], "km": card["km"]}
    s["lines"] = [f"❄ Frozen: {slug} ({fd}) — copied from trips/{slug}/frozen/ "
                  f"(days: {card['days']}, km: {card['km']})"]
    if changed:                                               # 5. edited after freezing
        s["after"] = lambda: loud(f"EDIT TO FROZEN TRIP {slug} — HAS NO EFFECT", [
            f"Changed after the freeze ({frozen_on}): {', '.join(changed)}.",
            f"The change has no effect: the published site is the copy from trips/{slug}/frozen/.",
            f"To unfreeze on purpose: python build.py {slug} --refreeze  (then commit frozen/)."])
    return s


def build_many(slugs, with_index, refreeze=False):
    """Build (or copy, if frozen) the given trips; a failing trip does not stop the others.
    Raises SystemExit at the end if anything failed."""
    results, errors = [], []
    for slug in slugs:
        try:
            s = process_trip(slug, refreeze)
            results.append(s)
            for line in s["lines"]:
                print(line)
            if "after" in s:
                s["after"]()
        except SystemExit as e:
            errors.append((slug, e))
            print(f"✗ {slug}: {e}")
    if with_index and results:
        write_site_index(results)
        print(f"✓ Built: _site/index.html  ({len(results)} trips)")
    if errors:
        raise SystemExit(f"ERROR: {len(errors)} of {len(slugs)} trips failed to build: "
                         + ", ".join(s for s, _ in errors))
    return results


def snapshot(slugs):
    paths = []
    def add_dir(d):
        for base, _dirs, files in os.walk(d):
            paths.extend(os.path.join(base, fn) for fn in files)
    add_dir(ENGINE_ASSETS)
    for slug in slugs:
        paths.append(os.path.join(TRIPS, slug, "trip.toml"))
        try:
            cfg_src = load_config(slug).source
        except SystemExit:
            cfg_src = "tresc.md"
        paths.append(cfg_src if os.path.isabs(cfg_src) else os.path.join(TRIPS, slug, cfg_src))
        add_dir(os.path.join(TRIPS, slug, "assets"))
    return tuple(sorted((p, os.path.getmtime(p)) for p in paths if os.path.exists(p)))


def serve_background(directory):
    import http.server, socketserver, threading, functools
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    port = 8000
    httpd = None
    while port < 8010:
        try:
            httpd = socketserver.TCPServer(("", port), handler); break
        except OSError:
            port += 1
    if not httpd:
        raise SystemExit("Could not start the preview (ports 8000-8009 are in use).")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__); return
    flags = [a for a in args if a.startswith("--")]
    bad = [a for a in flags if a not in ("--serve", "--watch", "--refreeze")]
    names = [a for a in args if not a.startswith("--")]
    if bad or len(names) > 1:
        raise SystemExit("Usage: python engine/build.py [<slug>] [--serve|--watch] | <slug> --refreeze")
    serve, watch, refreeze = "--serve" in flags, "--watch" in flags, "--refreeze" in flags
    if refreeze and not names:
        raise SystemExit("ERROR: --refreeze needs one trip: python build.py <slug> --refreeze\n"
                         "Refusing without a slug, so that every trip is not unfrozen at once.")
    if refreeze and (serve or watch):
        raise SystemExit("ERROR: --refreeze does not combine with --serve/--watch (every save would overwrite frozen/).")

    available = list_trips()
    if names:
        slug = names[0].strip("/")
        if slug not in available:
            raise SystemExit(f"ERROR: no trip \"{slug}\" (with a trip.toml) in trips/. Available: "
                             + (", ".join(available) or "none"))
        slugs = [slug]
    else:
        slugs = available
        if not slugs:
            raise SystemExit("ERROR: no trips found in trips/ (a trip needs trips/<slug>/trip.toml).")
    with_index = not names

    try:
        build_many(slugs, with_index, refreeze)
    except SystemExit as e:
        if not (watch or serve):
            raise
        print(e)
        print("Fix the note and save — I'll try again...\n")

    if not (serve or watch):
        return

    os.makedirs(SITE, exist_ok=True)
    port = serve_background(SITE)
    url = f"http://localhost:{port}/" + (f"{slugs[0]}/index.html" if names else "")
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
            snap = snapshot(slugs)
            if snap != last:
                if last is not None:
                    stamp = datetime.datetime.now().strftime("%H:%M:%S")
                    try:
                        build_many(slugs, with_index)
                        print(f"[{stamp}] ✓ rebuilt")
                    except SystemExit as e:
                        print(f"[{stamp}] {e}")
                last = snap
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()
