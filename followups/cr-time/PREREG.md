# Pre-registration: W3C specification lifecycle, follow-up 1 (robustness and time in CR)

**By MV2 of Munim, Inc. Prepared with AI agents working in his name.**
**Filed: 2026-10-30 (UTC), after run 1 was graded and before this job's statistics were
computed.** Code: Apache-2.0. Text: CC BY 4.0.

## Why

Run 1 (`results/run1-summary.json`, snapshot 2026-10-30) left three open questions:

1. P6 counted 70 "CR forever" specs: the latest version is CR-family and the first CR is at
   least 3 years old. A live check of `geolocation` showed that this definition also counts
   specs that became a Recommendation and later went back to CR for a revision (Geolocation
   was a Recommendation from 2022-09-01 to 2026-03-24, then a CR Snapshot). So 70 is an upper
   bound on specs that never reached Recommendation.
2. Run 1 mapped three raw statuses to OTHER (non-terminal): "Draft Note" (2,146 versions),
   "Draft Registry" (69) and "Statement" (3). Draft Note and Statement are on the Note track,
   so a spec that moves to them has arguably left the Recommendation track.
3. P3 (state four years after the first draft) found no shift after the 2020 Process, yet
   new Recommendations per year halved (P5). P3 starts the clock at the first draft. This
   follow-up starts it at the first Candidate Recommendation instead.

## Data

The same cache and data volume as run 1 (data_key w3c-api-versions), so the same snapshot.
The code reuses run 1's `job.py` unchanged (fetched from this repository at run time):
status families, version dedup, spec dedup and the per-spec timeline are all run 1's.

## Predictions and rules

**G1 (partly informed: geolocation and the 40 names in run 1's P6 sample were seen).**
Among run 1's P6 specs, those with no REC-family version at any date number at least 40.
HELD if at least 40, else FAILED. The excluded names are listed.

**G2 (robustness, reasoned before running).** Sensitivity S2 maps "Draft Note" and
"Statement" to END and recomputes P1-P3 with run 1's rules. The verdicts stay HELD, HELD
and FAILED. HELD if all three are unchanged; FAILED otherwise, naming the ones that changed.

**G3 (partly informed: run 1's P3-P6 results were seen; no CR-origin statistic was).**
For each deduplicated spec, c0 is the date of its first CR-family version. Specs with a
REC-family version before c0 are excluded and counted. The outcome is the first REC-family
or END-family version on or after c0. The old cohort has c0 from 2011-01-01 to 2015-12-31.
The new cohort has c0 from 2020-09-15 (the 2020 Process took effect) to 2023-09-30, so
every member has a full 3 years of follow-up by the snapshot. The share reaching REC within
1,096 days of c0 is lower in the new cohort by more than 0.10. HELD if new < old - 0.10;
REVERSED if new > old + 0.10; otherwise NULL. Reported with no prediction: the shares at 1
and 2 years, the END share at 3 years, the old cohort's 5-year share, and G3 under S2.

## Descriptives (no predictions)

- Cohort A entries per first-draft year to 2021, with their state four years later. This
  separates "fewer specs start" from "fewer of them finish".
- CR-family publications per year by raw status, and first-CR dates per year.

## Limits

The 2014-2015 Processes removed Last Call and the 2020 Process changed the Patent Policy,
so a G3 shift cannot be pinned on CR Drafts alone. The new cohort sits in the COVID years.
None of G1-G3 is fully blind (see above), so this is a robustness check on run 1 plus one
partly informed test, not an independent replication.
