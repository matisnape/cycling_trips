# Playbook: nowa strona wyprawy

Jak zbudowane są strony i jak dodać kolejną. Dla Ciebie i dla agenta (Claude Code).

---

## 1. Mapa systemu w 30 sekund

**Silnik = ekspres do kawy, wyprawa = kapsułka.** Ekspres jest jeden (`engine/`),
każda wyprawa to kapsułka w `trips/<slug>/`. Nowa wyprawa = nowa kapsułka,
ekspresu nie ruszasz.

```
trips/<slug>/
  trip.toml    ─┐  tytuł, hero, fakty, podstrony, kolor, analityka, data mrożenia
  tresc.md     ─┼─►  engine/build.py  ─►  _site/<slug>/index.html     strona główna + mapa
  pois.csv      │                                      dzien-N.html     dzień po dniu
  route.gpx/kml ┤                                      <podstrona>.html z [[pages]]
  assets/       │                                      zrodla.html
   route-data.js ◄── engine/gen_route.py               mobile.html      1 plik, offline
  frozen/      ─┘  zamrożona kopia strony (patrz §2)
engine/assets/ (style.css, map.js, site.js) ─► kopiowane do każdej wyprawy
                                               _site/index.html        lista wszystkich wypraw
```

| Plik | Co robi | Kto edytuje |
|---|---|---|
| `trips/<slug>/tresc.md` | cała treść, kontrakt nagłówków → `JAK-EDYTOWAC.md` | Ty, codziennie |
| `trips/<slug>/trip.toml` | tytuł, hero, fakty, podstrony, kolor, GA, **data mrożenia** | raz, przy zakładaniu |
| `trips/<slug>/pois.csv` | punkty na mapie: `day,name,lat,lon,blurb` | raz + poprawki |
| `trips/<slug>/route.gpx` / `.kml` | ślad trasy | raz |
| `trips/<slug>/assets/route-data.js` | **generowany** z dwóch powyższych | nie ręcznie |
| `trips/<slug>/frozen/` | zamrożona strona, **w repo** | tylko przez `--refreeze` |
| `engine/build.py` | generator | tylko świadomie (dotyka wszystkich niezamrożonych wypraw) |
| `engine/assets/*` | wygląd i mapa, wspólne | j.w. |
| `_site/` | wynik, nie w repo | nigdy |

**Adresy:** `anks.pl/cycling_trips/` (lista) → `anks.pl/cycling_trips/<slug>/`.
**Publikacja:** push na `main` → GitHub Actions buduje wszystko (~1–2 min).

---

## 2. Mrożenie wypraw — przeczytaj przed założeniem nowej

Wyprawa, która się skończyła, **nie powinna już być regenerowana**. Nikt jej nie
testuje, a każda zmiana w `engine/` mogłaby ją po cichu zepsuć — i nikt by tego
nie zauważył.

> To nie jest teoria. W Albanii filtr szkicu trasy offline wycinał „dzień busowy".
> Po przenumerowaniu planu z 10 dni na 8 numer dnia się przesunął i filtr zaczął
> wycinać dolinę Valbony, zostawiając punkty busowe. Błąd przeżył dwa miesiące,
> bo nikt tam nie zaglądał.

**Jak to działa:**

1. W `trip.toml` ustawiasz `[freeze] date = "RRRR-MM-DD"` — zwykle dzień po powrocie.
2. Przed tą datą build generuje stronę normalnie, przy każdym pushu.
3. **W dniu mrożenia** pierwszy build zapisuje gotową stronę do `trips/<slug>/frozen/`
   i commituje ją do repo. Build mówi o tym wprost.
4. **Po tej dacie** build nie uruchamia generatora dla tej wyprawy — tylko przepisuje
   `frozen/` do `_site/<slug>/`. Zmiany w `engine/` fizycznie nie mają jak jej dotknąć.
5. Jeśli edytujesz `tresc.md` zamrożonej wyprawy, build to zauważy i **ostrzeże**,
   że zmiana nie ma skutku.
6. Świadome odmrożenie: `python build.py <slug> --refreeze` — przebudowuje i nadpisuje
   `frozen/`. Rób to tylko wtedy, gdy naprawdę chcesz i obejrzysz wynik.

**Zamrożone dziś:** `albania-2026`, `rumunia-2026`.

---

## 3. Co dostaje każda wyprawa (za darmo, z silnika)

- Strona główna: hero, fakty, intro z `# Klucz do wyjazdu`, interaktywna mapa (Leaflet), plan dni, „Czego spróbować".
- Strona na każdy dzień: mapa przybliżona na punkty dnia, „W skrócie", „Miejsca i historia", ← →.
- Podstrony z `[[pages]]` (Praktyczne, Słowniczek, Kulinaria…) + Źródła.
- `mobile.html`: jedna strona, **zero zapytań do sieci**, szkic trasy w SVG, dolny pasek ← Sekcje →, hamburger działający bez JS, przycisk „Zapisz".
- Telefon na `index.html` sam przechodzi na `mobile.html` (wybór pamiętany **osobno dla każdej wyprawy**).
- Wersjonowane CSS/JS (`?v=hash`) — telefon nie trzyma starego wyglądu.

---

## 4. Nowa wyprawa — krok po kroku

### Krok 0. Zbierz wejście (checklista)

- [ ] notatka z planem dzień po dniu (Obsidian)
- [ ] ślad: KML z Google My Maps (*⋮ → Eksportuj do KML/KMZ → KML*) albo GPX
- [ ] link do Mapy Google / mapy.com
- [ ] daty, kraje, km dzienne (jeśli są)
- [ ] **data mrożenia** — zwykle dzień po powrocie. Bez niej nie zakładaj wyprawy

> **Agencie: o datę mrożenia pytaj zawsze**, przy każdej nowej wyprawie, nawet
> jeśli reszta wejścia jest kompletna. To jedyne pole, którego nie da się wywnioskować
> z materiałów.

### Krok 1. Folder

```sh
cp -r trips/_szablon trips/kraj-2027        # slug: <kraj>-<rok>, małe litery, bez polskich znaków
cp ~/Downloads/trasa.kml trips/kraj-2027/route.kml
```

### Krok 2. `trip.toml`

- [ ] `slug` = nazwa folderu
- [ ] `title`, `title_html`, `eyebrow`, `lede`, `home_title`, `home_description`, `footer`
- [ ] `facts` (przewyższenie, najwyższa przełęcz…)
- [ ] `show_total_km = false`, jeśli jakiś dzień ma `?km`
- [ ] `[[pages]]` — tylko te sekcje, które będą w `tresc.md`
- [ ] **`[freeze] date`**
- [ ] opcjonalnie `[theme] accent`, `[analytics]`

### Krok 3. Mapa

- [ ] `pois.csv`: 2–5 punktów na dzień, `day` = numer dnia z `tresc.md`
- [ ] `python engine/gen_route.py kraj-2027` → sprawdź, czy km śladu się zgadza
- [ ] punkty daleko od trasy (bus, wypad) → ich dzień do `[map] svg_skip_days`

### Krok 4. `tresc.md`

Najszybciej: daj agentowi notatkę + szablon. Ręcznie: wypełnij `trips/_szablon/tresc.md`.
Zasady kontraktu (pełne w `JAK-EDYTOWAC.md`):

- [ ] `# Meta` → `# Klucz do wyjazdu — „…"` → `---` → `# Plan wyjazdu`
- [ ] dzień: `## Dzień 7: Piątek, 21.08.2026, A > B (37km)`
- [ ] po dniach: `---`, pusta linia, `> [!note] Skąd te notatki`, pusta linia, `---`
- [ ] na końcu zawsze `# Źródła i dalsza lektura`, linki jako `- Opis: https://…`

### Krok 5. Podgląd

```sh
python build.py kraj-2027 --watch
```

Musi wypisać `✓ Built: _site/kraj-2027  (days: N, …)`.

### Krok 6. Kontrola jakości (5 min)

- [ ] liczba dni i km w hero = plan
- [ ] każdy dzień ma punkty na mapie (strona dnia nie pokazuje całej trasy)
- [ ] żaden „W skrócie" nie zaczyna się od `7. …` (markdown zrobi z tego listę numerowaną)
- [ ] `mobile.html` z wyłączonym internetem wygląda tak samo
- [ ] w treści nic prywatnego (strona jest publiczna): numery rezerwacji, telefony, inicjały ekipy
- [ ] sprzeczne dane w notatkach (godziny lotów, daty) — rozstrzygnięte

### Krok 7. Publikacja

```sh
git add trips/kraj-2027 && git commit -m "Nowa wyprawa: …" && git push    # prosto na main
```

- [ ] Actions zielone
- [ ] `anks.pl/cycling_trips/` pokazuje nową wyprawę

### Krok 8. Po powrocie

- [ ] w dniu z `[freeze] date` przepuść build — zapisze `frozen/` i zacommituj go

---

## 5. Gotowy prompt dla agenta

> W repo `cycling_trips` dodaj wyprawę `kraj-2027` wg `PLAYBOOK.md`.
> Wejście: [notatka z planem], [route.kml], [link do mapy], [data mrożenia].
> Skopiuj `trips/_szablon`, wypełnij `trip.toml`, `pois.csv` (2–5 punktów/dzień), wygeneruj mapę,
> przepisz notatkę do `tresc.md` zgodnie z `JAK-EDYTOWAC.md`. Nie wymyślaj faktów — czego brak,
> zostaw jako `?` i wypisz mi listę. Zbuduj, przejdź checklistę z kroku 6, wypchnij na `main`.

---

## 6. Pułapki (każda już raz ugryzła)

| Objaw | Przyczyna | Co zrobić |
|---|---|---|
| `ERROR: section not found` | zmieniony/usunięty nagłówek | przywróć nazwę z kontraktu |
| zmiana w `tresc.md` nic nie daje | wyprawa zamrożona | `--refreeze` albo zostaw |
| telefon pokazuje stary wygląd | cache | silnik dokleja `?v=hash`; w razie czego Cmd+Shift+R |
| po pushu strona się nie zmienia | zmiana na gałęzi / w PR | tylko push na `main` publikuje |
| „W skrócie" jako lista 1., 2. | linia zaczyna się od `7. dzień` | przeformułuj: „Dzień trasy nr 7." |
| danie nie trafia do „Czego spróbować" | brak ` - ` między nazwą a opisem | `- Hida-gyu - wołowina…` |
| kropka poza szkicem offline | punkt daleko od śladu | dzień do `svg_skip_days` |
| brak szkicu offline mimo danych | linia ma mniej punktów niż `svg_min_points` | uzupełnij ślad albo obniż próg |
| suma km bez sensu | dni z `?km` | `show_total_km = false`, km w `facts` |
| zewnętrzny font/obrazek w `mobile.html` | — | nigdy: ta strona ma działać bez sieci |

---

## 7. Zmiany w silniku

- Zmiana w `engine/` dotyka **wszystkich niezamrożonych** wypraw → po zmianie
  `python build.py` (bez slugu) i przejrzyj każdą.
- Zamrożonych nie dotyka w ogóle — to jest cel.
- Coś specyficznego dla jednej wyprawy → `trip.toml` (pole z domyślną wartością), nie `if slug == …`.
- Obrazki jednej wyprawy → `trips/<slug>/assets/`, w treści `![podpis](assets/plik.jpg)`.

---

## 8. Migracja starego repo

```sh
git clone https://github.com/matisnape/<stare-repo> tmp && cd tmp
git filter-repo --to-subdirectory-filter trips/<slug>          # pip install git-filter-repo
cd ../cycling_trips && git remote add old ../tmp && git fetch old
git merge --allow-unrelated-histories old/<main|master>         # historia zachowana
```

Uwaga: `git clone --depth 1` daje jeden commit — przed `filter-repo` pogłęb klon
(`git fetch --depth=1000 origin <gałąź>`), inaczej historia przepadnie.

Potem: `build.py` i `strona/assets` usunąć (są w `engine/`), `route-data.js` →
`trips/<slug>/assets/`, napisać `trip.toml` z tego, co było zaszyte w starym `build.py`.

**Przekierowanie ze starego adresu** — stare repo zostaje jako archiwum historii,
ale publikuje już tylko przekierowanie. Trzy rzeczy:

1. Katalog `przekierowanie/` z `index.html`, `404.html` (ta sama treść) i pustym
   `.nojekyll`. GitHub Pages podaje `404.html` na każdą nieistniejącą ścieżkę, więc
   ten jeden plik łapie wszystkie podstrony.
2. Workflow starego repo przestaje budować — zamiast kroków z Pythonem wrzuca
   `path: przekierowanie` do `upload-pages-artifact`.
3. Baner w `README.md` (i `CLAUDE.md`, jeśli jest), żeby nikt — człowiek ani agent —
   nie edytował archiwum.

```html
<!doctype html><html lang="pl"><meta charset="utf-8">
<title>Strona przeniesiona</title><meta name="robots" content="noindex">
<link rel="canonical" href="https://anks.pl/cycling_trips/<slug>/">
<!-- bez JS: po 2 s na stronę wyprawy; ze skryptem natychmiast i w konkretną podstronę -->
<meta http-equiv="refresh" content="2;url=https://anks.pl/cycling_trips/<slug>/">
<body><a id="cel" href="https://anks.pl/cycling_trips/<slug>/">Przejdź do nowej strony</a>
<script>
var cel="https://anks.pl/cycling_trips/<slug>/";
var nowy=cel+location.pathname.split("/").slice(2).join("/")+location.search+location.hash;
document.getElementById("cel").href=nowy;location.replace(nowy);
</script>
```

`slice(2)` obcina pusty człon i nazwę starego repo, zostawiając samą nazwę pliku.
Zakotwiczenie (`#mapa`) i parametry przechodzą dalej — sprawdzone w przeglądarce,
z JS i bez.

Nazwy plików (`dzien-3.html`, `mobile.html`) się nie zmieniły, więc stare linki trafiają w to samo miejsce.
