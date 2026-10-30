"""Self-contained tests for the W3C lifecycle verifier (no network).

A small hand-built fixture with known answers guards the metric and grading
logic in job.py. Apache-2.0.
"""
import datetime as dt
import json
import os
import tempfile
import unittest

import job

SNAP = dt.date(2026, 10, 30)


def v(date, status, uri, rt=True):
    return {"date": date, "status": status, "uri": uri, "rec-track": rt,
            "shortlink": None, "title": None}


FIXTURE = {
    # WD (rec-track false on the first version, as on css-color-3) -> CR -> REC at 1095 d.
    "s1": [v("2001-01-01", "Working Draft", "u1a", False),
           v("2003-01-01", "Candidate Recommendation Snapshot", "u1b"),
           v("2004-01-01", "Recommendation", "u1c")],
    # FPWD -> Group Note at 1247 d (END).
    "s2": [v("2005-01-01", "First Public Working Draft", "u2a"),
           v("2008-06-01", "Group Note", "u2b", False)],
    # Stale WD, censored. u3a is shared with s10.
    "s3": [v("2010-01-01", "Working Draft", "u3a"),
           v("2012-01-01", "Working Draft", "u3b")],
    # WD -> CR -> REC at 1096 d.
    "s4": [v("2011-06-01", "Working Draft", "u4a"),
           v("2013-01-01", "Candidate Recommendation Snapshot", "u4b"),
           v("2014-06-01", "Recommendation", "u4c")],
    # Living standard: CR Snapshot then CR Drafts, never REC.
    "s5": [v("2018-01-01", "First Public Working Draft", "u5a"),
           v("2020-01-01", "Candidate Recommendation Snapshot", "u5b"),
           v("2021-03-01", "Candidate Recommendation Draft", "u5c"),
           v("2022-05-01", "Candidate Recommendation Draft", "u5d")],
    # FPWD -> CRS (2021) -> REC 2022.
    "s6": [v("2019-01-01", "First Public Working Draft", "u6a"),
           v("2021-02-01", "Candidate Recommendation Snapshot", "u6b"),
           v("2022-01-01", "Recommendation", "u6c")],
    # Note-track WD: cohort B only.
    "s7": [v("2003-01-01", "Working Draft", "u7a", False),
           v("2004-01-01", "Note", "u7b", False)],
    # Enters as REC: excluded (entry_not_wd), but counts as a 1999 REC for P5.
    "s8": [v("1999-01-01", "Recommendation", "u8a", False)],
    # Subset of s5: dropped by dedup.
    "s9": [v("2018-01-01", "First Public Working Draft", "u5a"),
           v("2020-01-01", "Candidate Recommendation Snapshot", "u5b")],
    # Inherits s3's first draft, then retires at 2191 d.
    "s10": [v("2010-01-01", "Working Draft", "u3a"),
            v("2015-01-01", "Working Draft", "u10b"),
            v("2016-01-01", "Retired", "u10c", False)],
}


class TestHelpers(unittest.TestCase):
    def test_family(self):
        self.assertEqual(job.family(" Candidate Recommendation DRAFT "), "CR")
        self.assertEqual(job.family("Last Call Working Draft"), "WD")
        self.assertEqual(job.family("Retired"), "END")
        self.assertEqual(job.family("Draft Registry"), "OTHER")
        self.assertEqual(job.family(None), "OTHER")

    def test_add_years_leap(self):
        self.assertEqual(job.add_years(dt.date(2020, 2, 29), 1), dt.date(2021, 2, 28))

    def test_dedup(self):
        kept, dropped, empty = job.dedup_specs(FIXTURE)
        self.assertEqual(dropped, ["s9"])
        self.assertEqual(empty, [])
        self.assertEqual(len(kept), 9)

    def test_dedup_identical_keeps_first_name(self):
        same = {"b": [v("2001-01-01", "Working Draft", "x")],
                "a": [v("2001-01-01", "Working Draft", "x")]}
        kept, dropped, _ = job.dedup_specs(same)
        self.assertEqual(sorted(kept), ["a"])
        self.assertEqual(dropped, ["b"])

    def test_cif_ties_and_censoring(self):
        recs = [{"time_days": 10, "event": "REC"}, {"time_days": 10, "event": None},
                {"time_days": 20, "event": "END"}, {"time_days": 30, "event": "REC"}]
        out = job.cif(recs, 25)
        # t=10: 4 at risk, 1 REC -> 0.25, S=0.75; censored one leaves after.
        # t=20: 2 at risk, 1 END -> 0.375, S=0.375; t=30 beyond horizon.
        self.assertAlmostEqual(out["REC"], 0.25)
        self.assertAlmostEqual(out["END"], 0.375)


class TestCompute(unittest.TestCase):
    def setUp(self):
        self.m = job.compute(FIXTURE, SNAP)

    def test_counts(self):
        self.assertEqual(self.m["n_specs_raw"], 10)
        self.assertEqual(self.m["n_specs_kept"], 9)
        self.assertEqual(self.m["n_eligible"], 8)
        self.assertEqual(self.m["n_cohort_a"], 7)
        self.assertEqual(self.m["excluded_reasons"], {"entry_not_wd": 1})
        self.assertEqual(self.m["n_shared_uris"], 1)
        self.assertEqual(self.m["stale_censored_3y"], 2)

    def test_p1_p2_cif(self):
        # Cohort A 2000-2014: s1 REC 1095, s4 REC 1096, s2 END 1247, s10 END 2191, s3 censored.
        self.assertEqual(self.m["P1"]["n"], 5)
        self.assertAlmostEqual(self.m["P1"]["cif_rec_10y"], 0.4)
        self.assertAlmostEqual(self.m["P2"]["cif_end_10y"], 0.4)

    def test_p3_states(self):
        a = self.m["P3"]["A"]
        self.assertEqual(a["old_2010_2014"]["n"], 3)
        self.assertEqual(a["old_2010_2014"]["hist"], {"WD": 2, "REC": 1})
        self.assertEqual(a["new_2017_2021"]["hist"], {"CR": 1, "REC": 1})
        self.assertAlmostEqual(a["new_2017_2021"]["CR"], 0.5)

    def test_p4_p5_p6(self):
        self.assertEqual(self.m["P4"]["crd"], 2)
        self.assertEqual(self.m["P4"]["crs"], 1)
        self.assertEqual(self.m["P5"]["rec_by_year"],
                         {"1999": 1, "2004": 1, "2014": 1, "2022": 1})
        self.assertAlmostEqual(self.m["P5"]["mean_2015_2019"], 0.0)
        self.assertAlmostEqual(self.m["P5"]["mean_2021_2025"], 0.2)
        self.assertEqual(self.m["P6"]["sample"], ["s5"])

    def test_by_decade(self):
        d = self.m["by_decade"]
        self.assertEqual(d["2000s"]["n"], 3)
        self.assertEqual(d["2000s"]["end"], 2)
        self.assertEqual(d["2010s"]["rec"], 2)
        self.assertEqual(d["2010s"]["censored"], 2)

    def test_sensitivity_drops_shared(self):
        # Without u3a, s3 enters 2012 and s10 enters 2015 (out of the 2000-2014 cohort).
        self.assertEqual(self.m["S1"]["P1"]["n"], 4)
        self.assertAlmostEqual(self.m["S1"]["P1"]["cif_rec_10y"], 0.5)


class TestGrade(unittest.TestCase):
    def test_grades_from_fixture(self):
        g = job.grade(job.compute(FIXTURE, SNAP))
        self.assertEqual(g["P1"], "HELD")      # 0.4 < 0.50
        self.assertEqual(g["P2"], "HELD")      # 0.4 >= 0.15
        self.assertEqual(g["P3"], "FAILED")    # REC share rose, CR share rose
        self.assertEqual(g["P4"], "FAILED")    # 2:1 < 3:1
        self.assertEqual(g["P5"], "REVERSED")  # 0.2 > 1.1 x 0
        self.assertEqual(g["P6"], "FAILED")    # 1 < 40
        self.assertEqual(g["S1_agrees"], {"P1": False, "P2": True, "P3": True})


class TestLoad(unittest.TestCase):
    def test_load_from_cache(self):
        blob = {"downloaded": "2026-10-30T07:00:00Z", "n_listed": 10, "failed": [],
                "specs": FIXTURE}
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, job.CACHE_NAME), "w", encoding="utf-8") as fh:
                json.dump(blob, fh)
            got = job.load(d, d, allow_net=False)
        self.assertEqual(len(got["specs"]), 10)

    def test_missing_cache_without_net_exits(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                job.load(d, d, allow_net=False)


if __name__ == "__main__":
    unittest.main()
