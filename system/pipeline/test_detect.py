#!/usr/bin/env python3
"""Unit tests for pipeline/detect.py.

ALL FIXTURES HERE ARE SYNTHETIC — invented MMSI numbers, positions, and
timestamps created inside this test file purely to verify detector logic.
They are NEVER written to data/, NEVER shown in the demo UI, and must never
be presented as real vessel events.
"""

import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from detect import find_gaps, find_sts_candidates, find_feed_quiet_intervals, haversine_nm, DEFAULTS  # noqa: E402

T0 = datetime(2026, 10, 13, 0, 0, tzinfo=timezone.utc)


def rep(mmsi, minutes, lat, lon, sog, name=None):
    return {"mmsi": mmsi, "ship_name": name, "time": T0 + timedelta(minutes=minutes),
            "lat": lat, "lon": lon, "sog": sog}


def every(minutes_list, mmsi, lat, lon, sog, name=None):
    return [rep(mmsi, m, lat, lon, sog, name) for m in minutes_list]


class TestHaversine(unittest.TestCase):
    def test_known_distance(self):
        # ~1 degree of latitude ≈ 60 NM.
        d = haversine_nm(26.0, 56.0, 27.0, 56.0)
        self.assertAlmostEqual(d, 60.0, delta=0.5)

    def test_zero(self):
        self.assertAlmostEqual(haversine_nm(26.0, 56.0, 26.0, 56.0), 0.0)


class TestGapDetection(unittest.TestCase):
    def test_gap_inside_corridor_flagged(self):
        tracks = {"111111111": [rep("111111111", 0, 26.5, 56.5, 10.0),
                                rep("111111111", 60 * 8, 26.6, 56.6, 10.0)]}
        gaps = find_gaps(tracks, gap_min_hours=6.0)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["gap_hours"], 8.0)
        self.assertEqual(gaps[0]["mmsi"], "111111111")

    def test_short_gap_not_flagged(self):
        tracks = {"111111111": [rep("111111111", 0, 26.5, 56.5, 10.0),
                                rep("111111111", 60 * 2, 26.6, 56.6, 10.0)]}
        self.assertEqual(find_gaps(tracks, gap_min_hours=6.0), [])

    def test_gap_outside_corridor_not_flagged(self):
        # Last report far outside the Hormuz corridor (mid-Atlantic).
        tracks = {"111111111": [rep("111111111", 0, 30.0, -40.0, 10.0),
                                rep("111111111", 60 * 8, 30.1, -40.0, 10.0)]}
        self.assertEqual(find_gaps(tracks, gap_min_hours=6.0), [])


class TestStsDetection(unittest.TestCase):
    def test_stationary_pair_flagged(self):
        # Two synthetic vessels ~0.2 NM apart, both at 0.5 kt, for 45 minutes.
        mins = list(range(0, 46, 5))
        tracks = {
            "222222222": every(mins, "222222222", 26.50, 56.50, 0.5, "SYNTH-A"),
            "333333333": every(mins, "333333333", 26.503, 56.50, 0.5, "SYNTH-B"),
        }
        cands = find_sts_candidates(tracks, dict(DEFAULTS))
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["mmsi_a"], "222222222")
        self.assertEqual(cands[0]["mmsi_b"], "333333333")
        self.assertGreaterEqual(cands[0]["duration_min"], 30.0)

    def test_passing_vessels_not_flagged(self):
        # Two fast vessels crossing: same area, both at 12 kt — not an STS pattern.
        mins = list(range(0, 46, 5))
        tracks = {
            "444444444": every(mins, "444444444", 26.50, 56.50, 12.0, "SYNTH-C"),
            "555555555": every(mins, "555555555", 26.503, 56.50, 12.0, "SYNTH-D"),
        }
        self.assertEqual(find_sts_candidates(tracks, dict(DEFAULTS)), [])

    def test_brief_encounter_not_flagged(self):
        # Close + slow, but only 10 minutes — below the 30-minute threshold.
        mins = list(range(0, 11, 5))
        tracks = {
            "666666666": every(mins, "666666666", 26.50, 56.50, 0.5, "SYNTH-E"),
            "777777777": every(mins, "777777777", 26.503, 56.50, 0.5, "SYNTH-F"),
        }
        self.assertEqual(find_sts_candidates(tracks, dict(DEFAULTS)), [])

    def test_distant_pair_not_flagged(self):
        # Both slow, but ~6 NM apart — far beyond the 0.5 NM STS radius.
        mins = list(range(0, 46, 5))
        tracks = {
            "888888888": every(mins, "888888888", 26.50, 56.50, 0.5, "SYNTH-G"),
            "999999999": every(mins, "999999999", 26.60, 56.50, 0.5, "SYNTH-H"),
        }
        self.assertEqual(find_sts_candidates(tracks, dict(DEFAULTS)), [])


class TestFeedQuietBridging(unittest.TestCase):
    def _pair(self, minutes, extra_tracks=None):
        # Two synthetic vessels ~0.2 NM apart, both at 0.5 kt.
        tracks = {
            "101010101": every(minutes, "101010101", 26.50, 56.50, 0.5, "SYNTH-Q1"),
            "202020202": every(minutes, "202020202", 26.503, 56.50, 0.5, "SYNTH-Q2"),
        }
        if extra_tracks:
            tracks.update(extra_tracks)
        return tracks

    def test_quiet_intervals_flagged(self):
        mins = list(range(0, 26, 5)) + list(range(61, 87, 5))
        quiet = find_feed_quiet_intervals(
            self._pair(mins), quiet_from_min=5.0, bridge_max_min=45.0)
        self.assertEqual(len(quiet), 1)
        self.assertAlmostEqual(quiet[0]["quiet_min"], 35.0, delta=0.1)
        self.assertTrue(quiet[0]["bridged"])

    def test_long_quiet_interval_not_bridged(self):
        mins = list(range(0, 26, 5)) + list(range(91, 117, 5))
        quiet = find_feed_quiet_intervals(
            self._pair(mins), quiet_from_min=5.0, bridge_max_min=45.0)
        self.assertEqual(len(quiet), 1)
        self.assertFalse(quiet[0]["bridged"])

    def test_short_outage_bridges_run(self):
        # 35-minute global feed outage mid-run: one candidate, bridged.
        mins = list(range(0, 26, 5)) + list(range(61, 87, 5))
        tracks = self._pair(mins)
        quiet = find_feed_quiet_intervals(tracks, 5.0, 45.0)
        cands = find_sts_candidates(tracks, dict(DEFAULTS), quiet)
        self.assertEqual(len(cands), 1)
        self.assertAlmostEqual(cands[0]["bridged_feed_quiet_min"], 35.0, delta=1.0)
        self.assertGreaterEqual(cands[0]["duration_min"], 60.0)

    def test_long_outage_breaks_run(self):
        # 65-minute global outage: too long to bridge — two separate runs.
        mins = list(range(0, 36, 5)) + list(range(101, 137, 5))
        tracks = self._pair(mins)
        quiet = find_feed_quiet_intervals(tracks, 5.0, 45.0)
        cands = find_sts_candidates(tracks, dict(DEFAULTS), quiet)
        self.assertEqual(len(cands), 2)
        self.assertTrue(all(c["bridged_feed_quiet_min"] == 0.0 for c in cands))

    def test_pair_gap_with_live_feed_not_bridged(self):
        # The pair goes quiet for 35 minutes but a third vessel keeps
        # reporting (feed alive): the gap is real, the run breaks.
        pair_mins = list(range(0, 36, 5)) + list(range(71, 107, 5))
        live_mins = list(range(0, 108, 5))
        tracks = self._pair(
            pair_mins,
            {"303030303": every(live_mins, "303030303", 26.80, 56.80, 10.0, "SYNTH-Q3")})
        quiet = find_feed_quiet_intervals(tracks, 5.0, 45.0)
        self.assertEqual(quiet, [])
        cands = find_sts_candidates(tracks, dict(DEFAULTS), quiet)
        pair_cands = [c for c in cands
                      if {c["mmsi_a"], c["mmsi_b"]} == {"101010101", "202020202"}]
        self.assertEqual(len(pair_cands), 2)

    def test_unbridged_event_has_zero_bridged_minutes(self):
        mins = list(range(0, 46, 5))
        tracks = self._pair(mins)
        cands = find_sts_candidates(tracks, dict(DEFAULTS), [])
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["bridged_feed_quiet_min"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
