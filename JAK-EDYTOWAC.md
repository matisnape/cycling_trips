# Jak edytować stronę wyprawy w Obsidianie (z podglądem na żywo)

Edytujesz **jeden plik** — `trips/<wyprawa>/tresc.md`. Skrypt w tle po każdym zapisie
przebudowuje stronę, a podgląd w przeglądarce **odświeża się sam**. HTML-a nie ruszasz.

## Co jest w repo
```
trips/
  albania-2026/        jedna wyprawa:
    tresc.md             ← TO EDYTUJESZ (notatka w markdownie)
    trip.toml            nazwa, hero, podstrony, kolor, analityka
    pois.csv             punkty na mapie (day,name,lat,lon,blurb)
    route.gpx            ślad trasy (albo route.kml)
    assets/              route-data.js (generowany) + Twoje zdjęcia
  rumunia-2026/        druga wyprawa (bez śladu — patrz niżej)
  _szablon/            pusta wyprawa do skopiowania przy zakładaniu nowej
engine/                silnik wspólny dla wszystkich wypraw (nie ruszaj, jeśli nie musisz)
build.py               launcher: python build.py <wyprawa> [--watch]
buduj-windows.bat      dwuklik na Windows (podgląd na żywo)
buduj-mac-linux.command  dwuklik na Mac/Linux (podgląd na żywo)
_site/                 WYNIK: gotowe strony (generowane, w .gitignore, nie edytuj)
```

## Raz, na początku
Potrzebny **Python 3.11 lub nowszy** (`python --version`; jeśli brak —
https://www.python.org/downloads/, na Windows zaznacz „Add Python to PATH").
Biblioteka `markdown` doinstaluje się sama przy pierwszym uruchomieniu.

## Połączenie z Obsidianem
W Obsidianie: *Open another vault → Open folder as vault* i wskaż to repo (albo samą
`trips/<wyprawa>`). `tresc.md` pojawia się jako zwykła notatka.

## Praca z podglądem na żywo
1. Uruchom tryb na żywo:
   - **Windows:** dwuklik `buduj-windows.bat`
   - **Mac:** dwuklik `buduj-mac-linux.command` (jeśli system blokuje: prawy przycisk →
     Otwórz → Otwórz)
   - **albo w terminalu** w katalogu repo: `python build.py albania-2026 --watch`
   Launchery bez argumentu zapytają o nazwę wyprawy (nazwa katalogu w `trips/`).
2. W przeglądarce otwiera się podgląd. **Zostaw to okno uruchomione.**
3. Edytuj `tresc.md` i zapisz (Ctrl/Cmd+S). Po chwili strona w przeglądarce odświeży się sama.
4. Na koniec `Ctrl+C` w oknie skryptu.
5. Publikacja: wystarczy **wypchnąć zmiany na gałąź `main`** — GitHub Actions zbuduje
   wszystkie wyprawy i opublikuje je pod `anks.pl/cycling_trips/<wyprawa>/`. Lokalny
   podgląd służy tylko do obejrzenia zmian przed pushem.

> Bez podglądu, jednorazowy build: `python build.py albania-2026` (jedna wyprawa)
> albo `python build.py` (wszystkie + strona z listą wypraw).

## Zasady pisania w tresc.md (żeby skrypt się nie pogubił)
Skrypt rozpoznaje treść po nagłówkach — **zachowaj te nazwy i format**:

- `# Meta` — linie `- Nazwa - opis` to dania na stronie głównej („Czego spróbować");
  linie `Opis:`, `Mapa …:`, `Szlak:` to linki.
- `# Klucz do wyjazdu — ...` (z długą kreską) → wstęp na stronie głównej.
- `# Plan wyjazdu` → początek planu (kończy go linia `---`, a po niej blok
  `> [!note] Skąd te notatki`, znów otoczony `---`).
- Każdy dzień zaczyna się linią:
  ```
  ## Dzień 3: Niedziela, 16.08.2026, Gusinje > Rugova (42km)
  ```
  czyli `## Dzień <nr>: <dzień tygodnia>, <data>, <skąd> > <dokąd> (<km>km)`.
  Strzałka bierze się ze znaku `>`, liczba przed `km` idzie do podsumowań.
- Punkty `-` tuż pod nagłówkiem dnia → ramka **„W skrócie"**.
- Wszystko po `### Miejsca i historia` → treść główna dnia.
- Podpunkty robisz wcięciem (Tab lub 4 spacje). Pogrubienie `**tekst**`, kursywa `_tekst_`.
- `# Źródła i dalsza lektura` → strona ze źródłami. Linki pisz jako
  `- Etykieta: https://adres` — robi się z tego klikalny link.
- Linki Obsidiana `[[Coś]]` zamieniają się w zwykły tekst (nie psują strony).

Komunikat „section not found…" znaczy, że któryś z tych nagłówków zniknął lub zmienił
nazwę — przywróć go i zapisz. W trybie `--watch` skrypt spróbuje ponownie po następnym zapisie.

Wzór poprawnego pliku: `trips/_szablon/tresc.md`.

## Inne zmiany
- **Nowy dzień:** wklej kolejny blok `## Dzień N: ...` do sekcji `# Plan wyjazdu`.
- **Nowa podstrona** (np. słowniczek): blok `[[pages]]` w `trip.toml` + sekcja `# Nagłówek`
  w `tresc.md` (przed `# Źródła i dalsza lektura`); nagłówek musi się zgadzać z `heading`.
- **Nazwa, opis, fakty w hero, kolor, analityka:** `trips/<wyprawa>/trip.toml`.
- **Kolory/wygląd wspólny dla wszystkich wypraw:** `engine/assets/style.css` —
  uwaga, zmiana dotyka **każdej** wyprawy.
- **Zdjęcia:** wrzuć do `trips/<wyprawa>/assets/` i wstaw w notatce jako
  `![opis](assets/plik.jpg)` (działa też `![[plik.jpg]]` z Obsidiana).
- **Nowa wyprawa:** skopiuj `trips/_szablon` jako `trips/<slug>`, wypełnij `trip.toml`,
  `tresc.md`, `pois.csv`, dodaj `route.gpx`, uruchom `python engine/gen_route.py <slug>`.

## Mapa — skąd się bierze

`trips/<wyprawa>/assets/route-data.js` jest **generowany** przez `engine/gen_route.py` z:

- `route.gpx` albo `route.kml` — linia trasy, upraszczana do ok. 1000 punktów,
- `pois.csv` — punkty na mapie, nagłówek `day,name,lat,lon,blurb` (kolumny dodatkowe,
  np. `type`, są przepisywane do punktu). Opis z przecinkami ujmij w cudzysłów.

```
python engine/gen_route.py albania-2026
```

- Zmieniasz **ślad** → podmień `route.gpx`/`route.kml` i uruchom skrypt.
- Zmieniasz **punkty** (nazwa, opis, dzień) → edytuj `pois.csv` i uruchom skrypt.
- Ręczne dłubanie w `route-data.js` zniknie przy następnym uruchomieniu skryptu.

**Rumunia nie ma pliku śladu.** Jej `route-data.js` to jedyna kopia trasy — skrypt
odmówi jej regeneracji i nic nie nadpisze. Nie usuwaj tego pliku.

## Dwie wersje każdej wyprawy

Build robi **dwie** wersje z tego samego `tresc.md`:

- `index.html` + `dzien-N.html` + podstrony — **wersja pełna**: interaktywna mapa
  Leaflet, fonty Google, osobna strona na dzień.
- `mobile.html` — **jedna strona, w pełni offline**: cały CSS i szkic trasy (SVG)
  są w środku pliku, zero zapytań do sieci. Dni i sekcje jako zwijane `<details>`.
  Szkic się nie rysuje, gdy ślad ma mniej niż `svg_min_points` punktów (`trip.toml`).

**Przełączanie.** Na telefonie `index.html` sam przenosi na `mobile.html` (wykrywanie po
urządzeniu: `pointer:coarse` albo ekran dotykowy + wąski ekran — wąskie okno na desktopie
zostaje przy wersji pełnej). Link „Wersja pełna z mapą" na stronie mobilnej wchodzi na
`index.html?full=1`, a ten wybór jest pamiętany osobno dla każdej wyprawy
(`localStorage['gp-view:<wyprawa>']`). W nawigacji wersji pełnej jest link „📱 Telefon".

**Zapis offline.** Przycisk „Zapisz tę stronę offline" to zwykły link `<a download>` do
`mobile.html` — Safari na iPhonie zapisuje plik w Plikach, a otwarty z dysku wygląda identycznie.
