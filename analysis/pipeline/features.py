"""Leak-free pre-match features: own goal-based Elo + exponentially weighted team form.

Every feature for a match only uses matches strictly before its kick-off date.
1. and 2. Bundesliga share one timeline, so promoted clubs arrive with real form.
"""
import numpy as np
import pandas as pd


def elo_ratings(df, k=20.0, home_adv=60.0, carry=0.8, d2_offset=-150.0):
    """World-Football-Elo style ratings with a goal-difference multiplier.

    carry: share of the deviation from the league mean kept over the summer.
    d2_offset: starting rating gap for clubs first seen in the 2. Bundesliga.
    Returns pre-match ratings (elo_h, elo_a) aligned with df's rows.
    """
    r = {}
    out_h, out_a = np.empty(len(df)), np.empty(len(df))
    last_season = None
    for i, row in enumerate(df.itertuples(index=False)):
        if row.season != last_season and last_season is not None:
            mean = np.mean(list(r.values()))
            r = {t: mean + carry * (v - mean) for t, v in r.items()}
        last_season = row.season
        base = 1500.0 + (d2_offset if row.div == "D2" else 0.0)
        rh, ra = r.setdefault(row.home, base), r.setdefault(row.away, base)
        out_h[i], out_a[i] = rh, ra
        if np.isnan(row.hg):          # future fixture: rating only, no update
            continue
        exp_h = 1 / (1 + 10 ** (-(rh + home_adv - ra) / 400))
        gd = row.hg - row.ag
        res = 1.0 if gd > 0 else 0.5 if gd == 0 else 0.0
        mult = 1.0 if abs(gd) <= 1 else (1.5 if abs(gd) == 2 else (11 + abs(gd)) / 8)
        delta = k * mult * (res - exp_h)
        r[row.home], r[row.away] = rh + delta, ra - delta
    return out_h, out_a


def team_long(df):
    """One row per team per match (for rolling form)."""
    base = dict(date=df.date.values, mid=df.index.values, season=df.season.values)
    home = pd.DataFrame({**base, "team": df.home.values, "opp": df.away.values, "is_home": 1,
                         "gf": df.hg.values, "ga": df.ag.values, "sf": df.hs.values, "sa": df.as_.values,
                         "tf": df.hst.values, "ta": df.ast.values})
    away = pd.DataFrame({**base, "team": df.away.values, "opp": df.home.values, "is_home": 0,
                         "gf": df.ag.values, "ga": df.hg.values, "sf": df.as_.values, "sa": df.hs.values,
                         "tf": df.ast.values, "ta": df.hst.values})
    return pd.concat([home, away]).sort_values(["team", "date", "mid"]).reset_index(drop=True)


def ewm_form(long, halflife=8, stats=("gf", "ga", "sf", "sa", "tf", "ta")):
    """EWMA of each stat over the team's previous matches (shifted => strictly pre-match)."""
    out = long[["mid", "team", "date"]].copy()
    g = long.groupby("team", sort=False)
    for s in stats:
        out[f"{s}_ewm"] = g[s].transform(lambda x: x.shift(1).ewm(halflife=halflife, ignore_na=True).mean())
    out["n_prev"] = g.cumcount()
    out["rest_days"] = g["date"].transform(lambda x: x.diff().dt.days).clip(upper=30)
    out["pts_last5"] = g.apply(lambda x: pd.Series(
        np.where(x.gf > x.ga, 3, np.where(x.gf == x.ga, 1, 0)), index=x.index
    ).shift(1).rolling(5, min_periods=1).sum()).reset_index(level=0, drop=True)
    return out


def build_features(df, halflife=8):
    df = df.sort_values(["date", "div", "home"]).reset_index(drop=True)
    df["elo_h_own"], df["elo_a_own"] = elo_ratings(df)
    long = team_long(df)
    form = ewm_form(long, halflife)
    is_home = long.is_home.values == 1
    fh = form[is_home].set_index("mid").add_prefix("h_")
    fa = form[~is_home].set_index("mid").add_prefix("a_")
    X = df.join(fh, how="left").join(fa, how="left")
    X["elo_diff"] = X.elo_h_own - X.elo_a_own
    for s in ["gf", "ga", "sf", "sa", "tf", "ta"]:
        X[f"d_{s}"] = X[f"h_{s}_ewm"] - X[f"a_{s}_ewm"]
    X["h_conv"] = X.h_gf_ewm / X.h_tf_ewm.clip(lower=0.5)
    X["a_conv"] = X.a_gf_ewm / X.a_tf_ewm.clip(lower=0.5)
    X["h_keep"] = X.h_ga_ewm / X.h_ta_ewm.clip(lower=0.5)
    X["a_keep"] = X.a_ga_ewm / X.a_ta_ewm.clip(lower=0.5)
    # promoted this season = first top-flight season after a 2. Bundesliga campaign
    d1_seasons = {}
    for s, g in df[df["div"] == "D1"].groupby("season"):
        d1_seasons[s] = set(g.home)
    X["h_promoted"] = [int(h not in d1_seasons.get(s - 1, set())) for h, s in zip(X.home, X.season)]
    X["a_promoted"] = [int(a not in d1_seasons.get(s - 1, set())) for a, s in zip(X.away, X.season)]
    X["ghost"] = ((X.date >= "2020-05-16") & (X.date <= "2021-07-31")).astype(int)
    X["y"] = np.where(X.hg > X.ag, 0, np.where(X.hg == X.ag, 1, 2))
    return X


FEATURES = [
    "elo_h_own", "elo_a_own", "elo_diff",
    "h_gf_ewm", "h_ga_ewm", "h_sf_ewm", "h_sa_ewm", "h_tf_ewm", "h_ta_ewm",
    "a_gf_ewm", "a_ga_ewm", "a_sf_ewm", "a_sa_ewm", "a_tf_ewm", "a_ta_ewm",
    "d_gf", "d_ga", "d_tf", "d_ta", "h_conv", "a_conv", "h_keep", "a_keep",
    "h_pts_last5", "a_pts_last5", "h_rest_days", "a_rest_days",
    "h_promoted", "a_promoted", "ghost",
]
