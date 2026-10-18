#!/usr/bin/env python3
"""Fetch genuinely LIVE, KEYLESS context layers for the Hormuz corridor.

Sources (all keyless, no signup):
  - Open-Meteo Marine API  (wave height / direction / period, sea-surface temp)
  - Open-Meteo Forecast API (wind speed / gusts / direction)
  - USGS Earthquake feed, past day (GeoJSON), filtered to the corridor bbox
  - GDACS RSS (global disaster alerts), filtered to the corridor / region

This script fetches NO vessel / AIS data. Live vessel positions require the
AISStream key (see pipeline/aisstream_client.py and README.md).

Output: data/live_context.json, next to this repo's system/ directory.
Every record carries its source URL and the fetch timestamp (provenance).

Stdlib only. Usage:
    python3 pipeline/fetch_live.py [--out data/live_context.json]
"""

import argparse
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Strait of Hormuz corridor (expanded to include the Gulf of Oman approach).
BBOX = {"lat_min": 23.0, "lat_max": 29.0, "lon_min": 50.0, "lon_max": 61.0}

# Waypoints where sea-state / wind context is fetched.
WAYPOINTS = [
    {"id": "hormuz-west", "label": "Strait of Hormuz — west entrance",
     "lat": 26.55, "lon": 56.25},
    {"id": "hormuz-east", "label": "Strait of Hormuz — east exit / Gulf of Oman",
     "lat": 25.80, "lon": 57.20},
    {"id": "replay-site", "label": "H1 replay site vicinity (Gulf of Oman)",
     "lat": 25.29, "lon": 56.79},
]

OPEN_METEO_MARINE = "https://marine-api.open-meteo.com/v1/marine"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
GDACS_URL = "https://www.gdacs.org/xml/rss.xml"

HEADERS = {"User-Agent": "maritime-intel-demo/0.1 (research prototype; contact via repo README)"}


def fetch_json(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def nearest_current(hourly_times, values):
    """Return the value for the most recent hourly slot at/before now (UTC)."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    best_i, best_t = None, None
    for i, t in enumerate(hourly_times):
        try:
            dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt <= now and (best_t is None or dt > best_t):
            best_t, best_i = dt, i
    if best_i is None:
        return None, None
    return hourly_times[best_i], (values[best_i] if values and best_i < len(values) else None)


def fetch_waypoint(wp):
    """Sea state + wind for one waypoint. Returns dict with provenance."""
    marine_url = (
        f"{OPEN_METEO_MARINE}?latitude={wp['lat']}&longitude={wp['lon']}"
        "&hourly=wave_height,wave_direction,wave_period,sea_surface_temperature"
        "&forecast_days=1&timezone=UTC"
    )
    forecast_url = (
        f"{OPEN_METEO_FORECAST}?latitude={wp['lat']}&longitude={wp['lon']}"
        "&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        "&wind_speed_unit=kn&forecast_days=1&timezone=UTC"
    )
    out = {"waypoint": wp, "sources": [marine_url, forecast_url], "status": "ok"}
    try:
        marine = fetch_json(marine_url)
        h = marine.get("hourly", {})
        t, wh = nearest_current(h.get("time", []), h.get("wave_height"))
        _, wd = nearest_current(h.get("time", []), h.get("wave_direction"))
        _, wper = nearest_current(h.get("time", []), h.get("wave_period"))
        _, sst = nearest_current(h.get("time", []), h.get("sea_surface_temperature"))
        out["marine"] = {
            "time_utc": t,
            "wave_height_m": wh,
            "wave_direction_deg": wd,
            "wave_period_s": wper,
            "sea_surface_temperature_c": sst,
        }
    except Exception as exc:  # noqa: BLE001 - report, don't crash the whole fetch
        out["status"] = "marine_error"
        out["marine_error"] = str(exc)
    try:
        fc = fetch_json(forecast_url)
        h = fc.get("hourly", {})
        t, ws = nearest_current(h.get("time", []), h.get("wind_speed_10m"))
        _, wdir = nearest_current(h.get("time", []), h.get("wind_direction_10m"))
        _, gust = nearest_current(h.get("time", []), h.get("wind_gusts_10m"))
        out["wind"] = {
            "time_utc": t,
            "wind_speed_10m_kn": ws,
            "wind_direction_10m_deg": wdir,
            "wind_gusts_10m_kn": gust,
        }
    except Exception as exc:  # noqa: BLE001
        out["status"] = "wind_error" if out["status"] == "ok" else "marine_and_wind_error"
        out["wind_error"] = str(exc)
    return out


def fetch_quakes():
    """USGS past-day earthquakes inside the corridor bbox."""
    try:
        data = fetch_json(USGS_URL)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc), "source": USGS_URL, "events": []}
    events = []
    for f in data.get("features", []):
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        if BBOX["lat_min"] <= lat <= BBOX["lat_max"] and BBOX["lon_min"] <= lon <= BBOX["lon_max"]:
            p = f.get("properties", {})
            events.append({
                "magnitude": p.get("mag"),
                "place": p.get("place"),
                "time_utc": datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc).isoformat()
                if p.get("time") else None,
                "latitude": lat, "longitude": lon,
                "depth_km": coords[2] if len(coords) > 2 else None,
                "url": p.get("url"),
            })
    return {"status": "ok", "source": USGS_URL,
            "generated": (data.get("metadata") or {}).get("generated"),
            "total_worldwide_past_day": (data.get("metadata") or {}).get("count"),
            "events_in_corridor": events}


def fetch_gdacs():
    """GDACS RSS alerts; keep items geo-located in/near the corridor or
    mentioning the region by name. GDACS items rarely fall inside this small
    bbox, so an empty list is the NORMAL case, not an error."""
    ns = {
        "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
        "georss": "http://www.georss.org/georss",
    }
    try:
        text = fetch_text(GDACS_URL)
        root = ET.fromstring(text)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc), "source": GDACS_URL, "events": []}
    # Word-boundary matching: naive substring matching false-positives
    # (e.g. "oman" inside "Romania"). "Gulf" alone is too broad
    # (Gulf of Mexico / California) — require the full regional phrase.
    import re
    region_re = re.compile(
        r"\b(iran|oman|emirates|hormuz|pakistan|qatar|bahrain|saudi|yemen|"
        r"arabian\s+sea|gulf\s+of\s+oman|persian\s+gulf|arabian\s+gulf|"
        r"strait\s+of\s+hormuz|united\s+arab\s+emirates)\b",
        re.IGNORECASE)
    events = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        lat = item.findtext("geo:lat", namespaces=ns)
        lon = item.findtext("geo:long", namespaces=ns)
        in_bbox = False
        if lat and lon:
            try:
                in_bbox = (BBOX["lat_min"] <= float(lat) <= BBOX["lat_max"]
                           and BBOX["lon_min"] <= float(lon) <= BBOX["lon_max"])
            except ValueError:
                pass
        if in_bbox or region_re.search(title):
            events.append({"title": title, "link": link, "pub_date": pub,
                           "latitude": float(lat) if lat else None,
                           "longitude": float(lon) if lon else None})
    return {"status": "ok", "source": GDACS_URL, "events": events}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="Output JSON path (default: data/live_context.json next to system/)")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    system_dir = os.path.dirname(here)
    out_path = args.out or os.path.join(system_dir, "data", "live_context.json")

    fetched_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "data_mode": "LIVE KEYLESS CONTEXT (weather/sea + earthquakes + disaster alerts). "
                     "NO live vessel data — that needs the AISStream key.",
        "fetched_at_utc": fetched_at,
        "corridor_bbox": BBOX,
        "marine_weather": [fetch_waypoint(wp) for wp in WAYPOINTS],
        "earthquakes": fetch_quakes(),
        "gdacs_alerts": fetch_gdacs(),
        "provenance": "Each section carries its source URL. Timestamps are fetch time (UTC) "
                      "plus the source's own per-record time fields.",
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp, out_path)
    n_ok = sum(1 for w in payload["marine_weather"] if w["status"] == "ok")
    print(f"wrote {out_path}")
    print(f"fetched_at_utc={fetched_at}")
    print(f"marine waypoints ok: {n_ok}/{len(WAYPOINTS)}")
    print(f"quakes in corridor: {len(payload['earthquakes'].get('events_in_corridor', []))} "
          f"(status={payload['earthquakes']['status']})")
    print(f"GDACS region alerts: {len(payload['gdacs_alerts'].get('events', []))} "
          f"(status={payload['gdacs_alerts']['status']})")


if __name__ == "__main__":
    sys.exit(main())
