"""Grade a published forecast at full time and draw the full-time chart (English and German).

    python analysis/tools/fulltime.py analysis/2026-27-md6-hamburg-stuttgart --score 2 1 \
        --odds ../matchday-data/odds --understat ../matchday-data/understat \
        --frozen analysis/2026-27-md6-hamburg-stuttgart/frozen/*.json --fig 11

Reads the post's published_forecast.json (the numbers as published) and its entry in analysis/posts.json,
and writes <post>/fulltime.json plus figs/fig<N>_fulltime.svg and figs/de/fig<N>_fulltime.svg.

Grades:
  RPS          ranked probability score of every published forecaster for this one match (lower is better)
  paper bet    the Track record page's rule: 1 euro on every outcome the ensemble rates at least
               5 points above the market, at the odds quoted in the post
  CLV          closing-line value = odds taken x closing probability (margin removed) - 1, against the
               consensus of the last recorded snapshot before kick-off (football-data.co.uk's closing
               average follows on the Track record page when the source files update)
"""
import argparse
import glob
import gzip
import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "analysis", "pipeline"))
from teams import club_key  # noqa: E402

THRESHOLD = 0.05
NAMES = {"en": ["home win", "draw", "away win"], "de": ["Heimsieg", "Remis", "Auswärtssieg"]}


def rps(p, outcome):
    p = np.asarray(p, float) / np.sum(p)
    f = np.cumsum(p)[:2]
    o = np.array([outcome == 0, outcome <= 1], float)
    return float(((f - o) ** 2).sum() / 2)


def outcome_of(h, a):
    return 0 if h > a else 1 if h == a else 2


def fair(odds):
    inv = 1 / np.asarray(odds, float)
    return inv / inv.sum()


def snapshots_for(odds_dir, home, away, kickoff):
    """Consensus, Pinnacle and best reader prices in every recorded snapshot of this match before kick-off."""
    import odds_store
    out = []
    for path in odds_store.snapshot_files(odds_dir):
        snap = odds_store.read_snapshot(path)
        taken = pd.Timestamp(snap["meta"]["taken_at"])
        if taken >= kickoff:
            continue
        df = odds_store.tidy(snap)
        if not len(df):
            continue
        w = odds_store.match_odds(df)
        r = w[(w.home_key == club_key(home)) & (w.away_key == club_key(away))]
        if not len(r):
            continue
        s = odds_store.summarise(r)
        s.update(taken_at=taken.strftime("%Y-%m-%dT%H:%M:%SZ"), minutes_before=round((kickoff - taken).total_seconds() / 60),
                 reasons=snap["meta"].get("reasons"), label=snap["meta"].get("label"),
                 file=os.path.relpath(path, odds_dir))
        out.append(s)
    return out


def match_xg(understat_dir, home, away, kickoff):
    import understat
    u = understat.load(understat_dir)
    r = u[(u.home_key == club_key(home)) & (u.away_key == club_key(away))
          & ((u.day - kickoff.tz_convert(None).normalize()).abs() <= pd.Timedelta(days=1))]
    if len(r) != 1:
        return None
    r = r.iloc[0]
    out = dict(xg=[round(r.hxg, 2), round(r.axg, 2)], goals=[int(r.hg_u), int(r.ag_u)], understat_id=r.understat_id)
    for path in glob.glob(os.path.join(understat_dir, "Bundesliga", "*.json")):   # Understat's own result split
        for e in json.load(open(path, encoding="utf-8")).get("dates", []):
            if str(e["id"]) == r.understat_id and e.get("forecast"):
                fc = e["forecast"]
                out["xgResultSplit"] = [float(fc["w"]), float(fc["d"]), float(fc["l"])]
    return out


def ranked_scores(grid):
    """(home goals, away goals, percent) for every labelled cell, most likely first."""
    cells = [(i, j, v) for i, row in enumerate(grid) for j, v in enumerate(row) if v is not None]
    return sorted(cells, key=lambda c: -c[2])


# ------------------------------------------------------------------------------------------- chart
INK, MUTED, SURF = "#16161c", "#5f5f69", "#ffffff"
TINT = ["#a9c4f2", "#d4d4da", "#ebbd99"]   # light versions of the site's home / draw / away colours
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz,wght%5D.ttf"


def chart(ranked, score, labels, lang, path, top=12):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font = os.path.join(os.path.expanduser("~"), ".cache", "jans-matchday", "DMSans.ttf")
    try:
        if not os.path.exists(font):
            os.makedirs(os.path.dirname(font), exist_ok=True)
            urllib.request.urlretrieve(FONT_URL, font)
        font_manager.fontManager.addfont(font)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=font).get_name()
    except Exception as e:  # noqa: BLE001 - the chart still renders in the default font
        print("font skipped:", e)
    plt.rcParams.update({"svg.fonttype": "path", "font.size": 10.5, "text.color": INK,
                         "axes.labelcolor": MUTED, "ytick.color": INK})
    cut = ranked[top - 1][2]
    rows = [c for c in ranked if c[2] >= cut]               # ties at the cut-off all stay in
    hit = [c for c in ranked if (c[0], c[1]) == tuple(score)]
    extra = hit and hit[0] not in rows
    if extra:
        rows = rows + hit
    sep = "–" if lang == "en" else ":"
    pct = (lambda v: f"{v:.1f}%") if lang == "en" else (lambda v: f"{v:.1f}".replace(".", ",") + " %")
    tag = "← full time" if lang == "en" else "← Endstand"
    fig, ax = plt.subplots(figsize=(5.4, 0.27 * len(rows) + 0.35 + (0.25 if extra else 0)))
    ys = np.arange(len(rows))[::-1].astype(float)
    if extra:
        ys[-1] -= 0.6
    for y, (i, j, v) in zip(ys, rows):
        is_hit = (i, j) == tuple(score)
        ax.barh(y, v, height=0.62, color=INK if is_hit else TINT[outcome_of(i, j)], edgecolor=SURF, linewidth=0)
        ax.text(v + 0.15, y, pct(v) + (f"   {tag}" if is_hit else ""), va="center", fontsize=10.5, color=INK)
    if not hit:   # the score was below 0.5% and is not labelled on the published heatmap
        msg = f"{score[0]}{sep}{score[1]} at full time: below 0.5%" if lang == "en" else \
              f"Endstand {score[0]}{sep}{score[1]}: unter 0,5 %"
        ax.text(0, ys[-1] - 1.0, msg, fontsize=10.5, color=INK, va="center")
    ax.set_yticks(ys, [f"{i}{sep}{j}" for i, j, _ in rows], fontsize=11)
    ax.set_ylabel(f"{labels[0]} – {labels[1]}", fontsize=10.5, color=MUTED)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(0, ranked[0][2] * 1.45)
    ax.set_ylim(min(ys) - (1.6 if not hit else 0.6), max(ys) + 0.6)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.15, facecolor=SURF)
    plt.close(fig)


WEEKDAY = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "de": ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]}
BLUE, ORANGE = "#2f6fdb", "#c25a00"


def views_chart(rows, breakeven, odds, lang, path, color):
    """Everyone's probability for the outcome that was bet on, top to bottom, with the bet's break-even line.

    rows: (label, probability, kind) with kind in {"model", "market", "after"}."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 0.36 * len(rows) + 0.9))
    ys, y, last = [], 0.0, None
    for _, _, kind in rows:
        if last is not None and kind != last:
            y += 0.45                       # a little air between models, bookmakers and hindsight
        ys.append(-y)
        y, last = y + 1, kind
    ps = [p for _, p, _ in rows] + [breakeven]
    lo, hi = np.floor(min(ps) * 20 - 0.6) / 20, np.ceil(max(ps) * 20 + 0.6) / 20     # 5-point steps
    pc = (lambda v: f"{v * 100:.1f}%") if lang == "en" else (lambda v: f"{v * 100:.1f}".replace(".", ",") + "\u00a0%")
    for t in np.arange(lo, hi + 1e-9, 0.05):
        ax.axvline(t, color="#ececf0", linewidth=1, zorder=0)
        ax.text(t, ys[-1] - 0.95, f"{t * 100:.0f}%" if lang == "en" else f"{t * 100:.0f}\u00a0%",
                ha="center", va="top", fontsize=9, color=MUTED)
    ax.plot([breakeven, breakeven], [ys[-1] - 0.6, ys[0] + 0.6], color=MUTED, linewidth=1, linestyle=(0, (3, 3)), zorder=1)
    be = f"break-even at odds {odds:.2f}: {pc(breakeven)}" if lang == "en" else \
         f"Gewinnschwelle bei Quote {odds:.2f}".replace(".", ",") + f": {pc(breakeven)}"
    ax.text(breakeven, ys[0] + 0.8, be, ha="center", va="bottom", fontsize=9.5, color=MUTED)
    gap = (hi - lo) * 0.025
    for (label, p, kind), yy in zip(rows, ys):
        ax.scatter([p], [yy], s=70, color=color if kind != "after" else MUTED, edgecolor=SURF, linewidth=1.5, zorder=3)
        left = p < breakeven              # keep every value label clear of the break-even line
        ax.text(p - gap if left else p + gap, yy, pc(p), va="center", ha="right" if left else "left", fontsize=10, color=INK)
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=10)
    ax.tick_params(axis="y", length=0, colors=INK)
    ax.set_xticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlim(lo, hi)
    ax.set_ylim(ys[-1] - 1.3, ys[0] + 1.5)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.15, facecolor=SURF)
    plt.close(fig)


def views_rows(res, frozen, lang, pick, published_label, after_label):
    """The rows for views_chart: published models, frozen xG models, bookmakers over time, hindsight."""
    i = ["home", "draw", "away"].index(pick)
    w = WEEKDAY[lang]
    rows = [(published_label, res["paperBets"][0]["model"], "model")]
    for fz in frozen:
        if fz["xg"]:
            m = fz["fixtures"][0]["models"]["ens"]
            when = pd.Timestamp(fz["created_at"]).tz_convert("Europe/Berlin")
            lab = f"xG models (frozen {w[when.weekday()]} {when:%H:%M})" if lang == "en" else \
                  f"xG-Modelle (eingefroren {w[when.weekday()]} {when:%H:%M})"
            rows.append((lab, [m["H"], m["D"], m["A"]][i], "model"))
    pubq = "Bookmakers, Thu (Bet365, in the post)" if lang == "en" else "Buchmacher, Do. (Bet365, im Beitrag)"
    rows.append((pubq, res["paperBets"][0]["market"], "market"))
    snaps = res["odds"]["snapshots"]
    for n, s in enumerate(snaps):
        t = pd.Timestamp(s["taken_at"]).tz_convert("Europe/Berlin")
        base = "Bookmakers" if lang == "en" else "Buchmacher"
        lab = f"{base}, {w[t.weekday()]} {t:%H:%M}"
        if n == len(snaps) - 1:
            lab += " (close)" if lang == "en" else " (Schluss)"
        rows.append((lab, s["consensus"][i], "market"))
    split = (res.get("understat") or {}).get("xgResultSplit")
    if split:
        rows.append((after_label, split[i], "after"))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("post", help="post folder, e.g. analysis/2026-27-md6-hamburg-stuttgart")
    ap.add_argument("--score", nargs=2, type=int, required=True, metavar=("HOME", "AWAY"))
    ap.add_argument("--odds", help="odds data folder (private data repository, odds/)")
    ap.add_argument("--understat", help="Understat folder (private data repository, understat/)")
    ap.add_argument("--frozen", nargs="*", default=[], help="frozen forecast.py outputs to grade alongside")
    ap.add_argument("--fig", type=int, required=True, help="chart number in the post")
    ap.add_argument("--labels", nargs=2, help="club names for the chart (default: published_forecast.json)")
    a = ap.parse_args(argv)

    pub = json.load(open(os.path.join(a.post, "published_forecast.json"), encoding="utf-8"))
    slug = os.path.basename(os.path.normpath(a.post))
    posts = json.load(open(os.path.join(ROOT, "analysis", "posts.json"), encoding="utf-8"))["posts"]
    post = next(p for p in posts if p["slug"] == slug)
    f = post["forecast"]
    assert np.allclose(f["model"], pub["models"]["ensemble"]) and np.allclose(f["market"], pub["market"]), \
        "published_forecast.json and posts.json disagree"
    kickoff = pd.Timestamp(post["kickoff"])
    hg, ag = a.score
    y = outcome_of(hg, ag)
    res = dict(slug=slug, score=[hg, ag], outcome=["home", "draw", "away"][y])

    # RPS of every published forecaster
    res["rps"] = {k: round(rps(p, y), 4) for k, p in pub["models"].items()}
    res["rps"]["market"] = round(rps(pub["market"], y), 4)
    frozen = [json.load(open(path, encoding="utf-8")) for path in a.frozen]
    for fz in frozen:
        fx = fz["fixtures"][0]
        for k, m in fx["models"].items():
            res["rps"][f"frozen_{'xg' if fz['xg'] else 'pre_xg'}_{k}"] = round(rps([m["H"], m["D"], m["A"]], y), 4)

    # Exact score in the published grid
    ranked = ranked_scores(pub["gridPercent"])
    pos = [n for n, c in enumerate(ranked, 1) if (c[0], c[1]) == (hg, ag)]
    res["exactScore"] = dict(rank=pos[0], percent=ranked[pos[0] - 1][2]) if pos else dict(rank=None, percent="<0.5")

    # Side markets
    sm = pub["sideMarkets"]
    res["sideMarkets"] = dict(over25=dict(p=sm["over25"], hit=hg + ag > 2), btts=dict(p=sm["btts"], hit=hg > 0 and ag > 0),
                              homeByTwo=dict(p=sm["homeByTwo"], hit=hg - ag >= 2), awayByTwo=dict(p=sm["awayByTwo"], hit=ag - hg >= 2),
                              oneGoalGame=dict(p=sm["oneGoalGame"], hit=abs(hg - ag) == 1))

    # Odds over time, paper bet and CLV
    snaps = snapshots_for(a.odds, pub["home"], pub["away"], kickoff) if a.odds else []
    res["odds"] = dict(published=dict(odds=pub["marketOdds"], fair=[round(v, 4) for v in fair(pub["marketOdds"])],
                                      source=pub["marketSource"]),
                       snapshots=snaps)
    close = snaps[-1] if snaps else None
    bets = []
    for i, gap in enumerate(np.subtract(f["model"], f["market"])):
        if gap < THRESHOLD - 1e-9:
            continue
        odds = f["marketOdds"][i]
        b = dict(pick=["home", "draw", "away"][i], odds=odds, model=f["model"][i], market=f["market"][i], gap=round(gap, 4),
                 won=y == i, profit=round(odds - 1, 2) if y == i else -1.0)
        if close:
            b["clv_consensus"] = round(odds * close["consensus"][i] - 1, 4)
            if "pinnacle" in close:
                b["clv_pinnacle"] = round(odds * fair(close["pinnacle"])[i] - 1, 4)
            b["closing_consensus"] = close["consensus"][i]
            b["closing_snapshot"] = close["taken_at"]
        bets.append(b)
    res["paperBets"] = bets

    if a.understat:
        res["understat"] = match_xg(a.understat, pub["home"], pub["away"], kickoff)

    labels = a.labels or [pub["home"], pub["away"]]
    for lang, sub in (("en", ""), ("de", "de")):
        chart(ranked, (hg, ag), labels, lang, os.path.join(a.post, "figs", sub, f"fig{a.fig}_fulltime.svg"))
    if bets:   # how everyone rated the outcome that was bet on, against the bet's break-even
        b = bets[0]
        colour = {"home": BLUE, "away": ORANGE}.get(b["pick"], MUTED)
        for lang, sub in (("en", ""), ("de", "de")):
            rows = views_rows(res, frozen, lang, b["pick"],
                              "My models (Thu, published)" if lang == "en" else "Meine Modelle (Do., veröffentlicht)",
                              "The chances, in hindsight (Understat xG)" if lang == "en" else "Die Chancen im Nachhinein (Understat-xG)")
            views_chart(rows, 1 / b["odds"], b["odds"], lang, os.path.join(a.post, "figs", sub, f"fig{a.fig + 1}_views.svg"), colour)
    out = os.path.join(a.post, "fulltime.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    print("->", out)


if __name__ == "__main__":
    main()
