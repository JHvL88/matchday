"""Forecast every match of the coming matchday and publish it in data/forecasts.json.

The home page shows these next to the bookmakers' odds, one bar per match. The models, their
settings and the data are exactly those of the backtest and the deep dives (forecast.py with --xg
and --pool), so a forecast here is made the way the Track record grades them.

    python analysis/pipeline/site_forecasts.py data/matches.csv --pool tables --season 2026

Rules, fixed in advance:
  * One forecast per match, published once. A matchday already in the file is never refitted
    (unless --force, which is for repairs before kick-off and is recorded in the file).
  * A matchday is due from 72 hours before its first kick-off. The run waits while the source
    files still miss a played match, unless kick-off is less than 30 hours away; then it goes
    ahead and says so in the file.
  * The freeze date is the day of the run: only matches played before it are used.

Tests run without the models or the network: --openligadb takes a saved season file, and
forecast_json= lets a test hand in forecast.py's output.
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd

from jsonfmt import dumps
from site_odds import fixtures as openligadb_fixtures, openligadb_season
from teams import club_key

ABOUT = ("The models' forecast for every match of a matchday, per OpenLigaDB matchId. Written by "
         "analysis/pipeline/site_forecasts.py (never by hand) and never changed after it is published. "
         "model = the ensemble's home win, draw, away win; models = the three models it averages; "
         "grid[i][j] = chance that the home side scores i and the away side j (0 to 5 goals each); "
         "market = the bookmakers' average odds on the day of publication, for the record.")
MODEL_KEYS = {"dc": "dixonColes", "bay": "bayesian", "xgb": "xgboost"}
DUE_HOURS = 72
LAST_CHANCE_HOURS = 30
GRID_GOALS = 6


def utc(value):
    t = pd.Timestamp(value)
    return t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")


def due_matchday(fx, now, published, due_hours=DUE_HOURS):
    """The next matchday that has not started, if its first kick-off is within the window and it
    has no forecast yet. Returns (matchday or None, reason)."""
    first = fx.groupby("matchday").kickoff.min().sort_index()
    upcoming = first[first > now]
    if upcoming.empty:
        return None, "the season has no matchday left"
    matchday, kickoff = int(upcoming.index[0]), upcoming.iloc[0]
    if str(matchday) in published:
        return None, f"matchday {matchday} is already published"
    hours = (kickoff - now).total_seconds() / 3600
    if hours > due_hours:
        return None, f"matchday {matchday} starts in {hours:.0f} hours; forecasts go out {due_hours} hours before"
    return matchday, f"matchday {matchday} starts in {hours:.0f} hours"


def table_names(matches, season):
    """club key -> the club's name in the match table (football-data.co.uk spelling), this season's
    top flight only."""
    cur = matches[(matches.season == season) & (matches["div"] == "D1")]
    names = {}
    for name in sorted(set(cur.home) | set(cur.away)):
        key = club_key(name)
        if key is None or key in names:
            raise SystemExit(f"cannot tell clubs apart in the match table: {name!r}")
        names[key] = name
    return names


def missing_results(fx, matches, season, freeze):
    """Matches OpenLigaDB has as finished before the freeze date that the match table lacks."""
    cur = matches[(matches.season == season) & (matches["div"] == "D1") & matches.hg.notna()]
    have = {(club_key(h), club_key(a)) for h, a in zip(cur.home, cur.away)}
    played = fx[fx.finished & (fx.kickoff < utc(freeze))]
    return [f"{r.home} v {r.away}" for r in played.itertuples() if (r.home_key, r.away_key) not in have]


def fixture_rows(fx, matchday, names):
    rows = []
    for r in fx[fx.matchday == matchday].sort_values(["kickoff", "match_id"]).itertuples():
        unknown = [n for n, k in ((r.home, r.home_key), (r.away, r.away_key)) if k not in names]
        if unknown:
            raise SystemExit(f"no club in the match table for {unknown} (teams.py or a promoted side without a match yet)")
        rows.append(dict(match_id=r.match_id, kickoff=r.kickoff, home=r.home, away=r.away,
                         date=r.kickoff.tz_convert("Europe/Berlin").strftime("%Y-%m-%d"),
                         table_home=names[r.home_key], table_away=names[r.away_key]))
    return rows


def forecast_args(matches_path, out_path, freeze, rows, pool, warmup=None, samples=None):
    args = [matches_path, out_path, "--freeze", freeze, "--xg"]
    for r in rows:
        args += ["--fixture", r["date"], r["table_home"], r["table_away"]]
    if pool:
        args += ["--pool", pool]
    if warmup:
        args += ["--warmup", str(warmup)]
    if samples:
        args += ["--samples", str(samples)]
    return args


def three(m):
    """Home, draw, away as four-decimal numbers that add up to exactly 1."""
    total = m["H"] + m["D"] + m["A"]
    h, d = round(m["H"] / total, 4), round(m["D"] / total, 4)
    return [h, d, round(1 - h - d, 4)]


def site_block(forecast, rows, now, odds_block=None, note=None):
    """One matchday of data/forecasts.json from forecast.py's output."""
    by_fixture = {(f["date"], f["home"], f["away"]): f for f in forecast["fixtures"]}
    matches = {}
    for r in rows:
        f = by_fixture[(r["date"], r["table_home"], r["table_away"])]
        ens = f["models"]["ens"]
        entry = dict(home=r["home"], away=r["away"], kickoff=r["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                     model=three(ens),
                     models={MODEL_KEYS[k]: three(f["models"][k]) for k in MODEL_KEYS},
                     expectedGoals=[round(ens["lh"], 2), round(ens["la"], 2)],
                     mostLikely=dict(score=ens["mostLikely"]["score"], p=round(ens["mostLikely"]["p"], 3)),
                     over25=round(ens["over25"], 3), btts=round(ens["btts"], 3),
                     grid=[[round(p, 3) for p in line[:GRID_GOALS]] for line in f["grid"][:GRID_GOALS]])
        odds = (odds_block or {}).get("matches", {}).get(r["match_id"])
        if odds:
            entry["market"] = dict(odds=odds, quoted=odds_block.get("quoted"), books=odds_block.get("books"))
        matches[r["match_id"]] = entry
    block = dict(published=now.strftime("%Y-%m-%dT%H:%M:%SZ"), freeze=forecast["freeze"],
                 lastMatch=forecast["inputs"]["last_match"], models=forecast["models"],
                 codeCommit=forecast["inputs"].get("code_commit"),
                 matchesSha256=forecast["inputs"].get("matches_sha256"))
    if note:
        block["note"] = note
    block["matches"] = matches
    return block


def write_site(path, season, site):
    site["matchdays"] = dict(sorted(site["matchdays"].items(), key=lambda kv: int(kv[0])))
    ordered = {"about": ABOUT, "season": season, "matchdays": site["matchdays"]}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(ordered) + "\n")


def github_output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")


def main(argv=None, forecast_json=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("matches", nargs="?", help="match table with xG (build_matches.py --understat); not needed with --check")
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--out", default="data/forecasts.json")
    ap.add_argument("--pool", help="folder with ENG.csv, ESP.csv, ITA.csv, FRA.csv for the five-league XGBoost")
    ap.add_argument("--odds", default="data/odds.json", help="the site's odds file; today's prices go into the record")
    ap.add_argument("--matchday", type=int, help="forecast this matchday instead of the next one due")
    ap.add_argument("--force", action="store_true", help="replace a matchday that is already published (before kick-off only)")
    ap.add_argument("--check", action="store_true", help="only say whether a matchday is due (sets the workflow output 'due')")
    ap.add_argument("--openligadb", help="saved getmatchdata JSON instead of downloading (tests)")
    ap.add_argument("--now", help="pretend it is this UTC time (tests)")
    ap.add_argument("--work", default=None, help="where forecast.py's full output goes (default: the temp folder)")
    ap.add_argument("--warmup", type=int)
    ap.add_argument("--samples", type=int)
    a = ap.parse_args(argv)

    now = utc(a.now) if a.now else pd.Timestamp.now(tz="UTC")
    site = json.load(open(a.out, encoding="utf-8")) if os.path.exists(a.out) else {"season": a.season, "matchdays": {}}
    if site.get("season") != a.season:
        site = {"season": a.season, "matchdays": {}}
    fx = openligadb_fixtures(openligadb_season(a.season, a.openligadb))

    if a.matchday:
        day = fx[fx.matchday == a.matchday]
        if day.empty:
            raise SystemExit(f"OpenLigaDB has no matchday {a.matchday}")
        if day.kickoff.min() <= now:
            raise SystemExit(f"matchday {a.matchday} has started: a forecast after kick-off is not a forecast")
        if str(a.matchday) in site["matchdays"] and not a.force:
            print(f"matchday {a.matchday} is already published (use --force to replace it before kick-off)")
            github_output(due="false")
            return 0
        matchday, reason = a.matchday, f"matchday {a.matchday} on request"
    else:
        matchday, reason = due_matchday(fx, now, {} if a.force else site["matchdays"])
    print(reason)
    if matchday is None:
        github_output(due="false")
        return 0
    if a.check:
        github_output(due="true", matchday=matchday)
        return 0
    if not a.matches:
        raise SystemExit("the match table is needed to forecast")

    matches = pd.read_csv(a.matches, parse_dates=["date"])
    freeze = now.strftime("%Y-%m-%d")
    hours = (fx[fx.matchday == matchday].kickoff.min() - now).total_seconds() / 3600
    note = None
    missing = missing_results(fx, matches, a.season, freeze)
    if missing:
        if hours > LAST_CHANCE_HOURS:
            print(f"waiting: the source files do not have {len(missing)} played match(es) yet: {'; '.join(missing)}")
            github_output(due="false")
            return 0
        note = f"published without {len(missing)} played match(es) the source files did not have yet: {'; '.join(missing)}"
        print("WARNING:", note)
    if a.force and str(matchday) in site["matchdays"]:
        note = "; ".join(filter(None, [note, f"replaces the forecast published {site['matchdays'][str(matchday)].get('published')}"]))

    rows = fixture_rows(fx, matchday, table_names(matches, a.season))
    if forecast_json is None:
        work = a.work or os.path.join(tempfile.gettempdir(), f"forecast-md{matchday}.json")
        import forecast          # the models (numpyro, jax, xgboost): only loaded when a forecast is made
        forecast.main(forecast_args(a.matches, work, freeze, rows, a.pool, a.warmup, a.samples))
        forecast_json = json.load(open(work))
    odds_block = None
    if a.odds and os.path.exists(a.odds):
        odds_block = json.load(open(a.odds, encoding="utf-8")).get("matchdays", {}).get(str(matchday))
    site["matchdays"][str(matchday)] = site_block(forecast_json, rows, now, odds_block, note)
    write_site(a.out, a.season, site)
    print(f"{a.out}: matchday {matchday}, {len(rows)} matches, data to {forecast_json['inputs']['last_match']}")
    github_output(due="true", matchday=matchday, published="true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
