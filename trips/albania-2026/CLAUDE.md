# Instrukcje dla agenta (Claude Code) pracującego w tym repo

Repo generuje stronę wyprawy: **jeden plik źródłowy → statyczna strona** publikowana
przez GitHub Actions na http://anks.pl/longinada-albania-2026/

## Co wolno edytować

- **`tresc.md`** — jedyne źródło treści. Prawie każda prośba („dopisz notatkę z Theth",
  „popraw kilometraż dnia 4") = edycja tego pliku.
- `strona/*.html` są **generowane** przez `build.py` — nigdy ich nie edytuj ręcznie
  (są w `.gitignore`, zmiany i tak przepadną przy następnym buildzie).
- Punkty na mapie: `gen_route.py` (lista `POIS`), potem `python3 gen_route.py`.

## Kontrakt nagłówków w tresc.md — złamanie = build failuje

Zachowaj dokładnie te nagłówki i format:

- `# Meta` … `# Klucz do wyjazdu — …` … `# Plan wyjazdu`
- każdy dzień: `## Dzień <nr>: <DzieńTygodnia>, <DD.MM.RRRR>, <skąd> > <dokąd> (<NN>km)`
- opcjonalnie w dniu: `### Miejsca i historia` (wszystko po nim to treść główna dnia)
- sekcja planu kończy się linią `---`, po niej blok `> [!note] Skąd te notatki`,
  potem `---`
- dalsze sekcje: `# Praktyczne informacje`, `# Kulinaria i pamiątki`, `# Ciekawostki`,
  `# Źródła i dalsza lektura`

W `# Meta` linie `- Nazwa - opis` trafiają na stronę główną jako „Czego spróbować";
linie zaczynające się od `Opis:`, `Mapa …:`, `Szlak:` są traktowane jako linki.

## Jak sprawdzić, że nie zepsułeś buildu

```sh
python3 build.py     # musi wypisać "✓ Built: … (days: N, km: N, dishes: N)"
```

Jeśli zobaczysz `ERROR: section not found …` — wróciłeś nagłówek do złej nazwy.

## Publikacja

- Workflow `.github/workflows/deploy.yml` odpala się **tylko na push do `main`**.
- Pracując z telefonu/chmury: **commituj i pushuj wprost na `main`**, nie zakładaj PR-a
  — inaczej strona się nie odświeży, dopóki ktoś PR-a nie zmerguje.
- Po pushu sprawdź, że Actions są zielone: `gh run list --limit 1`.
- Commit messages i treść strony: po polsku.

## Dwie wersje strony (obie z tego samego `tresc.md`)

- `index.html` + `dzien-N.html` — wersja pełna z interaktywną mapą.
- `mobile.html` — jedna strona, w pełni offline (CSS i mapa-SVG w środku pliku,
  zero zapytań do sieci). Na urządzeniu dotykowym `index.html` sam tam przenosi.

Nie dodawaj do `mobile.html` zewnętrznych fontów, skryptów ani obrazków z sieci —
cały sens tej strony to działanie bez internetu.
