"""Add each published forecast's closing odds to analysis/posts.json, for closing-line value.

The closing price is football-data.co.uk's market average at kick-off (AvgC), the same benchmark as
the backtest. The Track record page then shows, for every paper bet, what it was worth at the close:

    closing-line value = odds taken x closing probability (margin removed) - 1

Positive means the bet was taken at a better price than the market settled on; over many bets that
is the best early sign of skill, long before profit and loss can say anything.

    python analysis/pipeline/grade_posts.py source/ analysis/posts.json
"""
import json
import sys

import pandas as pd

from build_matches import build
from jsonfmt import dumps
from teams import club_key

SOURCE_NOTE = {"en": "market average at kick-off (football-data.co.uk)",
               "de": "Marktdurchschnitt zum Anpfiff (football-data.co.uk)"}


def main(source_dir, posts_path):
    m = build(source_dir, first_season=2025)
    m = m[m["div"] == "D1"].copy()
    m["home_key"], m["away_key"] = m.home.map(club_key), m.away.map(club_key)
    posts = json.load(open(posts_path, encoding="utf-8"))
    changed = 0
    for p in posts["posts"]:
        kickoff = pd.Timestamp(p["kickoff"])
        if kickoff > pd.Timestamp.now(tz="UTC"):
            continue
        hk, ak = club_key(p["home"]["name"]), club_key(p["away"]["name"])
        day = kickoff.tz_convert("Europe/Berlin").tz_localize(None).normalize()
        row = m[(m.home_key == hk) & (m.away_key == ak) & ((m.date - day).abs() <= pd.Timedelta(days=1))]
        if len(row) != 1 or row[["avgc_h", "avgc_d", "avgc_a"]].isna().any(axis=None):
            print(f"{p['slug']}: no closing odds in the source files yet")
            continue
        r = row.iloc[0]
        closing = {"odds": [float(r.avgc_h), float(r.avgc_d), float(r.avgc_a)], "source": SOURCE_NOTE,
                   "file": f"{r.src_file}#L{int(r.src_row)}"}
        if p.get("closing") != closing:
            p["closing"] = closing
            changed += 1
            print(f"{p['slug']}: closing odds {closing['odds']} ({closing['file']})")
    if changed:
        with open(posts_path, "w", encoding="utf-8") as f:
            f.write(dumps(posts, inline_number_objects=True) + "\n")
    print(f"{changed} post(s) updated")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
