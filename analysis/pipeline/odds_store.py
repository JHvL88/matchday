"""Read recorded odds snapshots and summarise them.

Terms used:
  fair probabilities  a bookmaker's implied probabilities with its margin removed proportionally
  consensus           the average of the sportsbooks' fair probabilities (exchanges left out)
  reader price        the best price at a bookmaker German readers can use (Tipico, Winamax DE);
                      both pay the 5.3% German betting tax themselves
"""
import glob
import gzip
import json
import os

import numpy as np
import pandas as pd

from teams import club_key

EXCHANGES = {"betfair_ex_eu", "betfair_ex_uk", "matchbook", "smarkets"}
READER_BOOKS = {"tipico_de": "Tipico", "winamax_de": "Winamax"}
SHARP = "pinnacle"


def snapshot_files(data_dir):
    return sorted(glob.glob(os.path.join(data_dir, "snapshots", "*", "*", "*", "*.json.gz")))


def read_snapshot(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def tidy(snapshot):
    """One row per snapshot x match x bookmaker x market x outcome."""
    meta, rows = snapshot["meta"], []
    for e in snapshot["data"]:
        for b in e.get("bookmakers", []):
            for m in b.get("markets", []):
                for o in m.get("outcomes", []):
                    rows.append(dict(taken_at=meta["taken_at"], event_id=e["id"], commence_time=e["commence_time"],
                                     home=e["home_team"], away=e["away_team"], bookmaker=b["key"], title=b["title"],
                                     market=m["key"], outcome=o["name"], point=o.get("point"), price=o["price"],
                                     last_update=m.get("last_update") or b.get("last_update")))
    df = pd.DataFrame(rows)
    if len(df):
        for c in ("taken_at", "commence_time", "last_update"):
            df[c] = pd.to_datetime(df[c], utc=True)
        df["home_key"] = df.home.map(club_key)
        df["away_key"] = df.away.map(club_key)
    return df


def load(data_dir, since=None):
    files = snapshot_files(data_dir)
    frames = [tidy(read_snapshot(f)) for f in files]
    df = pd.concat([f for f in frames if len(f)], ignore_index=True) if frames else pd.DataFrame()
    if since is not None and len(df):
        df = df[df.taken_at >= pd.Timestamp(since)]
    return df


def match_odds(df):
    """Home/draw/away prices per snapshot, match and bookmaker (h2h market only), one row each."""
    h = df[df.market == "h2h"].copy()
    side = np.where(h.outcome == h.home, "h", np.where(h.outcome == h.away, "a", np.where(h.outcome == "Draw", "d", "?")))
    h["side"] = side
    wide = h.pivot_table(index=["taken_at", "event_id", "commence_time", "home", "away", "home_key", "away_key",
                                "bookmaker", "title"], columns="side", values="price", aggfunc="first").reset_index()
    wide = wide.dropna(subset=[c for c in ("h", "d", "a") if c in wide.columns])
    return wide


def fair(odds):
    inv = 1 / np.asarray(odds, float)
    return inv / inv.sum(-1, keepdims=True)


def summarise(rows):
    """Summary of one snapshot of one match: consensus, Pinnacle, best reader price."""
    books = rows[~rows.bookmaker.isin(EXCHANGES)]
    probs = fair(books[["h", "d", "a"]].to_numpy())
    consensus = probs.mean(0)
    margin = float((1 / books[["h", "d", "a"]].to_numpy()).sum(1).mean() - 1)
    out = dict(consensus=consensus.round(4).tolist(), books=int(len(books)), margin=round(margin, 4),
               average_odds=books[["h", "d", "a"]].mean().round(2).tolist())
    sharp = rows[rows.bookmaker == SHARP]
    if len(sharp):
        out["pinnacle"] = sharp[["h", "d", "a"]].iloc[0].round(2).tolist()
    readers = rows[rows.bookmaker.isin(READER_BOOKS)]
    if len(readers):
        best = []
        for side in ("h", "d", "a"):
            r = readers.loc[readers[side].idxmax()]
            best.append(dict(odds=round(float(r[side]), 2), bookmaker=READER_BOOKS[r.bookmaker]))
        out["reader_best"] = best
    return out
