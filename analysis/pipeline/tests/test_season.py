"""Tests for the season simulator (season_sim.py), its backtest helpers and the browser engine (season/sim.js).

    python -m pytest analysis/pipeline/tests -q

No network and no rating fit: ratings are made up, OpenLigaDB is a payload in its documented format.
The browser check runs only where Node.js is installed.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import season_sim as ss  # noqa: E402
import season_backtest as sb  # noqa: E402


def score_grid(lh, la, rho, maxg=11):
    """Dixon-Coles grid written out independently of bl_models (no JAX needed)."""
    from scipy.stats import poisson
    g = np.arange(maxg)
    M = np.outer(poisson.pmf(g, lh), poisson.pmf(g, la))
    M[0, 0] *= 1 - lh * la * rho
    M[0, 1] *= 1 + lh * rho
    M[1, 0] *= 1 + la * rho
    M[1, 1] *= 1 - rho
    return M / M.sum()


@pytest.mark.parametrize("lh, la, rho", [(1.6, 1.1, -0.06), (3.4, 0.8, -0.06), (1.2, 1.0, 0.08)])
def test_dc_sample_matches_the_score_grid(lh, la, rho):
    n = 400_000
    x, y = ss.dc_sample(np.full(n, lh), np.full(n, la), rho, np.random.default_rng(1))
    M = score_grid(lh, la, rho)
    for i, j in [(0, 0), (0, 1), (1, 0), (1, 1), (2, 1)]:
        emp = np.mean((x == i) & (y == j))
        se = np.sqrt(M[i, j] * (1 - M[i, j]) / n)
        assert abs(emp - M[i, j]) < 4.5 * se, (i, j, emp, M[i, j])


def flat_ratings(teams, strength=None, rho=0.0):
    strength = strength or {}
    return ss.Ratings(att={t: strength.get(t, 0.0) for t in teams}, de={t: strength.get(t, 0.0) for t in teams},
                      mu=0.3, home=0.25, rho=rho)


def test_finished_season_keeps_its_table():
    teams = ["A", "B", "C", "D"]
    table0 = {"A": (10, 5, 9, 6), "B": (10, 2, 8, 6), "C": (4, -3, 4, 6), "D": (1, -4, 2, 6)}
    res = ss.simulate(teams, table0, [], flat_ratings(teams), sigma=0.1, n=500, seed=3)
    assert res.pos[0, 0] == 500 and res.pos[1, 1] == 500 and res.pos[3, 3] == 500
    assert np.allclose(res.pts_sum / res.n, [10, 10, 4, 1])


def test_ties_after_goals_are_split_at_random():
    teams = ["A", "B"]
    table0 = {"A": (3, 0, 2, 2), "B": (3, 0, 2, 2)}
    res = ss.simulate(teams, table0, [], flat_ratings(teams), sigma=0, n=4000, seed=5)
    assert 0.45 < res.pos[0, 0] / res.n < 0.55


def test_stakes_average_back_to_the_overall_chances():
    teams = ["A", "B", "C", "D"]
    fixtures = [(h, a) for h in teams for a in teams if h != a]
    table0 = {t: (0, 0, 0, 0) for t in teams}
    rt = flat_ratings(teams, {"A": 0.3, "D": -0.3}, rho=-0.06)
    res = ss.simulate(teams, table0, fixtures, rt, sigma=0.05, n=20_000, seed=7, stakes=[0])
    acc = res.stakes[0]
    assert acc["n"].sum() == res.n
    mixed = sum(acc["pos"][o] for o in range(3))
    assert np.array_equal(mixed, res.pos)
    summary = ss.stakes_summary(res, fixtures, teams)[0]
    # the home side (A) wins the title more often when it wins this match than when it loses it
    assert summary["cond"]["home"][0]["title"] > summary["cond"]["home"][2]["title"]


def test_title_settled_counts_every_season():
    teams = ["A", "B", "C"]
    fixtures = [("A", "B"), ("B", "C"), ("C", "A"), ("B", "A"), ("C", "B"), ("A", "C")]
    schedule = [1, 1, 2, 2, 3, 3]
    table0 = {t: (0, 0, 0, 0) for t in teams}
    res = ss.simulate(teams, table0, fixtures, flat_ratings(teams, {"A": 1.0}), sigma=0, n=3000, seed=2, schedule=schedule)
    assert sum(res.clinch.values()) == res.n
    assert set(res.clinch) <= {1, 2, 3}
    # a 30-point lead with two games left is already settled
    lead = {"A": (30, 20, 30, 4), "B": (0, -10, 2, 4), "C": (0, -10, 2, 4)}
    res = ss.simulate(teams, lead, fixtures[4:], flat_ratings(teams), sigma=0, n=200, seed=2, schedule=[5, 5])
    assert res.clinch == {0: 200}


def test_doubt_widens_the_range():
    teams = [f"T{i}" for i in range(6)]
    fixtures = [(h, a) for h in teams for a in teams if h != a]
    table0 = {t: (0, 0, 0, 0) for t in teams}
    rt = flat_ratings(teams, {"T0": 0.4, "T5": -0.4})
    sure = ss.simulate(teams, table0, fixtures, rt, sigma=0, n=20_000, seed=1)
    doubt = ss.simulate(teams, table0, fixtures, rt, sigma=0.2, n=20_000, seed=1)
    assert doubt.pos[0, 0] < sure.pos[0, 0]           # the favourite is less sure of the title
    assert doubt.pos[5, 0] > sure.pos[5, 0]           # the weakest side wins it more often


def test_standings_and_market_probabilities():
    played = pd.DataFrame(dict(home=["A", "B"], away=["B", "A"], hg=[2, 1], ag=[0, 1]))
    tab = ss.standings(played, ["A", "B"])
    assert tab["A"] == (4, 2, 3, 2) and tab["B"] == (1, -2, 1, 2)
    df = pd.DataFrame(dict(avgc_h=[2.0, np.nan], avgc_d=[3.5, np.nan], avgc_a=[4.0, np.nan],
                           avg_h=[1.9, 1.5], avg_d=[3.6, 4.0], avg_a=[4.2, 6.0]))
    q = ss.market_probabilities(df)
    assert np.allclose(q.sum(1), 1)
    inv = np.array([1 / 2.0, 1 / 3.5, 1 / 4.0])
    assert np.allclose(q[0], inv / inv.sum())            # the closing price wins where it exists
    inv = np.array([1 / 1.5, 1 / 4.0, 1 / 6.0])
    assert np.allclose(q[1], inv / inv.sum())


def ol(match_id, md, kickoff, home, away, score=None):
    return {"matchID": match_id, "matchDateTimeUTC": kickoff, "group": {"groupOrderID": md},
            "team1": {"teamId": home, "teamName": f"T{home}"}, "team2": {"teamId": away, "teamName": f"T{away}"},
            "matchIsFinished": score is not None,
            "matchResults": [] if score is None else [{"resultTypeID": 2, "pointsTeam1": score[0], "pointsTeam2": score[1]}]}


def test_completed_matchday_skips_postponed_matches():
    now = pd.Timestamp("2026-11-18T08:00Z")
    payload = [ol(1, 1, "2026-11-01T14:30:00Z", 1, 2, (1, 0)), ol(2, 1, "2026-11-02T14:30:00Z", 3, 4, (0, 0)),
               ol(3, 2, "2026-11-08T14:30:00Z", 1, 3, (2, 2)), ol(4, 2, "2026-12-09T19:30:00Z", 2, 4),     # postponed
               ol(5, 3, "2026-11-22T14:30:00Z", 4, 1), ol(6, 3, "2026-11-22T14:30:00Z", 2, 3)]
    m = ss.openligadb_matches(payload)
    assert ss.completed_matchday(m, now) == 2
    # once the postponed match's date has passed without a result, matchday 2 is incomplete again
    assert ss.completed_matchday(m, pd.Timestamp("2026-12-10T08:00Z")) == 1
    payload[2] = ol(3, 2, "2026-11-08T14:30:00Z", 1, 3)        # matchday 2 not played yet
    assert ss.completed_matchday(ss.openligadb_matches(payload), now) == 1
    assert ss.completed_matchday(ss.openligadb_matches([ol(1, 1, "2026-11-01T14:30:00Z", 1, 2)]), now) == 0


def test_backtest_checkpoints_and_rps():
    dates = pd.date_range("2020-08-01", periods=34, freq="7D").repeat(9)
    cur = pd.DataFrame(dict(date=dates[:306], home=["A"] * 306, away=["B"] * 306))
    cut, played, rem = sb.checkpoint(cur, 0)
    assert len(played) == 0 and len(rem) == 306
    cut, played, rem = sb.checkpoint(cur, 10)
    assert len(played) == 90 and len(rem) == 216
    P = np.eye(18)
    y = np.arange(18)
    assert np.allclose(sb.rps_positions(P, y), 0)
    uniform = sb.rps_positions(np.full((18, 18), 1 / 18), y).mean()
    assert abs(uniform - 0.1759) < 1e-3


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_browser_engine_agrees_with_python(tmp_path):
    teams = [str(i) for i in range(1, 7)]
    fixtures = [(h, a) for h in teams for a in teams if h != a]
    strength = {"1": 0.35, "2": 0.15, "5": -0.2, "6": -0.3}
    rt = flat_ratings(teams, strength, rho=-0.06)
    table0 = {t: (0, 0, 0, 0) for t in teams}
    n = 40_000
    py = ss.simulate(teams, table0, fixtures, rt, sigma=0.1, n=n, seed=4)
    job = dict(teams=teams, table={t: [0, 0, 0] for t in teams}, fixtures=[dict(home=h, away=a) for h, a in fixtures],
               ratings=dict(mu=rt.mu, home=rt.home, rho=rt.rho, att=rt.att, de=rt.de), sigma=0.1, n=n, seed=9)
    script = tmp_path / "run.js"
    script.write_text(f"""require({json.dumps(os.path.join(ROOT, 'season', 'sim.js'))});
const job = {json.dumps(job)};
const r = SeasonSim.run(job);
console.log(JSON.stringify(Array.from(r.pos)));""")
    js = np.array(json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)).reshape(6, 6)
    p_py = py.pos / n
    p_js = js / n
    se = np.sqrt(np.maximum(p_py * (1 - p_py), 1e-4) * 2 / n)
    assert np.all(np.abs(p_js - p_py) < 4.5 * se), np.round(p_js - p_py, 4)
