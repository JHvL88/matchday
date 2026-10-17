"""Charts and numbers for the Bayern v Leipzig post, in English and German.

    python analysis/2026-27-md6-bayern-leipzig/post_charts.py matches.csv <backtest-results>/xg <post-model-out> <post-folder> <source-data>

Inputs: the match table (build_matches.py --understat), the published models' walk-forward predictions
(backtest-results branch, xg/), post_model.py's output (forecast.json, internals.pkl) and market.json.
Writes <post-folder>/figs/*.svg (English), figs/de/*.svg (German, drawn from the same numbers) and
numbers.json, which holds every figure the article quotes.
"""
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from bl_models import rps
from evaluate import cols, load

MATCHES, RESULTS, MODEL_OUT, POST, SOURCE = sys.argv[1:6]
HOME, AWAY, SEASON = "Bayern Munich", "RB Leipzig", 2026

# ----------------------------------------------------------------------------- style (as in the earlier posts)
FONT = os.path.expanduser("~/.cache/jans-matchday/DMSans.ttf")
if not os.path.exists(FONT):
    import urllib.request
    os.makedirs(os.path.dirname(FONT), exist_ok=True)
    urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz,wght%5D.ttf", FONT)
font_manager.fontManager.addfont(FONT)
INK, MUTED, GRID, SURF = "#16161c", "#5f5f69", "#e6e6ea", "#ffffff"
HC, AC, DRAW, NEUTRAL = "#2f6fdb", "#c25a00", "#9a9aa4", "#bdbdc5"
MODEL_C = "#c25a00"                      # "what the models said" (same encoding as matchday 6)
BLUE_RAMP = ["#f6f9fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({
    "font.family": font_manager.FontProperties(fname=FONT).get_name(),
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "font.size": 10.5, "axes.titlesize": 11, "svg.fonttype": "path",
    "axes.titlelocation": "left", "axes.titleweight": "normal", "axes.titlecolor": INK,
    "svg.hashsalt": "md6-bayern-leipzig",
})
SHORT = {"Bayern Munich": "Bayern", "Ein Frankfurt": "Frankfurt", "M'gladbach": "Gladbach", "Werder Bremen": "Bremen",
         "Union Berlin": "Union", "RB Leipzig": "Leipzig", "FC Koln": "Köln", "Schalke 04": "Schalke"}

T = {
    "en": dict(
        bookies="Bookmakers", ens="Ensemble", dc="Dixon–Coles", bay="Bayesian", xgb="XGBoost",
        hwin="Bayern win", draw="Draw", awin="Leipzig win",
        hgoals="Bayern goals", agoals="Leipzig goals",
        total_x="Total goals in the match", total_title="How many goals? Ensemble forecast",
        line="Bookmakers’ line: 4.5", over_lab="Over 4.5: models {m} · bookmakers {b}",
        xg_for="xG for", xg_against="xG against", goals="goals",
        season_t="{team}: expected goals in each league match so far", home="H", away="A",
        att="Shots on target created (× average)  →  better", dfn="Shots on target conceded (× average)  ↑ fewer",
        h2h_y="Bayern’s chance of winning, bookmakers’ average", h2h_today="Today",
        h2h_models="models", h2h_market="bookmakers",
        win="Bayern won", drew="Draw", lost="Leipzig won",
        fav_x="Chance the bookmakers’ favourite wins",
        fav_rows=["Favourite at 50–60%", "Favourite at 60–70%", "Favourite at 70–80%", "Favourite at 80%+", "Bayern at home"],
        n="{n} matches", n_this="{n} matches  ← this match",
        models_said="Models said", bookies_said="Bookmakers said", happened="Actually happened",
        what_moves="What moves {team}’s expected goals",
        tot_x="Goals per match", tot_rows=["All matches", "Models expect 3.6+", "Bookmakers expect goals", "Bayern, all", "Bayern at home"],
        tot_models="Models expected", tot_actual="Actually scored",
    ),
    "de": dict(
        bookies="Buchmacher", ens="Ensemble", dc="Dixon–Coles", bay="Bayes-Modell", xgb="XGBoost",
        hwin="Sieg Bayern", draw="Remis", awin="Sieg Leipzig",
        hgoals="Tore Bayern", agoals="Tore Leipzig",
        total_x="Tore im Spiel insgesamt", total_title="Wie viele Tore? Prognose des Ensembles",
        line="Linie der Buchmacher: 4,5", over_lab="Über 4,5: Modelle {m} · Buchmacher {b}",
        xg_for="xG für", xg_against="xG gegen", goals="Tore",
        season_t="{team}: erwartete Tore in jedem Ligaspiel bisher", home="H", away="A",
        att="Erzeugte Schüsse aufs Tor (× Schnitt)  →  besser", dfn="Zugelassene Schüsse aufs Tor (× Schnitt)  ↑ weniger",
        h2h_y="Bayerns Siegchance, Schnitt der Buchmacher", h2h_today="Heute",
        h2h_models="Modelle", h2h_market="Buchmacher",
        win="Bayern gewann", drew="Remis", lost="Leipzig gewann",
        fav_x="Siegchance des Buchmacher-Favoriten",
        fav_rows=["Favorit bei 50–60 %", "Favorit bei 60–70 %", "Favorit bei 70–80 %", "Favorit ab 80 %", "Bayern zu Hause"],
        n="{n} Spiele", n_this="{n} Spiele  ← dieses Spiel",
        models_said="Modelle sagten", bookies_said="Buchmacher sagten", happened="Tatsächlich eingetreten",
        what_moves="Was {team}s erwartete Tore bewegt",
        tot_x="Tore pro Spiel", tot_rows=["Alle Spiele", "Modelle erwarten 3,6+", "Buchmacher erwarten Tore", "Bayern, alle", "Bayern zu Hause"],
        tot_models="Modelle erwarteten", tot_actual="Tatsächlich gefallen",
    ),
}
FEAT = {
    "en": {"elo_h_own": "Bayern Elo", "elo_a_own": "Leipzig Elo", "elo_diff": "Elo gap",
           "h_gf_ewm": "Bayern goals scored (form)", "h_ga_ewm": "Bayern goals conceded (form)",
           "a_gf_ewm": "Leipzig goals scored (form)", "a_ga_ewm": "Leipzig goals conceded (form)",
           "h_tf_ewm": "Bayern shots on target (form)", "h_ta_ewm": "Bayern shots on target faced",
           "a_tf_ewm": "Leipzig shots on target (form)", "a_ta_ewm": "Leipzig shots on target faced",
           "h_sf_ewm": "Bayern shots (form)", "h_sa_ewm": "Bayern shots faced",
           "a_sf_ewm": "Leipzig shots (form)", "a_sa_ewm": "Leipzig shots faced",
           "h_xf_ewm": "Bayern xG (form)", "h_xa_ewm": "Bayern xG against (form)",
           "a_xf_ewm": "Leipzig xG (form)", "a_xa_ewm": "Leipzig xG against (form)",
           "d_xf": "xG gap", "d_xa": "xG-against gap",
           "d_gf": "Goals-scored gap", "d_ga": "Goals-conceded gap", "d_tf": "Shots-on-target gap",
           "d_ta": "Shots-on-target-faced gap", "h_conv": "Bayern finishing rate", "a_conv": "Leipzig finishing rate",
           "h_keep": "Bayern goals per shot on target faced", "a_keep": "Leipzig goals per shot on target faced",
           "h_pts_last5": "Bayern points, last 5", "a_pts_last5": "Leipzig points, last 5",
           "h_rest_days": "Bayern rest days", "a_rest_days": "Leipzig rest days",
           "h_promoted": "Bayern promoted", "a_promoted": "Leipzig promoted", "ghost": "Empty stadium"},
    "de": {"elo_h_own": "Bayern: Elo", "elo_a_own": "Leipzig: Elo", "elo_diff": "Elo-Differenz",
           "h_gf_ewm": "Bayern: erzielte Tore (Form)", "h_ga_ewm": "Bayern: Gegentore (Form)",
           "a_gf_ewm": "Leipzig: erzielte Tore (Form)", "a_ga_ewm": "Leipzig: Gegentore (Form)",
           "h_tf_ewm": "Bayern: Schüsse aufs Tor (Form)", "h_ta_ewm": "Bayern: zugelassene Schüsse aufs Tor",
           "a_tf_ewm": "Leipzig: Schüsse aufs Tor (Form)", "a_ta_ewm": "Leipzig: zugelassene Schüsse aufs Tor",
           "h_sf_ewm": "Bayern: Schüsse (Form)", "h_sa_ewm": "Bayern: zugelassene Schüsse",
           "a_sf_ewm": "Leipzig: Schüsse (Form)", "a_sa_ewm": "Leipzig: zugelassene Schüsse",
           "h_xf_ewm": "Bayern: xG (Form)", "h_xa_ewm": "Bayern: xG gegen (Form)",
           "a_xf_ewm": "Leipzig: xG (Form)", "a_xa_ewm": "Leipzig: xG gegen (Form)",
           "d_xf": "xG-Differenz", "d_xa": "Differenz xG gegen",
           "d_gf": "Differenz erzielte Tore", "d_ga": "Differenz Gegentore", "d_tf": "Differenz Schüsse aufs Tor",
           "d_ta": "Differenz zugelassene Schüsse aufs Tor", "h_conv": "Bayern: Chancenverwertung",
           "a_conv": "Leipzig: Chancenverwertung", "h_keep": "Bayern: Gegentore pro Schuss aufs Tor",
           "a_keep": "Leipzig: Gegentore pro Schuss aufs Tor", "h_pts_last5": "Bayern: Punkte, letzte 5",
           "a_pts_last5": "Leipzig: Punkte, letzte 5", "h_rest_days": "Bayern: Ruhetage",
           "a_rest_days": "Leipzig: Ruhetage", "h_promoted": "Bayern: Aufsteiger", "a_promoted": "Leipzig: Aufsteiger",
           "ghost": "Geisterspiel"},
}


def pct(v, lang, d=0):
    s = f"{v * 100:.{d}f}"
    return (s.replace(".", ",") + " %") if lang == "de" else s + "%"


def count(n, lang):
    return f"{n:,}".replace(",", "." if lang == "de" else ",")


def num(v, lang, d=2):
    s = f"{v:.{d}f}"
    return s.replace(".", ",") if lang == "de" else s


def save(fig, name, lang):
    d = os.path.join(POST, "figs") if lang == "en" else os.path.join(POST, "figs", "de")
    os.makedirs(d, exist_ok=True)
    fig.savefig(os.path.join(d, f"{name}.svg"), bbox_inches="tight", pad_inches=0.15,
                metadata={"Date": None})
    plt.close(fig)


# ----------------------------------------------------------------------------- inputs
fc = json.load(open(os.path.join(MODEL_OUT, "forecast.json")))
rec = fc["fixtures"][0]
I = pickle.load(open(os.path.join(MODEL_OUT, "internals.pkl"), "rb"))
mk = json.load(open(os.path.join(POST, "market.json")))
G = I["grids"]
M = G["ens"]
g = np.arange(M.shape[0])
tot = np.add.outer(g, g)
diff = np.subtract.outer(g, g)
mkt = np.array(mk["x12"]["consensus"])
over45_mkt = next(t["over"] for t in mk["totals"] if t["point"] == 4.5)
m = pd.read_csv(MATCHES, parse_dates=["date"])
d1 = m[m["div"] == "D1"]

N = dict(forecast={k: {kk: vv for kk, vv in v.items()} for k, v in rec["models"].items()},
         market=dict(x12=mkt.tolist(), over45=over45_mkt, taken_at=mk["taken_at"],
                     reader_best=mk["x12"]["reader_best"], average_odds=mk["x12"]["average_odds"],
                     margin=mk["x12"]["margin"], books=mk["x12"]["books"], totals=mk["totals"]),
         config=fc["config"], inputs=fc["inputs"])
N["scores"] = dict(
    over15=float(M[tot > 1.5].sum()), over25=float(M[tot > 2.5].sum()), over35=float(M[tot > 3.5].sum()),
    over45=float(M[tot > 4.5].sum()), over55=float(M[tot > 5.5].sum()), exp_total=float((M * tot).sum()),
    btts=float(M[1:, 1:].sum()), bayern_clean=float(M[:, 0].sum()), leipzig_clean=float(M[0, :].sum()),
    h_by2=float(M[diff >= 2].sum()), h_by3=float(M[diff >= 3].sum()), one_goal=float(M[np.abs(diff) == 1].sum()),
    top=[(f"{i}-{j}", float(M[i, j])) for i, j in zip(*np.unravel_index(np.argsort(M, axis=None)[::-1][:10], M.shape))],
    by_model_over45={k: float(G[k][tot > 4.5].sum()) for k in ["dc", "bay", "xgb"]},
)
N["fair_odds"] = (1 / np.array([rec["models"]["ens"][k] for k in "HDA"])).round(2).tolist()

# ----------------------------------------------------------------------------- backtest frame
o = load(MATCHES, RESULTS).dropna(subset=cols("bay"))
o = o[o["div"] == "D1"].copy()
fav_home = o.avgc_H >= o.avgc_A
o["p_mkt"] = np.where(fav_home, o.avgc_H, o.avgc_A)
o["p_ens"] = np.where(fav_home, o.ens_H, o.ens_A)
o["won"] = np.where(fav_home, o.y == 0, o.y == 2)
o["fav"] = np.where(fav_home, o.home, o.away)
FAV_BUCKETS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]
fav_rows = []
for lo, hi in FAV_BUCKETS:
    k = (o.p_mkt >= lo) & (o.p_mkt < hi)
    fav_rows.append(dict(n=int(k.sum()), models=float(o.p_ens[k].mean()), market=float(o.p_mkt[k].mean()),
                         actual=float(o.won[k].mean())))
bh = o[o.home == HOME]
fav_rows.append(dict(n=int(len(bh)), models=float(bh.ens_H.mean()), market=float(bh.avgc_H.mean()),
                     actual=float((bh.y == 0).mean())))
N["favourites"] = fav_rows
k = (o.p_mkt >= 0.7) & (o.p_ens - o.p_mkt <= -0.05)
N["fav_doubted"] = dict(n=int(k.sum()), models=float(o.p_ens[k].mean()), market=float(o.p_mkt[k].mean()),
                        actual=float(o.won[k].mean()))
k = o.p_mkt >= 0.7
N["fav70_rps"] = dict(n=int(k.sum()), ens=float(rps(o[k][cols("ens")].values, o[k].y.values).mean()),
                      market=float(rps(o[k][cols("avgc")].values, o[k].y.values).mean()))
N["backtest"] = dict(n=int(len(o)), seasons=[int(o.season.min()), int(o.season.max())],
                     rps={mm: float(rps(o[cols(mm)].values, o.y.values).mean()) for mm in ["avgc", "ens", "dc", "bay", "xgb"]})
cur = o[o.season == SEASON]
N["backtest"]["current"] = dict(n=int(len(cur)), ens=float(rps(cur[cols("ens")].values, cur.y.values).mean()),
                                market=float(rps(cur[cols("avgc")].values, cur.y.values).mean()))

# goals: the models' expected total (average of the three) against what happened. The bookmakers' closing
# over/under 2.5 price is read back from the football-data.co.uk files through each row's src_file/src_row.
o["tot"] = o.hg + o.ag
o["ens_tot"] = ((o.dc_lh + o.dc_la) + (o.bay_lh + o.bay_la) + (o.xgb_lh + o.xgb_la)) / 3
ou = []
for f, grp in o.groupby("src_file"):
    raw = pd.read_csv(os.path.join(SOURCE, f), encoding="utf-8-sig")
    r = raw.iloc[grp.src_row.values - 2]
    ou.append(pd.DataFrame({"over": 1 / r["AvgC>2.5"].values, "under": 1 / r["AvgC<2.5"].values}, index=grp.index))
ou = pd.concat(ou)
o["mkt_o25"] = ou.over / (ou.over + ou.under)
tot_rows = []
bayern = (o.home == HOME) | (o.away == HOME)
for kk in [o.index == o.index, o.ens_tot >= 3.6, o.mkt_o25 >= 0.7, bayern, o.home == HOME]:
    gg = o[kk]
    tot_rows.append(dict(n=int(len(gg)), models=float(gg.ens_tot.mean()), actual=float(gg.tot.mean()),
                         over25_market=float(gg.mkt_o25.mean()), over25_actual=float((gg.tot > 2.5).mean())))
N["totals_check"] = tot_rows

# ----------------------------------------------------------------------------- this season, both clubs
season = d1[d1.season == SEASON].sort_values("date")
form = {}
for team in [HOME, AWAY]:
    rows = []
    for r in season[(season.home == team) | (season.away == team)].itertuples():
        h = r.home == team
        rows.append(dict(date=r.date.strftime("%Y-%m-%d"), opp=SHORT.get(r.away if h else r.home, r.away if h else r.home),
                         venue="H" if h else "A", gf=int(r.hg if h else r.ag), ga=int(r.ag if h else r.hg),
                         xgf=float(r.hxg if h else r.axg), xga=float(r.axg if h else r.hxg),
                         sotf=int(r.hst if h else r.ast), sota=int(r.ast if h else r.hst)))
    f = pd.DataFrame(rows)
    pts = int(((f.gf > f.ga) * 3 + (f.gf == f.ga)).sum())
    form[team] = dict(matches=rows, pts=pts, gf=int(f.gf.sum()), ga=int(f.ga.sum()), xgf=float(f.xgf.sum()),
                      xga=float(f.xga.sum()), home_gf=int(f[f.venue == "H"].gf.sum()), home_ga=int(f[f.venue == "H"].ga.sum()),
                      away_gf=int(f[f.venue == "A"].gf.sum()), away_ga=int(f[f.venue == "A"].ga.sum()),
                      home_xgf=float(f[f.venue == "H"].xgf.sum()), home_xga=float(f[f.venue == "H"].xga.sum()),
                      away_xgf=float(f[f.venue == "A"].xgf.sum()), away_xga=float(f[f.venue == "A"].xga.sum()),
                      sotf=int(f.sotf.sum()), sota=int(f.sota.sum()), avg_total=float((f.gf + f.ga).mean()))
N["form"] = form


def table(after):
    rows = {}
    for r in season.itertuples():
        for t, gf, ga in [(r.home, r.hg, r.ag), (r.away, r.ag, r.hg)]:
            e = rows.setdefault(t, [0, 0, 0])
            e[0] += 3 * (gf > ga) + (gf == ga)
            e[1] += gf - ga
            e[2] += gf
    return sorted(rows, key=lambda t: (-rows[t][0], -rows[t][1], -rows[t][2], t)), rows


order, rows = table(None)
N["table"] = {t: dict(pos=order.index(t) + 1, pts=rows[t][0], gd=rows[t][1]) for t in order}
for team in [HOME, AWAY]:
    f = pd.DataFrame(form[team]["matches"])
    form[team].update(w=int((f.gf > f.ga).sum()), d=int((f.gf == f.ga).sum()), l=int((f.gf < f.ga).sum()))
last = {}
for r in d1[d1.season == SEASON - 1].itertuples():
    for t, gf, ga in [(r.home, r.hg, r.ag), (r.away, r.ag, r.hg)]:
        e = last.setdefault(t, [0, 0, 0])
        e[0] += 3 * (gf > ga) + (gf == ga)
        e[1] += gf - ga
        e[2] += gf
last_order = sorted(last, key=lambda t: (-last[t][0], -last[t][1], -last[t][2], t))
N["last_season"] = {t: dict(pos=last_order.index(t) + 1, pts=last[t][0], gf=last[t][2]) for t in [HOME, AWAY]}

# ----------------------------------------------------------------------------- head-to-head in Munich
h2h = d1[(d1.home == HOME) & (d1.away == AWAY)].sort_values("date")
hh = []
for r in h2h.itertuples():
    odds = (r.avgc_h, r.avgc_d, r.avgc_a) if pd.notna(r.avgc_h) else (r.avg_h, r.avg_d, r.avg_a)
    inv = 1 / np.array(odds, float)
    hh.append(dict(date=r.date.strftime("%Y-%m-%d"), score=[int(r.hg), int(r.ag)], p_bayern=float(inv[0] / inv.sum()),
                   closing=bool(pd.notna(r.avgc_h)), xg=[float(r.hxg), float(r.axg)]))
both_ways = d1[((d1.home == HOME) & (d1.away == AWAY)) | ((d1.home == AWAY) & (d1.away == HOME))]
bw = both_ways.assign(b=np.where(both_ways.home == HOME, both_ways.hg, both_ways.ag),
                      l=np.where(both_ways.home == HOME, both_ways.ag, both_ways.hg))
N["h2h"] = dict(munich=hh, all=dict(n=int(len(bw)), w=int((bw.b > bw.l).sum()), d=int((bw.b == bw.l).sum()),
                                    l=int((bw.b < bw.l).sum()), gf=int(bw.b.sum()), ga=int(bw.l.sum())))

# ----------------------------------------------------------------------------- Bayesian strengths
import bayes_model as bm
bm.PERIODS_PER_SEASON = 2
B = I["bayes"]
ST, META = B["states"], B["meta"]
tid = META["tid"]
d1_sets = {s_: [tid[t] for t in set(g_.home) if t in tid] for s_, g_ in d1.groupby("season")}


def vs_d1_average(arr):
    out = arr.copy()
    for p_ in range(arr.shape[2]):
        ids = d1_sets.get(META["first_season"] + p_ // 2)
        if ids:
            out[:, :, p_] = arr[:, :, p_] - arr[:, ids, p_].mean(axis=1, keepdims=True)
    return out


ATT, DEF = vs_d1_average(ST["att"]), vs_d1_average(ST["def_"])
P_now = (SEASON - META["first_season"]) * 2 + int(bm.period_of(10))
cur_teams = sorted(set(season.home))
att_now = np.exp(ATT[:, [tid[t] for t in cur_teams], P_now]).mean(0)     # shots on target created, x average
conc_now = np.exp(-DEF[:, [tid[t] for t in cur_teams], P_now]).mean(0)   # shots on target conceded, x average (<1 = fewer)
N["strength"] = {t: dict(att=float(a), conc=float(c)) for t, a, c in zip(cur_teams, att_now, conc_now)}
N["strength_rank"] = dict(att=[t for _, t in sorted(zip(-att_now, cur_teams))], conc=[t for _, t in sorted(zip(conc_now, cur_teams))])
N["bayes_shots"] = rec["bayesShots"]
N["bayes_fit"] = dict(first_season=int(META["first_season"]), clubs=int(META["T"]),
                      matches=int(((m.season >= META["first_season"]) & (m.date < pd.Timestamp(fc["freeze"]))).sum()))

# XGBoost drivers
X = I["xgb"]
N["xgb_drivers"] = {}
for key, tgt in [("home", "hg"), ("away", "ag")]:
    c = np.asarray(X["shap"][tgt][:-1])
    top = np.argsort(np.abs(c))[::-1][:6]
    N["xgb_drivers"][key] = [(X["features"][t], float(np.exp(c[t])), float(X["row"][X["features"][t]])) for t in top]

since = d1[(d1.season >= 2019) & d1.hxg.notna() & (d1.date < pd.Timestamp(fc["freeze"]))]
for team, tag in [(HOME, "bayern"), (AWAY, "leipzig")]:
    h, a = since[since.home == team], since[since.away == team]
    N[f"{tag}_goals_vs_xg"] = dict(n=int(len(h) + len(a)), goals=int(h.hg.sum() + a.ag.sum()),
                                   xg=float(h.hxg.sum() + a.axg.sum()))
own = []
for lo, hi in [(0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]:
    k = (o.p_ens >= lo) & (o.p_ens < hi)
    own.append(dict(lo=lo, n=int(k.sum()), models=float(o.p_ens[k].mean()), market=float(o.p_mkt[k].mean()),
                    actual=float(o.won[k].mean())))
N["by_model_buckets"] = own
xg_tab = {}
for r in season.itertuples():
    for t, xf, xa in [(r.home, r.hxg, r.axg), (r.away, r.axg, r.hxg)]:
        e = xg_tab.setdefault(t, [0.0, 0.0])
        e[0] += xf
        e[1] += xa
N["xg_rank"] = dict(xgf=sorted(xg_tab, key=lambda t: -xg_tab[t][0]), xga=sorted(xg_tab, key=lambda t: xg_tab[t][1]))
json.dump(N, open(os.path.join(POST, "numbers.json"), "w"), indent=1, default=float)


# ============================================================================= charts
def chart_forecast(L):
    t = T[L]
    fig, ax = plt.subplots(figsize=(8.2, 3.3))
    rows = [("bookies", mkt), ("ens", None), ("xgb", None), ("bay", None), ("dc", None)]
    for k_, (key, vals) in enumerate(rows):
        p = vals if vals is not None else [rec["models"][key][c] for c in "HDA"]
        left = 0
        for w, col in zip(p, [HC, DRAW, AC]):
            ax.barh(k_, w, left=left, color=col, height=0.74 if key == "ens" else 0.62, edgecolor=SURF, linewidth=2)
            if w > 0.06:
                ax.text(left + w / 2, k_, pct(w, L), ha="center", va="center", color=INK if col == DRAW else "white", fontsize=10)
            left += w
    ax.set_yticks(range(len(rows)), [t[r[0]] for r in rows])
    for lab in ax.get_yticklabels():
        if lab.get_text() == t["ens"]:
            lab.set_fontsize(11.5)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(left=False)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (HC, DRAW, AC)]
    ax.legend(hs, [t["hwin"], t["draw"], t["awin"]], ncol=3, frameon=False, loc="lower left",
              bbox_to_anchor=(0, 1.0), fontsize=9.5, handlelength=1.0, handleheight=1.0, borderaxespad=0.2)
    save(fig, "fig1_forecast", L)


def chart_scorelines(L):
    t = T[L]
    big = np.argwhere(M >= 0.005)
    KH, KA = int(big[:, 0].max()) + 1, int(big[:, 1].max()) + 1
    H = M[:KH, :KA]
    fig, ax = plt.subplots(figsize=(1.0 * KA + 1.2, 0.62 * KH + 0.9))
    vmax = H.max()
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    ax.imshow(H, cmap=cmap, vmin=0, vmax=vmax, origin="lower", aspect="auto")
    for i in range(KH):
        for j in range(KA):
            v = H[i, j]
            ax.text(j, i, pct(v, L, 1) if v >= 0.005 else "", ha="center", va="center", fontsize=10.5,
                    color="white" if v > 0.55 * vmax else INK)
    mi, mj = np.unravel_index(H.argmax(), H.shape)
    ax.add_patch(plt.Rectangle((mj - 0.5, mi - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=1.8))
    ax.set_xticks(range(KA), [str(k_) for k_ in range(KA)])
    ax.set_yticks(range(KH), [str(k_) for k_ in range(KH)])
    ax.set_xlabel(t["agoals"])
    ax.set_ylabel(t["hgoals"])
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(length=0, labelsize=11)
    save(fig, "fig2_scorelines", L)
    return KH, KA


def chart_totals(L):
    t = T[L]
    tg = np.array([M[tot == k_].sum() for k_ in range(9)] + [M[tot >= 9].sum()])
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    colors = [NEUTRAL if k_ <= 4 else HC for k_ in range(10)]
    ax.bar(range(10), tg, color=colors, width=0.74, edgecolor=SURF, linewidth=2)
    for k_, v in enumerate(tg):
        ax.text(k_, v + 0.004, pct(v, L), ha="center", va="bottom", fontsize=9.5, color=INK)
    ax.axvline(4.5, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
    top = tg.max() * 1.32
    ax.text(4.62, top * 0.97, t["line"], ha="left", va="top", fontsize=9.5, color=INK)
    ax.text(4.62, top * 0.86, t["over_lab"].format(m=pct(N["scores"]["over45"], L), b=pct(over45_mkt, L)),
            ha="left", va="top", fontsize=9.5, color=MUTED)
    ax.set_ylim(0, top)
    ax.set_xticks(range(10), [str(k_) for k_ in range(9)] + ["9+"])
    ax.set_xlabel(t["total_x"])
    ax.set_yticks([])
    ax.spines[["left"]].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(t["total_title"], fontsize=10.5)
    save(fig, "fig3_totals", L)


def chart_season(L):
    t = T[L]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6), sharey=True)
    ymax = max(max(r["xgf"], r["xga"]) for tm in form for r in form[tm]["matches"]) * 1.32
    for ax, team, col in [(axes[0], HOME, HC), (axes[1], AWAY, AC)]:
        rows = form[team]["matches"]
        x = np.arange(len(rows))
        ax.bar(x - 0.19, [r["xgf"] for r in rows], width=0.36, color=col, edgecolor=SURF, linewidth=1.5)
        ax.bar(x + 0.19, [r["xga"] for r in rows], width=0.36, color=NEUTRAL, edgecolor=SURF, linewidth=1.5)
        for xi, r in zip(x, rows):
            ax.text(xi - 0.19, r["xgf"] + 0.06, num(r["xgf"], L, 1), ha="center", va="bottom", fontsize=8.5, color=INK)
            ax.text(xi + 0.19, r["xga"] + 0.06, num(r["xga"], L, 1), ha="center", va="bottom", fontsize=8.5, color=MUTED)
        score = [f"{r['gf']}:{r['ga']}" if L == "de" else f"{r['gf']}–{r['ga']}" for r in rows]
        ax.set_xticks(x, [f"{r['opp']}\n{t['home'] if r['venue'] == 'H' else t['away']} · {s}" for r, s in zip(rows, score)],
                      fontsize=8.8)
        ax.set_title(SHORT[team], fontsize=11, color=INK)
        ax.set_ylim(0, ymax)
        ax.set_yticks([])
        ax.spines[["left"]].set_visible(False)
        ax.tick_params(length=0)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (HC, AC, NEUTRAL)]
    fig.tight_layout(w_pad=2.5, rect=(0, 0, 1, 0.9))
    fig.legend(hs, [f"{t['xg_for']} (Bayern)", f"{t['xg_for']} (Leipzig)", t["xg_against"]], frameon=False, ncol=3,
               loc="upper left", bbox_to_anchor=(0.01, 1.0), fontsize=9.5, handlelength=1.0, handleheight=1.0)
    save(fig, "fig4_season", L)


def chart_league_map(L):
    t = T[L]
    att, dfn = att_now, conc_now
    MANUAL = {"Elversberg": (-8, 9), "Schalke 04": (-9, 0), "Paderborn": (-9, 0), "Union Berlin": (-26, -24),
              "Hamburg": (22, -22), "Werder Bremen": (9, 0), "Mainz": (6, 9), "Hoffenheim": (8, -9)}
    fig, ax = plt.subplots(figsize=(8.4, 6.6))
    order_ = sorted(range(len(cur_teams)), key=lambda i: (cur_teams[i] not in (HOME, AWAY), cur_teams[i] not in MANUAL, -att[i]))
    for tm, x, y in zip(cur_teams, att, dfn):
        col = AC if tm == AWAY else HC if tm == HOME else NEUTRAL
        ax.scatter(x, y, s=70 if col != NEUTRAL else 44, color=col, edgecolor=SURF, linewidth=2, zorder=3)
    ax.set_xlim(min(att) - 0.19, max(att) + 0.12)
    ax.set_ylim(max(dfn) + 0.06, min(dfn) - 0.08)                 # flipped: up = fewer conceded
    fig.canvas.draw()
    pts = ax.transData.transform(np.column_stack([att, dfn]))
    renderer = fig.canvas.get_renderer()
    placed = []
    near = [(8, 0), (-8, 0), (0, 9), (0, -9), (8, 8), (8, -8), (-8, 8), (-8, -8)]
    far = [(r * np.cos(a_), r * np.sin(a_)) for r in (24, 34, 46, 58)
           for a_ in np.radians([0, 180, 30, -30, 150, -150, 60, -60, 120, -120, 90, -90])]

    def align(dx, dy):
        return ("left" if dx > 2 else "right" if dx < -2 else "center"), ("bottom" if dy > 2 else "top" if dy < -2 else "center")

    for i in order_:
        tm, hl = cur_teams[i], cur_teams[i] in (HOME, AWAY)
        style = dict(fontsize=10 if hl else 9, color=INK if hl else MUTED, fontweight="bold" if hl else "normal")
        chosen = None
        if tm in MANUAL:                                            # the crowded corner, placed by hand
            dx, dy = MANUAL[tm]
            ha, va = align(dx, dy)
            lead = np.hypot(dx, dy) > 15
            chosen = ax.annotate(SHORT.get(tm, tm), (att[i], dfn[i]), xytext=(dx, dy), textcoords="offset points",
                                 ha=ha, va=va, **style,
                                 arrowprops=dict(arrowstyle="-", color="#cfcfd6", lw=0.8, shrinkA=2, shrinkB=4) if lead else None)
            placed.append(chosen.get_window_extent(renderer).expanded(1.04, 1.1))
            continue
        cands = [(dx, dy, False) for dx, dy in near + far] + [(dx, dy, True) for dx, dy in far if np.hypot(dx, dy) > 40]
        for k_, (dx, dy, relaxed) in enumerate(cands):
            ha, va = align(dx, dy)
            lead = np.hypot(dx, dy) > 15
            txt = ax.annotate(SHORT.get(tm, tm), (att[i], dfn[i]), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                              arrowprops=dict(arrowstyle="-", color="#cfcfd6", lw=0.8, shrinkA=2, shrinkB=4) if lead else None,
                              **style)
            bb = txt.get_window_extent(renderer)
            pad = bb.expanded(1.08, 1.25)
            cx_, cy_ = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
            own = np.hypot(*(pts[i] - (cx_, cy_)))
            others = [np.hypot(px - cx_, py - cy_) for j, (px, py) in enumerate(pts) if j != i]
            ok = (not any(pad.contains(px, py) for j, (px, py) in enumerate(pts) if j != i)
                  and not any(pad.overlaps(o_) for o_ in placed)
                  and ax.bbox.contains(bb.x0, bb.y0) and ax.bbox.contains(bb.x1, bb.y1)
                  and (relaxed or own < 0.85 * min(others)))     # the label must sit nearest its own dot
            if ok:
                chosen = txt
                break
            txt.remove()
        if chosen is None:
            chosen = ax.annotate(SHORT.get(tm, tm), (att[i], dfn[i]), xytext=(8, 0), textcoords="offset points",
                                 ha="left", va="center", **style)
        placed.append(chosen.get_window_extent(renderer).expanded(1.04, 1.1))
    ax.axvline(1, color=GRID, zorder=0)
    ax.axhline(1, color=GRID, zorder=0)
    ax.set_xlabel(t["att"])
    ax.set_ylabel(t["dfn"])
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: num(v, L, 1) + "×")
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    save(fig, "fig5_league_map", L)


def chart_h2h(L):
    t = T[L]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    x = np.arange(len(hh) + 1)
    ps = [r["p_bayern"] for r in hh]
    ax.plot(x[:-1], ps, color=GRID, linewidth=1.6, zorder=1)
    for xi, r in zip(x, hh):
        s0, s1 = r["score"]
        col = HC if s0 > s1 else DRAW if s0 == s1 else AC
        ax.scatter(xi, r["p_bayern"], s=80, color=col, edgecolor=SURF, linewidth=2, zorder=3)
        lab = f"{s0}:{s1}" if L == "de" else f"{s0}–{s1}"
        ax.text(xi, r["p_bayern"] - 0.045, lab, ha="center", va="top", fontsize=9.5, color=INK)
    xt = x[-1]
    ax.scatter(xt, mkt[0], s=80, facecolor=SURF, edgecolor=MUTED, linewidth=2, zorder=3)
    ax.scatter(xt, rec["models"]["ens"]["H"], s=80, facecolor=SURF, edgecolor=MODEL_C, linewidth=2, zorder=3, marker="D")
    ax.text(xt + 0.22, mkt[0], f"{pct(mkt[0], L)} {t['h2h_market']}", va="center", fontsize=9, color=MUTED)
    ax.text(xt + 0.22, rec["models"]["ens"]["H"], f"{pct(rec['models']['ens']['H'], L)} {t['h2h_models']}",
            va="center", fontsize=9, color=MODEL_C)
    months = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
              "de": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."]}[L]
    labels = [f"{months[pd.Timestamp(r['date']).month - 1]}\n{pd.Timestamp(r['date']).year}" for r in hh] + [t["h2h_today"] + "\n2026"]
    ax.set_xticks(x, labels, fontsize=9)
    ax.set_xlim(-0.5, xt + 1.6)
    ax.set_ylim(0.3, 0.95)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: pct(v, L)))
    ax.set_ylabel(t["h2h_y"])
    ax.axhline(0.5, color=GRID, linewidth=0.8, zorder=0)
    hs = [plt.Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=c, markeredgecolor=SURF) for c in (HC, DRAW, AC)]
    ax.legend(hs, [t["win"], t["drew"], t["lost"]], ncol=3, frameon=False, loc="upper left", fontsize=9)
    save(fig, "fig6_h2h", L)


def chart_favourites(L):
    t = T[L]
    rows = N["favourites"]
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    ys = [0, 1, 2, 3, 4.35]
    for y, r in zip(ys, rows):
        vals = [r["models"], r["market"], r["actual"]]
        ax.plot([min(vals), max(vals)], [y, y], color=GRID, linewidth=2.2, zorder=1)
        ax.scatter(r["models"], y, s=80, color=MODEL_C, edgecolor=SURF, linewidth=2, zorder=3)
        ax.scatter(r["market"], y, s=80, color=MUTED, edgecolor=SURF, linewidth=2, zorder=3)
        ax.scatter(r["actual"], y, s=95, color=INK, edgecolor=SURF, linewidth=2, zorder=4, marker="D")
    ax.set_yticks(ys, t["fav_rows"])
    ax.invert_yaxis()
    ax.set_xlim(0.45, 0.97)
    for y, r, i in zip(ys, rows, range(5)):
        lab = t["n_this"] if i in (2, 4) else t["n"]
        ax.text(0.968, y, lab.format(n=count(r["n"], L)), ha="right", va="center", fontsize=9, color=MUTED)
    ax.axhline(3.68, color=GRID, linewidth=0.8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: pct(v, L)))
    ax.set_xlabel(t["fav_x"])
    ax.spines[["left"]].set_visible(False)
    ax.tick_params(left=False)
    hs = [plt.Line2D([], [], marker=mk_, linestyle="", markersize=8, markerfacecolor=c, markeredgecolor=SURF)
          for mk_, c in [("o", MODEL_C), ("o", MUTED), ("D", INK)]]
    ax.legend(hs, [t["models_said"], t["bookies_said"], t["happened"]], ncol=3, frameon=False, loc="lower left",
              bbox_to_anchor=(0, 1.0), fontsize=9.5)
    save(fig, "fig7_favourites", L)


def chart_totals_check(L):
    t = T[L]
    rows = N["totals_check"]
    fig, ax = plt.subplots(figsize=(8.0, 3.3))
    for y, r in enumerate(rows):
        ax.plot([r["models"], r["actual"]], [y, y], color=GRID, linewidth=2.2, zorder=1)
        ax.scatter(r["models"], y, s=80, color=MODEL_C, edgecolor=SURF, linewidth=2, zorder=3)
        ax.scatter(r["actual"], y, s=95, color=INK, edgecolor=SURF, linewidth=2, zorder=4, marker="D")
        ax.text(4.78, y, t["n"].format(n=count(r["n"], L)), ha="right", va="center", fontsize=9, color=MUTED)
    ax.set_yticks(range(len(rows)), t["tot_rows"])
    ax.invert_yaxis()
    ax.set_xlim(2.8, 4.8)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.2))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: num(v, L, 1)))
    ax.set_xlabel(t["tot_x"])
    ax.spines[["left"]].set_visible(False)
    ax.tick_params(left=False)
    hs = [plt.Line2D([], [], marker=mk_, linestyle="", markersize=8, markerfacecolor=c, markeredgecolor=SURF)
          for mk_, c in [("o", MODEL_C), ("D", INK)]]
    ax.legend(hs, [t["tot_models"], t["tot_actual"]], ncol=2, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0),
              fontsize=9.5)
    save(fig, "fig8_goals_check", L)


def chart_xgb(L):
    t = T[L]
    names = FEAT[L]
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 6.2))
    for ax, tgt, team, col in [(axes[0], "hg", "Bayern", HC), (axes[1], "ag", "Leipzig", AC)]:
        c = np.asarray(X["shap"][tgt][:-1])
        top = np.argsort(np.abs(c))[::-1][:6][::-1]
        v = c[top]
        ax.barh(range(len(top)), v, color=[col if x_ > 0 else NEUTRAL for x_ in v], height=0.6, edgecolor=SURF, linewidth=2)
        ax.set_yticks(range(len(top)), [names.get(X["features"][i], X["features"][i]) for i in top], fontsize=10.5)
        ax.axvline(0, color=MUTED, linewidth=0.8)
        ax.set_title(t["what_moves"].format(team=team), fontsize=11)
        lo_, hi_ = ax.get_xlim()
        lo_, hi_ = min(lo_, -0.002), max(hi_, 0.002)
        ax.set_xlim(lo_, hi_)
        ticks = [round(mm, 2) for mm in np.arange(0.60, 1.61, 0.10) if lo_ - 1e-9 <= np.log(round(mm, 2)) <= hi_ + 1e-9]
        ax.set_xticks(np.log(ticks), ["×" + num(mm, L, 1) for mm in ticks])
        ax.spines[["left"]].set_visible(False)
        ax.tick_params(left=False)
    plt.tight_layout()
    save(fig, "fig9_xgb_drivers", L)


for L in ["en", "de"]:
    chart_forecast(L)
    KH, KA = chart_scorelines(L)
    chart_totals(L)
    chart_season(L)
    chart_league_map(L)
    chart_h2h(L)
    chart_favourites(L)
    chart_totals_check(L)
    chart_xgb(L)
N["heatmap_shape"] = [KH, KA]
N["outside_heatmap_max"] = float(np.where(np.outer(g < KH, g < KA), 0, M).max())
json.dump(N, open(os.path.join(POST, "numbers.json"), "w"), indent=1, default=float)
print("charts and numbers.json written to", POST)
