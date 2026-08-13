# „Góry Przeklęte" trip site — user guide

This repository turns **a single notes file** (`tresc.md`) into a finished site:
a home page with the route map, 10 day subpages, and a sources page.

You have two ways to work and **both use the same `tresc.md`** — you can use them
interchangeably:

1. **On your computer** — live preview (watch). You edit in Obsidian and the site
   refreshes instantly on your machine.
2. **From a phone / browser** — you edit `tresc.md` on GitHub, and GitHub builds
   and publishes the site itself (Actions).

---

## The essentials in 30 seconds

- **You always edit only `tresc.md`.** The rest happens automatically.
- **On the computer:** open Obsidian → start the preview (double-click `buduj-windows.bat`
  / `buduj-mac-linux.command`) → write and save → the site in the browser refreshes itself.
- **From a phone:** in the GitHub app open `tresc.md`, fix it, "Commit". After ~2 min
  the live site is updated.
- **THE GOLDEN RULE of syncing:** before you start writing on the computer — **pull
  the changes**. When you're done — **push**. If you use the Obsidian Git plugin
  (see below), it does this for you.

Site address after publishing: `https://<your-name>.github.io/<repo>/`
(write yours in here once it exists, to keep it handy).

---

## 1. Setup — you do this ONCE

Tick them off one by one:

- [ ] **Python 3** on your computer. Check in a terminal: `python --version`
      (or `python3 --version`). If missing → https://www.python.org/downloads/
      (on Windows, during install check "Add Python to PATH").
- [ ] **A repository on GitHub** (public, e.g. `longinada-albania-2026`) with the entire
      contents of this folder — including the hidden `.github/`. Easiest via git or
      GitHub Desktop:
      ```bash
      cd <this-folder>
      git init && git add . && git commit -m "Trip site"
      git branch -M master
      git remote add origin https://github.com/<user>/longinada-albania-2026.git
      git push -u origin master
      ```
- [ ] **Pages in Actions mode:** in the repo → **Settings → Pages → Build and deployment
      → Source: "GitHub Actions"** (NOT "Deploy from a branch").
- [ ] **Check the first publish:** the **Actions** tab → the "Build and publish site"
      workflow → after the ✓, open the site address.
- [ ] **(recommended) Obsidian Git** — so computer↔phone syncing works by itself:
      open the repo folder as a vault in Obsidian → Settings → Community plugins →
      install and enable **Obsidian Git** → in its settings enable
      "pull on startup" and automatic "commit-and-sync" every e.g. 10 minutes.

After this step you don't return to setup — you work as below.

---

## 2. Day-to-day work

### A. On the computer (main mode — with live preview)
1. Open Obsidian on this vault. (Obsidian Git will pull any changes from the phone.)
2. Start the live preview — **double-click**:
   - Windows: `buduj-windows.bat`
   - Mac: `buduj-mac-linux.command` (if it gets blocked: right-click → Open → Open)
   - or in a terminal in this folder: `python build.py --watch`
3. A browser opens (`http://localhost:8000`). **Leave that window open.**
4. Edit `tresc.md` in Obsidian and save (Ctrl/Cmd+S) — the preview refreshes itself.
5. When done: close the preview (`Ctrl+C` in the script window) and **push the changes**
   (Obsidian Git will commit-and-sync by itself; or manually — see section 3).
   After the push, GitHub publishes the new version online.

> The live preview works **only on your machine** and needs no internet beyond the
> map/fonts. Pushing to GitHub is a separate step (push) — only that updates the live site.

### B. From a phone / any browser (via GitHub)
1. In the **GitHub** app (or on github.com) open the repo → open `tresc.md`.
2. Pencil (Edit) → fix the text → **Commit changes**.
3. GitHub builds and publishes the site itself (the Actions tab shows progress; ~1-2 min).
4. Next time on the computer: **pull those changes** (Obsidian Git does it on
   startup; or `git pull`) so you have them locally.

---

## 3. Syncing — how not to get lost

The computer and GitHub are the same project in two places. To keep them in sync:

- **Before you start writing on the computer:** pull the latest (`pull`).
- **When you finish on the computer:** push (`push`).

With **Obsidian Git** this happens automatically (pull on startup + periodic
commit-and-sync). Without the plugin, manually in a terminal in the repo folder:
```bash
git pull            # at the start of work
# ... you edit tresc.md ...
git add tresc.md
git commit -m "Update notes"
git push            # at the end
```

**When can there be a conflict?** Only if you change the same fragment of `tresc.md`
in parallel on both the phone and the computer without pulling first. Working solo,
that's rare. If it happens, git/Obsidian Git will warn you — then the simplest fix is
to keep one version of the text and save.

---

## 4. What is what (so you know what not to touch)

| File / folder | What for | Do you edit it? |
|---|---|---|
| `tresc.md` | **Your notes** — the source of the whole site | **YES** |
| `JAK-EDYTOWAC.md` | rules for writing in `tresc.md` (headings, day format, adding a day) | for reading |
| `build.py` | the site generator (run by watch and Actions) | no |
| `.github/workflows/deploy.yml` | automation: builds and publishes after a push | no |
| `strona/assets/route-data.js` | points and the line on the map | only if you want to change the map |
| `strona/assets/style.css` | colors and look (variables at the top of the file) | only if you want to change the look |
| `strona/*.html` | generated automatically | **no** (they're git-ignored anyway) |
| `buduj-*.bat / .command` | live-preview launchers | no |

How and what you can write in `tresc.md` (which headings must stay, how to add another
day, the date and kilometer format) — it's all in **`JAK-EDYTOWAC.md`**.

---

## 5. When something's off

- **The live preview doesn't refresh** → check that the script window (`--watch`) is
  still running and that the browser is at `http://localhost:8000` (not a file opened
  from disk). A manual refresh (F5) also helps.
- **"section not found…" during the build** → a heading disappeared or was renamed in
  `tresc.md` (e.g. `# Plan wyjazdu`, `## Dzień N: ...`). Restore it and save.
  The list of required headings is in `JAK-EDYTOWAC.md`.
- **`python` doesn't work / "command not found"** → try `python3 build.py --watch`.
  If still nothing — Python isn't installed (see section 1).
- **The workflow shows red on GitHub** → go to **Actions**, click the failed run;
  at the bottom you'll see the error message (usually the same thing as
  "section not found" — a typo in a heading in `tresc.md`).
- **Changes from the phone don't show on the computer** → run `git pull` (or restart
  Obsidian with Obsidian Git enabled).
- **The live site didn't change** → check in Actions that the publish reached the ✓;
  sometimes you need to refresh the page bypassing the cache (Ctrl/Cmd+Shift+R).

---

Enjoy the work — and enjoy the trip.
