#!/bin/bash
# Live preview of a trip. Usage: ./build-mac-linux.command <slug>
# Without an argument (e.g. after a double-click) it asks which trip to open.
cd "$(dirname "$0")"
SLUG="$1"
if [ -z "$SLUG" ]; then
  echo "Available trips:"
  for d in trips/*/; do n=$(basename "$d"); case "$n" in _*) ;; *) echo "  $n";; esac; done
  read -r -p "Trip name: " SLUG
fi
[ -z "$SLUG" ] && { echo "No trip given."; exit 1; }
echo "Live preview: $SLUG. Edit trips/$SLUG/tresc.md and save — the site refreshes itself."
echo "Stop: Ctrl+C."
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
"$PY" build.py "$SLUG" --watch
