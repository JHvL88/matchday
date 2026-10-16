/*
 * The Learn page: an odds calculator, a "grade it yourself" box and the glossary.
 * Loaded after i18n.js, glossary.js and explain.js. The prose is in the HTML (one copy per language);
 * the few words these widgets need live here.
 */
(() => {
  "use strict";

  const I18N = window.I18N;
  const GLOSSARY = window.GLOSSARY;

  const WORDS = {
    en: {
      oddsTitle: "Odds calculator",
      gradeTitle: "Grade it yourself",
      outcome: "Outcome",
      home: "Home win",
      draw: "Draw",
      away: "Away win",
      odds: "Odds",
      implied: "1 ÷ odds",
      market: "Market probability",
      fair: "Fair odds",
      yours: "Your chance",
      expected: "Expected return on €1",
      marginNote: "The three add up to {total}: a bookmaker’s margin of {margin}.",
      sumNote: "Your chances add up to {total}. They should make 100%.",
      invalid: "Odds have to be above 1.00.",
      reset: "Reset to the latest deep dive",
      source: "{match} · {bookmaker}",
      sourceNoBook: "{match} · bookmaker odds",
      result: "Pick a result",
      teamWin: "{team} win",
      models: "My models",
      bookies: "Bookmakers",
      shrug: "A shrug (⅓ each)",
      closerModels: "My models were closer, by {gap}.",
      closerMarket: "The bookmakers were closer, by {gap}.",
      level: "Dead level.",
      lower: "Ranked probability score, lower is better. Over a whole season a shrug averages about 0.238: it does well on draws and badly on everything else.",
      how: "How it’s calculated",
      howText: "Add the forecast up as you go (home win, then home win plus draw) and do the same for what happened, which is 0 or 1 at each step. Square the two gaps and average them. A draw sits between the two wins, so leaning the right way earns partial credit.",
      yourNote: "Your chance is a guess you type in. The expected return is your chance × the odds − €1, and it is only as good as the guess.",
    },
    de: {
      oddsTitle: "Quotenrechner",
      gradeTitle: "Selbst bewerten",
      outcome: "Ausgang",
      home: "Heim\u00adsieg",
      draw: "Remis",
      away: "Auswärts\u00adsieg",
      odds: "Quote",
      implied: "1 ÷ Quote",
      market: "Markt\u00adwahrscheinlichkeit",
      fair: "Faire Quote",
      yours: "Deine Chance",
      expected: "Erwarteter Ertrag auf 1 €",
      marginNote: "Zusammen ergeben die drei {total}: eine Buchmachermarge von {margin}.",
      sumNote: "Deine Chancen ergeben zusammen {total}. Es sollten 100 % sein.",
      invalid: "Quoten müssen über 1,00 liegen.",
      reset: "Zurück zur neuesten Analyse",
      source: "{match} · {bookmaker}",
      sourceNoBook: "{match} · Buchmacherquoten",
      result: "Ergebnis wählen",
      teamWin: "Sieg {team}",
      models: "Meine Modelle",
      bookies: "Buchmacher",
      shrug: "Schulterzucken (je ⅓)",
      closerModels: "Meine Modelle lagen näher dran, um {gap}.",
      closerMarket: "Die Buchmacher lagen näher dran, um {gap}.",
      level: "Exakt gleichauf.",
      lower: "Ranked Probability Score, niedriger ist besser. Über eine ganze Saison kommt ein Schulterzucken auf etwa 0,238: Bei Remis steht es gut da, bei allem anderen schlecht.",
      how: "So wird gerechnet",
      howText: "Man summiert die Prognose schrittweise auf (Heimsieg, dann Heimsieg plus Remis) und macht dasselbe mit dem, was passiert ist, also 0 oder 1 bei jedem Schritt. Die beiden Abstände quadriert man und bildet den Mittelwert. Ein Remis liegt zwischen den beiden Siegen, deshalb gibt es Teilpunkte für die richtige Tendenz.",
      yourNote: "Deine Chance ist eine Schätzung, die du eintippst. Der erwartete Ertrag ist deine Chance × Quote − 1 €, und er ist nur so gut wie die Schätzung.",
    },
  };

  // The latest deep dive at the time of writing, in case posts.json cannot be read.
  let fixture = {
    match: "Hamburger SV – VfB Stuttgart",
    home: "Hamburger SV",
    away: "VfB Stuttgart",
    bookmaker: "Bet365",
    odds: [3.8, 4.2, 1.8],
    model: [0.32, 0.24, 0.44],
    market: [0.249, 0.225, 0.526],
  };

  const calc = { odds: fixture.odds.map(String), yours: fixture.model.map((p) => String(Math.round(p * 100))) };
  let picked = null;
  let edited = false;

  const say = (key, params = {}) => (WORDS[I18N.lang]?.[key] ?? WORDS.en[key]).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const pct = (value, digits = 1) => new Intl.NumberFormat(I18N.locale, { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
  const euro = (value) => new Intl.NumberFormat(I18N.locale, { style: "currency", currency: "EUR", signDisplay: "exceptZero" }).format(value);

  // Accepts 3.80 and 3,80.
  function parse(text) {
    const value = Number(String(text).trim().replace(",", "."));
    return Number.isFinite(value) ? value : NaN;
  }

  function display(text, digits) {
    const value = parse(text);
    return Number.isFinite(value) ? I18N.number(value, digits) : text;
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

  /* ---------- Odds calculator ---------- */

  const oddsBox = document.getElementById("odds-calc");
  const cells = {};

  function input(kind, index, digits) {
    const field = element("input", "calc-input");
    field.type = "text";
    field.inputMode = "decimal";
    field.autocomplete = "off";
    field.spellcheck = false;
    field.value = display(calc[kind][index], digits);
    field.dataset.kind = kind;
    field.dataset.index = String(index);
    field.addEventListener("input", () => {
      edited = true;
      calc[kind][index] = field.value;
      updateOdds();
    });
    field.addEventListener("change", () => {
      if (Number.isFinite(parse(field.value))) field.value = display(field.value, digits);
    });
    return field;
  }

  function buildOdds() {
    if (!oddsBox) return;
    const head = element("div", "calc-head");
    head.append(element("p", "calc-title", say("oddsTitle")), element("p", "calc-source", fixture.bookmaker ? say("source", fixture) : say("sourceNoBook", fixture)));
    const reset = element("button", "calc-reset", say("reset"));
    reset.type = "button";
    reset.addEventListener("click", () => {
      calc.odds = fixture.odds.map(String);
      calc.yours = fixture.model.map((p) => String(Math.round(p * 100)));
      buildOdds();
    });

    const scroll = element("div", "calc-scroll");
    const table = element("table", "calc-table");
    const thead = element("thead");
    const headRow = element("tr");
    headRow.append(element("th", "", ""));
    for (const key of ["home", "draw", "away"]) {
      const th = element("th", `calc-col calc-${key}`, say(key));
      th.scope = "col";
      headRow.append(th);
    }
    thead.append(headRow);
    const body = element("tbody");
    const rows = [
      ["odds", "odds"], ["implied", "implied"], ["market", "market"], ["fair", "fair"], ["yours", "yours"], ["expected", "expected"],
    ];
    for (const [key, label] of rows) {
      const row = element("tr", `calc-row-${key}`);
      const th = element("th", "", "");
      th.scope = "row";
      if (key === "market" || key === "fair") {
        const term = element("button", "term", say(label));
        term.type = "button";
        term.dataset.term = key === "market" ? "market-probability" : "fair-odds";
        th.append(term);
      } else if (key === "yours") {
        th.append(say(label), element("span", "calc-unit", " (%)"));
      } else {
        th.textContent = say(label);
      }
      row.append(th);
      cells[key] = [];
      for (let index = 0; index < 3; index += 1) {
        const td = element("td");
        if (key === "odds") td.append(input("odds", index, 2));
        else if (key === "yours") td.append(input("yours", index, 0));
        else cells[key][index] = td;
        row.append(td);
      }
      body.append(row);
    }
    table.append(thead, body);
    scroll.append(table);

    const bar = element("div", "calc-bar");
    bar.setAttribute("aria-hidden", "true");
    cells.bar = [0, 1, 2].map((index) => {
      const part = element("span", `calc-bar-part part-${index}`);
      bar.append(part);
      return part;
    });
    cells.note = element("p", "calc-note");
    cells.sum = element("p", "calc-note calc-warning");
    const your = element("p", "calc-fine", say("yourNote"));
    oddsBox.replaceChildren(head, bar, scroll, cells.note, cells.sum, your, reset);
    updateOdds();
  }

  function updateOdds() {
    const odds = calc.odds.map(parse);
    const valid = odds.every((value) => value > 1);
    const fields = oddsBox.querySelectorAll('input[data-kind="odds"]');
    fields.forEach((field, index) => field.setAttribute("aria-invalid", String(!(odds[index] > 1))));
    if (!valid) {
      for (const key of ["implied", "market", "fair", "expected"]) cells[key].forEach((cell) => { cell.textContent = "–"; });
      cells.bar.forEach((part) => { part.style.flexGrow = "1"; part.textContent = ""; });
      cells.note.textContent = say("invalid");
      cells.sum.hidden = true;
      return;
    }
    const inverse = odds.map((value) => 1 / value);
    const total = inverse.reduce((sum, value) => sum + value, 0);
    const market = inverse.map((value) => value / total);
    const yours = calc.yours.map((text) => parse(text) / 100);
    odds.forEach((value, index) => {
      cells.implied[index].textContent = pct(inverse[index]);
      cells.market[index].textContent = pct(market[index]);
      cells.fair[index].textContent = I18N.number(1 / market[index], 2);
      const ev = Number.isFinite(yours[index]) ? yours[index] * value - 1 : NaN;
      cells.expected[index].textContent = Number.isFinite(ev) ? euro(Math.round(ev * 100) / 100) : "–";
      cells.expected[index].className = Number.isFinite(ev) && ev > 0.005 ? "is-positive" : Number.isFinite(ev) && ev < -0.005 ? "is-negative" : "";
      cells.bar[index].style.flexGrow = String(market[index]);
      cells.bar[index].textContent = market[index] >= 0.12 ? pct(market[index], 0) : "";
    });
    cells.note.textContent = say("marginNote", { total: pct(total), margin: pct(total - 1) });
    const yourTotal = yours.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
    cells.sum.hidden = Math.abs(yourTotal - 1) < 0.005;
    cells.sum.textContent = say("sumNote", { total: pct(yourTotal, 0) });
  }

  /* ---------- Grade it yourself ---------- */

  const gradeBox = document.getElementById("grade-calc");

  function buildGrade() {
    if (!gradeBox) return;
    const head = element("div", "calc-head");
    head.append(element("p", "calc-title", say("gradeTitle")), element("p", "calc-source", fixture.match));
    const choices = element("div", "grade-choices");
    choices.setAttribute("role", "group");
    choices.setAttribute("aria-label", say("result"));
    // Starts on the bookmakers' favourite winning, the most common way a match ends.
    if (picked === null) picked = fixture.market.indexOf(Math.max(...fixture.market));
    const labels = [say("teamWin", { team: fixture.home }), say("draw"), say("teamWin", { team: fixture.away })];
    labels.forEach((label, index) => {
      const button = element("button", `grade-choice part-${index}`, label);
      button.type = "button";
      button.setAttribute("aria-pressed", String(index === picked));
      button.addEventListener("click", () => {
        picked = index;
        buildGrade();
        gradeBox.querySelector(`.grade-choice.part-${index}`)?.focus();
      });
      choices.append(button);
    });

    const scores = [
      [say("models"), rps(fixture.model, picked), "is-models"],
      [say("bookies"), rps(fixture.market, picked), "is-market"],
      [say("shrug"), rps([1 / 3, 1 / 3, 1 / 3], picked), "is-shrug"],
    ];
    const list = element("dl", "grade-scores");
    for (const [label, value, className] of scores) {
      const row = element("div", `grade-score ${className}`);
      const bar = element("span", "grade-bar");
      bar.style.setProperty("--w", `${Math.min(100, (value / 0.5) * 100)}%`);
      const dd = element("dd");
      dd.append(bar, element("span", "grade-value", I18N.number(value, 3)));
      row.append(element("dt", "", label), dd);
      list.append(row);
    }
    const gap = scores[0][1] - scores[1][1];
    const verdict = element("p", "grade-verdict",
      Math.abs(gap) < 0.0005 ? say("level") : say(gap < 0 ? "closerModels" : "closerMarket", { gap: I18N.number(Math.abs(gap), 3) }));
    const axis = element("p", "calc-fine", say("lower"));
    const how = element("details", "howto");
    how.append(element("summary", "", say("how")), element("p", "", say("howText")));
    gradeBox.replaceChildren(head, choices, list, verdict, axis, how);
  }

  /* ---------- Glossary ---------- */

  const glossaryList = document.getElementById("glossary-list");

  function buildGlossary() {
    if (!glossaryList || !GLOSSARY) return;
    const entries = GLOSSARY[I18N.lang] ?? GLOSSARY.en;
    glossaryList.replaceChildren(...GLOSSARY.order.filter((id) => entries[id]).map((id) => {
      const entry = entries[id];
      const item = element("article", "glossary-entry");
      item.id = id;
      const read = element("p", "glossary-read");
      read.append(element("strong", "", `${I18N.t("explain.howToRead")} `), entry.read);
      item.append(element("h3", "", entry.term), element("p", "", entry.short), read);
      return item;
    }));
  }

  /* ---------- Start ---------- */

  function renderAll() {
    buildOdds();
    buildGrade();
    buildGlossary();
  }

  async function loadFixture() {
    try {
      const response = await fetch("../analysis/posts.json", { cache: "no-cache" });
      if (!response.ok) return;
      const data = await response.json();
      const post = data.posts?.find((item) => item.forecast?.model && item.forecast?.market && item.forecast?.marketOdds);
      if (!post) return;
      const f = post.forecast;
      fixture = {
        match: `${post.home.name} – ${post.away.name}`,
        home: post.home.name,
        away: post.away.name,
        bookmaker: f.marketBookmaker ?? null,
        odds: f.marketOdds,
        model: f.model,
        market: f.market,
      };
      if (!edited) {
        calc.odds = fixture.odds.map(String);
        calc.yours = fixture.model.map((p) => String(Math.round(p * 100)));
      }
      renderAll();
    } catch {
      // The built-in example stays.
    }
  }

  renderAll();
  loadFixture();
  I18N.onChange(renderAll);

  // The glossary is drawn by this script, so an address like #rps is followed once it exists.
  const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target) requestAnimationFrame(() => target.scrollIntoView());
})();
