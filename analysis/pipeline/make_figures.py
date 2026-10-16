"""Charts for the backtest report, in the posts' style.

    python analysis/pipeline/make_figures.py analysis/backtest/results.json analysis/backtest/figs
"""
import json
import os
import sys
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

INK, MUTED, GRID, SURF, SOFT = "#16161c", "#5f5f69", "#e6e6ea", "#ffffff", "#9a9aa4"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz,wght%5D.ttf"


def style(font_path):
    try:
        if not os.path.exists(font_path):
            urllib.request.urlretrieve(FONT_URL, font_path)
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=font_path).get_name()
    except Exception as e:  # noqa: BLE001 - charts still render in the default font
        print("font skipped:", e)
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
        "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": False, "font.size": 10.5, "axes.titlesize": 11.5, "svg.fonttype": "path",
        "axes.titlelocation": "left", "axes.titlecolor": INK,
    })


def save(fig, out, name):
    for ext in ("svg", "png"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), dpi=200, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def season_label(s, n=None, full=306):
    lab = f"{s}/{(s + 1) % 100:02d}"
    return lab + (" so far" if n is not None and n < full else "")


def gap_by_season(res, out):
    rows = [(season_label(r["season"], r["n"]), r["n"], r["gap"]) for r in res["per_season"]]
    rows.append(("All seasons", res["matches"], res["gap"]))
    fig, ax = plt.subplots(figsize=(7.6, 0.42 * len(rows) + 1.1))
    ys = list(range(len(rows)))[::-1]
    ys[-1] -= 0.6                                            # breathing room above the total row
    lo_all = min(r[2]["low"] for r in rows)
    hi_all = max(r[2]["high"] for r in rows)
    pad = (hi_all - lo_all) * 0.06
    ax.axvspan(lo_all - pad, 0, color="#f4f4f6", zorder=0, linewidth=0)
    ax.axvline(0, color=SOFT, linewidth=1, zorder=1)
    for y, (lab, n, g) in zip(ys, rows):
        total = lab == "All seasons"
        ax.plot([g["low"], g["high"]], [y, y], color=INK if total else SOFT, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([g["gap"]], [y], s=64 if total else 44, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(g["high"] + pad * 0.6, y, f"{g['gap'] * 1000:+.1f}", va="center", fontsize=9.5,
                color=INK)
    ax.set_yticks(ys, [f"{lab}  ·  {n:,}" for lab, n, _ in rows], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(lo_all - pad, hi_all + pad * 4)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 1000:+.0f}" if v else "0"))
    ax.set_xlabel("RPS gap × 1,000: ensemble minus closing market (right of 0 = bookmakers better)")
    ax.text(lo_all - pad * 0.7, ys[0] + 0.75, "models better", fontsize=8.5, color=MUTED, va="bottom")
    ax.text(pad * 0.3, ys[0] + 0.75, "bookmakers better", fontsize=8.5, color=MUTED, va="bottom")
    ax.set_ylim(ys[-1] - 0.7, ys[0] + 1.3)
    full = [r for r in res["per_season"] if r["n"] >= 306]
    behind = sum(r["gap"]["gap"] > 0 for r in full)
    ax.set_title(f"The bookmakers were better in {'all ' + str(behind) if behind == len(full) else f'{behind} of {len(full)}'} full seasons", pad=12)
    save(fig, out, "gap_by_season")


def bridge(res, out):
    steps = res["bridge"]
    labels = ["Published on the site", "Data rebuilt from source", "Closing market as the benchmark",
              f"Longer window ({res['window'].replace(' so far', '')})"]
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    ys = list(range(len(steps)))[::-1]
    vals = [s["gap"] for s in steps]
    for y, v, s, lab in zip(ys, vals, steps, labels):
        last = y == ys[-1]
        ax.barh(y, v, height=0.56, color=INK if last else "#c9c9d0", edgecolor=SURF, linewidth=2)
        ax.text(v + (0.00012 if v >= 0 else -0.00012), y, f"{v * 1000:+.1f}  ({s['n']:,} matches)", va="center",
                ha="left" if v >= 0 else "right", fontsize=9.5, color=INK)
    ax.set_yticks(ys, labels, fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=SOFT, linewidth=1)
    top = max(vals + [0])
    ax.set_xlim(min(vals + [0]) * 1.4 - 0.0004, top * 1.7 + 0.0004)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 1000:+.0f}" if v else "0"))
    ax.set_xlabel("RPS gap × 1,000, ensemble minus bookmakers (positive = bookmakers better)")
    ax.set_title("How the headline gap moved, one change at a time", pad=10)
    save(fig, out, "bridge")


if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(os.path.expanduser("~"), ".cache", "matchday")
    os.makedirs(cache, exist_ok=True)
    style(os.path.join(cache, "DMSans.ttf"))
    gap_by_season(res, out)
    if "bridge" in res:
        bridge(res, out)
    print("charts ->", out)
