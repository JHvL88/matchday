/*
 * The Season page: the rest of the season played many times over (data/season.json, written by
 * analysis/pipeline/season_sim.py after every completed matchday), the pre-registered test of the
 * simulator (data/season_test.json), past seasons as it saw them (data/season_replays.json, loaded
 * when the replays come into view) and OpenLigaDB for crests and results newer than the file.
 *
 * Results that came in after the file was written are played in the browser: the same model, the
 * same ratings, with those results fixed (sim.js, in a worker when the browser has one). The "what
 * if" picks work the same way. Loaded after i18n.js, glossary.js, explain.js and sim.js.
 */
(() => {
  "use strict";

  const I18N = window.I18N;
  const API = "https://api.openligadb.de";
  const DATA_URL = "../data/season.json";
  const TEST_URL = "../data/season_test.json";
  const REPLAYS_URL = "../data/season_replays.json";
  const TEAM_KEY = "jans-matchday:team";
  const VIEW_KEY = "jans-matchday:season-view";
  const TIME_ZONE = "Europe/Berlin";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const SEED = 20261;
  const KEY_OUTCOMES = ["title", "top4", "europe", "drop"];

  // The same 120 px crest thumbnails the home page uses (app.js).
  const WIKIMEDIA = "https://upload.wikimedia.org/wikipedia/";
  const CREST_THUMBS = {
    6: "de/thumb/f/f7/Bayer_Leverkusen_Logo.svg/120px-Bayer_Leverkusen_Logo.svg.png",
    7: "commons/thumb/6/67/Borussia_Dortmund_logo.svg/120px-Borussia_Dortmund_logo.svg.png",
    9: "commons/thumb/9/97/FC_Schalke_04_Logo.png/120px-FC_Schalke_04_Logo.png",
    16: "commons/thumb/e/eb/VfB_Stuttgart_1893_Logo.svg/120px-VfB_Stuttgart_1893_Logo.svg.png",
    31: "commons/thumb/e/e3/SC_Paderborn_07_Logo.svg/120px-SC_Paderborn_07_Logo.svg.png",
    40: "commons/thumb/1/1f/Logo_FC_Bayern_M%C3%BCnchen_%282002%E2%80%932017%29.svg/120px-Logo_FC_Bayern_M%C3%BCnchen_%282002%E2%80%932017%29.svg.png",
    65: "commons/thumb/0/01/1._FC_Koeln_Logo_2014%E2%80%93.svg/120px-1._FC_Koeln_Logo_2014%E2%80%93.svg.png",
    80: "commons/thumb/4/44/1._FC_Union_Berlin_Logo.svg/120px-1._FC_Union_Berlin_Logo.svg.png",
    81: "commons/thumb/9/9e/Logo_Mainz_05.svg/120px-Logo_Mainz_05.svg.png",
    87: "commons/thumb/8/81/Borussia_M%C3%B6nchengladbach_logo.svg/120px-Borussia_M%C3%B6nchengladbach_logo.svg.png",
    91: "en/thumb/7/7e/Eintracht_Frankfurt_crest.svg/120px-Eintracht_Frankfurt_crest.svg.png",
    95: "de/thumb/b/b5/Logo_FC_Augsburg.svg/120px-Logo_FC_Augsburg.svg.png",
    100: "commons/thumb/f/f7/Hamburger_SV_logo.svg/120px-Hamburger_SV_logo.svg.png",
    112: "de/thumb/b/bf/SC_Freiburg_Logo.svg/120px-SC_Freiburg_Logo.svg.png",
    134: "commons/thumb/b/be/SV-Werder-Bremen-Logo.svg/120px-SV-Werder-Bremen-Logo.svg.png",
    175: "commons/thumb/e/e7/Logo_TSG_Hoffenheim.svg/120px-Logo_TSG_Hoffenheim.svg.png",
    198: "commons/thumb/3/35/SV_Elversberg_Logo.svg/120px-SV_Elversberg_Logo.svg.png",
    1635: "en/thumb/0/04/RB_Leipzig_2014_logo.svg/120px-RB_Leipzig_2014_logo.svg.png",
  };

  const WORDS = {
    en: {
      stamp: "After matchday {md} · simulated {date} · {left} matches still to play",
      stampLive: "Live: {count} newer results played in, re-simulated in your browser",
      stampLiveOne: "Live: 1 newer result played in, re-simulated in your browser",
      noData: "The season simulator has not run yet. It publishes after the first completed matchday.",
      loadError: "The simulator’s numbers could not be loaded. Try again in a minute.",
      models: "My models",
      market: "Bookmakers",
      bookies: "bookies {p}",
      outcome: { title: "title", top4: "top four", europe: "Europe", playoff: "play-off (16th)", drop: "relegation (17th–18th)" },
      outcomeCap: { title: "Title", top4: "Top four", europe: "Europe", playoff: "Play-off", drop: "Down" },
      titleLead: "{a} win the league in {pa} of the simulated seasons, {b} in {pb}.",
      titleRest: "Nobody else gets past {p}.",
      titleThird: "Next best: {c}, {pc}.",
      titleOpen: "No club wins it in more than half the seasons: {list}.",
      titleMarket: "The bookmakers’ version says {p} for {a}.",
      head: { now: "#", club: "Club", pts: "Pts", xpts: "Exp. pts", title: "Title", top4: "Top 4", europe: "Europe", playoff: "16th", drop: "Down", strip: "Where they finish" },
      headTitle: { now: "Position now", pts: "Points now", xpts: "Expected final points", title: "Chance of finishing first", top4: "Chance of finishing in the top four (Champions League)", europe: "Chance of finishing in the top six (Europe, usually)", playoff: "Chance of finishing 16th (relegation play-off)", drop: "Chance of finishing 17th or 18th (relegated)", strip: "Chance of each final position, 1st on the left" },
      tableCaption: "Bundesliga final table, as {who} simulate it after matchday {md}",
      tableNote: "Sorted by average final position. – means it did not happen once in {n} seasons.",
      tableNoteLive: "Sorted by average final position, with the newer results played in. – means it did not happen once in {n} seasons.",
      stripCell: "{pos}: {p}",
      detailMost: "{club} finish {pos} more often than anywhere else ({p}).",
      detailPts: "Expected points: <strong>{xpts}</strong>, and in 8 of 10 seasons between {lo} and {hi}.",
      detailNow: "Now {pos} on {pts} points.",
      follow: "Follow {club}",
      unfollow: "Stop following {club}",
      posAxis: "Final position",
      zones: { cl: "Champions League", eu: "Europe", po: "Play-off", down: "Down" },
      win: "Win",
      draw: "Draw",
      loss: "Loss",
      stakesRank: "#{n}",
      stakesNone: "No matchday left to play.",
      stakesQuiet: "Not much riding on it: no chance moves by more than a point.",
      stakesMore: "Show all {count} matches",
      stakesLess: "Show fewer",
      stakesFinal: "Full time {score}",
      stakesNow: "now {p}",
      kickoff: "{day}, {time}",
      whatifTitle: "Matchday {md}",
      whatifDates: "{dates}",
      whatifPicks: { one: "{count} pick", other: "{count} picks" },
      whatifEmpty: "Pick a result or two above and the rest of the season plays out here.",
      whatifRunning: "Playing {n} seasons…",
      whatifStatus: "{n} seasons with your {picks}, played in your browser in {s} s. Compared with the same {n} seasons without them.",
      whatifNoChange: "Your picks barely move anything: no chance changes by more than a point.",
      whatifHead: { club: "Club", what: "", before: "Before", after: "After", change: "Change" },
      draw2: "Draw",
      played: "Played",
      raceMetric: { title: "Title", top4: "Top four", drop: "Down" },
      raceAria: "{metric} chance after each matchday",
      raceStart: "Before kick-off",
      raceAfter: "After matchday {md}",
      raceFinal: "Final table",
      raceFuture: "still to play",
      raceTable: "Show as table",
      raceChart: "Show as chart",
      raceCol: "MD {md}",
      linesTitle: "Champions",
      linesTop4: "Fourth place",
      linesSafety: "16th place",
      linesPts: "points",
      linesRange: "{lo}–{hi} in 8 of 10 seasons",
      linesTitleText: "{p} points beat the runner-up in 9 of 10 seasons.",
      linesTop4Text: "{p} points beat fifth place in 9 of 10 seasons.",
      linesSafetyText: "{p} points kept a club above 16th in 9 of 10 seasons. The old 40-point rule: enough in {q}.",
      linesSafetyNever: "{p} points kept a club above 16th in 9 of 10 seasons. The old 40-point rule never failed once.",
      histAria: "Points of the club in {pos} place across the simulated seasons",
      settledLead: "Most likely settled on matchday {md} ({p} of seasons). It goes to the final day, or to goal difference, in {last}.",
      settledDone: "Settled.",
      settledAxis: "Matchday the title is mathematically certain",
      settledTip: "Matchday {md}: {p}",
      replayStoryTitle: "{champ} won it. The simulator made them favourites for good after matchday {first} and passed 90% after matchday {sure}.",
      replayStoryTitleEarly: "{champ} won it, and were favourites from the start.",
      replayStoryTitleEarlySure: "{champ} won it, favourites from the start and past 90% after matchday {sure}.",
      replayStoryTitleLate: "{champ} won it. The simulator made them favourites for good after matchday {first}.",
      replayStoryUpset: "{champ} won it, which the simulator did not see coming: going into the final day it made {rival} favourites at {p}.",
      replayStoryRival: " {rival} peaked at {p} after matchday {md}.",
      replayStoryDrop: "Down went {list}.",
      replayStoryEscape: " Biggest escape: {club}, given {p} to go down after matchday {md}, stayed up.",
      replayStoryTop4: "Last into the top four: {club}, who were at {p} after matchday {md}.",
      replayLoading: "Loading the replays…",
      replayError: "The replays could not be loaded.",
      testCards: { models: "My models", market: "Bookmakers", table: "Table as it stands", uniform: "Guessing" },
      testUnit: "positional RPS",
      testSub: { models: "lower is better", market: "lower is better", table: "1–33 matchdays", uniform: "1/18 for each place" },
      verdict: {
        market: "The bookmakers’ version has been the better season forecaster since 2019/20: lower score overall and in {won} of 7 seasons.",
        models: "My models’ version has been the better season forecaster since 2019/20: lower score overall and in {won} of 7 seasons.",
        neither: "Neither version has been clearly better since 2019/20: the bookmakers’ was ahead in {won} of 7 seasons.",
      },
      calibOk: "Both are well calibrated: when they said 20%, it happened about 20% of the time, in every band of the chart below.",
      calibOkOne: "{who} is well calibrated in every band; {other} is off somewhere (the chart shows where).",
      calibOff: "Neither passes the strict calibration test set beforehand. Where they miss, they miss the same way: too cautious about strong chances.",
      calibMiss: "{who}: things given {f} happened {h} of the time.",
      doubt: "The doubt helps, a little: without it my models would score {nodoubt} instead of {score} on the test seasons, and the bookmakers’ version {mnodoubt} instead of {mscore}. Small, but in the same direction as on the tuning seasons, where it was chosen (σ = {sigma} for my models, {msigma} for the bookmakers’).",
      shrink: "Before a ball is kicked the error is {first}; after matchday 33 it is {last}. Football is a lot less random in May.",
      calibAxisX: "Forecast",
      calibAxisY: "Happened",
      calibTip: "Forecast {f} · happened {h} · {n} forecasts",
      kpi: "Positional RPS: how far a forecast of the final position was from where the club finished, with credit for near misses (forecasting 5th for a club that finishes 4th costs less than forecasting 15th). 0 is perfect.",
      testPending: "The test results will appear here.",
    },
    de: {
      stamp: "Nach dem {md}. Spieltag · simuliert am {date} · {left} Spiele stehen noch aus",
      stampLive: "Live: {count} neuere Ergebnisse eingerechnet, im Browser neu simuliert",
      stampLiveOne: "Live: 1 neueres Ergebnis eingerechnet, im Browser neu simuliert",
      noData: "Der Saison-Simulator ist noch nicht gelaufen. Er rechnet nach dem ersten abgeschlossenen Spieltag.",
      loadError: "Die Zahlen des Simulators konnten nicht geladen werden. Bitte gleich noch einmal versuchen.",
      models: "Meine Modelle",
      market: "Buchmacher",
      bookies: "Buchm. {p}",
      outcome: { title: "Meisterschaft", top4: "Top vier", europe: "Europa", playoff: "Relegation (16.)", drop: "Abstieg (17./18.)" },
      outcomeCap: { title: "Meister", top4: "Top vier", europe: "Europa", playoff: "Relegation", drop: "Abstieg" },
      titleLead: "{a} wird in {pa} der simulierten Spielzeiten Meister, {b} in {pb}.",
      titleRest: "Sonst kommt niemand über {p}.",
      titleThird: "Dahinter: {c} mit {pc}.",
      titleOpen: "Kein Klub wird in mehr als der Hälfte der Spielzeiten Meister: {list}.",
      titleMarket: "Die Version der Buchmacher sagt {p} für {a}.",
      head: { now: "#", club: "Klub", pts: "Pkt.", xpts: "Erw. Pkt.", title: "Meister", top4: "Top 4", europe: "Europa", playoff: "16.", drop: "Abstieg", strip: "Wo sie landen" },
      headTitle: { now: "Platz jetzt", pts: "Punkte jetzt", xpts: "Erwartete Punkte am Saisonende", title: "Chance auf Platz eins", top4: "Chance auf die Top vier (Champions League)", europe: "Chance auf die Top sechs (meist Europa)", playoff: "Chance auf Platz 16 (Relegation)", drop: "Chance auf Platz 17 oder 18 (Abstieg)", strip: "Chance auf jeden Endplatz, Platz eins links" },
      tableCaption: "Bundesliga-Abschlusstabelle, wie {who} sie nach dem {md}. Spieltag simulieren",
      tableNote: "Sortiert nach durchschnittlichem Endplatz. – heißt: in {n} Spielzeiten kein einziges Mal.",
      tableNoteLive: "Sortiert nach durchschnittlichem Endplatz, mit den neueren Ergebnissen. – heißt: in {n} Spielzeiten kein einziges Mal.",
      stripCell: "{pos}: {p}",
      detailMost: "{club} landet am häufigsten auf Platz {pos} ({p}).",
      detailPts: "Erwartete Punkte: <strong>{xpts}</strong>, in 8 von 10 Spielzeiten zwischen {lo} und {hi}.",
      detailNow: "Jetzt Platz {pos} mit {pts} Punkten.",
      follow: "{club} folgen",
      unfollow: "{club} nicht mehr folgen",
      posAxis: "Endplatz",
      zones: { cl: "Champions League", eu: "Europa", po: "Relegation", down: "Abstieg" },
      win: "Sieg",
      draw: "Remis",
      loss: "Niederl.",
      stakesRank: "#{n}",
      stakesNone: "Kein Spieltag mehr übrig.",
      stakesQuiet: "Hier geht es um wenig: Keine Chance bewegt sich um mehr als einen Punkt.",
      stakesMore: "Alle {count} Spiele zeigen",
      stakesLess: "Weniger zeigen",
      stakesFinal: "Endstand {score}",
      stakesNow: "jetzt {p}",
      kickoff: "{day}, {time}",
      whatifTitle: "{md}. Spieltag",
      whatifDates: "{dates}",
      whatifPicks: { one: "{count} Tipp", other: "{count} Tipps" },
      whatifEmpty: "Tipp oben ein, zwei Ergebnisse, und hier spielt sich der Rest der Saison ab.",
      whatifRunning: "{n} Spielzeiten laufen…",
      whatifStatus: "{n} Spielzeiten mit {picks}, gespielt in deinem Browser in {s} s. Verglichen mit denselben {n} Spielzeiten ohne sie.",
      whatifNoChange: "Deine Tipps bewegen kaum etwas: Keine Chance ändert sich um mehr als einen Punkt.",
      whatifHead: { club: "Klub", what: "", before: "Vorher", after: "Nachher", change: "Änderung" },
      draw2: "Remis",
      played: "Gespielt",
      raceMetric: { title: "Meister", top4: "Top vier", drop: "Abstieg" },
      raceAria: "Chance auf {metric} nach jedem Spieltag",
      raceStart: "Vor dem Anpfiff",
      raceAfter: "Nach dem {md}. Spieltag",
      raceFinal: "Abschlusstabelle",
      raceFuture: "noch zu spielen",
      raceTable: "Als Tabelle zeigen",
      raceChart: "Als Grafik zeigen",
      raceCol: "{md}. ST",
      linesTitle: "Meister",
      linesTop4: "Platz vier",
      linesSafety: "Platz 16",
      linesPts: "Punkte",
      linesRange: "{lo}–{hi} in 8 von 10 Spielzeiten",
      linesTitleText: "{p} Punkte lagen in 9 von 10 Spielzeiten vor dem Zweiten.",
      linesTop4Text: "{p} Punkte lagen in 9 von 10 Spielzeiten vor Platz fünf.",
      linesSafetyText: "Mit {p} Punkten blieb ein Klub in 9 von 10 Spielzeiten vor Platz 16. Die alte 40-Punkte-Regel: reichte in {q}.",
      linesSafetyNever: "Mit {p} Punkten blieb ein Klub in 9 von 10 Spielzeiten vor Platz 16. Die alte 40-Punkte-Regel versagte kein einziges Mal.",
      histAria: "Punkte des Klubs auf Platz {pos} über die simulierten Spielzeiten",
      settledLead: "Am wahrscheinlichsten am {md}. Spieltag entschieden ({p} der Spielzeiten). Bis zum letzten Spieltag oder bis zur Tordifferenz geht es in {last}.",
      settledDone: "Entschieden.",
      settledAxis: "Spieltag, an dem die Meisterschaft rechnerisch feststeht",
      settledTip: "{md}. Spieltag: {p}",
      replayStoryTitle: "{champ} wurde Meister. Der Simulator machte sie nach dem {first}. Spieltag endgültig zum Favoriten und lag nach dem {sure}. Spieltag über 90 %.",
      replayStoryTitleEarly: "{champ} wurde Meister und war von Anfang an Favorit.",
      replayStoryTitleEarlySure: "{champ} wurde Meister, war von Anfang an Favorit und lag nach dem {sure}. Spieltag über 90 %.",
      replayStoryTitleLate: "{champ} wurde Meister. Der Simulator machte sie nach dem {first}. Spieltag endgültig zum Favoriten.",
      replayStoryUpset: "{champ} wurde Meister, und das sah der Simulator nicht kommen: Vor dem letzten Spieltag machte er {rival} mit {p} zum Favoriten.",
      replayStoryRival: " {rival} kam nach dem {md}. Spieltag auf bis zu {p}.",
      replayStoryDrop: "Abgestiegen: {list}.",
      replayStoryEscape: " Größte Rettung: {club}, nach dem {md}. Spieltag mit {p} Abstiegschance, blieb drin.",
      replayStoryTop4: "Als Letzter in die Top vier: {club}, nach dem {md}. Spieltag bei {p}.",
      replayLoading: "Die Zeitreise lädt…",
      replayError: "Die Zeitreise konnte nicht geladen werden.",
      testCards: { models: "Meine Modelle", market: "Buchmacher", table: "Tabelle, wie sie steht", uniform: "Raten" },
      testUnit: "Positions-RPS",
      testSub: { models: "niedriger ist besser", market: "niedriger ist besser", table: "Spieltage 1–33", uniform: "1/18 pro Platz" },
      verdict: {
        market: "Die Version der Buchmacher hat die Saison seit 2019/20 besser vorhergesagt: niedrigerer Wert insgesamt und in {won} von 7 Spielzeiten.",
        models: "Die Version meiner Modelle hat die Saison seit 2019/20 besser vorhergesagt: niedrigerer Wert insgesamt und in {won} von 7 Spielzeiten.",
        neither: "Keine Version war seit 2019/20 klar besser: Die der Buchmacher lag in {won} von 7 Spielzeiten vorn.",
      },
      calibOk: "Beide sind gut kalibriert: Wenn sie 20 % sagten, trat es in etwa 20 % der Fälle ein, in jedem Bereich der Grafik unten.",
      calibOkOne: "{who} ist in jedem Bereich gut kalibriert; {other} liegt irgendwo daneben (die Grafik zeigt, wo).",
      calibOff: "Keine besteht den strengen, vorher festgelegten Kalibrierungstest. Wo sie danebenliegen, dann gleich: zu vorsichtig bei hohen Chancen.",
      calibMiss: "{who}: Was mit {f} bewertet wurde, trat in {h} der Fälle ein.",
      doubt: "Der Zweifel hilft, ein wenig: Ohne ihn kämen meine Modelle in den Testspielzeiten auf {nodoubt} statt {score}, die Version der Buchmacher auf {mnodoubt} statt {mscore}. Klein, aber in dieselbe Richtung wie in den Einstellspielzeiten, wo er gewählt wurde (σ = {sigma} für meine Modelle, {msigma} für die Buchmacher).",
      shrink: "Vor dem ersten Spiel liegt der Fehler bei {first}, nach dem 33. Spieltag bei {last}. Im Mai ist Fußball deutlich weniger Zufall.",
      calibAxisX: "Prognose",
      calibAxisY: "Eingetreten",
      calibTip: "Prognose {f} · eingetreten {h} · {n} Prognosen",
      kpi: "Positions-RPS: wie weit eine Prognose des Endplatzes vom tatsächlichen Platz entfernt lag, mit Bonus für knappe Fehler (Platz 5 für einen Klub, der Vierter wird, kostet weniger als Platz 15). 0 ist perfekt.",
      testPending: "Hier erscheinen die Testergebnisse.",
    },
  };

  const state = {
    data: null, test: null, replays: null, replaysLoading: false,
    view: readView(), team: readTeam(), crests: new Map(),
    liveFixed: {}, liveCount: 0, live: null,
    picks: new Map(), whatifMd: null, whatifResult: null, whatifBusy: false,
    baseline: new Map(), openClub: null, stakesAll: false,
    metric: { now: "title", replay: "title" }, keyClubs: { now: null, replay: null },
    tableView: { now: false, replay: false }, replaySeason: null,
  };

  /* ---------- Small helpers ---------- */

  function say(key, params = {}) {
    let entry = WORDS[I18N.lang]?.[key] ?? WORDS.en[key];
    if (entry && typeof entry === "object" && "other" in entry) entry = entry[new Intl.PluralRules(I18N.locale).select(Number(params.count))] ?? entry.other;
    return String(entry).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
  }

  function word(group, key) {
    return (WORDS[I18N.lang]?.[group] ?? WORDS.en[group])?.[key] ?? key;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function svg(tag, attributes = {}) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    return node;
  }

  function readView() {
    try {
      return localStorage.getItem(VIEW_KEY) === "market" ? "market" : "models";
    } catch {
      return "models";
    }
  }

  function readTeam() {
    try {
      const value = Number(localStorage.getItem(TEAM_KEY));
      return Number.isFinite(value) && value > 0 ? String(value) : null;
    } catch {
      return null;
    }
  }

  function store(key, value) {
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch {
      // Private mode: the choice lasts for this visit.
    }
  }

  // Chances as people read them: 90%, 7.4%, <0.1%, – for "never in all those seasons".
  function pct(p) {
    if (p === null || p === undefined || Number.isNaN(p)) return "–";
    if (p <= 0) return "–";
    const format = (value, digits) => new Intl.NumberFormat(I18N.locale, { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
    if (p < 0.0005) return `<${format(0.001, 1)}`;
    if (p >= 0.9995) return `>${format(0.999, 1)}`;
    // As close to certain as to impossible gets a decimal too, so 99.4% never rounds up to 100%.
    return p < 0.1 || p > 0.9 ? format(p, 1) : format(p, 0);
  }

  function signedPoints(delta) {
    const points = Math.round(delta * 1000) / 10;
    const text = I18N.number(Math.abs(points), Math.abs(points) < 10 ? 1 : 0);
    return `${points > 0 ? "+" : points < 0 ? "−" : "±"}${text}`;
  }

  async function json(url) {
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    return response.json();
  }

  function shortName(id) {
    return state.data?.teams?.[id]?.short ?? String(id);
  }

  function crestUrl(id, original) {
    const known = CREST_THUMBS[Number(id)];
    if (known) return WIKIMEDIA + known;
    return original || "";
  }

  function crest(id, name) {
    const url = crestUrl(id, state.crests.get(String(id)));
    if (!url) {
      const fallback = element("span", "crest logo-fallback", (name ?? shortName(id)).slice(0, 3));
      fallback.setAttribute("aria-hidden", "true");
      return fallback;
    }
    const img = element("img", "crest");
    img.src = url;
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.width = 22;
    img.height = 22;
    img.addEventListener("error", () => {
      const fallback = element("span", "crest logo-fallback", (name ?? shortName(id)).slice(0, 3));
      img.replaceWith(fallback);
    }, { once: true });
    return img;
  }

  function when(iso, options) {
    return I18N.dateFormat(iso, { timeZone: TIME_ZONE, ...options });
  }

  /* ---------- Numbers for the current view ---------- */

  function view() {
    return state.data.views[state.view];
  }

  function summaryFor(viewName = state.view) {
    if (state.live?.[viewName]) return state.live[viewName];
    return state.data.views[viewName].teams;
  }

  function sortedTeams(viewName = state.view) {
    const s = summaryFor(viewName);
    return Object.keys(state.data.teams).sort((a, b) => s[a].xpos - s[b].xpos || s[b].xpts - s[a].xpts);
  }

  function tableNow() {
    const teams = state.data.teams;
    const ids = Object.keys(teams);
    const order = [...ids].sort((a, b) => {
      const [pa, ga, fa] = teams[a].table;
      const [pb, gb, fb] = teams[b].table;
      return pb - pa || gb - ga || fb - fa || shortName(a).localeCompare(shortName(b));
    });
    return Object.fromEntries(order.map((id, i) => [id, i + 1]));
  }

  /* ---------- The simulator in the browser ---------- */

  let worker = null;
  let jobId = 0;
  const pending = new Map();

  function startWorker() {
    if (worker !== null || typeof Worker === "undefined") return;
    try {
      worker = new Worker("worker.js?v=1");
      worker.onmessage = (event) => {
        const { id, summary, error } = event.data;
        const job = pending.get(id);
        if (!job) return;
        pending.delete(id);
        if (error) job.reject(new Error(error));
        else job.resolve(summary);
      };
      worker.onerror = () => {
        worker = false;
        for (const [id, job] of pending) {
          pending.delete(id);
          runHere(job.job).then(job.resolve, job.reject);
        }
      };
    } catch {
      worker = false;
    }
  }

  function runHere(job) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        try {
          resolve(window.SeasonSim.summarise(window.SeasonSim.run(job)));
        } catch (error) {
          reject(error);
        }
      }, 20);
    });
  }

  function simulate(job) {
    startWorker();
    if (!worker) return runHere(job);
    return new Promise((resolve, reject) => {
      jobId += 1;
      pending.set(jobId, { resolve, reject, job });
      worker.postMessage({ id: jobId, job });
    });
  }

  function jobFor(viewName, fixed) {
    const d = state.data;
    const v = d.views[viewName];
    return {
      teams: Object.keys(d.teams),
      table: Object.fromEntries(Object.entries(d.teams).map(([id, team]) => [id, team.table])),
      fixtures: d.fixtures,
      ratings: v.ratings,
      sigma: v.sigma,
      n: d.browserSims ?? 10000,
      seed: SEED,
      fixed,
    };
  }

  /* ---------- Hero ---------- */

  function renderStamp() {
    const node = document.querySelector("#season-stamp");
    const d = state.data;
    node.replaceChildren();
    const text = element("span", "", say("stamp", {
      md: d.afterMatchday,
      date: when(d.updated, { day: "numeric", month: "short" }),
      left: d.fixtures.length,
    }));
    node.append(text);
    if (state.liveCount) {
      node.append(element("br"), element("span", "live-note", state.liveCount === 1 ? say("stampLiveOne") : say("stampLive", { count: state.liveCount })));
    }
    for (const button of document.querySelectorAll("[data-view]")) button.setAttribute("aria-pressed", String(button.dataset.view === state.view));
  }

  /* ---------- Title race ---------- */

  function renderTitle() {
    const box = document.querySelector("#title-bars");
    const models = summaryFor("models");
    const market = summaryFor("market");
    const ids = Object.keys(state.data.teams)
      .filter((id) => Math.max(models[id].p.title, market[id].p.title) >= 0.001)
      .sort((a, b) => models[b].p.title - models[a].p.title || market[b].p.title - market[a].p.title)
      .slice(0, 6);
    box.replaceChildren();
    for (const id of ids) {
      const row = element("div", `odds-row${id === state.team ? " is-followed" : ""}`);
      const club = element("div", "odds-club");
      club.append(crest(id), element("span", "", shortName(id)));
      const track = element("div", "odds-track");
      const fill = element("div", "odds-fill");
      fill.style.width = `${(models[id].p.title * 100).toFixed(2)}%`;
      const pin = element("div", "odds-pin");
      pin.style.left = `${(market[id].p.title * 100).toFixed(2)}%`;
      track.append(fill, pin);
      track.setAttribute("role", "img");
      track.setAttribute("aria-label", `${shortName(id)}: ${say("models")} ${pct(models[id].p.title)}, ${say("market")} ${pct(market[id].p.title)}`);
      const value = element("div", "odds-value", pct(models[id].p.title));
      value.append(element("small", "", say("bookies", { p: pct(market[id].p.title) })));
      row.append(club, track, value);
      box.append(row);
    }
    box.removeAttribute("aria-busy");

    const ranked = Object.keys(models).sort((a, b) => models[b].p.title - models[a].p.title);
    const [a, b, c] = ranked;
    const lede = document.querySelector("#title-lede");
    let text;
    if (models[a].p.title >= 0.5) {
      text = say("titleLead", { a: shortName(a), pa: pct(models[a].p.title), b: shortName(b), pb: pct(models[b].p.title) });
      text += " " + (models[c].p.title >= 0.02
        ? say("titleThird", { c: shortName(c), pc: pct(models[c].p.title) })
        : say("titleRest", { p: pct(Math.max(models[c].p.title, 0.0001)) }));
    } else {
      text = say("titleOpen", { list: ranked.slice(0, 4).filter((id) => models[id].p.title >= 0.01).map((id) => `${shortName(id)} ${pct(models[id].p.title)}`).join(", ") });
    }
    if (Math.abs(market[a].p.title - models[a].p.title) >= 0.02) text += " " + say("titleMarket", { a: shortName(a), p: pct(market[a].p.title) });
    lede.textContent = text;
  }

  /* ---------- The projected table ---------- */

  const COLUMNS = ["now", "club", "pts", "xpts", "title", "top4", "europe", "playoff", "drop", "strip"];
  const PHONE_HIDDEN = new Set(["europe", "playoff", "strip"]);

  function renderTable() {
    const d = state.data;
    const s = summaryFor();
    const now = tableNow();
    const head = document.querySelector("#season-table-head");
    const rows = document.querySelector("#season-table-rows");
    const tr = element("tr");
    for (const col of COLUMNS) {
      const th = element("th", `${col}-col${["title", "top4", "europe", "playoff", "drop"].includes(col) ? " p-col" : ""}${PHONE_HIDDEN.has(col) ? " hide-phone" : ""}`);
      th.scope = "col";
      const abbr = element("abbr", "", word("head", col));
      const title = word("headTitle", col);
      if (title !== col) abbr.title = title;
      th.append(abbr);
      tr.append(th);
    }
    head.replaceChildren(tr);
    document.querySelector("#season-table-caption").textContent = say("tableCaption", { who: say(state.view), md: d.afterMatchday });

    rows.replaceChildren();
    for (const id of sortedTeams()) {
      const t = s[id];
      const row = element("tr", `${id === state.team ? "is-followed" : ""}${state.openClub === id ? " is-open" : ""}`);
      row.dataset.team = id;
      row.append(element("td", "now-col", String(now[id])));
      const clubTd = element("td", "club-col");
      const button = element("button", "club-cell");
      button.type = "button";
      button.setAttribute("aria-expanded", String(state.openClub === id));
      button.append(crest(id), element("span", "club-name", shortName(id)));
      button.addEventListener("click", () => {
        state.openClub = state.openClub === id ? null : id;
        renderTable();
      });
      clubTd.append(button);
      row.append(clubTd);
      row.append(element("td", "pts-col", String(d.teams[id].table[0])));
      row.append(element("td", "xpts-col", I18N.number(t.xpts, 0)));
      for (const key of ["title", "top4", "europe", "playoff", "drop"]) {
        const td = element("td", `p-col heat${PHONE_HIDDEN.has(key) ? " hide-phone" : ""}${t.p[key] <= 0 ? " is-zero" : ""}`, pct(t.p[key]));
        td.style.setProperty("--p", Math.min(1, t.p[key]).toFixed(3));
        row.append(td);
      }
      const strip = element("td", "strip-col hide-phone");
      const cells = element("div", "pos-strip");
      cells.setAttribute("role", "img");
      cells.setAttribute("aria-label", t.pos.map((p, i) => (p >= 0.005 ? say("stripCell", { pos: I18N.ordinal(i + 1), p: pct(p) }) : null)).filter(Boolean).join(", "));
      const top = Math.max(...t.pos);
      t.pos.forEach((p) => {
        const cell = element("i");
        cell.style.setProperty("--a", (p > 0 ? 0.08 + 0.92 * (p / top) : 0).toFixed(3));
        cells.append(cell);
      });
      strip.append(cells);
      row.append(strip);
      rows.append(row);
      if (state.openClub === id) rows.append(detailRow(id));
    }
    document.querySelector("#season-table").removeAttribute("aria-busy");
    document.querySelector("#season-table-note").textContent = say(state.liveCount ? "tableNoteLive" : "tableNote", {
      n: I18N.number(state.liveCount ? d.browserSims : d.sims, 0),
    });
  }

  function detailRow(id) {
    const d = state.data;
    const t = summaryFor()[id];
    const other = summaryFor(state.view === "models" ? "market" : "models")[id];
    const row = element("tr", "detail-row");
    const td = element("td");
    td.colSpan = COLUMNS.length;
    const box = element("div", "club-detail");
    const best = t.pos.indexOf(Math.max(...t.pos));
    const facts = element("p", "club-facts");
    const now = tableNow()[id];
    const range = state.live?.[state.view] ? null : d.views[state.view].teams[id].ptsRange;
    let html = `${escapeHtml(say("detailNow", { pos: I18N.ordinal(now), pts: d.teams[id].table[0] }))} ${escapeHtml(say("detailMost", { club: shortName(id), pos: I18N.ordinal(best + 1), p: pct(t.pos[best]) }))}`;
    if (range) html += ` ${say("detailPts", { xpts: I18N.number(t.xpts, 1), lo: range[0], hi: range[2] })}`;
    facts.innerHTML = html;
    box.append(facts, posChart(t.pos, other.pos));
    const actions = element("div", "club-actions");
    const follow = element("button", "outline-link", say(state.team === id ? "unfollow" : "follow", { club: shortName(id) }));
    follow.type = "button";
    follow.addEventListener("click", () => {
      state.team = state.team === id ? null : id;
      store(TEAM_KEY, state.team);
      renderAll();
    });
    actions.append(follow);
    box.append(actions);
    td.append(box);
    row.append(td);
    return row;
  }

  function escapeHtml(text) {
    return String(text).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" })[ch]);
  }

  function posChart(pos, otherPos) {
    const wrap = element("div", "pos-chart");
    const width = Math.max(280, Math.min(680, (document.querySelector("#final-table")?.clientWidth ?? 340)));
    const height = 150;
    const m = { top: 16, right: 4, bottom: 40, left: 4 };
    const pw = width - m.left - m.right;
    const ph = height - m.top - m.bottom;
    const step = pw / 18;
    const top = Math.max(...pos, ...otherPos, 0.01);
    const y = (p) => m.top + ph - (p / top) * ph;
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img" });
    chart.setAttribute("aria-label", pos.map((p, i) => (p >= 0.01 ? `${I18N.ordinal(i + 1)} ${pct(p)}` : null)).filter(Boolean).join(", "));
    const best = pos.indexOf(Math.max(...pos));
    pos.forEach((p, i) => {
      const x = m.left + i * step + 2;
      const w = step - 4;
      if (p > 0) chart.append(svg("rect", { x, y: y(p), width: w, height: Math.max(1, m.top + ph - y(p)), rx: 2, class: `pos-bar${i === best ? " is-likely" : ""}` }));
      const q = otherPos[i];
      if (q > 0) chart.append(svg("rect", { x: x + 0.75, y: y(q), width: w - 1.5, height: Math.max(1, m.top + ph - y(q)), rx: 2, class: "pos-bar-market" }));
      const label = svg("text", { x: x + w / 2, y: m.top + ph + 14, class: "chart-tick", "text-anchor": "middle" });
      label.textContent = String(i + 1);
      chart.append(label);
      if (p >= 0.03) {
        const value = svg("text", { x: x + w / 2, y: y(p) - 4, class: "chart-tick", "text-anchor": "middle" });
        value.textContent = I18N.number(p * 100, 0);
        chart.append(value);
      }
    });
    chart.append(svg("line", { x1: m.left, x2: m.left + pw, y1: m.top + ph, y2: m.top + ph, class: "chart-baseline" }));
    const narrow = step < 30;
    const zones = [[0, 4, "cl", "middle"], [4, 6, "eu", "middle"], [15, 16, "po", "middle"], [16, 18, "down", "end"]];
    for (const [from, to, key, anchor] of zones) {
      if (narrow && key === "po") continue;        // no room under one column; the axis says 16
      const x1 = m.left + from * step;
      const x2 = m.left + to * step;
      chart.append(svg("line", { x1: x1 + 2, x2: x2 - 2, y1: m.top + ph + 22, y2: m.top + ph + 22, class: "zone-line" }));
      const label = svg("text", { x: anchor === "end" ? x2 - 2 : (x1 + x2) / 2, y: m.top + ph + 35, class: "zone-label", "text-anchor": anchor });
      label.textContent = narrow && key === "cl" ? "CL" : word("zones", key);
      chart.append(label);
    }
    wrap.append(chart);
    const key = element("p", "season-key");
    key.append(element("span", "key-fill"), element("span", "", say(state.view)), element("span", "key-pin"), element("span", "", say(state.view === "models" ? "market" : "models")));
    key.querySelector(".key-pin").style.cssText = "width:14px;height:8px;background:none;box-shadow:inset 0 0 0 1.5px var(--pin);";
    wrap.append(key);
    return wrap;
  }

  /* ---------- What's at stake ---------- */

  function renderStakes() {
    const box = document.querySelector("#stakes-list");
    box.replaceChildren();
    box.removeAttribute("aria-busy");
    const d = state.data;
    const stakes = [...(view().stakes ?? [])].sort((a, b) => b.total - a.total);
    if (!stakes.length) {
      box.append(element("p", "", say("stakesNone")));
      return;
    }
    const overall = summaryFor();
    const shown = state.stakesAll ? stakes : stakes.slice(0, 3);
    shown.forEach((stake, rank) => {
      const fx = d.fixtures[stake.fixture];
      const card = element("article", "stake-card");
      const head = element("div", "stake-head");
      const h3 = element("h3");
      h3.append(element("span", "stake-rank", say("stakesRank", { n: rank + 1 })), document.createTextNode(`${shortName(fx.home)} – ${shortName(fx.away)}`));
      head.append(h3);
      const actual = state.liveFixed[stake.fixture];
      if (Array.isArray(actual)) head.append(element("span", "stake-result", say("stakesFinal", { score: I18N.score(actual[0], actual[1]) })));
      else head.append(element("span", "stake-when", say("kickoff", { day: when(fx.kickoff, { weekday: "short", day: "numeric", month: "short" }), time: when(fx.kickoff, { hour: "2-digit", minute: "2-digit" }) })));
      card.append(head);
      const actualIndex = Array.isArray(actual) ? (actual[0] > actual[1] ? 0 : actual[0] === actual[1] ? 1 : 2) : null;
      let rows = 0;
      for (const side of ["home", "away"]) {
        const id = String(fx[side]);
        let bestKey = null;
        let bestSwing = 0;
        for (const key of KEY_OUTCOMES) {
          const vals = (stake[side][key] ?? []).filter((v) => v !== null);
          if (!vals.length) continue;
          const swing = Math.max(...vals) - Math.min(...vals);
          if (swing > bestSwing) {
            bestSwing = swing;
            bestKey = key;
          }
        }
        if (!bestKey || bestSwing < 0.01) continue;
        rows += 1;
        const values = stake[side][bestKey];
        // From this club's point of view: win, draw, loss.
        const order = side === "home" ? [0, 1, 2] : [2, 1, 0];
        const row = element("div", "stake-row");
        const label = element("div", "stake-label");
        label.append(element("strong", "", shortName(id)), document.createTextNode(`${word("outcome", bestKey)} · ${say("stakesNow", { p: pct(overall[id].p[bestKey]) })}`));
        row.append(label);
        order.forEach((index, k) => {
          const cell = element("div", `stake-cell${actualIndex === index ? " is-actual" : ""}`, pct(values[index]));
          cell.append(element("small", "", [say("win"), say("draw"), say("loss")][k]));
          row.append(cell);
        });
        card.append(row);
      }
      if (!rows) card.append(element("p", "calc-fine", say("stakesQuiet")));
      box.append(card);
    });
    if (stakes.length > 3) {
      const more = element("button", "outline-link stakes-more", state.stakesAll ? say("stakesLess") : say("stakesMore", { count: stakes.length }));
      more.type = "button";
      more.addEventListener("click", () => {
        state.stakesAll = !state.stakesAll;
        renderStakes();
      });
      box.append(more);
    }
  }

  /* ---------- What if ---------- */

  function matchdays() {
    return [...new Set(state.data.fixtures.map((f) => f.md))].sort((a, b) => a - b);
  }

  function outcomeProbs(fx) {
    // Analytic home / draw / away from the ratings (Dixon–Coles, no doubt), for "favourites win".
    const r = view().ratings;
    const h = String(fx.home);
    const a = String(fx.away);
    const lh = Math.exp(r.mu + r.home + r.att[h] - r.de[a]);
    const la = Math.exp(r.mu + r.att[a] - r.de[h]);
    const pois = (lambda) => {
      const out = [Math.exp(-lambda)];
      for (let k = 1; k < 11; k += 1) out.push(out[k - 1] * lambda / k);
      return out;
    };
    const ph = pois(lh);
    const pa = pois(la);
    let H = 0;
    let D = 0;
    let A = 0;
    for (let i = 0; i < 11; i += 1) {
      for (let j = 0; j < 11; j += 1) {
        let p = ph[i] * pa[j];
        if (i === 0 && j === 0) p *= 1 - lh * la * r.rho;
        else if (i === 0 && j === 1) p *= 1 + lh * r.rho;
        else if (i === 1 && j === 0) p *= 1 + la * r.rho;
        else if (i === 1 && j === 1) p *= 1 - r.rho;
        if (i > j) H += p;
        else if (i === j) D += p;
        else A += p;
      }
    }
    return [H, D, A];
  }

  function renderWhatIf() {
    const d = state.data;
    const mds = matchdays();
    const box = document.querySelector("#whatif-fixtures");
    if (!mds.length) {
      document.querySelector("#whatif").hidden = true;
      return;
    }
    if (state.whatifMd === null || !mds.includes(state.whatifMd)) state.whatifMd = mds[0];
    const md = state.whatifMd;
    const fixtures = d.fixtures.map((f, index) => ({ ...f, index })).filter((f) => f.md === md);
    const title = document.querySelector("#whatif-title");
    const first = fixtures[0]?.kickoff;
    const last = fixtures[fixtures.length - 1]?.kickoff;
    const dates = first ? `${when(first, { day: "numeric", month: "short" })}${when(first, { day: "numeric", month: "short" }) !== when(last, { day: "numeric", month: "short" }) ? ` – ${when(last, { day: "numeric", month: "short" })}` : ""}` : "";
    title.replaceChildren(document.createTextNode(say("whatifTitle", { md })), element("small", "", `${dates}${state.picks.size ? ` · ${say("whatifPicks", { count: state.picks.size })}` : ""}`));
    document.querySelector("#whatif-prev").disabled = md === mds[0];
    document.querySelector("#whatif-next").disabled = md === mds[mds.length - 1];

    box.replaceChildren();
    for (const fx of fixtures) {
      const played = state.liveFixed[fx.index];
      const row = element("div", `pick-row${Array.isArray(played) ? " is-played" : ""}`);
      row.setAttribute("role", "group");
      row.setAttribute("aria-label", `${shortName(fx.home)} – ${shortName(fx.away)}`);
      const current = Array.isArray(played) ? (played[0] > played[1] ? "H" : played[0] === played[1] ? "D" : "A") : state.picks.get(fx.index);
      const options = [["H", "pick-home", shortName(fx.home)], ["D", "pick-draw", Array.isArray(played) ? I18N.score(played[0], played[1]) : say("draw2")], ["A", "pick-away", shortName(fx.away)]];
      for (const [code, cls, text] of options) {
        const button = element("button", `pick ${cls}`);
        button.type = "button";
        button.setAttribute("aria-pressed", String(current === code));
        if (code !== "D") button.append(crest(code === "H" ? fx.home : fx.away));
        button.append(element("span", code === "D" && Array.isArray(played) ? "pick-score" : "", text));
        if (Array.isArray(played)) {
          button.disabled = true;
          button.title = say("played");
        } else {
          button.addEventListener("click", () => {
            if (state.picks.get(fx.index) === code) state.picks.delete(fx.index);
            else state.picks.set(fx.index, code);
            renderWhatIf();
            scheduleWhatIf();
          });
        }
        row.append(button);
      }
      box.append(row);
    }
    renderWhatIfResult();
  }

  let whatIfTimer = null;
  let whatIfRun = 0;

  function scheduleWhatIf() {
    clearTimeout(whatIfTimer);
    whatIfTimer = setTimeout(runWhatIf, 300);
  }

  async function baselineFor(viewName) {
    const key = `${viewName}|${JSON.stringify(state.liveFixed)}`;
    if (!state.baseline.has(key)) state.baseline.set(key, simulate(jobFor(viewName, state.liveFixed)));
    return state.baseline.get(key);
  }

  async function runWhatIf() {
    const run = (whatIfRun += 1);
    if (!state.picks.size) {
      state.whatifResult = null;
      renderWhatIfResult();
      return;
    }
    state.whatifBusy = true;
    renderWhatIfResult();
    const viewName = state.view;
    const fixed = { ...state.liveFixed };
    for (const [index, code] of state.picks) fixed[index] = code;
    const started = performance.now();
    try {
      const [before, after] = await Promise.all([baselineFor(viewName), simulate(jobFor(viewName, fixed))]);
      if (run !== whatIfRun) return;
      state.whatifResult = { before, after, seconds: (performance.now() - started) / 1000, picks: state.picks.size, view: viewName };
    } catch {
      state.whatifResult = null;
    }
    state.whatifBusy = false;
    renderWhatIfResult();
  }

  function renderWhatIfResult() {
    const box = document.querySelector("#whatif-result");
    box.replaceChildren();
    const n = I18N.number(state.data.browserSims ?? 10000, 0);
    if (state.whatifBusy) {
      box.append(element("p", "whatif-status", say("whatifRunning", { n })));
      return;
    }
    const res = state.whatifResult;
    if (!res || !state.picks.size) {
      box.append(element("p", "whatif-status", say("whatifEmpty")));
      return;
    }
    box.append(element("p", "whatif-status", say("whatifStatus", { n, picks: say("whatifPicks", { count: res.picks }), s: I18N.number(res.seconds, 1) })));
    const changes = [];
    for (const id of Object.keys(state.data.teams)) {
      for (const key of ["title", "top4", "europe", "playoff", "drop"]) {
        const b = res.before[id].p[key];
        const a = res.after[id].p[key];
        if (Math.abs(a - b) >= 0.01) changes.push({ id, key, b, a });
      }
    }
    changes.sort((x, y) => Math.abs(y.a - y.b) - Math.abs(x.a - x.b));
    if (!changes.length) {
      box.append(element("p", "", say("whatifNoChange")));
      return;
    }
    const table = element("table", "whatif-table");
    const head = element("tr");
    for (const key of ["club", "before", "after", "change"]) head.append(element("th", "", word("whatifHead", key)));
    const thead = element("thead");
    thead.append(head);
    const tbody = element("tbody");
    for (const change of changes.slice(0, 10)) {
      const tr = element("tr");
      const club = element("td", "");
      club.append(document.createTextNode(shortName(change.id)), element("small", "whatif-what", word("outcomeCap", change.key)));
      tr.append(club, element("td", "", pct(change.b)), element("td", "", pct(change.a)));
      tr.append(element("td", `delta${change.a < change.b ? " is-down" : ""}`, signedPoints(change.a - change.b)));
      tbody.append(tr);
    }
    table.append(thead, tbody);
    const wrap = element("div", "table-scroll");
    wrap.append(table);
    box.append(wrap);
  }

  /* ---------- Lines over the season (now and replays) ---------- */

  function metricValue(row, metric) {
    // history rows: [title, top4, europe, playoff, drop, xpts, table position]
    return { title: row[0], top4: row[1], drop: row[4] }[metric];
  }

  function seasonSeries(metric) {
    const d = state.data;
    const mds = Object.keys(d.history).map(Number).sort((a, b) => a - b);
    const ids = Object.keys(d.teams);
    const live = state.live?.[state.view];
    return ids.map((id) => {
      const values = new Array(35).fill(null);
      for (const md of mds) {
        const row = d.history[String(md)]?.views?.[state.view]?.[id];
        if (row) values[md] = metricValue(row, metric);
      }
      if (live) values[d.afterMatchday] = live[id].p[metric];
      return { id, name: shortName(id), values };
    });
  }

  function replaySeries(season, metric) {
    const clubs = state.replays.seasons[String(season)];
    const index = { title: 0, top4: 1, drop: 2 }[metric];
    return Object.entries(clubs).map(([key, club]) => {
      const values = club[state.view][index].map((v) => v / 1000);
      const lo = { title: 1, top4: 1, drop: 17 }[metric];
      const hi = { title: 1, top4: 4, drop: 18 }[metric];
      return { id: key, crestId: club.id, name: club.name, values, final: club.final, achieved: club.final >= lo && club.final <= hi };
    });
  }

  function renderRace(container, which, series, { lastX, maxX = 34 }) {
    container.replaceChildren();
    const metric = state.metric[which];
    const controls = element("div", "race-controls");
    const seg = element("div", "segmented chart-switch");
    seg.setAttribute("role", "group");
    for (const key of ["title", "top4", "drop"]) {
      const button = element("button", "", word("raceMetric", key));
      button.type = "button";
      button.setAttribute("aria-pressed", String(metric === key));
      button.addEventListener("click", () => {
        state.metric[which] = key;
        state.keyClubs[which] = null;
        which === "now" ? renderNow() : renderReplay();
      });
      seg.append(button);
    }
    const toggle = element("button", "data-toggle", state.tableView[which] ? say("raceChart") : say("raceTable"));
    toggle.type = "button";
    toggle.addEventListener("click", () => {
      state.tableView[which] = !state.tableView[which];
      which === "now" ? renderNow() : renderReplay();
    });
    controls.append(seg, toggle);
    container.append(controls);

    const latest = (s) => {
      for (let x = lastX; x >= 0; x -= 1) if (s.values[x] !== null && s.values[x] !== undefined) return s.values[x];
      return 0;
    };
    const peak = (s) => Math.max(...s.values.filter((v) => v !== null && v !== undefined));
    const drawn = series.filter((s) => peak(s) >= 0.01);
    const candidates = [...drawn].filter((s) => peak(s) >= 0.03).sort((a, b) => latest(b) - latest(a) || peak(b) - peak(a)).slice(0, 10);
    if (!state.keyClubs[which]) {
      // Now: the clubs with the biggest chance today. Replays: the clubs the story was about (the
      // biggest peaks), and always the ones it ended for.
      const ranked = which === "replay" ? [...candidates].sort((a, b) => peak(b) - peak(a)) : candidates;
      const keys = new Set(ranked.slice(0, metric === "title" ? 3 : 4).map((s) => s.id));
      if (which === "replay") for (const s of series) if (s.achieved && peak(s) >= 0.01) keys.add(s.id);
      const followed = series.find((s) => String(s.crestId ?? s.id) === state.team);
      if (followed && peak(followed) >= 0.01) keys.add(followed.id);
      state.keyClubs[which] = keys;
    }
    const keys = state.keyClubs[which];

    if (state.tableView[which]) {
      const table = element("table", "post-table wide season-data-table");
      const head = element("tr");
      head.append(element("th", "", word("head", "club")));
      for (let x = 0; x <= lastX; x += 1) head.append(element("th", "", say("raceCol", { md: x })));
      const thead = element("thead");
      thead.append(head);
      const tbody = element("tbody");
      for (const s of [...drawn].sort((a, b) => latest(b) - latest(a))) {
        const tr = element("tr", keys.has(s.id) ? "is-key" : "");
        tr.append(element("td", "", s.name));
        for (let x = 0; x <= lastX; x += 1) tr.append(element("td", "", pct(s.values[x])));
        tbody.append(tr);
      }
      table.append(thead, tbody);
      const wrap = element("div", "table-scroll");
      wrap.append(table);
      container.append(wrap);
      return;
    }

    const width = Math.max(290, container.clientWidth || 340);
    const height = width < 480 ? 250 : 300;
    const labelRoom = lastX <= maxX - 10 ? 8 : Math.min(128, Math.max(80, ...[...keys].map((id) => (series.find((s) => s.id === id)?.name.length ?? 6) * 7.5 + 58)));
    const m = { top: 12, right: labelRoom, bottom: 30, left: 46 };
    const pw = width - m.left - m.right;
    const ph = height - m.top - m.bottom;
    const x = (v) => m.left + (v / maxX) * pw;
    const y = (p) => m.top + ph - p * ph;
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true" });
    if (lastX < maxX) chart.append(svg("rect", { x: x(lastX), y: m.top, width: x(maxX) - x(lastX), height: ph, class: "race-future" }));
    const grid = svg("g", { class: "chart-grid" });
    for (const p of [0, 0.25, 0.5, 0.75, 1]) {
      grid.append(svg("line", { x1: m.left, x2: m.left + pw, y1: y(p), y2: y(p), class: p === 0 ? "chart-baseline" : "" }));
      const label = svg("text", { x: m.left - 8, y: y(p), class: "chart-tick", "text-anchor": "end", "dominant-baseline": "middle" });
      label.textContent = new Intl.NumberFormat(I18N.locale, { style: "percent" }).format(p);
      grid.append(label);
    }
    const every = pw < 260 ? 10 : 5;
    for (let v = 0; v <= maxX; v += 1) {
      if (v % every !== 0 && v !== maxX) continue;
      if (v !== maxX && maxX - v < every * 0.6) continue;     // no tick crowding the last one
      const label = svg("text", { x: x(v), y: height - 9, class: "chart-tick", "text-anchor": "middle" });
      label.textContent = String(v);
      grid.append(label);
    }
    chart.append(grid);
    if (lastX < maxX - 2) {
      const note = svg("text", { x: (x(lastX) + x(maxX)) / 2, y: m.top + 14, class: "race-note", "text-anchor": "middle" });
      note.textContent = say("raceFuture");
      chart.append(note);
    }
    const path = (s) => {
      let d = "";
      let open = false;
      for (let v = 0; v <= Math.min(maxX, s.values.length - 1); v += 1) {
        const value = s.values[v];
        if (value === null || value === undefined) {
          open = false;
          continue;
        }
        d += `${open ? "L" : "M"}${x(v).toFixed(1)},${y(value).toFixed(1)}`;
        open = true;
      }
      return d;
    };
    const context = svg("g");
    for (const s of drawn) if (!keys.has(s.id)) context.append(svg("path", { d: path(s), class: "race-line" }));
    chart.append(context);
    const labels = [];
    for (const s of drawn) {
      if (!keys.has(s.id)) continue;
      chart.append(svg("path", { d: path(s), class: "race-line is-key" }));
      let endX = Math.min(maxX, s.values.length - 1);
      while (endX > 0 && (s.values[endX] === null || s.values[endX] === undefined)) endX -= 1;
      chart.append(svg("circle", { cx: x(endX), cy: y(s.values[endX]), r: 3.5, class: "chart-focus-dot" }));
      labels.push({ s, endX, yy: y(s.values[endX]), xx: x(endX) });
    }
    // Labels at the line ends, pushed apart so they never overlap, and kept inside the plot.
    labels.sort((a, b) => a.yy - b.yy);
    for (let i = 1; i < labels.length; i += 1) labels[i].yy = Math.max(labels[i].yy, labels[i - 1].yy + 14);
    const overflow = labels.length ? labels[labels.length - 1].yy - (m.top + ph) : 0;
    if (overflow > 0) labels.forEach((label) => { label.yy -= overflow; });
    for (const label of labels) {
      const text = svg("text", { x: label.xx + 8, y: label.yy, class: "race-label", "dominant-baseline": "middle" });
      text.textContent = `${label.s.name} ${pct(label.s.values[label.endX])}${label.s.achieved ? " ✓" : ""}`;
      chart.append(text);
    }
    const crosshair = svg("line", { y1: m.top, y2: m.top + ph, class: "chart-crosshair", visibility: "hidden" });
    chart.append(crosshair);
    const frame = element("div", "chart-frame");
    frame.tabIndex = 0;
    frame.setAttribute("role", "group");
    frame.setAttribute("aria-label", say("raceAria", { metric: word("raceMetric", metric) }));
    frame.append(chart);
    container.append(frame);
    const tooltip = element("div", "chart-tooltip");
    tooltip.hidden = true;
    frame.append(tooltip);
    let active = null;
    const show = (v) => {
      active = v;
      crosshair.setAttribute("x1", x(v));
      crosshair.setAttribute("x2", x(v));
      crosshair.setAttribute("visibility", "visible");
      const rows = [element("span", "tooltip-title", v === 0 ? say("raceStart") : say("raceAfter", { md: v }))];
      const at = drawn.filter((s) => s.values[v] !== null && s.values[v] !== undefined)
        .sort((a, b) => b.values[v] - a.values[v])
        .filter((s, i) => keys.has(s.id) || i < 3)
        .slice(0, 6);
      for (const s of at) {
        const row = element("span", "tooltip-row");
        row.append(element("span", `tooltip-key ${keys.has(s.id) ? "is-focus" : "is-context"}`), element("strong", "", pct(s.values[v])), element("span", "", s.name));
        rows.push(row);
      }
      tooltip.replaceChildren(...rows);
      tooltip.hidden = false;
      const left = x(v) + 14 + tooltip.offsetWidth > frame.clientWidth ? x(v) - tooltip.offsetWidth - 14 : x(v) + 14;
      tooltip.style.left = `${Math.max(4, left)}px`;
      tooltip.style.top = `${m.top + 4}px`;
    };
    const hide = () => {
      active = null;
      tooltip.hidden = true;
      crosshair.setAttribute("visibility", "hidden");
    };
    const limit = which === "now" ? lastX : maxX;
    frame.addEventListener("pointermove", (event) => {
      const bounds = chart.getBoundingClientRect();
      const v = Math.round(((event.clientX - bounds.left - m.left) / pw) * maxX);
      show(Math.max(0, Math.min(limit, v)));
    });
    frame.addEventListener("pointerleave", hide);
    frame.addEventListener("blur", hide);
    frame.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const from = active ?? limit;
      const next = { ArrowLeft: from - 1, ArrowRight: from + 1, Home: 0, End: limit }[event.key];
      show(Math.max(0, Math.min(limit, next)));
    });

    const chips = element("div", "race-chips");
    for (const s of candidates) {
      const chip = element("button", "race-chip");
      chip.type = "button";
      chip.setAttribute("aria-pressed", String(keys.has(s.id)));
      chip.append(crest(s.crestId ?? s.id, s.name), element("span", "", s.name));
      chip.addEventListener("click", () => {
        if (keys.has(s.id)) keys.delete(s.id);
        else keys.add(s.id);
        which === "now" ? renderNow() : renderReplay();
      });
      chips.append(chip);
    }
    container.append(chips);
  }

  function renderNow() {
    renderRace(document.querySelector("#race-now"), "now", seasonSeries(state.metric.now), { lastX: state.data.afterMatchday });
  }

  /* ---------- Replays ---------- */

  function seasonLabel(year) {
    return `${year}/${String(Number(year) + 1).slice(-2)}`;
  }

  async function loadReplays() {
    if (state.replays || state.replaysLoading) return;
    state.replaysLoading = true;
    const story = document.querySelector("#replay-story");
    story.textContent = say("replayLoading");
    try {
      state.replays = await json(REPLAYS_URL);
      const seasons = Object.keys(state.replays.seasons).sort().reverse();
      const select = document.querySelector("#replay-season");
      select.replaceChildren(...seasons.map((s) => {
        const option = element("option", "", seasonLabel(s));
        option.value = s;
        return option;
      }));
      state.replaySeason = state.replaySeason ?? seasons[0];
      select.value = state.replaySeason;
      select.addEventListener("change", () => {
        state.replaySeason = select.value;
        state.keyClubs.replay = null;
        renderReplay();
      });
      renderReplay();
    } catch {
      story.textContent = say("replayError");
    }
    state.replaysLoading = false;
  }

  function renderReplay() {
    if (!state.replays) return;
    const series = replaySeries(state.replaySeason, state.metric.replay);
    renderRace(document.querySelector("#race-replay"), "replay", series, { lastX: 33, maxX: 33 });
    document.querySelector("#replay-story").textContent = replayStory(state.replaySeason, state.metric.replay);
  }

  function replayStory(season, metric) {
    const clubs = Object.values(state.replays.seasons[String(season)]);
    const idx = { title: 0, top4: 1, drop: 2 }[metric];
    const p = (club, md) => club[state.view][idx][md] / 1000;
    if (metric === "title") {
      const champ = clubs.find((c) => c.final === 1);
      const favourite = (md) => clubs.reduce((a, b) => (p(b, md) > p(a, md) ? b : a));
      const last = favourite(33);
      let text;
      if (last !== champ) {
        text = say("replayStoryUpset", { champ: champ.name, rival: last.name, p: pct(p(last, 33)) });
      } else {
        let first = 33;
        while (first > 0 && favourite(first - 1) === champ) first -= 1;
        let sure = null;
        for (let md = first; md <= 33; md += 1) if (sure === null && p(champ, md) >= 0.9) sure = md;
        text = first === 0
          ? say(sure === null ? "replayStoryTitleEarly" : "replayStoryTitleEarlySure", { champ: champ.name, sure })
          : say(sure === null ? "replayStoryTitleLate" : "replayStoryTitle", { champ: champ.name, first, sure });
      }
      let rival = null;
      for (const c of clubs) {
        if (c === champ || c === last) continue;
        for (let md = 1; md <= 33; md += 1) if (!rival || p(c, md) > rival.p) rival = { c, md, p: p(c, md) };
      }
      if (rival && rival.p >= 0.2) text += say("replayStoryRival", { rival: rival.c.name, p: pct(rival.p), md: rival.md });
      return text;
    }
    if (metric === "drop") {
      const down = clubs.filter((c) => c.final >= 17).map((c) => c.name);
      let text = say("replayStoryDrop", { list: down.join(I18N.lang === "de" ? " und " : " and ") });
      let escape = null;
      for (const c of clubs) {
        if (c.final >= 17) continue;
        for (let md = 1; md < 34; md += 1) if (!escape || p(c, md) > escape.p) escape = { c, md, p: p(c, md) };
      }
      if (escape && escape.p >= 0.2) text += say("replayStoryEscape", { club: escape.c.name, p: pct(escape.p), md: escape.md });
      return text;
    }
    const fourth = clubs.find((c) => c.final === 4);
    let low = null;
    for (let md = 5; md < 34; md += 1) if (!low || p(fourth, md) < low.p) low = { md, p: p(fourth, md) };
    return say("replayStoryTop4", { club: fourth.name, p: pct(low.p), md: low.md });
  }

  /* ---------- Points needed ---------- */

  function histQuantile(line, q) {
    let cum = 0;
    for (let i = 0; i < line.hist.length; i += 1) {
      cum += line.hist[i];
      if (cum >= q) return line.from + i;
    }
    return line.from + line.hist.length - 1;
  }

  function shareBelow(line, points) {
    let s = 0;
    for (let i = 0; i < line.hist.length; i += 1) if (line.from + i < points) s += line.hist[i];
    return s;
  }

  function enough(line) {
    // the smallest total that beats this place's points in 9 of 10 seasons
    for (let points = line.from; points <= line.from + line.hist.length; points += 1) if (shareBelow(line, points) >= 0.9) return points;
    return line.from + line.hist.length;
  }

  function renderLines() {
    const box = document.querySelector("#points-lines");
    box.replaceChildren();
    const lines = view().lines;
    if (!lines?.["1"]) return;
    const tiles = [
      { kicker: say("linesTitle"), line: lines["1"], text: say("linesTitleText", { p: enough(lines["2"]) }), mark: enough(lines["2"]), pos: 1 },
      { kicker: say("linesTop4"), line: lines["4"], text: say("linesTop4Text", { p: enough(lines["5"]) }), mark: enough(lines["5"]), pos: 4 },
      { kicker: say("linesSafety"), line: lines["16"], text: say(shareBelow(lines["16"], 40) >= 0.9995 ? "linesSafetyNever" : "linesSafetyText", { p: enough(lines["16"]), q: pct(shareBelow(lines["16"], 40)) }), mark: enough(lines["16"]), pos: 16 },
    ];
    for (const tile of tiles) {
      const node = element("div", "line-tile");
      node.append(element("p", "line-kicker", tile.kicker));
      const value = element("div", "line-value", String(tile.line.range[1]));
      value.append(element("small", "", ` ${say("linesPts")}`));
      node.append(value, element("p", "line-kicker", say("linesRange", { lo: tile.line.range[0], hi: tile.line.range[2] })));
      node.append(histogram(tile.line, tile.mark, tile.pos));
      node.append(element("p", "line-text", tile.text));
      box.append(node);
    }
  }

  function histogram(line, mark, pos) {
    const wrap = element("div", "line-hist");
    const width = 220;
    const height = 70;
    const lo = histQuantile(line, 0.005);
    const hi = histQuantile(line, 0.995);
    const n = Math.max(1, hi - lo + 1);
    const step = width / n;
    const top = Math.max(...line.hist);
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", height, preserveAspectRatio: "none", role: "img" });
    chart.setAttribute("aria-label", say("histAria", { pos: I18N.ordinal(pos) }));
    for (let points = lo; points <= hi; points += 1) {
      const p = line.hist[points - line.from] ?? 0;
      const h = (p / top) * (height - 16);
      chart.append(svg("rect", { x: (points - lo) * step + 0.5, y: height - 14 - h, width: Math.max(1, step - 1), height: h, class: "hist-bar" }));
    }
    if (mark >= lo && mark <= hi + 1) chart.append(svg("line", { x1: (mark - lo) * step, x2: (mark - lo) * step, y1: 0, y2: height - 12, class: "hist-mark" }));
    for (const points of [lo, hi]) {
      const label = svg("text", { x: (points - lo) * step + step / 2, y: height - 2, class: "chart-tick", "text-anchor": points === lo ? "start" : "end" });
      label.textContent = String(points);
      chart.append(label);
    }
    wrap.append(chart);
    return wrap;
  }

  /* ---------- When the title is settled ---------- */

  function renderSettled() {
    const box = document.querySelector("#settled-chart");
    const lede = document.querySelector("#settled-lede");
    box.replaceChildren();
    const settled = view().titleSettled;
    if (!settled) {
      lede.textContent = "";
      return;
    }
    const entries = Object.entries(settled).map(([md, p]) => [Number(md), p]).filter(([md]) => md > state.data.afterMatchday);
    if (!entries.length) {
      lede.textContent = say("settledDone");
      return;
    }
    const early = entries.filter(([md]) => md < 34);
    const mode = (early.length ? early : entries).reduce((a, b) => (b[1] > a[1] ? b : a));
    const last = settled["34"] ?? 0;
    lede.textContent = say("settledLead", { md: mode[0], p: pct(mode[1]), last: pct(last) });
    const from = state.data.afterMatchday + 1;
    const width = Math.max(280, box.clientWidth || 320);
    const height = 150;
    const m = { top: 18, right: 4, bottom: 22, left: 4 };
    const n = 34 - from + 1;
    const step = (width - m.left - m.right) / n;
    const top = Math.max(...entries.map(([, p]) => p), 0.01);
    const ph = height - m.top - m.bottom;
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img" });
    chart.setAttribute("aria-label", entries.filter(([, p]) => p >= 0.01).map(([md, p]) => say("settledTip", { md, p: pct(p) })).join(", "));
    const every = step < 16 ? 2 : 1;
    for (let md = from; md <= 34; md += 1) {
      const p = settled[String(md)] ?? 0;
      const h = (p / top) * ph;
      const xx = m.left + (md - from) * step;
      chart.append(svg("rect", { x: xx + 1.5, y: m.top + ph - h, width: Math.max(1, step - 3), height: Math.max(0, h), rx: 2, class: `settled-bar${md === 34 ? " is-final" : ""}` }));
      if (p >= 0.04) {
        const value = svg("text", { x: xx + step / 2, y: m.top + ph - h - 4, class: "chart-tick", "text-anchor": "middle" });
        value.textContent = I18N.number(p * 100, 0);
        chart.append(value);
      }
      if ((md - from) % every === 0 || md === 34) {
        const label = svg("text", { x: xx + step / 2, y: height - 6, class: "chart-tick", "text-anchor": "middle" });
        label.textContent = String(md);
        chart.append(label);
      }
    }
    chart.append(svg("line", { x1: m.left, x2: width - m.right, y1: m.top + ph, y2: m.top + ph, class: "chart-baseline" }));
    box.append(chart, element("p", "calc-fine", say("settledAxis")));
  }

  /* ---------- The test ---------- */

  function renderTest() {
    const box = document.querySelector("#season-test");
    box.replaceChildren();
    const t = state.test;
    if (!t) {
      box.append(element("p", "calc-fine", say("testPending")));
      return;
    }
    const cards = element("div", "test-cards");
    const scores = t.scores;
    const best = ["models", "market"].reduce((a, b) => (scores[b] < scores[a] ? b : a));
    for (const key of ["models", "market", "table", "uniform"]) {
      const card = element("div", `test-card${key === best ? " is-best" : ""}`);
      card.append(element("span", "", word("testCards", key)), element("strong", "", I18N.number(scores[key], 4)), element("small", "", word("testSub", key)));
      cards.append(card);
    }
    box.append(cards, element("p", "calc-fine", say("kpi")));
    const won = t.verdict.better === "models" ? 7 - t.marketBetterSeasons : t.marketBetterSeasons;
    const verdict = element("p", "season-lede", word("verdict", t.verdict.better).replace("{won}", won));
    box.append(verdict);
    const wc = t.verdict.wellCalibrated;
    const calibText = wc.models && wc.market ? say("calibOk")
      : wc.models || wc.market ? say("calibOkOne", { who: say(wc.models ? "models" : "market"), other: say(wc.models ? "market" : "models") })
        : say("calibOff");
    box.append(element("p", "", calibText));
    if (!(wc.models && wc.market)) {
      const misses = element("ul", "calib-misses");
      for (const viewName of ["models", "market"]) {
        for (const bin of (t.calibration[viewName] ?? []).filter((b) => !b.ok && b.n >= 100)) {
          misses.append(element("li", "", say("calibMiss", { who: say(viewName), f: pct(bin.forecast), h: pct(bin.happened) })));
        }
      }
      if (misses.children.length) box.append(misses);
    }
    box.append(calibChart(t.calibration));
    const key = element("p", "season-key");
    key.append(element("span", "key-fill"), element("span", "", say("models")), element("span", "key-pin"), element("span", "", say("market")));
    key.querySelector(".key-fill").style.cssText = "width:10px;height:10px;border-radius:50%;background:var(--ink);";
    key.querySelector(".key-pin").style.cssText = "width:10px;height:10px;border-radius:50%;background:var(--bg);box-shadow:inset 0 0 0 1.8px var(--pin);margin-left:10px;";
    box.append(key);
    const doubt = element("p", "");
    doubt.textContent = say("doubt", {
      nodoubt: I18N.number(scores.models_nodoubt, 4), score: I18N.number(scores.models, 4),
      mnodoubt: I18N.number(scores.market_nodoubt, 4), mscore: I18N.number(scores.market, 4),
      sigma: I18N.number(t.chosen.models.sigma, 3), msigma: I18N.number(t.chosen.market.sigma, 3),
    });
    box.append(doubt);
    const by = t.byCheckpoint?.models;
    if (by) box.append(element("p", "", say("shrink", { first: I18N.number(by[0], 3), last: I18N.number(by[33], 3) })));
  }

  function calibChart(calibration) {
    const wrap = element("div", "calib");
    const width = Math.min(420, Math.max(280, document.querySelector("#any-good")?.clientWidth ?? 320));
    const height = width;
    const m = { top: 16, right: 24, bottom: 38, left: 56 };
    const pw = width - m.left - m.right;
    const ph = height - m.top - m.bottom;
    const x = (p) => m.left + p * pw;
    const y = (p) => m.top + ph - p * ph;
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true" });
    const grid = svg("g", { class: "chart-grid" });
    for (const p of [0, 0.25, 0.5, 0.75, 1]) {
      grid.append(svg("line", { x1: m.left, x2: m.left + pw, y1: y(p), y2: y(p), class: p === 0 ? "chart-baseline" : "" }));
      const ly = svg("text", { x: m.left - 8, y: y(p), class: "chart-tick", "text-anchor": "end", "dominant-baseline": "middle" });
      ly.textContent = new Intl.NumberFormat(I18N.locale, { style: "percent" }).format(p);
      const lx = svg("text", { x: x(p), y: m.top + ph + 16, class: "chart-tick", "text-anchor": "middle" });
      lx.textContent = new Intl.NumberFormat(I18N.locale, { style: "percent" }).format(p);
      grid.append(ly, lx);
    }
    const ax = svg("text", { x: m.left + pw / 2, y: height - 2, class: "chart-tick", "text-anchor": "middle" });
    ax.textContent = say("calibAxisX");
    const ay = svg("text", { x: 10, y: m.top + ph / 2, class: "chart-tick", "text-anchor": "middle", transform: `rotate(-90 10 ${m.top + ph / 2})` });
    ay.textContent = say("calibAxisY");
    grid.append(ax, ay);
    chart.append(grid, svg("line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), class: "calib-diag" }));
    const frame = element("div", "chart-frame");
    frame.append(chart);
    const tooltip = element("div", "chart-tooltip");
    tooltip.hidden = true;
    for (const viewName of ["market", "models"]) {
      for (const bin of calibration[viewName] ?? []) {
        const dot = svg("circle", { cx: x(bin.forecast), cy: y(bin.happened), r: 5, class: `calib-dot${viewName === "market" ? " is-market" : ""}`, tabindex: 0 });
        const show = () => {
          tooltip.replaceChildren(element("span", "tooltip-title", say(viewName)), element("span", "", say("calibTip", { f: pct(bin.forecast), h: pct(bin.happened), n: I18N.number(bin.n, 0) })));
          tooltip.hidden = false;
          tooltip.style.left = `${Math.min(width - 170, x(bin.forecast) + 10)}px`;
          tooltip.style.top = `${Math.max(4, y(bin.happened) - 40)}px`;
        };
        dot.addEventListener("pointerenter", show);
        dot.addEventListener("focus", show);
        dot.addEventListener("pointerleave", () => { tooltip.hidden = true; });
        dot.addEventListener("blur", () => { tooltip.hidden = true; });
        chart.append(dot);
      }
    }
    frame.append(tooltip);
    wrap.append(frame);
    return wrap;
  }

  /* ---------- Live results ---------- */

  async function loadLive() {
    const d = state.data;
    try {
      const matches = await json(`${API}/getmatchdata/bl1/${encodeURIComponent(d.season)}`);
      if (!Array.isArray(matches)) return;
      const byId = new Map(matches.map((m) => [Number(m.matchID), m]));
      for (const m of matches) {
        for (const team of [m.team1, m.team2]) if (team?.teamId && team.teamIconUrl) state.crests.set(String(team.teamId), team.teamIconUrl);
      }
      const fixed = {};
      d.fixtures.forEach((fx, index) => {
        const m = byId.get(Number(fx.id));
        if (!m?.matchIsFinished) return;
        const final = (m.matchResults ?? []).find((r) => r.resultTypeID === 2);
        if (final) fixed[index] = [Number(final.pointsTeam1), Number(final.pointsTeam2)];
      });
      const count = Object.keys(fixed).length;
      if (!count) {
        renderAll();
        return;
      }
      state.liveFixed = fixed;
      state.liveCount = count;
      const [models, market] = await Promise.all([simulate(jobFor("models", fixed)), simulate(jobFor("market", fixed))]);
      state.live = { models, market };
      renderAll();
    } catch {
      // Offline or OpenLigaDB down: the published numbers stand.
    }
  }

  /* ---------- Start ---------- */

  function renderAll() {
    if (!state.data) return;
    renderStamp();
    renderTitle();
    renderTable();
    renderStakes();
    renderWhatIf();
    renderNow();
    renderLines();
    renderSettled();
    renderReplay();
    renderTest();
  }

  function showError(message) {
    const node = document.querySelector("#season-error");
    node.textContent = message;
    node.hidden = false;
  }

  async function start() {
    document.querySelector("#season-view-switch").addEventListener("click", (event) => {
      const button = event.target.closest("[data-view]");
      if (!button || button.dataset.view === state.view) return;
      state.view = button.dataset.view;
      store(VIEW_KEY, state.view === "market" ? "market" : null);
      state.keyClubs = { now: null, replay: null };
      renderAll();
      if (state.picks.size) scheduleWhatIf();
    });
    document.querySelector("#whatif-prev").addEventListener("click", () => {
      const mds = matchdays();
      state.whatifMd = mds[Math.max(0, mds.indexOf(state.whatifMd) - 1)];
      renderWhatIf();
    });
    document.querySelector("#whatif-next").addEventListener("click", () => {
      const mds = matchdays();
      state.whatifMd = mds[Math.min(mds.length - 1, mds.indexOf(state.whatifMd) + 1)];
      renderWhatIf();
    });
    document.querySelector("#whatif-reset").addEventListener("click", () => {
      state.picks.clear();
      renderWhatIf();
      scheduleWhatIf();
    });
    document.querySelector("#whatif-favourites").addEventListener("click", () => {
      state.data.fixtures.forEach((fx, index) => {
        if (fx.md !== state.whatifMd || Array.isArray(state.liveFixed[index])) return;
        const probs = outcomeProbs(fx);
        state.picks.set(index, ["H", "D", "A"][probs.indexOf(Math.max(...probs))]);
      });
      renderWhatIf();
      scheduleWhatIf();
    });

    try {
      state.data = await json(DATA_URL);
    } catch {
      showError(say("loadError"));
      return;
    }
    if (!state.data?.views) {
      showError(say("noData"));
      return;
    }
    renderAll();
    json(TEST_URL).then((test) => {
      state.test = test;
      renderTest();
    }).catch(() => {});
    loadLive();
    const replays = document.querySelector("#replays");
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          loadReplays();
        }
      }, { rootMargin: "600px" });
      observer.observe(replays);
    } else {
      loadReplays();
    }
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (!state.data) return;
      renderNow();
      renderReplay();
      renderSettled();
      if (state.openClub) renderTable();
    }, 200);
  });

  I18N.onChange(renderAll);
  start();
})();
