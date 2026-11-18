"""Charts for the season simulator's report.

    python analysis/pipeline/make_season_figures.py analysis/backtest/season/results.json analysis/backtest/season/figs
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figures import GRID, INK, MUTED, SOFT, SURF, save, style


def doubt(res, out):
    """Tuning seasons: the score for every amount of doubt, my models and the bookmakers' ratings."""
    grid = res["grid"]
    xi = res["chosen"]["market"]["xi"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    m = sorted((float(k), v) for k, v in grid["models"].items())
    k = sorted((float(s.split("|")[0]), v) for s, v in grid["market"].items() if float(s.split("|")[1]) == xi)
    ax.plot([a for a, _ in m], [b for _, b in m], color=INK, linewidth=2, marker="o", markersize=6, label="My models")
    ax.plot([a for a, _ in k], [b for _, b in k], color=INK, linewidth=1.5, linestyle=(0, (1, 2.5)), marker="o", markersize=6,
            markerfacecolor=SURF, label=f"Bookmakers (decay {xi:g} per day)")
    for chosen, rows, dy in ((res["chosen"]["models"]["sigma"], m, -16), (res["chosen"]["market"]["sigma"], k, 9)):
        y = dict(rows)[chosen]
        ax.annotate("chosen", (chosen, y), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=8.5, color=MUTED)
    ax.set_xlabel("Doubt: the spread (sigma) of one strength shift per club per simulated season")
    ax.set_ylabel("Positional RPS, lower is better")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.tick_params(length=0)
    ax.legend(frameon=False, loc="upper center")
    ax.set_title("Tuning seasons 2014/15 to 2018/19: a little doubt helps, a lot hurts", pad=12)
    save(fig, out, "doubt")


def calibration(res, out):
    t = res["test"]
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.plot([0, 1], [0, 1], color=SOFT, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    for key, face, label in (("market", SURF, "Bookmakers"), ("models", INK, "My models")):
        rows = t[key]["calibration"]
        ax.scatter([r["forecast"] for r in rows], [r["happened"] for r in rows], s=54, color=face, edgecolor=INK,
                   linewidth=1.5, zorder=3, label=label)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ticks = [0, 0.25, 0.5, 0.75, 1]
    ax.set_xticks(ticks, [f"{x:.0%}" for x in ticks])
    ax.set_yticks(ticks, [f"{x:.0%}" for x in ticks])
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_xlabel("Forecast chance (title, top 4, top 6, 16th, 17th–18th)")
    ax.set_ylabel("How often it happened")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Test seasons 2019/20 to 2025/26: forecast against reality", pad=12)
    save(fig, out, "calibration")


def through_the_season(res, out):
    t = res["test"]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = list(range(34))
    ax.plot(x, t["models"]["byCheckpoint"], color=INK, linewidth=2, label="My models")
    ax.plot(x, t["market"]["byCheckpoint"], color=INK, linewidth=1.6, linestyle=(0, (1, 2.5)), label="Bookmakers")
    ax.set_xlabel("Matchdays played")
    ax.set_ylabel("Positional RPS, lower is better")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.tick_params(length=0)
    ax.legend(frameon=False)
    ax.set_title("The forecast sharpens as the season goes on", pad=12)
    save(fig, out, "through_the_season")


def by_season(res, out):
    t = res["test"]
    seasons = sorted(t["models"]["seasons"], key=int)
    labels = [f"{int(s)}/{(int(s) + 1) % 100:02d}" for s in seasons]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    w = 0.38
    xs = range(len(seasons))
    ax.bar([i - w / 2 for i in xs], [t["models"]["seasons"][s] for s in seasons], width=w, color=INK, label="My models")
    ax.bar([i + w / 2 for i in xs], [t["market"]["seasons"][s] for s in seasons], width=w, color=SURF, edgecolor=INK, linewidth=1.3,
           label="Bookmakers")
    ax.set_xticks(list(xs), labels)
    ax.set_ylabel("Positional RPS, lower is better")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    won = t["marketBetterSeasons"]
    ax.set_title(f"Season by season: the bookmakers' ratings ahead in {won} of {len(seasons)}", pad=12)
    save(fig, out, "by_season")


def main():
    res = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(os.path.expanduser("~"), ".cache", "matchday")
    os.makedirs(cache, exist_ok=True)
    style(os.path.join(cache, "DMSans.ttf"))
    doubt(res, out)
    calibration(res, out)
    through_the_season(res, out)
    by_season(res, out)
    print("figures ->", out)


if __name__ == "__main__":
    main()
