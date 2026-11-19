"""Tests for the market-as-input test (evaluate_blend.py).

    pip install pytest numpy pandas && python -m pytest analysis/pipeline/tests -q

No network and no real data: made-up matches whose right answer is known.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

pytest.importorskip("jax")          # evaluate.py imports the models
import evaluate_blend as eb  # noqa: E402
from evaluate import cols  # noqa: E402


def draw(p, rng):
    """One result per match from its probabilities."""
    return (rng.random(len(p))[:, None] > np.cumsum(p, 1)).sum(1).clip(0, 2)


def world(n=6000, c=0.0, b=1.0, seed=3):
    """Matches where the truth is softmax(b ln market + c ln model)."""
    rng = np.random.default_rng(seed)
    market, model = rng.dirichlet([6, 3.5, 4], n), rng.dirichlet([6, 3.5, 4], n)
    truth = eb.predict(eb.design(market, [model]), np.array([0, 0, b, c]))
    return market, model, truth, draw(truth, rng)


def frame(market, model, y, seasons, margin=0.05):
    o = pd.DataFrame({"y": y, "season": seasons})
    o[cols("avg")], o[cols("avgc")], o[cols("ens")] = market, market, model
    for price in eb.PRICES:
        o[[f"{price}_h", f"{price}_d", f"{price}_a"]] = 1 / (market * (1 + margin))
    o[["avgc_h", "avgc_d", "avgc_a"]] = 1 / (market * (1 + margin))
    return o


def test_start_is_the_market_price_unchanged():
    market, model, _, _ = world(50)
    z = eb.design(market, [model])
    assert np.allclose(eb.predict(z, eb.start(4)), market)
    assert z.shape == (50, 3, 4) and z[:, 0, :2].sum() == 0 and (z[:, 1, 0] == 1).all() and (z[:, 2, 1] == 1).all()


def test_fit_recovers_the_weights_the_results_were_drawn_with():
    for c, b in [(0.0, 1.0), (0.4, 1.0), (-0.3, 1.1)]:
        market, model, _, y = world(40000, c, b)
        t = eb.fit(eb.design(market, [model]), y)
        assert t[2] == pytest.approx(b, abs=0.04) and t[3] == pytest.approx(c, abs=0.04)
        assert abs(t[0]) < 0.05 and abs(t[1]) < 0.05


def test_fit_is_at_the_maximum_and_the_floor_holds():
    market, model, _, y = world(3000, 0.2)
    model[0] = [0.0, 0.5, 0.5]                                   # a zero probability must not break the logarithm
    z = eb.design(market, [model])
    t = eb.fit(z, y)
    best = eb.logloss(eb.predict(z, t), y).sum()
    for i in range(4):
        for d in (-0.01, 0.01):
            u = t.copy()
            u[i] += d
            assert eb.logloss(eb.predict(z, u), y).sum() > best
    assert np.isfinite(z).all() and z[0, 0, 3] == pytest.approx(np.log(eb.FLOOR))


def test_bootstrap_refit_matches_fitting_the_resample_itself():
    market, model, _, y = world(800, 0.3)
    z = eb.design(market, [model])
    t = eb.fit(z, y)
    counts = np.random.default_rng(0).multinomial(800, np.full(800, 1 / 800), size=3)
    boot = eb.fit_boot(z, y, counts, t)
    for k in range(3):
        rows = np.repeat(np.arange(800), counts[k])
        assert np.allclose(boot[k], eb.fit(z[rows], y[rows]), atol=1e-6)


def test_weights_report_an_interval_that_covers_the_truth():
    market, model, _, y = world(5000, 0.0)
    w = eb.weights(market, [model], y)
    c = w["price_and_models"]["models"]
    assert c["low"] < 0 < c["high"] and c["low"] <= c["value"] <= c["high"]
    assert w["price_only"]["market"]["low"] < 1 < w["price_only"]["market"]["high"]
    assert w["log_loss"]["price_and_models"] <= w["log_loss"]["price_only"] <= w["log_loss"]["market"] + 1e-12


def test_plain_weight_finds_the_mix():
    rng = np.random.default_rng(5)
    market, model = rng.dirichlet([6, 3.5, 4], 30000), rng.dirichlet([6, 3.5, 4], 30000)
    y = draw(0.7 * market + 0.3 * model, rng)
    w = eb.plain_weight(market, model, y)
    assert w["value"] == pytest.approx(0.3, abs=0.05) and w["low"] <= 0.3 <= w["high"]
    assert eb.plain_weight(market, model, draw(market, rng))["value"] == pytest.approx(0.0, abs=0.05)


def test_walk_forward_never_sees_the_season_it_forecasts():
    market, model, _, y = world(3000, 0.3)
    seasons = np.repeat([2019, 2020, 2021], 1000)
    o = frame(market, model, y, seasons)
    rows, p0, p1, fitted = eb.walk_forward(o, "avg", ("ens",))
    assert rows.sum() == 2000 and np.isnan(p1[~rows]).all() and np.allclose(p1[rows].sum(1), 1)
    assert [f["fitted_on"] for f in fitted] == [1000, 2000]
    changed = o.copy()
    changed.loc[seasons == 2021, "y"] = 0                         # rewrite the last season's results
    _, q0, q1, _ = eb.walk_forward(changed, "avg", ("ens",))
    assert np.allclose(p1[rows], q1[rows]) and np.allclose(p0[rows], q0[rows])
    changed = o.copy()
    changed.loc[seasons == 2019, "y"] = 0                         # rewrite the first: every forecast moves
    _, _, q1, _ = eb.walk_forward(changed, "avg", ("ens",))
    assert not np.allclose(p1[seasons == 2020], q1[seasons == 2020])


def test_unseen_gain_is_below_zero_when_the_models_know_something_and_about_zero_when_not():
    seasons = np.repeat([2019, 2020, 2021, 2022], 2500)
    market, model, _, y = world(10000, 0.5)
    g = eb.Unseen(frame(market, model, y, seasons)).gain()
    assert g["matches"] == 7500 and g["log_loss"]["high"] < 0 and g["rps"]["value"] < 0
    market, model, _, y = world(10000, 0.0)
    g = eb.Unseen(frame(market, model, y, seasons)).gain()
    assert abs(g["log_loss"]["value"]) < 0.001


def test_rule_bets_where_probability_times_odds_reaches_the_bar():
    market = np.array([[0.5, 0.25, 0.25]] * 4)
    o = frame(market, market, [0, 1, 2, 0], [2019, 2019, 2020, 2020], margin=0.0)
    u = eb.Unseen.__new__(eb.Unseen)
    f = o.copy()
    f[cols("price")] = market
    f[cols("blend")] = np.array([[0.5, 0.25, 0.25], [0.55, 0.2, 0.25], [0.45, 0.30, 0.25], [0.5, 0.2, 0.3]])
    u.f, u.market, u.model = f, "avg", "ens"
    u.price, u.blend = eb.Matches(f, "price"), eb.Matches(f, "blend")
    u.w, u.y = u.blend.w, f.y.to_numpy()
    # fair odds are 2, 4, 4: blend x odds = 1 exactly where it agrees, above 1 where it is higher
    assert u.picks("blend", "avg").tolist() == [[True, True, True], [True, False, True], [False, True, True], [True, False, True]]
    assert u.picks("blend", "avg", 0.05).tolist() == [[False] * 3, [True, False, False], [False, True, False], [False, False, True]]
    r = u.bets("blend", "avg", 0.05)
    assert r["bets"] == 3 and r["matches"] == 3
    # €1 each on home at 2 (result draw: lost), draw at 4 (result away: lost), away at 4 (result home: lost)
    assert r["realised_return"]["mean"] == pytest.approx(-1.0)
    assert u.bets("price", "avg", 0.05) == dict(bets=0)


def test_verdicts_follow_the_pre_registered_rules():
    def a(c, lo, hi):
        return dict(price_and_models=dict(models=dict(value=c, low=lo, high=hi), market=dict(value=1.05)))

    def un(gain, lo, hi, ret=None):
        bet = dict(bets=0) if ret is None else dict(bets=10, realised_return=dict(mean=ret[0], low=ret[1], high=ret[2]))
        return dict(gain=dict(log_loss=dict(value=gain, low=lo, high=hi)), rule=dict(avg=bet, max=bet))
    helped, flat = un(-0.001, -0.002, -0.0005), un(-0.0001, -0.0005, 0.0003)
    assert eb.q1_verdict(a(0.3, 0.1, 0.5), helped)["verdict"] == "information"
    assert eb.q1_verdict(a(0.3, 0.1, 0.5), helped, a(-0.1, -0.5, 0.3))["verdict"] == "nothing"     # set B points the other way
    assert eb.q1_verdict(a(0.3, 0.1, 0.5), helped, a(0.1, -0.5, 0.3))["verdict"] == "information"
    assert eb.q1_verdict(a(0.3, 0.1, 0.5), flat)["verdict"] == "nothing"                           # no gain on unseen matches
    assert eb.q1_verdict(a(0.3, -0.1, 0.5), helped)["verdict"] == "nothing"                        # interval includes zero
    assert eb.q1_verdict(a(-0.3, -0.5, -0.1), helped)["verdict"] == "contrary"
    assert eb.q1_verdict(a(-0.3, -0.5, -0.1), flat)["verdict"] == "nothing"
    q = eb.q1_verdict(a(-0.3, -0.5, -0.1), flat)
    assert q["weight_inside_expected_range"] and q["market_weight_inside_expected_range"] and q["gain_inside_expected_range"]

    assert eb.q2_verdict(un(0, 0, 0))["verdict"] == "no value"
    assert eb.q2_verdict(un(0, 0, 0, (0.05, 0.01, 0.09)))["verdict"] == "value"
    assert eb.q2_verdict(un(0, 0, 0, (0.05, -0.01, 0.09)))["verdict"] == "no value"
    mixed = un(0, 0, 0, (0.05, -0.01, 0.09))
    mixed["rule"]["max"] = dict(bets=10, realised_return=dict(mean=0.06, low=0.01, high=0.1))
    assert eb.q2_verdict(mixed)["verdict"] == "value only by shopping around"
