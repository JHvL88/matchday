"""Tests for the multi-league pieces: the league list, per-league match tables, the pooled XGBoost trainer.

    pip install pytest numpy pandas && python -m pytest analysis/pipeline/tests -q

No network and no real data: small football-data-style files are written on the spot.
The pooled-trainer test also needs xgboost and is skipped without it.
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import build_matches  # noqa: E402
import fetch_football_data as ffd  # noqa: E402
from leagues import HOME, LEAGUES, divisions, league_names  # noqa: E402

HEADER = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HS,AS,HST,AST,HR,AR,AvgCH,AvgCD,AvgCA"


def write(source, folder, code, rows):
    path = source / "football-data" / folder
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{code}.csv").write_text("\n".join([HEADER] + [f"{code},{r},10,8,4,3,0,0,2.1,3.4,3.6" for r in rows]) + "\n")


def test_league_names():
    assert league_names(["all"]) == list(LEAGUES) and league_names(None) == list(LEAGUES)
    assert league_names(["fra", "GER", "fra"]) == ["GER", "FRA"]          # Germany first, no repeats
    assert divisions("ENG") == ("E0", "E1") and HOME == "GER"
    with pytest.raises(SystemExit):
        league_names(["NED"])


def test_fetcher_asks_for_germany_alone_unless_told(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setattr(ffd, "download", lambda url, **kw: (asked.append(url) or (b"x", {})))
    monkeypatch.setattr(ffd.time, "sleep", lambda s: None)
    ffd.main(["--out", str(tmp_path / "a"), "--to", "2006"])
    assert len(asked) == 14 and all(u.endswith(("D1.csv", "D2.csv")) for u in asked)      # 2000/01-2006/07, as before
    german = list(asked)
    asked.clear()
    ffd.main(["--out", str(tmp_path / "b"), "--to", "2006", "--leagues", "all"])
    assert asked[:14] == german                                           # Germany first, same order
    assert len(asked) == 14 + 4 * 2 * 2                                   # the others start in 2005/06
    assert asked[14].endswith("0506/E0.csv") and asked[-1].endswith("0607/F2.csv")


def test_other_league_table_has_the_same_shape(tmp_path):
    write(tmp_path, "1920", "E0", ["21/09/2019,Arsenal,Chelsea,2,1", "11/07/2020,Chelsea,Arsenal,0,0"])
    write(tmp_path, "1920", "E1", ["21/09/2019,Leeds,Derby,1,1"])
    write(tmp_path, "1920", "D1", ["21/09/2019,Dortmund,Mainz,3,0"])
    eng = build_matches.build(str(tmp_path), league="ENG")
    assert sorted(eng["div"].unique()) == ["D1", "D2"]                    # tiers, not football-data's codes
    assert set(eng.fd_div) == {"E0", "E1"} and set(eng.league) == {"ENG"}
    assert "Dortmund" not in set(eng.home)
    restart = eng[eng.date == "2020-07-11"].iloc[0]
    assert restart.season == 2020 and restart.fd_season == 2019          # the summer of 2020: July counts as the new season
    ger = build_matches.build(str(tmp_path))
    assert list(ger.home) == ["Dortmund"] and ger.league.iloc[0] == "GER" and ger["div"].iloc[0] == "D1"
    assert list(ger.columns) == list(eng.columns)


def test_missing_league_files_say_what_to_fetch(tmp_path):
    write(tmp_path, "1920", "D1", ["21/09/2019,Dortmund,Mainz,3,0"])
    with pytest.raises(FileNotFoundError, match="--leagues ITA"):
        build_matches.build(str(tmp_path), league="ITA")


def season_rows(teams, season, rng, strength):
    """A double round robin with goals driven by fixed team strengths."""
    rows, day = [], pd.Timestamp(f"{season}-08-10")
    for i, (h, a) in enumerate(itertools.permutations(teams, 2)):
        lam_h, lam_a = np.exp(0.25 + strength[h] - strength[a]), np.exp(strength[a] - strength[h])
        hg, ag = rng.poisson(lam_h), rng.poisson(lam_a)
        rows.append(f"{(day + pd.Timedelta(days=3 * (i // 4))):%d/%m/%Y},{h},{a},{hg},{ag}")
    return rows


def test_pooled_trainer_uses_every_league_and_keeps_own_models_separate(tmp_path):
    pytest.importorskip("xgboost")
    import pooled_xgb
    rng = np.random.default_rng(3)
    tables = {}
    for league, (top, second, _) in list(LEAGUES.items())[:2]:
        teams = [f"{league}{i}" for i in range(8)]
        strength = dict(zip(teams, np.linspace(-0.5, 0.5, 8)))
        for season in range(2008, 2013):
            write(tmp_path, f"{season % 100:02d}{(season + 1) % 100:02d}", top, season_rows(teams, season, rng, strength))
        path = tmp_path / f"{league}.csv"
        build_matches.build(str(tmp_path), league=league).to_csv(path, index=False)
        tables[league] = str(path)
    out, rounds, n_pool = pooled_xgb.walk_forward(tables, [2012], log=lambda m: None)
    assert set(out.league) == {"GER", "ENG"} and len(out) == 2 * 56          # every top-flight match of the test season
    assert out.drop(columns=["league", "key"]).notna().all().all() and (out.drop(columns=["league", "key"]) > 0).all().all()
    assert {"xgbp_lh", "xgbq_lh", "xgbo_lh"} <= set(out.columns)
    assert set(rounds) == {"xgbp:2012", "xgbq:2012", "own:GER:2012", "own:ENG:2012"}
    # the own-league model matches a model trained on that league's table alone
    alone, _, n_alone = pooled_xgb.walk_forward({"ENG": tables["ENG"]}, [2012], log=lambda m: None)
    eng = out[out.league == "ENG"].set_index("key").loc[alone.key]
    assert np.allclose(eng.xgbo_lh.values, alone.xgbo_lh.values) and n_pool == 2 * n_alone
