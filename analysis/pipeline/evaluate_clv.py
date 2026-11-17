"""Grade the pre-registered closing-line test (analysis/backtest/clv/PREREGISTRATION.md).

    python analysis/pipeline/evaluate_clv.py <tables dir> <source dir> <leagues results dir> out.json \
        [--xg-results <xg results dir>]

<tables dir> holds one match table per league (build_matches.py --league), <source dir> the
football-data.co.uk files (the source-data branch), <leagues results dir> is leagues/ on the
backtest-results branch and <xg results dir> its xg/ (the Bundesliga's published forecasts).

Three numbers per match and outcome (home, draw, away), all in probabilities with the bookmakers'
margin removed proportionally:

    edge       the ensemble minus the early market (football-data's pre-closing average)
    line move  the closing market minus the early market
    CLV        odds taken x closing probability - 1, for a bet (the site's definition)

Every interval is a bootstrap over matches (a match's outcomes and bets stay together).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from bl_models import rps
from build_matches import read_season_file
from evaluate import cols, load
from leagues import HOME, LEAGUES

N_BOOT, SEED = 4000, 0
THRESHOLD = 0.05                               # the Track record's rule
THRESHOLDS = [0.0, 0.02, 0.03, 0.05, 0.07, 0.10]
EDGE_BUCKETS = [(-1, -0.05, "Models 5+ points below the market"), (-0.05, -0.02, "2 to 5 points below"),
                (-0.02, 0.02, "Within 2 points"), (0.02, 0.05, "2 to 5 points above"),
                (0.05, 1, "Models 5+ points above the market")]
ODDS_BANDS = [(1, 2, "Odds below 2"), (2, 4, "Odds 2 to 4"), (4, 1e9, "Odds above 4")]
PRICES = {"avg": "Market average, early", "b365": "Bet365, early", "max": "Best price in the market, early"}
Q1_RANGE = (-0.03, 0.03)                       # written down beforehand
Q2_CLV_RANGE = (-0.08, -0.03)
# the best early price is not in the match tables; football-data's column names, newest first
MAX_EARLY = [("MaxH", "MaxD", "MaxA"), ("BbMxH", "BbMxD", "BbMxA")]
EPS = 1e-9


def source_odds(table, source_dir, options, prefix):
    """Read three odds columns for every row of a match table from the file and line it came from."""
    out = np.full((len(table), 3), np.nan)
    pos = pd.Series(np.arange(len(table)), index=table.index)
    for rel, rows in table.groupby("src_file"):
        f = read_season_file(os.path.join(source_dir, rel)).set_index("src_row")
        names = next((o for o in options if all(c in f.columns for c in o)), None)
        if names is None:
            continue
        v = f.loc[rows.src_row.values, list(names)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        out[pos[rows.index].values] = np.where(v > 1.0, v, np.nan)       # football-data uses blanks/0 for missing
    return pd.DataFrame(out, index=table.index, columns=[f"{prefix}_{s}" for s in "hda"])


def boot_weights(n, n_boot=N_BOOT, seed=SEED):
    """How often each match is drawn in each resample (n_boot x n). One set per group of matches, so
    every number about that group moves with the same resamples."""
    return np.random.default_rng(seed).multinomial(n, np.full(n, 1 / n), size=n_boot).astype(np.uint8)


def boot_sums(w, x, chunk=250):
    """Column sums of x (matches x k) in every resample."""
    x = np.asarray(x, float)
    return np.vstack([w[i:i + chunk].astype(np.float32) @ x for i in range(0, len(w), chunk)])


def ratio(w, num, den):
    """Sum(num) / Sum(den) over matches, with a 95% percentile interval. None if there is nothing to divide by."""
    num, den = np.nan_to_num(np.asarray(num, float)), np.nan_to_num(np.asarray(den, float))
    if den.sum() <= 0:
        return None
    s = boot_sums(w, np.column_stack([num, den]))
    ok = s[:, 1] > 0
    lo, hi = np.percentile(s[ok, 0] / s[ok, 1], [2.5, 97.5])
    return dict(mean=float(num.sum() / den.sum()), low=float(lo), high=float(hi))


class Matches:
    """One group of matches with one forecast, as arrays of shape (matches, 3 outcomes)."""

    def __init__(self, o, model):
        o = o.reset_index(drop=True)
        self.o, self.n, self.model = o, len(o), model
        self.p_model = o[cols(model)].to_numpy(float)
        self.p_early = o[cols("avg")].to_numpy(float)
        self.p_close = o[cols("avgc")].to_numpy(float)
        self.odds = {p: o[[f"{p}_h", f"{p}_d", f"{p}_a"]].to_numpy(float) for p in PRICES}
        self.odds_close = o[["avgc_h", "avgc_d", "avgc_a"]].to_numpy(float)
        self.won = (o.y.to_numpy()[:, None] == np.arange(3)[None, :]).astype(float)
        self.edge = self.p_model - self.p_early
        self.move = self.p_close - self.p_early
        self.w = boot_weights(self.n)

    # ---------- Q1 ----------
    def slope(self, rows=None, outcomes=(0, 1, 2)):
        """Least-squares slope of line move on edge (no intercept: both sum to zero within a match)."""
        k = np.ones(self.n, bool) if rows is None else rows
        e, m = self.edge[:, outcomes], self.move[:, outcomes]
        r = ratio(self.w, (e * m).sum(1) * k, (e * e).sum(1) * k)
        return dict(slope=r["mean"], low=r["low"], high=r["high"], n=int(k.sum()))

    def slope_controlled(self):
        """The same slope with the early probability (minus 1/3) as a second variable."""
        e, m, q = self.edge, self.move, self.p_early - 1 / 3
        stats = np.column_stack([(e * e).sum(1), (e * q).sum(1), (q * q).sum(1), (e * m).sum(1), (q * m).sum(1)])

        def solve(s):
            a, b, c, d, f = s.T if s.ndim == 2 else s
            det = a * c - b * b
            return (d * c - f * b) / det, (a * f - b * d) / det
        edge, early = solve(stats.sum(0))
        be, bq = solve(boot_sums(self.w, stats))
        return dict(edge=dict(slope=float(edge), low=float(np.percentile(be, 2.5)), high=float(np.percentile(be, 97.5))),
                    early_probability=dict(slope=float(early), low=float(np.percentile(bq, 2.5)),
                                           high=float(np.percentile(bq, 97.5))))

    def buckets(self):
        """Average line move by size of edge. The outer buckets are the rule's and the mirror rule's picks."""
        cuts = [c[1] for c in EDGE_BUCKETS[:-1]]                          # -0.05, -0.02, 0.02, 0.05
        which = np.select([self.edge <= cuts[0] + EPS, self.edge < cuts[1], self.edge < cuts[2], self.edge < cuts[3] - EPS],
                          [0, 1, 2, 3], default=4)
        out = []
        for i, (_, _, label) in enumerate(EDGE_BUCKETS):
            k = which == i
            mean = lambda v: float(v[k].mean()) if k.any() else None      # noqa: E731
            out.append(dict(label=label, outcomes=int(k.sum()), edge=mean(self.edge),
                            move=ratio(self.w, (self.move * k).sum(1), k.sum(1)),
                            won=mean(self.won), early=mean(self.p_early), closing=mean(self.p_close),
                            model=mean(self.p_model)))
        return out

    # ---------- Q2 ----------
    def picks(self, threshold=THRESHOLD, mirror=False):
        """Which outcomes the rule bets on: the model at least `threshold` above the early market
        (mirror: at least that far below)."""
        return (-self.edge if mirror else self.edge) >= threshold - EPS

    def bets(self, picks, price="avg", rows=None):
        """Grade €1 on every picked outcome at one price."""
        odds = self.odds[price]
        k = picks & np.isfinite(odds)
        if rows is not None:
            k = k & rows[:, None]
        n = k.sum(1)
        if n.sum() == 0:
            return dict(bets=0)
        o = np.where(k, odds, 0.0)
        clv = o * self.p_close - k
        ret = o * self.won - k
        return dict(bets=int(n.sum()), matches=int((n > 0).sum()),
                    clv=ratio(self.w, clv.sum(1), n), line_move=ratio(self.w, (self.move * k).sum(1), n),
                    realised_return=ratio(self.w, ret.sum(1), n),
                    won=float(self.won[k].mean()), odds=float(odds[k].mean()), edge=float(self.edge[k].mean()),
                    model=float(self.p_model[k].mean()), early=float(self.p_early[k].mean()),
                    closing=float(self.p_close[k].mean()),
                    longer_than_close=float((odds[k] > self.odds_close[k]).mean()),
                    outcomes=dict(zip(["home", "draw", "away"], [int(v) for v in k.sum(0)])))

    # ---------- looked at after the results were in (not pre-registered) ----------
    def same_price_excess(self, picks, price="avg", bins=20):
        """Realised return of the picked bets minus that of every other bet at about the same odds
        (`bins` equal-sized groups by price). Takes the favourite-longshot bias out of the comparison."""
        odds = self.odds[price]
        ok = np.isfinite(odds)
        cuts = np.quantile(odds[ok], np.linspace(0, 1, bins + 1)[1:-1])
        which = np.searchsorted(cuts, np.where(ok, odds, 1.0))
        ret = np.where(ok, odds, 0.0) * self.won - ok
        stats = []
        for b in range(bins):
            mine, rest = ok & picks & (which == b), ok & ~picks & (which == b)
            stats += [mine.sum(1), (ret * mine).sum(1), rest.sum(1), (ret * rest).sum(1)]

        def excess(s):
            s = s.reshape(*s.shape[:-1], bins, 4)
            n, r, n0, r0 = (s[..., i] for i in range(4))
            base = np.divide(r0, n0, out=np.zeros_like(r0, dtype=float), where=n0 > 0)
            return (r - n * base).sum(-1) / n.sum(-1)
        x = np.column_stack(stats).astype(float)
        boot = excess(boot_sums(self.w, x))
        return dict(mean=float(excess(x.sum(0))), low=float(np.percentile(boot, 2.5)), high=float(np.percentile(boot, 97.5)),
                    bets=int((ok & picks).sum()), bins=bins)

    def forecasters(self):
        """RPS of the early price, the closing price and the model, and the two gaps between them."""
        y = self.o.y.to_numpy()
        score = {k: rps(p, y) for k, p in [("early", self.p_early), ("closing", self.p_close), ("model", self.p_model)]}
        one = np.ones(self.n)
        return dict(rps={k: float(v.mean()) for k, v in score.items()},
                    early_minus_closing=ratio(self.w, score["early"] - score["closing"], one),
                    model_minus_early=ratio(self.w, score["model"] - score["early"], one),
                    model_minus_closing=ratio(self.w, score["model"] - score["closing"], one),
                    line_move_sd=float(self.move.std()), edge_sd=float(self.edge.std()),
                    home_move_mean_abs=float(np.abs(self.move[:, 0]).mean()))

    def afterwards(self):
        rule, mirror = self.picks(), self.picks(mirror=True)
        gap = lambda k: float(self.won[k].mean() - self.p_close[k].mean())      # noqa: E731
        odds = self.odds["avg"]
        return dict(forecasters=self.forecasters(),
                    same_price_excess=dict(rule=self.same_price_excess(rule), mirror=self.same_price_excess(mirror)),
                    won_minus_closing=dict(rule=gap(rule), mirror=gap(mirror), every_bet=0.0,
                                           by_price=[dict(label=label, rule=gap(rule & (odds >= lo) & (odds < hi)),
                                                          mirror=gap(mirror & (odds >= lo) & (odds < hi)),
                                                          every_bet=gap((odds >= lo) & (odds < hi)))
                                                     for lo, hi, label in ODDS_BANDS]),
                    mirror_by_price=[dict(label=label, mirror=self.bets(mirror & (odds >= lo) & (odds < hi), "avg"))
                                     for lo, hi, label in ODDS_BANDS])

    def margins(self):
        m = {p: float(np.nanmean((1 / v).sum(1) - 1)) for p, v in self.odds.items()}
        m["avgc"] = float(np.nanmean((1 / self.odds_close).sum(1) - 1))
        return m

    def block(self, detail=True):
        """Everything reported for one group of matches and one forecast."""
        rule = self.picks()
        out = dict(matches=self.n, model=self.model, margins=self.margins(),
                   q1=dict(self.slope(), buckets=self.buckets(), controlled=self.slope_controlled(),
                           by_outcome={name: self.slope(outcomes=(i,)) for i, name in enumerate(["home", "draw", "away"])}),
                   rule={p: self.bets(rule, p) for p in PRICES},
                   mirror={p: self.bets(self.picks(mirror=True), p) for p in PRICES},
                   every_bet={p: self.bets(np.ones_like(rule), p) for p in PRICES},
                   thresholds=[dict(threshold=t, rule=self.bets(self.picks(t), "avg"),
                                    mirror=self.bets(self.picks(t, mirror=True), "avg"),
                                    rule_best_price=self.bets(self.picks(t), "max")) for t in THRESHOLDS])
        if detail:
            o = self.o
            out["per_season"] = [dict(season=int(s), q1=self.slope((o.season == s).to_numpy()),
                                      rule=self.bets(rule, "avg", (o.season == s).to_numpy()))
                                 for s in sorted(o.season.unique())]
            out["by_outcome"] = {name: self.bets(rule & (np.arange(3) == i)[None, :], "avg")
                                 for i, name in enumerate(["home", "draw", "away"])}
            odds = self.odds["avg"]
            out["by_price"] = [dict(label=label, rule=self.bets(rule & (odds >= lo) & (odds < hi), "avg"),
                                    every_bet=self.bets((odds >= lo) & (odds < hi), "avg"))
                               for lo, hi, label in ODDS_BANDS]
            out["noticed_afterwards"] = self.afterwards()
        return out


def verdict(a, b=None):
    """The pre-registered Q2 rule, on set A at the average early price (and set B's direction)."""
    r = a["rule"]["avg"]
    value_a = r["clv"]["mean"] > 0 and r["clv"]["low"] > 0
    value_b = None if b is None else bool(b["rule"]["avg"]["clv"]["mean"] > 0)
    signal = r["line_move"]["mean"] > 0 and r["line_move"]["low"] > 0
    best = a["rule"]["max"]
    best_price_value = best["clv"]["mean"] > 0 and best["clv"]["low"] > 0
    if value_a and value_b is not False:
        name = "value"
    elif signal:
        name = "signal, no value"
    else:
        name = "nothing"
    forward_test = name == "value" or (name == "signal, no value" and best_price_value)
    return dict(verdict=name, clv_above_zero_five_leagues=bool(value_a), clv_above_zero_bundesliga=value_b,
                line_moves_toward_picks=bool(signal), best_price_clv_above_zero=bool(best_price_value),
                forward_test=bool(forward_test), clv=r["clv"], line_move=r["line_move"],
                realised_return=r["realised_return"], bets=r["bets"],
                expected_clv_range=list(Q2_CLV_RANGE),
                clv_inside_expected_range=bool(Q2_CLV_RANGE[0] <= r["clv"]["mean"] <= Q2_CLV_RANGE[1]))


def load_league(tables, source, results, league, pooled=None):
    """One league's forecasts with every price; `pooled` adds the five-league XGBoost and its ensemble."""
    o = load(os.path.join(tables, f"{league}.csv"), results)
    o = o.join(source_odds(o, source, MAX_EARLY, "max"))
    if pooled is not None:
        from evaluate_leagues import with_pooled
        o = with_pooled(o, pooled, league, tags=("xgbp",))
    return o.assign(league=league)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tables")
    ap.add_argument("source")
    ap.add_argument("results")
    ap.add_argument("out")
    ap.add_argument("--xg-results", help="the Bundesliga's published forecasts (xg/ on backtest-results)")
    a = ap.parse_args(argv)

    pooled = pd.read_csv(os.path.join(a.results, "pooled", "oos_xgb_pooled.csv"))
    frames = [load_league(a.tables, a.source, os.path.join(a.results, league), league, pooled) for league in LEAGUES]
    every = pd.concat(frames, ignore_index=True).dropna(subset=cols("bay") + cols("xgbp") + cols("avgc"))
    coverage = dict(matches=int(len(every)), **{p: int(every[[f"{p}_h", f"{p}_d", f"{p}_a"]].notna().all(axis=1).sum())
                                                 for p in PRICES})
    every = every.dropna(subset=cols("avg")).reset_index(drop=True)     # the edge needs the early average

    res = dict(coverage=coverage, matches=int(len(every)), threshold=THRESHOLD, prices=PRICES,
               seasons=[int(every.season.min()), int(every.season.max())],
               bootstrap=dict(resamples=N_BOOT, seed=SEED, over="matches"))
    A = Matches(every, "ens")
    res["five_leagues"] = A.block()
    res["five_leagues"]["per_league"] = {}
    for league in LEAGUES:
        g = Matches(every[every.league == league], "ens")
        res["five_leagues"]["per_league"][league] = dict(name=LEAGUES[league][2], matches=g.n, q1=g.slope(),
                                                         rule=g.bets(g.picks(), "avg"), mirror=g.bets(g.picks(mirror=True), "avg"),
                                                         rule_best_price=g.bets(g.picks(), "max"))
    res["five_leagues"]["per_model"] = {}
    for name, m in [("dixon_coles", "dc"), ("bayesian", "bay"), ("xgboost", "xgb"), ("ensemble_pooled_xgboost", "ens_xgbp")]:
        g = Matches(every, m)
        res["five_leagues"]["per_model"][name] = dict(q1=g.slope(), rule=g.bets(g.picks(), "avg"),
                                                      mirror=g.bets(g.picks(mirror=True), "avg"))

    B = None
    if a.xg_results:
        x = load_league(a.tables, a.source, a.xg_results, HOME)
        x = x.dropna(subset=cols("bay") + cols("avgc") + cols("avg")).reset_index(drop=True)
        B = Matches(x, "ens").block()
        res["bundesliga_published"] = B

    s = res["five_leagues"]["q1"]
    res["q1"] = dict(slope=s["slope"], low=s["low"], high=s["high"], expected_range=list(Q1_RANGE),
                     inside_expected_range=bool(Q1_RANGE[0] <= s["slope"] <= Q1_RANGE[1]))
    res["q2"] = verdict(res["five_leagues"], B)
    json.dump(res, open(a.out, "w"), indent=1)

    def pct(r, key):
        v = r[key]
        return f"{v['mean'] * 100:+.2f}% ({v['low'] * 100:+.2f} to {v['high'] * 100:+.2f})"

    def line(r):
        if not r.get("bets"):
            return "no bets"
        m = r["line_move"]
        return (f"{r['bets']:6d} bets  CLV {pct(r, 'clv')}  line move {m['mean'] * 100:+.2f} points "
                f"({m['low'] * 100:+.2f} to {m['high'] * 100:+.2f})  return {pct(r, 'realised_return')}  odds {r['odds']:.2f}")
    print(f"{coverage['matches']} matches; with the early average {coverage['avg']}, Bet365 {coverage['b365']}, best price {coverage['max']}")
    for label, b in [("Five leagues, original models", res["five_leagues"])] + ([("Bundesliga, published models", B)] if B else []):
        q = b["q1"]
        print(f"\n{label} ({b['matches']} matches)")
        print(f"  Q1 slope {q['slope']:+.4f} (95% {q['low']:+.4f} to {q['high']:+.4f}); with the early probability held fixed "
              f"{q['controlled']['edge']['slope']:+.4f}")
        for k in q["buckets"]:
            print(f"     {k['label']:36s} {k['outcomes']:6d}  edge {k['edge'] * 100:+6.2f}  line move {k['move']['mean'] * 100:+.3f} "
                  f"({k['move']['low'] * 100:+.3f} to {k['move']['high'] * 100:+.3f})")
        for p in PRICES:
            print(f"  rule   @ {p:5s} {line(b['rule'][p])}")
        for p in PRICES:
            print(f"  mirror @ {p:5s} {line(b['mirror'][p])}")
        print(f"  every bet @ avg {line(b['every_bet']['avg'])}")
        n = b["noticed_afterwards"]
        f, x = n["forecasters"], n["same_price_excess"]
        print(f"  afterwards: RPS early {f['rps']['early']:.4f}, closing {f['rps']['closing']:.4f}, model {f['rps']['model']:.4f}; "
              f"early - closing {f['early_minus_closing']['mean']:+.5f}, model - early {f['model_minus_early']['mean']:+.5f}")
        print(f"  afterwards: return against other bets at the same odds: rule "
              f"{x['rule']['mean'] * 100:+.2f}% ({x['rule']['low'] * 100:+.2f} to {x['rule']['high'] * 100:+.2f}), "
              f"mirror {x['mirror']['mean'] * 100:+.2f}% ({x['mirror']['low'] * 100:+.2f} to {x['mirror']['high'] * 100:+.2f})")
    print(f"\nQ1 inside {Q1_RANGE}: {res['q1']['inside_expected_range']}")
    print(f"Q2 verdict: {res['q2']['verdict'].upper()}; forward test: {res['q2']['forward_test']}")


if __name__ == "__main__":
    main()
