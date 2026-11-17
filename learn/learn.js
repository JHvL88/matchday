/*
 * The Learn page: an odds calculator, a "grade it yourself" box and the glossary.
 * Loaded after i18n.js, glossary.js and explain.js. The prose is in the HTML (one copy per language);
 * the few words these widgets need live here. The other playthings and the quick checks are in
 * play.js, which uses the helpers this file leaves on window.LEARN.
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
      you: "You",
      yourForecast: "Your forecast",
      restDraw: "The draw gets the rest: {rest}",
      beatBoth: "You’d have beaten us both.",
      beatMarket: "You’d have beaten the bookmakers, but not my models.",
      beatModels: "You’d have beaten my models, but not the bookmakers.",
      beatNone: "We’d both have beaten you.",
      cheat: "Setting the sliders after you pick the result is cheating. It is also how most betting tips get sold.",
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
      you: "Du",
      yourForecast: "Deine Prognose",
      restDraw: "Der Rest bleibt fürs Remis: {rest}",
      beatBoth: "Du hättest uns beide geschlagen.",
      beatMarket: "Du hättest die Buchmacher geschlagen, meine Modelle aber nicht.",
      beatModels: "Du hättest meine Modelle geschlagen, die Buchmacher aber nicht.",
      beatNone: "Wir hätten dich beide geschlagen.",
      cheat: "Die Regler erst nach dem Ergebnis einzustellen ist geschummelt. So werden übrigens auch die meisten Wetttipps verkauft.",
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
  let pickedByHand = false;
  let edited = false;
  // The reader's own forecast in "Grade it yourself": starts as a shrug.
  let yours = [0.33, 0.34, 0.33];

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

  /*
   * A home/draw/away forecast set with two sliders: home win and away win, the draw gets the rest.
   * Pushing one slider past what is left pulls the other back. Used here and by play.js.
   */
  function triSlider({ labels, value, onInput }) {
    const node = element("div", "tri");
    const bar = element("div", "calc-bar tri-bar");
    bar.setAttribute("aria-hidden", "true");
    const parts = [0, 1, 2].map((index) => {
      const part = element("span", `calc-bar-part part-${index}`);
      bar.append(part);
      return part;
    });
    let current = value.map((p) => Math.round(p * 100));
    current[1] = 100 - current[0] - current[2];
    const rows = [0, 2].map((index) => {
      const row = element("label", `tri-row tri-${index === 0 ? "home" : "away"}`);
      const field = element("input", "tri-range");
      field.type = "range";
      field.min = "0";
      field.max = "100";
      field.step = "1";
      field.value = String(current[index]);
      const out = element("output", "tri-value");
      field.addEventListener("input", () => {
        const other = index === 0 ? 2 : 0;
        current[index] = Number(field.value);
        current[other] = Math.min(current[other], 100 - current[index]);
        current[1] = 100 - current[0] - current[2];
        paint();
        onInput?.(current.map((p) => p / 100));
      });
      row.append(element("span", "tri-label", labels[index]), field, out);
      return { index, field, out };
    });
    const rest = element("p", "tri-rest");
    function paint() {
      for (const row of rows) {
        row.field.value = String(current[row.index]);
        row.out.textContent = I18N.percent(current[row.index] / 100);
      }
      parts.forEach((part, index) => {
        part.style.flexGrow = String(Math.max(current[index], 0.001));
        part.textContent = current[index] >= 12 ? I18N.percent(current[index] / 100) : "";
      });
      rest.textContent = say("restDraw", { rest: I18N.percent(current[1] / 100) });
    }
    node.append(bar, rows[0].field.parentNode, rows[1].field.parentNode, rest);
    paint();
    return {
      node,
      get value() { return current.map((p) => p / 100); },
    };
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
    if (!pickedByHand) picked = fixture.market.indexOf(Math.max(...fixture.market));
    const labels = [say("teamWin", { team: fixture.home }), say("draw"), say("teamWin", { team: fixture.away })];
    const buttons = labels.map((label, index) => {
      const button = element("button", `grade-choice part-${index}`, label);
      button.type = "button";
      button.addEventListener("click", () => {
        picked = index;
        pickedByHand = true;
        update();
      });
      choices.append(button);
      return button;
    });

    const rows = [
      [say("models"), "is-models"],
      [say("bookies"), "is-market"],
      [say("you"), "is-you"],
      [say("shrug"), "is-shrug"],
    ].map(([label, className]) => {
      const row = element("div", `grade-score ${className}`);
      const bar = element("span", "grade-bar");
      const value = element("span", "grade-value");
      const dd = element("dd");
      dd.append(bar, value);
      row.append(element("dt", "", label), dd);
      return { row, bar, value };
    });
    const list = element("dl", "grade-scores");
    list.append(...rows.map((item) => item.row));
    const verdict = element("p", "grade-verdict");
    const yourVerdict = element("p", "grade-verdict is-you");

    const own = element("div", "grade-own");
    const sliders = triSlider({
      labels: [say("teamWin", { team: fixture.home }), say("draw"), say("teamWin", { team: fixture.away })],
      value: yours,
      onInput: (value) => {
        yours = value;
        update();
      },
    });
    yours = sliders.value;
    own.append(element("p", "grade-own-title", say("yourForecast")), sliders.node, element("p", "calc-fine", say("cheat")));

    function update() {
      buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(index === picked)));
      const scores = [rps(fixture.model, picked), rps(fixture.market, picked), rps(yours, picked), rps([1 / 3, 1 / 3, 1 / 3], picked)];
      rows.forEach((item, index) => {
        item.bar.style.setProperty("--w", `${Math.min(100, (scores[index] / 0.5) * 100)}%`);
        item.value.textContent = I18N.number(scores[index], 3);
      });
      const gap = scores[0] - scores[1];
      verdict.textContent = Math.abs(gap) < 0.0005 ? say("level") : say(gap < 0 ? "closerModels" : "closerMarket", { gap: I18N.number(Math.abs(gap), 3) });
      const beatsModels = scores[2] < scores[0] - 0.0005;
      const beatsMarket = scores[2] < scores[1] - 0.0005;
      yourVerdict.textContent = say(beatsModels && beatsMarket ? "beatBoth" : beatsMarket ? "beatMarket" : beatsModels ? "beatModels" : "beatNone");
    }

    const axis = element("p", "calc-fine", say("lower"));
    const how = element("details", "howto");
    how.append(element("summary", "", say("how")), element("p", "", say("howText")));
    gradeBox.replaceChildren(head, choices, list, verdict, own, yourVerdict, axis, how);
    update();
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

  // Shared with play.js.
  window.LEARN = { element, triSlider, rps };

  renderAll();
  loadFixture();
  I18N.onChange(renderAll);

  // The glossary is drawn by this script, so an address like #rps is followed once it exists.
  const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target) requestAnimationFrame(() => target.scrollIntoView());
})();
