# Strona wyprawy „Cienie Austro-Węgier" — instrukcja obsługi

To repozytorium zamienia **jeden plik z notatkami** (`tresc.md`) w gotową stronę:
stronę główną z mapą trasy, 9 podstron dni i stronę źródeł.

Masz dwa sposoby pracy i **oba korzystają z tego samego `tresc.md`** — możesz ich
używać wymiennie:

1. **Na komputerze** — podgląd na żywo (watch). Edytujesz w Obsidianie, strona
   odświeża się od razu u Ciebie.
2. **Z telefonu / przeglądarki** — edytujesz `tresc.md` na GitHubie, a GitHub sam
   buduje i publikuje stronę (Actions).

---

## Najważniejsze w 30 sekundach

- **Edytujesz zawsze tylko `tresc.md`.** Reszta robi się sama.
- **Na kompie:** otwórz Obsidiana → uruchom podgląd (dwuklik `buduj-windows.bat`
  / `buduj-mac-linux.command`) → pisz i zapisuj → strona w przeglądarce odświeża się sama.
- **Z telefonu:** w aplikacji GitHub otwórz `tresc.md`, popraw, „Commit". Po ~2 min
  strona w sieci jest zaktualizowana.
- **ZŁOTA ZASADA synchronizacji:** zanim zaczniesz pisać na kompie — **pobierz zmiany**
  (pull). Gdy skończysz — **wyślij** (push). Jeśli używasz wtyczki Obsidian Git
  (patrz niżej), robi to za Ciebie.

Adres strony po publikacji: `https://<twoja-nazwa>.github.io/<repo>/`
(wpisz tu swój, gdy już będzie, żeby mieć pod ręką).

---

## 1. Konfiguracja — robisz RAZ

Odhacz po kolei:

- [ ] **Python 3** na komputerze. Sprawdź w terminalu: `python --version`
      (lub `python3 --version`). Jak brak → https://www.python.org/downloads/
      (na Windowsie przy instalacji zaznacz „Add Python to PATH").
- [ ] **Repozytorium na GitHubie** (publiczne, np. `longinada-2026`) z całą zawartością
      tego folderu — łącznie z ukrytym `.github/`. Najpewniej przez git lub GitHub
      Desktop:
      ```bash
      cd <ten-folder>
      git init && git add . && git commit -m "Strona wyprawy"
      git branch -M main
      git remote add origin https://github.com/<user>/longinada-2026.git
      git push -u origin main
      ```
- [ ] **Pages w trybie Actions:** w repo → **Settings → Pages → Build and deployment
      → Source: „GitHub Actions"** (NIE „Deploy from a branch").
- [ ] **Sprawdź pierwszą publikację:** zakładka **Actions** → workflow „Zbuduj i
      opublikuj stronę" → po ✓ wejdź na adres strony.
- [ ] **(zalecane) Obsidian Git** — żeby synchronizacja komputer↔telefon działała sama:
      otwórz folder repo jako sejf w Obsidianie → Settings → Community plugins →
      zainstaluj i włącz **Obsidian Git** → w jego ustawieniach włącz
      „pull przy starcie" i automatyczny „commit‑and‑sync" co np. 10 minut.

Po tym etapie nie wracasz już do konfiguracji — pracujesz jak niżej.

---

## 2. Codzienna praca

### A. Na komputerze (główny tryb — z podglądem na żywo)
1. Otwórz Obsidiana na tym sejfie. (Obsidian Git pobierze ewentualne zmiany z telefonu.)
2. Uruchom podgląd na żywo — **dwuklik**:
   - Windows: `buduj-windows.bat`
   - Mac: `buduj-mac-linux.command` (gdyby blokował: prawy klik → Otwórz → Otwórz)
   - albo w terminalu w tym folderze: `python build.py --watch`
3. Otworzy się przeglądarka (`http://localhost:8000`). **Zostaw to okno otwarte.**
4. Edytuj `tresc.md` w Obsidianie i zapisuj (Ctrl/Cmd+S) — podgląd odświeża się sam.
5. Gdy skończysz: zamknij podgląd (`Ctrl+C` w oknie skryptu) i **wyślij zmiany**
   (Obsidian Git zrobi commit‑and‑sync sam; albo ręcznie — patrz sekcja 3).
   GitHub po pushu opublikuje nową wersję w sieci.

> Podgląd na żywo działa **tylko u Ciebie** i nie wymaga internetu poza mapą/fontami.
> Wysłanie do GitHuba to osobny krok (push) — dopiero on aktualizuje stronę w sieci.

### B. Z telefonu / dowolnej przeglądarki (przez GitHub)
1. W aplikacji **GitHub** (lub na github.com) wejdź w repo → otwórz `tresc.md`.
2. Ołówek (Edit) → popraw tekst → **Commit changes**.
3. GitHub sam zbuduje i opublikuje stronę (zakładka Actions pokaże postęp; ~1–2 min).
4. Następnym razem na komputerze: **pobierz te zmiany** (Obsidian Git zrobi to przy
   starcie; albo `git pull`), żeby mieć je u siebie.

---

## 3. Synchronizacja — jak się nie pogubić

Komputer i GitHub to ten sam projekt w dwóch miejscach. Żeby się zgadzały:

- **Zanim zaczniesz pisać na kompie:** pobierz najnowsze (`pull`).
- **Gdy skończysz na kompie:** wyślij (`push`).

Z **Obsidian Git** dzieje się to automatycznie (pull przy starcie + cykliczny
commit‑and‑sync). Bez wtyczki, ręcznie w terminalu w folderze repo:
```bash
git pull            # na początku pracy
# ... edytujesz tresc.md ...
git add tresc.md
git commit -m "Aktualizacja notatek"
git push            # na końcu
```

**Kiedy może być konflikt?** Tylko jeśli ten sam fragment `tresc.md` zmienisz
równolegle i na telefonie, i na kompie bez wcześniejszego `pull`. Przy pracy w
pojedynkę to rzadkość. Gdyby się zdarzył, git/Obsidian Git Cię o tym uprzedzi —
wtedy najprościej zostawić jedną wersję tekstu i zapisać.

---

## 4. Co jest czym (żebyś wiedziała, czego nie ruszać)

| Plik / folder | Do czego | Edytujesz? |
|---|---|---|
| `tresc.md` | **Twoje notatki** — źródło całej strony | **TAK** |
| `JAK-EDYTOWAC.md` | zasady pisania w `tresc.md` (nagłówki, format dnia, dodanie dnia) | do czytania |
| `build.py` | generator strony (uruchamia go watch i Actions) | nie |
| `.github/workflows/deploy.yml` | automat: buduje i publikuje po pushu | nie |
| `strona/assets/route-data.js` | punkty i linia na mapie | tylko gdy chcesz zmienić mapę |
| `strona/assets/style.css` | kolory i wygląd (zmienne na górze pliku) | tylko gdy chcesz zmienić wygląd |
| `strona/*.html` | generowane automatycznie | **nie** (i tak są pomijane w gicie) |
| `buduj-*.bat / .command` | uruchamiacze podglądu na żywo | nie |

Jak i co możesz pisać w `tresc.md` (jakie nagłówki muszą zostać, jak dodać kolejny
dzień, format daty i kilometrów) — wszystko jest w **`JAK-EDYTOWAC.md`**.

---

## 5. Gdy coś nie gra

- **Podgląd na żywo się nie odświeża** → sprawdź, czy okno skryptu (`--watch`) wciąż
  działa i czy w przeglądarce jest `http://localhost:8000` (nie otwarty plik z dysku).
  Pomaga też ręczne odświeżenie (F5).
- **„nie znalazłem sekcji…" przy budowaniu** → w `tresc.md` zniknął lub zmienił nazwę
  któryś nagłówek (np. `# Plan wyjazdu`, `## Dzień N: ...`). Przywróć go i zapisz.
  Lista wymaganych nagłówków jest w `JAK-EDYTOWAC.md`.
- **`python` nie działa / „command not found"** → spróbuj `python3 build.py --watch`.
  Jeśli dalej nic — Python nie jest zainstalowany (patrz sekcja 1).
- **Na GitHubie workflow świeci się na czerwono** → wejdź w **Actions**, kliknij
  nieudany przebieg; na dole zobaczysz komunikat błędu (zwykle ta sama sprawa co
  „nie znalazłem sekcji" — literówka w nagłówku w `tresc.md`).
- **Zmiany z telefonu nie widać na kompie** → zrób `git pull` (albo zrestartuj
  Obsidiana z włączonym Obsidian Git).
- **Strona w sieci się nie zmieniła** → sprawdź w Actions, czy publikacja przeszła na
  ✓; bywa, że trzeba odświeżyć stronę z pominięciem cache (Ctrl/Cmd+Shift+R).

---

Miłej roboty — i miłej wyprawy.
