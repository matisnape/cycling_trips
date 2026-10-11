# Playbook: a new trip site

How the sites are built and how to add another one. For you and for the agent
(Claude Code).

Language rule: everything in this repo is written in English — code, comments, docs,
commit messages. The only Polish is what readers see on the published pages:
`tresc.md`, the strings in `trip.toml` and the markdown heading contract.

---

## 1. The system in 30 seconds

**The engine is the coffee machine, a trip is a capsule.** There is one machine
(`engine/`); every trip is a capsule in `trips/<slug>/`. A new trip means a new
capsule — you do not touch the machine.

```
trips/<slug>/
  trip.toml    ─┐  title, hero, facts, subpages, colour, analytics, freeze date
  tresc.md     ─┼─►  engine/build.py  ─►  _site/<slug>/index.html     home page + map
  pois.csv      │                                      dzien-N.html     day by day
  route.gpx/kml ┤                                      <subpage>.html   from [[pages]]
  assets/       │                                      zrodla.html
   route-data.js ◄── engine/gen_route.py               mobile.html      1 file, offline
  frozen/      ─┘  the frozen copy of the site (see section 2)
engine/assets/ (style.css, map.js, site.js) ─► copied into every trip
                                               _site/index.html        list of all trips
```

| File | What it does | Who edits it |
|---|---|---|
| `trips/<slug>/tresc.md` | all the content, heading contract → `HOW-TO-EDIT.md` | you, daily |
| `trips/<slug>/trip.toml` | title, hero, facts, subpages, colour, GA, **freeze date** | once, at setup |
| `trips/<slug>/pois.csv` | map points: `day,name,lat,lon,blurb` | once + fixes |
| `trips/<slug>/route.gpx` / `.kml` | the track | once |
| `trips/<slug>/assets/route-data.js` | **generated** from the two above | never by hand |
| `trips/<slug>/frozen/` | the frozen site, **kept in the repo** | only via `--refreeze` |
| `engine/build.py` | the generator | only deliberately (touches every unfrozen trip) |
| `engine/assets/*` | shared look and map | same |
| `_site/` | the output, not in the repo | never |

**Addresses:** `anks.pl/cycling_trips/` (the list) → `anks.pl/cycling_trips/<slug>/`.
**Publishing:** push to `main` → GitHub Actions builds everything (~1–2 min).

---

## 2. Freezing trips — read this before starting a new one

A trip that is over **should not be regenerated any more**. Nobody tests it, and any
change in `engine/` could quietly break it — with nobody noticing.

> This is not theory. In Albania the offline route-sketch filter cut out the "bus day".
> After the plan was renumbered from 10 days to 8 the day number shifted and the filter
> started cutting out the Valbona valley instead, keeping the bus points. The bug
> survived two months, because nobody looked.

**How it works:**

1. In `trip.toml` you set `[freeze] date = "YYYY-MM-DD"` — usually the day after you
   get back.
2. Before that date the build generates the site normally, on every push.
3. **On the freeze date** the first build writes the finished site into
   `trips/<slug>/frozen/` and you commit it. The build says so loudly.
4. **After that date** the build does not run the generator for that trip — it only
   copies `frozen/` into `_site/<slug>/`. Changes in `engine/` physically cannot reach it.
5. If you edit a frozen trip's `tresc.md`, the build notices and **warns** that the
   change has no effect.
6. Deliberate unfreezing: `python build.py <slug> --refreeze` — rebuilds and overwrites
   `frozen/`. Do it only when you really mean to and will look at the result.

**Frozen today:** `albania-2026`, `rumunia-2026`.

Their own files are left exactly as they were, Polish comments in `trip.toml` and
`route-data.js` included. The freeze hash covers whole files, so even a reworded
comment would make every later build warn about a change that has no effect. The
English-only rule therefore applies to everything except a frozen trip's own files.

---

## 3. What every trip gets for free, from the engine

- Home page: hero, facts, the intro from `# Klucz do wyjazdu`, an interactive map
  (Leaflet), the day plan, "Czego spróbować".
- A page per day: the map zoomed to that day's points, "W skrócie",
  "Miejsca i historia", ← →.
- Subpages from `[[pages]]` (Praktyczne, Słowniczek, Kulinaria…) plus Źródła.
- `mobile.html`: one page, **zero network requests**, the route as inline SVG, a bottom
  ← Sections → bar, a hamburger that works without JS, a "Zapisz" button.
- A phone landing on `index.html` is moved to `mobile.html` by itself (the choice is
  remembered **separately for each trip**).
- Versioned CSS/JS (`?v=hash`) — a phone does not keep the old look.

---

## 4. A new trip, step by step

### Step 0. Collect the input (checklist)

- [ ] the day-by-day plan note (Obsidian)
- [ ] the track: KML from Google My Maps (*⋮ → Export to KML/KMZ → KML*) or a GPX
- [ ] a link to the Google / mapy.com map
- [ ] dates, countries, daily distances (if known)
- [ ] **the freeze date** — usually the day after you get back. Do not start a trip
      without it

> **Agent: always ask for the freeze date**, for every new trip, even when the rest of
> the input is complete. It is the one field that cannot be inferred from the material.

### Step 1. The folder

```sh
cp -r trips/_template trips/country-2027    # slug: <country>-<year>, lowercase, ASCII only
cp ~/Downloads/route.kml trips/country-2027/route.kml
```

### Step 2. `trip.toml`

- [ ] `slug` = the folder name
- [ ] `title`, `title_html`, `eyebrow`, `lede`, `home_title`, `home_description`, `footer`
- [ ] `facts` (elevation gain, the highest pass…)
- [ ] `show_total_km = false` if any day has `?km`
- [ ] `[[pages]]` — only the sections that will exist in `tresc.md`
- [ ] **`[freeze] date`**
- [ ] optionally `[theme] accent`, `[analytics]`

### Step 3. The map

- [ ] `pois.csv`: 2–5 points per day, `day` = the day number from `tresc.md`
- [ ] `python engine/gen_route.py country-2027` → check the track distance matches
- [ ] points far from the route (a bus, a side trip) → put their day in
      `[map] svg_skip_days`

### Step 4. `tresc.md`

Fastest: hand the agent the note plus the template. By hand: fill in
`trips/_template/tresc.md`. The contract in brief (full version in `HOW-TO-EDIT.md`):

- [ ] `# Meta` → `# Klucz do wyjazdu — „…"` → `---` → `# Plan wyjazdu`
- [ ] a day: `## Dzień 7: Piątek, 21.08.2026, A > B (37km)`
- [ ] after the days: `---`, a blank line, `> [!note] Skąd te notatki`, a blank line, `---`
- [ ] always `# Źródła i dalsza lektura` at the end, links as `- Description: https://…`

### Step 5. Preview

```sh
python build.py country-2027 --watch
```

It must print `✓ Built: _site/country-2027  (days: N, …)`.

### Step 6. Quality check (5 min)

- [ ] the number of days and the distance in the hero match the plan
- [ ] every day has map points (a day page does not show the whole route)
- [ ] no "W skrócie" bullet starts with `7. …` (markdown turns that into a numbered list)
- [ ] `mobile.html` looks the same with the internet switched off
- [ ] nothing private in the content (the site is public): booking numbers, phone
      numbers, the team's initials
- [ ] contradictions in the notes (flight times, dates) resolved

### Step 7. Publishing

```sh
git add trips/country-2027 && git commit -m "New trip: …" && git push    # straight to main
```

- [ ] Actions green
- [ ] `anks.pl/cycling_trips/` shows the new trip

### Step 8. After you get back

- [ ] on the day in `[freeze] date`, let a build run — it writes `frozen/`; commit it

---

## 5. A ready-made prompt for the agent

> In the `cycling_trips` repo, add the trip `country-2027` following `PLAYBOOK.md`.
> Input: [the plan note], [route.kml], [map link], [freeze date].
> Copy `trips/_template`, fill in `trip.toml`, `pois.csv` (2–5 points per day), generate
> the map, rewrite the note into `tresc.md` following `HOW-TO-EDIT.md`. Invent no facts —
> leave anything missing as `?` and give me the list. Build it, go through the step 6
> checklist, push to `main`.

---

## 6. Traps (every one of these has bitten once)

| Symptom | Cause | What to do |
|---|---|---|
| `ERROR: section not found` | a heading was renamed or removed | restore the contract name |
| editing `tresc.md` changes nothing | the trip is frozen | `--refreeze` or leave it |
| the phone shows the old look | cache | the engine appends `?v=hash`; otherwise Cmd+Shift+R |
| the site does not change after a push | the change is on a branch / in a PR | only a push to `main` publishes |
| "W skrócie" renders as a 1., 2. list | the line starts with `7. dzień` | rephrase: „Dzień trasy nr 7." |
| a dish does not reach "Czego spróbować" | no ` - ` between name and description | `- Hida-gyu - wołowina…` |
| a dot outside the offline sketch | a point far from the track | add the day to `svg_skip_days` |
| no offline sketch despite data | the line has fewer points than `svg_min_points` | improve the track or lower the threshold |
| the total distance makes no sense | days with `?km` | `show_total_km = false`, distance in `facts` |
| an external font or image in `mobile.html` | — | never: that page must work offline |

---

## 7. Changing the engine

- A change in `engine/` touches **every unfrozen** trip → afterwards run
  `python build.py` (no slug) and look at each of them.
- It does not touch the frozen ones at all — that is the point.
- Something specific to one trip → `trip.toml` (a field with a default), not
  `if slug == …`.
- One trip's images → `trips/<slug>/assets/`, referenced as `![caption](assets/file.jpg)`.

---

## 8. Migrating an old repo

```sh
git clone https://github.com/matisnape/<old-repo> tmp && cd tmp
git filter-repo --to-subdirectory-filter trips/<slug>          # pip install git-filter-repo
cd ../cycling_trips && git remote add old ../tmp && git fetch old
git merge --allow-unrelated-histories old/<main|master>         # history preserved
```

Careful: `git clone --depth 1` gives you a single commit — deepen the clone before
`filter-repo` (`git fetch --depth=1000 origin <branch>`), or the history is lost.

Then: delete `build.py` and `strona/assets` (they live in `engine/`), move
`route-data.js` to `trips/<slug>/assets/`, and write `trip.toml` from whatever was
hardcoded in the old `build.py`.

**Redirecting the old address** — the old repo stays as an archive of the history but
publishes only a redirect. Three things:

1. A `redirect/` directory with `index.html`, `404.html` (same content) and an empty
   `.nojekyll`. GitHub Pages serves `404.html` for every path that does not exist, so
   that single file catches all the subpages.
2. The old repo's workflow stops building — instead of the Python steps it passes
   `path: redirect` to `upload-pages-artifact`.
3. A banner in `README.md` (and `CLAUDE.md`, if there is one) so that nobody — human or
   agent — edits the archive.

```html
<!doctype html><html lang="pl"><meta charset="utf-8">
<title>Strona przeniesiona</title><meta name="robots" content="noindex">
<link rel="canonical" href="https://anks.pl/cycling_trips/<slug>/">
<!-- no JS: the trip home page after 2 s; with JS, instantly and to the exact subpage -->
<meta http-equiv="refresh" content="2;url=https://anks.pl/cycling_trips/<slug>/">
<body><a id="target" href="https://anks.pl/cycling_trips/<slug>/">Przejdź do nowej strony</a>
<script>
var base="https://anks.pl/cycling_trips/<slug>/";
var url=base+location.pathname.split("/").slice(2).join("/")+location.search+location.hash;
document.getElementById("target").href=url;location.replace(url);
</script>
```

`slice(2)` drops the empty segment and the old repo name, leaving just the file name.
The fragment (`#mapa`) and query string survive — verified in a browser, with and
without JS.

The file names (`dzien-3.html`, `mobile.html`) did not change, so old links land in the
same place.
