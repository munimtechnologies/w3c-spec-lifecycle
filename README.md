# w3c-spec-lifecycle

A pre-registered survival and competing-risks study of W3C /TR specifications: how often a
Working Draft becomes a Recommendation or ends as a Note or Retired document, and whether
the 2020 W3C Process changed that.

By MV2 of Munim, Inc. (mv2@munimtech.com). The work was made with AI agents working in his
name. Code: Apache-2.0. Results and text: CC BY 4.0.

## What was pre-registered

`PREREG.md` lists six predictions (P1-P6), their definitions and grading rules. It was
published here before any lifecycle data was counted. `job.py` downloads every
specification's version history from the public W3C API (https://api.w3.org, no key) and
computes the statistics. `test_job.py` checks the arithmetic against a hand-built fixture.
The job ran once in a sealed container (tests passed first) on 2026-10-30. Its raw output is
`results/run1-summary.json`.

## Data

1,721 specifications listed, all fetched (0 failures), 17,756 versions. Six specs whose
version set is a subset of another spec's were dropped, leaving 1,715. Of these, 1,165 enter
as a Working Draft (550 enter as something else and are excluded), and 912 of those are on
the Recommendation track (cohort A).

## Results (snapshot 2026-10-30)

| | Prediction | Measured | Verdict |
|---|---|---|---|
| P1 | Cohort A, first draft 2000-2014: share reaching REC within 10 years < 0.50 | 0.448 (n = 496, Aalen-Johansen) | HELD |
| P2 | Same cohort: share ending as Note/Retired within 10 years >= 0.15 | 0.308 | HELD |
| P3 | Four years after the first draft, 2017-2021 vs 2010-2014: REC share lower by > 5 points AND CR share higher by > 5 points, in cohorts A and B | A: REC 25.0% -> 24.3%, CR 13.4% -> 14.7%. B: REC 20.5% -> 16.8%, CR 11.0% -> 10.2% | **FAILED** |
| P4 | CR publications since 2021: CR Drafts outnumber CR Snapshots at least 3:1 | 1,519 vs 107 (14.2:1) | HELD |
| P5 | New Recommendations per year: 2021-2025 mean < 0.9 x the 2015-2019 mean | 7.0 vs 15.2 (0.46 x) | HELD |
| P6 | At least 40 "CR forever" specs (latest version CR, first CR at least 3 years ago) | 70 | HELD, but an upper bound (see below) |

Sensitivity S1 (dropping version URIs shared between specs) gives the same verdicts for
P1-P3.

## What it says

- Fewer than half of rec-track specs started in 2000-2014 became a Recommendation within ten
  years, and about three in ten were closed as a Note or Retired.
- W3C now publishes about half as many new Recommendations a year as in 2015-2019, and since
  2021 almost every Candidate Recommendation publication is a CR Draft (14 for every CR
  Snapshot).
- **The failed prediction:** four years after a spec's first draft, the share at
  Recommendation (about a quarter) and the share in CR (about one in seven) did not change
  between the 2010-2014 and 2017-2021 starters. The 2020 Process did not visibly slow the
  first four years of a spec's life.

## Exploratory (seen after the run, not pre-registered)

- Fewer specs start. Cohort A had 224 first drafts in 2010-2014 and 136 in 2017-2021 (39%
  fewer), while the four-year REC share stayed near 25%. Fewer entrants explain much of the
  drop in Recommendations per year. Some Recommendations come more than four years after the
  first draft, so this is not a full decomposition.
- Fewer specs are closed. Four years after the first draft, 27.7% (62 of 224) of the
  2010-2014 rec-track starters had ended as a Note or Retired, against 6.6% (9 of 136) of the
  2017-2021 starters. The share still a Working Draft rose from 32.6% to 52.9%.
- 146 eligible specs have no outcome and no new version in over three years.

The follow-up below tests the first point from a different starting clock.

## Status strings and caveats

- The raw status histogram is in the results. Three strings fell outside the pre-registered
  families and were treated as OTHER (not an ending): "Draft Note" (2,146 versions), "Draft
  Registry" (69) and "Statement" (3). Draft Note and Statement are on the Note track. The
  follow-up re-runs P1-P3 with them counted as endings.
- P6 is an upper bound on specs that never became a Recommendation. A live check shows
  `geolocation` was a Recommendation from 2022-09-01 until a revision went back to CR on
  2026-03-26, and the P6 definition counts it. The follow-up counts only specs that never had
  a Recommendation.
- Old versions often carry rec-track = false even on specs that later became
  Recommendations (8 of 56 first versions in the 1990s are flagged, against 198 of 245 in the
  2020s). That is why cohort A also counts any spec with a CR, PR or REC version.
- A spec abandoned without a Note is censored, not counted as ended.

Live spot-checks against api.w3.org on 2026-10-30: css-color-3 (first draft 1999-06-23,
first CR 2003-05-14, Recommendation 2011-06-07), webdatabase (Retired 2010-11-18, 574 days
after its first draft) and user-timing (first CR 2021-12-02, latest a CR Draft of
2026-03-11, censored) all match the job's records.

## Follow-up 1 (pre-registered, queued)

`followups/cr-time/` holds the pre-registration and code for G1-G3: a strict "never a
Recommendation" CR-forever count, P1-P3 with Note-track drafts counted as endings, and the
share of specs reaching Recommendation within three years of their first CR, 2011-2015
against September 2020 to September 2023. Results will be added here.

## Nearest prior work

- alan33d/time-to-rec (W3C TPAC 2026 hackathon): an interactive visualization of FPWD -> CR
  -> REC durations by working group, with a "still waiting" list. It does not publish
  numbers, handle censoring or competing endings, or compare before and after the 2020
  Process.
- W3C's spec dashboard lists stale CR Drafts and specs with no /TR update in three years.
  W3C's Milestones guide gives planning durations, and a TPAC 2020 talk names the model "CR
  forever". Neither gives measured distributions.
- Baron and Spulber's Searle Center database (2018) studies withdrawal across standards
  bodies, not W3C draft-to-Recommendation time.

As far as searches on 2026-10-30 found, this is the first pre-registered, censoring-aware
cohort study of W3C /TR outcomes with a before/after test of the 2020 Process.

## Run it

    python -m unittest -v
    python job.py --data-dir ./data --out-dir ./out --allow-net

Standard library only, Python 3.10 or newer. The download takes about 15 minutes at the
built-in polite pace.

-- MV2, Munim, Inc.
