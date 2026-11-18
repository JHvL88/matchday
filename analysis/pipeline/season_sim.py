"""The season simulator: play the rest of the Bundesliga season many times over and count.

Every remaining match is drawn from a Dixon-Coles score distribution, the season is played to the
end, and the final table is ranked as the league ranks it (points, goal difference, goals scored;
the rare tie after that is split at random, where the league would use the head-to-head). Do that
50,000 times and the share of seasons a club finishes first is its title chance.

Two sets of ratings, two opinions, as everywhere on the site:

  models   my published Dixon-Coles (time decay 0.0019, a quarter xG), the model behind one third
           of the weekly ensemble, fitted on everything played before the cut-off.
  market   the same Dixon-Coles shape fitted to the bookmakers' prices instead of the scores: the
           ratings that best reproduce the margin-free 1X2 odds of past matches (closing average
           where football-data.co.uk has it, else its pre-closing average, else Bet365).

Ratings are uncertain and teams change during a season, so each simulated season first gives every
club a strength shift drawn from N(0, sigma^2), added to its attack and to its defence for the whole
of that season. sigma and the market's time decay were set by a pre-registered backtest on
2014/15 to 2018/19 and tested on 2019/20 to 2025/26 (analysis/backtest/season/README.md).

    python analysis/pipeline/season_sim.py data/matches.csv --season 2026 --out data/season.json
        [--openligadb saved.json] [--sims 50000] [--backfill] [--now 2026-11-18T08:00Z]

The site file data/season.json holds the latest snapshot (after the last completed matchday), the
ratings and remaining fixtures the page needs to re-simulate in the browser ("what if"), and one
line per club per matchday since the start of the season for the charts.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from jsonfmt import dumps

# ----------------------------------------------------------------------------- settings
DC_XI = 0.0019            # the published Dixon-Coles (forecast.py)
DC_XG_WEIGHT = 0.25
WINDOW_SEASONS = 8        # both rating sets learn from the last eight seasons, 1. and 2. Bundesliga
# From the pre-registered test (analysis/backtest/season/README.md); see SETTINGS_SOURCE.
SIGMA = {"models": 0.075, "market": 0.075}
MARKET_XI = 0.004
SETTINGS_SOURCE = "analysis/backtest/season/README.md"
SIMS = 50_000
BROWSER_SIMS = 20_000     # what the page re-runs in the browser
MAX_POINTS = 120          # histogram length (no Bundesliga club has reached 92)

TEAMS = 18
# Final positions -> outcomes (1-based positions, inclusive). Europe: 1-4 Champions League,
# 5 Europa League, 6 Conference League play-off; the cup winner and UEFA's extra places can move
# the line to 7th or add a fifth Champions League place, so "europe" means the usual top six.
OUTCOMES = {"title": (1, 1), "top4": (1, 4), "europe": (1, 6), "playoff": (16, 16), "drop": (17, 18)}
OUTCOME_KEYS = list(OUTCOMES)
RANK_LINES = [1, 4, 6, 7, 15, 16, 17]   # positions whose points total the page reports


# ----------------------------------------------------------------------------- ratings
@dataclass
class Ratings:
    """log lambda_home = mu + home + att[h] - de[a];  log lambda_away = mu + att[a] - de[h]."""
    att: dict
    de: dict
    mu: float
    home: float
    rho: float
    source: str = "models"
    extra: dict = field(default_factory=dict)

    def log_rates(self, home, away):
        return (self.mu + self.home + self.att[home] - self.de[away],
                self.mu + self.att[away] - self.de[home])

    def strength(self, team):
        """One number per club for sorting and display: attack plus defence (log scale)."""
        return self.att[team] + self.de[team]


def window(df, ref, season):
    ref = pd.Timestamp(ref)
    return df[(df.season >= season - WINDOW_SEASONS) & (df.date < ref)]


def model_ratings(df, ref, season, xg=True):
    """My published Dixon-Coles, fitted on matches strictly before `ref`."""
    from bl_models import DixonColes
    dc = DixonColes(xi=DC_XI, xg_weight=DC_XG_WEIGHT if xg else 0.0).fit(window(df, ref, season), pd.Timestamp(ref))
    return Ratings(att={k: float(v) for k, v in dc.att.items()}, de={k: float(v) for k, v in dc.de.items()},
                   mu=dc.mu, home=dc.home, rho=dc.rho, source="models", extra=dict(div2=dc.div2))


def market_probabilities(df):
    """Margin-free home/draw/away probabilities per row (proportional removal, as on the site), from the
    closing average, else the pre-closing average, else Bet365. Rows without odds give NaN."""
    out = np.full((len(df), 3), np.nan)
    for prefix in ["avgc", "avg", "b365"]:
        cols = [f"{prefix}_{o}" for o in "hda"]
        if not all(c in df for c in cols):
            continue
        odds = df[cols].to_numpy(dtype=float)
        ok = np.isnan(out[:, 0]) & np.all(odds > 1, axis=1)
        inv = 1 / odds[ok]
        out[ok] = inv / inv.sum(1, keepdims=True)
    return out


def market_ratings(df, ref, season, rho, xi=None, ridge=1e-3):
    """Dixon-Coles ratings fitted to the bookmakers' prices instead of the scores.

    Minimises the time-weighted cross-entropy between the market's margin-free 1X2 probabilities and
    the ones the ratings imply. The low-score correction rho is taken from the models' fit at the same
    date (the 1X2 prices barely pin it down); the goal level mu is learnt from how often the market
    expects draws."""
    import jax
    import jax.numpy as jnp
    from jax.scipy.special import gammaln
    from scipy.optimize import minimize
    from bl_models import MAXG, team_index
    jax.config.update("jax_enable_x64", True)
    xi = MARKET_XI if xi is None else xi
    ref = pd.Timestamp(ref)
    hist = window(df, ref, season)
    q = market_probabilities(hist)
    ok = ~np.isnan(q[:, 0])
    hist, q = hist[ok], q[ok]
    teams, idx = team_index(hist)
    T = len(teams)
    h = jnp.array(hist.home.map(idx).values)
    a = jnp.array(hist.away.map(idx).values)
    d2 = jnp.array((hist["div"] == "D2").values, dtype=float)
    days = (ref - hist.date).dt.days.values
    w = jnp.array(np.exp(-xi * days))
    Q = jnp.array(q)
    g = jnp.arange(MAXG, dtype=float)
    lower = jnp.array(np.tril(np.ones((MAXG, MAXG)), -1))
    diag = jnp.eye(MAXG)
    upper = jnp.array(np.triu(np.ones((MAXG, MAXG)), 1))

    def unpack(p):
        att = p[:T] - p[:T].mean()
        de = p[T:2 * T] - p[T:2 * T].mean()
        return att, de, p[2 * T], p[2 * T + 1], p[2 * T + 2]

    def loss(p):
        att, de, mu, home, div2 = unpack(p)
        lh = jnp.exp(mu + div2 * d2 + home + att[h] - de[a])
        la = jnp.exp(mu + div2 * d2 + att[a] - de[h])
        ph = jnp.exp(g[None, :] * jnp.log(lh)[:, None] - lh[:, None] - gammaln(g + 1)[None, :])
        pa = jnp.exp(g[None, :] * jnp.log(la)[:, None] - la[:, None] - gammaln(g + 1)[None, :])
        M = ph[:, :, None] * pa[:, None, :]
        M = M.at[:, 0, 0].multiply(1 - lh * la * rho)
        M = M.at[:, 0, 1].multiply(1 + lh * rho)
        M = M.at[:, 1, 0].multiply(1 + la * rho)
        M = M.at[:, 1, 1].multiply(1 - rho)
        tot = M.sum((1, 2))
        P = jnp.stack([(M * lower).sum((1, 2)), (M * diag).sum((1, 2)), (M * upper).sum((1, 2))], 1) / tot[:, None]
        ce = -(Q * jnp.log(jnp.clip(P, 1e-12, None))).sum(1)
        return (w * ce).sum() / w.sum() + ridge * (att ** 2 + de ** 2).sum()

    f = jax.jit(jax.value_and_grad(loss))
    p0 = np.zeros(2 * T + 3)
    p0[2 * T] = 0.3
    p0[2 * T + 1] = 0.25
    res = minimize(lambda p: [np.asarray(v, dtype=float) for v in f(jnp.array(p))], p0, jac=True, method="L-BFGS-B")
    att, de, mu, home, div2 = [np.asarray(v) for v in unpack(jnp.array(res.x))]
    return Ratings(att=dict(zip(teams, map(float, att))), de=dict(zip(teams, map(float, de))),
                   mu=float(mu), home=float(home), rho=float(rho), source="market",
                   extra=dict(div2=float(div2), xi=xi, matches=int(len(hist)), converged=bool(res.success)))


# ----------------------------------------------------------------------------- simulation
def dc_sample(lh, la, rho, rng):
    """Scores from the Dixon-Coles distribution, exactly and in one pass.

    The low-score factor tau only moves probability between the four scores 0-0, 0-1, 1-0 and 1-1,
    and it moves the same amount m = |rho| * lh * la * exp(-lh - la) out of two of them and into the
    other two (the grid still sums to one). So: draw two Poisson numbers, then move that mass. With
    rho < 0 (more draws, as fitted) a 0-1 becomes 0-0 with probability |rho| * lh and a 1-0 becomes
    1-1 with probability |rho| * la; with rho > 0 a 0-0 becomes 0-1 with probability rho * lh * la
    and a 1-1 becomes 1-0 with probability rho."""
    x = rng.poisson(lh)
    y = rng.poisson(la)
    if rho == 0:
        return x, y
    u = rng.random(lh.shape)
    if rho < 0:
        y = np.where((x == 0) & (y == 1) & (u < -rho * lh), 0, y)
        y = np.where((x == 1) & (y == 0) & (u < -rho * la), 1, y)
    else:
        y = np.where((x == 0) & (y == 0) & (u < rho * lh * la), 1, y)
        y = np.where((x == 1) & (y == 1) & (u < rho), 0, y)
    return x, y


@dataclass
class SimResult:
    teams: list
    n: int = 0
    pos: np.ndarray = None            # [team, position] counts
    pts_sum: np.ndarray = None
    pts_hist: np.ndarray = None       # [team, final points]
    rank_pts: np.ndarray = None       # [position, points of the club in that position]
    stakes: dict = None               # fixture index -> {"n": [3], "pos": [3, team, position]}
    clinch: dict = None               # matchday the title was settled -> count


def simulate(teams, table0, fixtures, ratings, sigma, n=SIMS, seed=0, stakes=(), schedule=None,
             fixed=None, chunk=10_000):
    """Play the remaining `fixtures` (list of (home, away)) n times.

    teams     the 18 clubs (names as in `ratings`)
    table0    {team: (points, goal difference, goals scored, played)} before the remaining fixtures
    stakes    fixture indices whose result the output is conditioned on ("what's at stake")
    schedule  matchday number per fixture (optional): adds the matchday the title was settled
    fixed     {fixture index: (home goals, away goals)} results to impose ("what if")
    """
    T = len(teams)
    ix = {t: i for i, t in enumerate(teams)}
    R = len(fixtures)
    hi = np.array([ix[h] for h, _ in fixtures], dtype=int)
    ai = np.array([ix[a] for _, a in fixtures], dtype=int)
    base = np.array([ratings.log_rates(h, a) for h, a in fixtures]).reshape(R, 2)
    Hm = np.zeros((R, T))
    Am = np.zeros((R, T))
    Hm[np.arange(R), hi] = 1
    Am[np.arange(R), ai] = 1
    pts0 = np.array([table0[t][0] for t in teams], dtype=float)
    gd0 = np.array([table0[t][1] for t in teams], dtype=float)
    gf0 = np.array([table0[t][2] for t in teams], dtype=float)
    rng = np.random.default_rng(seed)
    out = SimResult(teams=list(teams), pos=np.zeros((T, T), dtype=np.int64), pts_sum=np.zeros(T),
                    pts_hist=np.zeros((T, MAX_POINTS + 1), dtype=np.int64),
                    rank_pts=np.zeros((T, MAX_POINTS + 1), dtype=np.int64),
                    stakes={int(s): dict(n=np.zeros(3, dtype=np.int64), pos=np.zeros((3, T, T), dtype=np.int64)) for s in stakes},
                    clinch={} if schedule is not None else None)
    if schedule is not None:
        schedule = np.asarray(schedule)
        days = np.unique(schedule)
        left_after = np.array([[((schedule > d) & ((hi == t) | (ai == t))).sum() for t in range(T)] for d in days])
    fixed = fixed or {}
    done = 0
    while done < n:
        c = min(chunk, n - done)
        if R:
            delta = rng.normal(0.0, sigma, (c, T)) if sigma > 0 else np.zeros((c, T))
            lh = np.exp(base[:, 0][None, :] + delta[:, hi] - delta[:, ai])
            la = np.exp(base[:, 1][None, :] + delta[:, ai] - delta[:, hi])
            x, y = dc_sample(lh, la, ratings.rho, rng)
            for r, (gh, ga) in fixed.items():
                x[:, r], y[:, r] = gh, ga
            hp = 3 * (x > y) + (x == y)
            ap = 3 * (y > x) + (x == y)
            pts = pts0 + hp @ Hm + ap @ Am
            gf = gf0 + x @ Hm + y @ Am
            ga = y @ Hm + x @ Am
            gd = gd0 + (gf - gf0) - ga
        else:
            x = y = np.zeros((c, 0), dtype=int)
            pts, gd, gf = np.tile(pts0, (c, 1)), np.tile(gd0, (c, 1)), np.tile(gf0, (c, 1))
        key = pts * 1e7 + (gd + 1000) * 1e3 + gf + rng.random((c, T)) * 0.5
        order = np.argsort(-key, axis=1)                    # order[s, r] = team in position r
        position = np.empty_like(order)
        position[np.arange(c)[:, None], order] = np.arange(T)[None, :]
        out.pos += np.bincount((np.arange(T)[None, :] * T + position).ravel(), minlength=T * T).reshape(T, T)
        ptsi = np.clip(pts.astype(int), 0, MAX_POINTS)
        out.pts_sum += pts.sum(0)
        out.pts_hist += np.bincount((np.arange(T)[None, :] * (MAX_POINTS + 1) + ptsi).ravel(),
                                    minlength=T * (MAX_POINTS + 1)).reshape(T, MAX_POINTS + 1)
        ranked = np.take_along_axis(ptsi, order, axis=1)
        out.rank_pts += np.bincount((np.arange(T)[None, :] * (MAX_POINTS + 1) + ranked).ravel(),
                                    minlength=T * (MAX_POINTS + 1)).reshape(T, MAX_POINTS + 1)
        for s, acc in out.stakes.items():
            res = np.where(x[:, s] > y[:, s], 0, np.where(x[:, s] == y[:, s], 1, 2))
            for o in range(3):
                m = res == o
                acc["n"][o] += m.sum()
                if m.any():
                    acc["pos"][o] += np.bincount((np.arange(T)[None, :] * T + position[m]).ravel(), minlength=T * T).reshape(T, T)
        if schedule is not None:
            champ = order[:, 0]
            settled = np.full(c, -1)
            run = np.tile(pts0, (c, 1))
            # already decided before the remaining fixtures?
            for k, d in enumerate([None] + list(days)):
                if d is not None:
                    m = schedule == d
                    run = run + hp[:, m] @ Hm[m] + ap[:, m] @ Am[m]
                    left = left_after[k - 1]
                else:
                    left = np.array([((hi == t) | (ai == t)).sum() for t in range(T)])
                best_other = run + 3 * left[None, :]
                best_other[np.arange(c), champ] = -1
                clear = (run[np.arange(c), champ] > best_other.max(1)) & (settled < 0)
                settled[clear] = 0 if d is None else d
            settled[settled < 0] = days[-1] if len(days) else 0
            for d, cnt in zip(*np.unique(settled, return_counts=True)):
                out.clinch[int(d)] = out.clinch.get(int(d), 0) + int(cnt)
        done += c
        out.n += c
    return out


# ----------------------------------------------------------------------------- summaries
def outcome_probs(pos_row):
    """{outcome: probability} from one club's counts by final position (index 0 = first)."""
    total = pos_row.sum()
    return {k: float(pos_row[lo - 1:hi].sum() / total) for k, (lo, hi) in OUTCOMES.items()}


def quantiles(hist, qs=(0.1, 0.5, 0.9)):
    cdf = np.cumsum(hist) / hist.sum()
    return [int(np.searchsorted(cdf, q)) for q in qs]


def team_summary(res, i):
    pos = res.pos[i]
    return dict(p=outcome_probs(pos), pos=(pos / pos.sum()).tolist(), xpts=float(res.pts_sum[i] / res.n),
                ptsRange=quantiles(res.pts_hist[i]), xpos=float((np.arange(1, len(pos) + 1) * pos).sum() / pos.sum()))


def stakes_summary(res, fixtures, teams):
    """For each conditioned fixture: how each result moves both clubs' chances."""
    out = []
    for s, acc in res.stakes.items():
        home, away = fixtures[s]
        rows = {}
        for side, team in (("home", home), ("away", away)):
            i = teams.index(team)
            by = [outcome_probs(acc["pos"][o][i]) if acc["n"][o] else None for o in range(3)]
            rows[side] = by
        swings = {}
        for side in ("home", "away"):
            for k in OUTCOME_KEYS:
                vals = [b[k] for b in rows[side] if b is not None]
                swings[(side, k)] = max(vals) - min(vals) if vals else 0.0
        out.append(dict(index=s, home=home, away=away, share=(acc["n"] / acc["n"].sum()).tolist(),
                        cond=rows, swing=swings, total=sum(swings.values())))
    return out


# ----------------------------------------------------------------------------- the current season
def standings(played, teams):
    """{team: (points, goal difference, goals for, played)} from rows with home, away, hg, ag."""
    t = {k: [0, 0, 0, 0] for k in teams}
    for r in played.itertuples():
        hg, ag = int(r.hg), int(r.ag)
        for team, f, a in ((r.home, hg, ag), (r.away, ag, hg)):
            e = t[team]
            e[0] += 3 if f > a else 1 if f == a else 0
            e[1] += f - a
            e[2] += f
            e[3] += 1
    return {k: tuple(v) for k, v in t.items()}


def openligadb_matches(season_json):
    """One row per OpenLigaDB match: ids, matchday, kick-off, clubs and the final score if finished."""
    rows = []
    for m in season_json:
        final = next((r for r in m.get("matchResults") or [] if r.get("resultTypeID") == 2), None)
        t = pd.Timestamp(m["matchDateTimeUTC"])
        rows.append(dict(match_id=int(m["matchID"]), matchday=int(m["group"]["groupOrderID"]),
                         kickoff=t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC"),
                         home_id=int(m["team1"]["teamId"]), away_id=int(m["team2"]["teamId"]),
                         home_name=m["team1"]["teamName"], away_name=m["team2"]["teamName"],
                         home_short=m["team1"].get("shortName") or m["team1"]["teamName"],
                         away_short=m["team2"].get("shortName") or m["team2"]["teamName"],
                         finished=bool(m.get("matchIsFinished")) and final is not None,
                         hg=final["pointsTeam1"] if final else np.nan, ag=final["pointsTeam2"] if final else np.nan))
    return pd.DataFrame(rows).sort_values(["matchday", "kickoff", "match_id"]).reset_index(drop=True)


def completed_matchday(ol, now):
    """The last matchday N such that every matchday up to N is complete: all its matches finished,
    except any that were postponed (kick-off more than four days after the matchday's first)."""
    n = 0
    for md, g in ol.groupby("matchday"):
        first = g.kickoff.min()
        postponed = g.kickoff > first + pd.Timedelta(days=4)
        if (g.finished | (postponed & (g.kickoff > now))).all() and g.finished.any():
            n = int(md)
        else:
            break
    return n


def club_names(ol, matches, season):
    """OpenLigaDB team id -> the club's name in the match table, through teams.club_key."""
    from teams import club_key
    names = {}
    pool = matches[matches.season >= season - WINDOW_SEASONS]
    by_key = {}
    for name in sorted(set(pool.home) | set(pool.away)):
        by_key.setdefault(club_key(name), name)
    for tid, name in pd.concat([ol[["home_id", "home_name"]].set_axis(["id", "name"], axis=1),
                                ol[["away_id", "away_name"]].set_axis(["id", "name"], axis=1)]).drop_duplicates().itertuples(index=False):
        key = club_key(name)
        if key not in by_key:
            raise SystemExit(f"no club in the match table for {name!r} (key {key})")
        names[int(tid)] = by_key[key]
    return names


@dataclass
class Snapshot:
    matchday: int
    cut: pd.Timestamp           # ratings use matches strictly before this date
    played: pd.DataFrame        # in match-table names
    remaining: pd.DataFrame
    filled: int                 # played matches the match table did not have yet (goals only)


def snapshot_at(ol, matches, names, season, matchday):
    """The season as it stood after `matchday`: results up to it, the rest still to play."""
    ol = ol.assign(home=ol.home_id.map(names), away=ol.away_id.map(names))
    done = ol.finished & (ol.matchday <= matchday)
    played, remaining = ol[done], ol[~done]
    if len(played):
        last = played.kickoff.max().tz_convert("Europe/Berlin")
        cut = pd.Timestamp(last.date()) + pd.Timedelta(days=1)
    else:
        cut = pd.Timestamp(ol.kickoff.min().tz_convert("Europe/Berlin").date())
    cur = matches[(matches.season == season) & (matches["div"] == "D1") & (matches.date < cut)]
    have = set(zip(cur.home, cur.away))
    missing = played[[(h, a) not in have for h, a in zip(played.home, played.away)]]
    return Snapshot(matchday=matchday, cut=cut, played=played, remaining=remaining, filled=len(missing))


def fit_table(matches, snap, season):
    """The match table the ratings learn from at this snapshot: everything before the cut, plus any played
    match the source files lack yet (goals only, no xG or odds), so the newest results count."""
    df = matches[matches.date < snap.cut]
    cur = df[(df.season == season) & (df["div"] == "D1")]
    have = set(zip(cur.home, cur.away))
    extra = snap.played[[(h, a) not in have for h, a in zip(snap.played.home, snap.played.away)]]
    if len(extra):
        add = pd.DataFrame(dict(div="D1", date=pd.to_datetime(extra.kickoff.dt.tz_convert("Europe/Berlin").dt.date),
                                home=extra.home.values, away=extra.away.values, hg=extra.hg.values.astype(float),
                                ag=extra.ag.values.astype(float), season=season))
        df = pd.concat([df, add], ignore_index=True)
    return df


def run_snapshot(ol, matches, names, season, matchday, sims, seed=None, with_stakes=True):
    snap = snapshot_at(ol, matches, names, season, matchday)
    df = fit_table(matches, snap, season)
    teams = sorted(set(names.values()))
    table0 = standings(snap.played, teams)
    fixtures = list(zip(snap.remaining.home, snap.remaining.away))
    schedule = snap.remaining.matchday.to_numpy()
    nxt = snap.remaining[snap.remaining.matchday == matchday + 1]
    stakes = [int(np.flatnonzero(snap.remaining.match_id.to_numpy() == mid)[0]) for mid in nxt.match_id] if with_stakes else []
    seed = seed if seed is not None else season * 100 + matchday
    models = model_ratings(df, snap.cut, season)
    market = market_ratings(df, snap.cut, season, models.rho)
    views = {}
    for name, rt in (("models", models), ("market", market)):
        res = simulate(teams, table0, fixtures, rt, SIGMA[name], n=sims, seed=seed, stakes=stakes, schedule=schedule)
        views[name] = (rt, res)
    return snap, teams, table0, fixtures, views


# ----------------------------------------------------------------------------- site file
ABOUT = ("The season simulator: the rest of the Bundesliga season played many times over, by my models' "
         "ratings (Dixon-Coles) and by ratings implied by the bookmakers' odds. Written by "
         "analysis/pipeline/season_sim.py (never by hand) after each completed matchday. p = chance of each "
         "outcome (title: 1st; top4: 1st-4th; europe: 1st-6th; playoff: 16th; drop: 17th-18th); pos = chance "
         "of each final position; xpts = expected final points; ptsRange = 10th, 50th and 90th percentile of "
         "final points. ratings and fixtures let the page re-run the simulation in the browser.")


def r4(x):
    return round(float(x), 4)


def history_row(view_res, teams, ids_by_name, table0):
    rows = {}
    order = sorted(teams, key=lambda t: (-table0[t][0], -table0[t][1], -table0[t][2], t))
    for i, t in enumerate(teams):
        s = team_summary(view_res, i)
        rows[str(ids_by_name[t])] = [round(s["p"][k], 3) for k in OUTCOME_KEYS] + [round(s["xpts"], 1), order.index(t) + 1]
    return rows


def site_view(rt, res, sigma, teams, ids_by_name, fixtures, stakes_rows):
    summ = {str(ids_by_name[t]): team_summary(res, i) for i, t in enumerate(teams)}
    lines = {str(r): dict(range=quantiles(res.rank_pts[r - 1]), hist=res.rank_pts[r - 1][: MAX_POINTS + 1].tolist())
             for r in RANK_LINES}
    for v in lines.values():   # trim the histogram to where it has mass
        h = np.array(v["hist"])
        nz = np.flatnonzero(h)
        v["from"] = int(nz[0]) if len(nz) else 0
        v["hist"] = [r4(x) for x in (h[v["from"]: nz[-1] + 1] / h.sum())] if len(nz) else []
    teams_out = {}
    for t in teams:
        s = summ[str(ids_by_name[t])]
        teams_out[str(ids_by_name[t])] = dict(p={k: r4(v) for k, v in s["p"].items()}, pos=[r4(x) for x in s["pos"]],
                                              xpts=round(s["xpts"], 2), xpos=round(s["xpos"], 2), ptsRange=s["ptsRange"])
    view = dict(sigma=sigma, ratings=dict(mu=r4(rt.mu), home=r4(rt.home), rho=r4(rt.rho),
                                          att={str(ids_by_name[t]): r4(rt.att[t]) for t in teams},
                                          de={str(ids_by_name[t]): r4(rt.de[t]) for t in teams}),
                teams=teams_out, lines=lines)
    if res.clinch is not None:
        view["titleSettled"] = {str(k): r4(v / res.n) for k, v in sorted(res.clinch.items())}
    stakes = []
    for s in stakes_rows:
        stakes.append(dict(fixture=s["index"], share=[r4(x) for x in s["share"]],
                           home={k: [r4(b[k]) if b else None for b in s["cond"]["home"]] for k in OUTCOME_KEYS},
                           away={k: [r4(b[k]) if b else None for b in s["cond"]["away"]] for k in OUTCOME_KEYS},
                           total=r4(s["total"])))
    view["stakes"] = stakes
    return view


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def code_commit():
    try:
        return subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or None
    except OSError:
        return None


def build_site(ol, matches, names, season, matchday, sims, now, matches_path=None, history=None, verbose=True):
    t0 = time.time()
    snap, teams, table0, fixtures, views = run_snapshot(ol, matches, names, season, matchday, sims)
    ids_by_name = {v: k for k, v in names.items()}
    short = {}
    for r in ol.itertuples():
        short[r.home_id] = r.home_short
        short[r.away_id] = r.away_short
    out_views = {}
    for name, (rt, res) in views.items():
        out_views[name] = site_view(rt, res, SIGMA[name], teams, ids_by_name, fixtures, stakes_summary(res, fixtures, teams))
        if verbose:
            top = sorted(teams, key=lambda t: -res.pos[teams.index(t)][0])[:4]
            print(f"{name}: title " + ", ".join(f"{t} {res.pos[teams.index(t)][0] / res.n:.1%}" for t in top), flush=True)
    rem = snap.remaining
    hist = dict(history or {})
    hist[str(matchday)] = dict(date=snap.cut.strftime("%Y-%m-%d"),
                               views={n: history_row(res, teams, ids_by_name, table0) for n, (rt, res) in views.items()})
    site = dict(
        about=ABOUT, season=season, afterMatchday=matchday,
        updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"), cut=snap.cut.strftime("%Y-%m-%d"), sims=sims, browserSims=BROWSER_SIMS,
        settings=dict(source=SETTINGS_SOURCE, sigma=SIGMA, marketXi=MARKET_XI, dcXi=DC_XI, dcXgWeight=DC_XG_WEIGHT,
                      windowSeasons=WINDOW_SEASONS, tiebreak="points, goal difference, goals scored, then at random"),
        inputs=dict(matchesSha256=sha256(matches_path) if matches_path else None, codeCommit=code_commit(),
                    filledFromOpenLigaDB=snap.filled, marketMatches=views["market"][0].extra.get("matches")),
        teams={str(ids_by_name[t]): dict(name=t, short=short.get(ids_by_name[t], t), table=list(table0[t])) for t in teams},
        fixtures=[dict(id=int(r.match_id), md=int(r.matchday), kickoff=r.kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       home=int(r.home_id), away=int(r.away_id)) for r in rem.itertuples()],
        views=out_views,
        history=dict(sorted(hist.items(), key=lambda kv: int(kv[0]))),
        seconds=round(time.time() - t0),
    )
    return site


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("matches", help="match table with xG (build_matches.py --understat)")
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--out", default="data/season.json")
    ap.add_argument("--openligadb", help="saved getmatchdata JSON for the season instead of downloading")
    ap.add_argument("--sims", type=int, default=SIMS)
    ap.add_argument("--matchday", type=int, help="simulate after this matchday (default: the last completed one)")
    ap.add_argument("--backfill", action="store_true", help="also (re)compute the history line for every earlier matchday")
    ap.add_argument("--force", action="store_true", help="recompute even if the file already has this matchday")
    ap.add_argument("--now", help="pretend it is this UTC time (tests)")
    a = ap.parse_args(argv)

    from site_odds import openligadb_season
    now = pd.Timestamp(a.now) if a.now else pd.Timestamp.now(tz="UTC")
    now = now.tz_convert("UTC") if now.tzinfo else now.tz_localize("UTC")
    ol = openligadb_matches(openligadb_season(a.season, a.openligadb))
    matches = pd.read_csv(a.matches, parse_dates=["date"])
    names = club_names(ol, matches, a.season)
    matchday = a.matchday if a.matchday is not None else completed_matchday(ol, now)
    old = json.load(open(a.out, encoding="utf-8")) if os.path.exists(a.out) else None
    if old and old.get("season") != a.season:
        old = None
    history = (old or {}).get("history", {})
    if old and not a.force and not a.backfill and old.get("afterMatchday") == matchday:
        snap = snapshot_at(ol, matches, names, a.season, matchday)
        if old.get("inputs", {}).get("filledFromOpenLigaDB", 0) == 0 or snap.filled > 0:
            print(f"matchday {matchday} is already simulated; nothing to do")
            github_output(changed="false", matchday=matchday)
            return 0
        print(f"matchday {matchday}: the source files have caught up, simulating again with their xG and odds")
    if a.backfill:
        for md in range(0, matchday):
            snap, teams, table0, fixtures, views = run_snapshot(ol, matches, names, a.season, md, min(a.sims, 20_000), with_stakes=False)
            ids_by_name = {v: k for k, v in names.items()}
            history[str(md)] = dict(date=snap.cut.strftime("%Y-%m-%d"),
                                    views={n: history_row(res, teams, ids_by_name, table0) for n, (rt, res) in views.items()})
            print(f"history: after matchday {md} done", flush=True)
    site = build_site(ol, matches, names, a.season, matchday, a.sims, now, a.matches, history)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(dumps(site) + "\n")
    print(f"{a.out}: after matchday {matchday}, {a.sims:,} seasons, {len(site['fixtures'])} matches to play ({site['seconds']}s)")
    github_output(changed="true", matchday=matchday)
    return 0


def github_output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")


if __name__ == "__main__":
    sys.exit(main())
