"""Build one clean match table (1. + 2. Bundesliga) from the football-data.co.uk season files.

Every row keeps a pointer to its source file and row, so any number can be traced back.

Odds columns (decimal, home/draw/away), where football-data has them:
  avgc_*   market average, closing        <- the benchmark ("the market") from 2019/20 on
  avg_*    market average, pre-closing    (BbAv* before 2019/20)
  b365_*   Bet365, pre-closing             b365c_*  Bet365, closing
  maxc_*   best price in the market, closing
  psc_*    Pinnacle, closing  -- unreliable after 23 Jul 2025 (football-data's own warning); kept, never used

    python analysis/pipeline/build_matches.py source/ data/matches.csv
"""
import glob
import io
import os
import sys

import numpy as np
import pandas as pd

PINNACLE_STALE_FROM = pd.Timestamp("2025-07-23")
GHOST_GAMES = (pd.Timestamp("2020-05-16"), pd.Timestamp("2021-07-31"))   # behind closed doors

# football-data column -> our name. The first column found wins (newer files first).
COLUMNS = {
    "home": ["HomeTeam", "HT"], "away": ["AwayTeam", "AT"],
    "hg": ["FTHG", "HG"], "ag": ["FTAG", "AG"],
    "hs": ["HS"], "as_": ["AS"], "hst": ["HST"], "ast": ["AST"], "hr": ["HR"], "ar": ["AR"],
    "time": ["Time"],
}
ODDS = {
    "avgc": ("AvgCH", "AvgCD", "AvgCA"),
    "avg": [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA")],
    "b365": ("B365H", "B365D", "B365A"),
    "b365c": ("B365CH", "B365CD", "B365CA"),
    "maxc": ("MaxCH", "MaxCD", "MaxCA"),
    "psc": ("PSCH", "PSCD", "PSCA"),
}


def season_of(date):
    return np.where(date.dt.month >= 7, date.dt.year, date.dt.year - 1)


def read_season_file(path):
    """Read one football-data CSV as served (handles old encodings, stray blank columns/rows)."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    f = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, on_bad_lines="skip")
    f.columns = [c.strip() for c in f.columns]
    f = f.loc[:, [c for c in f.columns if c and not c.startswith("Unnamed")]]
    f["src_row"] = np.arange(2, len(f) + 2)          # 1-based line number in the file (header = 1)
    return f[f.get("HomeTeam", f.get("HT", "")).astype(str).str.strip() != ""].copy()


def standardise(f, div, rel_path):
    out = pd.DataFrame(index=f.index)
    out["div"] = div
    out["date"] = pd.to_datetime(f["Date"].str.strip(), dayfirst=True, format="mixed")
    for name, cands in COLUMNS.items():
        col = next((c for c in cands if c in f.columns), None)
        out[name] = f[col].str.strip() if col else ""
    for name in ["hg", "ag", "hs", "as_", "hst", "ast", "hr", "ar"]:
        out[name] = pd.to_numeric(out[name], errors="coerce")
    for key, spec in ODDS.items():
        options = spec if isinstance(spec, list) else [spec]
        cols = next((o for o in options if all(c in f.columns for c in o)), None)
        for side, k in zip("hda", range(3)):
            v = pd.to_numeric(f[cols[k]], errors="coerce") if cols else np.nan
            out[f"{key}_{side}"] = v
    for c in [c for c in out.columns if c[:-1].endswith("_") and c.split("_")[0] in ODDS]:
        out.loc[out[c] <= 1.0, c] = np.nan                # football-data uses blanks/0 for missing
    out["src_file"] = rel_path
    out["src_row"] = f["src_row"].values
    return out


def build(source_dir, first_season=2005):
    frames = []
    for path in sorted(glob.glob(os.path.join(source_dir, "football-data", "*", "D[12].csv"))):
        rel = os.path.relpath(path, source_dir)
        div = os.path.basename(path)[:2]
        frames.append(standardise(read_season_file(path), div, rel))
    df = pd.concat(frames, ignore_index=True)
    df["season"] = season_of(df.date)
    df = df[df.season >= first_season]
    df = df.dropna(subset=["hg", "ag"]).copy()
    df[["hg", "ag"]] = df[["hg", "ag"]].astype(int)
    df["ghost"] = ((df.date >= GHOST_GAMES[0]) & (df.date <= GHOST_GAMES[1])).astype(int)
    df["psc_stale"] = (df.date >= PINNACLE_STALE_FROM).astype(int)
    df = df.sort_values(["date", "div", "home"]).reset_index(drop=True)
    dup = df.duplicated(["date", "home", "away"])
    if dup.any():
        raise ValueError(f"{dup.sum()} duplicate matches, e.g. {df[dup].iloc[0][['date', 'home', 'away']].tolist()}")
    return df


def market_probs(df, prefix="avgc"):
    """Bookmaker probabilities with the margin removed proportionally."""
    inv = 1 / df[[f"{prefix}_h", f"{prefix}_d", f"{prefix}_a"]].to_numpy(float)
    return inv / inv.sum(1, keepdims=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--understat", help="add Understat match xG (hxg, axg) from this folder")
    a = ap.parse_args()
    out = a.out
    df = build(a.source)
    if a.understat:
        from understat import add_xg
        df = add_xg(df, a.understat)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    df.to_csv(out, index=False)
    d1 = df[df["div"] == "D1"]
    print(f"{len(df)} matches ({len(d1)} D1, {len(df) - len(d1)} D2), seasons {df.season.min()}-{df.season.max()}")
    cov = d1.groupby("season").agg(n=("hg", "size"), sot=("hst", lambda x: x.notna().mean()),
                                    avgc=("avgc_h", lambda x: x.notna().mean()), b365=("b365_h", lambda x: x.notna().mean()))
    print(cov.tail(10).round(3).to_string())
