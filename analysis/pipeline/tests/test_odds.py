"""Tests for the odds recorder, the site export, the publication helper and the CLV grading.

    pip install pytest numpy pandas && python -m pytest analysis/pipeline/tests -q

No network: The Odds API and OpenLigaDB are replaced by payloads in their documented formats.
"""
import gzip
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import odds_api  # noqa: E402
import record_odds  # noqa: E402
from odds_store import fair, match_odds, summarise, tidy  # noqa: E402
from teams import club_key  # noqa: E402

KICKOFF = "2026-10-17T13:30:00Z"
EVENTS = [
    {"id": "e1", "sport_key": "soccer_germany_bundesliga", "commence_time": KICKOFF,
     "home_team": "Hamburger SV", "away_team": "VfB Stuttgart"},
    {"id": "e2", "sport_key": "soccer_germany_bundesliga", "commence_time": KICKOFF,
     "home_team": "Borussia Monchengladbach", "away_team": "Bayern Munich"},
    {"id": "e3", "sport_key": "soccer_germany_bundesliga", "commence_time": "2026-10-18T15:30:00Z",
     "home_team": "1. FC Köln", "away_team": "FC St. Pauli"},
]


def book(key, title, h, d, a, home, away, total=(2.5, 1.9, 1.95)):
    return {"key": key, "title": title, "markets": [
        {"key": "h2h", "last_update": "2026-10-16T08:00:00Z",
         "outcomes": [{"name": home, "price": h}, {"name": away, "price": a}, {"name": "Draw", "price": d}]},
        {"key": "totals", "last_update": "2026-10-16T08:00:00Z",
         "outcomes": [{"name": "Over", "price": total[1], "point": total[0]},
                      {"name": "Under", "price": total[2], "point": total[0]}]}]}


def odds_payload():
    out = []
    prices = {"e1": [(3.7, 4.1, 1.85), (3.9, 4.0, 1.80), (3.6, 4.2, 1.90), (3.95, 4.3, 1.83), (4.4, 4.5, 1.95)],
              "e2": [(5.0, 4.6, 1.60), (5.2, 4.5, 1.58), (4.8, 4.7, 1.62), (5.1, 4.8, 1.59), (5.6, 5.0, 1.66)],
              "e3": [(2.1, 3.5, 3.4), (2.2, 3.4, 3.3), (2.05, 3.6, 3.5), (2.15, 3.45, 3.45), (2.3, 3.7, 3.7)]}
    for e in EVENTS:
        h, a = e["home_team"], e["away_team"]
        p = prices[e["id"]]
        out.append({**e, "bookmakers": [
            book("pinnacle", "Pinnacle", *p[0], h, a), book("williamhill", "William Hill", *p[1], h, a),
            book("tipico_de", "Tipico (DE)", *p[2], h, a), book("winamax_de", "Winamax (DE)", *p[3], h, a),
            book("betfair_ex_eu", "Betfair", *p[4], h, a)]})
    return out


@pytest.fixture
def fake_api(monkeypatch):
    calls = {"odds": 0, "remaining": 480.0}

    def events(key, sport=odds_api.SPORT):
        return EVENTS, {"remaining": calls["remaining"], "used": 500 - calls["remaining"], "last": 0.0}

    def odds(key, sport=odds_api.SPORT, regions="eu", markets="h2h,totals"):
        calls["odds"] += 1
        calls["remaining"] -= 2
        return odds_payload(), {"remaining": calls["remaining"], "used": 500 - calls["remaining"], "last": 2.0}

    monkeypatch.setattr(odds_api, "events", events)
    monkeypatch.setattr(odds_api, "odds", odds)
    monkeypatch.setenv("ODDS_API_KEY", "test")
    return calls


# ------------------------------------------------------------------------------- clubs
@pytest.mark.parametrize("a,b", [("M'gladbach", "Borussia Mönchengladbach"), ("Bayern Munich", "FC Bayern München"),
                                 ("Hamburg", "Hamburger SV"), ("FC Koln", "1. FC Köln"), ("St Pauli", "FC St. Pauli"),
                                 ("Ein Frankfurt", "Eintracht Frankfurt"), ("Union Berlin", "1. FC Union Berlin"),
                                 ("Elversberg", "SV 07 Elversberg"), ("Mainz", "1. FSV Mainz 05")])
def test_club_key_links_spellings(a, b):
    assert club_key(a) == club_key(b) is not None


def test_club_key_keeps_rivals_apart():
    keys = [club_key(n) for n in ["Hamburger SV", "FC St. Pauli", "Eintracht Frankfurt", "FSV Frankfurt",
                                  "Borussia Dortmund", "Borussia Mönchengladbach", "Union Berlin", "Hertha BSC",
                                  "Bayern Munich", "TSV 1860 München"]]
    assert len(set(keys)) == len(keys)
    assert club_key("Some New FC") is None


# ------------------------------------------------------------------------------- scheduling
def at(s):
    return record_odds.parse_time(s)


def test_daily_snapshot_once_per_day():
    state = record_odds.load_state("/nonexistent")
    reasons, _ = record_odds.due(EVENTS, state, at("2026-10-15T06:40:00Z"))
    assert reasons == []                       # before 07:00 UTC
    reasons, _ = record_odds.due(EVENTS, state, at("2026-10-15T07:07:00Z"))
    assert reasons == ["daily"]
    state["daily"] = "2026-10-15"
    assert record_odds.due(EVENTS, state, at("2026-10-15T15:37:00Z"))[0] == []


def test_pre_and_close_windows():
    state = record_odds.load_state("/nonexistent")
    state["daily"] = "2026-10-17"
    r, covers = record_odds.due(EVENTS, state, at("2026-10-17T12:37:00Z"))   # 53 min before 13:30
    assert r == ["pre"] and covers["pre"] == [KICKOFF]
    state["done"][KICKOFF] = ["pre"]
    assert record_odds.due(EVENTS, state, at("2026-10-17T12:50:00Z"))[0] == []
    r, _ = record_odds.due(EVENTS, state, at("2026-10-17T13:07:00Z"))        # 23 min before
    assert r == ["close"]
    assert record_odds.due(EVENTS, state, at("2026-10-17T13:40:00Z"))[0] == []   # after kick-off


def test_budget_guard():
    assert record_odds.allowed(["daily", "pre"], {"remaining": 300}) == ["daily", "pre"]
    assert record_odds.allowed(["daily", "close"], {"remaining": 20}) == ["close"]
    assert record_odds.allowed(["manual"], {"remaining": 3}) == []
    assert record_odds.allowed(["daily"], {}) == ["daily"]


def test_recorder_writes_snapshot_and_state(tmp_path, fake_api):
    d = tmp_path / "odds"
    assert record_odds.main(["--data-dir", str(d), "--now", "2026-10-16T07:07:00Z"]) == 0
    files = list(d.glob("snapshots/2026/10/16/*.json.gz"))
    assert len(files) == 1 and fake_api["odds"] == 1
    snap = json.load(gzip.open(files[0], "rt"))
    assert snap["meta"]["reasons"] == ["daily"] and snap["meta"]["matches"] == 3
    state = json.load(open(d / "state.json"))
    assert state["daily"] == "2026-10-16" and state["snapshots"][-1]["remaining"] == 478
    # 30 minutes later nothing is due: no API call, no new file
    assert record_odds.main(["--data-dir", str(d), "--now", "2026-10-16T07:37:00Z"]) == 0
    assert fake_api["odds"] == 1 and len(list(d.glob("snapshots/**/*.json.gz"))) == 1
    # a manual snapshot is always taken
    assert record_odds.main(["--data-dir", str(d), "--now", "2026-10-16T09:00:00Z", "--label", "md6 post"]) == 0
    assert fake_api["odds"] == 2


def test_no_key_means_no_calls(tmp_path, monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    assert record_odds.main(["--data-dir", str(tmp_path)]) == 0
    assert not list(tmp_path.iterdir())


# ------------------------------------------------------------------------------- summaries
def snapshot(taken_at="2026-10-16T07:07:00Z"):
    return {"meta": {"taken_at": taken_at, "reasons": ["daily"], "label": ""}, "data": odds_payload()}


def test_consensus_leaves_out_exchanges_and_finds_reader_price():
    wide = match_odds(tidy(snapshot()))
    rows = wide[wide.event_id == "e1"]
    s = summarise(rows)
    books = rows[rows.bookmaker != "betfair_ex_eu"][["h", "d", "a"]].to_numpy()
    assert s["books"] == 4
    assert s["consensus"] == pytest.approx(fair(books).mean(0), abs=1e-4)
    assert sum(s["consensus"]) == pytest.approx(1, abs=1e-3)
    assert s["pinnacle"] == [3.7, 4.1, 1.85]
    assert [r["odds"] for r in s["reader_best"]] == [3.95, 4.3, 1.9]          # best of Tipico / Winamax
    assert [r["bookmaker"] for r in s["reader_best"]] == ["Winamax", "Winamax", "Tipico"]


def write_snapshot(d, snap):
    t = snap["meta"]["taken_at"].replace("-", "").replace(":", "")
    p = d / "snapshots" / "2026" / "10" / snap["meta"]["taken_at"][8:10] / f"{t}.json.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt") as f:
        json.dump(snap, f)


def test_odds_at_takes_latest_snapshot_before_the_time(tmp_path):
    import odds_at
    early = snapshot("2026-10-15T07:07:00Z")
    late = snapshot("2026-10-16T07:07:00Z")
    for e in late["data"]:
        if e["id"] == "e1":
            e["bookmakers"][2]["markets"][0]["outcomes"][0]["price"] = 4.5      # Tipico lengthens HSV
    write_snapshot(tmp_path, early)
    write_snapshot(tmp_path, late)
    s = odds_at.market_at(str(tmp_path), "Hamburg", "Stuttgart", "2026-10-15T12:00:00Z")
    assert s["taken_at"] == "2026-10-15T07:07:00Z" and s["reader_best"][0]["odds"] == 3.95
    s = odds_at.market_at(str(tmp_path), "Hamburger SV", "VfB Stuttgart")
    assert s["taken_at"] == "2026-10-16T07:07:00Z" and s["reader_best"][0] == {"odds": 4.5, "bookmaker": "Tipico"}
    block = odds_at.forecast_block(s)
    assert block["marketOdds"] == [4.5, 4.3, 1.9] and block["marketQuoted"] == "2026-10-16"


# ------------------------------------------------------------------------------- site export
OPENLIGADB = [
    {"matchID": 83206, "matchDateTimeUTC": "2026-10-17T13:30:00Z", "group": {"groupOrderID": 6},
     "team1": {"teamName": "Hamburger SV"}, "team2": {"teamName": "VfB Stuttgart"}, "matchIsFinished": False},
    {"matchID": 83204, "matchDateTimeUTC": "2026-10-17T13:30:00Z", "group": {"groupOrderID": 6},
     "team1": {"teamName": "Borussia Mönchengladbach"}, "team2": {"teamName": "FC Bayern München"}, "matchIsFinished": False},
    {"matchID": 83201, "matchDateTimeUTC": "2026-10-16T18:30:00Z", "group": {"groupOrderID": 6},
     "team1": {"teamName": "Werder Bremen"}, "team2": {"teamName": "SC Freiburg"}, "matchIsFinished": True},
]


def test_site_export_links_and_merges(tmp_path):
    import site_odds
    d = tmp_path / "odds"
    write_snapshot(d, snapshot())
    ol = tmp_path / "ol.json"
    ol.write_text(json.dumps(OPENLIGADB))
    out = tmp_path / "odds.json"
    out.write_text(json.dumps({"season": 2026, "matchdays": {"6": {"source": "1xBet", "quoted": "2026-10-13",
                                                                 "matches": {"83201": [2.0, 4.3, 3.52], "83206": [4.08, 4.08, 1.9]}}}}))
    assert site_odds.main(["--data-dir", str(d), "--season", "2026", "--out", str(out), "--openligadb", str(ol)]) == 0
    site = json.loads(out.read_text())
    md6 = site["matchdays"]["6"]
    assert md6["matches"]["83201"] == [2.0, 4.3, 3.52]                  # played: untouched
    assert md6["matches"]["83206"] == pytest.approx([3.79, 4.15, 1.845], abs=0.006)   # average of the 4 sportsbooks
    assert md6["matches"]["83204"] == pytest.approx([5.03, 4.65, 1.6], abs=0.01)
    assert md6["source"] == {"en": "average of 4 bookmakers", "de": "Schnitt von 4 Buchmachern"}
    assert md6["quoted"] == "2026-10-16"
    assert "\n        \"83206\": [3.79, 4.15, 1.84]" in out.read_text()     # lists stay on one line


# ------------------------------------------------------------------------------- CLV
def clv(odds, closing, i):
    p = fair(closing)
    return odds * p[i] - 1


def test_clv_definition():
    # HSV at 3.80 against a closing market of 4.20 / 4.10 / 1.80: the price was worse than the close
    assert clv(3.80, [4.20, 4.10, 1.80], 0) < 0
    # ...and better against a close of 3.30 / 3.90 / 2.15
    assert clv(3.80, [3.30, 3.90, 2.15], 0) > 0
