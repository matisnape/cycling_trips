#!/bin/bash
cd "$(dirname "$0")"
echo "Live preview. Edit tresc.md in Obsidian and save — the site refreshes itself."
echo "Stop: Ctrl+C."
python3 build.py --watch || python build.py --watch
