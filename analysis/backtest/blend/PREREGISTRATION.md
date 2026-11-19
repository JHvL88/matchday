# Pre-registration: do the models know anything the price doesn't?

*Written and committed on 19 November 2026, before any result was regressed on a price and a
forecast together, and before any blend of the two was fitted or graded, on any group of matches.
Done before this point: the match tables were built and the matches were counted per season (the
numbers below). The git commit that adds this file is the timestamp. Anything decided after seeing
results will be labelled as such in the report.*

## Why

Every test so far has asked whether the models beat the market. They don't: not at the closing
price (the four-league test), not at the early price (the closing-line test). This test asks a
smaller question, and the last one worth asking about match results with these models:

> Give a forecaster the bookmakers' price. Does it forecast better if it is also shown the models?

A forecast can be worse than the market and still be useful next to it, the way a second opinion
from a junior doctor is useful if it catches something different. If the best mix of price and
models puts no weight on the models, they hold nothing the price doesn't, and no rule built on them
can find value in this market. If it puts some weight on them, the next question is whether that is
enough to pay the bookmaker's margin.

## What was already known

Whoever reads the prediction further down should know it is not a blind guess. From the
closing-line report (17 November):

- RPS over these matches: models 0.2008, early price 0.1963, closing price 0.1955.
- The line does not move toward the models (slope −0.001).
- Outcomes the models rated 5+ points above the early market: models 36.8%, market 29.0%, happened
  26.5%. Outcomes rated 5+ points below: models 45.1%, market 53.4%, happened 55.3%.
- Against other bets at the same odds, the rule's picks returned 8.4 points less (−13.8 to −2.9);
  betting against the models returned 1.5 points more (−2.1 to +4.8).
- Removing the margin proportionally overstates outsiders' chances.

These all point the same way: the weight on the models is zero or below.

Not done before this file was committed: no regression of results on prices and forecasts, no
blend, no weight, in any league, for any group of matches.

## Data

Exactly the matches, prices and forecasts of the closing-line test. Nothing is refitted.

- **Source:** football-data.co.uk, `source-data` commit `08f400c`.
- **Early price:** the market average collected a few days before the match (`avg`). The main
  price here, because it is one a reader could have taken.
- **Closing price:** the market average at kick-off (`avgc`).
- **Market probabilities:** odds with the margin removed proportionally, as everywhere on the site.
- **Set A. Five leagues, original models.** The three-model ensemble of the four-league report
  (`backtest-results` commit `f18b825`, `leagues/`). 12,958 matches with an early price, 2019/20
  to November 2026.
- **Set B. Bundesliga, published models.** The xG ensemble with XGBoost trained on all five
  leagues (`backtest-results` commit `f18b825`, `xg/`). 2,223 matches.

Matches per season in set A: 1,504 (2019/20), 2,047, 1,825, 1,826, 1,752, 1,752, 1,752 and 500
(2026/27 so far).

## The blend

For each match, each outcome (home, draw, away) gets a score, and the three scores are turned into
probabilities that sum to one (a softmax):

    score = a + b × ln(market probability) + c × ln(model probability)

`a` is one constant for draws and one for away wins (home wins have none). Two versions:

- **Price only:** `c` is fixed at zero. `a` and `b` let the price correct its own habits: `b` above
  1 means favourites win more often than the price says. This matters for fairness. Proportional
  margin removal is known to overstate outsiders, and the models like outsiders. Without this
  version the models would be blamed for the bookmakers' arithmetic.
- **Price and models:** `c` is free.

How to read `c`: at 0 the models add nothing to the price. Above 0 the best forecast leans from the
price toward the models. Below 0 it leans *away* from them: a model liking a team more than the
market does would be bad news about that team. With `a` = 0, `b` = 1 and `c` = 0 the blend is the
market price unchanged.

Both versions are fitted by maximum likelihood (Newton's method, no penalty). Probabilities are
floored at 0.000001 before the logarithm.

## Questions and rules

**Q1 (decision). Do the models add information to the early price?**

Two numbers, both on set A with the early price:

- **The weight.** `c` fitted on all 12,958 matches, with a 95% interval.
- **The gain on matches the blend hasn't seen.** For each season from 2020/21 to 2026/27, both
  versions are fitted on all earlier seasons of set A (five leagues together) and forecast that
  season. 2019/20 is only ever used for fitting, which leaves 11,454 forecast matches. The gain is
  the mean log loss of *price and models* minus that of *price only*; below zero means the models
  helped. Log loss is used because it is what the blend is fitted on; RPS is reported next to it.

Three verdicts:

1. **Information.** `c` above zero with its whole interval above zero, the gain below zero with its
   whole interval below zero, and `c` above zero in set B as well.
2. **Contrary.** `c` below zero with its whole interval below zero, and the gain below zero with
   its whole interval below zero. The models' disagreement with the market predicts results, in the
   wrong direction.
3. **Nothing.** Anything else.

**Q2 (decision). Does the blend pay the bookmaker's margin?**

The forecasts are the *price and models* blend's for the 11,454 matches it hadn't seen. The rule:
€1 on every outcome where blend probability × odds is at least 1, so the blend expects the bet at
least to break even. Three verdicts:

1. **Value.** At the average early price, the realised return is above zero with its whole 95%
   interval above zero.
2. **Value only by shopping around.** Not 1, but the same holds at the best early price in the
   market (`max`).
3. **No value.** Neither.

Realised return decides, not closing-line value. The closing-line test showed that CLV with
proportional margin removal understates losses on outsiders by a factor of three. CLV is reported
next to every return anyway.

Q2 is run whatever Q1 says, so nobody has to wonder.

## What follows from each

- **Information and Value (either kind):** a forward test on the weekly forecasts at recorded
  prices, pre-registered separately. Whether the site should show the blend rather than the raw
  models is a separate decision.
- **Information, No value:** the models see something, too little to bet on. The blend becomes the
  candidate for the calibration layer already on the list; no betting rule.
- **Contrary:** no betting rule from this data, whatever Q2 says about it. The follow-up is to find
  which input the models over-trust and the market discounts. That is exploratory and will be
  labelled so.
- **Nothing:** the match-result market is closed for these models. No further 1X2 tests of them.
  Work moves to total goals and handicaps, and to reader-bookmaker prices against the market
  consensus.

Nothing on the site changes with this report.

## Written down now so it can be wrong

- `c` between −0.35 and +0.05, more likely below zero than above.
- `b` between 1.00 and 1.15.
- The gain in log loss smaller than 0.0010 in either direction.
- Q1: Nothing or Contrary. Q2: No value at the average price, with fewer than 1,500 bets.

## Method

- **Interval for the weights:** bootstrap over matches, the blend refitted in each of 4,000
  resamples, seed 0, 95% percentile interval.
- **Interval for gains and returns:** bootstrap over matches on the forecasts as made (the blend is
  not refitted inside the resample), 4,000 resamples, seed 0. A match's outcomes and bets stay
  together.

## Reported without a decision

- **The same with the closing price** as the market: can the models add anything to the price at
  kick-off?
- **The plain version of the weight.** The single weight `w` in (1 − w) × market + w × models that
  fits the results best, searched from −0.5 to 1. Easier to say out loud than `c`: "of every 100
  points, w go to the models".
- **Each model alone** (Dixon–Coles, Bayesian, XGBoost), the ensemble with XGBoost trained on all
  five leagues, and all three models entered as three separate terms.
- **Set B** in full: the weight, and the walk-forward gain fitted on the Bundesliga alone.
- **Per league and per season:** the weight fitted on each alone.
- **RPS and log loss on the 11,454 forecast matches** for the raw early price, *price only*,
  *price and models*, the raw models and the closing price. Does adding the models bring the early
  price any closer to the closing one?
- **The betting rule further:** at Bet365's early price; with the break-even bar raised to 2%, 5%
  and 10% expected profit; the *price only* blend under the same rule (bets that owe nothing to the
  models, only to the price's own habits); and every return set against other bets at the same
  odds, as in the closing-line report.
- **Where the two blends differ most:** results by how far *price and models* sits from *price
  only*, in five groups.

## Known limitations

- **Timing.** The early price is a Friday or Tuesday afternoon snapshot, not the hour a post goes
  out.
- **The average is not a bookmaker**, and the best price assumes accounts everywhere and no stake
  limits.
- **Taxes and limits.** Germany's 5.3% betting tax and bookmakers' stake limits are ignored. Both
  make real returns worse than these.
- **The bootstrap treats matches as independent.** Matches of one round share news, so the
  intervals are a little too narrow.
- **The first forecast season leans on one season.** 2020/21 is forecast from 1,504 matches, most
  of them played before the pandemic's empty stadiums. Per-season numbers are reported.
- **One blend for five leagues.** The weights are shared; per-league weights are reported, not used.
- **No xG outside Germany.** Set A tests the original models; the published ones are set B only.
- **The author knew the closing-line results** (listed above) when choosing these rules.

## What happens next

`analysis/pipeline/evaluate_blend.py` applies these rules as written, and the report goes in
`analysis/backtest/blend/README.md`.
