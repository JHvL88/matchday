"""The pre-registered test of the season simulator (analysis/backtest/season/PREREGISTRATION.md).

Every 1. Bundesliga season from 2014/15 to 2025/26 is replayed from 34 points in time (before the
first kick-off, then after every matchday): the ratings are refitted on what was known then, the rest
of the season is simulated 10,000 times, and the forecast of every club's final position is kept.

    # 1. tuning seasons, every setting on the grid (about 25 minutes on two CPU cores)
    python analysis/pipeline/season_backtest.py run data/matches.csv /tmp/season-bt --phase tune
    # 2. choose the settings from the tuning seasons only
    python analysis/pipeline/season_backtest.py choose data/matches.csv /tmp/season-bt
    # 3. test seasons, with the chosen settings (and without doubt, for comparison)
    python analysis/pipeline/season_backtest.py run data/matches.csv /tmp/season-bt --phase test
    # 4. grade everything, write the report's numbers and the site's replay file
    python analysis/pipeline/season_backtest.py grade data/matches.csv /tmp/season-bt analysis/backtest/season/results.json \
        --site data/season_test.json --replays data/season_replays.json --openligadb-dir openligadb/

A checkpoint "after k matchdays" is the date of the season's (9k)th match in date order; every match
up to and including that date counts as played (football-data.co.uk has no matchday numbers).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

TUNING = list(range(2014, 2019))
TEST = list(range(2019, 2026))
SIGMAS = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
MARKET_XIS = [0.0019, 0.004, 0.008]
CHECKPOINTS = list(range(34))
SIMS = 10_000
OUTCOMES = {"title": (1, 1), "top4": (1, 4), "top6": (1, 6), "playoff": (16, 16), "drop": (17, 18)}
BINS = [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0000001]


def cfg_name(view, sigma, xi=None):
    return f"{view}_s{sigma:g}" + (f"_x{xi:g}" if xi is not None else "")


# ----------------------------------------------------------------------------- checkpoints
def season_table(matches, season):
    cur = matches[(matches.season == season) & (matches["div"] == "D1")].sort_values(["date", "home"]).reset_index(drop=True)
    if len(cur) != 306:
        raise SystemExit(f"{season}: {len(cur)} matches, expected 306")
    return cur


def checkpoint(cur, k):
    """(cut date, played rows, remaining rows) after k matchdays."""
    if k == 0:
        cut = cur.date.min()
    else:
        cut = cur.date.iloc[9 * k - 1] + pd.Timedelta(days=1)
    return cut, cur[cur.date < cut], cur[cur.date >= cut]


def table_order(table0, teams):
    """Positions as the site's table orders them: points, goal difference, goals, then name."""
    order = sorted(teams, key=lambda t: (-table0[t][0], -table0[t][1], -table0[t][2], t))
    return {t: order.index(t) for t in teams}


def final_positions(cur, teams):
    from season_sim import standings
    tab = standings(cur, teams)
    order = sorted(teams, key=lambda t: (-tab[t][0], -tab[t][1], -tab[t][2]))
    ties = [(a, b) for a, b in zip(order, order[1:]) if tab[a][:3] == tab[b][:3]]
    return {t: order.index(t) for t in teams}, ties


# ----------------------------------------------------------------------------- running
_MATCHES = None


def _init(path):
    global _MATCHES
    _MATCHES = pd.read_csv(path, parse_dates=["date"])


def run_one(task):
    """One season and checkpoint: fit, simulate every requested setting, return the distributions."""
    import season_sim as ss
    season, k, configs, out_dir = task
    path = os.path.join(out_dir, "raw", f"{season}_{k:02d}.npz")
    have = dict(np.load(path)) if os.path.exists(path) else {}
    todo = [c for c in configs if f"{cfg_name(*c)}_pos" not in have]
    if not todo:
        return season, k, 0.0
    t0 = time.time()
    cur = season_table(_MATCHES, season)
    teams = sorted(set(cur.home) | set(cur.away))
    cut, played, remaining = checkpoint(cur, k)
    table0 = ss.standings(played, teams)
    fixtures = list(zip(remaining.home, remaining.away))
    models = ss.model_ratings(_MATCHES, cut, season)
    market = {}
    for view, sigma, xi in todo:
        if view == "market" and xi not in market:
            market[xi] = ss.market_ratings(_MATCHES, cut, season, models.rho, xi=xi)
    out = dict(have)
    out["teams"] = np.array(teams)
    pos_now = table_order(table0, teams)
    out["table_pos"] = np.array([pos_now[t] for t in teams])
    for view, sigma, xi in todo:
        rt = models if view == "models" else market[xi]
        res = ss.simulate(teams, table0, fixtures, rt, sigma, n=SIMS, seed=season * 100 + k)
        name = cfg_name(view, sigma, xi)
        out[f"{name}_pos"] = (res.pos / res.n).astype(np.float32)
        out[f"{name}_xpts"] = (res.pts_sum / res.n).astype(np.float32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path, **out)
    return season, k, time.time() - t0


def tasks_for(phase, out_dir):
    if phase == "tune":
        configs = [("models", s, None) for s in SIGMAS] + [("market", s, x) for x in MARKET_XIS for s in SIGMAS]
        seasons = TUNING
    else:
        ch = json.load(open(os.path.join(out_dir, "chosen.json")))
        configs = [("models", ch["models"]["sigma"], None), ("models", 0.0, None),
                   ("market", ch["market"]["sigma"], ch["market"]["xi"]), ("market", 0.0, ch["market"]["xi"])]
        seasons = TEST
    configs = list(dict.fromkeys(configs))
    return [(s, k, configs, out_dir) for s in seasons for k in CHECKPOINTS]


def cmd_run(a):
    tasks = tasks_for(a.phase, a.out)
    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers, initializer=_init, initargs=(a.matches,)) as pool:
        for i, (season, k, sec) in enumerate(pool.imap_unordered(run_one, tasks), 1):
            if sec:
                print(f"[{i}/{len(tasks)}] {season}/{(season + 1) % 100:02d} after {k} matchdays ({sec:.0f}s)", flush=True)
    print(f"done in {(time.time() - t0) / 60:.1f} minutes")


# ----------------------------------------------------------------------------- grading
def rps_positions(P, y):
    """P: (n, 18) probabilities over final positions, y: (n,) actual positions (0-based)."""
    cp = np.cumsum(P, 1)[:, :-1]
    co = (np.arange(P.shape[1])[None, :-1] >= y[:, None]).astype(float)
    return ((cp - co) ** 2).mean(1)


def outcome_p(P, lo, hi):
    return P[:, lo - 1:hi].sum(1)


def load_raw(out_dir, seasons, matches):
    """{season: {k: npz dict}}, plus actual final positions per season."""
    raw, finals, ties = {}, {}, {}
    for s in seasons:
        cur = season_table(matches, s)
        teams = sorted(set(cur.home) | set(cur.away))
        fp, t = final_positions(cur, teams)
        finals[s], ties[s] = np.array([fp[x] for x in teams]), t
        raw[s] = {}
        for k in CHECKPOINTS:
            path = os.path.join(out_dir, "raw", f"{s}_{k:02d}.npz")
            if os.path.exists(path):
                raw[s][k] = dict(np.load(path))
                assert list(raw[s][k]["teams"]) == teams
    return raw, finals, ties


def score_config(raw, finals, seasons, name, ks=CHECKPOINTS):
    """Mean positional RPS overall and per season, for one setting."""
    per = {}
    for s in seasons:
        vals = [rps_positions(raw[s][k][f"{name}_pos"].astype(float), finals[s]) for k in ks if f"{name}_pos" in raw[s].get(k, {})]
        if len(vals) != len(ks):
            return None
        per[s] = float(np.mean(np.concatenate(vals)))
    return dict(overall=float(np.mean(list(per.values()))), seasons=per)


def baseline_scores(raw, finals, seasons):
    out = {"table": {}, "uniform": {}}
    for s in seasons:
        tv, uv = [], []
        for k in CHECKPOINTS:
            y = finals[s]
            n = len(y)
            if k >= 1:
                P = np.eye(n)[raw[s][k]["table_pos"]]
                tv.append(rps_positions(P, y))
            uv.append(rps_positions(np.full((n, n), 1 / n), y))
        out["table"][s] = float(np.mean(np.concatenate(tv)))
        out["uniform"][s] = float(np.mean(np.concatenate(uv)))
    return {k: dict(overall=float(np.mean(list(v.values()))), seasons=v) for k, v in out.items()}


def cmd_choose(a):
    matches = pd.read_csv(a.matches, parse_dates=["date"])
    raw, finals, _ = load_raw(a.out, TUNING, matches)
    grid = {"models": {}, "market": {}}
    for s in SIGMAS:
        grid["models"][f"{s:g}"] = score_config(raw, finals, TUNING, cfg_name("models", s))["overall"]
        for x in MARKET_XIS:
            grid["market"][f"{s:g}|{x:g}"] = score_config(raw, finals, TUNING, cfg_name("market", s, x))["overall"]
    best_m = min(grid["models"], key=grid["models"].get)
    best_k = min(grid["market"], key=grid["market"].get)
    chosen = dict(models=dict(sigma=float(best_m), rps=grid["models"][best_m]),
                  market=dict(sigma=float(best_k.split("|")[0]), xi=float(best_k.split("|")[1]), rps=grid["market"][best_k]),
                  grid=grid, edge=dict(models=float(best_m) == max(SIGMAS), market=float(best_k.split("|")[0]) == max(SIGMAS)))
    json.dump(chosen, open(os.path.join(a.out, "chosen.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in chosen.items() if k != "grid"}, indent=1))
    for view in grid:
        print(view, {k: round(v, 5) for k, v in sorted(grid[view].items(), key=lambda kv: kv[1])[:6]})


def calibration(raw, finals, seasons, name):
    """Pooled over the five outcomes: forecast bins against how often it happened."""
    p_all, y_all, o_all = [], [], []
    for s in seasons:
        for k in CHECKPOINTS:
            P = raw[s][k][f"{name}_pos"].astype(float)
            y = finals[s]
            for o, (lo, hi) in OUTCOMES.items():
                p_all.append(outcome_p(P, lo, hi))
                y_all.append(((y >= lo - 1) & (y <= hi - 1)).astype(float))
                o_all.append(np.full(len(y), o))
    p, y, o = np.concatenate(p_all), np.concatenate(y_all), np.concatenate(o_all)
    rows = []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (p >= lo) & (p < hi)
        n = int(m.sum())
        if not n:
            continue
        mean_p, freq = float(p[m].mean()), float(y[m].mean())
        se = np.sqrt(max(mean_p * (1 - mean_p), 1e-9) / n)
        ok = abs(freq - mean_p) <= max(1.96 * se, 0.03)
        rows.append(dict(lo=lo, hi=min(hi, 1.0), n=n, forecast=round(mean_p, 4), happened=round(freq, 4), ok=bool(ok)))
    brier = {oc: float(np.mean((p[o == oc] - y[o == oc]) ** 2)) for oc in OUTCOMES}
    return rows, brier


def by_checkpoint(raw, finals, seasons, name):
    return [float(np.mean([rps_positions(raw[s][k][f"{name}_pos"].astype(float), finals[s]).mean() for s in seasons]))
            for k in CHECKPOINTS]


def cmd_grade(a):
    matches = pd.read_csv(a.matches, parse_dates=["date"])
    ch = json.load(open(os.path.join(a.out, "chosen.json")))
    seasons = TUNING + TEST
    raw, finals, ties = load_raw(a.out, seasons, matches)
    sm, sk, xk = ch["models"]["sigma"], ch["market"]["sigma"], ch["market"]["xi"]
    names = {"models": cfg_name("models", sm), "market": cfg_name("market", sk, xk),
             "models_nodoubt": cfg_name("models", 0.0), "market_nodoubt": cfg_name("market", 0.0, xk)}
    res = dict(preregistration="analysis/backtest/season/PREREGISTRATION.md", chosen={k: v for k, v in ch.items() if k != "grid"},
               grid=ch["grid"], ties=ties and {str(s): t for s, t in ties.items() if t}, sims=SIMS)
    for label, ss_ in (("tuning", TUNING), ("test", TEST)):
        block = {}
        for key, name in names.items():
            sc = score_config(raw, finals, ss_, name)
            if sc:
                block[key] = sc
        block.update(baseline_scores(raw, finals, ss_))
        for key in ("models", "market"):
            if key in block:
                rows, brier = calibration(raw, finals, ss_, names[key])
                block[key]["calibration"] = rows
                block[key]["brier"] = brier
                block[key]["byCheckpoint"] = by_checkpoint(raw, finals, ss_, names[key])
                for stage, ks in (("early", range(0, 12)), ("middle", range(12, 23)), ("late", range(23, 34))):
                    block[key][f"stage_{stage}"] = score_config(raw, finals, ss_, names[key], list(ks))["overall"]
        if "models" in block and "market" in block:
            wins = sum(block["market"]["seasons"][s] < block["models"]["seasons"][s] for s in ss_)
            block["marketBetterSeasons"] = int(wins)
        res[label] = block
    # decision rule 2 and 3 on the test seasons
    t = res["test"]
    if t["market"]["overall"] < t["models"]["overall"] and t["marketBetterSeasons"] >= 5:
        verdict = "market"
    elif t["models"]["overall"] < t["market"]["overall"] and (len(TEST) - t["marketBetterSeasons"]) >= 5:
        verdict = "models"
    else:
        verdict = "neither"
    calib = {k: all(r["ok"] for r in t[k]["calibration"] if r["n"] >= 100) for k in ("models", "market")}
    res["verdict"] = dict(better=verdict, wellCalibrated=calib)
    os.makedirs(os.path.dirname(a.results) or ".", exist_ok=True)
    json.dump(res, open(a.results, "w"), indent=1)
    print(json.dumps(res["verdict"]), {k: round(v["overall"], 5) for k, v in t.items() if isinstance(v, dict) and "overall" in v})
    if a.site:
        write_site_test(res, a.site)
    if a.replays:
        write_replays(raw, finals, seasons, names, matches, a.replays, a.openligadb_dir)


def write_site_test(res, path):
    from jsonfmt import dumps
    t = res["test"]
    out = dict(about="The pre-registered test of the season simulator (analysis/backtest/season/README.md): 1. Bundesliga "
                     "2019/20 to 2025/26, replayed from before the first kick-off and after every matchday. rps = positional "
                     "ranked probability score, lower is better.",
               seasons="2019/20 to 2025/26", checkpoints=34, sims=res["sims"], chosen=res["chosen"], verdict=res["verdict"],
               scores={k: round(t[k]["overall"], 4) for k in ("models", "market", "models_nodoubt", "market_nodoubt", "table", "uniform")},
               marketBetterSeasons=t["marketBetterSeasons"],
               bySeason={k: {str(s): round(v, 4) for s, v in t[k]["seasons"].items()} for k in ("models", "market", "table")},
               byCheckpoint={k: [round(v, 4) for v in t[k]["byCheckpoint"]] for k in ("models", "market")},
               calibration={k: t[k]["calibration"] for k in ("models", "market")},
               brier={k: {o: round(v, 4) for o, v in t[k]["brier"].items()} for k in ("models", "market")})
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(out) + "\n")
    print("site test summary ->", path)


def write_replays(raw, finals, seasons, names, matches, path, ol_dir=None):
    """Every past season as the simulator saw it at the time: title, top four and relegation chances of every club
    after every matchday (both sets of ratings), in thousandths."""
    from jsonfmt import dumps
    from teams import club_key
    out = dict(about="Past seasons as the season simulator saw them at the time (out of sample: every number uses only matches "
                     "played before it). Per season and club: final position, then per set of ratings one list per outcome with "
                     "the chance after 0, 1, ..., 33 matchdays, in thousandths. Outcomes: title (1st), top4, drop (17th-18th), "
                     "playoff (16th). The settings were chosen on 2014/15 to 2018/19, so those seasons are in-sample for them.",
               outcomes=["title", "top4", "drop", "playoff"], seasons={})
    for s in seasons:
        cur = season_table(matches, s)
        teams = sorted(set(cur.home) | set(cur.away))
        short, ids = {}, {}
        if ol_dir and os.path.exists(os.path.join(ol_dir, f"bl1-{s}.json")):
            for m in json.load(open(os.path.join(ol_dir, f"bl1-{s}.json"))):
                for side in ("team1", "team2"):
                    key = club_key(m[side]["teamName"])
                    short[key] = m[side].get("shortName") or m[side]["teamName"]
                    ids[key] = m[side]["teamId"]
        clubs = {}
        for i, t in enumerate(teams):
            key = club_key(t)
            entry = dict(name=short.get(key, t), id=ids.get(key), final=int(finals[s][i]) + 1,
                         table=[int(raw[s][k]["table_pos"][i]) + 1 for k in CHECKPOINTS])
            for view in ("models", "market"):
                P = [raw[s][k][f"{names[view]}_pos"][i].astype(float) for k in CHECKPOINTS]
                entry[view] = [[int(round(1000 * p[lo - 1:hi].sum())) for p in P]
                               for lo, hi in ((1, 1), (1, 4), (17, 18), (16, 16))]
            clubs[key] = entry
        out["seasons"][str(s)] = clubs
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(out) + "\n")
    print("replays ->", path, f"{os.path.getsize(path) / 1024:.0f} KB")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("matches")
    r.add_argument("out")
    r.add_argument("--phase", choices=["tune", "test"], required=True)
    r.add_argument("--workers", type=int, default=2)
    c = sub.add_parser("choose")
    c.add_argument("matches")
    c.add_argument("out")
    g = sub.add_parser("grade")
    g.add_argument("matches")
    g.add_argument("out")
    g.add_argument("results")
    g.add_argument("--site")
    g.add_argument("--replays")
    g.add_argument("--openligadb-dir")
    a = ap.parse_args(argv)
    {"run": cmd_run, "choose": cmd_choose, "grade": cmd_grade}[a.cmd](a)


if __name__ == "__main__":
    main()
