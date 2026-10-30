"""Self-contained tests for the W3C follow-up (no network).

A small hand-built fixture with known answers guards G1-G3 and the
descriptives in cr_job.py. Apache-2.0.
"""
import datetime as dt
import unittest

import cr_job

job = cr_job.job
SNAP = dt.date(2026, 10, 30)


def v(date, status, uri, rt=True):
    return {"date": date, "status": status, "uri": uri, "rec-track": rt,
            "shortlink": None, "title": None}


FIXTURE = {
    # CR 2012 -> REC 517 days later (2012 is a leap year).
    "a": [v("2010-01-01", "Working Draft", "a1"),
          v("2012-01-01", "Candidate Recommendation Snapshot", "a2"),
          v("2013-06-01", "Recommendation", "a3")],
    # CR since 2014, never REC: strict CR forever.
    "b": [v("2011-01-01", "Working Draft", "b1"),
          v("2014-03-01", "Candidate Recommendation Snapshot", "b2"),
          v("2016-01-01", "Candidate Recommendation Draft", "b3"),
          v("2024-01-01", "Candidate Recommendation Draft", "b4")],
    # New-process CR, never REC.
    "c": [v("2019-01-01", "Working Draft", "c1"),
          v("2021-01-01", "Candidate Recommendation Snapshot", "c2"),
          v("2022-01-01", "Candidate Recommendation Draft", "c3")],
    # REC 579 days after CR, then back in CR (like geolocation): loose, not strict.
    "d": [v("2020-01-01", "First Public Working Draft", "d1"),
          v("2021-06-01", "Candidate Recommendation Snapshot", "d2"),
          v("2023-01-01", "Recommendation", "d3"),
          v("2025-01-01", "Candidate Recommendation Snapshot", "d4"),
          v("2026-01-01", "Candidate Recommendation Draft", "d5")],
    # CR, then a Note 365 days later (END).
    "e": [v("2018-01-01", "Working Draft", "e1"),
          v("2022-01-01", "Candidate Recommendation Snapshot", "e2"),
          v("2023-01-01", "Note", "e3", False)],
    # Draft Note 366 days after entry: OTHER in run 1, END under S2.
    "f": [v("2012-01-01", "Working Draft", "f1"),
          v("2013-01-01", "Draft Note", "f2", False)],
    # Already REC before its first CR: excluded from G3.
    "g": [v("2005-01-01", "Recommendation", "g1"),
          v("2012-06-01", "Candidate Recommendation Snapshot", "g2"),
          v("2013-01-01", "Recommendation", "g3")],
}


class TestHelpers(unittest.TestCase):
    def test_note_track_mapping_is_restored(self):
        self.assertEqual(cr_job.note_track_as_end(lambda: job.family("Draft Note")), "END")
        self.assertEqual(cr_job.note_track_as_end(lambda: job.family("Statement")), "END")
        self.assertEqual(job.family("Draft Note"), "OTHER")
        self.assertEqual(job.family("Draft Registry"), "OTHER")

    def test_cr_outcome(self):
        o = cr_job.cr_outcome(job.timeline(FIXTURE["a"]))
        self.assertEqual(o["c0"], dt.date(2012, 1, 1))
        self.assertEqual((o["event"], o["days"]), ("REC", 517))
        self.assertTrue(cr_job.cr_outcome(job.timeline(FIXTURE["g"]))["prior_rec"])
        self.assertIsNone(cr_job.cr_outcome(job.timeline(FIXTURE["f"])))


class TestCompute(unittest.TestCase):
    def setUp(self):
        self.m = cr_job.compute(FIXTURE, SNAP)

    def test_g1(self):
        g1 = self.m["G1"]
        self.assertEqual(g1["loose_count"], 3)
        self.assertEqual(g1["strict"], ["b", "c"])
        self.assertEqual(g1["returned_from_rec"], ["d"])

    def test_g2(self):
        g2 = self.m["G2"]
        self.assertEqual(g2["run1_verdicts"], {"P1": "HELD", "P2": "FAILED", "P3": "FAILED"})
        self.assertEqual(g2["s2_verdicts"], {"P1": "HELD", "P2": "HELD", "P3": "FAILED"})
        # S2: f ends at 366 d (1/3), then a reaches REC at 1247 d with 2 at risk.
        self.assertAlmostEqual(g2["s2_metrics"]["P1"]["cif_rec_10y"], 1 / 3)
        self.assertAlmostEqual(g2["s2_metrics"]["P2"]["cif_end_10y"], 1 / 3)

    def test_g3(self):
        old, new = self.m["G3"]["old"], self.m["G3"]["new"]
        self.assertEqual((old["n"], old["excluded_prior_rec"]), (2, 1))
        self.assertAlmostEqual(old["rec_1y"], 0.0)
        self.assertAlmostEqual(old["rec_2y"], 0.5)
        self.assertAlmostEqual(old["rec_3y"], 0.5)
        self.assertAlmostEqual(old["rec_5y"], 0.5)
        self.assertEqual(new["n"], 3)
        self.assertNotIn("rec_5y", new)
        self.assertAlmostEqual(new["rec_3y"], 1 / 3)
        self.assertAlmostEqual(new["end_3y"], 1 / 3)

    def test_descriptives(self):
        by = self.m["by_t0_year_cohort_a"]
        self.assertEqual(by["2012"], {"n": 1, "OTHER": 1})
        self.assertEqual(by["2018"], {"n": 1, "CR": 1})
        self.assertEqual(by["2020"], {"n": 1, "REC": 1})
        self.assertEqual(self.m["cr_publications_by_year"]["2021"],
                         {"Candidate Recommendation Snapshot": 2})
        self.assertEqual(self.m["first_cr_by_year"],
                         {"2012": 2, "2014": 1, "2021": 2, "2022": 1})


class TestGrade(unittest.TestCase):
    def test_grades_from_fixture(self):
        g = cr_job.grade(cr_job.compute(FIXTURE, SNAP), SNAP)
        self.assertEqual(g["G1"], "FAILED")    # 2 strict < 40
        self.assertEqual(g["G2"], "FAILED")    # P2 changes under S2
        self.assertEqual(g["G2_changed"], ["P2"])
        self.assertEqual(g["G3"], "HELD")      # 1/3 < 1/2 - 0.10

    def test_g3_needs_three_years(self):
        early = dt.date(2026, 1, 1)
        g = cr_job.grade(cr_job.compute(FIXTURE, early), early)
        self.assertEqual(g["G3"], "NULL (follow-up too short)")

    def test_g3_bands(self):
        def ct(o, n):
            return {"old": {"rec_3y": o}, "new": {"rec_3y": n}}
        self.assertEqual(cr_job.grade_g3(ct(0.5, 0.45)), "NULL")
        self.assertEqual(cr_job.grade_g3(ct(0.3, 0.45)), "REVERSED")
        self.assertEqual(cr_job.grade_g3(ct(None, 0.45)), "NULL")


if __name__ == "__main__":
    unittest.main()
