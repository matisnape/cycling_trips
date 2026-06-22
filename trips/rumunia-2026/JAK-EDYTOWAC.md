# Jak edytować stronę w Obsidianie (z podglądem na żywo)

Edytujesz **jeden plik** — `tresc.md` — w Obsidianie. Skrypt pilnuje go w tle i po
każdym zapisie automatycznie przebudowuje całą stronę, a podgląd w przeglądarce
**odświeża się sam**. Nie dotykasz HTML‑i ręcznie.

## Co jest w tym folderze
```
tresc.md                  ← TO EDYTUJESZ (Twoja notatka w markdownie)
build.py                  ← skrypt, który robi z tego stronę
buduj-windows.bat         ← dwuklik na Windowsie (tryb na żywo)
buduj-mac-linux.command   ← dwuklik na Macu/Linuksie (tryb na żywo)
JAK-EDYTOWAC.md           ← ten plik
strona/                   ← WYNIK: gotowa strona (to wrzucasz na GitHub Pages)
   ├─ index.html, dzien-1…9.html, zrodla.html  (generowane — nie ruszaj)
   ├─ assets/   (style + mapa — nie ruszaj, chyba że chcesz zmienić wygląd)
   ├─ README.md (instrukcja publikacji)
   └─ .nojekyll
```

## Raz, na początek
Potrzebujesz **Pythona 3** (`python --version` w terminalu to sprawdzi; jeśli go nie
ma — https://www.python.org/downloads/, na Windowsie zaznacz „Add Python to PATH").
Bibliotekę `markdown` skrypt dograje sam przy pierwszym uruchomieniu.

## Podłączenie do Obsidiana — wybierz jeden sposób

**A) Najprościej — otwórz ten folder jako sejf.**
W Obsidianie: *Open another vault → Open folder as vault* i wskaż ten folder.
`tresc.md` pojawi się jako notatka, którą edytujesz normalnie w Obsidianie.

**B) Trzymasz notatkę w swoim głównym sejfie.**
Otwórz `build.py` w Notatniku, znajdź na górze linijkę `SRC_OVERRIDE = ""` i wpisz
pełną ścieżkę do swojej notatki, np.:
```
SRC_OVERRIDE = r"C:\Users\Anks\Obsidian\Mój sejf\Longinada 2026.md"
```
(na Macu bez `r` i ze zwykłymi ukośnikami `/`). Zapisz `build.py`.

## Praca z podglądem na żywo
1. Uruchom tryb na żywo:
   - **Windows:** dwuklik `buduj-windows.bat`
   - **Mac:** dwuklik `buduj-mac-linux.command` (gdyby system blokował: prawy
     klik → Otwórz → Otwórz)
   - **albo z terminala** w tym folderze: `python build.py --watch`
2. Otworzy się przeglądarka z podglądem (`http://localhost:8000`). **Zostaw to okno
   uruchomione.**
3. Edytuj `tresc.md` w Obsidianie i zapisuj (Ctrl/Cmd+S). Po chwili strona w
   przeglądarce odświeży się sama.
4. Gdy skończysz: w oknie skryptu naciśnij `Ctrl+C`.
5. Publikacja: jeśli korzystasz z auto‑publikacji przez GitHub Actions (patrz
   `README.md`), wystarczy wysłać zmiany do repo — strona zbuduje się i opublikuje
   sama. Podgląd lokalny służy tylko do podejrzenia zmian u siebie, zanim je wyślesz.

> Bez podglądu, jednorazowe zbudowanie: `python build.py`.

## Zasady pisania w tresc.md (żeby skrypt się nie pogubił)
Skrypt rozpoznaje treść po nagłówkach — **zachowaj te nazwy i format**:

- `# Klucz do wyjazdu — ...` → wstęp na stronie głównej.
- `# Plan wyjazdu` → początek planu (kończy go linia `---`).
- Każdy dzień zaczyna się od linii w formacie:
  ```
  ## Dzień 3: Poniedziałek, 29.06.2026, Odorheiu Secuiesc > Sighișoara (68km)
  ```
  czyli `## Dzień <nr>: <dzień tygodnia>, <data>, <skąd> > <dokąd> (<km>km)`.
  Strzałkę robi znak `>`. Liczba przed `km` trafia do podsumowań.
- Punkty `-` zaraz pod nagłówkiem dnia → trafiają do boxu **„W skrócie"**.
- Wszystko po `### Miejsca i historia` → główna treść dnia.
- Podpunkty rób wcięciem (Tab lub 4 spacje). Pogrubienie `**tekst**`, kursywa `_tekst_`.
- `# Źródła i dalsza lektura` → strona źródeł. Linki pisz jako
  `- Etykieta: https://adres` — zrobi się z tego klikalny odnośnik.
- Linki Obsidiana `[[Coś]]` zamieniają się na zwykły tekst (nie psują strony).

Jeśli zobaczysz komunikat „nie znalazłem sekcji…", to znaczy, że któryś z tych
nagłówków zniknął lub się zmienił — przywróć go i zapisz. W trybie `--watch` skrypt
po prostu spróbuje ponownie przy następnym zapisie.

## Inne zmiany
- **Nowy dzień:** wklej kolejny blok `## Dzień N: ...` w sekcji `# Plan wyjazdu`.
- **Punkty na mapie:** `strona/assets/route-data.js` (czytelna lista `lat`/`lon`
  + numer dnia; jest tam też linia trasy `route`). Edycja tego pliku też wywoła
  odświeżenie w trybie na żywo.
- **Kolory/wygląd:** `strona/assets/style.css` — zmienne kolorów na górze pliku.
- **Zdjęcia:** wrzuć do `strona/assets/` i wstaw w notatce `![opis](assets/plik.jpg)`
  (działa też obsidianowe `![[plik.jpg]]`).
