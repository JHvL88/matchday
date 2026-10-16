"""Take a snapshot of Bundesliga odds when one is due, and keep a log of it.

A snapshot is one call to The Odds API: every upcoming Bundesliga match, every bookmaker in the EU
feed (Pinnacle, Betfair Exchange, Tipico, Winamax and about 20 more), match odds and total goals.

When is one due?
  daily     once a day from 07:00 UTC while any match is less than 8 days away
  pre       75 to 30 minutes before a kick-off time (the price after team news is out)
  close     the last 30 minutes before a kick-off time (our own closing line)
  manual    on request, e.g. when a post is published (--label "md7 post")

The workflow runs this every 30 minutes; most runs find nothing due and cost nothing, because
checking the fixture list is free. Snapshots go to <data-dir>/snapshots/YYYY/MM/DD/<time>.json.gz,
the log to <data-dir>/state.json.

Budget: the free plan has 500 credits a month and a snapshot costs 2 (match odds + totals).
Below RESERVE credits only closing and manual snapshots are taken; below 4 nothing is.

    ODDS_API_KEY=... python analysis/pipeline/record_odds.py --data-dir ../matchday-data/odds
"""
import argparse
import datetime as dt
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odds_api

RESERVE = 40
DAILY_FROM_HOUR = 7
PRE_WINDOW = (30, 75)      # minutes before kick-off
CLOSE_WINDOW = (0, 30)


def parse_time(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {"daily": None, "done": {}, "quota": {}, "snapshots": []}


def due(events, state, now, force=False):
    """Reasons a snapshot is due now, and which kick-off times it covers."""
    reasons, covers = [], {}
    kickoffs = sorted({e["commence_time"] for e in events if parse_time(e["commence_time"]) > now})
    soon = [k for k in kickoffs if parse_time(k) - now <= dt.timedelta(days=8)]
    if force:
        reasons.append("manual")
    if soon and now.hour >= DAILY_FROM_HOUR and state.get("daily") != now.date().isoformat():
        reasons.append("daily")
    for k in kickoffs:
        minutes = (parse_time(k) - now).total_seconds() / 60
        done = state["done"].get(k, [])
        for name, (lo, hi) in (("pre", PRE_WINDOW), ("close", CLOSE_WINDOW)):
            if lo < minutes <= hi:
                covers.setdefault(name, []).append(k)
                if name not in done and name not in reasons:
                    reasons.append(name)
    return reasons, covers


def allowed(reasons, quota):
    """Drop what the budget can't afford."""
    left = quota.get("remaining")
    if left is None:
        return reasons
    if left < 4:
        return []
    if left < RESERVE:
        return [r for r in reasons if r in ("close", "manual")]
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description="Take a Bundesliga odds snapshot if one is due.")
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--label", default="", help="take a snapshot now and tag it, e.g. 'md7 post'")
    ap.add_argument("--markets", default="h2h,totals")
    ap.add_argument("--regions", default="eu")
    ap.add_argument("--now", help="pretend it is this UTC time (tests)")
    a = ap.parse_args(argv)
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("ODDS_API_KEY is not set: nothing to do.")
        return 0

    now = parse_time(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    state_path = os.path.join(a.data_dir, "state.json")
    state = load_state(state_path)
    evs, quota_now = odds_api.events(key)
    if quota_now.get("remaining") is not None:     # the free call reports the budget too
        state["quota"] = quota_now
    reasons, covers = due(evs, state, now, force=bool(a.label))
    affordable = allowed(reasons, state.get("quota", {}))
    if not affordable:
        print(f"{now:%Y-%m-%d %H:%M} UTC: no snapshot due ({len(evs)} matches listed)"
              + (f"; skipped for budget: {reasons}" if reasons else ""))
        write_output(snapshot="false")       # nothing written, so nothing to commit
        return 0

    data, quota = odds_api.odds(key, regions=a.regions, markets=a.markets)
    books = sorted({b["key"] for e in data for b in e.get("bookmakers", [])})
    meta = dict(taken_at=iso(now), reasons=affordable, label=a.label, sport=odds_api.SPORT,
                regions=a.regions, markets=a.markets, quota=quota, matches=len(data), bookmakers=books)
    rel = os.path.join("snapshots", f"{now:%Y/%m/%d}", f"{now:%Y%m%dT%H%M%SZ}.json.gz")
    path = os.path.join(a.data_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump({"meta": meta, "data": data}, f, separators=(",", ":"))

    if "daily" in affordable:
        state["daily"] = now.date().isoformat()
    for name, ks in covers.items():
        for k in ks:
            if name not in state["done"].setdefault(k, []):
                state["done"][k].append(name)
    cutoff = now - dt.timedelta(days=14)
    state["done"] = {k: v for k, v in state["done"].items() if parse_time(k) > cutoff}
    state["quota"] = quota
    state["snapshots"].append(dict(file=rel, taken_at=meta["taken_at"], reasons=affordable, label=a.label,
                                   matches=len(data), bookmakers=len(books), credits=quota.get("last"),
                                   remaining=quota.get("remaining")))
    os.makedirs(a.data_dir, exist_ok=True)
    json.dump(state, open(state_path, "w"), indent=1)
    print(f"{now:%Y-%m-%d %H:%M} UTC: snapshot ({', '.join(affordable)}) -> {rel}: {len(data)} matches, "
          f"{len(books)} bookmakers, {quota.get('last')} credits, {quota.get('remaining')} left")
    write_output(snapshot="true", reasons=",".join(affordable), file=rel)
    return 0


def write_output(**kv):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


if __name__ == "__main__":
    sys.exit(main())
