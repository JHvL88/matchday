"""Understat match xG, joined onto the match table.

    from understat import load, add_xg
    m = add_xg(build(source_dir), "../matchday-data/understat")   # adds hxg, axg (NaN where unknown)

Joined on club (teams.club_key) and date (within a day, since Understat stores local kick-off time
and football-data the match date). Only 1. Bundesliga matches since 2014/15 get xG.

Understat is one small site and can be away for weeks (it was from 2 November 2026). So where it
has no xG for a played 1. Bundesliga match, `add_xg` takes football-data.co.uk's own xG columns
(HxG/AxG, in its files from 2026/27) and puts them on Understat's scale; `xg_src` says which
source each match used. See `fill_from_football_data`.
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


def fill_from_football_data(m, report=True, min_overlap=30):
    """Fill 1. Bundesliga matches Understat has no xG for with football-data.co.uk's xG, in place.

    The two providers don't use the same xG model, so football-data's numbers are first put on
    Understat's scale: a straight line fitted to every match that has both (home and away sides
    pooled). With fewer than `min_overlap` such matches the numbers are used as they are.
    The line is fitted on all such matches at once, so it isn't strictly walk-forward; it is two
    numbers for the whole league, and in the November 2026 gap every filled match is newer than the
    matches it was fitted on.
    """
    m["xg_src"] = np.where(m.hxg.notna(), "understat", "")
    if "fd_hxg" not in m:
        return None
    d1, fd = m["div"] == "D1", m.fd_hxg.notna() & m.fd_axg.notna()
    both, gap = d1 & fd & m.hxg.notna(), d1 & fd & m.hxg.isna()
    if not gap.any():
        return None
    x = np.r_[m.fd_hxg[both].values, m.fd_axg[both].values]
    y = np.r_[m.hxg[both].values, m.axg[both].values]
    slope, intercept, r = 1.0, 0.0, np.nan
    if both.sum() >= min_overlap:
        slope, intercept = (float(v) for v in np.polyfit(x, y, 1))
        r = float(np.corrcoef(x, y)[0, 1])
    m.loc[gap, "hxg"] = np.maximum(intercept + slope * m.fd_hxg[gap], 0.0)
    m.loc[gap, "axg"] = np.maximum(intercept + slope * m.fd_axg[gap], 0.0)
    m.loc[gap, "xg_src"] = "football-data"
    info = dict(filled=int(gap.sum()), first=m.date[gap].min(), last=m.date[gap].max(), overlap=int(both.sum()),
                slope=slope, intercept=intercept, r=r)
    if report:
        scale = (f"put on Understat's scale as {intercept:.3f} + {slope:.3f} x, fitted on {info['overlap']} matches "
                 f"with both (correlation {r:.2f})") if both.sum() >= min_overlap else \
                f"used as they are (only {info['overlap']} matches have both sources)"
        print(f"football-data.co.uk xG fills {info['filled']} matches Understat lacks "
              f"({info['first']:%Y-%m-%d} to {info['last']:%Y-%m-%d}), {scale}")
    return info


def add_xg(matches, understat_dir, report=True, fallback=True):
    """Return matches with hxg / axg / xg_src columns and a join report.

    fallback: fill matches Understat lacks from football-data.co.uk's xG (see fill_from_football_data).
    """
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
    if fallback:
        fill_from_football_data(m, report)
    else:
        m["xg_src"] = np.where(m.hxg.notna(), "understat", "")
    return m.drop(columns=["home_key", "away_key"])
