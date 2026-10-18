#!/usr/bin/env bash
# Hormuz Watch demo launcher: refresh live keyless context, then serve locally.
# Usage:  bash run_demo.sh          (serves on http://localhost:8000)
#         bash run_demo.sh 8080     (custom port)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8000}"
echo "== fetching live keyless context (Open-Meteo / USGS / GDACS) =="
python3 pipeline/fetch_live.py || echo "WARNING: live fetch failed — UI will show the last good snapshot / an error card."
echo
echo "== serving demo on http://localhost:${PORT}  (Ctrl-C to stop) =="
python3 -m http.server "$PORT"
