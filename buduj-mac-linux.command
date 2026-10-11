#!/bin/bash
# Podgląd na żywo wyprawy. Użycie: ./buduj-mac-linux.command <slug>
# Bez argumentu (np. po dwukliku) pyta o wyprawę.
cd "$(dirname "$0")"
SLUG="$1"
if [ -z "$SLUG" ]; then
  echo "Dostępne wyprawy:"
  for d in trips/*/; do n=$(basename "$d"); case "$n" in _*) ;; *) echo "  $n";; esac; done
  read -r -p "Podaj nazwę wyprawy: " SLUG
fi
[ -z "$SLUG" ] && { echo "Nie podano wyprawy."; exit 1; }
echo "Podgląd na żywo: $SLUG. Edytuj trips/$SLUG/tresc.md i zapisz — strona odświeży się sama."
echo "Zatrzymanie: Ctrl+C."
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
"$PY" build.py "$SLUG" --watch
