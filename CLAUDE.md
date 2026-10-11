# Instrukcje dla agenta (Claude Code) pracującego w tym repo

Repo generuje strony wielu wypraw rowerowych: **jeden silnik, wiele wypraw**.
Źródłem każdej wyprawy jest `trips/<slug>/tresc.md`; build robi z tego statyczną stronę
publikowaną przez GitHub Actions: `anks.pl/cycling_trips/` (lista wypraw) →
`anks.pl/cycling_trips/<slug>/`.

## Struktura

```
engine/build.py       generator (wspólny dla wszystkich wypraw)
engine/gen_route.py   route.gpx|kml + pois.csv -> trips/<slug>/assets/route-data.js
engine/assets/        style.css, map.js, site.js — wspólne dla wszystkich wypraw
trips/<slug>/         tresc.md, trip.toml, pois.csv, route.gpx|kml, assets/
trips/_szablon/       pusta wyprawa do kopiowania; build ją pomija
build.py              cienki launcher w korzeniu -> engine/build.py
_site/                WYNIK buildu, w .gitignore
```

## Co wolno edytować

- **`trips/<slug>/tresc.md`** — źródło treści. Prawie każda prośba („dopisz notatkę
  z Theth", „popraw kilometraż dnia 4") = edycja tego pliku w odpowiedniej wyprawie.
- `trips/<slug>/trip.toml` — nazwa, hero, podstrony, kolor akcentu, analityka.
- `trips/<slug>/pois.csv` (kolumny `day,name,lat,lon,blurb`, dodatkowe kolumny są
  przepisywane do punktu) i `route.gpx`/`route.kml` — punkty i ślad na mapie. Po zmianie:
  `python engine/gen_route.py <slug>`.
- **`_site/` jest generowany** — nigdy go nie edytuj ręcznie ani nie commituj
  (`.gitignore`; zmiany i tak przepadną przy następnym buildzie).
- **`trips/<slug>/assets/route-data.js` jest generowany** przez `gen_route.py` — nie
  edytuj ręcznie, o ile wyprawa ma `route.gpx`/`route.kml`.
- **Wyjątek: `trips/rumunia-2026/`** nie ma pliku śladu, więc jej `assets/route-data.js`
  to **jedyna kopia trasy**. Nie regeneruj go i nie nadpisuj.

## Uwaga: engine/ dotyka WSZYSTKICH wypraw

Zmiana w `engine/` (build.py, `engine/assets/*`) zmienia **każdą** wyprawę naraz — także te,
o które nie prosiono. Przed commitem zbuduj wszystkie (`python build.py`, bez argumentu)
i sprawdź, że żadna nie zgłasza błędu. Wszystko wyprawo-specyficzne (teksty, kolory,
podstrony, analityka) należy do `trip.toml`, nie do silnika.

## Kontrakt nagłówków w tresc.md — złamanie = build failuje

Zachowaj dokładnie te nagłówki i format:

- `# Meta` … `# Klucz do wyjazdu — …` (z em-dashem) … `# Plan wyjazdu`
- każdy dzień: `## Dzień <nr>: <DzieńTygodnia>, <DD.MM.RRRR>, <skąd> > <dokąd> (<NN>km)`
- opcjonalnie w dniu: `### Miejsca i historia` (wszystko po nim to treść główna dnia)
- sekcja planu kończy się linią `---`, po niej pusta linia, blok `> [!note] Skąd te notatki`,
  pusta linia i znów `---`
- `# Źródła i dalsza lektura` (wymagane)
- podstrony z `[[pages]]` w `trip.toml` (np. `# Praktyczne informacje`,
  `# Kulinaria i pamiątki`, `# Ciekawostki`) — nagłówek w `tresc.md` musi się zgadzać
  z `heading` w `trip.toml`; pusta lub nieobecna sekcja = brak podstrony, bez błędu

W `# Meta` linie `- Nazwa - opis` trafiają na stronę główną jako „Czego spróbować";
linie zaczynające się od `Opis:`, `Mapa …:`, `Szlak:` są linkami (lista prefiksów:
`meta_skip_prefixes` w `trip.toml`). Wzór poprawnego pliku: `trips/_szablon/tresc.md`.

## Jak sprawdzić, że nie zepsułeś buildu

```sh
python build.py albania-2026   # musi wypisać "✓ Built: _site/albania-2026 (days: N, km: N, dishes: N)"
python build.py                # wszystkie wyprawy + _site/index.html z listą
```

Jeśli zobaczysz `ERROR: section not found …` — wróciłeś nagłówek do złej nazwy.
Podgląd na żywo: `python build.py <slug> --watch` (lub `--serve`).

## Nowa wyprawa

1. `cp -r trips/_szablon trips/<slug>` i wypełnij `trip.toml` (w tym `slug` = nazwa katalogu).
2. Napisz `tresc.md`, dodaj `route.gpx`/`route.kml` i `pois.csv`.
3. `python engine/gen_route.py <slug>`, potem `python build.py <slug>`.

## Publikacja

- Workflow `.github/workflows/deploy.yml` odpala się **tylko na push do `main`** i buduje
  wszystkie wyprawy naraz (`python build.py`), a artefaktem jest `_site/`.
- Pracując z telefonu/chmury: **commituj i pushuj wprost na `main`**, nie zakładaj PR-a
  — inaczej strona się nie odświeży, dopóki ktoś PR-a nie zmerguje.
- Po pushu sprawdź, że Actions są zielone: `gh run list --limit 1`.
- Commit messages i treść stron: po polsku.

## Dwie wersje każdej wyprawy (obie z tego samego `tresc.md`)

- `index.html` + `dzien-N.html` + podstrony — wersja pełna z interaktywną mapą.
- `mobile.html` — jedna strona, w pełni offline (CSS i mapa-SVG w środku pliku,
  zero zapytań do sieci). Na urządzeniu dotykowym `index.html` sam tam przenosi;
  wybór „wersja pełna" pamięta `localStorage['gp-view:<slug>']` (osobno dla każdej wyprawy).

Nie dodawaj do `mobile.html` zewnętrznych fontów, skryptów ani obrazków z sieci —
cały sens tej strony to działanie bez internetu.
