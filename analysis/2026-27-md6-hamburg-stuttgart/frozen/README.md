# Frozen before kick-off

The models switched to their xG versions late on Friday 16 October 2026 (merged 22:50 CEST), after the pre-registered test ([`analysis/backtest/xg/`](../../backtest/xg/)). That was after this post was published. These two forecasts were made that same night, before Hamburg v Stuttgart kicked off, so the full-time review can grade them honestly:

| File | Models | Hamburg | Draw | Stuttgart |
|---|---|---|---|---|
| `md6_forecast_xg.json` | xG versions (now published) | 30.5% | 23.2% | 46.3% |
| `md6_forecast_pre_xg.json` | the versions the post used, rerun by the shared pipeline | 31.7% | 23.3% | 45.0% |
| (the post) | as published on 15 October | 32% | 24% | 44% |

Both runs used the same match table and saw only results before 16 October (matchdays 1–5, last match 11 October), the same information as the post. Commands:

```
python analysis/pipeline/build_matches.py <source-data> matches.csv --understat <understat>
python analysis/pipeline/forecast.py matches.csv md6_forecast_xg.json --xg --freeze 2026-10-16 --fixture 2026-10-17 Hamburg Stuttgart
python analysis/pipeline/forecast.py matches.csv md6_forecast_pre_xg.json --freeze 2026-10-16 --fixture 2026-10-17 Hamburg Stuttgart
```

Source data: `source-data` commit `e47f4cf`; Understat: data-repo commit `0887cd1`; match table SHA-256 `db628157…5a17`; code commit `ba6d516`. The rerun of the old models lands within about a point of the published numbers, as expected: the Bayesian model draws random samples, and the pipeline reads football-data.co.uk directly instead of the mirror the post used.

The forecast that gets graded on the Track record page is still the published one.
