"""Matchday 6 2026/27, Bayern v Leipzig: fit the three published (xG) models and freeze the forecast.

    python analysis/2026-27-md6-bayern-leipzig/post_model.py matches.csv out/

Same models and settings as analysis/pipeline/forecast.py (it imports them from there), so the
forecast is made exactly the way the backtest graded them. Writes
    out/forecast.json    the frozen forecast, same layout as forecast.py's output
    out/internals.pkl    what the charts need on top: Dixon-Coles ratings, the Bayesian posterior,
                         XGBoost's feature values and SHAP contributions (not committed: ~60 MB)
"""
import os
import pickle
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import numpy as np
import pandas as pd

import forecast as fc

FREEZE = "2026-10-17"                                  # results before matchday 6's Saturday
FIXTURE = dict(date=pd.Timestamp("2026-10-17"), home="Bayern Munich", away="RB Leipzig")
WARMUP, SAMPLES = 800, 800


def xgb_part(df, season):
    """forecast.xgb_rates, keeping the boosters and the fixture's feature row for the SHAP chart."""
    import xgboost as xgb
    from features import build_features, FEATURES_XG
    from backtest_utils import train_xgb_pair
    f = FIXTURE
    future = pd.DataFrame([dict(div="D1", date=f["date"], home=f["home"], away=f["away"], season=season,
                                hg=np.nan, ag=np.nan, hs=np.nan, as_=np.nan, hst=np.nan, ast=np.nan)])
    X = build_features(pd.concat([df, future], ignore_index=True), use_xg=True)
    d1 = X[X["div"] == "D1"]
    pool = d1[(d1.season >= 2008) & (d1.h_n_prev >= 5) & (d1.a_n_prev >= 5) & d1.hg.notna()]
    models, rounds = train_xgb_pair(pool[pool.season < season], features=FEATURES_XG)
    row = d1[(d1.date == f["date"]) & (d1.home == f["home"]) & (d1.away == f["away"]) & d1.hg.isna()]
    dm = xgb.DMatrix(row[FEATURES_XG])
    rates = (float(models["hg"].predict(dm)[0]), float(models["ag"].predict(dm)[0]))
    shap = {t: models[t].predict(dm, pred_contribs=True)[0] for t in ["hg", "ag"]}   # log-scale, last = bias
    return rates, rounds, dict(features=FEATURES_XG, row=row[FEATURES_XG].iloc[0].to_dict(), shap=shap)


def bayes_part(df):
    """forecast.bayes_grids, keeping the posterior."""
    import bayes_model as bm
    bm.PERIODS_PER_SEASON = 2
    bm.USE_XG = True
    ref = pd.Timestamp(FREEZE)
    mcmc, meta = bm.fit(df, ref.year - (ref.month < 7) - 6, ref, warmup=WARMUP, samples=SAMPLES,
                        chains=2, max_tree_depth=8)
    smp = {k: np.asarray(v) for k, v in mcmc.get_samples().items()}
    st = bm.reconstruct(smp, meta)
    div = int(np.sum(mcmc.get_extra_fields()["diverging"]))
    f = FIXTURE
    grid = bm.predict_matrix(smp, st, meta, f["home"], f["away"], f["date"])
    shots = fc.shot_view(smp, st, meta, f["home"], f["away"], f["date"], bm)
    keep = ["alpha", "beta", "home", "gamma_home", "phi"]
    return grid, shots, div, dict(samples={k: smp[k] for k in keep if k in smp}, states=st, meta=meta)


def rhat(x):
    """Split-chain R-hat for a (chains, draws) array."""
    c, n = x.shape
    half = n // 2
    s = np.concatenate([x[:, :half], x[:, half:2 * half]])
    w = s.var(1, ddof=1).mean()
    b = half * s.mean(1).var(ddof=1)
    return float(np.sqrt(((half - 1) / half * w + b / half) / w))


def main():
    import numpyro
    numpyro.set_host_device_count(2)
    from bl_models import score_matrix
    matches, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    df = pd.read_csv(matches, parse_dates=["date"])
    df = df[df.date < pd.Timestamp(FREEZE)].reset_index(drop=True)
    season = 2026

    dc = fc.fit_dc(df, pd.Timestamp(FREEZE), season, True)
    (xlh, xla), rounds, xgb_info = xgb_part(df, season)
    B, shots, divergences, bay_info = bayes_part(df)

    f = FIXTURE
    lh, la = dc.rates(f["home"], f["away"])
    grids = dict(dc=score_matrix(lh, la, dc.rho), bay=B, xgb=score_matrix(xlh, xla, dc.rho))
    grids["ens"] = (grids["dc"] + grids["bay"] + grids["xgb"]) / 3          # pre-registered equal weights
    rec = dict(date=f["date"].strftime("%Y-%m-%d"), home=f["home"], away=f["away"],
               models={k: fc.summary(M) for k, M in grids.items()}, bayesShots=shots,
               grid=np.round(grids["ens"], 6).tolist())
    e = rec["models"]["ens"]
    print(f"{f['home']} v {f['away']}: ensemble {e['H']:.3f} / {e['D']:.3f} / {e['A']:.3f}, "
          f"xG {e['lh']:.2f}-{e['la']:.2f}, most likely {e['mostLikely']['score']}", flush=True)
    for k in ["dc", "bay", "xgb"]:
        m = rec["models"][k]
        print(f"   {k:4s} {m['H']:.3f} / {m['D']:.3f} / {m['A']:.3f}   xG {m['lh']:.2f}-{m['la']:.2f}")

    # convergence: R-hat on the global parameters (two chains of SAMPLES draws each)
    rh = {}
    for k, v in bay_info["samples"].items():
        v = v.reshape(len(v), -1)
        for j in range(v.shape[1]):
            rh[f"{k}[{j}]"] = rhat(v[:, j].reshape(2, -1))
    st, meta = bay_info["states"], bay_info["meta"]
    for k in ["att", "def_", "fin", "keep"]:                # every club's current strengths too
        last = st[k][:, :, -1]
        for t in range(last.shape[1]):
            rh[f"{k}[{t},last]"] = rhat(last[:, t].reshape(2, -1))
    code = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    res = dict(created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), freeze=FREEZE,
               models="xG versions", xg=True,
               config=dict(dc_xi=fc.DC_XI, dc_xg_weight=fc.DC_XG_WEIGHT, dc_rho=dc.rho, xgb_rounds=rounds,
                           bayes_warmup=WARMUP, bayes_samples=SAMPLES, bayes_chains=2,
                           bayes_divergences=divergences, bayes_max_rhat=max(rh.values())),
               inputs=dict(matches_sha256=fc.sha256(matches), matches_used=int(len(df)),
                           last_match=df.date.max().strftime("%Y-%m-%d"), code_commit=code),
               seconds=round(time.time() - t0), fixtures=[rec])
    import json
    json.dump(res, open(os.path.join(out, "forecast.json"), "w"), indent=1)
    pickle.dump(dict(grids=grids, dc=dict(att=dc.att, de=dc.de, mu=dc.mu, home=dc.home, rho=dc.rho),
                     xgb=xgb_info, bayes=bay_info), open(os.path.join(out, "internals.pkl"), "wb"))
    print(f"saved -> {out} ({res['seconds']}s, {divergences} divergences, max R-hat {max(rh.values()):.3f})")


if __name__ == "__main__":
    main()
