"""Charts for the market-as-input report.

    python analysis/pipeline/make_blend_figures.py analysis/backtest/blend/results.json analysis/backtest/blend/figs
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figures import INK, MUTED, SOFT, SURF, save, season_label, style


def forest(rows, title, xlabel, out, name, fmt, left, right, gap_before=(), strong=(), ticks=None):
    """Dot and 95% interval per row. rows: (label, {value | mean, low, high}); fmt writes the number at the end."""
    fig, ax = plt.subplots(figsize=(7.6, 0.45 * len(rows) + 1.3))
    ys, y = [], 0.0
    for i in range(len(rows)):
        if i in gap_before:
            y -= 0.5
        ys.append(y)
        y -= 1
    val = lambda p: p["value"] if "value" in p else p["mean"]      # noqa: E731
    lo = min(min(r[1]["low"] for r in rows), 0.0)
    hi = max(max(r[1]["high"] for r in rows), 0.0)
    pad = (hi - lo) * 0.08
    ax.axvspan(lo - pad, 0, color="#f4f4f6", zorder=0, linewidth=0)
    ax.axvline(0, color=SOFT, linewidth=1, zorder=1)
    for i, (yy, (lab, p)) in enumerate(zip(ys, rows)):
        key = i in strong
        ax.plot([p["low"], p["high"]], [yy, yy], color=INK if key else SOFT, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([val(p)], [yy], s=64 if key else 44, color=INK, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(hi + pad * 1.2, yy, fmt(val(p)), va="center", fontsize=9.5, color=INK)
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(lo - pad, hi + pad * 3.8)
    if ticks:
        ax.set_xticks(ticks[0], ticks[1])
    ax.set_xlabel(xlabel)
    ax.text(-pad * 0.3, ys[0] + 0.7, left, fontsize=8.5, color=MUTED, va="bottom", ha="right")
    ax.text(pad * 0.3, ys[0] + 0.7, right, fontsize=8.5, color=MUTED, va="bottom", ha="left")
    ax.set_ylim(min(ys) - 0.7, ys[0] + 1.25)
    ax.set_title(title, pad=12)
    save(fig, out, name)


def weights(res, out):
    """The weight on the models next to the price, for every forecast tested."""
    A = res["five_leagues"]
    c = lambda b: b["weights"]["price_and_models"]["models"]      # noqa: E731
    rows = [(f"The ensemble  ·  {A['weights']['matches']:,} matches", c(A)),
            ("Dixon–Coles alone", c(A["per_model"]["dixon_coles"])),
            ("Bayesian alone", c(A["per_model"]["bayesian"])),
            ("XGBoost alone", c(A["per_model"]["xgboost"])),
            ("Ensemble, XGBoost on five leagues", c(A["per_model"]["ensemble_pooled_xgboost"])),
            ("The ensemble next to the closing price", c(A["closing_price"]))]
    gap = {5}
    if "bundesliga_published" in res:
        B = res["bundesliga_published"]
        rows.append((f"Bundesliga, published models  ·  {B['matches']:,}", c(B)))
        gap.add(6)
    above = sum(r[1]["low"] > 0 for r in rows)
    title = "No forecast earns a weight above zero next to the price" if not above else \
        f"{above} of {len(rows)} forecasts earn a weight above zero next to the price"
    forest(rows, title, "Weight on the models (c) once the forecaster has the early price, with 95% interval", out, "weights",
           lambda v: f"{v:+.2f}".replace("-", "−"), "lean away from the models", "lean toward them", gap_before=gap, strong={0},
           ticks=([-0.75, -0.5, -0.25, 0, 0.25], ["−0.75", "−0.5", "−0.25", "0", "+0.25"]))


def gain(res, out):
    """Log loss with the models minus without, on matches the blend had not seen, per season."""
    u = res["five_leagues"]["unseen"]
    rows = [(f"{season_label(r['season'], r['gain']['matches'], 1500)}  ·  {r['gain']['matches']:,} matches", r["gain"]["log_loss"])
            for r in u["per_season"]]
    rows.append((f"All seasons  ·  {u['gain']['matches']:,}", u["gain"]["log_loss"]))
    n = len(rows) - 1
    g = u["gain"]["log_loss"]
    title = "Shown the models, the price forecast no better" if g["low"] < 0 < g["high"] else \
        ("Shown the models, the price forecast better" if g["high"] < 0 else "Shown the models, the price forecast worse")
    forest(rows, title, "Log loss with the models minus without, on matches the blend hadn't seen (95% interval)", out, "gain",
           lambda v: f"{v:+.5f}".replace("-", "−"), "the models helped", "the models hurt", gap_before={n}, strong={n},
           ticks=([-0.001, 0, 0.001, 0.002], ["−0.001", "0", "+0.001", "+0.002"]))


def returns(res, out):
    """Realised return of the break-even rule, with and without the models, against betting on everything."""
    u = res["five_leagues"]["unseen"]
    rows = [(f"Price and models, average price  ·  {u['rule']['avg']['bets']:,} bets", u["rule"]["avg"]["realised_return"]),
            (f"Price and models, best price  ·  {u['rule']['max']['bets']:,}", u["rule"]["max"]["realised_return"]),
            (f"Price only, best price  ·  {u['price_only_rule']['max']['bets']:,}", u["price_only_rule"]["max"]["realised_return"]),
            (f"Every possible bet, average price  ·  {u['every_bet']['avg']['bets']:,}", u["every_bet"]["avg"]["realised_return"]),
            (f"Every possible bet, best price  ·  {u['every_bet']['max']['bets']:,}", u["every_bet"]["max"]["realised_return"])]
    clear = sum(r[1]["low"] > 0 for r in rows[:3])
    title = "No version of the rule clears zero" if not clear else f"{clear} of 3 versions of the rule clear zero"
    forest(rows, title, "Realised return per €1 staked, with 95% interval", out, "returns",
           lambda v: f"{v * 100:+.1f}%".replace("-", "−"), "money lost", "money won", gap_before={2, 3}, strong={0, 1},
           ticks=([-0.10, -0.05, 0, 0.05], ["−10%", "−5%", "0", "+5%"]))


if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(os.path.expanduser("~"), ".cache", "matchday")
    os.makedirs(cache, exist_ok=True)
    style(os.path.join(cache, "DMSans.ttf"))
    weights(res, out)
    gain(res, out)
    returns(res, out)
