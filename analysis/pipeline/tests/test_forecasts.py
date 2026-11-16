"""Tests for the weekly forecast publisher (site_forecasts.py).

    python -m pytest analysis/pipeline/tests -q

No network and no model fit: OpenLigaDB is a saved payload in its documented format, and
forecast.py's output is handed in.
"""
import json
import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import site_forecasts  # noqa: E402
from site_odds import fixtures  # noqa: E402

CLUBS = [(40, "FC Bayern München", "Bayern Munich"), (65, "1. FC Köln", "FC Koln"),
         (87, "Borussia Mönchengladbach", "M'gladbach"), (7, "Borussia Dortmund", "Dortmund")]


def ol_match(match_id, matchday, kickoff, home, away, score=None):
    return {"matchID": match_id, "matchDateTimeUTC": kickoff, "group": {"groupOrderID": matchday},
            "team1": {"teamId": home[0], "teamName": home[1]}, "team2": {"teamId": away[0], "teamName": away[1]},
            "matchIsFinished": score is not None,
            "matchResults": [] if score is None else [{"resultTypeID": 2, "pointsTeam1": score[0], "pointsTeam2": score[1]}]}


def season_payload():
    b, k, g, d = CLUBS
    return [ol_match(1, 9, "2026-11-07T14:30:00Z", b, g, (2, 0)), ol_match(2, 9, "2026-11-08T16:30:00Z", d, k, (1, 1)),
            ol_match(11, 10, "2026-11-20T19:30:00Z", b, k), ol_match(12, 10, "2026-11-21T14:30:00Z", g, d),
            ol_match(21, 11, "2026-11-28T14:30:00Z", k, g)]


def match_table(with_sunday=True):
    rows = [dict(div="D1", season=2026, date="2026-11-07", home="Bayern Munich", away="M'gladbach", hg=2, ag=0)]
    if with_sunday:
        rows.append(dict(div="D1", season=2026, date="2026-11-08", home="Dortmund", away="FC Koln", hg=1, ag=1))
    else:   # the clubs still have to be in the table, from an earlier round
        rows.append(dict(div="D1", season=2026, date="2026-10-31", home="FC Koln", away="Dortmund", hg=0, ag=3))
    return pd.DataFrame(rows)


def model(h, d, a):
    return dict(H=h, D=d, A=a, lh=1.9, la=1.1, over25=0.61, btts=0.58, mostLikely=dict(score=[2, 1], p=0.0871))


def forecast_output():
    grid = [[round(0.01 * (i + 1) * (j + 1) / 10, 6) for j in range(11)] for i in range(11)]
    fx = []
    for date, home, away in [("2026-11-20", "Bayern Munich", "FC Koln"), ("2026-11-21", "M'gladbach", "Dortmund")]:
        fx.append(dict(date=date, home=home, away=away, grid=grid,
                       models=dict(dc=model(0.70, 0.18, 0.12), bay=model(0.74, 0.15, 0.11),
                                   xgb=model(0.66, 0.19, 0.15), ens=model(0.69995, 0.17333, 0.12661))))
    return dict(freeze="2026-11-19", models="xG versions, XGBoost trained on five leagues", fixtures=fx,
                inputs=dict(last_match="2026-11-08", code_commit="abc123", matches_sha256="f00"))


@pytest.fixture
def files(tmp_path):
    ol, table, odds = tmp_path / "ol.json", tmp_path / "matches.csv", tmp_path / "odds.json"
    ol.write_text(json.dumps(season_payload()), encoding="utf-8")
    match_table().to_csv(table, index=False)
    odds.write_text(json.dumps({"season": 2026, "matchdays": {"10": {"quoted": "2026-11-19", "books": 21,
                                                                 "matches": {"11": [1.08, 11.5, 19.7]}}}}))
    return dict(ol=str(ol), table=str(table), odds=str(odds), out=str(tmp_path / "forecasts.json"))


def run(files, now, *extra, forecast=None):
    args = [files["table"], "--season", "2026", "--out", files["out"], "--openligadb", files["ol"],
            "--odds", files["odds"], "--now", now, *extra]
    return site_forecasts.main(args, forecast_json=forecast_output() if forecast is None else forecast)


@pytest.mark.parametrize("now, expected", [
    ("2026-11-16T08:00:00Z", None),       # four and a half days before Friday's kick-off: too early
    ("2026-11-18T08:00:00Z", 10),         # inside 72 hours
    ("2026-11-20T19:00:00Z", 10),         # half an hour before kick-off still counts
    ("2026-11-20T19:31:00Z", None),       # matchday 10 has started; matchday 11 is a week away
    ("2026-11-26T08:00:00Z", 11),
])
def test_due_window(now, expected):
    fx = fixtures(season_payload())
    assert site_forecasts.due_matchday(fx, site_forecasts.utc(now), {})[0] == expected


def test_published_matchday_is_not_due_again():
    fx = fixtures(season_payload())
    assert site_forecasts.due_matchday(fx, site_forecasts.utc("2026-11-19T08:00:00Z"), {"10": {}})[0] is None


def test_publishes_one_matchday(files):
    assert run(files, "2026-11-19T08:41:00Z") == 0
    site = json.load(open(files["out"], encoding="utf-8"))
    block = site["matchdays"]["10"]
    assert site["season"] == 2026 and list(site["matchdays"]) == ["10"]
    assert block["freeze"] == "2026-11-19" and block["published"] == "2026-11-19T08:41:00Z"
    assert set(block["matches"]) == {"11", "12"}
    m = block["matches"]["11"]
    assert m["home"] == "FC Bayern München" and m["away"] == "1. FC Köln" and m["kickoff"] == "2026-11-20T19:30:00Z"
    assert m["model"] == [0.7, 0.1733, 0.1267] and abs(sum(m["model"]) - 1) < 1e-9
    assert set(m["models"]) == {"dixonColes", "bayesian", "xgboost"}
    assert len(m["grid"]) == 6 and all(len(line) == 6 for line in m["grid"])
    assert m["mostLikely"] == {"score": [2, 1], "p": 0.087}
    assert m["market"] == {"odds": [1.08, 11.5, 19.7], "quoted": "2026-11-19", "books": 21}
    assert "market" not in block["matches"]["12"]          # no odds recorded for that match


def test_fixture_names_are_translated_for_the_models(files):
    fx = fixtures(season_payload())
    names = site_forecasts.table_names(pd.read_csv(files["table"], parse_dates=["date"]), 2026)
    rows = site_forecasts.fixture_rows(fx, 10, names)
    args = site_forecasts.forecast_args("m.csv", "o.json", "2026-11-19", rows, "tables")
    assert args == ["m.csv", "o.json", "--freeze", "2026-11-19", "--xg",
                    "--fixture", "2026-11-20", "Bayern Munich", "FC Koln",
                    "--fixture", "2026-11-21", "M'gladbach", "Dortmund", "--pool", "tables"]


def test_never_refits_a_published_matchday(files):
    run(files, "2026-11-18T08:41:00Z")
    first = open(files["out"], encoding="utf-8").read()
    changed = forecast_output()
    changed["fixtures"][0]["models"]["ens"] = model(0.5, 0.25, 0.25)
    assert run(files, "2026-11-19T08:41:00Z", forecast=changed) == 0
    assert run(files, "2026-11-19T08:41:00Z", "--matchday", "10", forecast=changed) == 0
    assert open(files["out"], encoding="utf-8").read() == first


def test_force_replaces_and_says_so(files):
    run(files, "2026-11-18T08:41:00Z")
    changed = forecast_output()
    changed["fixtures"][0]["models"]["ens"] = model(0.5, 0.25, 0.25)
    run(files, "2026-11-19T08:41:00Z", "--matchday", "10", "--force", forecast=changed)
    block = json.load(open(files["out"], encoding="utf-8"))["matchdays"]["10"]
    assert block["matches"]["11"]["model"] == [0.5, 0.25, 0.25]
    assert "replaces the forecast published 2026-11-18T08:41:00Z" in block["note"]


def test_no_forecast_after_kick_off(files):
    with pytest.raises(SystemExit, match="has started"):
        run(files, "2026-11-20T19:31:00Z", "--matchday", "10")


def test_waits_for_missing_results_then_goes_ahead(files, capsys):
    match_table(with_sunday=False).to_csv(files["table"], index=False)
    assert run(files, "2026-11-18T08:41:00Z") == 0                 # 59 hours before kick-off: wait
    assert not os.path.exists(files["out"])
    assert "Borussia Dortmund v 1. FC Köln" in capsys.readouterr().out
    assert run(files, "2026-11-19T20:00:00Z") == 0                 # 23.5 hours before: publish, with a note
    block = json.load(open(files["out"], encoding="utf-8"))["matchdays"]["10"]
    assert "published without 1 played match" in block["note"]


def test_check_only_reports(files, tmp_path, monkeypatch):
    out = tmp_path / "gh.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    args = ["--season", "2026", "--out", files["out"], "--openligadb", files["ol"], "--check"]
    assert site_forecasts.main(args + ["--now", "2026-11-16T08:00:00Z"]) == 0
    assert site_forecasts.main(args + ["--now", "2026-11-19T08:00:00Z"]) == 0
    assert out.read_text().splitlines() == ["due=false", "due=true", "matchday=10"]
    assert not os.path.exists(files["out"])


def test_unknown_club_stops_the_run(files):
    payload = season_payload()
    payload[2]["team2"]["teamName"] = "FC Neuland 26"
    open(files["ol"], "w", encoding="utf-8").write(json.dumps(payload))
    with pytest.raises(SystemExit, match="no club in the match table"):
        run(files, "2026-11-19T08:41:00Z")
