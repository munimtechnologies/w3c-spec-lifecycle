#!/usr/bin/env python3
"""W3C specification lifecycle: grade the pre-registration against api.w3.org.

Downloads every specification's version history from the public W3C API (no
key), caches it as one compact JSON, and computes the pre-registered
statistics in PREREG.md (P1-P6), writing a graded summary to
<out-dir>/summary.json.

Apache-2.0. Standard library only. Designed to run once in a sealed container:
    python job.py --data-dir /data --out-dir /out --allow-net
If <data-dir>/w3c-versions.json exists it is reused and nothing is downloaded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import time
import urllib.error
import urllib.request

API = "https://api.w3.org"
CACHE_NAME = "w3c-versions.json"
UA = "mv2-munim-research/1.0 (MV2, Munim, Inc., mv2@munimtech.com)"

WD = {"first public working draft", "working draft", "last call working draft"}
CR = {"candidate recommendation", "candidate recommendation snapshot",
      "candidate recommendation draft"}
PR = {"proposed recommendation", "proposed edited recommendation"}
REC = {"recommendation", "edited recommendation", "amended recommendation"}
END = {"note", "group note", "working group note", "interest group note",
       "retired", "discontinued draft"}

# Specs named for the live spot-check recorded in the summary.
SPOTCHECK = ["css-color-3", "webdatabase", "user-timing", "webgpu", "html5", "WCAG21"]

KEEP = ("date", "status", "rec-track", "uri", "shortlink", "title")


def family(status):
    s = (status or "").strip().lower()
    for name, group in (("WD", WD), ("CR", CR), ("PR", PR), ("REC", REC), ("END", END)):
        if s in group:
            return name
    return "OTHER"


def parse_date(value):
    try:
        return dt.date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February
        return d.replace(year=d.year + years, day=28)


def _share(num, den):
    return (num / den) if den else None


# ---------------------------------------------------------------- dataset prep

def dedup_specs(specs):
    """Drop specs whose version-URI set is a subset of another spec's set."""
    sets = {k: frozenset(v["uri"] for v in vs if v.get("uri")) for k, vs in specs.items()}
    keys = sorted(sets)
    dropped = []
    for a in keys:
        for b in keys:
            if a == b or not sets[a]:
                continue
            if sets[a] < sets[b] or (sets[a] == sets[b] and b < a):
                dropped.append(a)
                break
    kept = {k: v for k, v in specs.items() if k not in set(dropped)}
    empty = [k for k in kept if not sets[k]]
    for k in empty:
        kept.pop(k)
    return kept, sorted(dropped), sorted(empty)


def shared_uris(specs):
    count = {}
    for vs in specs.values():
        for u in {v["uri"] for v in vs if v.get("uri")}:
            count[u] = count.get(u, 0) + 1
    return {u for u, c in count.items() if c > 1}


def drop_shared(specs):
    shared = shared_uris(specs)
    return {k: [v for v in vs if v.get("uri") not in shared] for k, vs in specs.items()}


def timeline(versions):
    """Sorted, URI-deduped list of (date, family, raw_status, rec_track)."""
    seen = set()
    out = []
    for v in versions:
        d = parse_date(v.get("date"))
        u = v.get("uri")
        if d is None or u in seen:
            continue
        seen.add(u)
        out.append((d, family(v.get("status")), v.get("status") or "",
                    bool(v.get("rec-track"))))
    out.sort(key=lambda r: r[0])
    return out


def classify(versions, snapshot):
    """Per-spec record used by every metric."""
    tl = timeline(versions)
    rec = {"n_versions": len(tl), "eligible": False, "reason": None}
    if not tl:
        rec["reason"] = "no_dated_versions"
        return rec
    t0 = None
    for d, fam, _, _ in tl:
        if fam == "WD":
            t0 = d
            break
        if fam in ("CR", "PR", "REC", "END"):
            break
    if t0 is None:
        rec["reason"] = "entry_not_wd"
    rec_date = next((d for d, f, _, _ in tl if f == "REC" and (t0 is None or d >= t0)), None)
    first_cr = next((d for d, f, _, _ in tl if f == "CR"), None)
    rec.update({
        "t0": t0,
        "first_rec": rec_date,
        "first_cr": first_cr,
        "latest_family": tl[-1][1],
        "latest_date": tl[-1][0],
        "any_rec_track": any(r for _, _, _, r in tl),
        "any_cr_pr_rec": any(f in ("CR", "PR", "REC") for _, f, _, _ in tl),
        "timeline": tl,
    })
    if t0 is None:
        return rec
    end_date = next((d for d, f, _, _ in tl if f == "END" and d >= t0
                     and (rec_date is None or d < rec_date)), None)
    if end_date is not None:
        event, when = "END", end_date
    elif rec_date is not None:
        event, when = "REC", rec_date
    else:
        event, when = None, snapshot
    rec.update({"eligible": True, "event": event,
                "time_days": (when - t0).days, "cohort_a": rec["any_rec_track"] or rec["any_cr_pr_rec"]})
    return rec


def state_at(rec, when):
    if rec["event"] is not None and t_event(rec) <= when:
        return rec["event"]
    fam = "NONE"
    for d, f, _, _ in rec["timeline"]:
        if d > when:
            break
        fam = f
    return fam


def t_event(rec):
    return rec["t0"] + dt.timedelta(days=rec["time_days"])


# ---------------------------------------------------------------- statistics

def cif(records, horizon_days):
    """Aalen-Johansen cumulative incidence of REC and END at horizon_days."""
    pts = sorted((r["time_days"], r["event"] or "") for r in records)
    n = len(pts)
    surv = 1.0
    out = {"REC": 0.0, "END": 0.0}
    i = 0
    while i < n:
        t = pts[i][0]
        if t > horizon_days:
            break
        j = i
        d = {"REC": 0, "END": 0}
        while j < n and pts[j][0] == t:
            if pts[j][1] in d:
                d[pts[j][1]] += 1
            j += 1
        at_risk = n - i
        for k in d:
            out[k] += surv * d[k] / at_risk
        surv *= 1 - (d["REC"] + d["END"]) / at_risk
        i = j
    out["n"] = n
    return out


def cohort(recs, lo, hi, which):
    return [r for r in recs if r["eligible"] and lo <= r["t0"].year <= hi
            and (which == "B" or r["cohort_a"])]


def state_shares(recs):
    hist = {}
    for r in recs:
        s = state_at(r, add_years(r["t0"], 4))
        hist[s] = hist.get(s, 0) + 1
    n = len(recs)
    return {"n": n, "hist": hist,
            "REC": _share(hist.get("REC", 0), n), "CR": _share(hist.get("CR", 0), n)}


def core_metrics(specs, snapshot):
    recs = {k: classify(vs, snapshot) for k, vs in specs.items()}
    vals = list(recs.values())
    a_old = cohort(vals, 2000, 2014, "A")
    p12 = cif(a_old, int(10 * 365.25))
    p3 = {}
    for which in ("A", "B"):
        p3[which] = {"old_2010_2014": state_shares(cohort(vals, 2010, 2014, which)),
                     "new_2017_2021": state_shares(cohort(vals, 2017, 2021, which))}
    return recs, {"P1": {"cif_rec_10y": p12["REC"], "n": p12["n"]},
                  "P2": {"cif_end_10y": p12["END"], "n": p12["n"]},
                  "P3": p3}


def compute(specs, snapshot):
    """specs: {shortname: [version dicts]}. snapshot: date. Returns metrics dict."""
    status_hist = {}
    n_versions_raw = 0
    for vs in specs.values():
        for v in vs:
            n_versions_raw += 1
            s = v.get("status") or ""
            status_hist[s] = status_hist.get(s, 0) + 1

    kept, dropped, empty = dedup_specs(specs)
    recs, core = core_metrics(kept, snapshot)
    vals = list(recs.values())
    eligible = [r for r in vals if r["eligible"]]

    # P4: CR-family publications from 2021 on, unique URIs across kept specs.
    crd = crs = cr_other = 0
    seen = set()
    for vs in kept.values():
        for v in vs:
            d = parse_date(v.get("date"))
            u = v.get("uri")
            if d is None or u in seen or d < dt.date(2021, 1, 1):
                continue
            seen.add(u)
            s = (v.get("status") or "").strip().lower()
            if s == "candidate recommendation draft":
                crd += 1
            elif s == "candidate recommendation snapshot":
                crs += 1
            elif s in CR:
                cr_other += 1

    # P5: first REC-family date per kept spec (any entry), counted by year.
    rec_years = {}
    for r in vals:
        if r.get("first_rec") is not None:
            y = r["first_rec"].year
            rec_years[y] = rec_years.get(y, 0) + 1
    early = statistics.mean(rec_years.get(y, 0) for y in range(2015, 2020))
    late = statistics.mean(rec_years.get(y, 0) for y in range(2021, 2026))

    # P6: CR forever.
    cutoff = add_years(snapshot, -3)
    cr_forever = sorted(k for k, r in recs.items() if r.get("latest_family") == "CR"
                        and r.get("first_cr") is not None and r["first_cr"] <= cutoff)

    # Descriptives.
    reasons = {}
    for r in vals:
        if not r["eligible"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    by_decade = {}
    for r in eligible:
        dec = "%ds" % (r["t0"].year // 10 * 10)
        b = by_decade.setdefault(dec, {"n": 0, "cohort_a": 0, "rec": 0, "end": 0,
                                       "censored": 0, "rec_years": []})
        b["n"] += 1
        b["cohort_a"] += int(r["cohort_a"])
        if r["event"] == "REC":
            b["rec"] += 1
            b["rec_years"].append(r["time_days"] / 365.25)
        elif r["event"] == "END":
            b["end"] += 1
        else:
            b["censored"] += 1
    for b in by_decade.values():
        yrs = b.pop("rec_years")
        b["median_years_to_rec"] = statistics.median(yrs) if yrs else None
    stale = sum(1 for r in eligible if r["event"] is None
                and (snapshot - r["latest_date"]).days > int(3 * 365.25))
    first_rt = {}
    for r in eligible:
        dec = "%ds" % (r["t0"].year // 10 * 10)
        first_flag = r["timeline"][0][3]
        f = first_rt.setdefault(dec, {"first_version_rec_track_true": 0, "n": 0})
        f["n"] += 1
        f["first_version_rec_track_true"] += int(first_flag)

    # S1: drop shared URIs, recompute P1-P3.
    shared = shared_uris(kept)
    _, s1 = core_metrics(drop_shared(kept), snapshot)

    return {
        "n_specs_raw": len(specs),
        "n_versions_raw": n_versions_raw,
        "n_specs_dropped_subset": len(dropped),
        "dropped_subset_sample": dropped[:25],
        "n_specs_empty": len(empty),
        "n_specs_kept": len(kept),
        "n_eligible": len(eligible),
        "n_cohort_a": sum(1 for r in eligible if r["cohort_a"]),
        "excluded_reasons": reasons,
        "status_hist": status_hist,
        "by_decade": by_decade,
        "first_version_rec_track_by_decade": first_rt,
        "stale_censored_3y": stale,
        "n_shared_uris": len(shared),
        "P1": core["P1"],
        "P2": core["P2"],
        "P3": core["P3"],
        "P4": {"crd": crd, "crs": crs, "cr_other": cr_other,
               "ratio": (crd / crs) if crs else None},
        "P5": {"rec_by_year": {str(k): rec_years[k] for k in sorted(rec_years)},
               "mean_2015_2019": early, "mean_2021_2025": late},
        "P6": {"count": len(cr_forever), "sample": cr_forever[:40]},
        "S1": s1,
    }


def _grade_p3(p3):
    held = rev = True
    for which in ("A", "B"):
        old, new = p3[which]["old_2010_2014"], p3[which]["new_2017_2021"]
        if None in (old["REC"], new["REC"], old["CR"], new["CR"]):
            return "NULL"
        rec_d = new["REC"] - old["REC"]
        cr_d = new["CR"] - old["CR"]
        held = held and rec_d < -0.05 and cr_d > 0.05
        rev = rev and rec_d > 0.05 and cr_d < -0.05
    return "HELD" if held else ("REVERSED" if rev else "FAILED")


def grade_core(m):
    g = {}
    a = m["P1"]["cif_rec_10y"]
    g["P1"] = "NULL" if not m["P1"]["n"] else ("HELD" if a < 0.50 else "FAILED")
    b = m["P2"]["cif_end_10y"]
    g["P2"] = "NULL" if not m["P2"]["n"] else ("HELD" if b >= 0.15 else "FAILED")
    g["P3"] = _grade_p3(m["P3"])
    return g


def grade(m):
    """Apply the prereg decision rules; return {claim: verdict}."""
    g = grade_core(m)
    r = m["P4"]["ratio"]
    if r is None:
        g["P4"] = "HELD" if m["P4"]["crd"] > 0 else "NULL"
    else:
        g["P4"] = "HELD" if r >= 3 else "FAILED"
    e, l = m["P5"]["mean_2015_2019"], m["P5"]["mean_2021_2025"]
    if l < 0.9 * e:
        g["P5"] = "HELD"
    elif l > 1.1 * e:
        g["P5"] = "REVERSED"
    else:
        g["P5"] = "NULL"
    g["P6"] = "HELD" if m["P6"]["count"] >= 40 else "FAILED"
    s1 = grade_core(m["S1"])
    g["S1_agrees"] = {k: s1[k] == g[k] for k in ("P1", "P2", "P3")}
    return g


# ---------------------------------------------------------------- download

def get_json(url, tries=5):
    delay = 2.0
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if attempt == tries - 1:
                raise
        except (OSError, ValueError):  # URLError, resets, timeouts, bad JSON
            if attempt == tries - 1:
                raise
        time.sleep(delay)
        delay *= 2
    return None


def download(pause=0.25):
    names = []
    page = 1
    while True:
        data = get_json("%s/specifications?items=1000&page=%d" % (API, page))
        for s in data["_links"]["specifications"]:
            names.append(s["href"].rstrip("/").rsplit("/", 1)[-1])
        if page >= int(data.get("pages", 1)):
            break
        page += 1
        time.sleep(pause)
    specs, failed = {}, []
    for i, name in enumerate(names):
        versions = []
        page = 1
        try:
            while True:
                time.sleep(pause)
                data = get_json("%s/specifications/%s/versions?embed=true&items=100&page=%d"
                                % (API, name, page))
                if data is None:
                    break
                for v in data.get("_embedded", {}).get("version-history", []):
                    versions.append({k: v.get(k) for k in KEEP})
                if page >= int(data.get("pages", 1)):
                    break
                page += 1
        except Exception as exc:  # recorded, not fatal
            failed.append([name, repr(exc)[:200]])
            continue
        specs[name] = versions
        if i % 200 == 0:
            print("fetched %d/%d" % (i + 1, len(names)), flush=True)
    return {"downloaded": dt.datetime.utcnow().isoformat() + "Z", "n_listed": len(names),
            "failed": failed, "specs": specs}


def load(data_dir, out_dir, allow_net):
    path = os.path.join(data_dir, CACHE_NAME)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    if not allow_net:
        raise SystemExit("no %s in %s and --allow-net not set" % (CACHE_NAME, data_dir))
    blob = download()
    for d in (data_dir, out_dir):
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, CACHE_NAME), "w", encoding="utf-8") as fh:
                json.dump(blob, fh, separators=(",", ":"))
        except OSError:
            pass
    return blob


def _jsonable(o):
    if isinstance(o, dt.date):
        return o.isoformat()
    raise TypeError(type(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--allow-net", action="store_true")
    args = ap.parse_args()

    blob = load(args.data_dir, args.out_dir, args.allow_net)
    specs = blob["specs"]
    snapshot = parse_date(blob.get("downloaded")) or dt.date.today()
    metrics = compute(specs, snapshot)
    verdicts = grade(metrics)
    complete = not blob["failed"] or len(blob["failed"]) <= 0.05 * max(1, blob["n_listed"])
    if snapshot < dt.date(2026, 1, 1):
        verdicts["P3"] = "NULL (snapshot before 2026-01-01)"

    spot = {}
    for name in SPOTCHECK:
        if name in specs:
            r = classify(specs[name], snapshot)
            spot[name] = {k: r.get(k) for k in ("t0", "event", "time_days", "first_rec",
                                                 "first_cr", "latest_family", "n_versions")}
    first_keys = {}
    for vs in specs.values():
        if vs:
            first_keys = vs[0]
            break

    summary = {
        "data_source": API + "/specifications",
        "snapshot_date": snapshot.isoformat(),
        "n_listed": blob["n_listed"],
        "n_failed": len(blob["failed"]),
        "failed_sample": blob["failed"][:20],
        "complete": complete,
        "first_record": first_keys,
        "metrics": metrics,
        "verdicts": verdicts,
        "spotcheck": spot,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=_jsonable)
    print(json.dumps({"verdicts": verdicts, "complete": complete,
                      "n_specs_kept": metrics["n_specs_kept"],
                      "n_eligible": metrics["n_eligible"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
