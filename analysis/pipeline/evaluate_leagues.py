"""Grade the pre-registered four-league test (analysis/backtest/leagues/PREREGISTRATION.md).

    python analysis/pipeline/evaluate_leagues.py <tables dir> <leagues results dir> out.json \
        [--xg-table GER_xg.csv --xg-results <xg results dir>]

<tables dir> holds one match table per league (GER.csv, ENG.csv, ...; build_matches.py --league),
<leagues results dir> is leagues/ on the backtest-results branch. With --xg-table and --xg-results
(the Bundesliga's table with xG and the published xG predictions) the Q2 and Q3 rules are applied.

Differences are new minus current, or model minus market: negative means the first one is better.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from bl_models import outcome_probs, rps, score_matrix
from evaluate import cols, disagreement, load
from evaluate_xg import N_BOOT, SEED, paired, rule, scores
from leagues import HOME, LEAGUES

NEW = [name for name in LEAGUES if name != HOME]
NOISE = 0.0001          # pre-registered: smaller differences aren't read as real
Q1_RANGE = (0.003, 0.008)


def grid_probs(lh, la, rho):
    """Home/draw/away from two goal rates and Dixon-Coles' low-score correction, as in the published forecasts."""
    return np.array([outcome_probs(score_matrix(a, b, r)) for a, b, r in zip(lh, la, rho)])


def with_pooled(o, pooled, league, tags=("xgbp", "xgbq", "xgbo")):
    """Add the pooled job's XGBoost variants (and the ensembles built on them) to one league's forecasts."""
    p = pooled[pooled.league == league].drop(columns="league")
    o = o.merge(p, on="key", how="left")
    for tag in tags:
        o[cols(tag)] = grid_probs(o[f"{tag}_lh"], o[f"{tag}_la"], o.dc_rho)
        o[cols(f"ens_{tag}")] = (o[cols("dc")].values + o[cols("bay")].values + o[cols(tag)].values) / 3
    o[cols("two_db")] = (o[cols("dc")].values + o[cols("bay")].values) / 2
    return o


def diff(o, a, b):
    """b minus a on the rows of o."""
    return paired(o[cols(a)].values, o[cols(b)].values, o.y.values)


def block(o):
    """Everything reported for one league or one group of leagues."""
    out = dict(matches=int(len(o)),
               scores={name: scores(o, m) for name, m in [("market", "avgc"), ("ensemble", "ens"), ("dixon_coles", "dc"),
                                                          ("bayesian", "bay"), ("xgboost", "xgb"), ("xgboost_pooled", "xgbp"),
                                                          ("two_model", "two_db")]},
               gap_to_market=diff(o, "avgc", "ens"),
               models_to_market={m: diff(o, "avgc", m) for m in ["dc", "bay", "xgb", "xgbp"]},
               pooled_minus_own=diff(o, "xgbo", "xgbp"),
               pooled_minus_own_ensemble=diff(o, "ens_xgbo", "ens_xgbp"),
               pooled_plain_minus_own=diff(o, "xgbo", "xgbq"),
               two_minus_three=diff(o, "ens", "two_db"),
               own_refit_minus_backtest=diff(o, "xgb", "xgbo"))
    out["uniform_rps"] = float(rps(np.full((len(o), 3), 1 / 3), o.y.values).mean())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tables")
    ap.add_argument("results")
    ap.add_argument("out")
    ap.add_argument("--xg-table", help="the Bundesliga's match table with xG (build_matches.py --understat)")
    ap.add_argument("--xg-results", help="the published xG predictions (xg/ on backtest-results)")
    a = ap.parse_args(argv)

    pooled = pd.read_csv(os.path.join(a.results, "pooled", "oos_xgb_pooled.csv"))
    per, dropped, meta = {}, {}, {}
    for league in LEAGUES:
        o = load(os.path.join(a.tables, f"{league}.csv"), os.path.join(a.results, league))
        o = with_pooled(o, pooled, league)
        full = o.dropna(subset=cols("bay") + cols("xgbp") + cols("avgc"))
        dropped[league] = int(len(o) - len(full))
        full = full.assign(league=league)
        per[league] = full
        meta[league] = json.load(open(os.path.join(a.results, league, "oos_dc.json")))
    everything = pd.concat(per.values(), ignore_index=True)
    new = everything[everything.league.isin(NEW)]

    res = dict(matches=int(len(everything)), without_all_three_models=dropped,
               seasons=[int(everything.season.min()), int(everything.season.max())],
               last_match={k: f"{v.date.max():%Y-%m-%d}" for k, v in per.items()},
               bootstrap=dict(resamples=N_BOOT, seed=SEED))
    res["leagues"] = {}
    for league, o in per.items():
        b = block(o)
        b.update(name=LEAGUES[league][2], dc_xi=meta[league].get("dc_xi"), dc_xi_scores=meta[league].get("dc_xi_scores"),
                 per_season=[dict(season=int(s), **diff(g, "avgc", "ens")) for s, g in o.groupby("season")],
                 disagreement=disagreement(o, ["dc", "bay", "xgb"]),
                 goals_per_match=float((o.hg + o.ag).mean()), home_wins=float((o.hg > o.ag).mean()))
        res["leagues"][league] = b
    res["new_four"], res["all_five"] = block(new), block(everything)
    res["all_five"]["per_season"] = [dict(season=int(s), **diff(g, "avgc", "ens"))
                                     for s, g in everything.groupby("season")]
    res["all_five"]["disagreement"] = disagreement(everything, ["dc", "bay", "xgb"])
    res["new_four"]["disagreement"] = disagreement(new, ["dc", "bay", "xgb"])

    # Q1: no decision; the expectation was written down beforehand
    g = res["new_four"]["gap_to_market"]
    res["q1"] = dict(question="Ensemble minus market, the four new leagues together", **g,
                     expected_range=list(Q1_RANGE), inside_expected_range=bool(Q1_RANGE[0] <= g["diff"] <= Q1_RANGE[1]),
                     market_ahead_in=[k for k, v in res["leagues"].items() if v["gap_to_market"]["diff"] > 0])

    # Q2 and Q3 need the Bundesliga's xG models
    if a.xg_table and a.xg_results:
        px = pd.read_csv(os.path.join(a.results, "pooled", "oos_xgb_pooled_xg.csv"))
        x = with_pooled(load(a.xg_table, a.xg_results), px, HOME)
        x = x.dropna(subset=cols("bay") + cols("xgbp") + cols("avgc"))
        q2 = diff(x, "ens_xgbo", "ens_xgbp")
        switch = rule(q2) and abs(q2["diff"]) >= NOISE
        res["q2"] = dict(comparison="xG ensemble with pooled XGBoost-xG minus xG ensemble as published", **q2,
                         passes_rule=rule(q2), above_noise_floor=bool(abs(q2["diff"]) >= NOISE), switch_to_pooled=bool(switch),
                         xgboost_alone=diff(x, "xgbo", "xgbp"), plain_pooled_ensemble=diff(x, "ens_xgbo", "ens_xgbq"),
                         published_ensemble_check=diff(x, "ens", "ens_xgbo"),
                         scores={name: scores(x, m) for name, m in
                                 [("market", "avgc"), ("ensemble_xg", "ens_xgbo"), ("ensemble_xg_pooled", "ens_xgbp"),
                                  ("xgboost_xg", "xgbo"), ("xgboost_xg_pooled", "xgbp")]})
        chosen = "ens_xgbp" if switch else "ens_xgbo"
        five, home = res["all_five"]["two_minus_three"], diff(x, chosen, "two_db")
        res["q3"] = dict(comparison="(Dixon-Coles + Bayesian) minus all three",
                         five_leagues_original_models=five, bundesliga_xg_models=home,
                         drop_xgboost=bool(rule(five) and abs(five["diff"]) >= NOISE and home["diff"] < 0))
    json.dump(res, open(a.out, "w"), indent=1)

    def line(p):
        return f"{p['diff']:+.5f} (95% {p['low']:+.5f} to {p['high']:+.5f}, n={p['n']})"
    print(f"{res['matches']} matches with all three models; left out: {dropped}")
    for league, b in list(res["leagues"].items()) + [("new four", res["new_four"]), ("all five", res["all_five"])]:
        s = b["scores"]
        print(f"{league:9s} market {s['market']['rps']:.4f}  ensemble {s['ensemble']['rps']:.4f}  dc {s['dixon_coles']['rps']:.4f}  "
              f"bay {s['bayesian']['rps']:.4f}  xgb {s['xgboost']['rps']:.4f}  pooled xgb {s['xgboost_pooled']['rps']:.4f}")
        print(f"          gap to market {line(b['gap_to_market'])}")
        print(f"          pooled - own XGBoost {line(b['pooled_minus_own'])}; in the ensemble {line(b['pooled_minus_own_ensemble'])}")
        print(f"          two models - three {line(b['two_minus_three'])}")
    print(f"Q1 new four: {line(res['q1'])}; inside {Q1_RANGE}: {res['q1']['inside_expected_range']}; market ahead in {res['q1']['market_ahead_in']}")
    if "q2" in res:
        print(f"Q2 {res['q2']['comparison']}: {line(res['q2'])} -> {'SWITCH to pooled' if res['q2']['switch_to_pooled'] else 'keep the Bundesliga-only XGBoost'}")
        print(f"   XGBoost-xG alone, pooled - own: {line(res['q2']['xgboost_alone'])}")
        print(f"   refitted own ensemble - published ensemble (should be ~0): {line(res['q2']['published_ensemble_check'])}")
        print(f"Q3 five leagues: {line(res['q3']['five_leagues_original_models'])}; Bundesliga xG models: "
              f"{line(res['q3']['bundesliga_xg_models'])} -> {'DROP XGBoost' if res['q3']['drop_xgboost'] else 'keep XGBoost'}")


if __name__ == "__main__":
    main()
