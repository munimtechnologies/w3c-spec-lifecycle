#!/usr/bin/env python3
"""W3C specification lifecycle, follow-up 1: robustness of run 1 and time in CR.

Reads the run-1 cache (w3c-versions.json, snapshot 2026-10-30) and computes the
pre-registered statistics in followups/cr-time/PREREG.md (G1-G3 and the
descriptives), writing a graded summary to <out-dir>/summary.json.

Apache-2.0. Standard library only. Reuses job.py from the repository root:
    python cr_job.py --data-dir /data --out-dir /out --allow-net
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, os.pardir, os.pardir)):
    if os.path.exists(os.path.join(_p, "job.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break
import job  # noqa: E402

RUN1_SNAPSHOT = dt.date(2026, 10, 30)
# Note-track statuses that run 1 left as OTHER; sensitivity S2 counts them as END.
NOTE_TRACK = {"draft note", "statement"}
OLD_CR = (dt.date(2011, 1, 1), dt.date(2015, 12, 31))
NEW_CR = (dt.date(2020, 9, 15), dt.date(2023, 9, 30))
HORIZON = 1096  # 3 years


def note_track_as_end(fn):
    """Run fn() with Draft Note and Statement mapped to END, then restore."""
    saved = job.END
    job.END = saved | NOTE_TRACK
    try:
        return fn()
    finally:
        job.END = saved


# ---------------------------------------------------------------- G1: CR forever

def cr_forever(recs, snapshot):
    """Run-1 P6 list, split by whether the spec ever had a REC-family version."""
    cutoff = job.add_years(snapshot, -3)
    loose = sorted(k for k, r in recs.items() if r.get("latest_family") == "CR"
                   and r.get("first_cr") is not None and r["first_cr"] <= cutoff)
    returned = [k for k in loose
                if any(f == "REC" for _, f, _, _ in recs[k]["timeline"])]
    strict = [k for k in loose if k not in set(returned)]
    return {"loose_count": len(loose), "strict_count": len(strict),
            "strict": strict, "returned_from_rec": returned}


# ---------------------------------------------------------------- G3: time in CR

def cr_outcome(tl):
    """First CR-family date, and the first REC or END on or after it."""
    c0 = next((d for d, f, _, _ in tl if f == "CR"), None)
    if c0 is None:
        return None
    hit = next(((d, f) for d, f, _, _ in tl if d >= c0 and f in ("REC", "END")), None)
    return {"c0": c0,
            "prior_rec": any(f == "REC" and d < c0 for d, f, _, _ in tl),
            "event": hit[1] if hit else None,
            "days": (hit[0] - c0).days if hit else None}


def cr_cohort(specs, lo, hi):
    rows, prior = [], 0
    for vs in specs.values():
        o = cr_outcome(job.timeline(vs))
        if o is None or not lo <= o["c0"] <= hi:
            continue
        if o["prior_rec"]:
            prior += 1
            continue
        rows.append(o)
    return rows, prior


def within(rows, event, days):
    k = sum(1 for o in rows if o["event"] == event and o["days"] <= days)
    return job._share(k, len(rows))


def cr_time(specs):
    out = {}
    for name, (lo, hi) in (("old", OLD_CR), ("new", NEW_CR)):
        rows, prior = cr_cohort(specs, lo, hi)
        b = {"window": [lo.isoformat(), hi.isoformat()], "n": len(rows),
             "excluded_prior_rec": prior,
             "rec_1y": within(rows, "REC", 365), "rec_2y": within(rows, "REC", 731),
             "rec_3y": within(rows, "REC", HORIZON), "end_3y": within(rows, "END", HORIZON)}
        if name == "old":
            b["rec_5y"] = within(rows, "REC", 1826)
        out[name] = b
    return out


def grade_g3(ct):
    o, n = ct["old"]["rec_3y"], ct["new"]["rec_3y"]
    if o is None or n is None:
        return "NULL"
    if n < o - 0.10:
        return "HELD"
    if n > o + 0.10:
        return "REVERSED"
    return "NULL"


# ---------------------------------------------------------------- descriptives

def by_t0_year(recs, last_year):
    """Cohort A entries per first-draft year and their state four years later."""
    out = {}
    for r in recs.values():
        if not r["eligible"] or not r["cohort_a"] or r["t0"].year > last_year:
            continue
        b = out.setdefault(str(r["t0"].year), {"n": 0})
        b["n"] += 1
        s = job.state_at(r, job.add_years(r["t0"], 4))
        b[s] = b.get(s, 0) + 1
    return dict(sorted(out.items()))


def cr_publications_by_year(specs):
    """CR-family publications per year by raw status (unique URIs)."""
    seen, out = set(), {}
    for vs in specs.values():
        for v in vs:
            d, u = job.parse_date(v.get("date")), v.get("uri")
            if d is None or u in seen or job.family(v.get("status")) != "CR":
                continue
            seen.add(u)
            y = out.setdefault(str(d.year), {})
            s = v.get("status")
            y[s] = y.get(s, 0) + 1
    return dict(sorted(out.items()))


def first_cr_by_year(specs):
    out = {}
    for vs in specs.values():
        o = cr_outcome(job.timeline(vs))
        if o is not None:
            y = str(o["c0"].year)
            out[y] = out.get(y, 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- main

def compute(specs, snapshot):
    kept, _, _ = job.dedup_specs(specs)
    recs, core = job.core_metrics(kept, snapshot)
    _, s2 = note_track_as_end(lambda: job.core_metrics(kept, snapshot))
    return {
        "n_specs_kept": len(kept),
        "G1": cr_forever(recs, snapshot),
        "G2": {"run1_verdicts": job.grade_core(core), "s2_verdicts": job.grade_core(s2),
               "s2_metrics": s2},
        "G3": cr_time(kept),
        "G3_s2": note_track_as_end(lambda: cr_time(kept)),
        "by_t0_year_cohort_a": by_t0_year(recs, snapshot.year - 5),
        "cr_publications_by_year": cr_publications_by_year(kept),
        "first_cr_by_year": first_cr_by_year(kept),
    }


def grade(m, snapshot):
    g = {"G1": "HELD" if m["G1"]["strict_count"] >= 40 else "FAILED"}
    changed = [k for k in ("P1", "P2", "P3")
               if m["G2"]["s2_verdicts"][k] != m["G2"]["run1_verdicts"][k]]
    g["G2"] = "FAILED" if changed else "HELD"
    g["G2_changed"] = changed
    if snapshot < NEW_CR[1] + dt.timedelta(days=HORIZON):
        g["G3"] = "NULL (follow-up too short)"
    else:
        g["G3"] = grade_g3(m["G3"])
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--allow-net", action="store_true")
    args = ap.parse_args()

    blob = job.load(args.data_dir, args.out_dir, args.allow_net)
    snapshot = job.parse_date(blob.get("downloaded")) or dt.date.today()
    metrics = compute(blob["specs"], snapshot)
    verdicts = grade(metrics, snapshot)
    summary = {
        "data_source": job.API + "/specifications",
        "snapshot_date": snapshot.isoformat(),
        "snapshot_matches_run1": snapshot == RUN1_SNAPSHOT,
        "n_listed": blob["n_listed"],
        "n_failed": len(blob["failed"]),
        "metrics": metrics,
        "verdicts": verdicts,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=job._jsonable)
    print(json.dumps({"verdicts": verdicts, "snapshot": snapshot.isoformat(),
                      "G1": {k: metrics["G1"][k] for k in ("loose_count", "strict_count")},
                      "G3": metrics["G3"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
