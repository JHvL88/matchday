"""Fill the article's [[placeholders]] from numbers.json, so no figure in the post is typed by hand.

    python analysis/2026-27-md6-bayern-leipzig/post_fill.py analysis/2026-27-md6-bayern-leipzig

Reads article.template.html and numbers.json in the post folder and writes index.html, with every chart's
width and height filled in. The English copy gets 71% / 2.97 / 2–1, the German copy 71 % / 2,97 / 2:1.
Stops on an unknown or left-over placeholder.
"""
import json
import os
import re
import sys

POST = sys.argv[1]
N = json.load(open(os.path.join(POST, "numbers.json")))


def pct(v, L, d=0):
    s = f"{v * 100:.{d}f}"
    return s.replace(".", ",") + "\u00a0%" if L == "de" else s + "%"


def dec(v, L, d=2):
    s = f"{v:.{d}f}"
    return s.replace(".", ",") if L == "de" else s


def score(s, L):
    a, b = s.split("-") if isinstance(s, str) else s
    return f"{a}:{b}" if L == "de" else f"{a}–{b}"


def values(L):
    V = {}
    F, mk = N["forecast"], N["market"]
    for m in ["dc", "bay", "xgb", "ens"]:
        for k in "HDA":
            V[f"{m}_{k}"] = pct(F[m][k], L)
        V[f"{m}_lh"], V[f"{m}_la"] = dec(F[m]["lh"], L), dec(F[m]["la"], L)
    for k, v in zip("HDA", mk["x12"]):
        V[f"mkt_{k}"] = pct(v, L)
        V[f"mkt1_{k}"] = pct(v, L, 1)
    for k in "HDA":
        V[f"ens1_{k}"] = pct(F["ens"][k], L, 1)
    gaps = [F["ens"][k] - v for k, v in zip("HDA", mk["x12"])]
    V["gap_H"] = dec(-gaps[0] * 100, L, 1)          # how much less sure of Bayern the models are, in points
    V["gap_D"], V["gap_A"] = dec(gaps[1] * 100, L, 1), dec(gaps[2] * 100, L, 1)
    V["ens_total"] = dec(N["scores"]["exp_total"], L)
    V["mode"] = score(F["ens"]["mostLikely"]["score"], L)
    V["p_mode"] = pct(F["ens"]["mostLikely"]["p"], L, 1)
    top = N["scores"]["top"]
    for i in range(1, 8):
        V[f"top{i}"], V[f"p_top{i}"] = score(top[i - 1][0], L), pct(top[i - 1][1], L, 1)
    for k in ["over15", "over25", "over35", "over45", "over55", "btts", "bayern_clean", "leipzig_clean", "h_by2", "h_by3", "one_goal"]:
        V[k] = pct(N["scores"][k], L)
    V["under45"] = pct(1 - N["scores"]["over45"], L)
    for m in ["dc", "bay", "xgb"]:
        V[f"{m}_over45"] = pct(N["scores"]["by_model_over45"][m], L)
    V["mkt_over45"] = pct(mk["over45"], L)
    V["mkt_under45"] = pct(1 - mk["over45"], L)
    t45 = next(t for t in mk["totals"] if t["point"] == 4.5)
    V["best_over45"], V["best_under45"] = dec(t45["best_over"], L), dec(t45["best_under"], L)
    V["books_over45"] = str(t45["books"])
    V["fair_under45"] = dec(1 / (1 - N["scores"]["over45"]), L)
    for i, k in enumerate("HDA"):
        V[f"fair_{k}"] = dec(N["fair_odds"][i], L)
        V[f"odds_{k}"] = dec(mk["reader_best"][i]["odds"], L)
        V[f"avgodds_{k}"] = dec(mk["average_odds"][i], L)
    V["reader_book"] = " / ".join(sorted({r["bookmaker"] for r in mk["reader_best"]}))
    V["margin"] = pct(mk["margin"], L, 1)
    V["books"] = str(mk["books"])
    V["market_time"] = mk["taken_at"][11:16]
    import datetime as _dt
    day = _dt.date.fromisoformat(mk["taken_at"][:10])
    V["market_day"] = (f"{day.day} October" if L == "en" else f"{day.day}. Oktober") if day.month == 10 else mk["taken_at"][:10]
    # favourites
    for name, r in zip(["f50", "f60", "f70", "f80", "bh", "bhl"], N["favourites"]):
        V[f"{name}_n"] = f"{r['n']:,}".replace(",", ".") if L == "de" else f"{r['n']:,}"
        for k in ["models", "market", "actual"]:
            V[f"{name}_{k}"] = pct(r[k], L)
    for r in N["by_model_buckets"]:
        name = f"own{int(round(r['lo'] * 100))}"
        V[f"{name}_n"] = str(r["n"])
        for k in ["models", "market", "actual"]:
            V[f"{name}_{k}"] = pct(r[k], L)
    for name, r in zip(["bhl", "bhz", "bhm"], N["bayern_home_split"]):
        V[f"{name}_n"] = str(r["n"])
        for k in ["models", "market", "actual"]:
            V[f"{name}_{k}"] = pct(r[k], L)
    r = N["favourites"][4]
    V["bh_gap"] = dec((r["market"] - r["models"]) * 100, L, 1)
    r = N["fav_doubted"]
    V["fd_n"] = str(r["n"])
    for k in ["models", "market", "actual"]:
        V[f"fd_{k}"] = pct(r[k], L)
    for i, name in enumerate(["t_all", "t_hi", "t_mkt", "t_bay", "t_bh"]):
        r = N["totals_check"][i]
        V[f"{name}_n"] = f"{r['n']:,}".replace(",", ".") if L == "de" else f"{r['n']:,}"
        V[f"{name}_models"], V[f"{name}_actual"] = dec(r["models"], L), dec(r["actual"], L)
        V[f"{name}_o25mkt"], V[f"{name}_o25act"] = pct(r["over25_market"], L), pct(r["over25_actual"], L)
        V[f"{name}_diff"] = dec(r["actual"] - r["models"], L)
    # backtest
    bt = N["backtest"]
    V["bt_n"] = f"{bt['n']:,}".replace(",", ".") if L == "de" else f"{bt['n']:,}"
    for k, v in bt["rps"].items():
        V[f"rps_{k}"] = dec(v, L, 4)
    V["rps_gap"] = dec(bt["rps"]["ens"] - bt["rps"]["avgc"], L, 4)
    V["cur_n"] = str(bt["current"]["n"])
    V["cur_ens"], V["cur_mkt"] = dec(bt["current"]["ens"], L, 4), dec(bt["current"]["market"], L, 4)
    V["f70rps_n"] = str(N["fav70_rps"]["n"])
    V["f70rps_ens"], V["f70rps_mkt"] = dec(N["fav70_rps"]["ens"], L, 4), dec(N["fav70_rps"]["market"], L, 4)
    # form and table
    for tag, team in [("fcb", "Bayern Munich"), ("rbl", "RB Leipzig")]:
        f = N["form"][team]
        for k in ["pts", "gf", "ga", "home_gf", "home_ga", "away_gf", "away_ga", "sotf", "sota", "w", "d", "l"]:
            V[f"{tag}_{k}"] = str(f[k])
        ls = N["last_season"][team]
        V[f"{tag}_last_pos"], V[f"{tag}_last_pts"], V[f"{tag}_last_gf"] = str(ls["pos"]), str(ls["pts"]), str(ls["gf"])
        for k in ["xgf", "xga", "home_xgf", "home_xga", "away_xgf", "away_xga"]:
            V[f"{tag}_{k}"] = dec(f[k], L, 1)
        V[f"{tag}_avg_total"] = dec(f["avg_total"], L, 1)
        V[f"{tag}_xgf_pg"] = dec(f["xgf"] / len(f["matches"]), L, 1)
        V[f"{tag}_xga_pg"] = dec(f["xga"] / len(f["matches"]), L, 1)
        V[f"{tag}_pos"] = str(N["table"][team]["pos"])
        V[f"{tag}_gd"] = f"{N['table'][team]['gd']:+d}"
        s = N["strength"][team]
        V[f"{tag}_att"], V[f"{tag}_conc"] = dec(s["att"], L), dec(s["conc"], L)
        V[f"{tag}_att_rank"] = str(N["strength_rank"]["att"].index(team) + 1)
        V[f"{tag}_conc_rank"] = str(N["strength_rank"]["conc"].index(team) + 1)
        V[f"{tag}_xgf_rank"] = str(N["xg_rank"]["xgf"].index(team) + 1)
        V[f"{tag}_xga_rank"] = str(N["xg_rank"]["xga"].index(team) + 1)
        for i, r in enumerate(f["matches"], 1):                     # each league match, in order
            V[f"{tag}_m{i}_score"] = score([r["gf"], r["ga"]], L)
            V[f"{tag}_m{i}_xgf"], V[f"{tag}_m{i}_xga"] = dec(r["xgf"], L, 1), dec(r["xga"], L, 1)
        gx = N["bayern_goals_vs_xg" if tag == "fcb" else "leipzig_goals_vs_xg"]
        V[f"{tag}_goals_xg_pct"] = pct(gx["goals"] / gx["xg"] - 1, L)
    SHORT = {"Bayern Munich": "Bayern", "Ein Frankfurt": "Frankfurt", "M'gladbach": "Gladbach", "Werder Bremen": "Bremen",
             "Union Berlin": "Union", "RB Leipzig": "Leipzig", "FC Koln": "Köln", "Schalke 04": "Schalke"}
    order = list(N["table"])
    V["leader"], V["second"] = SHORT.get(order[0], order[0]), SHORT.get(order[1], order[1])
    V["leader_pts"] = str(N["table"][order[0]]["pts"])
    V["xga_top"] = SHORT.get(N["xg_rank"]["xga"][0], N["xg_rank"]["xga"][0])
    for tag, team in [("fcb", "Bayern Munich"), ("rbl", "RB Leipzig")]:
        for key, pos in [("pos_ord", N["table"][team]["pos"]), ("last_ord", N["last_season"][team]["pos"])]:
            V[f"{tag}_{key}"] = f"{pos}." if L == "de" else f"{pos}{({1: 'st', 2: 'nd', 3: 'rd'}).get(pos if pos < 20 else pos % 10, 'th')}"
    bs = N["bayes_shots"]
    V["sot_h"], V["sot_a"] = dec(bs["sot"][0], L, 1), dec(bs["sot"][1], L, 1)
    V["conv_h"], V["conv_a"] = pct(bs["conv"][0], L), pct(bs["conv"][1], L)
    # head-to-head
    h = N["h2h"]
    V["h2h_n"], V["h2h_w"], V["h2h_d"], V["h2h_l"] = (str(h["all"][k]) for k in ["n", "w", "d", "l"])
    V["h2h_gf"], V["h2h_ga"] = str(h["all"]["gf"]), str(h["all"]["ga"])
    mu = h["munich"]
    V["mun_n"] = str(len(mu))
    V["mun_w"] = str(sum(r["score"][0] > r["score"][1] for r in mu))
    V["mun_d"] = str(sum(r["score"][0] == r["score"][1] for r in mu))
    V["mun_l"] = str(sum(r["score"][0] < r["score"][1] for r in mu))
    V["mun_first_p"] = pct(mu[0]["p_bayern"], L)
    V["mun_last_p"] = pct(mu[-1]["p_bayern"], L)
    V["mun_min_p"] = pct(min(r["p_bayern"] for r in mu), L)
    V["mun_2023_p"] = pct(next(r["p_bayern"] for r in mu if r["date"].startswith("2023-05")), L)
    V["mun_avg_p"] = pct(sum(r["p_bayern"] for r in mu) / len(mu), L)
    V["mun_won_share"] = pct(sum(r["score"][0] > r["score"][1] for r in mu) / len(mu), L)
    # model config
    c = N["config"]
    V["divergences"] = str(c["bayes_divergences"])
    V["rhat"] = dec(c["bayes_max_rhat"], L, 3)
    bf = N["bayes_fit"]
    V["bayes_matches"] = f"{bf['matches']:,}".replace(",", ".") if L == "de" else f"{bf['matches']:,}"
    V["bayes_clubs"] = str(bf["clubs"])
    V["bayes_from"] = f"{bf['first_season']}/{(bf['first_season'] + 1) % 100:02d}"
    V["matches_used"] = f"{N['inputs']['matches_used']:,}".replace(",", ".") if L == "de" else f"{N['inputs']['matches_used']:,}"
    # XGBoost drivers
    for side in ["home", "away"]:
        for i, (feat, mult, val) in enumerate(N["xgb_drivers"][side][:3], 1):
            V[f"xgb_{side}{i}_mult"] = dec(mult, L)
    # full time (fulltime.json, written by analysis/tools/fulltime.py after the match)
    ft_path = os.path.join(POST, "fulltime.json")
    if os.path.exists(ft_path):
        FT = json.load(open(ft_path, encoding="utf-8"))
        V["ft_score"] = score(FT["score"], L)
        for k, v in FT["rps"].items():
            V[f"ft_rps_{k}"] = dec(v, L, 3)
        V["ft_rank"] = str(FT["exactScore"]["rank"])
        V["ft_p"] = pct(FT["exactScore"]["percent"] / 100, L, 1)
        u = FT["understat"]
        V["ft_xg_h"], V["ft_xg_a"] = dec(u["xg"][0], L), dec(u["xg"][1], L)
        V["ft_xgwin"] = pct(u["xgResultSplit"][0], L)
        close = FT["odds"]["snapshots"][-1]
        V["ft_close_H"], V["ft_close_A"] = pct(close["consensus"][0], L, 1), pct(close["consensus"][2], L, 1)
        V["ft_close_A_dec"] = dec(close["consensus"][2], L, 4)
        V["ft_close_min"], V["ft_close_books"] = str(close["minutes_before"]), str(close["books"])
        clv = mk["reader_best"][2]["odds"] * close["consensus"][2] - 1      # a Leipzig ticket at the best reader price
        V["ft_clv_A"] = ("+" if clv >= 0 else "−") + pct(abs(clv), L, 1)
    return V


def fill(text, L):
    V = values(L)

    def rep(m):
        k = m.group(1)
        if k not in V:
            raise SystemExit(f"unknown placeholder [[{k}]] ({L})")
        return V[k]
    out = re.sub(r"\[\[([a-zA-Z0-9_]+)\]\]", rep, text)
    return out


tpl = open(os.path.join(POST, "article.template.html"), encoding="utf-8").read()
cut = tpl.index('<article class="post" lang="de"')
html = fill(tpl[:cut], "en") + fill(tpl[cut:], "de")
left = re.findall(r"\[\[[^\]]+\]\]", html)
if left:
    raise SystemExit(f"left-over placeholders: {left}")
open(os.path.join(POST, "index.html"), "w", encoding="utf-8").write(html)
# chart sizes on every <img>, so the page does not jump while charts load (analysis/tools/size_figures.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from pathlib import Path
from size_figures import size_post
size_post(Path(POST))
print("wrote", os.path.join(POST, "index.html"))
