#!/usr/bin/env python3
"""Real AISStream client for the Strait of Hormuz corridor.

Connects to the AISStream WebSocket (wss://stream.aisstream.io/v0/stream),
subscribes with a Hormuz bounding box + message-type filter, and writes:
  - data/ais_raw.jsonl     : every raw AIS envelope received (append-only log)
  - data/vessel_state.json : latest known state per MMSI (position, name, type...)

The API key is read ONLY from the AISSTREAM_API_KEY environment variable.
It is NEVER printed, logged, or written to any file. If the variable is
missing/empty, this script exits with setup instructions instead of connecting.

Requires: websockets  (pip install -r pipeline/requirements.txt)

Usage:
    export AISSTREAM_API_KEY="paste-your-free-key-here"   # never commit this
    python3 pipeline/aisstream_client.py --duration 300   # 5-minute capture
    python3 pipeline/aisstream_client.py --max-messages 5000
    python3 pipeline/aisstream_client.py --check-config   # no connection, just config check

Then run the detector:
    python3 pipeline/detect.py --messages data/ais_raw.jsonl --out data/detected_events.json

AISStream protocol notes (from aisstream.io public docs):
  - Send ONE JSON subscription message within 3 seconds of connecting.
  - The key goes in the subscription message body field "APIKey"
    (not in an HTTP header).
  - BoundingBoxes: list of [[lat, lon], [lat, lon]] corner pairs.
  - FilterMessageTypes constrains the firehose; without it the server may
    disconnect a slow client (TCP queue limit).
"""

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

# Strait of Hormuz + Gulf of Oman approach. Same corridor as the replay set.
BBOX = [[27.5, 55.0], [25.0, 59.5]]

MESSAGE_TYPES = [
    "PositionReport",
    "ShipStaticData",
    "StaticDataReport",
    "StandardClassBPositionReport",
    "ExtendedClassBPositionReport",
]

STREAM_URL = "wss://stream.aisstream.io/v0/stream"


def here(*parts):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def system_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_position(envelope):
    """Return (lat, lon, sog, cog, heading) or None for position messages."""
    msg = envelope.get("Message") or {}
    for key in ("PositionReport", "StandardClassBPositionReport",
                "ExtendedClassBPositionReport"):
        if key in msg and isinstance(msg[key], dict):
            pr = msg[key]
            try:
                return (float(pr["Latitude"]), float(pr["Longitude"]),
                        pr.get("Sog"), pr.get("Cog"), pr.get("TrueHeading"))
            except (KeyError, TypeError, ValueError):
                return None
    return None


def extract_static(envelope):
    """Return static-voyage fields or {} for static messages."""
    msg = envelope.get("Message") or {}
    for key in ("ShipStaticData", "StaticDataReport"):
        if key in msg and isinstance(msg[key], dict):
            sd = msg[key]
            return {
                "ship_name": sd.get("ShipName") or sd.get("CallSign"),
                "call_sign": sd.get("CallSign"),
                "ship_type": sd.get("ShipType"),
                "destination": sd.get("Destination"),
                "eta": sd.get("Eta"),
                "draught": sd.get("Draught"),
                "dimension": sd.get("Dimension"),
            }
    return {}


class Collector:
    def __init__(self, raw_path, state_path, max_messages=0, save_every=100):
        self.raw_path = raw_path
        self.state_path = state_path
        self.max_messages = max_messages
        self.save_every = save_every
        self.state = {}
        self.count = 0
        self.started = time.time()

    def handle(self, envelope):
        meta = envelope.get("MetaData") or {}
        mmsi = str(meta.get("MMSI", ""))
        if not mmsi:
            return
        entry = self.state.setdefault(mmsi, {"mmsi": mmsi, "message_count": 0})
        entry["message_count"] += 1
        entry["last_seen_utc"] = meta.get("time_utc") or datetime.now(timezone.utc).isoformat()
        if meta.get("ShipName"):
            entry["ship_name"] = meta["ShipName"]
        pos = extract_position(envelope)
        if pos:
            lat, lon, sog, cog, heading = pos
            entry.update({"latitude": lat, "longitude": lon, "sog_knots": sog,
                          "cog_deg": cog, "true_heading": heading,
                          "last_position_utc": entry["last_seen_utc"]})
        entry.update({k: v for k, v in extract_static(envelope).items() if v})
        with open(self.raw_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope) + "\n")
        self.count += 1
        if self.count % self.save_every == 0:
            self.save_state()

    def save_state(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"updated_at_utc": datetime.now(timezone.utc).isoformat(),
                       "vessels": self.state}, fh, indent=1)
        os.replace(tmp, self.state_path)

    def summary(self):
        return (f"messages={self.count} vessels={len(self.state)} "
                f"elapsed_s={time.time() - self.started:.0f}")


async def run_stream(api_key, collector, duration_s, stop_event):
    import websockets  # imported here so --check-config works without the dep
    deadline = time.time() + duration_s if duration_s > 0 else None
    backoff = 5
    while not stop_event.is_set():
        try:
            async with websockets.connect(STREAM_URL, max_size=4 * 1024 * 1024) as ws:
                # Must subscribe within 3 seconds of connecting.
                await ws.send(json.dumps({
                    "APIKey": api_key,
                    "BoundingBoxes": [BBOX],
                    "FilterMessageTypes": MESSAGE_TYPES,
                }))
                print("subscribed to AISStream (Hormuz bbox). Waiting for messages…",
                      flush=True)
                backoff = 5
                while not stop_event.is_set():
                    if deadline and time.time() > deadline:
                        stop_event.set()
                        break
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        continue
                    envelope = json.loads(raw)
                    collector.handle(envelope)
                    if collector.max_messages and collector.count >= collector.max_messages:
                        stop_event.set()
                        break
                    if collector.count % 500 == 0 and collector.count:
                        print(f"  … {collector.summary()}", flush=True)
        except Exception as exc:  # noqa: BLE001 - reconnect with backoff
            if stop_event.is_set():
                break
            print(f"connection error ({exc}); reconnecting in {backoff}s…", flush=True)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
    collector.save_state()
    print(f"done. {collector.summary()}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=0,
                    help="Seconds to stream (0 = until Ctrl-C).")
    ap.add_argument("--max-messages", type=int, default=0,
                    help="Stop after N messages (0 = unlimited).")
    ap.add_argument("--check-config", action="store_true",
                    help="Validate config (key present, paths writable) without connecting.")
    args = ap.parse_args()

    sys_dir = system_dir()
    raw_path = os.path.join(sys_dir, "data", "ais_raw.jsonl")
    state_path = os.path.join(sys_dir, "data", "vessel_state.json")
    os.makedirs(os.path.join(sys_dir, "data"), exist_ok=True)

    api_key = os.environ.get("AISSTREAM_API_KEY", "").strip()
    if args.check_config:
        print(f"STREAM_URL={STREAM_URL}")
        print(f"BBOX={BBOX}")
        print(f"FilterMessageTypes={MESSAGE_TYPES}")
        print(f"raw log -> {raw_path}")
        print(f"vessel state -> {state_path}")
        if api_key:
            print("AISSTREAM_API_KEY: SET (value not shown)")
        else:
            print("AISSTREAM_API_KEY: MISSING — see README.md 'Get the free AISStream key'.")
            return 2
        try:
            import websockets  # noqa: F401
            print("websockets package: installed")
        except ImportError:
            print("websockets package: MISSING — run: pip install -r pipeline/requirements.txt")
            return 2
        return 0

    if not api_key:
        print("ERROR: AISSTREAM_API_KEY is not set.", file=sys.stderr)
        print("Get a FREE key (2 minutes, GitHub sign-in) — steps in README.md:", file=sys.stderr)
        print("  1. https://aisstream.io  → sign in with GitHub", file=sys.stderr)
        print("  2. https://aisstream.io/apikeys  → create a key", file=sys.stderr)
        print("  3. export AISSTREAM_API_KEY=\"<your-key>\"  (never commit it)", file=sys.stderr)
        print("  4. re-run this script", file=sys.stderr)
        return 2

    collector = Collector(raw_path, state_path, max_messages=args.max_messages)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event = asyncio.Event()

    def _stop(*_a):
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_a: _stop())
    try:
        loop.run_until_complete(run_stream(api_key, collector, args.duration, stop_event))
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
