"""Bayesian dynamic 'shots-to-goals' model (NumPyro / JAX — GPU in Colab).

Two-stage data-generating story for each team in a match:
  1) chance creation:  shots on target  SOT ~ NegBin(mean = lam, conc = phi)
        log lam = alpha[div] + home*(1 - ghost) + home_ghost*ghost
                  + att[team, period] - def[opp, period] + red_eff*(red_opp - red_own)
  2) finishing:        goals | SOT ~ Binomial(SOT, p)
        logit p = beta[div] + gamma_home + fin[team, season] - keep[opp, season]
  When SOT is missing, goals ~ NegBin(mean = lam*p, conc = phi)  (thinning of a NegBin).

att/def follow Gaussian random walks over ~quarter-season periods (bigger steps over summers),
fin/keep follow slower random walks over seasons. 1. and 2. Bundesliga share one scale, so
promoted clubs carry their 2. Bundesliga form into the top flight.
"""
import numpy as np
import pandas as pd
import jax
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS, init_to_median

PERIODS_PER_SEASON = 4
USE_XG = False   # pre-registered xG variant: xG as a second, noisy view of chance creation


def period_of(month):
    """Within-season period index.
    4 periods: Jul-Sep=0, Oct-Dec=1, Jan-Feb=2, Mar-Jun=3.  2 periods: Jul-Dec=0, Jan-Jun=1."""
    m = np.asarray(month)
    if PERIODS_PER_SEASON == 2:
        out = np.where(m >= 7, 0, 1)
    else:
        out = np.select([(m >= 7) & (m <= 9), m >= 10, m <= 2], [0, 1, 2], 3)
    return out if out.ndim else int(out)


def build_data(df, first_season, ref_date):
    df = df[(df.season >= first_season) & (df.date < ref_date)].copy()
    teams = sorted(set(df.home) | set(df.away))
    tid = {t: i for i, t in enumerate(teams)}
    S = int(pd.Timestamp(ref_date).year - (pd.Timestamp(ref_date).month < 7) - first_season + 1)
    P = S * PERIODS_PER_SEASON
    per = (df.season.values - first_season) * PERIODS_PER_SEASON + period_of(df.date.dt.month.values)
    ghost = ((df.date >= "2020-05-16") & (df.date <= "2021-07-31")).values.astype(float)
    hst = df.hst.values.copy()
    ast = df.ast.values.copy()
    has = ~(np.isnan(hst) | np.isnan(ast))
    hst = np.where(has, np.maximum(np.nan_to_num(hst), df.hg.values), 0).astype(int)
    ast = np.where(has, np.maximum(np.nan_to_num(ast), df.ag.values), 0).astype(int)
    use_xg = USE_XG and "hxg" in df
    has_xg = (df.hxg.notna() & df.axg.notna()).values if use_xg else np.zeros(len(df), bool)
    xg_h = np.maximum(df.hxg.fillna(1.0).values, 0.02) if use_xg else np.ones(len(df))
    xg_a = np.maximum(df.axg.fillna(1.0).values, 0.02) if use_xg else np.ones(len(df))
    data = dict(
        has_xg=has_xg, xg_h=xg_h, xg_a=xg_a,
        h=df.home.map(tid).values, a=df.away.map(tid).values,
        per=per.astype(int), sea=(df.season.values - first_season).astype(int),
        d2=(df["div"] == "D2").values.astype(int), ghost=ghost,
        hst=hst, ast=ast, has=has, hg=df.hg.values.astype(int), ag=df.ag.values.astype(int),
        hr=np.nan_to_num(df.hr.values), ar=np.nan_to_num(df.ar.values),
    )
    # summer boundaries (period p where p % 4 == 0 starts a new season)
    new_season = (np.arange(P) % PERIODS_PER_SEASON == 0).astype(float)
    meta = dict(teams=teams, tid=tid, S=S, P=P, T=len(teams), new_season=new_season,
                first_season=first_season, use_xg=bool(use_xg))
    return {k: jnp.asarray(v) for k, v in data.items()}, meta


def random_walk(name, T, n, sig0, sig_step):
    """Non-centred Gaussian random walk, centred across teams in every step. Returns (T, n)."""
    z = numpyro.sample(f"z_{name}", dist.Normal(0, 1).expand([T, n]).to_event(2))
    steps = z * sig_step[None, :]
    steps = steps.at[:, 0].set(z[:, 0] * sig0)
    x = jnp.cumsum(steps, axis=1)
    return x - x.mean(axis=0, keepdims=True)


def model(d, meta):
    T, P, S = meta["T"], meta["P"], meta["S"]
    new_season = jnp.asarray(meta["new_season"])

    alpha = numpyro.sample("alpha", dist.Normal(1.4, 0.5).expand([2]).to_event(1))
    beta = numpyro.sample("beta", dist.Normal(-1.0, 0.5).expand([2]).to_event(1))
    home = numpyro.sample("home", dist.Normal(0.15, 0.1))
    home_ghost = numpyro.sample("home_ghost", dist.Normal(0.0, 0.1))
    gamma_home = numpyro.sample("gamma_home", dist.Normal(0.0, 0.1))
    red_eff = numpyro.sample("red_eff", dist.Normal(0.2, 0.2))
    phi = numpyro.sample("phi", dist.LogNormal(3.0, 1.0))

    s_within = numpyro.sample("s_within", dist.HalfNormal(0.1))
    s_summer = numpyro.sample("s_summer", dist.HalfNormal(0.2))
    s_fin = numpyro.sample("s_fin", dist.HalfNormal(0.1))
    s0 = numpyro.sample("s0", dist.HalfNormal(0.4))
    s_fin0 = numpyro.sample("s_fin0", dist.HalfNormal(0.2))

    sig = s_within + (s_summer - s_within) * new_season
    att = random_walk("att", T, P, s0, sig)
    dfn = random_walk("def", T, P, s0, sig)
    sig_f = jnp.full(S, s_fin)
    fin = random_walk("fin", T, S, s_fin0, sig_f)
    keep = random_walk("keep", T, S, s_fin0, sig_f)

    h, a, per, sea, d2 = d["h"], d["a"], d["per"], d["sea"], d["d2"]
    hadv = home * (1 - d["ghost"]) + home_ghost * d["ghost"]
    eta_h = alpha[d2] + hadv + att[h, per] - dfn[a, per] + red_eff * (d["ar"] - d["hr"])
    eta_a = alpha[d2] + att[a, per] - dfn[h, per] + red_eff * (d["hr"] - d["ar"])
    lam_h = jnp.exp(jnp.clip(eta_h, -4.0, 5.0))   # numerical guard only
    lam_a = jnp.exp(jnp.clip(eta_a, -4.0, 5.0))
    p_h = jax.nn.sigmoid(beta[d2] + gamma_home + fin[h, sea] - keep[a, sea])
    p_a = jax.nn.sigmoid(beta[d2] + fin[a, sea] - keep[h, sea])

    has = d["has"]
    nb = lambda mu: dist.NegativeBinomial2(mu, phi)
    with numpyro.plate("matches", len(h)):
        with numpyro.handlers.mask(mask=has):
            numpyro.sample("hst", nb(lam_h), obs=d["hst"])
            numpyro.sample("ast", nb(lam_a), obs=d["ast"])
            numpyro.sample("hg_c", dist.Binomial(d["hst"], probs=p_h), obs=d["hg"])
            numpyro.sample("ag_c", dist.Binomial(d["ast"], probs=p_a), obs=d["ag"])
        with numpyro.handlers.mask(mask=~has):
            numpyro.sample("hg_m", nb(lam_h * p_h), obs=d["hg"])
            numpyro.sample("ag_m", nb(lam_a * p_a), obs=d["ag"])
    if meta.get("use_xg"):
        # xG ~ Gamma with mean psi * expected shots on target: more evidence on att/def, no new team parameters
        psi = numpyro.sample("psi", dist.LogNormal(jnp.log(0.32), 0.3))
        kappa = numpyro.sample("kappa", dist.Gamma(2.0, 0.5))
        with numpyro.plate("xg_matches", len(h)), numpyro.handlers.mask(mask=d["has_xg"]):
            numpyro.sample("xg_h", dist.Gamma(kappa, kappa / (psi * lam_h)), obs=d["xg_h"])
            numpyro.sample("xg_a", dist.Gamma(kappa, kappa / (psi * lam_a)), obs=d["xg_a"])


def reconstruct(samples, meta):
    """Rebuild the latent random walks from posterior draws of the innovations."""
    T, P, S = meta["T"], meta["P"], meta["S"]
    ns = jnp.asarray(meta["new_season"])

    def rw(z, s0, sig):
        steps = z * sig[:, None, :]
        steps = steps.at[:, :, 0].set(z[:, :, 0] * s0[:, None])
        x = jnp.cumsum(steps, axis=2)
        return x - x.mean(axis=1, keepdims=True)

    sig = samples["s_within"][:, None] + (samples["s_summer"] - samples["s_within"])[:, None] * ns[None, :]
    sig_f = jnp.repeat(samples["s_fin"][:, None], S, axis=1)
    return dict(
        att=np.asarray(rw(samples["z_att"], samples["s0"], sig)),
        def_=np.asarray(rw(samples["z_def"], samples["s0"], sig)),
        fin=np.asarray(rw(samples["z_fin"], samples["s_fin0"], sig_f)),
        keep=np.asarray(rw(samples["z_keep"], samples["s_fin0"], sig_f)),
    )


def fit(df, first_season, ref_date, warmup=500, samples=500, chains=2, seed=0, chain_method=None,
        max_tree_depth=10):
    # one GPU -> run chains vectorised on it; CPU -> one chain per core
    chain_method = chain_method or ("vectorized" if jax.default_backend() == "gpu" else "parallel")
    d, meta = build_data(df, first_season, ref_date)
    kernel = NUTS(model, target_accept_prob=0.85, max_tree_depth=max_tree_depth,
                  init_strategy=init_to_median(num_samples=15))
    mcmc = MCMC(kernel, num_warmup=warmup, num_samples=samples,
                num_chains=chains, chain_method=chain_method, progress_bar=False)
    mcmc.run(jax.random.PRNGKey(seed), d, meta, extra_fields=("num_steps", "diverging"))
    return mcmc, meta


def simulate_match(samples, states, meta, home_team, away_team, ref_date, n_per_draw=20, seed=1):
    """Posterior-predictive score distribution for a future 1. Bundesliga match.

    The future period's strengths = last observed period + one random-walk innovation, so
    parameter uncertainty AND drift since the last match are both carried into the forecast.
    """
    rng = np.random.default_rng(seed)
    tid = meta["tid"]
    ref = pd.Timestamp(ref_date)
    season = ref.year - (ref.month < 7)
    p_now = (season - meta["first_season"]) * PERIODS_PER_SEASON + int(period_of(ref.month))
    p_last = min(p_now, meta["P"] - 1)
    s_idx = min(season - meta["first_season"], meta["S"] - 1)
    h, a = tid[home_team], tid[away_team]
    n = len(samples["alpha"])
    # The forecast period (Oct-Dec 2026) has no matches yet, so its latent state is the
    # Jul-Sep state plus one posterior random-walk innovation: drift uncertainty is included.
    att, de, fin, keep = states["att"], states["def_"], states["fin"], states["keep"]
    lam_h = np.exp(samples["alpha"][:, 0] + samples["home"] + att[:, h, p_last] - de[:, a, p_last])
    lam_a = np.exp(samples["alpha"][:, 0] + att[:, a, p_last] - de[:, h, p_last])
    ph = 1 / (1 + np.exp(-(samples["beta"][:, 0] + samples["gamma_home"] + fin[:, h, s_idx] - keep[:, a, s_idx])))
    pa = 1 / (1 + np.exp(-(samples["beta"][:, 0] + fin[:, a, s_idx] - keep[:, h, s_idx])))
    phi = samples["phi"]

    def nb_draw(mu):
        g = rng.gamma(np.repeat(phi, n_per_draw), np.repeat(mu / phi, n_per_draw))
        return rng.poisson(g)

    sot_h, sot_a = nb_draw(lam_h), nb_draw(lam_a)
    g_h = rng.binomial(sot_h, np.repeat(ph, n_per_draw))
    g_a = rng.binomial(sot_a, np.repeat(pa, n_per_draw))
    return dict(lam_sot_h=lam_h, lam_sot_a=lam_a, p_h=ph, p_a=pa,
                xg_h=lam_h * ph, xg_a=lam_a * pa, sot_h=sot_h, sot_a=sot_a, g_h=g_h, g_a=g_a)


def predict_matrix(samples, states, meta, home_team, away_team, date, maxg=11, thin=4):
    """Exact posterior-predictive score matrix: goals = Binomial thinning of NegBin shots on target
    => goals ~ NegBin(mean = lam * p, conc = phi); averaged over posterior draws."""
    from scipy.stats import nbinom
    tid = meta["tid"]
    ref = pd.Timestamp(date)
    season = ref.year - (ref.month < 7)
    p_now = min((season - meta["first_season"]) * PERIODS_PER_SEASON + int(period_of(ref.month)), meta["P"] - 1)
    s_idx = min(season - meta["first_season"], meta["S"] - 1)
    sl = slice(None, None, thin)
    al, be = samples["alpha"][sl, 0], samples["beta"][sl, 0]
    att, de = states["att"][sl], states["def_"][sl]
    fin, keep = states["fin"][sl], states["keep"][sl]
    phi = samples["phi"][sl]
    out = np.zeros((maxg, maxg))
    if home_team not in tid or away_team not in tid:
        return None
    h, a = tid[home_team], tid[away_team]
    lam_h = np.exp(al + samples["home"][sl] + att[:, h, p_now] - de[:, a, p_now])
    lam_a = np.exp(al + att[:, a, p_now] - de[:, h, p_now])
    ph = 1 / (1 + np.exp(-(be + samples["gamma_home"][sl] + fin[:, h, s_idx] - keep[:, a, s_idx])))
    pa = 1 / (1 + np.exp(-(be + fin[:, a, s_idx] - keep[:, h, s_idx])))
    g = np.arange(maxg)
    mh, ma = lam_h * ph, lam_a * pa
    fh = nbinom.pmf(g[None, :], phi[:, None], (phi / (phi + mh))[:, None])
    fa = nbinom.pmf(g[None, :], phi[:, None], (phi / (phi + ma))[:, None])
    out = np.einsum("ni,nj->ij", fh, fa) / len(phi)
    return out / out.sum()
