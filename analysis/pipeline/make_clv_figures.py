"""Charts for the closing-line report.

    python analysis/pipeline/make_clv_figures.py analysis/backtest/clv/results.json analysis/backtest/clv/figs
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figures import GRID, INK, MUTED, SOFT, SURF, save, style


def line_move(block, out):
    """Average line move against the models' edge, with the two lines it could have followed."""
    rows = block["q1"]["buckets"]
    x = [r["edge"] * 100 for r in rows]
    y = [r["move"]["mean"] * 100 for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    lim = 10
    ax.axhline(0, color=SOFT, linewidth=1, zorder=1)
    ax.plot([-lim, lim], [-lim, lim], color=SOFT, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(4.0, 3.45, "if the market came round\nto the models completely", fontsize=8.5, color=MUTED, ha="left", va="top")
    ax.text(lim, 0.22, "if it ignored them", fontsize=8.5, color=MUTED, ha="right", va="bottom")
    for xx, r in zip(x, rows):
        ax.plot([xx, xx], [r["move"]["low"] * 100, r["move"]["high"] * 100], color=INK, linewidth=2, solid_capstyle="round", zorder=2)
    ax.scatter(x, y, s=64, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
    for xx, yy, r in zip(x, y, rows):
        near_diagonal = abs(xx) < 1.5
        ax.text(xx + (0.9 if near_diagonal else 0), yy - (0.3 if near_diagonal else 0.5), f"{yy:+.2f}",
                ha="left" if near_diagonal else "center", va="top", fontsize=9.5, color=INK)
        ax.text(xx, -4.25, f"{r['outcomes']:,}", ha="center", va="bottom", fontsize=8.5, color=MUTED)
    ax.text(-lim, -3.72, "outcomes in each group", ha="left", va="bottom", fontsize=8.5, color=MUTED)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-4.4, 3.7)
    ax.set_xticks([-8, -4, 0, 4, 8], ["−8", "−4", "0", "+4", "+8"])
    ax.set_yticks([-3, -2, -1, 0, 1, 2, 3], ["−3", "−2", "−1", "0", "+1", "+2", "+3"])
    ax.tick_params(length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Models minus early market (points): right of 0 = the models rate the outcome higher")
    ax.set_ylabel("Line move by kick-off (points)")
    s = block["q1"]
    flat = s["low"] < 0 < s["high"]
    ax.set_title("Whatever the models thought, the line did not move their way" if flat else
                 f"The line closed {s['slope'] * 100:+.1f}% of the gap to the models", pad=12)
    save(fig, out, "line_move")


def forest(rows, title, xlabel, out, name, gap_before=(), strong=(), lo_hi=None):
    """Dot and 95% interval per row, in percent. rows: (label, {mean, low, high})."""
    fig, ax = plt.subplots(figsize=(7.6, 0.45 * len(rows) + 1.3))
    ys, y = [], 0.0
    for i in range(len(rows)):
        if i in gap_before:
            y -= 0.5
        ys.append(y)
        y -= 1
    lo, hi = lo_hi or (min(r[1]["low"] for r in rows), max(max(r[1]["high"] for r in rows), 0.0))
    pad = (hi - lo) * 0.08
    ax.axvspan(lo - pad, 0, color="#f4f4f6", zorder=0, linewidth=0)
    ax.axvline(0, color=SOFT, linewidth=1, zorder=1)
    for i, (yy, (lab, p)) in enumerate(zip(ys, rows)):
        key = i in strong
        ax.plot([p["low"], p["high"]], [yy, yy], color=INK if key else SOFT, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([p["mean"]], [yy], s=64 if key else 44, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(hi + pad * 1.2, yy, f"{p['mean'] * 100:+.1f}%", va="center", fontsize=9.5, color=INK)
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(lo - pad, hi + pad * 3.8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 100:+.0f}%" if abs(v) > 1e-9 else "0"))
    ax.set_xlabel(xlabel)
    ax.text(lo - pad * 0.8, ys[0] + 0.7, "money lost", fontsize=8.5, color=MUTED, va="bottom")
    ax.text(pad * 0.3, ys[0] + 0.7, "money won", fontsize=8.5, color=MUTED, va="bottom")
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
    A = res["five_leagues"]
    line_move(A, out)

    rule, mirror, every = A["rule"]["avg"], A["mirror"]["avg"], A["every_bet"]["avg"]
    rows = [(f"The site's rule  ·  {rule['bets']:,} bets", rule["realised_return"]),
            (f"The mirror rule  ·  {mirror['bets']:,}", mirror["realised_return"]),
            (f"Every possible bet  ·  {every['bets']:,}", every["realised_return"])]
    forest(rows, f"The rule lost {-rule['realised_return']['mean'] * 100:.0f} cents per euro; betting on everything lost "
                 f"{-every['realised_return']['mean'] * 100:.0f}",
           "Realised return per €1 staked at the average early price, with 95% interval", out, "returns", strong={0})

    leagues = [(f"{b['name']}  ·  {b['rule']['bets']:,} bets", b["rule"]["realised_return"]) for b in A["per_league"].values()]
    n = len(leagues)
    lost = sum(r[1]["mean"] < 0 for r in leagues)
    rows = leagues + [(f"All five  ·  {rule['bets']:,}", rule["realised_return"])]
    forest(rows, f"The rule lost money in {'every league' if lost == n else f'{lost} of {n} leagues'}",
           "Realised return per €1 staked at the average early price, with 95% interval", out, "returns_by_league",
           gap_before={n}, strong={n})
