"""Tests for the closing-line test (evaluate_clv.py).

    pip install pytest numpy pandas && python -m pytest analysis/pipeline/tests -q

No network and no real data: a handful of made-up matches with known answers.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

pytest.importorskip("jax")          # evaluate.py imports the models
import evaluate_clv as ec  # noqa: E402
from evaluate import cols  # noqa: E402


def frame(model, early, closing, results, odds=None):
    """A match table as evaluate.load() returns it, from probabilities (the odds default to fair ones)."""
    model, early, closing = (np.asarray(v, float) for v in (model, early, closing))
    o = pd.DataFrame({"y": results, "season": 2024})
    o[cols("ens")], o[cols("avg")], o[cols("avgc")] = model, early, closing
    fair = 1 / early if odds is None else np.asarray(odds, float)
    for price in ec.PRICES:
        o[[f"{price}_h", f"{price}_d", f"{price}_a"]] = fair
    o[["avgc_h", "avgc_d", "avgc_a"]] = 1 / closing
    return o


def test_slope_is_the_share_of_the_gap_the_line_closes():
    rng = np.random.default_rng(1)
    early = rng.dirichlet([5, 3, 3], 400)
    model = rng.dirichlet([5, 3, 3], 400)
    for share in (0.0, 0.25, 1.0, -0.5):
        m = ec.Matches(frame(model, early, early + share * (model - early), np.zeros(400, int)), "ens")
        s = m.slope()
        assert s["slope"] == pytest.approx(share, abs=1e-9) and s["low"] <= s["slope"] <= s["high"]
        assert s["n"] == 400
    # holding the early probability fixed changes nothing when the move is all edge
    c = ec.Matches(frame(model, early, early + 0.25 * (model - early), np.zeros(400, int)), "ens").slope_controlled()
    assert c["edge"]["slope"] == pytest.approx(0.25, abs=1e-6)
    assert c["early_probability"]["slope"] == pytest.approx(0.0, abs=1e-6)


def test_rule_picks_at_least_five_points_and_the_mirror_the_other_side():
    early = [[0.50, 0.25, 0.25], [0.40, 0.30, 0.30]]
    model = [[0.44, 0.25, 0.31], [0.45, 0.2501, 0.2999]]   # +6 on the away side; exactly +5 on the home side
    m = ec.Matches(frame(model, early, early, [2, 1]), "ens")
    assert m.picks().tolist() == [[False, False, True], [True, False, False]]
    assert m.picks(mirror=True).tolist() == [[True, False, False], [False, False, False]]
    assert m.picks(0.0).sum() == 3 and m.picks(0.10).sum() == 0
    kinds = [b["outcomes"] for b in m.buckets()]
    assert kinds == [1, 1, 2, 0, 2] and sum(kinds) == 6      # every outcome lands in exactly one bucket


def test_clv_and_return_of_a_bet():
    early = [[0.50, 0.25, 0.25], [0.50, 0.25, 0.25]]
    closing = [[0.45, 0.25, 0.30], [0.55, 0.25, 0.20]]       # the away price shortens, then drifts
    model = [[0.40, 0.25, 0.35], [0.40, 0.25, 0.35]]         # +10 on the away side both times
    odds = [[1.9, 3.8, 3.8], [1.9, 3.8, 3.8]]
    m = ec.Matches(frame(model, early, closing, [2, 0], odds), "ens")
    b = m.bets(m.picks(), "avg")
    assert b["bets"] == 2 and b["matches"] == 2 and b["outcomes"] == {"home": 0, "draw": 0, "away": 2}
    assert b["clv"]["mean"] == pytest.approx(((3.8 * 0.30 - 1) + (3.8 * 0.20 - 1)) / 2)
    assert b["line_move"]["mean"] == pytest.approx((0.05 - 0.05) / 2)
    assert b["realised_return"]["mean"] == pytest.approx(((3.8 - 1) + (-1)) / 2)
    assert b["won"] == 0.5 and b["odds"] == pytest.approx(3.8)
    assert b["longer_than_close"] == 0.5                      # 3.8 beats 1/0.30, not 1/0.20
    one = m.bets(m.picks(), "avg", rows=np.array([True, False]))
    assert one["bets"] == 1 and one["clv"]["mean"] == pytest.approx(3.8 * 0.30 - 1)
    assert m.bets(m.picks(0.5), "avg") == {"bets": 0}


def test_a_missing_price_drops_the_bet_not_the_match():
    early = [[0.50, 0.25, 0.25], [0.50, 0.25, 0.25]]
    model = [[0.40, 0.25, 0.35], [0.40, 0.25, 0.35]]
    o = frame(model, early, early, [2, 2])
    o.loc[1, ["b365_h", "b365_d", "b365_a"]] = np.nan
    m = ec.Matches(o, "ens")
    assert m.bets(m.picks(), "avg")["bets"] == 2 and m.bets(m.picks(), "b365")["bets"] == 1


def test_bootstrap_is_over_matches_and_repeatable():
    w = ec.boot_weights(50)
    assert w.shape == (ec.N_BOOT, 50) and (w.sum(1) == 50).all()
    assert (w == ec.boot_weights(50)).all()
    x = np.arange(50.0)
    r = ec.ratio(w, x, np.ones(50))
    assert r["mean"] == pytest.approx(x.mean()) and r["low"] < r["mean"] < r["high"]
    assert ec.ratio(w, x, np.zeros(50)) is None


def test_verdicts():
    def block(clv, move, best=(-0.01, -0.02, 0.0)):
        triple = lambda v: dict(mean=v[0], low=v[1], high=v[2])
        row = lambda c: dict(clv=triple(c), line_move=triple(move), realised_return=triple((0, -1, 1)), bets=10)
        return dict(rule=dict(avg=row(clv), max=row(best)))
    win, lose = (0.02, 0.01, 0.03), (-0.05, -0.06, -0.04)
    toward, flat = (0.004, 0.002, 0.006), (0.001, -0.001, 0.003)
    assert ec.verdict(block(win, toward), block(win, toward))["verdict"] == "value"
    assert ec.verdict(block(win, toward), block(lose, toward))["verdict"] == "signal, no value"   # Bundesliga disagrees
    v = ec.verdict(block(lose, toward), block(lose, toward))
    assert v["verdict"] == "signal, no value" and not v["forward_test"]
    assert ec.verdict(block(lose, toward, best=win), None)["forward_test"]
    v = ec.verdict(block(lose, flat), block(lose, flat))
    assert v["verdict"] == "nothing" and not v["forward_test"] and v["clv_inside_expected_range"]


def test_source_odds_follow_the_pointer_back_to_the_file(tmp_path):
    folder = tmp_path / "football-data" / "2425"
    folder.mkdir(parents=True)
    (folder / "E0.csv").write_text("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,MaxH,MaxD,MaxA\n"
                                   "E0,17/08/2024,Arsenal,Wolves,2,0,1.25,7.5,15\n"
                                   "E0,17/08/2024,Everton,Brighton,0,3,2.9,3.6,0\n")
    (folder / "D1.csv").write_text("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,BbMxH,BbMxD,BbMxA\n"
                                   "D1,24/08/2024,Mainz,Union Berlin,1,1,2.3,3.5,3.4\n")
    table = pd.DataFrame({"src_file": ["football-data/2425/E0.csv", "football-data/2425/D1.csv", "football-data/2425/E0.csv"],
                          "src_row": [3, 2, 2]}, index=[7, 8, 9])
    got = ec.source_odds(table, str(tmp_path), ec.MAX_EARLY, "max")
    assert list(got.columns) == ["max_h", "max_d", "max_a"] and list(got.index) == [7, 8, 9]
    assert got.loc[9].tolist() == [1.25, 7.5, 15.0] and got.loc[8].tolist() == [2.3, 3.5, 3.4]
    assert got.loc[7, ["max_h", "max_d"]].tolist() == [2.9, 3.6] and np.isnan(got.loc[7, "max_a"])   # 0 means missing


def test_same_price_excess_compares_with_other_bets_at_the_same_odds():
    # 200 matches, every outcome at fair odds of 3.0. The model likes the home side in the first 100,
    # and those home sides never win; everything else wins one time in three.
    n = 200
    early = np.full((n, 3), 1 / 3)
    model = early.copy()
    model[:100] = [0.43, 0.2833, 0.2867]
    results = np.where(np.arange(n) < 100, 1 + np.arange(n) % 2, np.arange(n) % 3)
    m = ec.Matches(frame(model, early, early, results), "ens")
    x = m.same_price_excess(m.picks(), bins=1)
    others = (100 * 3.0 + 100 * 3.0 - 500) / 500           # the 500 other bets: 200 winners at 3.0
    assert x["bets"] == 100 and x["mean"] == pytest.approx(-1.0 - others)
    assert x["low"] <= x["mean"] <= x["high"] < 0


def test_forecasters_orders_early_closing_and_model():
    rng = np.random.default_rng(3)
    truth = rng.dirichlet([6, 3, 4], 3000)
    results = np.array([rng.choice(3, p=p) for p in truth])
    early = 0.8 * truth + 0.2 / 3
    model = 0.5 * truth + 0.5 / 3
    f = ec.Matches(frame(model, early, truth, results), "ens").forecasters()
    assert f["rps"]["closing"] < f["rps"]["early"] < f["rps"]["model"]
    assert f["early_minus_closing"]["mean"] > 0 and f["model_minus_early"]["mean"] > 0
    assert f["model_minus_closing"]["mean"] == pytest.approx(f["early_minus_closing"]["mean"] + f["model_minus_early"]["mean"])
