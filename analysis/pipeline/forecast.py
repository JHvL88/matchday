"""Forecast fixtures with the three published models, fitted only on matches before a freeze date.

    python analysis/pipeline/forecast.py data/matches.csv out.json --freeze 2026-10-16 \
        --fixture 2026-10-17 Hamburg Stuttgart [--fixture ...] [--xg] [--warmup 800 --samples 800]

Same set-up as the backtest (backtest.py), so a live forecast is made the way the backtest graded them:
  Dixon-Coles  last eight seasons, time decay 0.0019; with --xg the pre-registered quarter-xG blend
  XGBoost      trained on earlier seasons only (2008 onwards), 30 features; with --xg plus 6 xG features
  Bayesian     six seasons plus the current one, half-season periods, NUTS on two chains
  Ensemble     equal-weight average of the three score grids
Team names as in the match table (football-data.co.uk spelling).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

DC_XI = 0.0019            # step 1 tuning (analysis/backtest/README.md)
DC_XG_WEIGHT = 0.25       # xG test tuning (analysis/backtest/xg/README.md)


def summary(M):
    """Home/draw/away, expected goals and the usual side markets from a score grid M[home, away]."""
    g = np.arange(M.shape[0])
    i, j = np.unravel_index(M.argmax(), M.shape)
    return dict(H=float(np.tril(M, -1).sum()), D=float(np.trace(M)), A=float(np.triu(M, 1).sum()),
                lh=float((M.sum(1) * g).sum()), la=float((M.sum(0) * g).sum()),
                over25=float(M[(g[:, None] + g[None, :]) > 2].sum()),
                btts=float(M[1:, 1:].sum()), mostLikely=dict(score=[int(i), int(j)], p=float(M[i, j])))


def fit_dc(df, freeze, season, use_xg):
    from bl_models import DixonColes
    hist = df[df.season >= season - 8]
    return DixonColes(xi=DC_XI, xg_weight=DC_XG_WEIGHT if use_xg else 0.0).fit(hist, freeze)


def xgb_rates(df, fixtures, season, use_xg):
    import xgboost as xgb
    from features import build_features, FEATURES, FEATURES_XG
    from backtest_utils import train_xgb_pair
    future = pd.DataFrame([dict(div="D1", date=f["date"], home=f["home"], away=f["away"], season=season,
                                hg=np.nan, ag=np.nan, hs=np.nan, as_=np.nan, hst=np.nan, ast=np.nan)
                           for f in fixtures])
    X = build_features(pd.concat([df, future], ignore_index=True), use_xg=use_xg)
    feats = FEATURES_XG if use_xg else FEATURES
    d1 = X[X["div"] == "D1"]
    pool = d1[(d1.season >= 2008) & (d1.h_n_prev >= 5) & (d1.a_n_prev >= 5) & d1.hg.notna()]
    models, rounds = train_xgb_pair(pool[pool.season < season], features=feats)
    out = []
    for f in fixtures:
        row = d1[(d1.date == f["date"]) & (d1.home == f["home"]) & (d1.away == f["away"]) & d1.hg.isna()]
        dm = xgb.DMatrix(row[feats])
        out.append((float(models["hg"].predict(dm)[0]), float(models["ag"].predict(dm)[0])))
    return out, rounds


def bayes_grids(df, fixtures, freeze, use_xg, warmup, samples):
    import bayes_model as bm
    bm.PERIODS_PER_SEASON = 2
    bm.USE_XG = use_xg
    ref = pd.Timestamp(freeze)
    mcmc, meta = bm.fit(df, ref.year - (ref.month < 7) - 6, ref, warmup=warmup, samples=samples,
                        chains=2, max_tree_depth=8)
    smp = {k: np.asarray(v) for k, v in mcmc.get_samples().items()}
    st = bm.reconstruct(smp, meta)
    div = int(np.sum(mcmc.get_extra_fields()["diverging"]))
    grids, shots = [], []
    for f in fixtures:
        grids.append(bm.predict_matrix(smp, st, meta, f["home"], f["away"], f["date"]))
        shots.append(shot_view(smp, st, meta, f["home"], f["away"], f["date"], bm))
    return grids, shots, div


def shot_view(smp, st, meta, home, away, date, bm):
    """Posterior means of expected shots on target and goals per shot on target (the model's two stages)."""
    tid, ref = meta["tid"], pd.Timestamp(date)
    season = ref.year - (ref.month < 7)
    p = min((season - meta["first_season"]) * bm.PERIODS_PER_SEASON + int(bm.period_of(ref.month)), meta["P"] - 1)
    s = min(season - meta["first_season"], meta["S"] - 1)
    h, a = tid[home], tid[away]
    al, be = smp["alpha"][:, 0], smp["beta"][:, 0]
    lam_h = np.exp(al + smp["home"] + st["att"][:, h, p] - st["def_"][:, a, p])
    lam_a = np.exp(al + st["att"][:, a, p] - st["def_"][:, h, p])
    ph = 1 / (1 + np.exp(-(be + smp["gamma_home"] + st["fin"][:, h, s] - st["keep"][:, a, s])))
    pa = 1 / (1 + np.exp(-(be + st["fin"][:, a, s] - st["keep"][:, h, s])))
    return dict(sot=[float(lam_h.mean()), float(lam_a.mean())], conv=[float(ph.mean()), float(pa.mean())])


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv=None):
    import numpyro
    numpyro.set_host_device_count(2)      # before JAX starts, so the two chains run in parallel
    from bl_models import score_matrix
    ap = argparse.ArgumentParser()
    ap.add_argument("matches")
    ap.add_argument("out")
    ap.add_argument("--freeze", required=True, help="use only matches strictly before this date (YYYY-MM-DD)")
    ap.add_argument("--fixture", nargs=3, action="append", required=True, metavar=("DATE", "HOME", "AWAY"))
    ap.add_argument("--xg", action="store_true", help="the xG versions adopted in October 2026")
    ap.add_argument("--warmup", type=int, default=800)
    ap.add_argument("--samples", type=int, default=800)
    a = ap.parse_args(argv)
    t0 = time.time()
    df = pd.read_csv(a.matches, parse_dates=["date"])
    freeze = pd.Timestamp(a.freeze)
    df = df[df.date < freeze].reset_index(drop=True)
    if a.xg and "hxg" not in df:
        raise SystemExit("--xg needs a match table with hxg/axg (build_matches.py --understat)")
    fixtures = [dict(date=pd.Timestamp(d), home=h, away=w) for d, h, w in a.fixture]
    teams = set(df.home) | set(df.away)
    missing = sorted({t for f in fixtures for t in (f["home"], f["away"])} - teams)
    if missing:
        raise SystemExit(f"unknown team names: {missing}")
    season = fixtures[0]["date"].year - (fixtures[0]["date"].month < 7)

    dc = fit_dc(df, freeze, season, a.xg)
    xr, rounds = xgb_rates(df, fixtures, season, a.xg)
    bg, shots, divergences = bayes_grids(df, fixtures, freeze, a.xg, a.warmup, a.samples)

    out = []
    for f, (xlh, xla), B, sv in zip(fixtures, xr, bg, shots):
        lh, la = dc.rates(f["home"], f["away"])
        grids = dict(dc=score_matrix(lh, la, dc.rho), bay=B, xgb=score_matrix(xlh, xla, dc.rho))
        grids["ens"] = (grids["dc"] + grids["bay"] + grids["xgb"]) / 3
        rec = dict(date=f["date"].strftime("%Y-%m-%d"), home=f["home"], away=f["away"],
                   models={k: summary(M) for k, M in grids.items()},
                   bayesShots=sv, grid=np.round(grids["ens"], 6).tolist())
        out.append(rec)
        e = rec["models"]["ens"]
        print(f"{f['home']} v {f['away']}: ensemble {e['H']:.3f} / {e['D']:.3f} / {e['A']:.3f}, "
              f"xG {e['lh']:.2f}-{e['la']:.2f}, most likely {e['mostLikely']['score']}", flush=True)
        for k in ["dc", "bay", "xgb"]:
            m = rec["models"][k]
            print(f"   {k:4s} {m['H']:.3f} / {m['D']:.3f} / {m['A']:.3f}")

    try:
        code = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or None
    except OSError:
        code = None
    res = dict(created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), freeze=a.freeze,
               models="xG versions" if a.xg else "pre-xG versions", xg=a.xg,
               config=dict(dc_xi=DC_XI, dc_xg_weight=DC_XG_WEIGHT if a.xg else 0.0, dc_rho=dc.rho,
                           xgb_rounds=rounds, bayes_warmup=a.warmup, bayes_samples=a.samples, bayes_chains=2,
                           bayes_divergences=divergences),
               inputs=dict(matches_sha256=sha256(a.matches), matches_used=int(len(df)),
                           last_match=df.date.max().strftime("%Y-%m-%d"), code_commit=code),
               seconds=round(time.time() - t0), fixtures=out)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print(f"saved -> {a.out} ({res['seconds']}s, {divergences} divergences)")


if __name__ == "__main__":
    main()
