# How to edit the site in Obsidian (with live preview)

You edit **one file** — `tresc.md` — in Obsidian. The script watches it in the
background and, after every save, automatically rebuilds the whole site, and the
preview in the browser **refreshes itself**. You don't touch the HTML by hand.

## What's in this folder
```
tresc.md                  ← YOU EDIT THIS (your markdown note)
build.py                  ← the script that turns it into a site
buduj-windows.bat         ← double-click on Windows (live mode)
buduj-mac-linux.command   ← double-click on Mac/Linux (live mode)
JAK-EDYTOWAC.md           ← this file
strona/                   ← OUTPUT: the finished site (this is what goes to GitHub Pages)
   ├─ index.html, dzien-1…10.html, zrodla.html  (generated — don't touch)
   ├─ assets/   (styles + map — don't touch, unless you want to change the look)
   ├─ README.md (publishing guide)
   └─ .nojekyll
```

## Once, at the start
You need **Python 3** (`python --version` in a terminal checks it; if it's missing —
https://www.python.org/downloads/, on Windows check "Add Python to PATH").
The `markdown` library is installed by the script itself on first run.

## Connecting to Obsidian — pick one way

**A) Simplest — open this folder as a vault.**
In Obsidian: *Open another vault → Open folder as vault* and point to this folder.
`tresc.md` shows up as a note you edit normally in Obsidian.

**B) You keep the note in your main vault.**
Open `build.py` in a text editor, find the line `SRC_OVERRIDE = ""` near the top and
enter the full path to your note, e.g.:
```
SRC_OVERRIDE = r"C:\Users\Anks\Obsidian\My vault\Longinada 2026.md"
```
(on Mac without `r` and with regular slashes `/`). Save `build.py`.

## Working with live preview
1. Start live mode:
   - **Windows:** double-click `buduj-windows.bat`
   - **Mac:** double-click `buduj-mac-linux.command` (if the system blocks it: right-
     click → Open → Open)
   - **or from a terminal** in this folder: `python build.py --watch`
2. A browser opens with the preview (`http://localhost:8000`). **Leave that window
   running.**
3. Edit `tresc.md` in Obsidian and save (Ctrl/Cmd+S). After a moment the site in the
   browser refreshes itself.
4. When done: press `Ctrl+C` in the script window.
5. Publishing: if you use auto-publishing via GitHub Actions (see `README.md`),
   it's enough to push the changes to the repo — the site builds and publishes
   itself. The local preview is only for previewing changes on your machine before
   you push them.

> Without the preview, a one-off build: `python build.py`.

## Rules for writing in tresc.md (so the script doesn't get lost)
The script recognizes content by its headings — **keep these names and format**:

- `# Klucz do wyjazdu — ...` → the intro on the home page.
- `# Plan wyjazdu` → the start of the plan (a `---` line ends it).
- Each day starts with a line in the format:
  ```
  ## Dzień 3: Niedziela, 16.08.2026, Gusinje > Rugova (42km)
  ```
  i.e. `## Dzień <no>: <weekday>, <date>, <from> > <to> (<km>km)`.
  The arrow comes from the `>` character. The number before `km` goes into the summaries.
- `-` bullets right under the day heading → go into the **"W skrócie"** box.
- Everything after `### Miejsca i historia` → the day's main content.
- Make sub-bullets with indentation (Tab or 4 spaces). Bold `**text**`, italics `_text_`.
- `# Źródła i dalsza lektura` → the sources page. Write links as
  `- Label: https://address` — it becomes a clickable link.
- Obsidian links `[[Something]]` turn into plain text (they don't break the page).

If you see the message "section not found…", it means one of these headings
disappeared or changed — restore it and save. In `--watch` mode the script simply
tries again on the next save.

## Other changes
- **A new day:** paste another `## Dzień N: ...` block into the `# Plan wyjazdu` section.
- **Points on the map:** `strona/assets/route-data.js` (a readable list of `lat`/`lon`
  + a day number; the route line `route` is in there too). Editing this file also
  triggers a refresh in live mode.
- **Colors/look:** `strona/assets/style.css` — color variables at the top of the file.
- **Photos:** drop them into `strona/assets/` and insert in the note as
  `![caption](assets/file.jpg)` (Obsidian's `![[file.jpg]]` works too).

## Mapa — skąd się bierze

`strona/assets/route-data.js` jest **generowany** skryptem `gen_route.py` z pliku
`~/Downloads/Albania/albania.gpx` (linia trasy, uproszczona do ~1000 punktów) plus
tabeli punktów `POIS` wpisanej w samym skrypcie.

- Zmieniasz **ślad** (nowy GPX) → popraw ścieżkę `GPX` w `gen_route.py` i uruchom
  `python3 gen_route.py`.
- Zmieniasz **punkty na mapie** (nazwa, opis, przypisanie do dnia) → edytuj listę
  `POIS` w `gen_route.py` i uruchom go ponownie.
- Ręczne dłubanie w `route-data.js` też działa, ale zniknie przy kolejnym
  uruchomieniu skryptu.
