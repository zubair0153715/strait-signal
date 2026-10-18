# Hormuz Watch — Maritime Intelligence Demo (Prototype)

AIS-gap / STS-candidate detection for the Strait of Hormuz corridor.
**Demo/prototype, NOT a production system.** No outreach, no contact with anyone.

## What this is

A working map-based demo with three layers:

| Layer | Mode | Data |
|---|---|---|
| Vessel events | **HISTORICAL REPLAY** | One documented public incident (17 June 2025 collision, Gulf of Oman) with source links, per-field confidence, and explicit non-claims |
| Sea state + wind | **LIVE, keyless** | Open-Meteo Marine + Forecast APIs (3 corridor waypoints) |
| Earthquakes + disaster alerts | **LIVE, keyless** | USGS past-day feed + GDACS RSS, filtered to the corridor |
| Live vessel positions (AIS) | **NOT ACTIVE — needs your free signup** | AISStream WebSocket pipeline is fully built; it runs once you add your free key (below) |

**The UI banner always states the data mode. No live vessel data is shown, and no
vessel data is faked, simulated, or presented as live.**

## Quick start (no key needed)

```bash
cd ~/workspace/maritime-intel/system
bash run_demo.sh          # refreshes live context, serves on http://localhost:8000
```

Open http://localhost:8000 in a browser. (Serving over HTTP is required —
`file://` may block the page's `fetch()` of the JSON files.)

What you will see:
- Map of the Hormuz corridor (schematic bbox outline — **not for navigation**)
- One red marker: H1 replay incident (25.2869, 56.79017), with a popup
- Blue markers: live sea-state waypoints; orange markers: any USGS quakes in corridor (24h)
- Event table with vessel, type, timestamps, lat/lon, confidence, evidence/provenance
- Live-context cards with fetch timestamps
- "How detection works" panel (the rules the detector applies to live AIS)

## The historical replay (read before judging the demo)

The replay set contains **exactly one** documented incident:

- **H1 — FRONT EAGLE / ADALYNN collision, 17 June 2025, 00:15 local (20:15 UTC 16 June),
  Gulf of Oman (~15 NM off Fujairah).** Position 25.2869, 56.79017 as reported by
  TankerTrackers.com (quoted in Lokmat Times). Owner + UKMTO assessed it as a
  navigational incident, not conflict-related. 24 crew evacuated, no injuries,
  no pollution reported at the time.

Deliberate honesty points:
- **H1 is NOT an STS event.** The replay set contains **no confirmed STS transfer**.
  Do not present the collision as an STS detection.
- The "shadow fleet" description of ADALYNN in some media is **UNVERIFIED** in this
  demo. No sanctions-list match was checked; no vessel here is labelled "sanctioned".
- H1's coordinates come from a single public source and were **not independently verified**.
- GPS/electronic interference in the Gulf in June 2025 is reported *context*, not a
  proven cause of the collision.

## Deployed collector (durable fix — the collector now survives restarts)

The AIS collector also runs **inside the clinic-demo FastAPI Cloud app**
(no 4th app — the free plan caps at 3), so a VM or deploy restart brings
it back automatically. Code: `~/workspace/clinic-demo/app/strait_signal/`
(collector + detector + routes, wired into `app/main.py` lifespan).

- Live status: `GET https://clinic-demo.fastapicloud.dev/strait-signal/status`
- Human-readable live page (mobile-friendly): `https://clinic-demo.fastapicloud.dev/strait-signal/live`
  → collector state, `key_set` (boolean ONLY — never the key value),
  messages/vessels seen, last event time.
- Live events: `GET https://clinic-demo.fastapicloud.dev/strait-signal/events`
  → detected events JSON, candidate-labelled, with provenance.
- Events live in memory (capped) + an append-only JSONL file in the
  container. Container storage is wiped on deploy, so **do not treat
  container state as durable** — the live endpoints are the working view.
- If the key is unset, the collector logs "key not set — collector idle",
  retries every 5 minutes, and the app keeps serving normally. Bad keys
  back off (5s doubling to 300s) instead of crash-looping.

### The user's one step — set the secret, then say "redeploy"

1. In the **FastAPI Cloud dashboard**, open the **clinic-demo** app →
   Environment variables → add a **SECRET** variable:
   - Name: `AISSTREAM_API_KEY`
   - Value: the key (paste it in the dashboard form only — never in chat,
     never in a file).
2. Tell the agent **"redeploy"** — the agent redeploys clinic-demo so the
   app picks up the new secret, then verifies
   `/strait-signal/status` shows `key_set: true` and `status: streaming`.

The local transient-key runs below are now the **fallback only**
(useful for a quick manual capture); the deployed collector is the
durable path. Never paste the key into chat, even for a local run —
use a shell `export` for the current session only (below).

## Get the free AISStream key (the user's step — ~2 minutes, $0)

Live vessel positions come from AISStream (free terrestrial AIS WebSocket).
This is the **only** step that needs the user — everything else is built.

1. Go to **https://aisstream.io** and **sign in with GitHub**.
2. Open **https://aisstream.io/apikeys** and **create a new API key**.
3. Keep the key private. **Never paste it into chat, never commit it to a file.**
   Export it for the current shell session only:
   ```bash
   export AISSTREAM_API_KEY="<your-key>"
   ```
4. Check the setup (no connection, key value never printed):
   ```bash
   pip install -r pipeline/requirements.txt   # installs `websockets`
   python3 pipeline/aisstream_client.py --check-config
   ```
5. Capture live AIS for the corridor (e.g. 5 minutes):
   ```bash
   python3 pipeline/aisstream_client.py --duration 300
   # writes data/ais_raw.jsonl (raw message log) + data/vessel_state.json (latest per MMSI)
   ```
6. Run the detector:
   ```bash
   python3 pipeline/detect.py --messages data/ais_raw.jsonl --out data/detected_events.json
   ```
   Output is candidate events only (see "Legal red lines" below).

> Note: `data/ais_raw.jsonl` and `data/detected_events.json` are NOT shipped in
> this demo (no key → no capture). The `.env.example` file shows the variable
> name with an empty placeholder. A `.gitignore` mindset applies: never commit
> `AISSTREAM_API_KEY`, `data/ais_raw.jsonl`, or any file containing the key.

## Pipeline

```
fetch_live.py        stdlib-only. Pulls Open-Meteo (sea+wind), USGS quakes, GDACS alerts
                     → data/live_context.json (with source URLs + fetch timestamp)

aisstream_client.py  Real AISStream WebSocket client (needs `websockets` + key).
                     Subscribes: Hormuz bbox 25.0–27.5°N, 55.0–59.5°E,
                     PositionReport + static message types.
                     → data/ais_raw.jsonl (append-only raw log)
                     → data/vessel_state.json (latest state per MMSI)

detect.py            Stdlib-only detector over the raw log.
                     GAP: consecutive in-corridor reports > 6h apart (tunable).
                     STS CANDIDATE: two vessels ≤ 0.5 NM apart, both ≤ 2 kt,
                     continuously ≥ 30 min (all tunable).
                     → data/detected_events.json (candidates + provenance)

test_detect.py       Unit tests on LABELED-SYNTHETIC fixtures (in-test only).
                     Run:  python3 -m unittest pipeline/test_detect.py -v
                     Synthetic fixtures never enter data/ or the UI.
```

## Tests / verification performed (2026-10-13)

- `python3 -m unittest pipeline/test_detect.py` — detector logic (gap + STS + negatives).
- `python3 pipeline/fetch_live.py` — live keyless feeds verified working:
  Open-Meteo Marine (HTTP 200, real wave data), USGS GeoJSON (HTTP 200),
  GDACS RSS (HTTP 200).
- `python3 -m http.server` + HTTP fetch of `index.html` — page serves.
- AISStream client: `--check-config` path verified without a key (exits with setup
  instructions, never prints a key). A live WebSocket connection was NOT tested
  (no key in this environment) — the first live run is the user's step above.
  The subscription format follows AISStream's public docs (see LICENSE-NOTES.md).
- Deployed collector (2026-10-14): verified live at
  `https://clinic-demo.fastapicloud.dev/strait-signal/status` — boots with
  `key_set: false`, status `idle`, existing routes intact; with a dummy key
  it attempts to connect, backs off on auth failure, and the app stays up.

## Known limits (do not hide these in a pitch)

- Free terrestrial AIS has regional gaps + latency; open-ocean satellite AIS is
  a paid layer this demo does not have. A "gap" can be a receiver gap, not a
  switched-off transponder.
- Sentinel-1 SAR correlation (the "second sensor" that would confirm a dark
  contact) is NOT built yet — it needs Copernicus auth + SAR processing.
  Until then, every alert is single-sensor and must say so.
- One replay incident does not validate the detector. Validation = detector
  run on real AIS + manual review of every candidate.
- Solo + free feeds cannot promise 24/7 uptime or SLA. This demo is a
  verification artefact, not a service.

## Legal red lines

1. **No named-person tracking.** This system tracks vessels (MMSI/IMO), never people.
   Do not add crew/passenger/owner-personal data.
2. **No military / private-jet targeting product.** No targeting use-case, ever.
   Do not add military vessels, aircraft, or any targeting feature.
3. **No safety-critical claims.** Nothing here is for navigation, collision
   avoidance, or emergency response. The map is explicitly "not for navigation".
4. **Provenance + timestamps on every alert.** Detector output carries source file,
   parameters, generation time, and message counts. Replay rows carry source links.
5. **Never label a vessel "sanctioned" without an official list match.**
   Correct language: "AIS-gap event / STS candidate, matches pattern X".
   Media descriptions ("shadow fleet") are allegations, not findings — label them so.
6. **No defamation risk.** Do not publish accusations ("sanctions evasion",
   "smuggling") about named vessels. Publish *observations* (gap, geometry, time)
   with evidence, and let the buyer / authority draw conclusions.
7. **No ToS violations.** Do not scrape MarineTraffic, VesselFinder, Kpler, or any
   site against its terms. AIS comes from AISStream (its own terms) or another
   licensed feed. News sources are cited, not scraped or redistributed.
8. **No outbound contact.** This demo sends nothing to anyone.

## Data licensing

See **LICENSE-NOTES.md** for per-source commercial-use terms, attribution
requirements, and what is still unverified. Rule of thumb: **check before
commercial use** for anything marked unverified.

## File map

```
system/
├── index.html / app.js / style.css   map UI (Leaflet via CDN)
├── data/
│   ├── historical_replay.json        H1 incident (sourced, with non-claims)
│   └── live_context.json             generated by fetch_live.py (live keyless)
├── pipeline/
│   ├── fetch_live.py                 keyless live feeds (stdlib)
│   ├── aisstream_client.py           real AISStream client (needs key + websockets)
│   ├── detect.py                     gap + STS-candidate detector (stdlib)
│   ├── test_detect.py                unit tests (synthetic fixtures only)
│   └── requirements.txt              websockets
├── .env.example                      key placeholder (empty — never a real key)
├── run_demo.sh                       fetch live context + serve locally
├── README.md                         this file
└── LICENSE-NOTES.md                  per-source licensing + ToS notes
```
