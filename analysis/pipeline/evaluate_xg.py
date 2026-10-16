"""Grade the pre-registered xG test (analysis/backtest/xg/PREREGISTRATION.md).

    python analysis/pipeline/evaluate_xg.py data/matches.csv <current results> <xG results> out.json

Differences are always new minus current: negative means the new version forecasts better.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

from bl_models import logloss, rps
from evaluate import cols, disagreement, load

N_BOOT, SEED = 4000, 0


def paired(a, b, y):
    """Mean RPS difference b - a with a paired bootstrap 95% interval."""
    d = rps(b, y) - rps(a, y)
    boot = np.random.default_rng(SEED).choice(d, (N_BOOT, len(d))).mean(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(diff=float(d.mean()), low=float(lo), high=float(hi), n=int(len(d)),
                better_share=float((d < 0).mean()), worse_share=float((d > 0).mean()))


def rule(p):
    """Pre-registered rule: adopt only if the difference and its whole interval are below zero."""
    return p["diff"] < 0 and p["high"] < 0


def scores(df, m):
    p, y = df[cols(m)].values, df.y.values
    return dict(rps=float(rps(p, y).mean()), logLoss=float(logloss(p, y).mean()), topPick=float((p.argmax(1) == y).mean()))


def main(matches, current_dir, xg_dir, out):
    cur = load(matches, current_dir).set_index("key")
    new = load(matches, xg_dir).set_index("key").loc[cur.index]
    y = cur.y.values
    both = cur.copy()
    for m in ["dc", "bay", "xgb", "ens", "two"]:
        both[cols(f"{m}x")] = new[cols(m)].values
    for suffix in ("", "x"):   # Dixon-Coles + Bayesian, equal weights (for Q2)
        for k in "HDA":
            both[f"two_db{suffix}_{k}"] = (both[f"dc{suffix}_{k}"] + both[f"bay{suffix}_{k}"]) / 2
    res = dict(matches=int(len(both)), seasons=[int(both.season.min()), int(both.season.max())])

    # Q1: the ensembles
    q1 = paired(both[cols("ens")].values, both[cols("ensx")].values, y)
    res["q1"] = dict(comparison="Ensemble-xG minus Ensemble", **q1, adopt_xg=rule(q1))
    chosen = "x" if res["q1"]["adopt_xg"] else ""

    # Q2: two-model (Dixon-Coles + Bayesian) minus three-model ensemble, on the chosen model set
    three, two = cols(f"ens{chosen}"), cols(f"two_db{chosen}")
    q2 = paired(both[three].values, both[two].values, y)
    res["q2"] = dict(comparison=f"(Dixon-Coles + Bayesian) minus all three{' (xG versions)' if chosen else ''}",
                     **q2, drop_xgboost=rule(q2))

    # Reported without a decision
    res["components"] = {m: paired(both[cols(m)].values, both[cols(f"{m}x")].values, y) for m in ["dc", "bay", "xgb"]}
    res["scores"] = {name: scores(both, m) for name, m in
                     [("market", "avgc"), ("ensemble", "ens"), ("ensemble_xg", "ensx"), ("dixon_coles", "dc"),
                      ("dixon_coles_xg", "dcx"), ("bayesian", "bay"), ("bayesian_xg", "bayx"), ("xgboost", "xgb"),
                      ("xgboost_xg", "xgbx"), ("two_model", "two_db"), ("two_model_xg", "two_dbx")]}
    res["per_season"] = [dict(season=int(s), **paired(g[cols("ens")].values, g[cols("ensx")].values, g.y.values))
                         for s, g in both.groupby("season")]
    res["gap_to_market"] = {k: paired(both[cols("avgc")].values, both[cols(m)].values, y) for k, m in
                            [("ensemble", "ens"), ("ensemble_xg", "ensx")]}
    tmp = both.copy()
    for k in "HDA":
        for m in ["dc", "bay", "xgb"]:
            tmp[f"{m}_{k}"] = both[f"{m}x_{k}"]
    res["disagreement_xg"] = disagreement(tmp, ["dc", "bay", "xgb"])
    meta = json.load(open(os.path.join(xg_dir, "oos_dc.json")))
    res["dc_xg_weight"] = meta.get("dc_xg_weight")
    res["dc_xg_weight_scores"] = meta.get("dc_xg_weight_scores")
    json.dump(res, open(out, "w"), indent=1)

    print(f"{res['matches']} matches, {res['seasons'][0]}/{res['seasons'][0] % 100 + 1:02d} to {res['seasons'][1]}/{res['seasons'][1] % 100 + 1:02d}")
    print(f"Q1 {res['q1']['comparison']}: {q1['diff']:+.5f} (95% {q1['low']:+.5f} to {q1['high']:+.5f}) -> "
          f"{'ADOPT xG' if res['q1']['adopt_xg'] else 'keep current models'}")
    print(f"Q2 {res['q2']['comparison']}: {q2['diff']:+.5f} (95% {q2['low']:+.5f} to {q2['high']:+.5f}) -> "
          f"{'DROP XGBoost' if res['q2']['drop_xgboost'] else 'keep XGBoost'}")
    for m, p in res["components"].items():
        print(f"  {m}-xG minus {m}: {p['diff']:+.5f} ({p['low']:+.5f} to {p['high']:+.5f})")
    for k, s in res["scores"].items():
        print(f"  {k:16s} RPS {s['rps']:.4f}  log loss {s['logLoss']:.4f}  top pick {s['topPick']:.3f}")
    for s in res["per_season"]:
        print(f"  {s['season']}: {s['diff']:+.5f} ({s['low']:+.5f} to {s['high']:+.5f})")
    print("  Dixon-Coles xG weight:", res["dc_xg_weight"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
