"""Tests for the Understat fetcher's outage handling and the football-data xG fallback.

    pip install pytest numpy pandas && python -m pytest analysis/pipeline/tests -q

No network: Understat's answers are replaced by the ones it actually gave in October and November 2026.
"""
import json
import os
import sys
import urllib.error

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import fetch_understat as fu  # noqa: E402
import understat  # noqa: E402

HOLDING_PAGE = ('<!DOCTYPE html> <html> <head> <title>Understat.com</title> <meta charset="UTF-8" /> '
                '<link href="/css/errors.css" rel="stylesheet" media="screen"> </head> '
                '<body class="th"><div class="error">We will come back soon</div></body></html>').encode()


def season_json(played, total=306):
    dates = [dict(id=str(i), isResult=i < played, h=dict(title="Freiburg"), a=dict(title="Bayern Munich"),
                  goals=dict(h="1", a="3"), xG=dict(h="0.8", a="3.1"), datetime="2026-10-25 16:30:00")
             for i in range(total)]
    return json.dumps(dict(dates=dates)).encode()


def run(monkeypatch, tmp_path, answer, previous=None, seasons=2):
    """Run the fetcher with `answer(url)` in place of the network; returns (exit code, manifest)."""
    def fake_get(url, headers, **kw):
        out = answer(url)
        if isinstance(out, Exception):
            raise out
        return out
    monkeypatch.setattr(fu, "get", fake_get)
    monkeypatch.setattr(fu.time, "sleep", lambda s: None)
    first = fu.dt.date.today().year - (0 if fu.dt.date.today().month >= 7 else 1) - seasons + 1
    argv = ["--out", str(tmp_path / "out"), "--from", str(first)] + (["--previous", str(previous)] if previous else [])
    code = fu.main(argv)
    return code, json.load(open(tmp_path / "out" / "understat" / "manifest.json"))


def store(tmp_path, played):
    """A stored copy with one season file per season the fetcher will ask for."""
    folder = tmp_path / "stored" / "Bundesliga"
    folder.mkdir(parents=True)
    year = fu.dt.date.today().year - (0 if fu.dt.date.today().month >= 7 else 1)
    for season in (year - 1, year):
        (folder / f"{season}.json").write_bytes(season_json(played))
    return tmp_path / "stored"


def test_normal_run_saves_every_season(monkeypatch, tmp_path):
    code, m = run(monkeypatch, tmp_path, lambda url: season_json(63))
    assert code == 0 and m["status"] == "ok" and len(m["files"]) == 2 and not m["failed"]
    assert m["files"][0]["played"] == 63 and m["files"][0]["route"] == "getLeagueData"


def test_holding_page_is_an_outage_not_a_failure(monkeypatch, tmp_path, capsys):
    # 16 November 2026: the data endpoint answered with nothing, the league page with "We will come back soon"
    answer = lambda url: b"" if "getLeagueData" in url else HOLDING_PAGE
    code, m = run(monkeypatch, tmp_path, answer, previous=store(tmp_path, 63))
    assert code == fu.EXIT_UNAVAILABLE and m["status"] == "unavailable" and not m["files"] and not m["failed"]
    assert "We will come back soon" in m["reason"]
    last_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "126 played matches" in last_line and "2026-10-25" in last_line and "football-data" in last_line


@pytest.mark.parametrize("error", [
    urllib.error.URLError("timed out"),                               # 2 November 2026
    urllib.error.URLError("[Errno -5] No address associated with hostname"),
    urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None),
    TimeoutError("timed out"),
])
def test_no_answer_is_an_outage(monkeypatch, tmp_path, error):
    code, m = run(monkeypatch, tmp_path, lambda url: error)
    assert code == fu.EXIT_UNAVAILABLE and m["status"] == "unavailable"


def test_a_page_we_cannot_read_still_fails(monkeypatch, tmp_path):
    # Understat is up but its layout changed: that needs a look, so the run must fail
    page = ("<html><body>" + "<div>league table</div>" * 500 + "</body></html>").encode()
    code, m = run(monkeypatch, tmp_path, lambda url: b"<html>" if "getLeagueData" in url else page)
    assert code == 1 and m["status"] == "failed" and len(m["failed"]) == 2


def test_blocked_is_a_failure(monkeypatch, tmp_path):
    code, m = run(monkeypatch, tmp_path, lambda url: urllib.error.HTTPError("u", 403, "Forbidden", {}, None))
    assert code == 1 and m["status"] == "failed"


def test_going_down_halfway_fails_and_keeps_nothing_partial(monkeypatch, tmp_path):
    seen = []
    def answer(url):
        seen.append(url)
        return season_json(306) if len(seen) == 1 else urllib.error.URLError("timed out")
    code, m = run(monkeypatch, tmp_path, answer)
    assert code == 1 and m["status"] == "failed" and len(m["files"]) == 1 and len(m["failed"]) == 1


def test_fewer_played_matches_than_stored_is_refused(monkeypatch, tmp_path):
    # Understat back from a backup that misses recent matches must not replace the stored copy
    code, m = run(monkeypatch, tmp_path, lambda url: season_json(54), previous=store(tmp_path, 63))
    assert code == 1 and m["status"] == "failed" and not m["files"]
    assert "stored copy has 63" in m["failed"][0]["error"]


def test_league_page_route_still_works(monkeypatch, tmp_path):
    blob = json.dumps(json.loads(season_json(10, 20))["dates"]).replace('"', "\\x22")
    page = f"<html><script>var datesData = JSON.parse('{blob}');</script></html>".encode()
    code, m = run(monkeypatch, tmp_path, lambda url: b"" if "getLeagueData" in url else page)
    assert code == 0 and m["files"][0]["route"] == "league page" and m["files"][0]["played"] == 10


# --- football-data xG where Understat has none ---

def table(n_both=40, n_gap=5, n_d2=3, seed=1):
    rng = np.random.default_rng(seed)
    n = n_both + n_gap
    fd = rng.gamma(4, 0.4, size=(n, 2))
    us = 0.1 + 1.05 * fd + rng.normal(0, 0.05, size=(n, 2))
    m = pd.DataFrame(dict(div="D1", date=pd.date_range("2026-08-28", periods=n), home="A", away="B",
                          fd_hxg=fd[:, 0], fd_axg=fd[:, 1], hxg=us[:, 0], axg=us[:, 1]))
    m.loc[n_both:, ["hxg", "axg"]] = np.nan
    d2 = pd.DataFrame(dict(div="D2", date=pd.date_range("2026-11-01", periods=n_d2), home="C", away="D",
                           fd_hxg=1.0, fd_axg=1.0, hxg=np.nan, axg=np.nan))
    return pd.concat([m, d2], ignore_index=True), us


def test_fallback_fills_only_the_gap_on_understats_scale():
    m, us = table()
    before = m.copy()
    info = understat.fill_from_football_data(m, report=False)
    assert info["filled"] == 5 and info["overlap"] == 40
    assert abs(info["slope"] - 1.05) < 0.03 and abs(info["intercept"] - 0.1) < 0.05
    assert m.hxg[:40].equals(before.hxg[:40]) and m.axg[:40].equals(before.axg[:40])     # Understat untouched
    assert np.allclose(m.hxg[40:45], us[40:, 0], atol=0.15) and np.allclose(m.axg[40:45], us[40:, 1], atol=0.15)
    assert list(m.xg_src[:40].unique()) == ["understat"] and list(m.xg_src[40:45].unique()) == ["football-data"]
    assert m.hxg[45:].isna().all() and (m.xg_src[45:] == "").all()                      # 2. Bundesliga: no xG, as before


def test_fallback_uses_raw_numbers_without_enough_overlap():
    m, _ = table(n_both=10)
    info = understat.fill_from_football_data(m, report=False)
    assert info["slope"] == 1.0 and info["intercept"] == 0.0
    assert np.allclose(m.hxg[10:15], m.fd_hxg[10:15])


def test_fallback_does_nothing_when_understat_is_complete_or_columns_are_missing():
    m, _ = table(n_gap=0)
    before = m.copy()
    assert understat.fill_from_football_data(m, report=False) is None
    assert m.hxg.equals(before.hxg) and (m.xg_src[:40] == "understat").all()
    old = before.drop(columns=["fd_hxg", "fd_axg"])
    assert understat.fill_from_football_data(old, report=False) is None
