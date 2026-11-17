/*
 * Part two of the Learn page (learn/part-two/), loaded after learn.js and play.js:
 *
 *   - League of clones   18 identical clubs play a season; how spread out the table gets by luck alone,
 *                        against the real Bundesliga
 *   - Elo calculator     the real current ratings; pick a match and a result, watch the ratings move
 *   - Boldness dial      every published forecast since 2019/20, made bolder or shyer; calibration and score
 *   - Stake simulator    flat stakes, Kelly and its fractions when your belief about your edge is off
 *   - Penalty shoot-out  ten real past matches: you against my models and the bookmakers, graded on results
 *
 * The real numbers come from data/learn.json (analysis/pipeline/learn_data.py). The quick checks, the
 * progress strip and the shared pieces are in play.js; the prose is in the HTML.
 */
(() => {
  "use strict";

  const I18N = window.I18N;
  const { element, triSlider, rps, head, stat, button, barRow, svg, random, niceStep } = window.LEARN;
  const HERE = new URL(".", document.currentScript.src);
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)");

  const WORDS = {
    en: {
      draw: "Draw",
      teamWin: "{team} win",
      // League of clones
      cloneTitle: "League of clones",
      cloneSource: "18 identical clubs · home win {h}, draw {d}, away win {a}",
      clones: ["Real Coinflip", "Dynamo Dice", "Sporting Chance", "Athletic Fluke", "Inter Random", "Lucky Rovers",
        "FC Hunch", "Union Odds", "Borussia Hazard", "Fortuna Fifty", "Eintracht Toss", "Rapid Roll", "SV Shrug",
        "Olympic Lottery", "Wild Card United", "Bounce City", "Long Shot Town", "Snake Eyes 04"],
      newSeason: "Play a new season",
      playSeason: "Watch it unfold",
      afterMd: "After matchday {md}",
      matchday: "Matchday",
      leader: "Top",
      bottom: "Bottom",
      gap: "Gap",
      pts: { one: "{count} pt", other: "{count} pts" },
      cloneEarly: "After {md} matchdays {club} lead with {pts}. The papers would call it a title race. It is dice.",
      cloneEnd: "{club} are champions with {pts}, {gap} clear of the bottom. Nobody in this league is better than anybody else.",
      spreadTitle: "How spread out is the table?",
      real: "Real Bundesliga",
      cloneLine: "League of clones",
      spreadNote: "After {md} matchdays the clones are {ratio} as spread out as the real league.",
      spreadFine: "Spread: the standard deviation of the clubs’ points, roughly how far a typical club sits from the middle. Real: average of {n} complete seasons, {first} to {last}. Clones: average of {sims} simulated seasons.",
      axisMd: "matchday",
      tableAria: "Table of the league of clones after matchday {md}. {club} top with {pts}.",
      chartAria: "Spread of points by matchday. After 34 matchdays: real Bundesliga {real}, league of clones {clones}.",
      // Elo
      eloTitle: "Elo calculator",
      eloSource: "Real ratings after {date}",
      homeClub: "Home",
      awayClub: "Away",
      eloGap: "Gap, with 60 for home advantage: {gap}",
      expected: "Share of the points Elo expects",
      result: "Pick a result",
      eloMove: "{home} {dh} to {rh}, {away} {da} to {ra}.",
      eloNone: "Pick a result to see the ratings move. Press it again for a run of them.",
      resetElo: "Reset the ratings",
      ladder: "The ladder",
      ladderNote: "Dot: rating now. Faint dot: a year earlier.",
      eloFine: "Elo’s expected share counts a draw as half a win, so it is not the chance of winning. The ratings come from the same code that feeds XGBoost and move every matchday; these are as of {date}.",
      sameClub: "Pick two different clubs.",
      // Calibration
      calTitle: "Boldness dial",
      calSource: "{n} forecasts, {first} to {last}, made before kick-off",
      boldness: "Boldness",
      published: "as published",
      shy: "shyer",
      bold: "bolder",
      saidAxis: "Forecast",
      happenedAxis: "How often it happened",
      models: "My models",
      bookmakers: "Bookmakers",
      calScore: "Score at this setting",
      calPublished: "As published",
      calMarket: "Bookmakers",
      calNow: "As published: the dots hug the line. Shy between 60% and 80%, a touch brash above, but no setting of the dial does much better.",
      calBold: "Bolder: favourites now win less often than claimed, so the dots on the right sink below the line. The score is {worse} worse.",
      calShy: "Shyer: everything is squeezed towards a third, the dots tilt away from the line, and the score is {worse} worse.",
      findBest: "Find the best setting",
      calClose: "This close to the published setting the score hardly moves ({score}): the models are about as bold as they should be.",
      calBest: "Best setting: ×{b}, a score of {score}. Tuned on the same matches it is graded on, so even that tiny gain flatters. The bookmakers stay ahead at {market}: they know more, they are not braver.",
      calFine: "All three outcomes of every match, pooled into bins of ten points. Bigger dots: more forecasts. Score: ranked probability score, lower is better.",
      calAria: "Calibration chart at boldness {b}. Ranked probability score {score}.",
      tipBin: "Said {said}, happened {happened} ({n} forecasts)",
      // Staking
      stakeTitle: "Stake simulator",
      stakeSource: "€100, 500 bets at odds of 2.10, true chance 50%",
      belief: "What you think your chance is",
      beliefRight: "spot on",
      beliefHigh: "{gap} too optimistic",
      beliefLow: "{gap} too pessimistic",
      plan: "Staking plan",
      flat: "€2 a bet",
      half: "Half Kelly",
      kelly: "Kelly",
      double: "Double Kelly",
      stakeLine: "Kelly says: {f} of the pot on every bet.",
      stakeNone: "With that belief there is no edge, so Kelly says: don’t bet.",
      stakeFlat: "A flat €2 on every bet, whatever the pot.",
      median: "Typical pot after 500 bets",
      below: "Ended below €100",
      wiped: "Lost 90% or more",
      stakeAria: "{n} simulated bettors. Typical pot after 500 bets {median}; {below} end below €100.",
      stakeLegend: "Each line is one bettor (log scale). Dashed: the typical pot. Figures from 2,000 bettors.",
      stakeGood: "With an honest belief, Kelly grows the pot fastest. Even so, about {below} of bettors are behind after 500 bets.",
      stakeOver: "Too sure of yourself: Kelly bets {times} what the true edge supports and the typical bettor ends up with {median}.",
      stakeHalf: "Half the stake, much less pain: fractions of Kelly forgive a belief that is a little off.",
      stakeFlatLine: "Flat stakes are slow and steady. They also never grow with the pot.",
      stakeZero: "No bets, no losses. Sometimes that is the right answer.",
      stakeDouble: "Double Kelly earns no more than not betting at all, with far bigger swings. Over-betting is worse than under-betting.",
      rerun: "Run again",
      // Penalties
      penTitle: "Penalty shoot-out",
      penSource: "Ten real Bundesliga matches since 2019/20",
      kick: "Penalty {n} of {total}",
      penAsk: "Set your forecast, then shoot.",
      shoot: "Take the penalty",
      you: "You",
      finalScore: "Full time: {score}",
      scores: "{who} scores.",
      scoresTwo: "{a} and {b} score.",
      scoresAll: "Everybody scores.",
      nextKick: "Next penalty",
      finalWhistle: "Final whistle",
      shootout: "Penalties: you {you}, my models {models}, bookmakers {books}.",
      avgLine: "It is decided on the average score, like the track record: you {you}, my models {models}, bookmakers {books}. Lower wins.",
      penTrap: "Most goals, but not the best average. Hedging wins the draws and the upsets and quietly loses everything else, which is why the track record grades the average score and never counts wins.",
      longRun: "Over all {n} matches: bookmakers {books}, my models {models}, a shrug {shrug}.",
      penWin: "You won the shoot-out on average score. Ten matches is a small sample, but take the bow.",
      penLose: "Not your shoot-out. Over thousands of matches, nobody on this page beats the bookmakers either.",
      again: "Another shoot-out",
      penFine: "Closest forecast scores: the lowest ranked probability score for that match. My models’ forecasts are out of sample, as the track record grades them; bookmakers: closing average, margin removed.",
      scoreAria: "{who}: {goals} of {kicks}",
      noData: "The match data could not be loaded. Try again later.",
    },
    de: {
      draw: "Remis",
      teamWin: "Sieg {team}",
      cloneTitle: "Liga der Klone",
      cloneSource: "18 gleich starke Klubs · Heimsieg {h}, Remis {d}, Auswärtssieg {a}",
      clones: ["Real Münzwurf", "Dynamo Würfel", "Sporting Zufall", "Fortuna Glück", "Borussia Pech", "Eintracht Los",
        "FC Bauchgefühl", "Union Quote", "Rot-Weiß Roulette", "SV Schulterzucken", "Rapid Würfelbecher",
        "Olympia Lotterie", "Kickers Kopf oder Zahl", "TuS Tombola", "Wacker Wahrscheinlich", "Alemannia Ahnung",
        "Glücksritter 04", "VfL Vielleicht"],
      newSeason: "Neue Saison spielen",
      playSeason: "Saison ablaufen lassen",
      afterMd: "Nach dem {md}. Spieltag",
      matchday: "Spieltag",
      leader: "Spitze",
      bottom: "Ende",
      gap: "Abstand",
      pts: { one: "{count} Pkt.", other: "{count} Pkt." },
      cloneEarly: "Nach {md} Spieltagen führt {club} mit {pts}. Die Zeitungen würden von einem Titelrennen schreiben. Es ist Würfelglück.",
      cloneEnd: "{club} ist Meister mit {pts}, {gap} vor dem Letzten. Dabei ist in dieser Liga keiner besser als der andere.",
      spreadTitle: "Wie weit liegt die Tabelle auseinander?",
      real: "Echte Bundesliga",
      cloneLine: "Liga der Klone",
      spreadNote: "Nach {md} Spieltagen sind die Klone {ratio} so weit auseinander wie die echte Liga.",
      spreadFine: "Streuung: die Standardabweichung der Punkte, grob gesagt, wie weit ein typischer Klub von der Mitte entfernt ist. Echt: Schnitt aus {n} vollständigen Saisons, {first} bis {last}. Klone: Schnitt aus {sims} simulierten Saisons.",
      axisMd: "Spieltag",
      tableAria: "Tabelle der Liga der Klone nach dem {md}. Spieltag. {club} führt mit {pts}.",
      chartAria: "Streuung der Punkte nach Spieltagen. Nach 34 Spieltagen: echte Bundesliga {real}, Liga der Klone {clones}.",
      eloTitle: "Elo-Rechner",
      eloSource: "Echte Ratings nach dem {date}",
      homeClub: "Heim",
      awayClub: "Gast",
      eloGap: "Abstand, mit 60 für den Heimvorteil: {gap}",
      expected: "Anteil der Punkte, den Elo erwartet",
      result: "Ergebnis wählen",
      eloMove: "{home} {dh} auf {rh}, {away} {da} auf {ra}.",
      eloNone: "Ein Ergebnis wählen und zusehen, wie sich die Ratings bewegen. Mehrmals drücken ergibt eine Serie.",
      resetElo: "Ratings zurücksetzen",
      ladder: "Die Rangliste",
      ladderNote: "Punkt: Rating jetzt. Blasser Punkt: vor einem Jahr.",
      eloFine: "Elos erwarteter Anteil zählt ein Remis als halben Sieg, er ist also nicht die Siegchance. Die Ratings stammen aus demselben Code, der XGBoost füttert, und ändern sich jeden Spieltag; Stand {date}.",
      sameClub: "Zwei verschiedene Klubs wählen.",
      calTitle: "Mutregler",
      calSource: "{n} Prognosen, {first} bis {last}, abgegeben vor dem Anpfiff",
      boldness: "Mut",
      published: "wie veröffentlicht",
      shy: "zaghafter",
      bold: "forscher",
      saidAxis: "Prognose",
      happenedAxis: "Wie oft es eintrat",
      models: "Meine Modelle",
      bookmakers: "Buchmacher",
      calScore: "Score bei dieser Einstellung",
      calPublished: "Wie veröffentlicht",
      calMarket: "Buchmacher",
      calNow: "Wie veröffentlicht: Die Punkte liegen nah an der Linie. Zwischen 60 und 80 % etwas zaghaft, darüber etwas großspurig, aber keine Reglerstellung macht es deutlich besser.",
      calBold: "Forscher: Favoriten gewinnen jetzt seltener als behauptet, die Punkte rechts rutschen unter die Linie. Der Score wird um {worse} schlechter.",
      calShy: "Zaghafter: Alles wird Richtung ein Drittel gedrückt, die Punkte kippen von der Linie weg, und der Score wird um {worse} schlechter.",
      findBest: "Beste Einstellung suchen",
      calClose: "So nah an der veröffentlichten Einstellung bewegt sich der Score kaum ({score}): Die Modelle sind etwa so forsch, wie sie sein sollten.",
      calBest: "Beste Einstellung: ×{b}, ein Score von {score}. Optimiert auf denselben Spielen, auf denen bewertet wird, also schmeichelt selbst dieser winzige Gewinn. Die Buchmacher bleiben vorn mit {market}: Sie wissen mehr, mutiger sind sie nicht.",
      calFine: "Alle drei Ausgänge jedes Spiels, in Klassen von zehn Prozentpunkten. Größere Punkte: mehr Prognosen. Score: Ranked Probability Score, niedriger ist besser.",
      calAria: "Kalibrierungsgrafik bei Mut {b}. Ranked Probability Score {score}.",
      tipBin: "Gesagt {said}, eingetreten {happened} ({n} Prognosen)",
      stakeTitle: "Einsatz-Simulator",
      stakeSource: "100 €, 500 Wetten zur Quote 2,10, wahre Chance 50 %",
      belief: "Was du für deine Chance hältst",
      beliefRight: "genau richtig",
      beliefHigh: "{gap} zu optimistisch",
      beliefLow: "{gap} zu pessimistisch",
      plan: "Einsatzplan",
      flat: "2 € pro Wette",
      half: "Halber Kelly",
      kelly: "Kelly",
      double: "Doppelter Kelly",
      stakeLine: "Kelly sagt: {f} des Topfs auf jede Wette.",
      stakeNone: "Mit dieser Einschätzung gibt es keinen Vorteil, also sagt Kelly: nicht wetten.",
      stakeFlat: "Fest 2 € auf jede Wette, egal wie groß der Topf ist.",
      median: "Typischer Topf nach 500 Wetten",
      below: "Unter 100 € geendet",
      wiped: "90 % oder mehr verloren",
      stakeAria: "{n} simulierte Wettende. Typischer Topf nach 500 Wetten {median}; {below} enden unter 100 €.",
      stakeLegend: "Jede Linie ist eine Person (logarithmische Skala). Gestrichelt: der typische Topf. Kennzahlen aus 2.000 Wettenden.",
      stakeGood: "Mit ehrlicher Einschätzung lässt Kelly den Topf am schnellsten wachsen. Trotzdem liegen nach 500 Wetten etwa {below} hinten.",
      stakeOver: "Zu selbstsicher: Kelly setzt {times} so viel, wie der wahre Vorteil hergibt, und der typische Topf endet bei {median}.",
      stakeHalf: "Halber Einsatz, viel weniger Schmerz: Bruchteile von Kelly verzeihen eine Einschätzung, die etwas danebenliegt.",
      stakeFlatLine: "Feste Einsätze sind langsam und stetig. Mit dem Topf wachsen sie aber nie.",
      stakeZero: "Keine Wetten, keine Verluste. Manchmal ist das die richtige Antwort.",
      stakeDouble: "Doppelter Kelly bringt nicht mehr als gar nicht zu wetten, schwankt aber viel stärker. Zu viel setzen ist schlimmer als zu wenig.",
      rerun: "Noch mal laufen lassen",
      penTitle: "Elfmeterschießen",
      penSource: "Zehn echte Bundesligaspiele seit 2019/20",
      kick: "Elfmeter {n} von {total}",
      penAsk: "Prognose einstellen, dann schießen.",
      shoot: "Elfmeter schießen",
      you: "Du",
      finalScore: "Endstand: {score}",
      scores: "{who} trifft.",
      scoresTwo: "{a} und {b} treffen.",
      scoresAll: "Alle treffen.",
      nextKick: "Nächster Elfmeter",
      finalWhistle: "Schlusspfiff",
      shootout: "Elfmeter: du {you}, meine Modelle {models}, Buchmacher {books}.",
      avgLine: "Entschieden wird nach dem Score im Schnitt, wie in der Bilanz: du {you}, meine Modelle {models}, Buchmacher {books}. Niedriger gewinnt.",
      penTrap: "Die meisten Tore, aber nicht der beste Schnitt. Wer sich nicht festlegt, gewinnt die Remis und die Überraschungen und verliert still alles andere. Deshalb bewertet die Bilanz den Schnitt und zählt nie Siege.",
      longRun: "Über alle {n} Spiele: Buchmacher {books}, meine Modelle {models}, Schulterzucken {shrug}.",
      penWin: "Du hast das Elfmeterschießen nach Score gewonnen. Zehn Spiele sind wenig, aber die Verbeugung hast du dir verdient.",
      penLose: "Nicht dein Elfmeterschießen. Über Tausende Spiele schlägt hier allerdings auch sonst niemand die Buchmacher.",
      again: "Noch ein Elfmeterschießen",
      penFine: "Wer am nächsten dran ist, trifft: der niedrigste Ranked Probability Score für das Spiel. Die Prognosen meiner Modelle sind außerhalb der Stichprobe entstanden, so wie die Bilanz sie bewertet; Buchmacher: Schlussquoten im Schnitt, ohne Marge.",
      scoreAria: "{who}: {goals} von {kicks}",
      noData: "Die Spieldaten konnten nicht geladen werden. Bitte später noch einmal versuchen.",
    },
  };

  const words = () => WORDS[I18N.lang] ?? WORDS.en;
  function say(key, params = {}) {
    let text = words()[key] ?? WORDS.en[key];
    if (text && typeof text === "object" && !Array.isArray(text)) {
      text = text[new Intl.PluralRules(I18N.locale).select(params.count)] ?? text.other;
    }
    return String(text).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
  }
  const pct = (value) => I18N.percent(value);
  const pct1 = (value) => new Intl.NumberFormat(I18N.locale, { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value);
  const num = (value, digits = 0) => I18N.number(value, digits);
  const euro = (value) => new Intl.NumberFormat(I18N.locale, { style: "currency", currency: "EUR", maximumFractionDigits: value < 10 ? 2 : 0, minimumFractionDigits: 0 }).format(value);
  const signed = (value, digits = 1) => `${value > 0 ? "+" : value < 0 ? "−" : "±"}${num(Math.abs(value), digits)}`;
  const date = (iso, options = { day: "numeric", month: "long", year: "numeric" }) => I18N.dateFormat(`${iso}T12:00:00Z`, { ...options, timeZone: "Europe/Berlin" });
  const seasonLabel = (iso) => {
    const [year, month] = iso.split("-").map(Number);
    const start = month >= 7 ? year : year - 1;
    return `${start}/${String((start + 1) % 100).padStart(2, "0")}`;
  };

  let data = null;

  // A hover/tap readout for a chart: a small label that follows the pointer inside the chart's box.
  function tipLayer(box) {
    box.classList.add("has-tip");
    const tip = element("div", "chart-tip");
    tip.hidden = true;
    box.append(tip);
    return {
      show(text, x, y) {
        tip.textContent = text;
        tip.hidden = false;
        const width = box.clientWidth;
        tip.style.left = `${Math.max(4, Math.min(width - tip.offsetWidth - 4, x - tip.offsetWidth / 2))}px`;
        tip.style.top = `${Math.max(0, y - tip.offsetHeight - 10)}px`;
      },
      hide() { tip.hidden = true; },
    };
  }

  // Pointer position in SVG units.
  function svgPoint(node, event) {
    const matrix = node.getScreenCTM();
    if (!matrix) return null;
    return new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
  }

  /* ---------- League of clones ---------- */

  const cloneBox = document.getElementById("clone-toy");
  const CLUBS = 18;
  const SIMS = 400;
  const clone = { seed: 1, md: 34, points: null, average: null, timer: null };

  // A double round robin: 17 rounds by the circle method, then the same with home and away swapped.
  const SCHEDULE = (() => {
    let order = Array.from({ length: CLUBS }, (_, index) => index);
    const rounds = [];
    for (let round = 0; round < CLUBS - 1; round += 1) {
      const pairs = [];
      for (let index = 0; index < CLUBS / 2; index += 1) {
        const pair = [order[index], order[CLUBS - 1 - index]];
        pairs.push(round % 2 ? pair.reverse() : pair);
      }
      rounds.push(pairs);
      order = [order[0], order[CLUBS - 1], ...order.slice(1, CLUBS - 1)];
    }
    return [...rounds, ...rounds.map((pairs) => pairs.map(([home, away]) => [away, home]))];
  })();

  // points[md][club] after each matchday (md 0 = before the season).
  function playSeason(next, [home, draw]) {
    const points = [new Array(CLUBS).fill(0)];
    SCHEDULE.forEach((pairs) => {
      const row = [...points[points.length - 1]];
      for (const [h, a] of pairs) {
        const roll = next();
        if (roll < home) row[h] += 3;
        else if (roll < home + draw) { row[h] += 1; row[a] += 1; }
        else row[a] += 3;
      }
      points.push(row);
    });
    return points;
  }

  function spread(row) {
    const mean = row.reduce((sum, value) => sum + value, 0) / row.length;
    return Math.sqrt(row.reduce((sum, value) => sum + (value - mean) ** 2, 0) / row.length);
  }

  function buildClones() {
    if (!cloneBox || !data) return;
    const shares = data.table.homeDrawAway;
    if (!clone.average) {
      const next = random(2026);
      const sums = new Array(35).fill(0);
      for (let sim = 0; sim < SIMS; sim += 1) {
        playSeason(next, shares).forEach((row, md) => { sums[md] += spread(row); });
      }
      clone.average = sums.map((sum) => sum / SIMS);
    }
    if (!clone.points) clone.points = playSeason(random(clone.seed * 9973), shares);
    const names = words().clones;

    const top = head(say("cloneTitle"), say("cloneSource", { h: pct(shares[0]), d: pct(shares[1]), a: pct(shares[2]) }));
    const actions = element("div", "toy-actions");
    const play = button("toy-button is-primary", say("playSeason"), () => animate());
    actions.append(
      play,
      button("toy-button", say("newSeason"), () => {
        clone.seed += 1;
        clone.points = playSeason(random(clone.seed * 9973), shares);
        animate();
      }),
    );

    const sliderRow = element("label", "slider-row");
    const field = element("input", "tri-range");
    field.type = "range";
    field.min = "1";
    field.max = "34";
    field.step = "1";
    const out = element("output", "tri-value is-wide");
    sliderRow.append(element("span", "tri-label", say("matchday")), field, out);

    const stats = element("dl", "stats");
    const tiles = [stat(say("leader"), ""), stat(say("bottom"), ""), stat(say("gap"), "")];
    stats.append(...tiles.map((tile) => tile.node));
    const table = element("ol", "clone-table");
    table.setAttribute("role", "img");
    const line = element("p", "calc-note toy-line");
    line.setAttribute("aria-live", "polite");

    // The spread chart: real against clones, matchday by matchday.
    const chartBox = element("div", "line-chart");
    const tip = tipLayer(chartBox);
    const note = element("p", "calc-note");
    const legend = element("p", "bar-key line-key");
    legend.append(element("span", "key-real", say("real")), element("span", "key-clones", say("cloneLine")));

    let chart = null;
    function drawChart() {
      const width = Math.max(260, Math.round(chartBox.clientWidth || 320));
      const height = 200;
      const pad = { left: 30, right: 12, top: 12, bottom: 26 };
      const real = data.table.sd;
      const high = Math.ceil(Math.max(...real, ...clone.average) / 4) * 4;
      const x = (md) => pad.left + ((md - 1) / 33) * (width - pad.left - pad.right);
      const y = (value) => pad.top + (1 - value / high) * (height - pad.top - pad.bottom);
      const node = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "line-svg", role: "img" });
      node.setAttribute("aria-label", say("chartAria", { real: num(real[33], 1), clones: num(clone.average[34], 1) }));
      const axis = svg("g", { class: "long-axis" });
      for (let tick = 0; tick <= high; tick += 4) {
        axis.append(svg("line", { x1: pad.left, x2: width - pad.right, y1: y(tick), y2: y(tick), class: tick === 0 ? "is-zero" : "" }));
        const label = svg("text", { x: pad.left - 6, y: y(tick) + 4, "text-anchor": "end" });
        label.textContent = num(tick);
        axis.append(label);
      }
      for (const md of [1, 17, 34]) {
        const label = svg("text", { x: x(md), y: height - 6, "text-anchor": md === 1 ? "start" : md === 34 ? "end" : "middle" });
        label.textContent = md === 34 ? `34 ${say("axisMd")}` : String(md);
        axis.append(label);
      }
      const path = (values) => values.map((value, index) => `${index ? "L" : "M"}${x(index + 1).toFixed(1)},${y(value).toFixed(1)}`).join("");
      const marker = svg("line", { class: "line-marker", y1: pad.top, y2: height - pad.bottom });
      const dots = [svg("circle", { r: 4.5, class: "line-dot is-real" }), svg("circle", { r: 4.5, class: "line-dot is-clones" })];
      node.append(axis, marker,
        svg("path", { d: path(real), class: "line-real" }),
        svg("path", { d: path(clone.average.slice(1)), class: "line-clones" }), ...dots);
      const hit = svg("rect", { x: pad.left, y: 0, width: width - pad.left - pad.right, height, class: "line-hit" });
      node.append(hit);
      hit.addEventListener("pointermove", (event) => {
        const point = svgPoint(node, event);
        if (!point) return;
        const md = Math.min(34, Math.max(1, Math.round(1 + ((point.x - pad.left) / (width - pad.left - pad.right)) * 33)));
        tip.show(`${say("afterMd", { md })}: ${say("real")} ${num(real[md - 1], 1)} · ${say("cloneLine")} ${num(clone.average[md], 1)}`, x(md), y(real[md - 1]));
      });
      hit.addEventListener("pointerleave", () => tip.hide());
      chartBox.replaceChildren(node, chartBox.querySelector(".chart-tip") ?? element("div"));
      chart = { x, y, marker, dots };
    }

    function paint() {
      const md = clone.md;
      field.value = String(md);
      out.textContent = say("afterMd", { md });
      const row = clone.points[md];
      const order = row.map((value, index) => [index, value]).sort((a, b) => b[1] - a[1] || a[0] - b[0]);
      const most = Math.max(1, order[0][1]);
      table.replaceChildren(...order.map(([club, value], position) => {
        const item = element("li", `clone-row${position === 0 ? " is-top" : position >= CLUBS - 2 ? " is-bottom" : ""}`);
        const bar = element("span", "clone-bar");
        bar.style.setProperty("--w", `${(value / most) * 100}%`);
        item.append(element("span", "clone-pos", String(position + 1)), element("span", "clone-name", names[club]), bar, element("span", "clone-pts", num(value)));
        return item;
      }));
      const leader = order[0];
      const last = order[CLUBS - 1];
      table.setAttribute("aria-label", say("tableAria", { md, club: names[leader[0]], pts: say("pts", { count: leader[1] }) }));
      tiles[0].number.textContent = num(leader[1]);
      tiles[1].number.textContent = num(last[1]);
      tiles[2].number.textContent = num(leader[1] - last[1]);
      line.textContent = md === 34
        ? say("cloneEnd", { club: names[leader[0]], pts: say("pts", { count: leader[1] }), gap: say("pts", { count: leader[1] - last[1] }) })
        : say("cloneEarly", { md, club: names[leader[0]], pts: say("pts", { count: leader[1] }) });
      const ratio = clone.average[md] / data.table.sd[md - 1];
      note.textContent = say("spreadNote", { md, ratio: pct(ratio) });
      if (chart) {
        const cx = chart.x(md);
        chart.marker.setAttribute("x1", cx);
        chart.marker.setAttribute("x2", cx);
        chart.dots[0].setAttribute("cx", cx);
        chart.dots[0].setAttribute("cy", chart.y(data.table.sd[md - 1]));
        chart.dots[1].setAttribute("cx", cx);
        chart.dots[1].setAttribute("cy", chart.y(clone.average[md]));
      }
    }

    function animate() {
      clearInterval(clone.timer);
      if (calm.matches) {
        clone.md = 34;
        paint();
        return;
      }
      clone.md = 1;
      paint();
      clone.timer = setInterval(() => {
        clone.md += 1;
        paint();
        if (clone.md >= 34) clearInterval(clone.timer);
      }, 140);
    }

    field.addEventListener("input", () => {
      clearInterval(clone.timer);
      clone.md = Number(field.value);
      paint();
    });

    const t = data.table;
    cloneBox.replaceChildren(top, actions, sliderRow, stats, line, table,
      element("p", "chart-title", say("spreadTitle")), legend, chartBox, note,
      element("p", "calc-fine", say("spreadFine", { n: t.seasons, first: `${t.first}/${String((t.first + 1) % 100).padStart(2, "0")}`, last: `${t.last}/${String((t.last + 1) % 100).padStart(2, "0")}`, sims: num(SIMS) })));
    drawChart();
    paint();
    cloneBox.redraw = () => { drawChart(); paint(); };
  }

  /* ---------- Elo calculator ---------- */

  const eloBox = document.getElementById("elo-toy");
  const elo = { home: 1, away: 0, ratings: null, last: null };

  function eloExpected(home, away) {
    return 1 / (1 + 10 ** (-(home + data.elo.homeAdvantage - away) / 400));
  }

  // The update in analysis/pipeline/features.py: k = 20, more for a win by two or more.
  function eloUpdate(home, away, homeGoals, awayGoals) {
    const expected = eloExpected(home, away);
    const gd = homeGoals - awayGoals;
    const result = gd > 0 ? 1 : gd === 0 ? 0.5 : 0;
    const mult = Math.abs(gd) <= 1 ? 1 : Math.abs(gd) === 2 ? 1.5 : (11 + Math.abs(gd)) / 8;
    return data.elo.k * mult * (result - expected);
  }

  function buildElo() {
    if (!eloBox || !data) return;
    const clubs = data.elo.clubs;
    if (!elo.ratings) elo.ratings = clubs.map(([, rating]) => rating);
    const top = head(say("eloTitle"), say("eloSource", { date: date(data.elo.asOf) }));

    const picks = element("div", "elo-picks");
    const selects = ["homeClub", "awayClub"].map((key, side) => {
      const label = element("label", "toy-pick");
      const select = element("select", "toy-select");
      clubs.forEach(([name], index) => select.append(new Option(name, String(index))));
      select.value = String(side === 0 ? elo.home : elo.away);
      select.addEventListener("change", () => {
        elo[side === 0 ? "home" : "away"] = Number(select.value);
        elo.last = null;
        update();
      });
      label.append(element("span", "toy-pick-label", say(key)), select);
      picks.append(label);
      return select;
    });

    const gapLine = element("p", "calc-note");
    const expectedTitle = element("p", "chart-title", say("expected"));
    const bar = element("div", "calc-bar elo-bar");
    bar.setAttribute("aria-hidden", "true");
    const parts = [element("span", "calc-bar-part part-0"), element("span", "calc-bar-part part-2")];
    bar.append(...parts);
    const barKey = element("p", "bar-key");
    const keyHome = element("span", "key-0");
    const keyAway = element("span", "key-2");
    barKey.append(keyHome, keyAway);

    const results = element("div", "toy-actions");
    results.setAttribute("role", "group");
    results.setAttribute("aria-label", say("result"));
    results.append(element("span", "toy-actions-label", say("result")));
    for (const [h, a] of [[1, 0], [3, 0], [1, 1], [0, 1], [0, 3]]) {
      results.append(button("toy-chip", I18N.score(h, a), () => {
        if (elo.home === elo.away) return;
        const delta = eloUpdate(elo.ratings[elo.home], elo.ratings[elo.away], h, a);
        elo.ratings[elo.home] += delta;
        elo.ratings[elo.away] -= delta;
        elo.last = delta;
        update();
      }));
    }
    const move = element("p", "calc-note toy-line");
    move.setAttribute("aria-live", "polite");

    const ladderTitle = element("p", "chart-title", say("ladder"));
    const ladder = element("ol", "elo-ladder");
    const reset = button("toy-button is-quiet", say("resetElo"), () => {
      elo.ratings = clubs.map(([, rating]) => rating);
      elo.last = null;
      update();
    });

    function update() {
      const home = elo.ratings[elo.home];
      const away = elo.ratings[elo.away];
      const [homeName] = clubs[elo.home];
      const [awayName] = clubs[elo.away];
      selects[0].value = String(elo.home);
      selects[1].value = String(elo.away);
      if (elo.home === elo.away) {
        gapLine.textContent = say("sameClub");
      } else {
        const gap = home + data.elo.homeAdvantage - away;
        gapLine.textContent = say("eloGap", { gap: signed(Math.round(gap), 0) });
      }
      const expected = eloExpected(home, away);
      parts[0].style.flexGrow = String(expected);
      parts[1].style.flexGrow = String(1 - expected);
      parts[0].textContent = expected >= 0.12 ? num(expected, 2) : "";
      parts[1].textContent = 1 - expected >= 0.12 ? num(1 - expected, 2) : "";
      keyHome.textContent = `${homeName} ${num(expected, 2)}`;
      keyAway.textContent = `${awayName} ${num(1 - expected, 2)}`;
      move.textContent = elo.last === null ? say("eloNone") : say("eloMove", {
        home: homeName, away: awayName,
        dh: signed(elo.last), da: signed(-elo.last),
        rh: num(Math.round(home)), ra: num(Math.round(away)),
      });
      // The ladder: dots on one scale, a faint dot a year earlier.
      const all = [...elo.ratings, ...clubs.map(([, , before]) => before)];
      const low = Math.floor((Math.min(...all) - 10) / 50) * 50;
      const high = Math.ceil((Math.max(...all) + 10) / 50) * 50;
      const at = (value) => `${((value - low) / (high - low)) * 100}%`;
      const order = elo.ratings.map((rating, index) => [index, rating]).sort((a, b) => b[1] - a[1]);
      ladder.replaceChildren(...order.map(([index, rating], position) => {
        const [name, , before] = clubs[index];
        const item = element("li", `elo-row${index === elo.home || index === elo.away ? " is-picked" : ""}`);
        const track = element("span", "elo-track");
        const span = element("span", "elo-span");
        span.style.left = at(Math.min(rating, before));
        span.style.width = `calc(${at(Math.max(rating, before))} - ${at(Math.min(rating, before))})`;
        const then = element("span", "elo-dot is-then");
        then.style.left = at(before);
        const now = element("span", "elo-dot");
        now.style.left = at(rating);
        track.append(span, then, now);
        item.append(element("span", "clone-pos", String(position + 1)), element("span", "elo-name", name), track,
          element("span", "elo-value", num(Math.round(rating))));
        item.title = `${name}: ${num(Math.round(rating))} (${signed(Math.round(rating - before), 0)})`;
        return item;
      }));
      const scale = element("li", "elo-row is-scale");
      scale.setAttribute("aria-hidden", "true");
      const ticks = element("span", "elo-track is-scale");
      // Three labels: both ends and the middle, so they never collide on a phone.
      for (const value of [low, Math.round((low + high) / 100) * 50, high]) {
        const tick = element("span", "elo-tick", String(value));
        tick.style.left = at(value);
        ticks.append(tick);
      }
      scale.append(element("span", "clone-pos", ""), element("span", "elo-name", ""), ticks, element("span", "elo-value", ""));
      ladder.append(scale);
    }

    eloBox.replaceChildren(top, picks, gapLine, expectedTitle, bar, barKey, results, move, ladderTitle,
      element("p", "calc-fine", say("ladderNote")), ladder, reset, element("p", "calc-fine", say("eloFine", { date: date(data.elo.asOf) })));
    update();
  }

  /* ---------- Boldness dial ---------- */

  const calBox = document.getElementById("cal-toy");
  const cal = { b: 1, message: null };
  let games = null; // [{ date, home, away, hg, ag, y, model: [h, d, a], market: [h, d, a] }]

  function decode() {
    if (games || !data) return;
    games = data.matches.map(([day, home, away, hg, ag, mh, md, kh, kd]) => ({
      date: day, home: data.clubs[home], away: data.clubs[away], hg, ag,
      y: hg > ag ? 0 : hg === ag ? 1 : 2,
      model: [mh / 1000, md / 1000, (1000 - mh - md) / 1000],
      market: [kh / 1000, kd / 1000, (1000 - kh - kd) / 1000],
    }));
  }

  // b > 1 sharpens a home/draw/away forecast, b < 1 flattens it towards a third each.
  function bolder(p, b) {
    const q = p.map((value) => Math.max(value, 1e-6) ** b);
    const sum = q[0] + q[1] + q[2];
    return q.map((value) => value / sum);
  }

  const meanRps = (pick) => games.reduce((sum, game) => sum + rps(pick(game), game.y), 0) / games.length;

  function bins(pick) {
    const out = Array.from({ length: 10 }, () => ({ said: 0, happened: 0, n: 0 }));
    for (const game of games) {
      pick(game).forEach((p, outcome) => {
        const bin = out[Math.min(9, Math.floor(p * 10))];
        bin.said += p;
        bin.happened += outcome === game.y ? 1 : 0;
        bin.n += 1;
      });
    }
    return out.filter((bin) => bin.n >= 20).map((bin) => ({ said: bin.said / bin.n, happened: bin.happened / bin.n, n: bin.n }));
  }

  function buildCalibration() {
    if (!calBox || !data) return;
    decode();
    cal.message = null;
    const top = head(say("calTitle"), say("calSource", { n: num(games.length), first: seasonLabel(games[0].date), last: date(games[games.length - 1].date, { month: "long", year: "numeric" }) }));
    const row = element("label", "slider-row has-ends");
    const field = element("input", "tri-range");
    field.type = "range";
    field.min = "0.5";
    field.max = "2";
    field.step = "0.01";
    field.value = String(cal.b);
    const out = element("output", "tri-value is-wide");
    const ends = element("span", "range-ends");
    ends.append(element("span", "", say("shy")), element("span", "", say("bold")));
    row.append(element("span", "tri-label", say("boldness")), field, ends, out);

    const chartBox = element("div", "cal-chart");
    const tip = tipLayer(chartBox);
    const legend = element("p", "bar-key line-key");
    legend.append(element("span", "key-dot", say("models")), element("span", "key-ring", say("bookmakers")));
    const stats = element("dl", "stats");
    const tiles = [stat(say("calScore"), ""), stat(say("calPublished"), ""), stat(say("calMarket"), "")];
    stats.append(...tiles.map((tile) => tile.node));
    const published = meanRps((game) => game.model);
    const market = meanRps((game) => game.market);
    tiles[1].number.textContent = num(published, 4);
    tiles[2].number.textContent = num(market, 4);
    const verdict = element("p", "calc-note toy-line");
    verdict.setAttribute("aria-live", "polite");
    const marketBins = bins((game) => game.market);

    function draw() {
      const b = cal.b;
      const pick = (game) => (b === 1 ? game.model : bolder(game.model, b));
      const score = meanRps(pick);
      const size = Math.max(240, Math.min(380, Math.round(chartBox.clientWidth || 300)));
      const pad = { left: 38, right: 10, top: 10, bottom: 34 };
      const inner = size - pad.left - pad.right;
      const x = (p) => pad.left + p * inner;
      const y = (p) => pad.top + (1 - p) * inner;
      const node = svg("svg", { viewBox: `0 0 ${size} ${inner + pad.top + pad.bottom}`, width: size, height: inner + pad.top + pad.bottom, class: "cal-svg", role: "img" });
      node.setAttribute("aria-label", say("calAria", { b: num(b, 2), score: num(score, 4) }));
      const axis = svg("g", { class: "long-axis" });
      for (let tick = 0; tick <= 1.0001; tick += 0.2) {
        axis.append(svg("line", { x1: x(0), x2: x(1), y1: y(tick), y2: y(tick) }));
        axis.append(svg("line", { x1: x(tick), x2: x(tick), y1: y(0), y2: y(1) }));
        const left = svg("text", { x: pad.left - 6, y: y(tick) + 4, "text-anchor": "end" });
        left.textContent = pct(tick);
        const bottom = svg("text", { x: x(tick), y: y(0) + 16, "text-anchor": tick === 0 ? "start" : tick > 0.99 ? "end" : "middle" });
        bottom.textContent = pct(tick);
        axis.append(left, bottom);
      }
      const xTitle = svg("text", { x: x(0.5), y: y(0) + 30, "text-anchor": "middle", class: "axis-title" });
      xTitle.textContent = say("saidAxis");
      const yTitle = svg("text", { x: x(0.02), y: y(0.97), "text-anchor": "start", class: "axis-title" });
      yTitle.textContent = say("happenedAxis");
      axis.append(xTitle, yTitle);
      const diagonal = svg("line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), class: "cal-diagonal" });
      const most = Math.max(...bins(pick).map((bin) => bin.n), ...marketBins.map((bin) => bin.n));
      const radius = (n) => 3.5 + 7 * Math.sqrt(n / most);
      const dots = svg("g");
      const addDot = (bin, className, who) => {
        const dot = svg("circle", { cx: x(bin.said), cy: y(bin.happened), r: radius(bin.n).toFixed(1), class: className });
        dot.addEventListener("pointerenter", () => tip.show(`${who}: ${say("tipBin", { said: pct(bin.said), happened: pct(bin.happened), n: num(bin.n) })}`, x(bin.said), y(bin.happened) - radius(bin.n)));
        dot.addEventListener("pointerleave", () => tip.hide());
        dots.append(dot);
      };
      // Rings on top of the dots, so the bookmakers stay visible where the two agree.
      bins(pick).forEach((bin) => addDot(bin, "cal-dot", say("models")));
      marketBins.forEach((bin) => addDot(bin, "cal-dot is-market", say("bookmakers")));
      node.append(axis, diagonal, dots);
      chartBox.replaceChildren(node, chartBox.querySelector(".chart-tip") ?? element("div"));
      out.textContent = `×${num(b, 2)}${Math.abs(b - 1) < 0.001 ? ` · ${say("published")}` : ""}`;
      tiles[0].number.textContent = num(score, 4);
      return score;
    }

    // A message from "Find the best setting" stays until the dial moves again (a redraw keeps it).
    function update() {
      const score = draw();
      const worse = score - published;
      verdict.textContent = cal.message ?? (Math.abs(cal.b - 1) < 0.001 ? say("calNow")
        : worse < 0.0002 ? say("calClose", { score: num(score, 4) })
          : say(cal.b > 1 ? "calBold" : "calShy", { worse: num(worse, 4) }));
    }

    field.addEventListener("input", () => {
      cal.b = Number(field.value);
      cal.message = null;
      update();
    });
    const best = button("toy-button", say("findBest"), () => {
      let bestB = 1;
      let bestScore = Infinity;
      for (let b = 0.8; b <= 1.3001; b += 0.01) {
        const score = meanRps((game) => bolder(game.model, b));
        if (score < bestScore) { bestScore = score; bestB = Math.round(b * 100) / 100; }
      }
      cal.b = bestB;
      field.value = String(cal.b);
      cal.message = say("calBest", { b: num(bestB, 2), score: num(bestScore, 4), market: num(market, 4) });
      update();
    });
    const actions = element("div", "toy-actions");
    actions.append(best);
    calBox.replaceChildren(top, row, legend, chartBox, stats, verdict, actions, element("p", "calc-fine", say("calFine")));
    update();
    calBox.redraw = () => update();
  }

  /* ---------- Stake simulator ---------- */

  const stakeBox = document.getElementById("stake-toy");
  const STAKE = { odds: 2.1, trueP: 0.5, bets: 500, start: 100, shown: 30, many: 2000 };
  const stake = { belief: 0.5, plan: "kelly", seed: 1 };
  const PLANS = ["flat", "half", "kelly", "double"];

  const kellyShare = (p, odds) => Math.max(0, (p * odds - 1) / (odds - 1));

  function share(plan, belief) {
    const k = kellyShare(belief, STAKE.odds);
    return plan === "half" ? k / 2 : plan === "double" ? Math.min(0.95, 2 * k) : plan === "kelly" ? k : 0;
  }

  // One bettor; returns the pot after every `every` bets. A pot below one cent counts as gone.
  function run(next, plan, belief, every) {
    const fraction = share(plan, belief);
    let pot = STAKE.start;
    const path = every ? [pot] : null;
    for (let bet = 1; bet <= STAKE.bets; bet += 1) {
      const amount = plan === "flat" ? Math.min(pot, 2) : fraction * pot;
      pot += next() < STAKE.trueP ? amount * (STAKE.odds - 1) : -amount;
      if (pot < 0.01) pot = 0.01;
      if (every && bet % every === 0) path.push(pot);
    }
    return every ? path : pot;
  }

  function buildStakes() {
    if (!stakeBox) return;
    const top = head(say("stakeTitle"), say("stakeSource"));
    const row = element("label", "slider-row");
    const field = element("input", "tri-range");
    field.type = "range";
    field.min = "45";
    field.max = "60";
    field.step = "0.5";
    field.value = String(stake.belief * 100);
    const out = element("output", "tri-value is-wide");
    row.append(element("span", "tri-label", say("belief")), field, out);

    const planRow = element("div", "slider-row");
    const seg = element("div", "segmented toy-seg is-four");
    seg.setAttribute("role", "group");
    seg.setAttribute("aria-label", say("plan"));
    const segButtons = PLANS.map((plan) => {
      const node = button("", say(plan), () => {
        stake.plan = plan;
        update();
      });
      seg.append(node);
      return { plan, node };
    });
    planRow.append(element("span", "tri-label", say("plan")), seg);
    const planLine = element("p", "calc-note");

    const chartBox = element("div", "long-chart");
    const stats = element("dl", "stats");
    const tiles = [stat(say("median"), ""), stat(say("below"), ""), stat(say("wiped"), "")];
    stats.append(...tiles.map((tile) => tile.node));
    const verdict = element("p", "calc-note toy-line");
    verdict.setAttribute("aria-live", "polite");

    function summary() {
      const next = random(4242 + Math.round(stake.belief * 1000) + PLANS.indexOf(stake.plan) * 7);
      const pots = Array.from({ length: STAKE.many }, () => run(next, stake.plan, stake.belief, 0)).sort((a, b) => a - b);
      return {
        median: pots[Math.floor(pots.length / 2)],
        below: pots.filter((pot) => pot < STAKE.start).length / pots.length,
        wiped: pots.filter((pot) => pot <= STAKE.start * 0.1).length / pots.length,
      };
    }

    function drawChart(median) {
      const width = Math.max(260, Math.round(chartBox.clientWidth || 320));
      const height = 230;
      const pad = { left: 52, right: 10, top: 10, bottom: 26 };
      const every = 5;
      const next = random(stake.seed * 31 + 7);
      const paths = Array.from({ length: STAKE.shown }, () => run(next, stake.plan, stake.belief, every));
      const values = paths.flat();
      const low = Math.max(-2, Math.floor(Math.log10(Math.min(...values, median, 50))));
      const high = Math.max(3, Math.ceil(Math.log10(Math.max(...values, median, 200))));
      const x = (index) => pad.left + (index / (paths[0].length - 1)) * (width - pad.left - pad.right);
      const y = (pot) => pad.top + ((high - Math.log10(pot)) / (high - low)) * (height - pad.top - pad.bottom);
      const node = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "long-svg", role: "img" });
      const axis = svg("g", { class: "long-axis" });
      for (let power = low; power <= high; power += 1) {
        const value = 10 ** power;
        axis.append(svg("line", { x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value), class: power === 2 ? "is-zero" : "" }));
        const label = svg("text", { x: pad.left - 6, y: y(value) + 4, "text-anchor": "end" });
        label.textContent = euro(value);
        axis.append(label);
      }
      for (const fraction of [0, 0.5, 1]) {
        const label = svg("text", { x: x((paths[0].length - 1) * fraction), y: height - 6, "text-anchor": fraction === 0 ? "start" : fraction === 1 ? "end" : "middle" });
        label.textContent = fraction === 1 ? `${num(STAKE.bets)} ${I18N.lang === "de" ? "Wetten" : "bets"}` : num(STAKE.bets * fraction);
        axis.append(label);
      }
      const lines = svg("g", { class: "long-lines" });
      for (const path of [...paths].sort((a, b) => a[a.length - 1] - b[b.length - 1])) {
        lines.append(svg("polyline", {
          points: path.map((pot, index) => `${x(index).toFixed(1)},${y(pot).toFixed(1)}`).join(" "),
          class: path[path.length - 1] > STAKE.start ? "is-up" : "is-down",
        }));
      }
      // The typical pot: the median at each step across the 30 bettors on screen.
      const typical = paths[0].map((_, index) => {
        const column = paths.map((path) => path[index]).sort((a, b) => a - b);
        return column[Math.floor(column.length / 2)];
      });
      const points = typical.map((pot, index) => `${x(index).toFixed(1)},${y(pot).toFixed(1)}`).join(" ");
      node.append(axis, lines, svg("polyline", { points, class: "long-mean-halo is-path" }), svg("polyline", { points, class: "long-mean is-path" }));
      chartBox.replaceChildren(node);
      return node;
    }

    function update() {
      const belief = stake.belief;
      const gap = belief - STAKE.trueP;
      out.textContent = `${pct1(belief)} · ${Math.abs(gap) < 0.001 ? say("beliefRight") : say(gap > 0 ? "beliefHigh" : "beliefLow", { gap: `${num(Math.abs(gap) * 100, 1)} ${I18N.lang === "de" ? "Punkte" : "points"}` })}`;
      segButtons.forEach((item) => item.node.setAttribute("aria-pressed", String(item.plan === stake.plan)));
      const fraction = share(stake.plan, belief);
      planLine.textContent = stake.plan === "flat" ? say("stakeFlat")
        : fraction <= 0 ? say("stakeNone")
          : say("stakeLine", { f: pct1(fraction) });
      const result = summary();
      tiles[0].number.textContent = euro(result.median);
      tiles[1].number.textContent = pct(result.below);
      tiles[2].number.textContent = pct(result.wiped);
      const node = drawChart(result.median);
      node.setAttribute("aria-label", say("stakeAria", { n: STAKE.shown, median: euro(result.median), below: pct(result.below) }));
      const trueKelly = kellyShare(STAKE.trueP, STAKE.odds);
      const over = stake.plan === "kelly" && gap > 0.004;
      verdict.textContent = stake.plan === "flat" ? say("stakeFlatLine")
        : fraction <= 0 ? say("stakeZero")
          : stake.plan === "double" ? say("stakeDouble")
            : stake.plan === "half" ? say("stakeHalf")
              : over ? say("stakeOver", { times: `${num(fraction / trueKelly, 1)}×`, median: euro(result.median) })
                : say("stakeGood", { below: pct(result.below) });
    }

    field.addEventListener("input", () => {
      stake.belief = Number(field.value) / 100;
      update();
    });
    const actions = element("div", "toy-actions");
    actions.append(button("toy-button", say("rerun"), () => {
      stake.seed += 1;
      update();
    }));
    stakeBox.replaceChildren(top, row, planRow, planLine, chartBox, element("p", "calc-fine", say("stakeLegend")), stats, verdict, actions);
    update();
    stakeBox.redraw = update;
  }

  /* ---------- Penalty shoot-out ---------- */

  const penBox = document.getElementById("penalty-toy");
  const KICKS = 10;
  const SHOOTERS = ["you", "models", "bookmakers"];
  let pen = null; // { picks: [game index], index, locked, guess, goals: [[bool x3]], scores: [[rps x3]] }
  const seen = new Set();

  function newShootout() {
    decode();
    const next = Math.random;
    const picks = [];
    if (seen.size > games.length - KICKS) seen.clear();
    while (picks.length < KICKS) {
      const index = Math.floor(next() * games.length);
      if (!seen.has(index)) {
        seen.add(index);
        picks.push(index);
      }
    }
    pen = { picks, index: 0, locked: false, guess: [0.33, 0.34, 0.33], goals: [], scores: [] };
  }

  function scoreboard() {
    const board = element("div", "pen-board");
    SHOOTERS.forEach((who, row) => {
      const line = element("div", "pen-row");
      const goals = pen.goals.filter((kick) => kick[row]).length;
      line.setAttribute("aria-label", say("scoreAria", { who: say(who), goals, kicks: pen.goals.length }));
      const balls = element("span", "pen-balls");
      for (let kick = 0; kick < KICKS; kick += 1) {
        const state = kick < pen.goals.length ? (pen.goals[kick][row] ? " is-goal" : " is-miss") : "";
        balls.append(element("span", `pen-ball${state}`));
      }
      line.append(element("span", "pen-who", say(who)), balls, element("span", "pen-total", String(goals)));
      board.append(line);
    });
    return board;
  }

  function buildPenalties() {
    if (!penBox) return;
    if (!data) return;
    decode();
    if (!pen) newShootout();
    const top = head(say("penTitle"), say("penSource"));
    const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length;

    if (pen.index >= KICKS) {
      const totals = SHOOTERS.map((_, row) => pen.goals.filter((kick) => kick[row]).length);
      const averages = SHOOTERS.map((_, row) => mean(pen.scores.map((kick) => kick[row])));
      const all = {
        n: num(games.length),
        books: num(meanRps((game) => game.market), 3),
        models: num(meanRps((game) => game.model), 3),
        shrug: num(meanRps(() => [1 / 3, 1 / 3, 1 / 3]), 3),
      };
      // Decided on the average score, as the track record is: counting kicks rewards shrugging at upsets.
      const won = averages[0] < Math.min(averages[1], averages[2]) - 0.0005;
      const mostGoals = totals[0] > Math.max(totals[1], totals[2]);
      const actions = element("div", "toy-actions");
      actions.append(button("toy-button is-primary", say("again"), () => {
        newShootout();
        buildPenalties();
        penBox.querySelector(".tri-range")?.focus();
      }));
      penBox.replaceChildren(top, element("p", "game-result", say("finalWhistle")), scoreboard(),
        element("p", "calc-note", say("shootout", { you: totals[0], models: totals[1], books: totals[2] })),
        element("p", "calc-note", say("avgLine", { you: num(averages[0], 3), models: num(averages[1], 3), books: num(averages[2], 3) })),
        element("p", "grade-verdict", say(won ? "penWin" : "penLose")),
        ...(mostGoals && !won ? [element("p", "calc-note", say("penTrap"))] : []),
        element("p", "calc-note", say("longRun", all)), actions, element("p", "calc-fine", say("penFine")));
      return;
    }

    const game = games[pen.picks[pen.index]];
    const count = element("p", "game-count", say("kick", { n: pen.index + 1, total: KICKS }));
    const name = element("p", "toy-match", `${game.home} – ${game.away}`);
    const when = element("p", "calc-source pen-date", `${date(game.date, { weekday: "long", day: "numeric", month: "long", year: "numeric" })} · ${seasonLabel(game.date)}`);
    const labels = [say("teamWin", { team: game.home }), say("draw"), say("teamWin", { team: game.away })];
    const children = [top, scoreboard(), count, name, when];

    if (!pen.locked) {
      const sliders = triSlider({ labels, value: pen.guess, onInput: (value) => { pen.guess = value; } });
      pen.guess = sliders.value;
      const actions = element("div", "toy-actions");
      actions.append(button("toy-button is-primary", say("shoot"), () => {
        const forecasts = [pen.guess, game.model, game.market];
        const scores = forecasts.map((p) => rps(p, game.y));
        const best = Math.min(...scores);
        pen.scores.push(scores);
        pen.goals.push(scores.map((value) => value <= best + 0.0005));
        pen.locked = true;
        buildPenalties();
        penBox.querySelector(".toy-button.is-primary")?.focus();
      }));
      children.push(element("p", "calc-note", say("penAsk")), sliders.node, actions);
    } else {
      const scores = pen.scores[pen.index];
      const goals = pen.goals[pen.index];
      const rows = element("div", "bar-rows");
      const teams = { home: game.home, away: game.away };
      rows.append(
        barRow(`${say("you")} · ${num(scores[0], 3)}`, pen.guess, teams),
        barRow(`${say("models")} · ${num(scores[1], 3)}`, game.model, teams, { key: true }),
        barRow(`${say("bookmakers")} · ${num(scores[2], 3)}`, game.market, teams, { outline: true }),
      );
      const key = element("p", "bar-key");
      labels.forEach((label, index) => key.append(element("span", `key-${index}${index === game.y ? " is-result" : ""}`, label)));
      const result = element("p", "pen-result", say("finalScore", { score: I18N.score(game.hg, game.ag) }));
      const scorers = SHOOTERS.filter((_, row) => goals[row]).map((who) => say(who));
      const verdict = element("p", "grade-verdict", scorers.length === 3 ? say("scoresAll")
        : scorers.length === 2 ? say("scoresTwo", { a: scorers[0], b: scorers[1] })
          : say("scores", { who: scorers[0] }));
      verdict.setAttribute("aria-live", "polite");
      const actions = element("div", "toy-actions");
      actions.append(button("toy-button is-primary", say(pen.index === KICKS - 1 ? "finalWhistle" : "nextKick"), () => {
        pen.index += 1;
        pen.locked = false;
        pen.guess = [0.33, 0.34, 0.33];
        buildPenalties();
        (penBox.querySelector(".tri-range") ?? penBox.querySelector(".toy-button"))?.focus();
      }));
      children.push(result, rows, key, verdict, actions);
    }
    children.push(element("p", "calc-fine", say("penFine")));
    penBox.replaceChildren(...children);
  }

  /* ---------- Start ---------- */

  function renderAll() {
    buildClones();
    buildElo();
    buildCalibration();
    buildStakes();
    buildPenalties();
  }

  function showError() {
    for (const box of [cloneBox, eloBox, calBox, penBox]) {
      if (box) box.replaceChildren(element("p", "calc-note", say("noData")));
    }
  }

  async function start() {
    buildStakes(); // needs no data
    try {
      const response = await fetch(new URL("../data/learn.json", HERE), { cache: "no-cache" });
      if (!response.ok) throw new Error(String(response.status));
      data = await response.json();
      renderAll();
    } catch {
      showError();
    }
    // Follow an address such as #elo again now that the boxes have their height.
    if (location.hash.length > 1) {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target && window.scrollY < 50) requestAnimationFrame(() => target.scrollIntoView({ behavior: "instant" }));
    }
  }

  I18N.onChange(() => (data ? renderAll() : buildStakes()));

  // Charts are drawn to the width of their box.
  if ("ResizeObserver" in window) {
    for (const box of [cloneBox, calBox, stakeBox]) {
      if (!box) continue;
      let last = 0;
      new ResizeObserver(() => {
        if (box.clientWidth !== last && box.redraw) {
          last = box.clientWidth;
          box.redraw();
        }
      }).observe(box);
    }
  }

  start();
})();
