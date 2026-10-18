#!/usr/bin/env python3
"""AIS-gap + STS-candidate detector (pure stdlib).

Reads the raw AIS message log written by pipeline/aisstream_client.py
(data/ais_raw.jsonl) and emits candidate events. NOT a sanctions finder:
every output is labelled "candidate — requires human review" and no vessel
is ever labelled "sanctioned".

Detection rules (defaults; all tunable via CLI flags):
  GAP — one vessel's consecutive position reports inside the corridor are
        separated by more than GAP_MIN_HOURS. A long silence inside a busy
        corridor is consistent with AIS switched off, receiver gaps, or
        spoofing — the event says "AIS gap", never "went dark to evade".
  STS CANDIDATE — two vessels stay within STS_MAX_DIST_NM of each other,
        both at or below STS_MAX_SOG_KT, continuously for at least
        STS_MIN_DURATION_MIN. That geometry is consistent with a
        ship-to-ship transfer, a joint anchorage, bunkering, or a
        coincidence — the event says "STS candidate, matches pattern X".

Every output event carries: detection parameters, source file, message
counts, and a UTC generation timestamp (provenance / audit trail).

Usage:
    python3 pipeline/detect.py --messages data/ais_raw.jsonl --out data/detected_events.json
    python3 pipeline/detect.py --messages data/ais_raw.jsonl --gap-hours 24 --sts-min-minutes 60
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

CORRIDOR = {"lat_min": 25.0, "lat_max": 27.5, "lon_min": 55.0, "lon_max": 59.5}

DEFAULTS = {
    "gap_min_hours": 6.0,
    "sts_max_dist_nm": 0.5,
    "sts_max_sog_kt": 2.0,
    "sts_min_duration_min": 30.0,
    "sts_pair_window_min": 15.0,
    # Feed-aware bridging: global feed outages (nobody reporting) up to
    # feed_bridge_max_min may be spanned by an STS run; longer silences
    # break runs. Quiet intervals longer than feed_quiet_from_min are
    # logged in the payload for audit.
    "feed_bridge_max_min": 45.0,
    "feed_quiet_from_min": 5.0,
}


def haversine_nm(lat1, lon1, lat2, lon2):
    r = math.radians
    dlat = r(lat2 - lat1)
    dlon = r(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(dlon / 2) ** 2
    return 3440.065 * 2 * math.asin(min(1.0, math.sqrt(a)))


def in_corridor(lat, lon):
    return (CORRIDOR["lat_min"] <= lat <= CORRIDOR["lat_max"]
            and CORRIDOR["lon_min"] <= lon <= CORRIDOR["lon_max"])


def parse_time(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_report(envelope):
    """Normalise one AISStream envelope to a position report dict or None."""
    meta = envelope.get("MetaData") or {}
    msg = envelope.get("Message") or {}
    pr = None
    for key in ("PositionReport", "StandardClassBPositionReport",
                "ExtendedClassBPositionReport"):
        if key in msg and isinstance(msg[key], dict):
            pr = msg[key]
            break
    if pr is None:
        return None
    try:
        lat, lon = float(pr["Latitude"]), float(pr["Longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    ts = parse_time(meta.get("time_utc")) or parse_time(pr.get("Timestamp"))
    if ts is None:
        return None
    try:
        sog = float(pr.get("Sog")) if pr.get("Sog") is not None else None
    except (TypeError, ValueError):
        sog = None
    return {"mmsi": str(meta.get("MMSI", "")),
            "ship_name": meta.get("ShipName"),
            "time": ts, "lat": lat, "lon": lon, "sog": sog}


def load_tracks(path):
    """Return {mmsi: [sorted reports]}, plus message counters."""
    tracks = {}
    total = kept = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            total += 1
            line = line.strip()
            if not line:
                continue
            try:
                rep = extract_report(json.loads(line))
            except json.JSONDecodeError:
                continue
            if rep is None or not rep["mmsi"]:
                continue
            kept += 1
            tracks.setdefault(rep["mmsi"], []).append(rep)
    for mmsi in tracks:
        tracks[mmsi].sort(key=lambda r: r["time"])
    return tracks, total, kept


def find_gaps(tracks, gap_min_hours):
    events = []
    for mmsi, reps in tracks.items():
        for a, b in zip(reps, reps[1:]):
            gap_h = (b["time"] - a["time"]).total_seconds() / 3600.0
            if gap_h >= gap_min_hours and in_corridor(a["lat"], a["lon"]):
                events.append({
                    "event_type": "ais_gap_event",
                    "classification": "AIS-gap event — requires human review. "
                                      "Consistent with AIS off, receiver gap, or spoofing. "
                                      "NOT proof of wrongdoing.",
                    "mmsi": mmsi,
                    "ship_name": a.get("ship_name"),
                    "gap_start_utc": a["time"].isoformat(),
                    "gap_end_utc": b["time"].isoformat(),
                    "gap_hours": round(gap_h, 2),
                    "last_lat": a["lat"], "last_lon": a["lon"],
                    "reappearance_lat": b["lat"], "reappearance_lon": b["lon"],
                    "confidence": "candidate",
                })
    return sorted(events, key=lambda e: e["gap_start_utc"])


def find_feed_quiet_intervals(tracks, quiet_from_min, bridge_max_min):
    """Global feed-quiet intervals: spans where NO vessel reported at all.

    A quiet interval opens when consecutive feed-wide reports are more than
    quiet_from_min apart. Intervals up to bridge_max_min long are marked
    'bridged' — short feed outages that STS run continuity may span.
    Longer silences are not bridged: runs break there, and the silence
    itself may be worth alerting on.
    """
    times = sorted(r["time"] for reps in tracks.values() for r in reps)
    intervals = []
    for a, b in zip(times, times[1:]):
        mins = (b - a).total_seconds() / 60.0
        if mins > quiet_from_min:
            intervals.append({
                "quiet_start_utc": a.isoformat(),
                "quiet_end_utc": b.isoformat(),
                "quiet_min": round(mins, 1),
                "bridged": mins <= bridge_max_min,
            })
    return intervals


def _bridged_gap_minutes(gap_start, gap_end, quiet_intervals):
    """Minutes of the [gap_start, gap_end] sample-gap explained by bridged
    feed-quiet intervals. Only the whole gap counts: a gap is bridged when
    bridged quiet intervals cover it near-entirely (1-minute tolerance).
    Partial coverage or a non-bridged (long) interval means the run breaks.
    """
    total = (gap_end - gap_start).total_seconds() / 60.0
    if total <= 0:
        return 0.0
    covered = 0.0
    for qi in quiet_intervals:
        if not qi["bridged"]:
            continue
        qs = datetime.fromisoformat(qi["quiet_start_utc"])
        qe = datetime.fromisoformat(qi["quiet_end_utc"])
        lo, hi = max(gap_start, qs), min(gap_end, qe)
        if hi > lo:
            covered += (hi - lo).total_seconds() / 60.0
    return covered if covered >= total - 1.0 else 0.0


def _close_pairs(rep_a, rep_b, max_dist_nm, max_sog, window_min):
    """Yield (time, dist_nm) samples where two tracks are close, slow, and
    near-simultaneous. Two-pointer merge over sorted tracks."""
    i = j = 0
    a, b = rep_a, rep_b
    while i < len(a) and j < len(b):
        dt_min = abs((a[i]["time"] - b[j]["time"]).total_seconds()) / 60.0
        if dt_min <= window_min:
            dist = haversine_nm(a[i]["lat"], a[i]["lon"], b[j]["lat"], b[j]["lon"])
            sog_a = a[i]["sog"] if a[i]["sog"] is not None else 999.0
            sog_b = b[j]["sog"] if b[j]["sog"] is not None else 999.0
            if dist <= max_dist_nm and sog_a <= max_sog and sog_b <= max_sog:
                yield (max(a[i]["time"], b[j]["time"]), dist,
                       (a[i]["lat"] + b[j]["lat"]) / 2.0,
                       (a[i]["lon"] + b[j]["lon"]) / 2.0)
            # Advance the earlier report.
            if a[i]["time"] <= b[j]["time"]:
                i += 1
            else:
                j += 1
        elif a[i]["time"] < b[j]["time"]:
            i += 1
        else:
            j += 1


def find_sts_candidates(tracks, params, quiet_intervals=None):
    """STS candidates with feed-aware run continuity.

    Close-pair sample runs break when samples are >2x the pair window
    apart — unless the sample gap is explained by a bridged feed-quiet
    interval (a short global feed outage, not a vessel going quiet while
    the feed was alive). Bridged runs keep their window open across the
    outage and record how many quiet minutes they spanned.
    """
    quiet_intervals = quiet_intervals or []
    events = []
    mmsis = sorted(tracks)
    for x in range(len(mmsis)):
        for y in range(x + 1, len(mmsis)):
            m1, m2 = mmsis[x], mmsis[y]
            run_start = run_end = None
            run_min_dist = None
            run_mid = (None, None)
            run_bridged_min = 0.0
            last_t = None
            samples = list(_close_pairs(
                tracks[m1], tracks[m2],
                params["sts_max_dist_nm"], params["sts_max_sog_kt"],
                params["sts_pair_window_min"]))
            for t, dist, mlat, mlon in samples:
                if run_start is None:
                    run_start = run_end = t
                    run_min_dist = dist
                    run_mid = (mlat, mlon)
                elif (t - last_t).total_seconds() / 60.0 <= params["sts_pair_window_min"] * 2:
                    run_end = t
                    run_min_dist = min(run_min_dist, dist)
                    run_mid = (mlat, mlon)
                else:
                    bridged = _bridged_gap_minutes(last_t, t, quiet_intervals)
                    if bridged > 0:
                        # Feed was quiet for everyone during this gap: keep
                        # the run open across the short outage instead of
                        # splitting it.
                        run_bridged_min += bridged
                        run_end = t
                        run_min_dist = min(run_min_dist, dist)
                        run_mid = (mlat, mlon)
                    else:
                        if (run_end - run_start).total_seconds() / 60.0 >= params["sts_min_duration_min"]:
                            events.append(_sts_event(m1, m2, tracks, run_start, run_end, run_min_dist, run_mid, run_bridged_min))
                        run_start = run_end = t
                        run_min_dist = dist
                        run_mid = (mlat, mlon)
                        run_bridged_min = 0.0
                last_t = t
            if run_start is not None and (run_end - run_start).total_seconds() / 60.0 >= params["sts_min_duration_min"]:
                events.append(_sts_event(m1, m2, tracks, run_start, run_end, run_min_dist, run_mid, run_bridged_min))
    return sorted(events, key=lambda e: e["window_start_utc"])


def _sts_event(m1, m2, tracks, start, end, min_dist, mid, bridged_min=0.0):
    names = []
    for m in (m1, m2):
        nm = next((r.get("ship_name") for r in tracks[m] if r.get("ship_name")), None)
        names.append(nm)
    return {
        "event_type": "sts_candidate",
        "classification": "STS candidate — matches pattern: two vessels close together, "
                          "both near-stationary, for an extended window. Also consistent "
                          "with joint anchorage / bunkering / coincidence. NOT proof of a "
                          "transfer and NOT a sanctions finding.",
        "mmsi_a": m1, "ship_name_a": names[0],
        "mmsi_b": m2, "ship_name_b": names[1],
        "window_start_utc": start.isoformat(),
        "window_end_utc": end.isoformat(),
        "duration_min": round((end - start).total_seconds() / 60.0, 1),
        "min_distance_nm": round(min_dist, 3),
        "approx_lat": mid[0], "approx_lon": mid[1],
        # Minutes of this window that span bridged feed outages (feed quiet
        # for everyone, not the vessels going quiet). 0.0 when unbridged.
        "bridged_feed_quiet_min": round(bridged_min, 1),
        "confidence": "candidate",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--messages", required=True, help="AIS raw JSONL log (ais_raw.jsonl).")
    ap.add_argument("--out", default=None, help="Output JSON path.")
    ap.add_argument("--gap-hours", type=float, default=DEFAULTS["gap_min_hours"])
    ap.add_argument("--sts-max-dist-nm", type=float, default=DEFAULTS["sts_max_dist_nm"])
    ap.add_argument("--sts-max-sog", type=float, default=DEFAULTS["sts_max_sog_kt"])
    ap.add_argument("--sts-min-minutes", type=float, default=DEFAULTS["sts_min_duration_min"])
    ap.add_argument("--feed-bridge-max-min", type=float, default=DEFAULTS["feed_bridge_max_min"],
                    help="Bridge STS runs across global feed outages up to this long (minutes).")
    args = ap.parse_args()

    params = {"gap_min_hours": args.gap_hours,
              "sts_max_dist_nm": args.sts_max_dist_nm,
              "sts_max_sog_kt": args.sts_max_sog,
              "sts_min_duration_min": args.sts_min_minutes,
              "sts_pair_window_min": DEFAULTS["sts_pair_window_min"],
              "feed_bridge_max_min": args.feed_bridge_max_min,
              "feed_quiet_from_min": DEFAULTS["feed_quiet_from_min"]}

    if not os.path.exists(args.messages):
        print(f"ERROR: no message log at {args.messages}", file=sys.stderr)
        print("Run pipeline/aisstream_client.py first (needs AISSTREAM_API_KEY).", file=sys.stderr)
        return 2

    tracks, total, kept = load_tracks(args.messages)
    gaps = find_gaps(tracks, params["gap_min_hours"])
    quiet = find_feed_quiet_intervals(tracks, params["feed_quiet_from_min"], params["feed_bridge_max_min"])
    sts = find_sts_candidates(tracks, params, quiet)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": os.path.abspath(args.messages),
        "messages_read": total,
        "position_reports_kept": kept,
        "vessels_seen": len(tracks),
        "detector_params": params,
        "corridor": CORRIDOR,
        "provenance": "Candidate events only. Each event is derived from the source "
                      "message log; no vessel is labelled sanctioned.",
        "feed_quiet_intervals": quiet,
        "gap_events": gaps,
        "sts_candidates": sts,
    }
    out = args.out or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "data", "detected_events.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp, out)
    print(f"wrote {out}")
    print(f"messages={total} position_reports={kept} vessels={len(tracks)} "
          f"gap_events={len(gaps)} sts_candidates={len(sts)} "
          f"feed_quiet_intervals={len(quiet)} "
          f"(bridged={sum(1 for q in quiet if q['bridged'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
