#!/usr/bin/env bash
# Strait Signal — durable collector burst.
#
# Why this exists: a 6-hour foreground collector dies when the session that
# started it ends (that is what happened on 2026-10-13: the run started
# ~19:52 PKT and stopped writing at ~20:14 PKT). The durable pattern is
# short bursts on a schedule (e.g. hourly), all appending to the same log.
# Gap detection still works: a 10-min collection gap is far below the 6h
# gap threshold, so scheduled bursts do not create false gap events.
# (STS runs can be split by a burst boundary — detector output notes that.)
#
# Key handling — the key is NEVER pasted in chat and NEVER written by Muse:
#   1. Revoke the key that was pasted in chat at aisstream.io/apikeys
#      (delete it, create a fresh one) — chat history is not a safe place.
#   2. Save the FRESH key in a file only you own, via an editor (not echo,
#      which lands in shell history):
#        mkdir -p ~/.config/strait-signal
#        nano ~/.config/strait-signal/aisstream.key   # paste key, save, exit
#        chmod 600 ~/.config/strait-signal/aisstream.key
#   3. Run this script:  bash pipeline/run_collector_burst.sh [seconds]
#      Default burst: 3000s (50 min) — sized to fit an hourly schedule.
#      The key is read into memory for this run only and never printed,
#      logged, or written to any file by this script.
#
# After the burst, the detector runs once over the full log so
# data/detected_events.json stays fresh.
set -u
cd "$(dirname "$0")/.." || exit 1

DURATION="${1:-3000}"
KEY_FILE="$HOME/.config/strait-signal/aisstream.key"
LOG="data/collector.log"
mkdir -p data

if [ -n "${AISSTREAM_API_KEY:-}" ]; then
  : # env var already set for this shell — use it, do not print it
elif [ -f "$KEY_FILE" ]; then
  PERMS="$(stat -c %a "$KEY_FILE" 2>/dev/null || stat -f %Lp "$KEY_FILE")"
  if [ "$PERMS" != "600" ]; then
    echo "REFUSING: $KEY_FILE has permissions $PERMS — run: chmod 600 $KEY_FILE" | tee -a "$LOG"
    exit 2
  fi
  AISSTREAM_API_KEY="$(cat "$KEY_FILE")"
  export AISSTREAM_API_KEY
else
  echo "SETUP NEEDED: no AISSTREAM_API_KEY in env and no $KEY_FILE" | tee -a "$LOG"
  echo "Create the key file (editor, not echo) per the header of this script, then re-run." | tee -a "$LOG"
  exit 2
fi

PY="$(ls ~/workspace/.venv-fc/bin/python 2>/dev/null || echo python3)"
echo "$(date -u +%FT%TZ) burst start duration=${DURATION}s" >> "$LOG"
# shellcheck disable=SC2086
"$PY" pipeline/aisstream_client.py --duration "$DURATION" >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) burst end" >> "$LOG"
"$PY" pipeline/detect.py --messages data/ais_raw.jsonl --out data/detected_events.json >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) detection refreshed" >> "$LOG"
# Disk guard: raw log grows ~1 MB per 50-min burst; warn before it gets large.
SIZE_MB="$(du -m data/ais_raw.jsonl 2>/dev/null | cut -f1)"
if [ "${SIZE_MB:-0}" -gt 100 ]; then
  echo "$(date -u +%FT%TZ) WARNING: ais_raw.jsonl is ${SIZE_MB} MB — archive it before it grows further" >> "$LOG"
fi
