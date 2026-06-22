#!/bin/bash
cd "$(dirname "$0")"
echo "Podgląd na żywo. Edytuj tresc.md w Obsidianie, zapisuj — strona odświeży się sama."
echo "Zatrzymaj: Ctrl+C."
python3 build.py --watch || python build.py --watch
