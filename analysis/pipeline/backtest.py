"""Walk-forward backtest of the three published models against the closing market.

Every forecast only uses matches played before it, exactly as a live forecast would.
  dc     Dixon-Coles, refit every week; time-decay xi tuned on the season before the window
  xgb    XGBoost-Poisson pair, refit every season
  bayes  Bayesian shots-to-goals model (NUTS), refit every calendar month

    python analysis/pipeline/backtest.py dc    data/matches.csv out/oos_dc.csv    --seasons 2019 2026
    python analysis/pipeline/backtest.py xgb   data/matches.csv out/oos_xgb.csv   --seasons 2019 2026
    python analysis/pipeline/backtest.py bayes data/matches.csv out/oos_bay_2019.csv --seasons 2019 2019

Output: one row per Bundesliga match with the model's home/draw/away probabilities and expected goals.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

KEY_COLS = ["date", "season", "home", "away", "hg", "ag"]
XI_GRID = [0.0012, 0.0019, 0.0028, 0.004]
# xG variants (analysis/backtest/xg/PREREGISTRATION.md): time decay fixed at the step 1 choice,
# the goals/xG blend tuned on the season before the window.
XG_XI = 0.0019
XG_WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]


def load(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["key"] = df.date.dt.strftime("%Y-%m-%d") + "|" + df.home + "|" + df.away
    return df


def dc_walk_forward(df, d1, xi, seasons, xg_weight=0.0):
    from bl_models import DixonColes, score_matrix, outcome_probs
    rows = []
    for s in seasons:
        hist = df[df.season >= s - 8]
        test = d1[d1.season == s]
        for _, g in test.groupby(test.date.dt.to_period("W-MON")):     # Tue..Mon blocks
            m = DixonColes(xi=xi, xg_weight=xg_weight).fit(hist, g.date.min())
            for r in g.itertuples():
                lh, la = m.rates(r.home, r.away)
                p = outcome_probs(score_matrix(lh, la, m.rho))
                rows.append(dict(key=r.key, dc_H=p[0], dc_D=p[1], dc_A=p[2], dc_lh=lh, dc_la=la, dc_rho=m.rho))
        print(f"DC season {s}: {len(test)} matches", flush=True)
    return pd.DataFrame(rows)


def run_dc(df, seasons, meta):
    from bl_models import rps
    d1 = df[df["div"] == "D1"]
    tune_season = seasons[0] - 1
    scores = {}
    for xi in XI_GRID:
        p = dc_walk_forward(df, d1, xi, [tune_season])
        y = d1.set_index("key").loc[p.key]
        yv = np.where(y.hg > y.ag, 0, np.where(y.hg == y.ag, 1, 2))
        scores[xi] = float(rps(p[["dc_H", "dc_D", "dc_A"]].values, yv).mean())
        print(f"  xi={xi}: RPS {tune_season}/{tune_season % 100 + 1:02d} = {scores[xi]:.4f}", flush=True)
    xi = min(scores, key=scores.get)
    meta.update(dc_tune_season=tune_season, dc_xi_scores=scores, dc_xi=xi)
    return dc_walk_forward(df, d1, xi, seasons)


def run_dc_xg(df, seasons, meta):
    from bl_models import rps
    d1 = df[df["div"] == "D1"]
    tune_season = seasons[0] - 1
    scores = {}
    for w in XG_WEIGHTS:
        p = dc_walk_forward(df, d1, XG_XI, [tune_season], xg_weight=w)
        y = d1.set_index("key").loc[p.key]
        yv = np.where(y.hg > y.ag, 0, np.where(y.hg == y.ag, 1, 2))
        scores[w] = float(rps(p[["dc_H", "dc_D", "dc_A"]].values, yv).mean())
        print(f"  xG weight {w}: RPS {tune_season}/{tune_season % 100 + 1:02d} = {scores[w]:.5f}", flush=True)
    w = min(scores, key=scores.get)
    meta.update(dc_tune_season=tune_season, dc_xi=XG_XI, dc_xg_weight_scores=scores, dc_xg_weight=w)
    return dc_walk_forward(df, d1, XG_XI, seasons, xg_weight=w)


def run_xgb(df, seasons, meta, use_xg=False):
    import xgboost as xgb
    from features import build_features, FEATURES, FEATURES_XG
    from backtest_utils import train_xgb_pair
    X = build_features(df.drop(columns=["key"]), use_xg=use_xg)
    feats = FEATURES_XG if use_xg else FEATURES
    X["key"] = X.date.dt.strftime("%Y-%m-%d") + "|" + X.home + "|" + X.away
    d1 = X[X["div"] == "D1"]
    pool = d1[(d1.season >= 2008) & (d1.h_n_prev >= 5) & (d1.a_n_prev >= 5)]
    rows, rounds = [], {}
    for s in seasons:
        models, best = train_xgb_pair(pool[pool.season < s], features=feats)
        rounds[s] = best
        test = d1[d1.season == s]
        lh = models["hg"].predict(xgb.DMatrix(test[feats]))
        la = models["ag"].predict(xgb.DMatrix(test[feats]))
        # H/D/A come later from the score grid with Dixon-Coles' rho, as in the published posts
        rows += [dict(key=k, xgb_lh=float(a), xgb_la=float(b)) for k, a, b in zip(test.key, lh, la)]
        print(f"XGB season {s}: {len(test)} matches, rounds {best}", flush=True)
    meta.update(xgb_rounds={str(k): v for k, v in rounds.items()})
    return pd.DataFrame(rows)


def run_bayes(df, seasons, meta, warmup, samples, use_xg=False):
    import numpyro
    numpyro.set_host_device_count(2)
    import bayes_model as bm
    from bl_models import outcome_probs
    bm.PERIODS_PER_SEASON = 2
    bm.USE_XG = use_xg
    base = df.drop(columns=["key"])
    d1 = df[(df["div"] == "D1") & df.season.isin(seasons)].sort_values("date")
    rows, fits = [], []
    for month, g in d1.groupby(d1.date.dt.to_period("M")):
        ref = g.date.min().normalize()
        t = time.time()
        mcmc, m = bm.fit(base, ref.year - (ref.month < 7) - 6, ref, warmup=warmup, samples=samples,
                         chains=2, max_tree_depth=8)
        smp = {k: np.asarray(v) for k, v in mcmc.get_samples().items()}
        st = bm.reconstruct(smp, m)
        ex = mcmc.get_extra_fields()
        for r in g.itertuples():
            M = bm.predict_matrix(smp, st, m, r.home, r.away, r.date)
            p = outcome_probs(M)
            lh = float((M.sum(1) * np.arange(M.shape[0])).sum())
            la = float((M.sum(0) * np.arange(M.shape[1])).sum())
            rows.append(dict(key=r.key, bay_H=p[0], bay_D=p[1], bay_A=p[2], bay_lh=lh, bay_la=la))
        fits.append(dict(month=str(month), matches=len(g), seconds=round(time.time() - t),
                         divergences=int(np.sum(ex["diverging"]))))
        print(f"Bayes {month}: {len(g)} matches, {fits[-1]['seconds']}s, {fits[-1]['divergences']} divergences", flush=True)
    meta.update(bayes_fits=fits, bayes_warmup=warmup, bayes_samples=samples)
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["dc", "xgb", "bayes"])
    ap.add_argument("matches")
    ap.add_argument("out")
    ap.add_argument("--seasons", nargs=2, type=int, required=True, metavar=("FIRST", "LAST"))
    ap.add_argument("--warmup", type=int, default=250)
    ap.add_argument("--samples", type=int, default=250)
    ap.add_argument("--xg", action="store_true", help="the pre-registered xG variant (needs hxg/axg columns)")
    a = ap.parse_args(argv)
    df = load(a.matches)
    seasons = list(range(a.seasons[0], a.seasons[1] + 1))
    meta = dict(model=a.model, xg=a.xg, seasons=seasons, matches_file=os.path.basename(a.matches))
    if a.xg and "hxg" not in df:
        raise SystemExit("--xg needs a match table with hxg/axg (build_matches.py --understat)")
    t = time.time()
    if a.model == "dc":
        out = run_dc_xg(df, seasons, meta) if a.xg else run_dc(df, seasons, meta)
    elif a.model == "xgb":
        out = run_xgb(df, seasons, meta, use_xg=a.xg)
    else:
        out = run_bayes(df, seasons, meta, a.warmup, a.samples, use_xg=a.xg)
    meta["seconds"] = round(time.time() - t)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.to_csv(a.out, index=False, float_format="%.6f")
    json.dump(meta, open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
    print(f"saved {len(out)} rows -> {a.out} ({meta['seconds']}s)")


if __name__ == "__main__":
    main()
