# Instructions for the agent (Claude Code) working in this repo

The repo generates the sites of several cycling trips: **one engine, many trips**.
Each trip's source is `trips/<slug>/tresc.md`; the build turns it into a static site
published by GitHub Actions: `anks.pl/cycling_trips/` (the list of trips) →
`anks.pl/cycling_trips/<slug>/`.

## Language

- **Everything on GitHub is in English**: code, comments, CLI messages, docs,
  README files, commit messages, PR titles and bodies.
- **Only the published page content is in Polish**: `trips/<slug>/tresc.md`, the string
  values in `trip.toml` (title, lede, footer, page labels…) and the Polish UI literals
  inside the engine's HTML templates (`Dzień`, `Źródła`, `Plan wyjazdu`, …). Those are
  what the reader sees — do not translate them.
- The markdown heading contract below is part of the content, so its headings stay
  Polish too.
- **A frozen trip's own files are never touched**, not even to translate a comment:
  the freeze hash covers whole files, so any edit makes every later build warn about
  a change that cannot have an effect.

## Layout

```
engine/build.py       generator (shared by every trip)
engine/gen_route.py   route.gpx|kml + pois.csv -> trips/<slug>/assets/route-data.js
engine/assets/        style.css, map.js, site.js — shared by every trip
trips/<slug>/         tresc.md, trip.toml, pois.csv, route.gpx|kml, assets/
trips/_template/      an empty trip to copy; the build skips it
build.py              thin launcher in the root -> engine/build.py
site.toml             settings for the whole site: list-page title, shared analytics
_site/                BUILD OUTPUT, in .gitignore
```

## What may be edited

- **`trips/<slug>/tresc.md`** — the content source. Almost every request ("add a note
  about Theth", "fix the distance on day 4") means editing this file in the right trip.
- `trips/<slug>/trip.toml` — name, hero, subpages, accent colour, analytics.
- `trips/<slug>/TODO.md` — open questions for that trip, if it has any. Not
  published; read it before asking the owner something already settled there.
- `trips/<slug>/pois.csv` (columns `day,name,lat,lon,blurb`; extra columns are copied
  onto the point) and `route.gpx`/`route.kml` — map points and track. After a change:
  `python engine/gen_route.py <slug>`.
- **`_site/` is generated** — never edit it by hand and never commit it
  (`.gitignore`; changes would be lost on the next build anyway).
- **`trips/<slug>/assets/route-data.js` is generated** by `gen_route.py` — do not edit
  it by hand as long as the trip has a `route.gpx`/`route.kml`.
- **Exception: `trips/rumunia-2026/`** has no track file, so its `assets/route-data.js`
  is the **only copy of that route**. Do not regenerate or overwrite it.

## Careful: engine/ touches EVERY trip

A change in `engine/` (build.py, `engine/assets/*`) changes **every** trip at once —
including the ones nobody asked about. Before committing, build them all
(`python build.py`, no argument) and check that none of them reports an error.
Anything trip-specific (text, colours, subpages, analytics) belongs in `trip.toml`,
not in the engine.

Finished trips are **frozen** (`[freeze] date` in `trip.toml`): from that date on the
generator is not run for them at all and `trips/<slug>/frozen/` is copied instead, so an
engine change cannot silently alter a trip nobody tests any more. See PLAYBOOK.md,
section 2.

## The heading contract in tresc.md — breaking it fails the build

Keep exactly these headings and this format (they are Polish because they are content):

- `# Meta` … `# Klucz do wyjazdu — …` (em dash required) … `# Plan wyjazdu`
- every day: `## Dzień <nr>: <Weekday>, <DD.MM.YYYY>, <from> > <to> (<NN>km)`
- optional inside a day: `### Miejsca i historia` (everything after it is the day's
  main text)
- the plan section ends with a `---` line, then a blank line, the block
  `> [!note] Skąd te notatki`, a blank line and `---` again
- `# Źródła i dalsza lektura` (required)
- subpages from `[[pages]]` in `trip.toml` (e.g. `# Praktyczne informacje`,
  `# Kulinaria i pamiątki`, `# Ciekawostki`) — the heading in `tresc.md` must match
  `heading` in `trip.toml`; an empty or missing section means no subpage, not an error

Inside `# Meta`, lines shaped `- Name - description` become the "Czego spróbować" pills
on the home page; lines starting with `Opis:`, `Mapa …:`, `Szlak:` become links (the
prefix list is `meta_skip_prefixes` in `trip.toml`). A correct example file:
`trips/_template/tresc.md`.

## How to check you have not broken the build

```sh
python build.py albania-2026   # must print "✓ Built: _site/albania-2026 (days: N, km: N, dishes: N)"
python build.py                # every trip + _site/index.html with the list
```

`ERROR: section not found …` means a heading was renamed or removed.
Live preview: `python build.py <slug> --watch` (or `--serve`).

## A new trip

1. `cp -r trips/_template trips/<slug>` and fill in `trip.toml` (including
   `slug` = the directory name).
2. Write `tresc.md`, add `route.gpx`/`route.kml` and `pois.csv`.
3. `python engine/gen_route.py <slug>`, then `python build.py <slug>`.
4. Ask the owner for the trip's freeze date and put it in `[freeze] date`.

## Publishing

- The workflow `.github/workflows/deploy.yml` runs **only on a push to `main`** and
  builds every trip at once (`python build.py`), with `_site/` as the artifact.
- Working from a phone or the cloud: **commit and push straight to `main`**, do not open
  a PR — otherwise the site does not refresh until someone merges it.
- After pushing, check that Actions are green.

## Two versions of every trip (both from the same `tresc.md`)

- `index.html` + `dzien-N.html` + subpages — the full version with an interactive map.
- `mobile.html` — a single page, fully offline (CSS and the SVG map live inside the
  file, zero network requests). On a touch device `index.html` redirects there by
  itself; the "full version" choice is remembered in `localStorage['gp-view:<slug>']`
  (separately for each trip).

Never add external fonts, scripts or images to `mobile.html` — working without internet
is the entire point of that page.
