"""Understat match xG, joined onto the match table.

    from understat import load, add_xg
    m = add_xg(build(source_dir), "../matchday-data/understat")   # adds hxg, axg (NaN where unknown)

Joined on club (teams.club_key) and date (within a day, since Understat stores local kick-off time
and football-data the match date). Only 1. Bundesliga matches since 2014/15 get xG.
"""
import glob
import json
import os

import numpy as np
import pandas as pd

from teams import club_key


def load(understat_dir, league="Bundesliga"):
    rows = []
    for path in sorted(glob.glob(os.path.join(understat_dir, league, "*.json"))):
        for e in json.load(open(path, encoding="utf-8")).get("dates", []):
            if not e.get("isResult"):
                continue
            rows.append(dict(understat_id=str(e["id"]), datetime=pd.Timestamp(e["datetime"]),
                             home_u=e["h"]["title"], away_u=e["a"]["title"],
                             hg_u=int(e["goals"]["h"]), ag_u=int(e["goals"]["a"]),
                             hxg=float(e["xG"]["h"]), axg=float(e["xG"]["a"])))
    u = pd.DataFrame(rows)
    u["home_key"], u["away_key"] = u.home_u.map(club_key), u.away_u.map(club_key)
    u["day"] = u.datetime.dt.normalize()
    return u


def add_xg(matches, understat_dir, report=True):
    """Return matches with hxg / axg columns and a join report."""
    m = matches.copy()
    u = load(understat_dir)
    unknown = sorted(set(u.home_u[u.home_key.isna()]) | set(u.away_u[u.away_key.isna()]))
    if unknown:
        raise ValueError(f"Understat club names without a key: {unknown}")
    m["home_key"], m["away_key"] = m.home.map(club_key), m.away.map(club_key)
    d1 = m[m["div"] == "D1"].reset_index()
    cand = d1.merge(u, on=["home_key", "away_key"], how="inner")
    cand = cand[(cand.date - cand.day).abs() <= pd.Timedelta(days=1)]
    if cand["index"].duplicated().any() or cand.understat_id.duplicated().any():
        raise ValueError("ambiguous Understat join")
    m["hxg"], m["axg"] = np.nan, np.nan
    m.loc[cand["index"], "hxg"] = cand.hxg.values
    m.loc[cand["index"], "axg"] = cand.axg.values
    m.loc[cand["index"], "understat_id"] = cand.understat_id.values
    goals_differ = cand[(cand.hg != cand.hg_u) | (cand.ag != cand.ag_u)]
    if report:
        cov = m[(m["div"] == "D1") & (m.season >= 2014)].groupby("season").hxg.apply(lambda x: x.notna().mean())
        print("Understat xG coverage of 1. Bundesliga matches:", cov.round(3).to_dict())
        print(f"joined {len(cand)} of {len(u)} Understat matches; score disagreements: {len(goals_differ)}")
        for r in goals_differ.itertuples():
            print(f"  {r.date:%Y-%m-%d} {r.home} v {r.away}: football-data {r.hg}-{r.ag}, Understat {r.hg_u}-{r.ag_u}")
    return m.drop(columns=["home_key", "away_key"])
