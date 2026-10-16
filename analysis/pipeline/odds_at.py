"""The market for one match as recorded at (or just before) a given time, for a post.

    python analysis/pipeline/odds_at.py --data-dir ../matchday-data/odds --home Hamburg --away Stuttgart
    python analysis/pipeline/odds_at.py ... --at 2026-10-23T09:00:00Z

Prints the snapshot summary and a ready-made `forecast` block for analysis/posts.json:
  market        consensus fair probabilities (average of the sportsbooks, margins removed)
  marketOdds    the best price at Tipico or Winamax, the two German-licensed books in the feed,
                i.e. a price a reader could actually have taken; paper bets are settled at these
Take a manual snapshot first (Actions > Record odds > Run workflow) so the price is fresh.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd

from odds_store import match_odds, read_snapshot, snapshot_files, summarise, tidy
from teams import club_key


def market_at(data_dir, home, away, at=None):
    hk, ak = club_key(home), club_key(away)
    if not hk or not ak:
        raise SystemExit(f"unknown club: {home if not hk else away}")
    at = pd.Timestamp(at or pd.Timestamp.now(tz="UTC"))
    at = at.tz_localize("UTC") if at.tzinfo is None else at
    for path in reversed(snapshot_files(data_dir)):
        snap = read_snapshot(path)
        if pd.Timestamp(snap["meta"]["taken_at"]) > at:
            continue
        wide = match_odds(tidy(snap))
        rows = wide[(wide.home_key == hk) & (wide.away_key == ak)] if len(wide) else wide
        if len(rows):
            s = summarise(rows)
            s.update(taken_at=snap["meta"]["taken_at"], label=snap["meta"].get("label", ""),
                     match=f"{rows.home.iloc[0]} v {rows.away.iloc[0]}", kickoff=str(rows.commence_time.iloc[0]))
            return s
    raise SystemExit(f"no snapshot before {at} lists {home} v {away}")


def forecast_block(s):
    block = dict(market=s["consensus"], marketQuoted=s["taken_at"][:10], marketSnapshot=s["taken_at"])
    if "reader_best" in s:
        block["marketOdds"] = [r["odds"] for r in s["reader_best"]]
        books = sorted({r["bookmaker"] for r in s["reader_best"]})
        block["marketBookmaker"] = " / ".join(books)
    return block


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--home", required=True)
    ap.add_argument("--away", required=True)
    ap.add_argument("--at", help="UTC time, default now")
    a = ap.parse_args()
    s = market_at(a.data_dir, a.home, a.away, a.at)
    print(json.dumps(s, indent=1))
    print("\nFor analysis/posts.json (forecast):")
    print(json.dumps(forecast_block(s), indent=1))
