# Pre-registration: does the closing line move toward the models?

*Written and committed on 17 November 2026, before any early price was compared with a closing
price, a forecast or a result. Done before this point: the match tables were built and the
matches with each price were counted (the numbers below). The git commit that adds this file is the
timestamp. Anything decided after seeing results will be labelled as such in the report.*

## Why

The site's paper bets are graded on closing-line value (CLV): was the price taken better than the
one the market settled on at kick-off? Two bets a month will take decades to say anything. The
source files answer the same question for 12,959 matches at once, because since 2019/20 every row
carries two prices: one collected a few days before the match and one at kick-off.

The four-league test showed that the closing market forecasts better than the models. That does not
settle this question. A model can lose to the closing price and still be right against the *early*
price often enough to be worth something. This test asks whether it is.

## What was already known

- The closing market beats the ensemble by 0.0053 RPS in all five leagues.
- When models and closing market disagree about the favourite, results side with the market and go
  a little further (the disagreement table in the four-league report).

Not looked at before this file was committed: how prices moved between the early and the closing
collection, in any league, for any group of matches.

## Data

- **Source:** football-data.co.uk, `source-data` commit `08f400c` (the files of the four-league test).
- **Early price:** football-data.co.uk's pre-closing odds. Its notes say they are collected on
  Friday afternoons for weekend matches and on Tuesday afternoons for midweek matches. Three versions:
  - `avg`: the market average. What a typical bookmaker offered; the main one here.
  - `b365`: Bet365, one real bookmaker.
  - `max`: the best price anywhere in the market. An upper bound: it needs an account everywhere.
    The match tables don't carry it, so it is read from the source files, row by row.
- **Closing price:** the market average at kick-off (`avgc`), the benchmark of every other test here.
- **Probabilities:** bookmaker odds with the margin removed proportionally, as everywhere on the site.
- **Test set:** the 12,959 top-flight matches of the four-league test (2019/20 to November 2026).
  12,958 have the early average and best price; 12,954 have Bet365's. A match without the price a
  comparison needs is left out of that comparison, and the report says how many.

## Forecasts (fixed now, nothing is refitted)

- **A. Five leagues, original models.** The three-model ensemble exactly as graded in the
  four-league report (`backtest-results` commit `7124cc7`, `leagues/`). 12,959 matches.
- **B. Bundesliga, published models.** The xG ensemble with XGBoost trained on all five leagues, as
  the site runs it (`backtest-results` commit `f18b825`, `xg/`). 2,223 matches.

Every forecast uses only matches played before it. Dixon–Coles is refitted from the matches before
each Tuesday-to-Monday block, the Bayesian model from the matches before each month, and XGBoost's
features come from each team's own earlier matches. So no model knows anything that happened after
the early price was collected.

## Definitions

For each match and each outcome (home, draw, away):

- **Edge** = the ensemble's probability minus the early market's (average, margin removed).
- **Line move** = the closing probability minus the early probability.
- **CLV of a bet** = odds taken × closing probability − 1, the site's definition. Zero means a fair
  bet if the closing market is right. A bet picked at random at a typical bookmaker scores about
  minus the margin, roughly −5%.

## Questions and rules

**Q1 (no decision). Does the line move toward the models?**

- The slope of line move on edge over all three outcomes of every match (least squares; both sum to
  zero within a match, so there is no intercept to fit). 0 means the market ignores what the models
  think, 1 means it closes the whole gap, below 0 means it moves away.
- A table of the average line move by size of edge: below −5 points, −5 to −2, −2 to +2, +2 to +5,
  above +5.
- Written down now so it can be wrong: the slope over five leagues lies between −0.03 and +0.03.
  The market does not care what my models think.

**Q2 (decision). Does the site's betting rule find value?**

The rule is the one on the Track record: €1 on every outcome the ensemble rates at least 5 points
above the market, here the early market, at the early price. Three verdicts, on set A at the average
early price:

1. **Value.** Mean CLV above zero with its whole 95% interval above zero, and mean CLV above zero in
   set B as well.
2. **Signal, no value.** Not 1, but the line moves toward the picks: mean line move of the rule's
   bets above zero with its whole interval above zero. The models see something, but not enough to
   pay the bookmaker's margin.
3. **Nothing.** Neither.

What follows from each:

- **Value:** a forward test on the weekly forecasts with recorded prices, pre-registered separately.
- **Signal, no value:** the same forward test only if the best-price version (`max`) has mean CLV
  above zero with its interval above zero; otherwise as for Nothing.
- **Nothing:** the paper-betting text on the Track record says so, as a follow-up change. The ledger
  itself runs on as registered. The search for an edge moves to total goals and handicaps.

Nothing on the site changes with this report.

Written down now so it can be wrong: verdict 3 or at best 2; mean CLV at the average price between
−8% and −3%; realised return below zero.

## Method

- **Interval:** bootstrap over matches (a match's outcomes and bets stay together), 4,000 resamples,
  seed 0, 95% percentile interval.
- **Realised return** per €1 staked is reported next to every CLV, with its interval. It is the
  check that does not depend on how the margin is removed, and it is far noisier.

## Reported without a decision

- The rule at other thresholds: 0, 2, 3, 5, 7 and 10 points. The best-looking threshold found here
  does not become a rule; that would need new matches.
- **The mirror rule:** €1 on every outcome the ensemble rates at least 5 points *below* the early
  market. If the models are a contrary indicator, this is where it shows.
- The rule at Bet365's early price and at the best early price, and the share of bets whose price
  was longer than the closing average.
- Every possible bet (all three outcomes of every match) at each price, as the no-skill baseline.
- Q1 and Q2 per league, per season, per outcome and by price (odds below 2, 2 to 4, above 4).
- Each of the three models alone, set B, and set A with XGBoost trained on all five leagues.
- The Q1 slope with the early probability as a second variable, to tell "the models know something"
  from "early prices drift in a direction anyone could see", such as favourites shortening.

## Known limitations

- **Timing.** The early price is a Friday or Tuesday afternoon snapshot. The site's posts go out
  about as early, but not at the same hour.
- **The average is not a bookmaker.** Nobody offers exactly the average price, and the best price
  assumes accounts everywhere and no stake limits.
- **Margin removal.** Removing the margin proportionally overstates outsiders' chances a little
  (the favourites note in the four-league report). The rule's picks lean towards outsiders, so their
  CLV is flattered. Realised return is the cross-check.
- **Taxes and limits.** Germany's 5.3% betting tax and bookmakers' stake limits are ignored. Both
  make real returns worse than these.
- **The bootstrap treats matches as independent.** Matches of one round share news, so the
  intervals are a little too narrow.
- **No xG outside Germany.** Set A tests the original models; the published ones are set B only.

## What happens next

`analysis/pipeline/evaluate_clv.py` applies these rules as written, and the report goes in
`analysis/backtest/clv/README.md`.
