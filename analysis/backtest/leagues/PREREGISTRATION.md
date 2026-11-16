# Pre-registration: four more leagues

*Written and committed on 16 November 2026, before any model was fitted on English, Spanish, Italian
or French matches. Done before this point: the files were downloaded, the match tables built, and
matches and coverage counted (the numbers below). The git commit that adds this file is the
timestamp. Anything decided after seeing results will be labelled as such in the report.*

## Why

The Bundesliga backtest has 2,223 matches. That is enough to see that the closing market beats the
models, but too few to settle smaller questions, and it is one league. England, Spain, Italy and
France come in the same files from the same source, with the same closing odds. They add 10,736
matches the models have never seen.

## Questions

**Q1 (no decision).** Are the models as far behind the closing market in the four new leagues as in
the Bundesliga?

**Q2 (decision).** Does XGBoost forecast the Bundesliga better when it is trained on all five leagues
instead of the Bundesliga alone?

**Q3 (decision).** Does XGBoost earn its place in the ensemble, now that there are five leagues to
judge it on?

## Data

- **Source:** football-data.co.uk, `source-data` commit `08f400c` (230 files, fetched 16 November
  2026). Top two tiers of each league; the four new leagues from 2005/06.
- **Test set:** every top-flight match from season 2019 on, 12,959 matches, all with market-average
  closing odds (`AvgC`).

  | League | Top flight | Second tier | Test matches | Last match |
  |---|---|---|---|---|
  | Germany | Bundesliga | 2. Bundesliga | 2,223 | 8 Nov 2026 |
  | England | Premier League | Championship | 2,760 | 8 Nov 2026 |
  | Spain | La Liga | Segunda División | 2,779 | 15 Nov 2026 |
  | Italy | Serie A | Serie B | 2,770 | 8 Nov 2026 |
  | France | Ligue 1 | Ligue 2 | 2,427 | 8 Nov 2026 |

- A match without a forecast from all three models (a failed job, say) is left out of every
  comparison, and the report says how many.
- **xG:** the Bundesliga only (Understat to 25 October 2026, football-data.co.uk's xG on Understat's
  scale after that). The four new leagues have no xG here: Understat is offline, and
  football-data.co.uk's xG starts in 2026/27.

## Models (fixed now)

1. **Each league on its own.** Dixon–Coles, XGBoost and the Bayesian model exactly as in the
   Bundesliga backtest (the original, pre-xG versions): same code, features, hyperparameters, priors,
   sampler settings (250 warm-up, 250 draws, 2 chains, tree depth 8) and refit schedule (weekly,
   per season, monthly). Each league is a world of its own, with its own Elo ratings and team
   strengths. Dixon–Coles' time decay is chosen per league from the same four values by RPS on
   2018/19, as it was for the Bundesliga. Nothing else is tuned on the new leagues. The ensemble is
   the equal-weight average of the three.
2. **Pooled XGBoost.** One model for all five leagues.
   - Training pool: the top-flight matches of all five leagues from 2008 on where both teams have at
     least five earlier matches, in seasons before the one being forecast. For 2019 that is about
     20,000 matches, against about 3,400 for the Bundesliga alone.
   - Features: the same 30, computed inside each league, plus one 0/1 indicator per league (35).
   - Same hyperparameters, same early stopping on the last training season, same refit per season.
3. **Pooled XGBoost-xG** (for the Bundesliga): the same with the six xG form features (41 features).
   They are missing for the four leagues without xG and left to XGBoost's missing-value handling.
4. **Pooled XGBoost without the league indicators** (30 features): reported, no decision.

XGBoost's home/draw/away probabilities come from its two goal rates and Dixon–Coles' low-score
correction for the same league, as in the published forecasts.

## Metric and rules

- **Metric:** ranked probability score (RPS) per match. Differences are new minus current, or model
  minus market, so negative means the first one is better.
- **Interval:** paired bootstrap over matches, 4,000 resamples, seed 0, 95% percentile interval.
- **Q1:** the ensemble's RPS minus the market's, for each league, for the four new leagues together
  and for all five. No decision hangs on it. Written down now so it can be wrong: the market is ahead
  in every league, and the gap over the four new leagues together lies between 0.003 and 0.008 (the
  Bundesliga's was 0.0053). Outside that range, the report says the Bundesliga result did not carry
  over as expected.
- **Q2 rule:** switch the published XGBoost to the pooled version if and only if, on Bundesliga
  matches, the xG ensemble with pooled XGBoost-xG minus the xG ensemble as published is below zero
  with its 95% interval entirely below zero.
  - Test set for the rule: the 2,187 Bundesliga matches of the xG test, the ones with published
    Dixon–Coles-xG and Bayesian-xG forecasts (`backtest-results`, `xg/` as of commit `15e0402`).
  - Both XGBoost versions are fitted in the same job, so only the training set differs.
  - If the rule says switch, the switch is made in a follow-up change to `forecast.py`. Nothing on
    the site changes in this one.
- **Q3 rule:** drop XGBoost from the ensemble if and only if both hold:
  - over all five leagues with the original models, the two-model ensemble (Dixon–Coles + Bayesian)
    minus the three-model ensemble is below zero with its 95% interval entirely below zero;
  - on the Bundesliga with the xG models (XGBoost as chosen by Q2), the same difference is below zero.
- **Noise floor:** two runs of the same Bayesian model on different machines move mean ensemble RPS
  by about ±0.00005. Differences smaller than 0.0001 aren't read as real even if they pass a rule.
- **Reported without a decision:**
  - pooled against own XGBoost in each league and over all five, alone and inside the ensemble;
  - each model's RPS, log loss and top-pick rate per league;
  - per-season results;
  - the disagreement check (when models and market differ on the favourite, who is right) per league;
  - the time decay chosen per league.

## Known limitations

- **The summer of 2020.** The pipeline's season runs July to June by match date. England, Spain and
  Italy finished 2019/20 in July and August 2020, so those 221 top-flight matches count as the
  start of 2020 here: 2019 looks short and 2020 long in the per-season tables. Every forecast still
  uses only earlier matches.
- **Empty stadiums.** The models' closed-doors window is Germany's (16 May 2020 to 31 July 2021).
  The other leagues' dates differ by a few weeks.
- **France 2019/20** was abandoned in March 2020 (279 matches).
- **Second-tier shots on target** are missing before 2017/18 in Spain, Italy and France, as in Germany.
- **xG only for Germany,** so the new leagues test the original models, not the xG versions on the site.
- **The bootstrap treats matches as independent.** Matches of one round share news and weather, so
  the intervals are a little too narrow.

## What happens next

The workflow **Backtest (leagues)** runs everything on GitHub and stores the predictions under
`leagues/` on the `backtest-results` branch. The report in `analysis/backtest/leagues/README.md`
applies these rules as written.
