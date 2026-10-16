"""Model zoo for Bundesliga match prediction (JAX -> runs on GPU in Colab, CPU elsewhere)."""
import numpy as np
import pandas as pd
import jax
import jax.numpy as jnp
from jax.scipy.special import gammaln
from scipy.optimize import minimize
from scipy.stats import poisson

jax.config.update("jax_enable_x64", True)
MAXG = 11  # score grid 0..10


# ----------------------------------------------------------------------------- utils
def team_index(df):
    teams = sorted(set(df.home) | set(df.away))
    return teams, {t: i for i, t in enumerate(teams)}


def outcome_probs(M):
    """Home / draw / away probabilities from a score matrix M[home_goals, away_goals]."""
    return np.array([np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()])


def rps(p, y):
    """Ranked probability score. p: (n,3) H/D/A, y: (n,) 0=H 1=D 2=A. Lower is better."""
    p = np.atleast_2d(p)
    o = np.eye(3)[np.asarray(y)]
    cp, co = np.cumsum(p, 1)[:, :2], np.cumsum(o, 1)[:, :2]
    return ((cp - co) ** 2).sum(1) / 2


def logloss(p, y):
    p = np.clip(np.atleast_2d(p), 1e-12, 1)
    return -np.log(p[np.arange(len(p)), np.asarray(y)])


def result_code(hg, ag):
    return np.where(hg > ag, 0, np.where(hg == ag, 1, 2))


def dc_tau_matrix(lh, la, rho):
    """Dixon-Coles low-score adjustment applied to a Poisson score grid."""
    t = np.ones((MAXG, MAXG))
    t[0, 0] = 1 - lh * la * rho
    t[0, 1] = 1 + lh * rho
    t[1, 0] = 1 + la * rho
    t[1, 1] = 1 - rho
    return t


def score_matrix(lh, la, rho=0.0):
    g = np.arange(MAXG)
    M = np.outer(poisson.pmf(g, lh), poisson.pmf(g, la)) * dc_tau_matrix(lh, la, rho)
    return M / M.sum()


# ----------------------------------------------------------------------------- Dixon-Coles
class DixonColes:
    """Time-weighted Dixon-Coles (1997) with a 2. Bundesliga intercept.

    log lambda_home = mu + div + home + att[h] - def[a]
    log lambda_away = mu + div        + att[a] - def[h]
    Sum-to-zero constraints via centring; weights w = exp(-xi * days_ago).
    """

    def __init__(self, xi=0.0025, ridge=1e-3, xg_weight=0.0):
        # xg_weight > 0: the Poisson part learns from w*xG + (1-w)*goals where xG exists (hxg/axg
        # columns); the low-score correction still uses actual goals. 0 = the published model.
        self.xi, self.ridge, self.xg_weight = xi, ridge, xg_weight

    def fit(self, df, ref_date):
        df = df[df.date < ref_date]
        self.teams, self.idx = team_index(df)
        T = len(self.teams)
        h = jnp.array(df.home.map(self.idx).values)
        a = jnp.array(df.away.map(self.idx).values)
        x = jnp.array(df.hg.values, dtype=float)
        y = jnp.array(df.ag.values, dtype=float)
        tx, ty = x, y
        if self.xg_weight > 0 and "hxg" in df:
            w_xg = self.xg_weight
            tx = jnp.array(np.where(df.hxg.notna(), w_xg * df.hxg.fillna(0) + (1 - w_xg) * df.hg, df.hg), dtype=float)
            ty = jnp.array(np.where(df.axg.notna(), w_xg * df.axg.fillna(0) + (1 - w_xg) * df.ag, df.ag), dtype=float)
        d2 = jnp.array((df["div"] == "D2").values, dtype=float)
        days = (pd.Timestamp(ref_date) - df.date).dt.days.values
        w = jnp.array(np.exp(-self.xi * days))
        ridge = self.ridge

        def unpack(p):
            att = p[:T] - p[:T].mean()
            de = p[T:2 * T] - p[T:2 * T].mean()
            return att, de, p[2 * T], p[2 * T + 1], p[2 * T + 2], p[2 * T + 3]

        def nll(p):
            att, de, mu, home, div2, rho = unpack(p)
            lh = jnp.exp(mu + div2 * d2 + home + att[h] - de[a])
            la = jnp.exp(mu + div2 * d2 + att[a] - de[h])
            ll = tx * jnp.log(lh) - lh - gammaln(tx + 1) + ty * jnp.log(la) - la - gammaln(ty + 1)
            tau = jnp.where((x == 0) & (y == 0), 1 - lh * la * rho,
                  jnp.where((x == 0) & (y == 1), 1 + lh * rho,
                  jnp.where((x == 1) & (y == 0), 1 + la * rho,
                  jnp.where((x == 1) & (y == 1), 1 - rho, 1.0))))
            ll = ll + jnp.log(jnp.clip(tau, 1e-10, None))
            return -(w * ll).sum() / w.sum() + ridge * (att ** 2 + de ** 2).sum()

        f = jax.jit(jax.value_and_grad(nll))
        p0 = np.zeros(2 * T + 4)
        p0[2 * T] = 0.3
        p0[2 * T + 1] = 0.25
        res = minimize(lambda p: [np.asarray(v, dtype=float) for v in f(jnp.array(p))],
                       p0, jac=True, method="L-BFGS-B")
        att, de, mu, home, div2, rho = [np.asarray(v) for v in unpack(jnp.array(res.x))]
        self.att, self.de = dict(zip(self.teams, att)), dict(zip(self.teams, de))
        self.mu, self.home, self.div2, self.rho = float(mu), float(home), float(div2), float(rho)
        return self

    def rates(self, home, away, d2=False):
        base = self.mu + (self.div2 if d2 else 0.0)
        lh = np.exp(base + self.home + self.att.get(home, 0) - self.de.get(away, 0))
        la = np.exp(base + self.att.get(away, 0) - self.de.get(home, 0))
        return lh, la

    def predict_matrix(self, home, away):
        lh, la = self.rates(home, away)
        return score_matrix(lh, la, self.rho)
