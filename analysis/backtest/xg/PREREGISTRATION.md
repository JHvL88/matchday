# Pre-registration: does xG improve the models?

*Written and committed on 16 October 2026, before any xG model was fitted or any xG backtest was run.
The git commit that adds this file is the timestamp. Anything decided after seeing results will be
labelled as such in the report.*

## Questions

**Q1 (primary).** Do the three published models forecast better when they also learn from expected
goals (xG)?

**Q2 (secondary).** Does XGBoost earn its place in the ensemble?

## Data

- **Matches and closing odds:** football-data.co.uk, `source-data` commit `e47f4cf` (as in the step 1 backtest).
- **xG:** Understat, match-level xG for every 1. Bundesliga match since 2014/15, fetched on 16 October 2026 into the private data repository (`understat/`, SHA-256 manifest).
  - Joined on club and date (within a day).
  - All 3,717 Understat matches join; 100% of 1. Bundesliga matches since 2014/15 have xG.
  - The one score disagreement is Union v Bochum, 14 December 2024, where football-data records the awarded 0–2 and Understat the 1–1 on the pitch.
  - The 2. Bundesliga has no xG, and neither do seasons before 2014/15.
- **Test set:** the same 2,187 matches as the step 1 backtest, every 1. Bundesliga match from 2019/20 to matchday 5 of 2026/27. Same walk-forward rules: every forecast uses only matches played before it.

## Model variants (fixed now)

The current models are unchanged. Their predictions come from `backtest-results` commit `eee9da5` (workflow run 38910301480, code `5e8d2ed`). Each xG variant changes one thing.

1. **Dixon–Coles-xG.**
   - The Poisson part of the likelihood uses a blended target, `w × xG + (1 − w) × goals`, for matches with xG, and goals otherwise.
   - The low-score correction still uses actual goals.
   - Time decay stays at ξ = 0.0019, the step 1 choice.
   - `w` is chosen from {0, 0.25, 0.5, 0.75, 1} by RPS on 2018/19, the season before the test set, with the same weekly refits. If `w = 0` wins, Dixon–Coles-xG is Dixon–Coles.
2. **XGBoost-xG.**
   - The current 30 features plus six xG form features: home and away team xG for and against (exponentially weighted, half-life 8 matches, like the other form features), and the home-minus-away gaps in both.
   - Missing (2. Bundesliga, pre-2014/15) is left to XGBoost's native missing-value handling.
   - Same hyperparameters, training pool (2008 onwards) and per-season refits.
3. **Bayesian-xG.**
   - The same model, plus xG as a second, noisy view of chance creation: for each team in a match with xG, `max(xG, 0.02) ~ Gamma(mean = ψ × λ, shape κ)`, where λ is the model's existing expected shots on target.
   - Priors: ψ ~ LogNormal(log 0.32, 0.3), since xG per shot on target is 0.32 in these data, and κ ~ Gamma(2, 0.5).
   - No new team parameters.
   - Same sampler settings (250 warm-up, 250 draws, 2 chains, tree depth 8) and monthly refits.
4. **Ensemble-xG:** the equal-weight average of the three xG variants.

## Metric and decision rules

- **Metric:** ranked probability score (RPS) per match. The difference is always new minus current, so negative means the new version is better.
- **Interval:** paired bootstrap over matches, 4,000 resamples, seed 0, 95% percentile interval.
- **Q1 rule:** switch the published models to the xG versions if and only if the Ensemble-xG minus Ensemble RPS difference is below zero and its 95% interval lies entirely below zero. Otherwise keep the current models.
- **Q2 rule:** on the model set chosen by Q1, drop XGBoost from the ensemble if and only if the two-model ensemble (Dixon–Coles + Bayesian, equal weights) minus the three-model ensemble is below zero with the 95% interval entirely below zero. Otherwise keep XGBoost.
- **Reported without a decision:**
  - each variant against its current model;
  - log loss and top-pick rate;
  - the gap to the closing market;
  - per-season results;
  - the disagreement check;
  - the tuned `w`.

## What the noise looks like (measured before writing this)

Two runs of the current models on identical code and data, on different GitHub machines, give slightly different Bayesian samples: 520 of 2,187 ensemble forecasts change, by up to 3 points. The effect on mean ensemble RPS is −0.000002 (95% interval −0.00004 to +0.00003). That pure-noise comparison does not pass the Q1 rule (its interval includes zero), as it shouldn't, but effects smaller than about 0.0001 shouldn't be read as real even if they pass.

## Known limitations

- **xG model vintage.** Understat's xG for a 2019 match may come from a model fitted later, so it may carry a sliver of information from the future. The xG of a match is only used for forecasts of later matches, but the xG model itself isn't frozen in time.
- **One xG provider.** Understat's model isn't documented in detail.
- **2. Bundesliga.** Promoted clubs have no xG history, so their first top-flight months rest on goals and shots alone.

## What happens next

The xG backtest runs on GitHub, like the step 1 backtest. The report in `analysis/backtest/xg/README.md` will apply these rules as written, and the site's figures only change if a rule says so.
