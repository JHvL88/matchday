/*
 * The Track record page: every published forecast graded against the bookmakers, the season and
 * backtest figures, the disagreement check and the paper-betting ledger.
 * Data: ../data/forecasts.json (the weekly forecasts), ../data/odds.json (bookmakers' odds),
 * ../analysis/posts.json (deep dives), ../data/record.json (notebook figures) and OpenLigaDB for
 * final scores. Loaded after i18n.js, glossary.js and explain.js.
 */
(() => {
  "use strict";

  const I18N = window.I18N;
  const API = "https://api.openligadb.de";
  const TIME_ZONE = "Europe/Berlin";

  const WORDS = {
    en: {
      matchday: "Matchday {n}",
      weeklyTitle: "Weekly forecasts on this site",
      weeklyNoneSub: "All nine matches of a matchday. The first grades arrive after full time on {date}.",
      weeklySub: { one: "{graded} graded forecast · models closer in {won} of {graded}", other: "{graded} graded forecasts · models closer in {won} of {graded}" },
      weekPublished: { one: "Published {date} · {count} match", other: "Published {date} · {count} matches" },
      weekOpen: "Not played yet",
      weekUnderway: "Under way, no final score yet",
      weekPartly: "{graded} of {count} graded",
      weekCloser: "Models closer in {won} of {graded}",
      weekRps: "RPS {models} v {market}",
      weeklyEmpty: "No weekly forecast has been published yet.",
      bookiesSplit: "Bookmakers {h} / {d} / {a}",
      noMarket: "No bookmakers’ odds recorded",
      barLabel: "My models: home win {mh}, draw {md}, away win {ma}. Bookmakers: {bh}, {bd}, {ba}.",
      barLabelModels: "My models: home win {mh}, draw {md}, away win {ma}.",
      deepDive: "Deep dive",
      divesTitle: "Deep dives on this site",
      divesNone: "No result yet",
      divesNoneSub: "The first grade arrives after full time on {date}.",
      divesSub: { one: "{graded} graded forecast · models closer in {won} of {graded}", other: "{graded} graded forecasts · models closer in {won} of {graded}" },
      seasonTitle: "This season, every match",
      seasonSub: "{count} matches · {who}",
      longTitle: "The long run",
      longSub: "{count} matches in the backtest · 95% interval of the gap {low} to {high}",
      modelsAhead: "models ahead, for now",
      marketAhead: "bookmakers ahead",
      models: "My models",
      bookies: "Bookmakers",
      vs: "v",
      gapModels: "Models ahead by {gap}",
      gapMarket: "Bookmakers ahead by {gap}",
      forecast: "Forecast",
      result: "Result",
      grade: "Grade",
      pending: "Kick-off {when}",
      awaiting: "Awaiting the final score",
      loading: "Fetching the final score…",
      unknown: "Score not available right now",
      closerModels: "Models closer",
      closerMarket: "Bookmakers closer",
      level: "Level",
      home: "Home",
      draw: "Draw",
      away: "Away",
      read: "Read the deep dive",
      ensembleRow: "Ensemble",
      ensembleSub: "{count} matches since 2019/20",
      modelsSaid: "Models said",
      marketSaid: "Bookmakers said",
      happened: "Actually happened",
      axis: "How often the bookmakers’ favourite won, when the models were 7+ points less sure",
      disagreeLine: "{models} from the models, {market} from the bookmakers, {actual} in reality.",
      forecaster: "Forecaster",
      rps: "RPS",
      vsMarket: "v bookmakers",
      logLoss: "Log loss",
      topPick: "Top pick right",
      rowNames: { market: "Bookmakers", ensemble: "Ensemble (published)", dixonColes: "Dixon–Coles", bayesian: "Bayesian shots-to-goals", xgboost: "XGBoost" },
      asOf: "Backtest as of {date}, {label}.",
      paperProgress: "{graded} of {needed} deep dives graded",
      paperHidden: "Profit and loss appear after {needed} graded deep dives.",
      paperTotal: "{count} bets settled · {pl} on {stake} staked",
      bet: "€1 on {pick} at {odds}",
      noBet: "No bet: the biggest gap was {gap} points ({pick}).",
      betWhy: "models {model}, market {market}",
      betPending: "open",
      betWon: "won {amount}",
      betLost: "lost {amount}",
      clv: "CLV {value}",
      clvTitle: "Closing-line value: what this bet was worth at the market-average closing odds, margin removed. Positive means a better price than the market settled on.",
      clvAverage: "average CLV {value}",
      teamWin: "{team} win",
      theDraw: "the draw",
      loadError: "The track record could not be loaded. Try again in a moment.",
    },
    de: {
      matchday: "Spieltag {n}",
      weeklyTitle: "Wochenprognosen auf dieser Seite",
      weeklyNoneSub: "Alle neun Spiele eines Spieltags. Die ersten Bewertungen gibt es nach dem Abpfiff am {date}.",
      weeklySub: { one: "{graded} bewertete Prognose · Modelle {won}-mal von {graded} näher dran", other: "{graded} bewertete Prognosen · Modelle {won}-mal von {graded} näher dran" },
      weekPublished: { one: "Veröffentlicht am {date} · {count} Spiel", other: "Veröffentlicht am {date} · {count} Spiele" },
      weekOpen: "Noch nicht gespielt",
      weekUnderway: "Läuft, noch kein Endergebnis",
      weekPartly: "{graded} von {count} bewertet",
      weekCloser: "Modelle {won}-mal von {graded} näher dran",
      weekRps: "RPS {models} gegen {market}",
      weeklyEmpty: "Noch ist keine Wochenprognose veröffentlicht.",
      bookiesSplit: "Buchmacher {h} / {d} / {a}",
      noMarket: "Keine Buchmacherquoten aufgezeichnet",
      barLabel: "Meine Modelle: Heimsieg {mh}, Remis {md}, Auswärtssieg {ma}. Buchmacher: {bh}, {bd}, {ba}.",
      barLabelModels: "Meine Modelle: Heimsieg {mh}, Remis {md}, Auswärtssieg {ma}.",
      deepDive: "Zur Analyse",
      divesTitle: "Analysen auf dieser Seite",
      divesNone: "Noch kein Ergebnis",
      divesNoneSub: "Die erste Bewertung gibt es nach dem Abpfiff am {date}.",
      divesSub: { one: "{graded} bewertete Prognose · Modelle {won}-mal von {graded} näher dran", other: "{graded} bewertete Prognosen · Modelle {won}-mal von {graded} näher dran" },
      seasonTitle: "Diese Saison, jedes Spiel",
      seasonSub: "{count} Spiele · {who}",
      longTitle: "Auf lange Sicht",
      longSub: "{count} Spiele im Backtest · 95-%-Intervall des Abstands {low} bis {high}",
      modelsAhead: "Modelle vorn, vorerst",
      marketAhead: "Buchmacher vorn",
      models: "Meine Modelle",
      bookies: "Buchmacher",
      vs: "gegen",
      gapModels: "Modelle vorn um {gap}",
      gapMarket: "Buchmacher vorn um {gap}",
      forecast: "Prognose",
      result: "Ergebnis",
      grade: "Bewertung",
      pending: "Anstoß {when}",
      awaiting: "Endergebnis steht noch aus",
      loading: "Endergebnis wird geladen …",
      unknown: "Ergebnis gerade nicht abrufbar",
      closerModels: "Modelle näher dran",
      closerMarket: "Buchmacher näher dran",
      level: "Gleichauf",
      home: "Heim",
      draw: "Remis",
      away: "Auswärts",
      read: "Zur Analyse",
      ensembleRow: "Ensemble",
      ensembleSub: "{count} Spiele seit 2019/20",
      modelsSaid: "Modelle sagten",
      marketSaid: "Buchmacher sagten",
      happened: "Tatsächlich passiert",
      axis: "Wie oft der Favorit der Buchmacher gewann, wenn die Modelle 7+ Punkte weniger sicher waren",
      disagreeLine: "{models} laut Modellen, {market} laut Buchmachern, {actual} in der Realität.",
      forecaster: "Prognose von",
      rps: "RPS",
      vsMarket: "gegen Buchmacher",
      logLoss: "Log-Loss",
      topPick: "Top-Tipp richtig",
      rowNames: { market: "Buchmacher", ensemble: "Ensemble (veröffentlicht)", dixonColes: "Dixon–Coles", bayesian: "Bayesianisches Schüsse-zu-Toren-Modell", xgboost: "XGBoost" },
      asOf: "Backtest mit Stand {date}, {label}.",
      paperProgress: "{graded} von {needed} Analysen bewertet",
      paperHidden: "Gewinn und Verlust erscheinen nach {needed} bewerteten Analysen.",
      paperTotal: "{count} Wetten abgerechnet · {pl} bei {stake} Einsatz",
      bet: "1 € auf {pick} zu {odds}",
      noBet: "Keine Wette: Der größte Abstand waren {gap} Punkte ({pick}).",
      betWhy: "Modelle {model}, Markt {market}",
      betPending: "offen",
      betWon: "gewonnen {amount}",
      betLost: "verloren {amount}",
      clv: "CLV {value}",
      clvTitle: "Closing Line Value: was diese Wette zu den durchschnittlichen Schlussquoten wert war, Marge herausgerechnet. Positiv heißt: ein besserer Preis als der, auf den sich der Markt am Ende einigte.",
      clvAverage: "CLV im Schnitt {value}",
      teamWin: "Sieg {team}",
      theDraw: "Remis",
      loadError: "Die Bilanz konnte nicht geladen werden. Bitte gleich noch einmal versuchen.",
    },
  };

  const state = {
    posts: [], record: null, forecasts: null, odds: null,
    results: new Map(), resultsLoaded: false, weeksLoaded: false, failed: false,
    openWeeks: null, // which matchdays of the weekly list are unfolded; null until first drawn
  };

  function say(key, params = {}) {
    let entry = WORDS[I18N.lang]?.[key] ?? WORDS.en[key];
    if (entry && typeof entry === "object") entry = entry[new Intl.PluralRules(I18N.locale).select(Number(params.count ?? params.graded))] ?? entry.other;
    return String(entry).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const num = (value, digits) => I18N.number(value, digits);
  const signed = (value, digits) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${num(Math.abs(value), digits)}`;
  const pct = (value) => I18N.percent(value);
  const signedPct = (value) => new Intl.NumberFormat(I18N.locale, { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" }).format(value);
  // Closing-line value: what a bet at these odds was worth at the margin-free closing price.
  function clvOf(odds, closing, index) {
    if (!odds || !Array.isArray(closing) || closing.length !== 3) return null;
    const inverse = closing.map((price) => 1 / price);
    const total = inverse.reduce((sum, value) => sum + value, 0);
    return odds * (inverse[index] / total) - 1;
  }
  const euro = (value, sign = false) => new Intl.NumberFormat(I18N.locale, { style: "currency", currency: "EUR", signDisplay: sign ? "exceptZero" : "auto" }).format(value);
  const when = (iso, options) => I18N.dateFormat(iso, { timeZone: TIME_ZONE, ...options });

  const whole = (p) => num(p * 100, 0);

  // Odds to probabilities, the margin removed proportionally (the same sum as on the home page).
  function marginFree(odds) {
    if (!Array.isArray(odds) || odds.length !== 3 || odds.some((value) => !(Number(value) > 1))) return null;
    const inverse = odds.map((value) => 1 / Number(value));
    const total = inverse.reduce((sum, value) => sum + value, 0);
    return inverse.map((value) => value / total);
  }

  function rps(probs, outcome) {
    let forecast = 0;
    let actual = 0;
    let total = 0;
    for (let index = 0; index < 2; index += 1) {
      forecast += probs[index];
      actual += index === outcome ? 1 : 0;
      total += (forecast - actual) ** 2;
    }
    return total / 2;
  }

  // OpenLigaDB: resultTypeID 2 is the final score.
  function finalScore(match) {
    if (!match?.matchIsFinished) return null;
    const results = Array.isArray(match.matchResults) ? match.matchResults : [];
    const final = results.find((item) => Number(item.resultTypeID) === 2)
      ?? [...results].sort((a, b) => b.resultOrderID - a.resultOrderID)[0];
    return final ? [Number(final.pointsTeam1), Number(final.pointsTeam2)] : null;
  }

  function grade(post) {
    const f = post.forecast ?? {};
    const kickoff = new Date(post.kickoff);
    const entry = {
      post, matchday: post.matchday, home: post.home.name, away: post.away.name, link: `../${post.path}`,
      model: f.model, market: f.market, odds: f.marketOdds ?? null, closing: post.closing?.odds ?? null, kickoff, status: "pending", score: null,
    };
    if (Date.now() < kickoff.getTime()) return entry;
    // The post's own full-time numbers win; otherwise the score comes from OpenLigaDB.
    const known = post.fullTime?.score;
    let score = Array.isArray(known) ? known : null;
    if (!score) {
      if (!state.resultsLoaded) return { ...entry, status: "loading" };
      const match = state.results.get(Number(post.matchId));
      if (match === undefined) return { ...entry, status: "unknown" };
      score = finalScore(match);
      if (!score) return { ...entry, status: "awaiting" };
    }
    const outcome = score[0] > score[1] ? 0 : score[0] === score[1] ? 1 : 2;
    const published = post.fullTime?.rps;
    return {
      ...entry,
      status: "graded",
      score,
      outcome,
      models: published?.models ?? rps(f.model, outcome),
      marketScore: published?.market ?? rps(f.market, outcome),
    };
  }

  // A weekly forecast: the models as published, against the bookmakers' average odds as last recorded
  // before kick-off (the price stored with the forecast if the odds file has none). The home page
  // grades with the same two numbers.
  function gradeWeekly(matchday, id, forecast) {
    const kickoff = new Date(forecast.kickoff);
    const market = marginFree(state.odds?.matchdays?.[matchday]?.matches?.[id]) ?? marginFree(forecast.market?.odds);
    const post = state.posts.find((item) => Number(item.matchId) === Number(id));
    const entry = {
      matchday: Number(matchday), home: forecast.home, away: forecast.away, dive: post ? `../${post.path}` : null,
      model: forecast.model, market, kickoff, status: "pending", score: null,
    };
    if (Date.now() < kickoff.getTime()) return entry;
    if (!state.weeksLoaded) return { ...entry, status: "loading" };
    const match = state.results.get(Number(id));
    if (match === undefined) return { ...entry, status: "unknown" };
    const score = finalScore(match);
    if (!score) return { ...entry, status: "awaiting" };
    const outcome = score[0] > score[1] ? 0 : score[0] === score[1] ? 1 : 2;
    const graded = { ...entry, score, outcome, models: rps(forecast.model, outcome) };
    // Without a bookmakers' price there is a result but nothing to compare it with.
    return market ? { ...graded, status: "graded", marketScore: rps(market, outcome) } : { ...graded, status: "scored" };
  }

  function weeks() {
    const days = state.forecasts?.matchdays ?? {};
    return Object.keys(days).map(Number).sort((a, b) => b - a).map((matchday) => {
      const block = days[String(matchday)];
      const entries = Object.entries(block.matches ?? {})
        .map(([id, forecast]) => gradeWeekly(String(matchday), id, forecast))
        .sort((a, b) => a.kickoff - b.kickoff || a.home.localeCompare(b.home));
      return { matchday, published: block.published, entries };
    });
  }

  function pickLabel(post, index) {
    if (index === 1) return say("theDraw");
    return say("teamWin", { team: (index === 0 ? post.home : post.away).name });
  }

  /* ---------- The score ---------- */

  function card(title, value, sub, className = "") {
    const box = element("div", `score-card ${className}`.trim());
    box.append(element("p", "score-card-title", title), value, element("p", "score-card-sub", sub));
    return box;
  }

  function versus(models, market, digits) {
    const line = element("p", "score-card-value");
    const left = element("span", `score-side${models < market ? " is-ahead" : ""}`);
    left.append(element("span", "score-who", say("models")), element("span", "score-num", num(models, digits)));
    const right = element("span", `score-side${market < models ? " is-ahead" : ""}`);
    right.append(element("span", "score-who", say("bookies")), element("span", "score-num", num(market, digits)));
    line.append(left, element("span", "score-vs", say("vs")), right);
    return line;
  }

  const mean = (entries, key) => entries.reduce((sum, entry) => sum + entry[key], 0) / entries.length;

  function renderScore(entries, weekEntries) {
    const box = document.getElementById("score-cards");
    if (!box) return;
    const cards = [];
    const weekly = weekEntries.filter((entry) => entry.status === "graded");
    if (weekly.length) {
      cards.push(card(say("weeklyTitle"), versus(mean(weekly, "models"), mean(weekly, "marketScore"), 3),
        say("weeklySub", { graded: weekly.length, won: weekly.filter((entry) => entry.models < entry.marketScore).length }), "is-live"));
    } else if (weekEntries.length) {
      const first = [...weekEntries].sort((a, b) => a.kickoff - b.kickoff)[0];
      cards.push(card(say("weeklyTitle"), element("p", "score-card-value is-empty", say("divesNone")),
        say("weeklyNoneSub", { date: when(first.kickoff, { weekday: "long", day: "numeric", month: "long" }) }), "is-live"));
    }
    const graded = entries.filter((entry) => entry.status === "graded");
    if (graded.length) {
      const won = graded.filter((entry) => entry.models < entry.marketScore).length;
      cards.push(card(say("divesTitle"), versus(mean(graded, "models"), mean(graded, "marketScore"), 3), say("divesSub", { graded: graded.length, won }), "is-live"));
    } else {
      const next = entries.filter((entry) => entry.status === "pending").sort((a, b) => a.kickoff - b.kickoff)[0];
      cards.push(card(say("divesTitle"), element("p", "score-card-value is-empty", say("divesNone")),
        next ? say("divesNoneSub", { date: when(next.kickoff, { weekday: "long", day: "numeric", month: "long" }) }) : "", "is-live"));
    }
    const record = state.record;
    if (record?.season) {
      const s = record.season;
      cards.push(card(say("seasonTitle"), versus(s.models, s.market, 4), say("seasonSub", { count: num(s.matches, 0), who: say(s.models < s.market ? "modelsAhead" : "marketAhead") })));
    }
    const bt = record?.backtest;
    const market = bt?.rows?.find((row) => row.key === "market");
    const ensemble = bt?.rows?.find((row) => row.key === "ensemble");
    if (market && ensemble) {
      cards.push(card(say("longTitle"), versus(ensemble.rps, market.rps, 4),
        say("longSub", { count: num(bt.matches, 0), low: signed(bt.gapLow, 4), high: signed(bt.gapHigh, 4) })));
    }
    box.replaceChildren(...cards);
    box.removeAttribute("aria-busy");
  }

  /* ---------- The two lists: every weekly forecast, every deep dive ---------- */

  // The site's forecast bar: filled segments are my models, the two pins the bookmakers' split.
  function pinBar(entry) {
    const bar = element("span", "pbar");
    bar.setAttribute("role", "img");
    const [mh, md, ma] = entry.model.map(pct);
    const [bh, bd, ba] = (entry.market ?? []).map(pct);
    bar.setAttribute("aria-label", entry.market ? say("barLabel", { mh, md, ma, bh, bd, ba }) : say("barLabelModels", { mh, md, ma }));
    const track = element("span", "pbar-track");
    ["home", "draw", "away"].forEach((key, index) => {
      const segment = element("span", `pbar-seg is-${key}`);
      if (index < 2) segment.style.width = `${Math.max(0, entry.model[index] * 100).toFixed(1)}%`;
      track.append(segment);
    });
    bar.append(track);
    if (entry.market) {
      [entry.market[0], entry.market[0] + entry.market[1]].forEach((cut) => {
        const pin = element("span", "pbar-pin");
        pin.style.left = `${(cut * 100).toFixed(1)}%`;
        bar.append(pin);
      });
    }
    return bar;
  }

  function row(entry, { day = true } = {}) {
    const item = element("article", `ledger-row is-${entry.status}`);
    const meta = element("div", "ledger-meta");
    if (day) {
      meta.append(element("p", "ledger-day", `${say("matchday", { n: entry.matchday })} · ${when(entry.kickoff, { weekday: "short", day: "numeric", month: "short" })}`));
    }
    const title = element("h3", "ledger-match");
    const names = `${entry.home} – ${entry.away}`;
    if (entry.link) {
      const link = element("a", "", names);
      link.href = entry.link;
      title.append(link);
    } else {
      title.textContent = names;
    }
    meta.append(title);
    if (entry.dive) {
      const more = element("a", "ledger-dive", say("deepDive"));
      more.href = entry.dive;
      meta.append(more);
    }

    const forecast = element("div", "ledger-forecast");
    const numbers = element("p", "ledger-nums");
    [say("home"), say("draw"), say("away")].forEach((label, index) => {
      const hit = entry.outcome === undefined ? "" : index === entry.outcome ? "is-hit" : "is-miss";
      const part = element("span", hit);
      part.append(`${label} `, element("strong", "", pct(entry.model[index])));
      numbers.append(part);
    });
    const [h, d, a] = (entry.market ?? []).map(whole);
    forecast.append(pinBar(entry), numbers, element("p", "ledger-market", entry.market ? say("bookiesSplit", { h, d, a }) : say("noMarket")));

    const result = element("div", "ledger-result");
    if (entry.score) result.append(element("p", "ledger-score", I18N.score(entry.score[0], entry.score[1])));
    if (entry.status === "graded") {
      const verdict = entry.models < entry.marketScore ? "closerModels" : entry.models > entry.marketScore ? "closerMarket" : "level";
      const line = element("p", "ledger-verdict");
      // Solid for my models, outline for the bookmakers: the same rule as the bars.
      line.append(element("span", `pill${verdict === "closerModels" ? " is-solid" : ""}`, say(verdict)));
      result.append(line);
      result.append(element("p", "ledger-grades", say("weekRps", { models: num(entry.models, 3), market: num(entry.marketScore, 3) })));
    } else if (entry.status !== "scored") {
      const text = entry.status === "pending"
        ? say("pending", { when: when(entry.kickoff, { weekday: "short", hour: "2-digit", minute: "2-digit" }) })
        : say(entry.status);
      result.append(element("p", "ledger-waiting", text));
    }
    item.append(meta, forecast, result);
    return item;
  }

  function renderWeeks(list) {
    const box = document.getElementById("weekly-list");
    if (!box) return;
    if (!list.length) {
      box.replaceChildren(element("p", "ledger-waiting", say("weeklyEmpty")));
      box.removeAttribute("aria-busy");
      return;
    }
    // The newest matchday starts unfolded; after that the reader's own choice is kept.
    if (!state.openWeeks) state.openWeeks = new Set([list[0].matchday]);
    const blocks = list.map(({ matchday, published, entries }) => {
      const block = element("details", "week");
      block.open = state.openWeeks.has(matchday);
      block.addEventListener("toggle", () => {
        if (block.open) state.openWeeks.add(matchday);
        else state.openWeeks.delete(matchday);
      });
      const head = element("summary", "week-head");
      const name = element("span", "week-name");
      name.append(
        element("span", "week-title", say("matchday", { n: matchday })),
        element("span", "week-sub", say("weekPublished", { date: when(published, { day: "numeric", month: "long" }), count: entries.length })),
      );
      const graded = entries.filter((entry) => entry.status === "graded");
      const tally = element("span", "week-tally");
      if (graded.length) {
        const won = graded.filter((entry) => entry.models < entry.marketScore).length;
        tally.append(
          element("span", "week-closer", say("weekCloser", { won, graded: graded.length })),
          element("span", "week-rps", `${graded.length < entries.length ? `${say("weekPartly", { graded: graded.length, count: entries.length })} · ` : ""}${say("weekRps", { models: num(mean(graded, "models"), 3), market: num(mean(graded, "marketScore"), 3) })}`),
        );
      } else {
        tally.append(element("span", "week-rps", say(entries.some((entry) => entry.status !== "pending") ? "weekUnderway" : "weekOpen")));
      }
      head.append(name, tally);
      const rows = element("div", "ledger");
      rows.append(...entries.map((entry) => row(entry, { day: false })));
      block.append(head, rows);
      return block;
    });
    box.replaceChildren(...blocks);
    box.removeAttribute("aria-busy");
  }

  function renderLedger(entries) {
    const box = document.getElementById("ledger-list");
    if (!box) return;
    box.replaceChildren(...entries.map((entry) => row(entry)));
    box.removeAttribute("aria-busy");
  }

  /* ---------- When they disagree ---------- */

  function renderDisagree() {
    const box = document.getElementById("disagree-chart");
    const rows = state.record?.disagreement;
    if (!box || !rows?.length) return;
    const all = rows.flatMap((row) => [row.models, row.market, row.actual]);
    const low = Math.floor((Math.min(...all) - 0.03) * 20) / 20;
    const high = Math.ceil((Math.max(...all) + 0.03) * 20) / 20;
    const x = (value) => `${((value - low) / (high - low)) * 100}%`;
    const list = element("div", "disagree-rows");
    for (const row of rows) {
      const item = element("div", "disagree-row");
      const label = element("div", "disagree-label");
      label.append(element("span", "disagree-name", say(`${row.key}Row`)), element("span", "disagree-sub", say(`${row.key}Sub`, { count: num(row.matches, 0) })));
      const track = element("div", "disagree-track");
      track.setAttribute("role", "img");
      track.setAttribute("aria-label", say("disagreeLine", { models: pct(row.models), market: pct(row.market), actual: pct(row.actual) }));
      const span = element("span", "disagree-span");
      span.style.left = x(Math.min(row.models, row.market, row.actual));
      span.style.right = `calc(100% - ${x(Math.max(row.models, row.market, row.actual))})`;
      track.append(span);
      for (const [key, value] of [["models", row.models], ["market", row.market], ["actual", row.actual]]) {
        const dot = element("span", `disagree-dot is-${key}`);
        dot.style.left = x(value);
        dot.title = pct(value);
        track.append(dot);
      }
      const values = element("p", "disagree-values", say("disagreeLine", { models: pct(row.models), market: pct(row.market), actual: pct(row.actual) }));
      item.append(label, track, values);
      list.append(item);
    }
    const axis = element("div", "disagree-axis");
    for (let value = low; value <= high + 1e-9; value += 0.05) {
      const tick = element("span", "", pct(value));
      tick.style.left = x(value);
      axis.append(tick);
    }
    const legend = element("p", "disagree-legend");
    for (const [key, text] of [["models", "modelsSaid"], ["market", "marketSaid"], ["actual", "happened"]]) {
      const entry = element("span");
      entry.append(element("span", `disagree-dot is-${key} is-key`), say(text));
      legend.append(entry);
    }
    box.replaceChildren(list, axis, element("p", "disagree-caption", say("axis")), legend);
  }

  /* ---------- The backtest ---------- */

  function renderBacktest() {
    const box = document.getElementById("backtest-table");
    const bt = state.record?.backtest;
    if (!box || !bt?.rows?.length) return;
    const market = bt.rows.find((row) => row.key === "market");
    const scroll = element("div", "table-scroll");
    const table = element("table", "post-table wide");
    const head = element("tr");
    for (const label of [say("forecaster"), say("rps"), say("vsMarket"), say("logLoss"), say("topPick")]) head.append(element("th", "", label));
    const thead = element("thead");
    thead.append(head);
    const body = element("tbody");
    for (const row of bt.rows) {
      const tr = element("tr", row.key === "ensemble" ? "is-key" : "");
      const names = WORDS[I18N.lang]?.rowNames ?? WORDS.en.rowNames;
      tr.append(
        element("td", "", names[row.key] ?? row.key),
        element("td", "", num(row.rps, 4)),
        element("td", "", row.key === "market" || !market ? "–" : signed(row.rps - market.rps, 4)),
        element("td", "", num(row.logLoss, 3)),
        element("td", "", pct(row.topPick)),
      );
      body.append(tr);
    }
    table.append(thead, body);
    scroll.append(table);
    const note = element("p", "calc-fine", say("asOf", { date: when(`${state.record.asOf}T12:00:00Z`, { day: "numeric", month: "long", year: "numeric" }), label: typeof bt.label === "string" ? bt.label : (bt.label?.[I18N.lang] ?? bt.label?.en) }));
    box.replaceChildren(scroll, note);
  }

  /* ---------- Paper betting ---------- */

  function renderPaper(entries) {
    const box = document.getElementById("paper-ledger");
    const rules = state.record?.paperBetting;
    if (!box || !rules) return;
    const graded = entries.filter((entry) => entry.status === "graded").length;
    const progress = element("div", "paper-progress");
    const meter = element("span", "paper-meter");
    meter.style.setProperty("--done", `${Math.min(100, (graded / rules.minGraded) * 100)}%`);
    meter.setAttribute("role", "progressbar");
    meter.setAttribute("aria-valuemin", "0");
    meter.setAttribute("aria-valuemax", String(rules.minGraded));
    meter.setAttribute("aria-valuenow", String(graded));
    meter.setAttribute("aria-label", say("paperProgress", { graded, needed: rules.minGraded }));
    progress.append(element("p", "paper-count", say("paperProgress", { graded, needed: rules.minGraded })), meter);

    let settled = 0;
    let profit = 0;
    const clvs = [];
    const list = element("ul", "paper-list");
    for (const entry of entries) {
      if (!entry.model || !entry.market) continue;
      const gaps = entry.model.map((p, index) => p - entry.market[index]);
      const item = element("li", "paper-item");
      item.append(element("span", "paper-match", `${say("matchday", { n: entry.post.matchday })} · ${entry.post.home.name} – ${entry.post.away.name}`));
      const picks = gaps.map((gap, index) => ({ gap, index })).filter(({ gap }) => gap >= rules.threshold - 1e-9);
      if (!picks.length || !entry.odds) {
        const best = gaps.map((gap, index) => ({ gap, index })).sort((a, b) => b.gap - a.gap)[0];
        item.append(element("span", "paper-bet is-none", say("noBet", { gap: num(best.gap * 100, 1), pick: pickLabel(entry.post, best.index) })));
      } else {
        for (const { index } of picks) {
          const odds = entry.odds[index];
          const line = element("span", "paper-bet");
          line.append(
            element("strong", "", say("bet", { pick: pickLabel(entry.post, index), odds: num(odds, 2) })),
            element("span", "paper-why", ` (${say("betWhy", { model: pct(entry.model[index]), market: pct(entry.market[index]) })})`),
          );
          const clv = clvOf(odds, entry.closing, index);
          if (clv !== null) {
            clvs.push(clv);
            const tag = element("span", `paper-clv ${clv >= 0 ? "is-plus" : "is-minus"}`, say("clv", { value: signedPct(clv) }));
            tag.title = say("clvTitle");
            line.append(" ", tag);
          }
          let status;
          if (entry.status === "graded") {
            settled += 1;
            const won = entry.outcome === index;
            const amount = won ? (odds - 1) * rules.stake : -rules.stake;
            profit += amount;
            // The result of a single bet is shown; the running total waits for the minimum sample.
            status = element("span", `paper-status ${won ? "is-won" : "is-lost"}`, say(won ? "betWon" : "betLost", { amount: euro(Math.abs(amount)) }));
          } else {
            status = element("span", "paper-status", say("betPending"));
          }
          line.append(status);
          item.append(line);
        }
      }
      list.append(item);
    }
    const average = clvs.length ? ` · ${say("clvAverage", { value: signedPct(clvs.reduce((sum, value) => sum + value, 0) / clvs.length) })}` : "";
    const total = graded >= rules.minGraded
      ? element("p", "paper-total", say("paperTotal", { count: settled, pl: euro(profit, true), stake: euro(settled * rules.stake) }) + average)
      : element("p", "paper-total is-hidden", say("paperHidden", { needed: rules.minGraded }));
    box.replaceChildren(progress, list, total);
  }

  /* ---------- Start ---------- */

  function renderAll() {
    if (state.failed) {
      for (const id of ["score-cards", "weekly-list", "ledger-list"]) {
        const box = document.getElementById(id);
        if (box) {
          box.replaceChildren(element("p", "page-error", say("loadError")));
          box.removeAttribute("aria-busy");
        }
      }
      return;
    }
    const entries = state.posts.map(grade).sort((a, b) => b.kickoff - a.kickoff);
    const list = weeks();
    renderScore(entries, list.flatMap((week) => week.entries));
    renderWeeks(list);
    renderLedger(entries);
    renderDisagree();
    renderBacktest();
    renderPaper(entries);
  }

  async function json(url) {
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    return response.json();
  }

  async function start() {
    const [posts, record, forecasts, odds] = await Promise.allSettled([
      json("../analysis/posts.json"), json("../data/record.json"), json("../data/forecasts.json"), json("../data/odds.json"),
    ]);
    if (posts.status !== "fulfilled") {
      state.failed = true;
      renderAll();
      return;
    }
    state.posts = (posts.value.posts ?? []).filter((post) => post.forecast?.model && post.forecast?.market);
    if (record.status === "fulfilled") state.record = record.value;
    if (forecasts.status === "fulfilled") state.forecasts = forecasts.value;
    if (odds.status === "fulfilled") state.odds = odds.value;
    renderAll();
    // Final scores, one small request per finished deep dive.
    const started = state.posts.filter((post) => !post.fullTime?.score && Date.now() >= new Date(post.kickoff).getTime());
    const results = await Promise.allSettled(started.map((post) => json(`${API}/getmatchdata/${encodeURIComponent(post.matchId)}`)));
    results.forEach((result, index) => {
      if (result.status === "fulfilled" && result.value) state.results.set(Number(started[index].matchId), result.value);
    });
    state.resultsLoaded = true;
    // And one request per matchday of weekly forecasts that has kicked off.
    const days = Object.entries(state.forecasts?.matchdays ?? {})
      .filter(([, block]) => Object.values(block.matches ?? {}).some((match) => Date.now() >= new Date(match.kickoff).getTime()))
      .map(([matchday]) => matchday);
    const season = encodeURIComponent(state.forecasts?.season ?? "");
    const rounds = await Promise.allSettled(days.map((matchday) => json(`${API}/getmatchdata/bl1/${season}/${encodeURIComponent(matchday)}`)));
    for (const round of rounds) {
      if (round.status !== "fulfilled" || !Array.isArray(round.value)) continue;
      for (const match of round.value) state.results.set(Number(match.matchID), match);
    }
    state.weeksLoaded = true;
    renderAll();
  }

  I18N.onChange(renderAll);
  start();
})();
