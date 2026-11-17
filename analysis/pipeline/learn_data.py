"""Write data/learn.json: the real numbers behind part two of the Learn page.

Everything comes from the files the rest of the pipeline uses, through the same functions, so the
Learn page can never disagree with the Track record:

  table      How far apart the clubs are in the real table, matchday by matchday, averaged over every
             complete 1. Bundesliga season in the source files; plus the home/draw/away shares the
             "league of clones" plays with.
  elo        The current Elo rating of every club in this season's 1. Bundesliga, from
             features.elo_ratings (the rating XGBoost uses), with the rating a year earlier.
  matches    Every graded backtest match (2019/20 on): date, clubs, score, the published ensemble's
             forecast and the market's (closing average, margin removed), exactly as evaluate.py
             grades them. Probabilities are stored in tenths of a percent (0-1000): home, draw; away is
             the rest. The calibration drill and the penalty shoot-out read from here.

    python analysis/pipeline/build_matches.py /tmp/source /tmp/matches.csv
    python analysis/pipeline/learn_data.py /tmp/matches.csv /tmp/results/xg data/learn.json --as-of 2026-11-16

The match table does not need --understat: nothing here is refitted.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from evaluate import cols, load
from features import elo_ratings
from teams import club_key

# Short club names for the page (same in English and German, apart from the umlaut).
NAMES = {
    "bayern": "Bayern", "dortmund": "Dortmund", "gladbach": "Gladbach", "leverkusen": "Leverkusen",
    "leipzig": "Leipzig", "frankfurt": "Frankfurt", "stuttgart": "Stuttgart", "stpauli": "St. Pauli",
    "hamburg": "Hamburg", "koln": "Köln", "bremen": "Bremen", "wolfsburg": "Wolfsburg",
    "freiburg": "Freiburg", "mainz": "Mainz", "augsburg": "Augsburg", "hoffenheim": "Hoffenheim",
    "union": "Union Berlin", "hertha": "Hertha", "heidenheim": "Heidenheim", "bochum": "Bochum",
    "kiel": "Kiel", "elversberg": "Elversberg", "paderborn": "Paderborn", "darmstadt": "Darmstadt",
    "schalke": "Schalke", "hannover": "Hannover", "dusseldorf": "Düsseldorf", "nurnberg": "Nürnberg",
    "bielefeld": "Bielefeld", "furth": "Fürth", "braunschweig": "Braunschweig",
}


def name(fd_name):
    return NAMES.get(club_key(fd_name), fd_name)


def table_spread(m):
    """Standard deviation of points across the 18 clubs after each matchday, real seasons only."""
    rows = []
    for season, s in m[(m["div"] == "D1") & m.hg.notna()].groupby("season"):
        if len(s) != 306:          # complete seasons only
            continue
        s = s.sort_values(["date", "home"])
        points = {}
        for r in s.itertuples(index=False):
            ph, pa = (3, 0) if r.hg > r.ag else (1, 1) if r.hg == r.ag else (0, 3)
            for club, p in ((r.home, ph), (r.away, pa)):
                points.setdefault(club, []).append(p)
        cum = np.array([np.cumsum(v) for v in points.values()])   # 18 clubs x 34 matchdays
        sd = cum.std(0)
        rows.append(dict(season=int(season), sd=sd, top=cum[:, -1].max(), bottom=cum[:, -1].min()))
    d1 = m[(m["div"] == "D1") & m.hg.notna()]
    shares = [float((d1.hg > d1.ag).mean()), float((d1.hg == d1.ag).mean()), float((d1.hg < d1.ag).mean())]
    return dict(
        seasons=len(rows), first=min(r["season"] for r in rows), last=max(r["season"] for r in rows),
        sd=[round(float(v), 2) for v in np.mean([r["sd"] for r in rows], 0)],
        champion=round(float(np.mean([r["top"] for r in rows])), 1),
        bottom=round(float(np.mean([r["bottom"] for r in rows])), 1),
        homeDrawAway=[round(v, 4) for v in shares], matches=int(len(d1)),
    )


def current_elo(m, season):
    """Ratings after the last played match, from the pipeline's own function."""
    df = m.sort_values(["date", "div", "home"]).reset_index(drop=True)
    played = df[df.hg.notna()].reset_index(drop=True)
    clubs = sorted(set(played[(played.season == season) & (played["div"] == "D1")].home))
    # One pretend fixture per club after the last match: elo_ratings returns the pre-match rating
    # of a fixture without a score and does not update on it, so this reads the ratings as they stand.
    last = played.date.max()
    ghost = pd.DataFrame([dict(date=last + pd.Timedelta(days=1), season=season, div="D1", home=c, away="~",
                               hg=np.nan, ag=np.nan) for c in clubs])
    full = pd.concat([played[["date", "season", "div", "home", "away", "hg", "ag"]], ghost], ignore_index=True)
    rh, _ = elo_ratings(full)
    now = dict(zip(clubs, rh[-len(clubs):]))
    # A year earlier, the same way.
    year_ago = last - pd.Timedelta(days=365)
    before = played[played.date <= year_ago]
    ghost["date"] = year_ago + pd.Timedelta(days=1)
    ghost["season"] = before.season.max()
    full = pd.concat([before[["date", "season", "div", "home", "away", "hg", "ag"]], ghost], ignore_index=True)
    rh, _ = elo_ratings(full)
    then = dict(zip(clubs, rh[-len(clubs):]))
    return dict(
        asOf=str(last.date()), homeAdvantage=60, k=20,
        clubs=sorted(([name(c), round(float(now[c])), round(float(then[c]))] for c in clubs), key=lambda x: -x[1]),
    )


def backtest_rows(o):
    clubs = sorted({name(c) for c in pd.concat([o.home, o.away])})
    index = {c: i for i, c in enumerate(clubs)}
    per_mille = lambda p: [int(round(1000 * p[0])), int(round(1000 * p[1]))]
    rows = []
    ens = o[cols("ens")].to_numpy(float)
    mkt = o[cols("avgc")].to_numpy(float)
    for i, r in enumerate(o.itertuples(index=False)):
        rows.append([r.date.strftime("%Y-%m-%d"), index[name(r.home)], index[name(r.away)], int(r.hg), int(r.ag),
                     *per_mille(ens[i]), *per_mille(mkt[i])])
    return clubs, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matches_csv")
    ap.add_argument("results_dir", help="the published models' backtest predictions (backtest-results branch, xg/)")
    ap.add_argument("out")
    ap.add_argument("--as-of", required=True)
    a = ap.parse_args()

    m = pd.read_csv(a.matches_csv, parse_dates=["date"])
    o = load(a.matches_csv, a.results_dir)
    o = o[o.hg.notna() & o[cols("avgc")].notna().all(axis=1) & o[cols("ens")].notna().all(axis=1)].reset_index(drop=True)
    season = int(m[m.hg.notna()].season.max())
    clubs, rows = backtest_rows(o)

    out = {
        "about": "Real numbers behind part two of the Learn page, written by analysis/pipeline/learn_data.py "
                 "(never by hand). matches rows: date, home club, away club (indexes into clubs), home goals, "
                 "away goals, ensemble home and draw, market home and draw, all probabilities in tenths of a "
                 "percent; the away win is the rest. The ensemble is the published one, graded out of sample; "
                 "the market is the closing average with the margin removed.",
        "asOf": a.as_of,
        "table": table_spread(m),
        "elo": current_elo(m, season),
        "clubs": clubs,
        "matches": rows,
    }
    # Written next to the target and moved into place, so a failed run never leaves half a file.
    tmp = f"{a.out}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    os.replace(tmp, a.out)
    t = out["table"]
    print(f"table: {t['seasons']} seasons {t['first']}-{t['last']}, final spread {t['sd'][-1]}, "
          f"champion {t['champion']}, bottom {t['bottom']}, H/D/A {t['homeDrawAway']}")
    print(f"elo: {len(out['elo']['clubs'])} clubs as of {out['elo']['asOf']}: {out['elo']['clubs'][:3]}")
    print(f"matches: {len(rows)} from {rows[0][0]} to {rows[-1][0]}; {os.path.getsize(a.out) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
