"""Check the data behind published posts against the original football-data.co.uk files.

1. The 2026/27 rows embedded in each post's notebook (they were transcribed, so check every cell).
2. The GitHub mirror (xgabora) used for earlier seasons: results, shots and which odds its columns hold.

    python analysis/pipeline/verify_sources.py source/ mirror/Matches.csv data/verify.json
"""
import glob
import io
import json
import re
import sys

import numpy as np
import pandas as pd

from build_matches import build, read_season_file

KEY = ["Date", "HomeTeam", "AwayTeam"]


def embedded_rows(notebook):
    nb = json.load(open(notebook))
    src = "".join("".join(c["source"]) for c in nb["cells"])
    m = re.search(r"EMBEDDED_2627 = '''\n(.*?)'''", src, re.S)
    return None if m is None else pd.read_csv(io.StringIO(m.group(1)))


def check_embedded(notebook, source_dir):
    emb = embedded_rows(notebook)
    if emb is None:
        return None
    live = read_season_file(f"{source_dir}/football-data/2627/D1.csv")
    live = live[[c for c in emb.columns if c in live.columns]].copy()
    for c in emb.columns:
        if c not in KEY:
            live[c] = pd.to_numeric(live[c], errors="coerce")
    m = emb.merge(live, on=KEY, how="left", suffixes=("", "_src"), indicator=True)
    missing = int((m["_merge"] == "left_only").sum())
    diffs = []
    for c in [c for c in emb.columns if c not in KEY]:
        bad = ~np.isclose(m[c], m[f"{c}_src"], rtol=0, atol=1e-9, equal_nan=True)
        for _, r in m[bad & (m["_merge"] == "both")].iterrows():
            diffs.append(dict(date=r.Date, home=r.HomeTeam, away=r.AwayTeam, column=c,
                              embedded=float(r[c]), source=None if pd.isna(r[f"{c}_src"]) else float(r[f"{c}_src"])))
    return dict(notebook=notebook, rows=int(len(emb)), cells=int(len(emb) * (len(emb.columns) - len(KEY))),
                missing_in_source=missing, mismatched_cells=len(diffs), mismatches=diffs)


def check_mirror(mirror_csv, source_dir):
    src = build(source_dir, first_season=2000)
    mir = pd.read_csv(mirror_csv, low_memory=False, parse_dates=["MatchDate"])
    mir = mir[mir.Division.isin(["D1", "D2"])].dropna(subset=["FTHome", "FTAway"])
    mir = mir.rename(columns={"Division": "div", "MatchDate": "date", "HomeTeam": "home", "AwayTeam": "away"})
    m = mir.merge(src, on=["div", "date", "home", "away"], how="outer", indicator=True)
    both = m[m["_merge"] == "both"]
    out = dict(mirror_rows=int(len(mir)), source_rows=int(len(src[src.date <= mir.date.max()])),
               matched=int(len(both)), only_in_mirror=int((m["_merge"] == "left_only").sum()),
               only_in_source_up_to_mirror_end=int(((m["_merge"] == "right_only") & (m.date <= mir.date.max())).sum()))
    pairs = {"goals": [("FTHome", "hg"), ("FTAway", "ag")], "shots": [("HomeShots", "hs"), ("AwayShots", "as_")],
             "shots_on_target": [("HomeTarget", "hst"), ("AwayTarget", "ast")], "red_cards": [("HomeRed", "hr"), ("AwayRed", "ar")]}
    out["field_mismatches"] = {}
    for name, cols in pairs.items():
        bad = np.zeros(len(both), bool)
        for a, b in cols:
            bad |= ~np.isclose(both[a].astype(float), both[b].astype(float), equal_nan=True)
        out["field_mismatches"][name] = int(bad.sum())
    # Which odds does the mirror's OddHome/Draw/Away hold?
    has = both.dropna(subset=["OddHome"])
    odds = {}
    for prefix in ["b365", "b365c", "avg", "avgc"]:
        sub = has.dropna(subset=[f"{prefix}_h"])
        if len(sub):
            eq = np.isclose(sub.OddHome, sub[f"{prefix}_h"]) & np.isclose(sub.OddDraw, sub[f"{prefix}_d"]) & np.isclose(sub.OddAway, sub[f"{prefix}_a"])
            odds[prefix] = dict(compared=int(len(sub)), identical=float(eq.mean()))
    out["mirror_odds_equal_to"] = odds
    recent = has[has.date >= "2025-07-01"]
    out["mirror_odds_equal_to_since_2025_26"] = {
        p: float((np.isclose(recent.OddHome, recent[f"{p}_h"]) & np.isclose(recent.OddAway, recent[f"{p}_a"])).mean())
        for p in ["b365", "b365c", "avgc"] if recent[f"{p}_h"].notna().any()}
    return out


if __name__ == "__main__":
    source_dir, mirror_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    res = dict(embedded=[r for nb in sorted(glob.glob("analysis/*/*.ipynb")) if (r := check_embedded(nb, source_dir))],
               mirror=check_mirror(mirror_csv, source_dir))
    json.dump(res, open(out, "w"), indent=1, default=str)
    for r in res["embedded"]:
        print(f"{r['notebook']}: {r['rows']} rows, {r['cells']} cells, {r['missing_in_source']} rows not in source, "
              f"{r['mismatched_cells']} cells differ")
        for d in r["mismatches"][:20]:
            print("   ", d)
    print(json.dumps(res["mirror"], indent=1))
