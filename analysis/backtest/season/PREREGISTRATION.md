# Pre-registration: how good is the season simulator?

*Written and committed on 18 November 2026, before the simulator was run on any past season for a
score. Done before this point: the simulator (`analysis/pipeline/season_sim.py`) was written and run on
the current season (2026/27 after matchday 9); one 10,000-season run on 2016/17 after 90 matches was
timed, its output not looked at; the rating fits were timed at three dates in November 2016. The git
commit that adds this file is the timestamp. Anything decided after seeing results will be labelled as
such in the report.*

## Why

The new Season page says things like "Bayern 90% to win the league" and "Schalke 48% to go down". A
number like that is only worth printing if, over many seasons, the clubs given 48% went down about 48%
of the time. The match-level backtest says nothing about this: a simulator can use good match forecasts
and still be far too sure of itself, because it plays the whole season with ratings frozen on the day it
starts. Real teams change. How much doubt to add is the one setting this test has to fix.

The second question is the site's usual one. My models rate the clubs from scores and xG; the bookmakers'
prices rate them too. Which ratings make the better season forecast?

## Data

- **Source:** football-data.co.uk, `source-data` commit `08f400c`; Understat xG from the private data
  repository (the files the xG test used), so the models are the published ones.
- **Seasons:** the 1. Bundesliga from 2014/15 to 2025/26. Understat has xG from 2014/15.
  - **Tuning:** 2014/15 to 2018/19 (5 seasons). The settings are chosen here.
  - **Test:** 2019/20 to 2025/26 (7 seasons). Scored once, with the settings fixed.
- **Checkpoints:** after k matchdays for k = 0 (before the first kick-off) to 33. football-data.co.uk has
  no matchday numbers, so "after k matchdays" means: after the date of the season's (9k)th match in date
  order, every match up to and including that date counted as played. Postponed matches make this
  approximate; it is the same for every forecaster.
- **Outcome:** the final table ranked by points, goal difference and goals scored (the head-to-head never
  decided a position in these seasons' top flights if the check in the report confirms it; any case where
  it would have is reported and settled by hand from the official table).

## The simulator

For each checkpoint:

1. **Ratings**, fitted only on matches played before the checkpoint (1. and 2. Bundesliga, the last
   eight seasons):
   - **models:** the published Dixon–Coles (time decay 0.0019 per day, a quarter xG), unchanged.
   - **market:** the same Dixon–Coles shape fitted to the bookmakers' margin-free 1X2 probabilities
     (proportional margin removal) instead of the scores: closing average where the files have it
     (2019/20 on), else the pre-closing average, else Bet365. Time-weighted cross-entropy, the same
     small ridge penalty, the low-score parameter rho taken from the models' fit at the same date.
2. **Doubt:** each simulated season gives every club one strength shift δ ~ N(0, σ²), added to its
   attack and its defence for all its remaining matches.
3. **Play** every remaining match from the Dixon–Coles score distribution (the low-score correction
   included), 10,000 seasons, seed fixed per season and checkpoint and shared by all settings.
4. **Rank** by points, goal difference, goals scored, then at random.

## Settings to choose (tuning seasons only)

- σ ∈ {0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20}, separately for each set of ratings.
- The market ratings' time decay ξ ∈ {0.0019, 0.004, 0.008} per day, chosen jointly with its σ.

The values in `season_sim.py` before this test (σ = 0.075 for both, ξ = 0.004) are placeholders and
will be replaced by the chosen ones.

## Scores

- **Primary: positional RPS.** For each club at each checkpoint, the ranked probability score of the
  forecast distribution over the 18 final positions: the mean over positions 1–17 of
  (P(finish r-th or better) − 1[finished r-th or better])². Lower is better. Averaged over clubs,
  checkpoints 0–33 and seasons, every checkpoint weighted equally.
- **Secondary:** Brier scores for the title, the top four, the top six, 16th place and 17th–18th;
  calibration of all those probabilities pooled (bins of predicted probability against how often it
  happened); the same by stage of the season (checkpoints 0–11, 12–22, 23–33).
- **Baselines:** "the table as it stands" (probability 1 on the current position, checkpoints 1–33
  only; ties ordered as the site's table orders them) and "know nothing" (1/18 for every position).

## Decision rules, fixed now

1. **σ for each set of ratings** is the grid value with the lowest primary score on the tuning seasons
   (with ξ for the market). Fixed before the test seasons are scored. If the best value is at the edge of
   the grid (0.20), that is reported, and the edge value is used; the grid is not widened after seeing it.
2. **What the page says about which ratings are better** is decided by the test seasons: if one set has
   the lower primary score overall *and* in at least 5 of the 7 test seasons, the page says it has been
   the better season forecaster since 2019/20. Otherwise it says neither has been clearly better.
   Either way the page leads with my models' numbers and shows the bookmakers' beside them, as every
   other page does; the test decides the wording, not the layout.
3. **Calibration claim.** The page may call the simulator "well calibrated" only if, on the test
   seasons, every probability bin with at least 100 forecasts has an observed frequency within its 95%
   binomial interval of the bin's average forecast, or within 3 percentage points of it. Otherwise the
   page says where it is too sure or too shy.
4. Also reported, decided nothing: σ = 0 on the test seasons (how much the doubt matters), and both
   baselines.

## What will not change after this

The Dixon–Coles settings, the definition of a checkpoint, the tie-break, the number of simulations,
the scores and the seasons in each set.
