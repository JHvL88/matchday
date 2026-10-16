"""Charts for the xG test report.

    python analysis/pipeline/make_xg_figures.py analysis/backtest/xg/results.json analysis/backtest/xg/figs
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figures import INK, MUTED, SOFT, SURF, save, season_label, style


def dots(rows, title, xlabel, out, name, highlight_last=True):
    fig, ax = plt.subplots(figsize=(7.6, 0.45 * len(rows) + 1.2))
    ys = list(range(len(rows)))[::-1]
    if highlight_last and len(ys) > 1:
        ys[-1] -= 0.5
    lo = min(r[1]["low"] for r in rows)
    hi = max(r[1]["high"] for r in rows)
    lo, hi = min(lo, -abs(hi) * 0.3), max(hi, abs(lo) * 0.3)
    pad = (hi - lo) * 0.08
    ax.axvspan(lo - pad, 0, color="#f4f4f6", zorder=0, linewidth=0)
    ax.axvline(0, color=SOFT, linewidth=1, zorder=1)
    for i, (y, (lab, p)) in enumerate(zip(ys, rows)):
        key = highlight_last and i == len(rows) - 1
        ax.plot([p["low"], p["high"]], [y, y], color=INK if key else SOFT, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([p["diff"]], [y], s=64 if key else 44, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(hi + pad * 1.2, y, f"{p['diff'] * 1000:+.2f}", va="center", fontsize=9.5, color=INK)   # one column
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(lo - pad, hi + pad * 3.5)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 1000:+.1f}" if v else "0"))
    ax.set_xlabel(xlabel)
    ax.text(lo - pad * 0.8, ys[0] + 0.7, "xG version better", fontsize=8.5, color=MUTED, va="bottom")
    ax.text(pad * 0.3, ys[0] + 0.7, "current version better", fontsize=8.5, color=MUTED, va="bottom")
    ax.set_ylim(min(ys) - 0.7, ys[0] + 1.25)
    ax.set_title(title, pad=12)
    save(fig, out, name)


if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(os.path.expanduser("~"), ".cache", "matchday")
    os.makedirs(cache, exist_ok=True)
    style(os.path.join(cache, "DMSans.ttf"))
    c = res["components"]
    rows = [("Dixon–Coles", c["dc"]), ("Bayesian", c["bay"]), ("XGBoost", c["xgb"]), ("Ensemble (the test)", res["q1"])]
    verdict = "xG helps every model" if all(r[1]["diff"] < 0 for r in rows) else "What xG changed"
    dots(rows, verdict, "RPS difference × 1,000, xG version minus current (left of 0 = xG better)", out, "xg_by_model")
    seasons = [(season_label(s["season"], s["n"]), s) for s in res["per_season"]]
    better = sum(s[1]["diff"] < 0 for s in seasons if s[1]["n"] >= 306)
    full = sum(1 for s in seasons if s[1]["n"] >= 306)
    dots(seasons, f"The xG ensemble was better in {better} of {full} full seasons",
         "RPS difference × 1,000, Ensemble-xG minus Ensemble (left of 0 = xG better)", out, "xg_by_season", highlight_last=False)
    print("charts ->", out)
