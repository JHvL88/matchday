"""Charts for the four-league report.

    python analysis/pipeline/make_league_figures.py analysis/backtest/leagues/results.json analysis/backtest/leagues/figs
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figures import INK, MUTED, SOFT, SURF, save, season_label, style


def forest(rows, title, xlabel, left, right, out, name, strong=(), gap_before=(), decimals=1):
    """Dot and 95% interval per row. rows: (label, {diff, low, high}); strong rows are drawn in ink."""
    fig, ax = plt.subplots(figsize=(7.6, 0.45 * len(rows) + 1.3))
    ys, y = [], 0.0
    for i in range(len(rows)):
        if i in gap_before:
            y -= 0.5
        ys.append(y)
        y -= 1
    lo, hi = min(r[1]["low"] for r in rows), max(r[1]["high"] for r in rows)
    lo, hi = min(lo, -abs(hi) * 0.25), max(hi, abs(lo) * 0.25)
    pad = (hi - lo) * 0.08
    ax.axvspan(lo - pad, 0, color="#f4f4f6", zorder=0, linewidth=0)
    ax.axvline(0, color=SOFT, linewidth=1, zorder=1)
    for i, (yy, (lab, p)) in enumerate(zip(ys, rows)):
        key = i in strong
        ax.plot([p["low"], p["high"]], [yy, yy], color=INK if key else SOFT, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([p["diff"]], [yy], s=64 if key else 44, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(hi + pad * 1.2, yy, f"{p['diff'] * 1000:+.{decimals}f}", va="center", fontsize=9.5, color=INK)
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(lo - pad, hi + pad * 3.5)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 1000:+.{max(decimals - 1, 0)}f}" if v else "0"))
    ax.set_xlabel(xlabel)
    ax.text(lo - pad * 0.8, ys[0] + 0.7, left, fontsize=8.5, color=MUTED, va="bottom")
    ax.text(pad * 0.3, ys[0] + 0.7, right, fontsize=8.5, color=MUTED, va="bottom")
    ax.set_ylim(min(ys) - 0.7, ys[0] + 1.25)
    ax.set_title(title, pad=12)
    save(fig, out, name)


def league_rows(res, key):
    rows = [(f"{b['name']}  ·  {b['matches']:,}", b[key]) for b in res["leagues"].values()]
    return rows


if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(os.path.expanduser("~"), ".cache", "matchday")
    os.makedirs(cache, exist_ok=True)
    style(os.path.join(cache, "DMSans.ttf"))
    n = len(res["leagues"])
    four, five = res["new_four"], res["all_five"]

    rows = league_rows(res, "gap_to_market") + [(f"Four new leagues  ·  {four['matches']:,}", four["gap_to_market"]),
                                                (f"All five  ·  {five['matches']:,}", five["gap_to_market"])]
    behind = sum(b["gap_to_market"]["diff"] > 0 for b in res["leagues"].values())
    clear = sum(b["gap_to_market"]["low"] > 0 for b in res["leagues"].values())
    title = (f"The bookmakers were better in {'all ' + str(n) if behind == n else f'{behind} of {n}'} leagues"
             + (f", clearly so in {clear}" if 0 < clear < behind else ""))
    forest(rows, title, "RPS gap × 1,000: ensemble minus closing market (right of 0 = bookmakers better)",
           "models better", "bookmakers better", out, "gap_by_league", strong={n, n + 1}, gap_before={n})

    rows = league_rows(res, "pooled_minus_own") + [(f"All five  ·  {five['matches']:,}", five["pooled_minus_own"])]
    better = sum(b["pooled_minus_own"]["diff"] < 0 for b in res["leagues"].values())
    forest(rows, f"XGBoost trained on all five leagues was better in {better} of {n}",
           "RPS difference × 1,000: pooled XGBoost minus the league's own (left of 0 = pooled better)",
           "pooled better", "own league better", out, "pooled_by_league", strong={n}, gap_before={n}, decimals=2)

    rows = league_rows(res, "two_minus_three") + [(f"All five  ·  {five['matches']:,}", five["two_minus_three"])]
    worse = sum(b["two_minus_three"]["diff"] > 0 for b in res["leagues"].values())
    forest(rows, f"Dropping XGBoost made the ensemble worse in {worse} of {n} leagues" if worse >= n / 2 else
           f"Dropping XGBoost made the ensemble better in {n - worse} of {n} leagues",
           "RPS difference × 1,000: Dixon–Coles + Bayesian minus all three (left of 0 = better without XGBoost)",
           "better without XGBoost", "better with XGBoost", out, "xgboost_place", strong={n}, gap_before={n}, decimals=2)

    seasons = [(f"{season_label(s['season'])}  ·  {s['n']:,}", s) for s in five["per_season"]]
    behind = sum(s[1]["diff"] > 0 for s in seasons)
    forest(seasons, f"All five leagues together: the bookmakers were better in {'every season' if behind == len(seasons) else f'{behind} of {len(seasons)} seasons'}",
           "RPS gap × 1,000: ensemble minus closing market (right of 0 = bookmakers better)",
           "models better", "bookmakers better", out, "gap_by_season")
