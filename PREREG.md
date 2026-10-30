# Pre-registration: W3C specification lifecycle (run 210, 2026-10-30)

Work by MV2 of Munim, Inc., made with AI agents. Code Apache-2.0; results CC BY 4.0.

Written before any lifecycle data was downloaded or counted. While designing it, the
only version histories read were five specs, used to learn the API's shape:
user-timing, webdatabase, css-color-3, cors (metadata only) and the spec list.

## Question

How often does a W3C specification that enters as a Working Draft become a
Recommendation, how often does it end as a Note, Retired or Discontinued, and did the
2020 Process (Candidate Recommendation Drafts and "living standards", operative
2020-09-15) change where specifications sit four years after their first draft?

## Prior art checked (2026-10-30)

- W3C Milestones guide: planning figure of about 174 days to Recommendation, with no
  measured distribution.
- TPAC 2020 breakout "W3C 2020: Living Standards and Reviews": calls the model
  "Candidate Recommendation forever", with no numbers.
- Baron & Spulber, Searle Center Database (JEMS 27(3), 2018): survival of standard
  documents from release to withdrawal, across SSOs. It does not measure W3C
  draft-to-Recommendation time.
- Simcoe, "Standard Setting Committees" (AER 2012): IETF committee delay, not W3C.
- Web searches for W3C Recommendations per year, FPWD-to-REC durations and the
  effects of the 2020 Process turned up no quantified study. Per-spec history pages
  exist, but nobody has aggregated them.

The delta here: the first cohort-level survival and competing-risks analysis of W3C
/TR histories, with a before/after test of the 2020 Process.

## Data

api.w3.org (no key): /specifications (1,721 at design time) and
/specifications/<shortname>/versions?embed=true, which gives each version's date,
status, rec-track, uri and shortlink. Snapshot = the download date.

## Definitions (fixed now)

Status families are matched case-insensitively. Every raw status string is reported.
- WD: First Public Working Draft, Working Draft, Last Call Working Draft
- CR: Candidate Recommendation, Candidate Recommendation Snapshot, Candidate Recommendation Draft
- PR: Proposed Recommendation, Proposed Edited Recommendation
- REC: Recommendation, Edited Recommendation, Amended Recommendation
- END: Note, Group Note, Working Group Note, Interest Group Note, Retired, Discontinued Draft
- anything else: OTHER (non-terminal)

Spec dedup: a spec whose set of version URIs is a subset of another spec's set is
dropped. For identical sets, the alphabetically first shortname is kept.

Entry t0 = the date of the spec's first WD-family version, provided no CR, PR, REC or END
version comes earlier. Specs without such an entry are excluded and counted.

Event: first REC-family date on or after t0. Competing event: first END-family date on
or after t0 that comes before any REC. Otherwise the spec is censored at the snapshot.
Cumulative incidence uses Aalen-Johansen.

Cohort A (rec-track): eligible specs with any version rec-track=true or any CR, PR or
REC version. Cohort B: all eligible specs. Cohort B exists because old versions carry
rec-track=false even on specs that later became Recommendations (seen on css-color-3).

State at t0+4y: REC if the event came by then, END likewise. Otherwise it is the family
of the latest version dated on or before t0+4y.

Sensitivity S1: drop every version URI that appears in more than one remaining spec
(inherited predecessors, e.g. webdatabase lists a webstorage draft), then recompute
P1-P3.

## Predictions

- P1: Cohort A, t0 2000-2014: CIF_REC at 10 years < 0.50.
- P2: Cohort A, t0 2000-2014: CIF_END at 10 years >= 0.15.
- P3: State at t0+4y, cohort 2017-2021 vs 2010-2014: the REC share is lower by more
  than 0.05 AND the CR share is higher by more than 0.05.
  - HELD only if both conditions hold in cohort A and in cohort B.
  - REVERSED if both effects go the opposite way by more than 0.05 in both cohorts.
  - FAILED otherwise.
  - Every member of both cohorts has a full 4 years of follow-up, given a snapshot
    on or after 2026-01-01.
- P4: Among CR-family publications dated 2021-01-01 or later (unique URIs), CR Drafts
  outnumber CR Snapshots at least 3:1.
- P5: New Recommendations per year (first REC-family date per deduped spec): the
  2021-2025 mean is below 0.9 x the 2015-2019 mean. REVERSED if above 1.1 x;
  otherwise NULL. Both windows are closed years, so lag cannot bias this.
- P6: "CR forever": at least 40 deduped specs whose latest version is CR-family and
  whose first CR-family version is at least 3 years before the snapshot.

## Known limits

- The 2020 Process also changed the Patent Policy (CR Snapshots get patent
  commitments), and the 2014-2015 Processes removed Last Call. A shift therefore
  cannot be pinned on CR Drafts alone.
- A spec abandoned without a Note is censored, not counted as ended. Its staleness is
  reported separately.
- The API's spec identity follows W3C's own version-history links. Level splits and
  merges are handled only by dedup and S1.
