"""The bookmakers' view of Bayern v Leipzig from the recorded odds, for the post.

    python analysis/2026-27-md6-bayern-leipzig/post_market.py <matchday-data>/odds analysis/2026-27-md6-bayern-leipzig/market.json [--at UTC]

Reads the latest snapshot taken before --at (default: now) from the private odds store and writes the
derived numbers only (The Odds API's terms allow displaying their data, not republishing raw files):
  1x2       consensus fair probabilities (sportsbooks' average, margins removed), average odds, margin,
            Pinnacle, and the best price at Tipico/Winamax (what a German reader could take)
  totals    for each goal line: consensus fair probability of over, number of books, best over/under
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import numpy as np
import pandas as pd

from odds_at import market_at
from odds_store import EXCHANGES, READER_BOOKS, read_snapshot, snapshot_files, tidy
from teams import club_key

HOME, AWAY = "Bayern Munich", "RB Leipzig"


def totals_at(data_dir, taken_at):
    hk, ak = club_key(HOME), club_key(AWAY)
    for path in reversed(snapshot_files(data_dir)):
        snap = read_snapshot(path)
        if snap["meta"]["taken_at"] != taken_at:
            continue
        t = tidy(snap)
        t = t[(t.home_key == hk) & (t.away_key == ak) & (t.market == "totals") & ~t.bookmaker.isin(EXCHANGES)]
        out = []
        for point, g in t.groupby("point"):
            w = g.pivot_table(index="bookmaker", columns="outcome", values="price", aggfunc="first").dropna()
            if not len(w):
                continue
            inv = 1 / w[["Over", "Under"]].to_numpy(float)
            fair_over = (inv[:, 0] / inv.sum(1))
            readers = w[w.index.isin(READER_BOOKS)]
            out.append(dict(point=float(point), books=int(len(w)), over=round(float(fair_over.mean()), 4),
                            best_over=round(float(w.Over.max()), 2), best_under=round(float(w.Under.max()), 2),
                            reader_over=round(float(readers.Over.max()), 2) if len(readers) else None,
                            reader_under=round(float(readers.Under.max()), 2) if len(readers) else None))
        return out
    return []


if __name__ == "__main__":
    data_dir, out = sys.argv[1], sys.argv[2]
    at = sys.argv[sys.argv.index("--at") + 1] if "--at" in sys.argv else None
    s = market_at(data_dir, HOME, AWAY, at)
    res = dict(match=s["match"], kickoff=s["kickoff"], taken_at=s["taken_at"], label=s["label"],
               x12=dict(consensus=s["consensus"], average_odds=s["average_odds"], margin=s["margin"],
                        books=s["books"], pinnacle=s.get("pinnacle"), reader_best=s.get("reader_best")),
               totals=totals_at(data_dir, s["taken_at"]),
               source="The Odds API (EU feed), recorded by the Record odds workflow; derived figures only")
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
