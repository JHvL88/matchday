/*
 * The season simulator in the browser: the same model as analysis/pipeline/season_sim.py, for the
 * "what if" picks and for re-simulating with results that came in after the last published run.
 *
 *   SeasonSim.run({ teams, table, fixtures, ratings, sigma, n, seed, fixed })
 *     teams     team ids, in any order
 *     table     { id: [points, goal difference, goals for] } before the fixtures below
 *     fixtures  [{ home, away }] still to play
 *     ratings   { mu, home, rho, att: { id }, de: { id } }:
 *               log lambda_home = mu + home + att[h] - de[a], log lambda_away = mu + att[a] - de[h]
 *     sigma     doubt: each simulated season nudges every club by N(0, sigma^2) on attack and defence
 *     fixed     { fixture index: [home goals, away goals] or "H" | "D" | "A" }
 *   returns { n, teams, pos (counts, team-major: pos[t * T + place]), pts (sum of final points) }
 *
 * Every random number comes from a stream keyed by (seed, season, fixture) or (seed, season, club), so
 * two runs with the same seed differ only where their picks differ: the comparison "before / after your
 * picks" shows the picks, not the dice. Loaded as a plain script by the page and by worker.js.
 */
(function (root) {
  "use strict";

  let state = 0;

  // mulberry32: small, fast, good enough for dice.
  function uniform() {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  function mix(a, b, c) {
    let h = (a ^ Math.imul(b + 1, 0x9e3779b1) ^ Math.imul(c + 1, 0x85ebca77)) | 0;
    h = Math.imul(h ^ (h >>> 16), 0x7feb352d);
    h = Math.imul(h ^ (h >>> 15), 0x846ca68b);
    return (h ^ (h >>> 16)) | 0;
  }

  function stream(seed, season, slot) {
    state = mix(seed, season, slot);
  }

  function normal() {
    const u = uniform() || 1e-12;
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * uniform());
  }

  // Knuth's method: fine for the rates of football (well under 10 goals).
  function poisson(lambda) {
    const limit = Math.exp(-lambda);
    let k = 0;
    let p = uniform();
    while (p > limit) {
      k += 1;
      p *= uniform();
    }
    return k;
  }

  // Dixon–Coles scoreline: two Poisson draws, then the low-score correction moves the same small
  // amount of probability between 0-0, 0-1, 1-0 and 1-1 that the model's tau does (exact).
  function score(lh, la, rho) {
    const x = poisson(lh);
    let y = poisson(la);
    if (rho < 0) {
      if (x === 0 && y === 1 && uniform() < -rho * lh) y = 0;
      else if (x === 1 && y === 0 && uniform() < -rho * la) y = 1;
    } else if (rho > 0) {
      if (x === 0 && y === 0 && uniform() < rho * lh * la) y = 1;
      else if (x === 1 && y === 1 && uniform() < rho) y = 0;
    }
    return [x, y];
  }

  function outcomeOf(x, y) {
    return x > y ? "H" : x === y ? "D" : "A";
  }

  function run({ teams, table, fixtures, ratings, sigma = 0, n = 20000, seed = 1, fixed = {} }) {
    const T = teams.length;
    const index = new Map(teams.map((id, i) => [String(id), i]));
    const R = fixtures.length;
    const hi = new Int32Array(R);
    const ai = new Int32Array(R);
    const baseH = new Float64Array(R);
    const baseA = new Float64Array(R);
    fixtures.forEach((f, r) => {
      const h = String(f.home);
      const a = String(f.away);
      hi[r] = index.get(h);
      ai[r] = index.get(a);
      baseH[r] = ratings.mu + ratings.home + ratings.att[h] - ratings.de[a];
      baseA[r] = ratings.mu + ratings.att[a] - ratings.de[h];
    });
    const pts0 = new Float64Array(T);
    const gd0 = new Float64Array(T);
    const gf0 = new Float64Array(T);
    teams.forEach((id, i) => {
      const row = table[String(id)] ?? [0, 0, 0];
      pts0[i] = row[0];
      gd0[i] = row[1];
      gf0[i] = row[2];
    });
    const fixedAt = new Map(Object.entries(fixed).map(([k, v]) => [Number(k), v]));
    const pos = new Float64Array(T * T);
    const ptsSum = new Float64Array(T);
    const delta = new Float64Array(T);
    const pts = new Float64Array(T);
    const gd = new Float64Array(T);
    const gf = new Float64Array(T);
    const key = new Float64Array(T);
    const order = Array.from({ length: T }, (_, i) => i);
    const byKey = (a, b) => key[b] - key[a];

    for (let s = 0; s < n; s += 1) {
      for (let t = 0; t < T; t += 1) {
        stream(seed, s, 100000 + t);
        delta[t] = sigma > 0 ? sigma * normal() : 0;
        pts[t] = pts0[t];
        gd[t] = gd0[t];
        gf[t] = gf0[t];
      }
      for (let r = 0; r < R; r += 1) {
        const h = hi[r];
        const a = ai[r];
        let x;
        let y;
        const pick = fixedAt.get(r);
        if (Array.isArray(pick)) {
          [x, y] = pick;
        } else {
          stream(seed, s, r);
          const lh = Math.exp(baseH[r] + delta[h] - delta[a]);
          const la = Math.exp(baseA[r] + delta[a] - delta[h]);
          let tries = 0;
          do {
            [x, y] = score(lh, la, ratings.rho);
            tries += 1;
          } while (pick && outcomeOf(x, y) !== pick && tries < 5000);
          if (pick && outcomeOf(x, y) !== pick) [x, y] = pick === "H" ? [1, 0] : pick === "A" ? [0, 1] : [1, 1];
        }
        if (x > y) pts[h] += 3;
        else if (x < y) pts[a] += 3;
        else {
          pts[h] += 1;
          pts[a] += 1;
        }
        gd[h] += x - y;
        gd[a] += y - x;
        gf[h] += x;
        gf[a] += y;
      }
      stream(seed, s, 999999);
      for (let t = 0; t < T; t += 1) {
        key[t] = pts[t] * 1e7 + (gd[t] + 1000) * 1e3 + gf[t] + uniform() * 0.5;
        ptsSum[t] += pts[t];
      }
      order.sort(byKey);
      for (let place = 0; place < T; place += 1) pos[order[place] * T + place] += 1;
    }
    return { n, teams: teams.map(String), pos, pts: ptsSum };
  }

  // Chances of the page's outcomes from one run (positions are 1-based in the ranges).
  const OUTCOMES = { title: [1, 1], top4: [1, 4], europe: [1, 6], playoff: [16, 16], drop: [17, 18] };

  function summarise(result) {
    const T = result.teams.length;
    const out = {};
    result.teams.forEach((id, t) => {
      const row = result.pos.subarray(t * T, t * T + T);
      const total = row.reduce((sum, v) => sum + v, 0) || 1;
      const p = {};
      for (const [name, [lo, hi]] of Object.entries(OUTCOMES)) {
        let c = 0;
        for (let place = lo - 1; place < hi; place += 1) c += row[place];
        p[name] = c / total;
      }
      let xpos = 0;
      row.forEach((v, place) => { xpos += (place + 1) * v; });
      out[id] = { p, pos: Array.from(row, (v) => v / total), xpts: result.pts[t] / result.n, xpos: xpos / total };
    });
    return out;
  }

  root.SeasonSim = { run, summarise, OUTCOMES };
})(typeof globalThis !== "undefined" ? globalThis : self);
