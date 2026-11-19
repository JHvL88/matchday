"""Grade the pre-registered market-as-input test (analysis/backtest/blend/PREREGISTRATION.md).

    python analysis/pipeline/evaluate_blend.py <tables dir> <source dir> <leagues results dir> out.json \
        [--xg-results <xg results dir>]

The same matches, prices and forecasts as evaluate_clv.py. The blend gives each outcome of a match
(home, draw, away) a score and turns the three scores into probabilities (a softmax):

    score = a + b * ln(market probability) + c * ln(model probability)

`a` is one constant for draws and one for away wins. "Price only" fixes c at 0; "price and models"
lets it go. c = 0 means the models add nothing to the price, c > 0 that the best forecast leans
toward them, c < 0 that it leans away. Fitted by maximum likelihood (Newton's method, no penalty).

Every interval is a bootstrap over matches: the blend is refitted in each resample for the weights,
and the forecasts are kept as made for gains and returns.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from bl_models import logloss, rps
from evaluate import cols
from evaluate_clv import N_BOOT, Matches, boot_weights, load_league, ratio
from leagues import HOME, LEAGUES

RESAMPLES = N_BOOT                             # --resamples lowers it for the weights (a quick look)
FLOOR = 1e-6                                   # probabilities are floored here before the logarithm
BARS = [0.0, 0.02, 0.05, 0.10]                 # expected profit a bet must reach; the rule is the first
PRICES = {"avg": "Market average, early", "b365": "Bet365, early", "max": "Best price in the market, early"}
WEIGHTS = np.round(np.arange(-0.5, 1.0001, 0.01), 2)      # the plain version: (1 - w) market + w models
C_RANGE, B_RANGE, GAIN_LIMIT, BETS_LIMIT = (-0.35, 0.05), (1.00, 1.15), 0.0010, 1500      # written down beforehand
MIN_BETS = 50                                  # fewer bets than this are not set against others at the same odds
EXAMPLES = [[0.75, 0.15, 0.10], [0.50, 0.25, 0.25], [0.35, 0.28, 0.37], [0.20, 0.23, 0.57]]      # home, draw, away
EPS = 1e-9


# ----------------------------------------------------------------------------- the blend
def design(market, models=()):
    """(matches, 3 outcomes, terms): a constant for draws, one for away wins, ln market, ln each model."""
    market = np.asarray(market, float)
    z = np.zeros((len(market), 3, 3 + len(models)))
    z[:, 1, 0] = 1
    z[:, 2, 1] = 1
    z[:, :, 2] = np.log(np.clip(market, FLOOR, 1))
    for j, m in enumerate(models):
        z[:, :, 3 + j] = np.log(np.clip(np.asarray(m, float), FLOOR, 1))
    return z


def start(terms):
    """The market price unchanged: a = 0, b = 1, c = 0."""
    t = np.zeros(terms)
    t[2] = 1.0
    return t


def predict(z, theta):
    s = z @ theta
    e = np.exp(s - s.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def fit(z, y, theta=None, tol=1e-10, max_iter=100):
    """Maximum-likelihood weights of the blend. The log-likelihood is concave, so Newton's method
    with step halving finds the one maximum."""
    n, _, terms = z.shape
    y = np.asarray(y)
    theta = start(terms) if theta is None else np.array(theta, float)
    zy = z[np.arange(n), y]

    def ll(t):
        return float(np.log(predict(z, t)[np.arange(n), y]).sum())
    now = ll(theta)
    for _ in range(max_iter):
        p = predict(z, theta)
        zbar = np.einsum("nk,nkp->np", p, z)
        g = (zy - zbar).sum(0)
        h = np.einsum("nk,nkp,nkq->pq", p, z, z) - zbar.T @ zbar
        step = np.linalg.solve(h, g)
        while True:
            new = ll(theta + step)
            if new >= now - 1e-12 or np.abs(step).max() < tol:
                break
            step = step / 2
        theta, gain, now = theta + step, new - now, new
        if np.abs(step).max() < tol or gain < 1e-13:
            break
    return theta


def fit_boot(z, y, w, theta, iters=8, chunk=100):
    """The weights refitted in every resample. w: (resamples, matches) = how often each match is drawn.
    Each resample starts from the full-sample fit, so a few Newton steps are enough."""
    n, _, terms = z.shape
    y = np.asarray(y)
    zy = z[np.arange(n), y]
    flat = z.reshape(n * 3, terms)
    zz = np.einsum("nkp,nkq->nkpq", z, z).reshape(n * 3, terms * terms)
    out = []
    for i in range(0, len(w), chunk):
        wb = w[i:i + chunk].astype(float)
        th = np.tile(np.asarray(theta, float), (len(wb), 1))
        for _ in range(iters):
            s = (th @ flat.T).reshape(-1, n, 3)
            e = np.exp(s - s.max(2, keepdims=True))
            p = e / e.sum(2, keepdims=True)
            zbar = sum(p[:, :, k, None] * z[None, :, k, :] for k in range(3))        # (resamples, matches, terms)
            wz = wb[:, :, None] * zbar
            g = wb @ zy - wz.sum(1)
            h = ((wb[:, :, None] * p).reshape(-1, n * 3) @ zz).reshape(-1, terms, terms) - wz.transpose(0, 2, 1) @ zbar
            step = np.linalg.solve(h, g[:, :, None])[:, :, 0]
            th = th + step
            if np.abs(step).max() < 1e-7:
                break
        out.append(th)
    return np.vstack(out)


def interval(value, boot):
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(value=float(value), low=float(lo), high=float(hi))


NAMES = ["draw", "away", "market"]
_PRICE_ONLY = {}                               # price-only fits already bootstrapped, by market and results


def weights(market, models, y, names=("models",), boot=True, resamples=None):
    """The fitted blend with a 95% interval for every weight: price only, and price and models."""
    y = np.asarray(y)
    z1 = design(market, models)
    z0 = z1[:, :, :3]
    t0, t1 = fit(z0, y), fit(z1, y)
    out = dict(matches=int(len(y)),
               log_loss=dict(market=float(logloss(market, y).mean()), price_only=float(logloss(predict(z0, t0), y).mean()),
                             price_and_models=float(logloss(predict(z1, t1), y).mean())))
    if boot:
        w = boot_weights(len(y), resamples or RESAMPLES)
        key = hash((z0.tobytes(), y.tobytes(), len(w)))
        if key not in _PRICE_ONLY:
            _PRICE_ONLY[key] = fit_boot(z0, y, w, t0)
        b0, b1 = _PRICE_ONLY[key], fit_boot(z1, y, w, t1)
        out["price_only"] = {k: interval(t0[i], b0[:, i]) for i, k in enumerate(NAMES)}
        out["price_and_models"] = {k: interval(t1[i], b1[:, i]) for i, k in enumerate(NAMES + list(names))}
    else:
        out["price_only"] = {k: dict(value=float(t0[i])) for i, k in enumerate(NAMES)}
        out["price_and_models"] = {k: dict(value=float(t1[i])) for i, k in enumerate(NAMES + list(names))}
    return out


def plain_weight(market, model, y, resamples=None):
    """The single weight w in (1 - w) market + w models that fits the results best, with its interval."""
    y = np.asarray(y)
    market, model = np.asarray(market, float), np.asarray(model, float)
    ll = np.empty((len(y), len(WEIGHTS)))
    for j, w in enumerate(WEIGHTS):
        p = np.clip((1 - w) * market + w * model, FLOOR, None)
        ll[:, j] = np.log(p[np.arange(len(y)), y] / p.sum(1))
    best = WEIGHTS[ll.sum(0).argmax()]
    counts = boot_weights(len(y), resamples or RESAMPLES)
    boot = WEIGHTS[np.vstack([counts[i:i + 250].astype(float) @ ll for i in range(0, len(counts), 250)]).argmax(1)]
    return dict(interval(best, boot), searched=[float(WEIGHTS[0]), float(WEIGHTS[-1])])


# ----------------------------------------------------------------------------- matches the blend hasn't seen
def walk_forward(o, market, models):
    """Forecast every season after the first from a blend fitted on all earlier seasons.
    Returns (rows forecast, price-only probabilities, price-and-models probabilities, weights per season)."""
    y, season = o.y.to_numpy(), o.season.to_numpy()
    z1 = design(o[cols(market)].to_numpy(float), [o[cols(m)].to_numpy(float) for m in models])
    z0 = z1[:, :, :3]
    p0, p1 = np.full((len(o), 3), np.nan), np.full((len(o), 3), np.nan)
    seasons, fitted = sorted(set(season)), []
    for s in seasons[1:]:
        train, test = season < s, season == s
        t0, t1 = fit(z0[train], y[train]), fit(z1[train], y[train])
        p0[test], p1[test] = predict(z0[test], t0), predict(z1[test], t1)
        fitted.append(dict(season=int(s), fitted_on=int(train.sum()), forecast=int(test.sum()),
                           price_only=[float(v) for v in t0], price_and_models=[float(v) for v in t1]))
    return season > seasons[0], p0, p1, fitted


def paired(w, a, b):
    """Mean of a - b over matches with a 95% interval."""
    r = ratio(w, np.asarray(a) - np.asarray(b), np.ones(len(a)))
    return dict(value=r["mean"], low=r["low"], high=r["high"])


class Unseen:
    """The walk-forward forecasts of one set of matches, graded as forecasts and as bets."""

    def __init__(self, o, market="avg", models=("ens",)):
        rows, p0, p1, self.fitted = walk_forward(o, market, models)
        f = o[rows].reset_index(drop=True).copy()
        f[cols("price")], f[cols("blend")] = p0[rows], p1[rows]
        self.f, self.market, self.model = f, market, models[0]
        self.price, self.blend = Matches(f, "price"), Matches(f, "blend")       # .p_model is the forecast
        self.w, self.y = self.blend.w, f.y.to_numpy()

    def gain(self, rows=None):
        """Log loss and RPS of price and models minus price only: below zero means the models helped."""
        k = np.ones(len(self.y), bool) if rows is None else rows
        a, b, y, w = self.blend.p_model[k], self.price.p_model[k], self.y[k], self.w[:, k]
        return dict(matches=int(k.sum()), log_loss=paired(w, logloss(a, y), logloss(b, y)), rps=paired(w, rps(a, y), rps(b, y)))

    def forecasters(self):
        """Every forecast of these matches side by side, and each one's distance from the closing price."""
        f, y = self.f, self.y
        who = [("early_price", f[cols(self.market)].to_numpy(float)), ("price_only", self.price.p_model),
               ("price_and_models", self.blend.p_model), ("models", f[cols(self.model)].to_numpy(float)),
               ("closing_price", f[cols("avgc")].to_numpy(float))]
        close = who[-1][1]
        out = {}
        for name, p in who:
            out[name] = dict(rps=float(rps(p, y).mean()), log_loss=float(logloss(p, y).mean()),
                             rps_minus_closing=paired(self.w, rps(p, y), rps(close, y)),
                             distance_to_closing=float(np.abs(p - close).mean()))
        return out

    def picks(self, which, price, bar=0.0):
        """The rule: every outcome where forecast probability x odds is at least 1 + bar."""
        m = self.blend if which == "blend" else self.price
        odds = m.odds[price]
        return np.isfinite(odds) & (m.p_model * np.where(np.isfinite(odds), odds, 0.0) >= 1 + bar - EPS)

    def bets(self, which, price, bar=0.0, rows=None):
        m = self.blend if which == "blend" else self.price
        k = self.picks(which, price, bar)
        r = m.bets(k, price, rows)
        if r["bets"] and rows is None:
            r["forecast"] = r.pop("model")
            if r["bets"] >= MIN_BETS:                              # too few bets and some resamples hold none
                r["against_same_odds"] = m.same_price_excess(k, price)
        return r

    # ---------- looked at after the results were in (not pre-registered) ----------
    def afterwards(self):
        """What the price's own correction is worth, and which outcomes its bets at the best price are on."""
        y, early = self.y, self.f[cols(self.market)].to_numpy(float)
        out = dict(price_only_minus_early_price=dict(log_loss=paired(self.w, logloss(self.price.p_model, y), logloss(early, y)),
                                                     rps=paired(self.w, rps(self.price.p_model, y), rps(early, y))),
                   by_outcome={})
        everything = np.ones((len(y), 3), bool)
        for i, name in enumerate(["home", "draw", "away"]):
            only = (np.arange(3) == i)[None, :]
            out["by_outcome"][name] = dict(
                every_bet={p: self.price.bets(everything & only, p) for p in ("avg", "max")},
                price_only_rule=self.price.bets(self.picks("price", "max") & only, "max"),
                rule=self.blend.bets(self.picks("blend", "max") & only, "max"))
        return out

    def groups(self, n=5):
        """Results by how far price and models sits from price only, in n equal groups of outcomes."""
        d = self.blend.p_model - self.price.p_model
        cuts = np.quantile(d, np.linspace(0, 1, n + 1)[1:-1])
        which = np.searchsorted(cuts, d)
        won, out = self.blend.won, []
        for i in range(n):
            k = which == i
            hit = ratio(self.w, (won * k).sum(1), k.sum(1))
            out.append(dict(outcomes=int(k.sum()), shift=float(d[k].mean()), price_only=float(self.price.p_model[k].mean()),
                            price_and_models=float(self.blend.p_model[k].mean()),
                            models=float(self.f[cols(self.model)].to_numpy(float)[k].mean()),
                            early_price=float(self.blend.p_early[k].mean()), closing_price=float(self.blend.p_close[k].mean()),
                            happened=dict(value=hit["mean"], low=hit["low"], high=hit["high"])))
        return out

    def block(self, detail=True):
        out = dict(matches=int(len(self.y)), fitted=self.fitted, gain=self.gain(),
                   rule={p: self.bets("blend", p) for p in PRICES},
                   price_only_rule={p: self.bets("price", p) for p in PRICES},
                   every_bet={p: self.blend.bets(np.ones((len(self.y), 3), bool), p) for p in PRICES})
        if detail:
            season = self.f.season.to_numpy()
            out["forecasters"] = self.forecasters()
            out["groups"] = self.groups()
            out["bars"] = [dict(bar=b, rule={p: self.bets("blend", p, b) for p in ("avg", "max")},
                                price_only_rule={p: self.bets("price", p, b) for p in ("avg", "max")}) for b in BARS]
            out["noticed_afterwards"] = self.afterwards()
            out["per_season"] = [dict(season=int(s), gain=self.gain(season == s),
                                      rule={p: self.bets("blend", p, rows=season == s) for p in ("avg", "max")})
                                 for s in sorted(set(season))]
        return out


# ----------------------------------------------------------------------------- verdicts
def q1_verdict(a, unseen, b=None):
    """The pre-registered Q1 rule: the weight on set A, the gain on unseen matches, set B's direction."""
    c, gain = a["price_and_models"]["models"], unseen["gain"]["log_loss"]
    helped = gain["value"] < 0 and gain["high"] < 0
    c_b = None if b is None else b["price_and_models"]["models"]["value"]
    if c["value"] > 0 and c["low"] > 0 and helped and (c_b is None or c_b > 0):
        name = "information"
    elif c["value"] < 0 and c["high"] < 0 and helped:
        name = "contrary"
    else:
        name = "nothing"
    bb, b0 = a["price_and_models"]["market"]["value"], a.get("price_only", {}).get("market", {}).get("value")
    return dict(verdict=name, weight=c, gain=gain, gain_is_real=bool(helped), weight_bundesliga_published=c_b,
                expected=dict(weight=list(C_RANGE), market_weight=list(B_RANGE), gain_smaller_than=GAIN_LIMIT),
                weight_inside_expected_range=bool(C_RANGE[0] <= c["value"] <= C_RANGE[1]),
                market_weight_inside_expected_range=bool(B_RANGE[0] <= bb <= B_RANGE[1]),
                market_weight_price_only_inside_expected_range=None if b0 is None else bool(B_RANGE[0] <= b0 <= B_RANGE[1]),
                gain_inside_expected_range=bool(abs(gain["value"]) < GAIN_LIMIT))


def q2_verdict(unseen):
    """The pre-registered Q2 rule: realised return of the break-even rule at the average, then the best, early price."""
    def above_zero(r):
        return bool(r.get("bets")) and r["realised_return"]["mean"] > 0 and r["realised_return"]["low"] > 0
    avg, best = unseen["rule"]["avg"], unseen["rule"]["max"]
    name = "value" if above_zero(avg) else "value only by shopping around" if above_zero(best) else "no value"
    return dict(verdict=name, average_price=avg, best_price=best, bets_expected_below=BETS_LIMIT,
                bets_inside_expected_range=bool(avg.get("bets", 0) < BETS_LIMIT))


# ----------------------------------------------------------------------------- report
def load_sets(tables, source, results, xg_results=None):
    """Set A (five leagues, original models) and set B (Bundesliga, published models), as in evaluate_clv.py."""
    pooled = pd.read_csv(os.path.join(results, "pooled", "oos_xgb_pooled.csv"))
    frames = [load_league(tables, source, os.path.join(results, league), league, pooled) for league in LEAGUES]
    a = pd.concat(frames, ignore_index=True).dropna(subset=cols("bay") + cols("xgbp") + cols("avgc") + cols("avg"))
    a = a.sort_values(["date", "league", "home"]).reset_index(drop=True)
    b = None
    if xg_results:
        b = load_league(tables, source, xg_results, HOME).dropna(subset=cols("bay") + cols("avgc") + cols("avg"))
        b = b.sort_values(["date", "home"]).reset_index(drop=True)
    return a, b


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tables")
    ap.add_argument("source")
    ap.add_argument("results")
    ap.add_argument("out")
    ap.add_argument("--xg-results", help="the Bundesliga's published forecasts (xg/ on backtest-results)")
    ap.add_argument("--resamples", type=int, default=N_BOOT, help="bootstrap resamples for the weights (the report: 4000)")
    a = ap.parse_args(argv)
    global RESAMPLES
    RESAMPLES = a.resamples
    A, B = load_sets(a.tables, a.source, a.results, a.xg_results)
    y = A.y.to_numpy()

    def P(name, o=A):
        return o[cols(name)].to_numpy(float)

    res = dict(matches=int(len(A)), seasons=[int(A.season.min()), int(A.season.max())], prices=PRICES, floor=FLOOR,
               bootstrap=dict(resamples=N_BOOT, resamples_for_weights=RESAMPLES, seed=0, over="matches"))
    five = dict(weights=weights(P("avg"), [P("ens")], y), plain_weight=plain_weight(P("avg"), P("ens"), y))
    t0 = np.array([five["weights"]["price_only"][k]["value"] for k in NAMES])
    five["examples"] = [dict(early_price=e, price_only=[float(v) for v in predict(design(np.array([e])), t0)[0]]) for e in EXAMPLES]
    unseen = Unseen(A)
    five["unseen"] = unseen.block()
    five["closing_price"] = dict(weights=weights(P("avgc"), [P("ens")], y), plain_weight=plain_weight(P("avgc"), P("ens"), y),
                                 gain=Unseen(A, market="avgc").gain())
    five["per_model"] = {}
    for name, m in [("dixon_coles", "dc"), ("bayesian", "bay"), ("xgboost", "xgb"), ("ensemble_pooled_xgboost", "ens_xgbp")]:
        five["per_model"][name] = dict(weights=weights(P("avg"), [P(m)], y), gain=Unseen(A, models=(m,)).gain())
    three = ("dc", "bay", "xgb")
    five["three_terms"] = dict(weights=weights(P("avg"), [P(m) for m in three], y, names=("dixon_coles", "bayesian", "xgboost")),
                               gain=Unseen(A, models=three).gain())
    five["per_league"] = {}
    for league in LEAGUES:
        g = A[A.league == league]
        five["per_league"][league] = dict(name=LEAGUES[league][2], weights=weights(P("avg", g), [P("ens", g)], g.y.to_numpy()),
                                          gain=unseen.gain((unseen.f.league == league).to_numpy()))
    five["per_season"] = [dict(season=int(s), weights=weights(P("avg", g), [P("ens", g)], g.y.to_numpy()))
                          for s, g in A.groupby("season")]
    res["five_leagues"] = five

    wb = None
    if B is not None:
        wb = weights(P("avg", B), [P("ens", B)], B.y.to_numpy())
        res["bundesliga_published"] = dict(matches=int(len(B)), weights=wb,
                                           plain_weight=plain_weight(P("avg", B), P("ens", B), B.y.to_numpy()),
                                           unseen=Unseen(B).block(detail=False))
    res["q1"] = q1_verdict(five["weights"], five["unseen"], wb)
    res["q2"] = q2_verdict(five["unseen"])
    json.dump(res, open(a.out, "w"), indent=1)

    def iv(v, d=3, scale=1.0):
        key = "value" if "value" in v else "mean"
        return f"{v[key] * scale:+.{d}f} ({v['low'] * scale:+.{d}f} to {v['high'] * scale:+.{d}f})"

    def line(r):
        if not r.get("bets"):
            return "no bets"
        x = r.get("against_same_odds")
        return (f"{r['bets']:6d} bets  return {iv(r['realised_return'], 1, 100)}%  CLV {iv(r['clv'], 2, 100)}%  odds {r['odds']:.2f}"
                + (f"  against same odds {iv(x, 1, 100)}" if x else ""))

    def show(label, wt, un=None):
        t = wt["price_and_models"]
        print(f"\n{label} ({wt['matches']} matches)")
        print(f"  price only        b {iv(wt['price_only']['market'])}  draw {wt['price_only']['draw']['value']:+.3f}  "
              f"away {wt['price_only']['away']['value']:+.3f}")
        print(f"  price and models  b {iv(t['market'])}  c " + "  ".join(f"{k} {iv(t[k])}" for k in list(t)[3:]))
        if un:
            g = un["gain"]
            print(f"  unseen ({g['matches']}): log loss gain {iv(g['log_loss'], 5)}  RPS gain {iv(g['rps'], 5)}")
            for p in PRICES:
                print(f"  rule       @ {p:5s} {line(un['rule'][p])}")
            for p in PRICES:
                print(f"  price only @ {p:5s} {line(un['price_only_rule'][p])}")
            print(f"  every bet  @ avg   {line(un['every_bet']['avg'])}")
    show("Five leagues, original models, early price", five["weights"], five["unseen"])
    print(f"  plain weight w {iv(five['plain_weight'], 2)}")
    for name, v in five["unseen"]["forecasters"].items():
        print(f"     {name:18s} RPS {v['rps']:.4f}  log loss {v['log_loss']:.4f}  minus closing {iv(v['rps_minus_closing'], 4)}")
    for g in five["unseen"]["groups"]:
        print(f"     shift {g['shift'] * 100:+5.2f}  price only {g['price_only'] * 100:5.1f}  with models {g['price_and_models'] * 100:5.1f}  "
              f"happened {iv(g['happened'], 1, 100)}  closing {g['closing_price'] * 100:5.1f}")
    show("Five leagues, closing price", five["closing_price"]["weights"])
    print(f"  unseen: log loss gain {iv(five['closing_price']['gain']['log_loss'], 5)}")
    for name, v in five["per_model"].items():
        show(name, v["weights"])
        print(f"  unseen: log loss gain {iv(v['gain']['log_loss'], 5)}")
    show("three terms", five["three_terms"]["weights"])
    for league, v in five["per_league"].items():
        print(f"  {v['name']:15s} c {iv(v['weights']['price_and_models']['models'])}  gain {iv(v['gain']['log_loss'], 5)}")
    for v in five["per_season"]:
        print(f"  {v['season']}  c {iv(v['weights']['price_and_models']['models'])}")
    if B is not None:
        show("Bundesliga, published models", wb, res["bundesliga_published"]["unseen"])
    print(f"\nQ1 verdict: {res['q1']['verdict'].upper()}; Q2 verdict: {res['q2']['verdict'].upper()}")


if __name__ == "__main__":
    main()
