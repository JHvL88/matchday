"""Refresh data/odds.json (the home page's home/draw/away bars) from the latest odds snapshot.

Each upcoming match gets the average price across the sportsbooks in the snapshot, keyed by its
OpenLigaDB match id. Matches the snapshot doesn't cover (already played, or not listed yet) keep the
odds they had, so finished matches still show what the market expected.

    python analysis/pipeline/site_odds.py --data-dir ../matchday-data/odds --season 2026 --out data/odds.json
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd

from odds_store import match_odds, read_snapshot, snapshot_files, summarise, tidy
from jsonfmt import dumps
from teams import club_key

OPENLIGADB = "https://api.openligadb.de/getmatchdata/bl1/{season}"
ABOUT = ("Bookmaker 1X2 odds (home win, draw, away win) per OpenLigaDB matchId, one block per matchday. "
         "Written by analysis/pipeline/site_odds.py from the odds recorder: the average price across the "
         "sportsbooks in The Odds API's EU feed. The site turns them into probabilities by removing the margin "
         "proportionally. Matches without odds simply show no bar.")


def openligadb_season(season, path=None):
    if path:
        return json.load(open(path))
    req = urllib.request.Request(OPENLIGADB.format(season=season), headers={"User-Agent": "jans-matchday/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def fixtures(season_json):
    rows = []
    for m in season_json:
        t = pd.Timestamp(m["matchDateTimeUTC"])
        rows.append(dict(match_id=str(m["matchID"]), matchday=int(m["group"]["groupOrderID"]),
                         kickoff=t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC"),
                         home=m["team1"]["teamName"], away=m["team2"]["teamName"],
                         finished=bool(m.get("matchIsFinished"))))
    f = pd.DataFrame(rows)
    f["home_key"] = f.home.map(club_key)
    f["away_key"] = f.away.map(club_key)
    return f


def link(events, fx, tolerance_hours=36):
    """Pair each odds event with its OpenLigaDB fixture: same clubs, kick-off within the tolerance."""
    out, missing = {}, []
    for e in events.itertuples():
        cand = fx[(fx.home_key == e.home_key) & (fx.away_key == e.away_key)
                  & ((fx.kickoff - e.commence_time).abs() <= pd.Timedelta(hours=tolerance_hours))]
        if len(cand) == 1:
            out[e.event_id] = cand.iloc[0]
        else:
            missing.append(f"{e.home} v {e.away} ({e.commence_time:%Y-%m-%d %H:%M})")
    return out, missing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--out", default="data/odds.json")
    ap.add_argument("--openligadb", help="saved getmatchdata JSON instead of downloading (tests)")
    a = ap.parse_args(argv)

    files = snapshot_files(a.data_dir)
    if not files:
        print("no snapshots yet")
        return 0
    snap = read_snapshot(files[-1])
    wide = match_odds(tidy(snap))
    if wide.empty:
        print("latest snapshot has no match odds")
        return 0
    events = wide.drop_duplicates("event_id")[["event_id", "commence_time", "home", "away", "home_key", "away_key"]]
    fx = fixtures(openligadb_season(a.season, a.openligadb))
    linked, missing = link(events, fx)
    for m in missing:
        print("WARNING: no OpenLigaDB fixture for", m)

    site = json.load(open(a.out)) if os.path.exists(a.out) else {"season": a.season, "matchdays": {}}
    if site.get("season") != a.season:
        site = {"season": a.season, "matchdays": {}}
    quoted = snap["meta"]["taken_at"][:10]
    changed = 0
    for event_id, f in linked.items():
        if f.finished:
            continue
        s = summarise(wide[wide.event_id == event_id])
        block = site["matchdays"].setdefault(str(f.matchday), {"matches": {}})
        if block["matches"].get(f.match_id) != s["average_odds"]:
            changed += 1
        block["matches"][f.match_id] = s["average_odds"]
        block["books"] = max(block.get("books", 0) if block.get("quoted") == quoted else 0, s["books"])
        block["quoted"] = quoted
        block["url"] = "https://the-odds-api.com/"
        block["source"] = {"en": f"average of {block['books']} bookmakers", "de": f"Schnitt von {block['books']} Buchmachern"}
    site["about"] = ABOUT
    site["matchdays"] = dict(sorted(site["matchdays"].items(), key=lambda kv: int(kv[0])))
    ordered = {"about": site["about"], "season": site["season"], "matchdays": site["matchdays"]}
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(dumps(ordered) + "\n")
    print(f"{a.out}: {len(linked)} matches linked, {changed} prices changed, snapshot {snap['meta']['taken_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
