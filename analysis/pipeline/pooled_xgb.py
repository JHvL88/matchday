"""XGBoost trained on several leagues at once, walk-forward (analysis/backtest/leagues/PREREGISTRATION.md).

The published XGBoost learns from the Bundesliga's own past: about 5,000 matches for 30 features.
This variant learns from every league's top flight, five times the matches, and forecasts each
league with the one shared model. The features are the same and are computed inside each league
(own Elo, own form), so a match looks the same to both models; only the training set differs.

    python analysis/pipeline/pooled_xgb.py out/oos_xgb_pooled.csv --seasons 2019 2026 \
        --table GER data/GER.csv --table ENG data/ENG.csv ... [--xg]

Output: one row per top-flight match of the test seasons with expected goals from
  xgbp_*  the pooled model with a league indicator per league (the pre-registered variant)
  xgbq_*  the pooled model without the indicators (reported, no decision)
  xgbo_*  each league's own model, trained on that league alone (the published set-up), refitted here
          so the comparison runs on one machine
With --xg the six xG form features are added; leagues without xG leave them missing.

--publish GER out/oos_xgb.csv also writes one league's pooled forecasts in backtest.py's format
(key, xgb_lh, xgb_la), which is how the published xG backtest gets its XGBoost since November 2026.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from leagues import LEAGUES

FIRST_TRAIN_SEASON, MIN_PREV = 2008, 5      # as in backtest.run_xgb
INDICATORS = [f"lg_{name}" for name in LEAGUES]


def top_flight_features(df, league, use_xg):
    """Top-flight rows of one league's matches with the published features and league indicators."""
    from features import build_features
    df = df.copy()
    if use_xg and "hxg" not in df:
        df["hxg"], df["axg"] = np.nan, np.nan          # no xG for this league: left to XGBoost's missing-value handling
    X = build_features(df, use_xg=use_xg)
    X["key"] = X.date.dt.strftime("%Y-%m-%d") + "|" + X.home + "|" + X.away
    X["league"] = league
    for name in LEAGUES:
        X[f"lg_{name}"] = int(name == league)
    return X[X["div"] == "D1"]


def league_features(path, league, use_xg):
    from backtest import load
    return top_flight_features(load(path).drop(columns=["key"]), league, use_xg)


def training_pool(top):
    """The rows XGBoost may learn from: played, 2008 on, both teams with five earlier matches."""
    return top[(top.season >= FIRST_TRAIN_SEASON) & (top.h_n_prev >= MIN_PREV) & (top.a_n_prev >= MIN_PREV) & top.hg.notna()]


def walk_forward(tables, seasons, use_xg=False, log=print):
    import xgboost as xgb
    from backtest_utils import train_xgb_pair
    from features import FEATURES, FEATURES_XG
    feats = FEATURES_XG if use_xg else FEATURES
    top = pd.concat([league_features(path, league, use_xg) for league, path in tables.items()], ignore_index=True)
    pool = training_pool(top)
    variants = {"xgbp": (None, feats + INDICATORS), "xgbq": (None, feats)}
    variants.update({f"own:{league}": (league, feats) for league in tables})
    rows, rounds = [], {}
    for s in seasons:
        test = top[top.season == s]
        if test.empty:
            continue
        out = test[["league", "key"]].copy()
        for name, (league, cols) in variants.items():
            train = pool[pool.season < s] if league is None else pool[(pool.season < s) & (pool.league == league)]
            target = test if league is None else test[test.league == league]
            if target.empty:
                continue
            models, best = train_xgb_pair(train, features=cols)
            rounds[f"{name}:{s}"] = best
            prefix = "xgbo" if league else name
            out.loc[target.index, f"{prefix}_lh"] = models["hg"].predict(xgb.DMatrix(target[cols]))
            out.loc[target.index, f"{prefix}_la"] = models["ag"].predict(xgb.DMatrix(target[cols]))
            log(f"{name} season {s}: trained on {len(train)} matches, {len(target)} forecast, rounds {best}")
        rows.append(out)
    return pd.concat(rows, ignore_index=True), rounds, len(pool)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--table", nargs=2, action="append", required=True, metavar=("LEAGUE", "CSV"))
    ap.add_argument("--seasons", nargs=2, type=int, required=True, metavar=("FIRST", "LAST"))
    ap.add_argument("--xg", action="store_true", help="add the six xG form features (missing where a league has no xG)")
    ap.add_argument("--publish", nargs=2, metavar=("LEAGUE", "CSV"),
                    help="also write this league's pooled forecasts in backtest.py's format (key, xgb_lh, xgb_la)")
    a = ap.parse_args(argv)
    tables = {league.upper(): path for league, path in a.table}
    unknown = [name for name in tables if name not in LEAGUES]
    if unknown:
        raise SystemExit(f"unknown league(s) {unknown}")
    t = time.time()
    seasons = list(range(a.seasons[0], a.seasons[1] + 1))
    out, rounds, n_pool = walk_forward(tables, seasons, a.xg, log=lambda m: print(m, flush=True))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.to_csv(a.out, index=False, float_format="%.6f")
    meta = dict(model="pooled xgboost", xg=a.xg, leagues=list(tables), seasons=seasons, pool_matches=n_pool,
                rounds=rounds, seconds=round(time.time() - t))
    json.dump(meta, open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
    print(f"saved {len(out)} rows -> {a.out} ({meta['seconds']}s)")
    if a.publish:
        league, path = a.publish[0].upper(), a.publish[1]
        one = out[out.league == league].rename(columns={"xgbp_lh": "xgb_lh", "xgbp_la": "xgb_la"})[["key", "xgb_lh", "xgb_la"]]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        one.to_csv(path, index=False, float_format="%.6f")
        json.dump(dict(model="xgb", xg=a.xg, seasons=seasons, pooled_over=list(tables), pool_matches=n_pool,
                       xgb_rounds={k.split(":")[1]: v for k, v in rounds.items() if k.startswith("xgbp:")},
                       seconds=meta["seconds"]), open(os.path.splitext(path)[0] + ".json", "w"), indent=1)
        print(f"saved {len(one)} rows -> {path} ({league}, pooled over {', '.join(tables)})")


if __name__ == "__main__":
    main()
