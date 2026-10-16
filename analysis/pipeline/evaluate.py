"""Grade the backtest: models against the bookmakers, one benchmark everywhere.

"The market" = the market-average closing price on football-data.co.uk (AvgC), margin removed
proportionally. It exists for every Bundesliga match since 2019/20 and is the best public estimate
of the true probabilities. The ensemble is the pre-registered equal-weight average of the three models.

    python analysis/pipeline/evaluate.py data/matches.csv results/ analysis/backtest/results.json
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from bl_models import logloss, outcome_probs, rps, score_matrix

MODELS = ["dc", "bay", "xgb", "ens"]
BENCHMARKS = {"avgc": "Market average, closing", "b365": "Bet365, early-week", "b365c": "Bet365, closing",
              "avg": "Market average, early-week"}
BUCKETS = [(-1, -0.07, "Models 7+ points less sure"), (-0.07, -0.03, "Models 3-7 points less sure"),
           (-0.03, 0.03, "Within 3 points"), (0.03, 1, "Models 3+ points more sure")]
N_BOOT = 4000


def cols(m):
    return [f"{m}_H", f"{m}_D", f"{m}_A"]


def load(matches_csv, results_dir):
    m = pd.read_csv(matches_csv, parse_dates=["date"])
    m["key"] = m.date.dt.strftime("%Y-%m-%d") + "|" + m.home + "|" + m.away
    dc = pd.read_csv(os.path.join(results_dir, "oos_dc.csv"))
    xg = pd.read_csv(os.path.join(results_dir, "oos_xgb.csv"))
    bay_files = sorted(glob.glob(os.path.join(results_dir, "oos_bay_*.csv")))
    bay = pd.concat([pd.read_csv(f) for f in bay_files]) if bay_files else pd.DataFrame(columns=["key"])
    o = m.merge(dc, on="key").merge(xg, on="key").merge(bay, on="key", how="left")
    # XGBoost's score grid uses Dixon-Coles' low-score correction, as in the published posts
    o[cols("xgb")] = np.array([outcome_probs(score_matrix(a, b, r)) for a, b, r in zip(o.xgb_lh, o.xgb_la, o.dc_rho)])
    o[cols("ens")] = (o[cols("dc")].values + o[cols("bay")].values + o[cols("xgb")].values) / 3
    o[cols("two")] = (o[cols("dc")].values + o[cols("xgb")].values) / 2
    for b in BENCHMARKS:
        inv = 1 / o[[f"{b}_h", f"{b}_d", f"{b}_a"]].to_numpy(float)
        o[cols(b)] = inv / inv.sum(1, keepdims=True)
    o["y"] = np.where(o.hg > o.ag, 0, np.where(o.hg == o.ag, 1, 2))
    return o.sort_values("date").reset_index(drop=True)


def score(o, m):
    p, y = o[cols(m)].values, o.y.values
    return dict(rps=float(rps(p, y).mean()), logLoss=float(logloss(p, y).mean()),
                topPick=float((p.argmax(1) == y).mean()))


def gap_ci(o, model="ens", bench="avgc", seed=0):
    """Mean RPS gap (model minus benchmark; positive = bookmakers ahead) with a bootstrap 95% interval."""
    d = rps(o[cols(model)].values, o.y.values) - rps(o[cols(bench)].values, o.y.values)
    rng = np.random.default_rng(seed)
    boot = rng.choice(d, (N_BOOT, len(d))).mean(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(gap=float(d.mean()), low=float(lo), high=float(hi), n=int(len(d)))


def disagreement(o, models, bench="avgc"):
    m = {k: sum(o[f"{c}_{k}"] for c in models) / len(models) for k in "HDA"}
    fav_home = o[f"{bench}_H"] >= o[f"{bench}_A"]
    p_mod = np.where(fav_home, m["H"], m["A"])
    p_mkt = np.where(fav_home, o[f"{bench}_H"], o[f"{bench}_A"])
    won = np.where(fav_home, o.y == 0, o.y == 2)
    gap = p_mod - p_mkt
    out = []
    for lo, hi, lab in BUCKETS:
        k = (gap >= lo) & (gap < hi)
        out.append(dict(label=lab, n=int(k.sum()), models=float(p_mod[k].mean()), market=float(p_mkt[k].mean()),
                        actual=float(won[k].mean())))
    return out


def evaluate(o, mirror_last_date=None, published=None):
    full = o.dropna(subset=cols("bay"))
    seasons = sorted(full.season.unique())
    first = f"{seasons[0]}/{(seasons[0] + 1) % 100:02d}"
    last = f"{seasons[-1]}/{(seasons[-1] + 1) % 100:02d}"
    ongoing = (full.season == seasons[-1]).sum() < 306
    label = f"{first} to {last}" + (" so far" if ongoing else "")
    label_de = f"{first} bis heute" if ongoing else f"{first} bis {last}"
    res = dict(window=label, window_de=label_de, seasons=[int(seasons[0]), int(seasons[-1])], matches=int(len(full)),
               benchmark="avgc", benchmark_label=BENCHMARKS["avgc"])
    res["rows"] = {m: score(full, m) for m in ["avgc"] + MODELS}
    res["uniform_rps"] = float(rps(np.full((len(full), 3), 1 / 3), full.y.values).mean())
    res["gap"] = gap_ci(full)
    res["per_season"] = [dict(season=int(s), n=int(len(g)), **{m: score(g, m)["rps"] for m in ["avgc"] + MODELS},
                              gap=gap_ci(g)) for s, g in full.groupby("season")]
    cur = full[full.season == seasons[-1]]
    res["current_season"] = dict(season=int(seasons[-1]), n=int(len(cur)), models=score(cur, "ens")["rps"],
                                 market=score(cur, "avgc")["rps"], gap=gap_ci(cur))
    res["benchmarks"] = {b: dict(label=lab, rps=score(full, b)["rps"], ensemble_gap=gap_ci(full, "ens", b))
                         for b, lab in BENCHMARKS.items() if full[f"{b}_h"].notna().all()}
    res["disagreement"] = dict(ensemble=disagreement(full, ["dc", "bay", "xgb"]),
                               two_models=disagreement(full, ["dc", "xgb"]))
    res["bayes_coverage"] = dict(with_bayes=int(len(full)), total=int(len(o)))
    if published:   # what moved the headline gap, step by step, on the same predictions where possible
        old = full[full.season >= published["first_season"]]
        mixed = old.copy()
        early = mixed.date <= pd.Timestamp(mirror_last_date)
        for k in "HDA":
            mixed.loc[early, f"mixed_{k}"] = mixed.loc[early, f"b365_{k}"]
            mixed.loc[~early, f"mixed_{k}"] = mixed.loc[~early, f"avgc_{k}"]
        res["bridge"] = [
            dict(step="Published (old data, mixed benchmark)", gap=published["gap"], n=published["matches"]),
            dict(step="Rebuilt from source, same window and benchmark", gap=gap_ci(mixed, "ens", "mixed")["gap"], n=int(len(mixed))),
            dict(step="Closing market average as the benchmark", gap=gap_ci(old, "ens", "avgc")["gap"], n=int(len(old))),
            dict(step=f"Window extended to {label}", gap=res["gap"]["gap"], n=int(len(full))),
        ]
    return res


def record_block(res, as_of, source):
    """The figures the Track record page reads (data/record.json)."""
    names = {"avgc": "market", "ens": "ensemble", "dc": "dixonColes", "bay": "bayesian", "xgb": "xgboost"}
    order = sorted(["avgc", "ens", "dc", "bay", "xgb"], key=lambda m: res["rows"][m]["rps"])
    seven = res["disagreement"]["ensemble"][0]
    return dict(
        asOf=as_of, source=source,
        season=dict(matches=res["current_season"]["n"], models=round(res["current_season"]["models"], 4),
                    market=round(res["current_season"]["market"], 4)),
        backtest=dict(label=dict(en=res["window"], de=res["window_de"]), matches=res["matches"],
                      rows=[dict(key=names[m], rps=round(res["rows"][m]["rps"], 4), logLoss=round(res["rows"][m]["logLoss"], 3),
                                 topPick=round(res["rows"][m]["topPick"], 2)) for m in order],
                      gap=round(res["gap"]["gap"], 4), gapLow=round(res["gap"]["low"], 4), gapHigh=round(res["gap"]["high"], 4)),
        disagreement=[dict(key="ensemble", matches=seven["n"], models=round(seven["models"], 2),
                           market=round(seven["market"], 2), actual=round(seven["actual"], 2))],
    )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("matches")
    ap.add_argument("results_dir")
    ap.add_argument("out")
    ap.add_argument("--record", help="update this data/record.json in place (keeps 'about' and 'paperBetting')")
    ap.add_argument("--as-of", help="date for the record, YYYY-MM-DD")
    a = ap.parse_args()
    o = load(a.matches, a.results_dir)
    published = dict(first_season=2025, gap=0.0026, matches=351)   # data/record.json before this change
    res = evaluate(o, mirror_last_date="2026-08-30", published=published)   # the old mirror's last match day
    json.dump(res, open(a.out, "w"), indent=1)
    r = res["rows"]
    print(f"{res['window']}: {res['matches']} matches (Bayesian predictions for {res['bayes_coverage']['with_bayes']} of {res['bayes_coverage']['total']})")
    for m in ["avgc"] + MODELS:
        print(f"  {m:5s} RPS {r[m]['rps']:.4f}  log loss {r[m]['logLoss']:.3f}  top pick {r[m]['topPick']:.3f}")
    g = res["gap"]
    print(f"  gap ensemble - market {g['gap']:+.4f} (95% {g['low']:+.4f} to {g['high']:+.4f}); uniform RPS {res['uniform_rps']:.4f}")
    for s in res["per_season"]:
        print(f"  {s['season']}: n={s['n']} gap {s['gap']['gap']:+.4f} ({s['gap']['low']:+.4f} to {s['gap']['high']:+.4f})")
    for b in res.get("bridge", []):
        print(f"  bridge: {b['step']}: {b['gap']:+.4f} (n={b['n']})")
    for b, v in res["benchmarks"].items():
        print(f"  benchmark {b:6s} RPS {v['rps']:.4f}  ensemble gap {v['ensemble_gap']['gap']:+.4f}")
    for row in res["disagreement"]["ensemble"]:
        print(f"  disagreement {row['label']}: n={row['n']} models {row['models']:.3f} market {row['market']:.3f} actual {row['actual']:.3f}")
    if a.record:
        rec = json.load(open(a.record))
        rec.update(record_block(res, a.as_of, "analysis/backtest/"))
        rec["about"] = ("Figures behind the Track record page, written by analysis/pipeline/evaluate.py --record "
                        "(never typed by hand). Benchmark: market-average closing odds, margin removed. "
                        "RPS = ranked probability score (lower is better).")
        order = ["about", "asOf", "source", "season", "backtest", "disagreement", "paperBetting"]
        rec = {k: rec[k] for k in order if k in rec} | {k: v for k, v in rec.items() if k not in order}
        open(a.record, "w").write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        print("updated", a.record)
