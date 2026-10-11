# How to edit a trip site in Obsidian (with live preview)

You edit **one file** — `trips/<trip>/tresc.md`. A background script rebuilds the site
after every save and the preview in the browser **refreshes itself**. You never touch
the HTML.

Note on language: the pages are written in Polish, so `tresc.md`, the texts in
`trip.toml` and the headings below stay Polish. Everything else in the repo — code,
comments, docs, commit messages — is English.

## What is in the repo
```
trips/
  albania-2026/        one trip:
    tresc.md             ← THIS IS WHAT YOU EDIT (a markdown note)
    trip.toml            name, hero, subpages, colour, analytics
    pois.csv             map points (day,name,lat,lon,blurb)
    route.gpx            the track (or route.kml)
    assets/              route-data.js (generated) + your photos
  rumunia-2026/        the second trip (no track file — see below)
  _template/           an empty trip to copy when starting a new one
engine/                the engine shared by every trip (leave it alone unless you must)
build.py               launcher: python build.py <trip> [--watch]
build-windows.bat      double-click on Windows (live preview)
build-mac-linux.command  double-click on Mac/Linux (live preview)
_site/                 OUTPUT: the finished sites (generated, in .gitignore, do not edit)
```

## Once, at the start
You need **Python 3.11 or newer** (`python --version`; if you have none,
https://www.python.org/downloads/, and on Windows tick "Add Python to PATH").
The `markdown` library installs itself on the first run.

## Connecting Obsidian
In Obsidian: *Open another vault → Open folder as vault* and point it at this repo (or
at `trips/<trip>` alone). `tresc.md` shows up as an ordinary note.

## Working with the live preview
1. Start live mode:
   - **Windows:** double-click `build-windows.bat`
   - **Mac:** double-click `build-mac-linux.command` (if the system blocks it:
     right-click → Open → Open)
   - **or in a terminal** in the repo directory: `python build.py albania-2026 --watch`
   With no argument the launchers ask for the trip name (the directory name in `trips/`).
2. The preview opens in the browser. **Leave that window running.**
3. Edit `tresc.md` and save (Ctrl/Cmd+S). A moment later the page refreshes itself.
4. When you are done, `Ctrl+C` in the script window.
5. Publishing: just **push to the `main` branch** — GitHub Actions builds every trip and
   publishes it at `anks.pl/cycling_trips/<trip>/`. The local preview is only for
   looking at the changes before pushing.

> A one-off build without the preview: `python build.py albania-2026` (one trip)
> or `python build.py` (all of them + the page listing the trips).

## Rules for writing tresc.md (so the script does not get lost)
The script recognises content by its headings — **keep these names and this format**:

- `# Meta` — lines shaped `- Name - description` become the dishes on the home page
  ("Czego spróbować"); lines `Opis:`, `Mapa …:`, `Szlak:` become links.
- `# Klucz do wyjazdu — ...` (with an em dash) → the intro on the home page.
- `# Plan wyjazdu` → the start of the plan (a `---` line ends it, followed by the block
  `> [!note] Skąd te notatki`, again wrapped in `---`).
- Every day starts with a line:
  ```
  ## Dzień 3: Niedziela, 16.08.2026, Gusinje > Rugova (42km)
  ```
  that is, `## Dzień <no>: <weekday>, <date>, <from> > <to> (<km>km)`.
  The arrow comes from the `>` character; the number before `km` feeds the summaries.
- `-` bullets right under a day heading → the **"W skrócie"** box.
- Everything after `### Miejsca i historia` → the day's main text.
- Sub-bullets are made by indenting (Tab or 4 spaces). Bold `**text**`, italics `_text_`.
- `# Źródła i dalsza lektura` → the sources page. Write links as
  `- Label: https://address` and they become clickable.
- Obsidian links `[[Something]]` turn into plain text (they do not break the page).

A "section not found…" message means one of those headings disappeared or was renamed —
put it back and save. In `--watch` mode the script retries after the next save.

A correct example file: `trips/_template/tresc.md`.

## Other changes
- **A new day:** paste another `## Dzień N: ...` block into the `# Plan wyjazdu` section.
- **A new subpage** (a glossary, say): a `[[pages]]` block in `trip.toml` + a `# Heading`
  section in `tresc.md` (before `# Źródła i dalsza lektura`); the heading must match
  `heading`.
- **Name, description, hero facts, colour, analytics:** `trips/<trip>/trip.toml`.
- **Colours and look shared by every trip:** `engine/assets/style.css` — careful, a
  change there touches **every** trip.
- **Photos:** drop them in `trips/<trip>/assets/` and reference them in the note as
  `![description](assets/file.jpg)` (Obsidian's `![[file.jpg]]` works too).
- **A new trip:** copy `trips/_template` to `trips/<slug>`, fill in `trip.toml`,
  `tresc.md`, `pois.csv`, add `route.gpx`, run `python engine/gen_route.py <slug>`.

## The map — where it comes from

`trips/<trip>/assets/route-data.js` is **generated** by `engine/gen_route.py` from:

- `route.gpx` or `route.kml` — the route line, simplified to roughly 1000 points,
- `pois.csv` — the map points, header `day,name,lat,lon,blurb` (extra columns such as
  `type` are copied onto the point). Quote a blurb that contains commas.

```
python engine/gen_route.py albania-2026
```

- Changing the **track** → swap `route.gpx`/`route.kml` and run the script.
- Changing the **points** (name, blurb, day) → edit `pois.csv` and run the script.
- Hand edits in `route-data.js` disappear the next time the script runs.

**Romania has no track file.** Its `route-data.js` is the only copy of that route — the
script refuses to regenerate it and overwrites nothing. Do not delete that file.

## Two versions of every trip

The build makes **two** versions from the same `tresc.md`:

- `index.html` + `dzien-N.html` + subpages — the **full version**: an interactive
  Leaflet map, Google fonts, one page per day.
- `mobile.html` — **a single page, fully offline**: all the CSS and the route sketch
  (SVG) live inside the file, zero network requests. Days and sections are collapsible
  `<details>`. The sketch is not drawn when the track has fewer than `svg_min_points`
  points (`trip.toml`).

**Switching.** On a phone `index.html` sends you to `mobile.html` by itself (detected by
device: `pointer:coarse`, or a touch screen plus a narrow viewport — a narrow window on a
desktop stays on the full version). The "Wersja pełna z mapą" link on the mobile page
goes to `index.html?full=1`, and that choice is remembered separately for each trip
(`localStorage['gp-view:<trip>']`). The full version's navigation carries a
"📱 Telefon" link back.

**Saving offline.** The "Zapisz tę stronę offline" button is a plain `<a download>` link
to `mobile.html` — Safari on an iPhone saves it into Files, and opened from disk it looks
exactly the same.
