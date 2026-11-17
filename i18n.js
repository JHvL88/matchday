/*
 * Language support for Jan’s Matchday (English and German).
 *
 * Loaded before app.js on the home page and on its own on the analysis pages. It:
 *   - picks the language: ?lang=de|en in the URL, else the saved choice, else the browser language;
 *   - translates static markup that carries data-i18n attributes (see apply());
 *   - exposes window.I18N so app.js can translate the text it builds at render time;
 *   - re-runs everything when the visitor presses the EN / DE switch in the top bar.
 *
 * To add a string: add the same key to both `messages.en` and `messages.de`.
 * Values are plain strings with {placeholders}, or { one, other } objects for plurals
 * (the number comes from the `count` parameter).
 */
(() => {
  "use strict";

  const STORAGE_KEY = "jans-matchday:lang";
  const SUPPORTED = ["en", "de"];
  const FALLBACK = "en";
  const LOCALES = { en: "en-GB", de: "de-DE" };

  const messages = {
    en: {
      /* Page and navigation */
      "meta.title": "Jan’s Matchday — Bundesliga results, table and analysis",
      "meta.description": "Jan’s Matchday: Bundesliga fixtures, live scores, the table, season insights and data-driven match analysis.",
      "lang.label": "Language",
      "nav.skip": "Skip to matches",
      "nav.skipArticle": "Skip to the article",
      "nav.label": "Sections",
      "nav.table": "Table",
      "brand.home": "Jan’s Matchday home",

      /* Hero */
      "hero.intro": "Forecasts, results and the table for every Bundesliga matchday, with the maths explained.",

      /* Matchday hub */
      "hub.prev": "Previous matchday",
      "hub.next": "Next matchday",
      "hub.titlePlaceholder": "Matchday",
      "hub.title": "Matchday {matchday}",
      "hub.datesTbc": "Dates to be confirmed",
      "hub.goTo": "Back to matchday {matchday}",
      "hub.updated": "Updated {time}",
      "hub.updateFailed": "Update failed · showing earlier scores",
      "hub.refresh": "Refresh",
      "hub.stripLabel": "Choose a matchday",
      "strip.aria": "Matchday {matchday}, {status}",
      "strip.ariaCurrent": "Matchday {matchday}, {status}, current",
      "strip.played": "played",
      "strip.partial": "in progress",
      "strip.live": "live now",
      "strip.upcoming": "upcoming",

      /* At a glance */
      "glance.label": "Matchday at a glance",
      "glance.goals": "Goals",
      "glance.results": "Results",
      "glance.biggestWin": "Biggest win",
      "glance.leader": "Top of the table",
      "glance.perMatch": "{avg} per match",
      "glance.season": "season {avg}",
      "glance.live": "{count} live",
      "glance.resultsSub": "Home wins · draws · away wins",
      "glance.noResults": "No results yet",
      "glance.allDraws": "Every result so far is a draw",
      "glance.margin": { one: "By {count} goal", other: "By {count} goals" },
      "glance.sameMargin": " · {count} more by the same margin",
      "glance.leaderClear": "{points} pts · {gap} clear",
      "glance.leaderGd": "{points} pts · top on goal difference",
      "glance.leaderNone": "The table starts with the first results",
      "glance.topClash": "Top clash",
      "glance.bottomClash": "Bottom clash",
      "glance.fixture": "{home} v {away}",
      "glance.positions": "{home} v {away}",
      "time.inMinutes": { one: "in {count} min", other: "in {count} min" },
      "time.inHours": "in {hours} h {minutes} min",
      "time.inDays": { one: "in {count} day", other: "in {count} days" },

      /* Fixtures */
      "fixtures.eyebrow": "Fixtures, forecasts and odds",
      "fixtures.title": "Matches",
      "fixtures.loading": "Finding the latest scores…",
      "fixtures.foot": "Kick-off times in Europe/Berlin · match data from",
      "filter.label": "Filter matches",
      "filter.all": "All",
      "filter.live": "Live",
      "filter.finished": "Finished",
      "filter.upcoming": "Upcoming",
      "match.fullTime": "Full time",
      "match.halfTime": "HT {score}",
      "match.live": "Live",
      "match.liveSecondHalf": "Live · 2nd half",
      "match.pending": "Result pending",
      "match.kickoff": "Kick-off",
      "match.dateTbc": "Date to be confirmed",
      "match.showDetails": "Show match details",
      "match.spectators": "{viewers} spectators",
      "match.goals": "Goals",
      "match.unknownScorer": "Unknown scorer",
      "match.ownGoal": "own goal",
      "match.penalty": "penalty",
      "match.scoredFor": " for {team}",
      "match.noGoals.goalless": "Goalless.",
      "match.noGoals.unavailable": "No goal details are available for this match.",
      "match.noGoals.live": "No goals reported yet.",
      "match.noGoals.pending": "Goal details are unavailable while the final result is pending.",
      "match.noGoals.upcoming": "Goals will appear here during the match.",
      "match.dive.badge": "Deep dive",
      "match.dive.forecast": "Forecast: {home} {h} · draw {d} · {away} {a}",
      "match.dive.read": "Read the deep dive",
      "empty.noMatches.title": "No matches yet",
      "empty.noMatches.text": "There are no matches listed for this matchday yet.",
      "empty.live.title": "No live matches",
      "empty.live.text": "Nothing is being played on matchday {matchday} right now.",
      "empty.finished.title": "No results yet",
      "empty.finished.text": "No match on matchday {matchday} has finished yet.",
      "empty.upcoming.title": "Nothing left to play",
      "empty.upcoming.text": "Every match on matchday {matchday} has kicked off.",
      "empty.showAll": "Show all matches",
      "error.scores.title": "Scores could not be loaded",
      "error.scores.text": "Please check your connection and try again.",
      "error.retry": "Try again",
      "error.standings.caption": "Standings unavailable",
      "error.standings.text": "Please refresh to load the match results.",

      /* Table */
      "table.eyebrow": "Standings",
      "table.title": "Table",
      "table.viewLabel": "Table view",
      "table.overall": "Overall",
      "table.home": "Home",
      "table.away": "Away",
      "table.loading": "Loading standings…",
      "table.captionDefault": "Bundesliga table",
      "table.col.position": "Position",
      "table.col.club": "Club",
      "table.col.played": "P",
      "table.col.playedTitle": "Played",
      "table.col.won": "W",
      "table.col.wonTitle": "Won",
      "table.col.drawn": "D",
      "table.col.drawnTitle": "Drawn",
      "table.col.lost": "L",
      "table.col.lostTitle": "Lost",
      "table.col.goals": "Goals",
      "table.col.gd": "GD",
      "table.col.gdTitle": "Goal difference",
      "table.col.points": "Pts",
      "table.col.pointsTitle": "Points",
      "table.col.form": "Form",
      "table.legend.label": "Table colour key",
      "table.legend.ucl": "Champions League",
      "table.legend.uel": "Europa League",
      "table.legend.uecl": "Conference League",
      "table.legend.playoff": "Relegation play-off",
      "table.legend.down": "Relegation",
      "table.note": "Calculated from completed results. Ties are split by goal difference, then goals scored. Tap a club to follow it across the page.",
      "table.venue.home": "Home table · ",
      "table.venue.away": "Away table · ",
      "table.caption": "{venue}After matchday {matchday}{progress}",
      "table.progressNone": " · no results from this matchday yet",
      "table.progressPending": { one: " · {count} match still to finish", other: " · {count} matches still to finish" },
      "table.ariaCaption.all": "Bundesliga table after matchday {matchday}",
      "table.ariaCaption.home": "Bundesliga home table after matchday {matchday}",
      "table.ariaCaption.away": "Bundesliga away table after matchday {matchday}",
      "table.empty": "No clubs listed for this season yet.",
      "table.follow": "Follow {team}",
      "table.unfollow": "Stop following {team}",
      "table.up": "Up {count} since matchday {matchday}",
      "table.down": "Down {count} since matchday {matchday}",
      "table.upSr": " up {count}",
      "table.downSr": " down {count}",
      "form.W": "W",
      "form.D": "D",
      "form.L": "L",
      "form.win": "win",
      "form.draw": "draw",
      "form.loss": "loss",
      "form.aria": "Last {count}: {results}",
      "form.none": "No matches yet",
      "form.titleHome": "Matchday {matchday}: {score} v {opponent}",
      "form.titleAway": "Matchday {matchday}: {score} at {opponent}",

      /* Insights */
      "insights.title": "Insights",
      "insights.eyebrow": "Season to date",
      "insights.eyebrowThrough": "Season to date · through matchday {matchday}",
      "insights.follow": "Follow",
      "insights.followTop": "Top of the table",
      "chart.showTable": "Show as table",
      "chart.points.title": "Points race",
      "chart.points.default": "Cumulative points after each matchday.",
      "chart.points.empty": "The points race starts with the first results.",
      "chart.points.aria": "Points race chart, {team} highlighted. Use the left and right arrow keys to step through matchdays.",
      "chart.points.start": "Start of the season",
      "chart.points.after": "After matchday {matchday}",
      "chart.points.pts": "{points} pts",
      "chart.points.position": "{ord}",
      "chart.points.leader": "{team} · leader",
      "chart.points.leadClear": {
        one: "{team} lead after matchday {matchday}, {count} point clear. Every other club in grey.",
        other: "{team} lead after matchday {matchday}, {count} points clear. Every other club in grey.",
      },
      "chart.points.leadGd": "{team} lead after matchday {matchday} on goal difference. Every other club in grey.",
      "chart.points.behind": {
        one: "{team} are {position}, {count} point behind {leader} after matchday {matchday}.",
        other: "{team} are {position}, {count} points behind {leader} after matchday {matchday}.",
      },
      "chart.points.colClub": "Club",
      "chart.points.colMatchday": "MD{matchday}",
      "chart.minutes.title": "When the goals go in",
      "chart.minutes.default": "Goals by match minute.",
      "chart.minutes.empty": "No goals recorded yet.",
      "chart.minutes.aria": "Goals by match minute",
      "chart.minutes.halfTime": "Half-time",
      "chart.minutes.range": "Minutes {label}",
      "chart.minutes.bar": { one: "Minutes {label}: {count} goal, {share}", other: "Minutes {label}: {count} goals, {share}" },
      "chart.minutes.tooltip": { one: "goal · {share} of the total", other: "goals · {share} of the total" },
      "chart.minutes.summary": "{goals} in {matches} ({avg} per match). The busiest spell is minutes {label}.",
      "chart.minutes.unknown": { one: " {count} without a recorded minute is left out.", other: " {count} without a recorded minute are left out." },
      "chart.minutes.colMinutes": "Minutes",
      "chart.minutes.colGoals": "Goals",
      "chart.minutes.colShare": "Share",

      /* Counts used inside other sentences */
      "count.matches": { one: "{count} match", other: "{count} matches" },
      "count.matchesIn": { one: "{count} match", other: "{count} matches" },
      "count.goals": { one: "{count} goal", other: "{count} goals" },

      /* Analysis */
      "analysis.eyebrow": "One match, three models, every week",
      "analysis.title": "Deep dives",
      /* Each post's <title> and meta description (the cards come from analysis/posts.json) */
      "analysis.pageTitleMd6": "Hamburg vs Stuttgart: the forecast — Jan’s Matchday",
      "analysis.metaMd6": "Pre-match forecast for Hamburger SV vs VfB Stuttgart, Bundesliga matchday 6 2026/27: three models against the bookmakers, and who has been right when they disagree.",
      "analysis.pageTitleMd6Bl": "Bayern vs Leipzig: the forecast — Jan’s Matchday",
      "analysis.metaMd6Bl": "Pre-match forecast for FC Bayern vs RB Leipzig, Bundesliga matchday 6 2026/27: three xG models against the bookmakers on a big favourite and a 4.5-goal line.",
      "analysis.pageTitleMd5": "Augsburg vs Bayern: the forecast — Jan’s Matchday",
      "analysis.metaMd5": "Pre-match forecast for FC Augsburg vs FC Bayern, Bundesliga matchday 5 2026/27: Dixon-Coles, a Bayesian shots-to-goals model and XGBoost, backtested against the bookmakers.",
      "analysis.back": "← All deep dives",
      "nav.skipPage": "Skip to the content",
      "learn.pageTitle": "How it works: probabilities, odds and grading — Jan’s Matchday",
      "learn.meta": "How the forecasts on Jan’s Matchday work: what a probability means, how to turn betting odds into chances, how forecasts are graded, and a glossary.",
      "record.pageTitle": "Track record: models v bookmakers — Jan’s Matchday",
      "record.meta": "The track record of Jan’s Matchday: every published Bundesliga forecast graded against the bookmakers after full time, plus the backtest and a paper-betting ledger.",

      /* Redesign: navigation, the weekend hub, forecasts, deep dives, track record */
      "nav.matchday": "Matchday",
      "nav.dives": "Deep dives",
      "nav.record": "Track record",
      "nav.learn": "Learn",
      "nav.main": "Main",
      "tab.matchday": "Matchday",
      "tab.table": "Table",
      "tab.dives": "Deep dives",
      "tab.record": "Record",
      "tab.learn": "Learn",
      "hub.when.current": "This weekend",
      "hub.when.past": "Results",
      "hub.when.future": "Coming up",
      "countdown.next": "Next kick-off",
      "countdown.startsIn": "Starts in",
      "countdown.hours": "h",
      "countdown.days": { one: "{count} day", other: "{count} days" },
      "countdown.live": "Live now",
      "countdown.liveCount": { one: "{count} match in play", other: "{count} matches in play" },
      "countdown.refreshing": "Scores refresh every minute",
      "countdown.status": "Status",
      "countdown.liveBadge": "Live",
      "countdown.complete": "Matchday complete",
      "countdown.completeGoals": "{goals} in {matches}",
      "countdown.nextMatchday": "Matchday {matchday} starts {date}",
      "follow.button": "Follow a club",
      "follow.change": "Following {team}. Change club",
      "follow.title": "Follow a club",
      "follow.text": "Your club is highlighted in the fixtures, the table and the charts. The choice stays on this device.",
      "follow.clear": "Stop following",
      "dialog.close": "Close",
      "featured.label": "Latest deep dive",
      "featured.tag": "Latest deep dive",
      "featured.played": "Played {date}",
      "featured.locked": "Locked {date}",
      "featured.v": "v",
      "featured.teamMeta": "{position} · {points}",
      "featured.mostLikely": "Most likely {score} ({p}%)",
      "featured.over25": "Over 2.5 goals {p}",
      "featured.btts": "Both score {p}",
      "featured.read": "Read the deep dive",
      "count.points": { one: "{count} pt", other: "{count} pts" },
      "prob.models": "My models",
      "prob.market": "Bookmakers",
      "prob.draw": "Draw",
      "prob.win": "{team} win",
      "prob.marketShort": "market {value}",
      "prob.fairOdds": "fair odds {value}",
      "prob.aria": "{home} win {h}, draw {d}, {away} win {a}",
      "legend.home": "Home win",
      "legend.draw": "Draw",
      "legend.away": "Away win",
      "legend.explain": "How to read a bar",
      "fixtures.oddsFoot": "odds: {sources}, margin removed",
      "odds.source": "{bookmaker}, {date}",
      "odds.sourceUnnamed": "bookmaker odds, {date}",
      "forecast.heading": "The forecast",
      "forecast.col.outcome": "Outcome",
      "forecast.col.market": "Bookmakers",
      "forecast.col.fair": "Fair odds",
      "forecast.col.odds": "Odds",
      "forecast.sourceLead": "Bookmakers: {source}, with the",
      "forecast.marginValue": "bookmaker margin of {margin}% removed",
      "forecast.margin": "bookmaker margin removed",
      "forecast.surprise": "The bookmakers gave this result {chance}, about 1 in {count}.",
      "forecast.fullTime": "Full time: {home} {score} {away}.",
      "forecast.gradeLead": "Graded by",
      "forecast.rps": "ranked probability score",
      "forecast.grade": "models {models}, market {market}.",
      "forecast.modelsCloser": "Models closer",
      "forecast.marketCloser": "Bookmakers closer",
      "forecast.tie": "Dead heat",
      "forecast.lessSure": "My models are less sure of {team} than the bookmakers.",
      "forecast.moreSure": "My models like {team} more than the bookmakers do.",
      "forecast.history": "In {count} past matches with a gap this big, the favourite won {actual}: the bookmakers said {market}, my models {models}. Lean towards the bookmakers.",
      "forecast.historyShort": "In past disagreements this big, the bookmakers have usually been closer.",
      "glance.favourite": "Biggest favourite",
      "glance.closest": "Closest call",
      "glance.vs": "v {team}",
      "glance.at": "at {team}",
      "glance.upset": "Biggest upset",
      "glance.upsetSub": "The market gave it {chance}, about 1 in {count}",
      "glance.seasonGoals": "Goals per match",
      "glance.seasonGoalsSub": { one: "this season, from {count} match", other: "this season, from {count} matches" },
      "analysis.minutes": { one: "{count} min read", other: "{count} min read" },
      "analysis.thumbResult": "the models gave this result {p}",
      "analysis.learnThumb": "How the models work",
      "analysis.learnTag": "Learn · start here",
      "analysis.learnTitle": "Probabilities, odds and why the bookies usually win",
      "analysis.learnDesc": "The three models, how a forecast gets graded, and a glossary for every number on this site.",
      "teaser.eyebrow": "Keeping score",
      "teaser.title": "Are the models any good?",
      "teaser.text": "Every forecast is graded after full time: how far were the percentages from what happened? The lower the score, the better.",
      "teaser.what": "How the score works",
      "teaser.link": "See every graded forecast",
      "teaser.seasonModels": "This season, models",
      "teaser.seasonMarket": "This season, market",
      "teaser.modelsAhead": "models ahead, for now",
      "teaser.marketAhead": "market ahead",
      "teaser.longRun": "Since 2019/20",
      "teaser.market": "Market",
      "teaser.models": "Models",
      "teaser.longRunSub": "{market} v {models} · {count} matches",
      "teaser.dives": "Deep dives graded",
      "teaser.divesSub": { one: "models closer in {count}", other: "models closer in {count}" },
      "explain.label": "Explainer",
      "explain.close": "Close the explanation",
      "explain.howToRead": "How to read it:",
      "explain.glossaryLink": "All terms in the glossary",
      "depth.label": "Reading depth",
      "depth.quick": "Quick take",
      "depth.full": "Full analysis",
      "depth.nerd": "Nerd mode",
      "depth.minutes": { one: "{count} min", other: "{count} min" },
      "toc.title": "On this page",
      "figure.enlarge": "Enlarge chart",
      "figure.close": "Close the chart",
      "figure.hint": "Swipe sideways to see the whole chart.",
      "footer.more": "More",
      "footer.howItWorks": "How it works",
      "footer.glossary": "Glossary",
      "footer.github": "Notebooks on GitHub",

      /* Footer */
      "footer.tagline": "Jan’s pitch. Bundesliga passion.",
      "footer.install": "On iPhone or iPad: tap <strong>Share</strong>, then <strong>Add to Home Screen</strong> to install Jan’s Matchday.",
      "footer.photos": "Background photos:",
      "footer.photoBall": "football on grass",
      "footer.by": "by",
      "footer.responsible": "18+. Forecasts are analysis, not betting advice. If betting stops being fun: <a href=\"https://www.check-dein-spiel.de/\" target=\"_blank\" rel=\"noreferrer\">check-dein-spiel.de</a> (Germany) · <a href=\"https://www.sos-spielsucht.ch/\" target=\"_blank\" rel=\"noreferrer\">sos-spielsucht.ch</a> (Switzerland).",

      /* The weekend board */
      "strip.caption": "{played} of {total} matchdays played",
      "board.title.both": { one: "{count} match, two opinions", other: "{count} matches, two opinions" },
      "board.title.done": "How the forecasts did",
      "board.intro.both": "Each bar is my models’ forecast. The two white pins show where the bookmakers would cut the same bar. Pins off the joins mean we disagree.",
      "board.intro.models": "Each bar is my models’ forecast for the match.",
      "board.intro.market": "My forecast for this matchday is not out yet. Until then the outlined bars show the bookmakers’ odds, turned into chances.",
      "board.intro.marketPast": "There was no model forecast for this matchday. The outlined bars show what the bookmakers expected before kick-off.",
      "board.intro.mixed": "An outlined bar means bookmakers only: no model forecast for that match.",
      "legend.pin": "Bookmakers’ split",
      "lead.argument.label": "Biggest argument this matchday",
      "lead.argument.team": "My models give {team} {models}, the bookmakers {market}.",
      "lead.argument.draw": "My models make a draw {models} likely, the bookmakers {market}.",
      "lead.agree.label": "No big arguments",
      "lead.agree.text": { one: "My models and the bookmakers are within {count} point of each other on every match.", other: "My models and the bookmakers are within {count} points of each other on every match." },
      "lead.market.label": "What the bookmakers expect",
      "lead.market.closest": "Closest call:",
      "lead.market.favourite": "Biggest favourite:",
      "lead.market.at": "at {chance}.",
      "lead.upset.label": "Biggest upset",
      "lead.upset.models": "My models gave this result {chance}, about 1 in {count}.",
      "lead.upset.market": "The bookmakers gave this result {chance}, about 1 in {count}.",
      "lead.results.label": "The matchday in numbers",
      "lead.results.split": "Home wins {h}, draws {d}, away wins {a}.",
      "row.bookmakers": "Bookmakers {h} / {d} / {a}",
      "row.gap": { one: "{count} point apart on {team}", other: "{count} points apart on {team}" },
      "row.theDraw": "the draw",
      "row.locked": "Forecast locked at kick-off",
      "row.modelsOnly": "No bookmaker odds for this match",
      "row.marketOnly": "Bookmakers only",
      "row.marketResult": "The bookmakers gave this result {chance}",
      "row.fullTime": "FT",
      "forecast.headingPast": "The forecast before kick-off",
      "hundred.models": "Play this match 100 times. On my models’ numbers {home} win about {h}, {d} end level and {away} win {a}.",
      "hundred.market": "Play this match 100 times. On the bookmakers’ odds {home} win about {h}, {d} end level and {away} win {a}.",
      "split.heading": "Three models, one average",
      "split.note": "Home win / draw / away win. My forecast is the plain average of the three.",
      "facts.heading": "Goals",
      "facts.xg": "Expected goals",
      "facts.likely": "Most likely score",
      "facts.over25": "Over 2.5 goals",
      "facts.btts": "Both teams score",
      "grid.caption": "Chance of each score in percent. {home} goals down the side, {away} along the top. The outlined cell is the likeliest.",
      "grid.captionFinal": "Chance of each score in percent, before kick-off. {home} goals down the side, {away} along the top. The dashed cell is the final score.",
      "grid.aria": "Score grid for {home} v {away}. Most likely: {score} at {p}.",
      "grade.heading": "How the forecast did",
      "grade.surpriseModels": "My models gave this result {chance}, about 1 in {count}.",
      "grade.term": "Ranked probability score:",
      "grade.note": "0 is perfect, so the shorter bar was closer.",
      "gauge.guess": "Pure guessing",
      "gauge.better": "Closer to what happened",
      "gauge.worse": "Further off",
      "gauge.longMarket": "The long run: {count} matches since 2019/20, every forecast made only with what was known before kick-off. The bookmakers are ahead.",
      "gauge.longModels": "The long run: {count} matches since 2019/20, every forecast made only with what was known before kick-off. My models are ahead.",
      "gauge.seasonAhead": { one: "This season, after {count} match, my models are ahead: {models} against the bookmakers’ {market}. Lovely, and proof of almost nothing yet.", other: "This season, after {count} matches, my models are ahead: {models} against the bookmakers’ {market}. Lovely, and proof of almost nothing yet." },
      "gauge.seasonBehind": { one: "This season, after {count} match, the bookmakers are ahead: {market} against my models’ {models}.", other: "This season, after {count} matches, the bookmakers are ahead: {market} against my models’ {models}." },
      "gauge.aria": "Ranked probability score over {count} matches, lower is better: bookmakers {market}, my models {models}, pure guessing {guess}.",
      "dive.latest": "Latest",
      "analysis.intro": "One match taken apart before kick-off, then marked after full time.",
      "analysis.learnLink": "New here? How the models work",
      "table.zone.mid": "Mid-table",
    },

    de: {
      /* Seite und Navigation */
      "meta.title": "Jan’s Matchday — Bundesliga-Ergebnisse, Tabelle und Analysen",
      "meta.description": "Jan’s Matchday: Bundesliga-Spielplan, Live-Ergebnisse, Tabelle, Saisonstatistiken und datengestützte Spielanalysen.",
      "lang.label": "Sprache",
      "nav.skip": "Zu den Spielen springen",
      "nav.skipArticle": "Zum Artikel springen",
      "nav.label": "Bereiche",
      "nav.table": "Tabelle",
      "brand.home": "Jan’s Matchday – Startseite",

      /* Hero */
      "hero.intro": "Prognosen, Ergebnisse und Tabelle zu jedem Bundesliga-Spieltag, mit der Mathematik dahinter erklärt.",

      /* Spieltag-Übersicht */
      "hub.prev": "Vorheriger Spieltag",
      "hub.next": "Nächster Spieltag",
      "hub.titlePlaceholder": "Spieltag",
      "hub.title": "Spieltag {matchday}",
      "hub.datesTbc": "Termine offen",
      "hub.goTo": "Zurück zu Spieltag {matchday}",
      "hub.updated": "Aktualisiert {time}",
      "hub.updateFailed": "Aktualisierung fehlgeschlagen · frühere Ergebnisse werden angezeigt",
      "hub.refresh": "Aktualisieren",
      "hub.stripLabel": "Spieltag wählen",
      "strip.aria": "Spieltag {matchday}, {status}",
      "strip.ariaCurrent": "Spieltag {matchday}, {status}, aktuell",
      "strip.played": "gespielt",
      "strip.partial": "läuft",
      "strip.live": "live",
      "strip.upcoming": "bevorstehend",

      /* Auf einen Blick */
      "glance.label": "Spieltag auf einen Blick",
      "glance.goals": "Tore",
      "glance.results": "Ergebnisse",
      "glance.biggestWin": "Höchster Sieg",
      "glance.leader": "Tabellenführer",
      "glance.perMatch": "{avg} pro Spiel",
      "glance.season": "Saison {avg}",
      "glance.live": "{count} live",
      "glance.resultsSub": "Heimsiege · Unentschieden · Auswärtssiege",
      "glance.noResults": "Noch keine Ergebnisse",
      "glance.allDraws": "Bisher endeten alle Spiele unentschieden",
      "glance.margin": { one: "{count} Tor Unterschied", other: "{count} Tore Unterschied" },
      "glance.sameMargin": " · {count} weitere mit gleichem Abstand",
      "glance.leaderClear": {
        one: "{points} Pkt. · {gap} Punkt Vorsprung",
        other: "{points} Pkt. · {gap} Punkte Vorsprung",
      },
      "glance.leaderGd": "{points} Pkt. · vorn nach Tordifferenz",
      "glance.leaderNone": "Die Tabelle startet mit den ersten Ergebnissen",
      "glance.topClash": "Spitzenspiel",
      "glance.bottomClash": "Kellerduell",
      "glance.fixture": "{home} – {away}",
      "glance.positions": "{home} gegen {away}",
      "time.inMinutes": { one: "in {count} Min.", other: "in {count} Min." },
      "time.inHours": "in {hours} Std. {minutes} Min.",
      "time.inDays": { one: "in {count} Tag", other: "in {count} Tagen" },

      /* Spiele */
      "fixtures.eyebrow": "Spiele, Prognosen und Quoten",
      "fixtures.title": "Spiele",
      "fixtures.loading": "Aktuelle Ergebnisse werden geladen…",
      "fixtures.foot": "Anstoßzeiten in Europe/Berlin (deutsche Zeit) · Spieldaten von",
      "filter.label": "Spiele filtern",
      "filter.all": "Alle",
      "filter.live": "Live",
      "filter.finished": "Beendet",
      "filter.upcoming": "Anstehend",
      "match.fullTime": "Endstand",
      "match.halfTime": "HZ {score}",
      "match.live": "Live",
      "match.liveSecondHalf": "Live · 2. Halbzeit",
      "match.pending": "Ergebnis ausstehend",
      "match.kickoff": "Anstoß",
      "match.dateTbc": "Termin offen",
      "match.showDetails": "Spieldetails anzeigen",
      "match.spectators": "{viewers} Zuschauer",
      "match.goals": "Tore",
      "match.unknownScorer": "Torschütze unbekannt",
      "match.ownGoal": "Eigentor",
      "match.penalty": "Elfmeter",
      "match.scoredFor": " für {team}",
      "match.noGoals.goalless": "Torlos.",
      "match.noGoals.unavailable": "Zu diesem Spiel liegen keine Tordetails vor.",
      "match.noGoals.live": "Noch keine Tore gemeldet.",
      "match.noGoals.pending": "Tordetails sind nicht verfügbar, solange das Endergebnis aussteht.",
      "match.noGoals.upcoming": "Die Tore erscheinen hier während des Spiels.",
      "match.dive.badge": "Analyse",
      "match.dive.forecast": "Prognose: {home} {h} · Remis {d} · {away} {a}",
      "match.dive.read": "Analyse lesen",
      "empty.noMatches.title": "Noch keine Spiele",
      "empty.noMatches.text": "Für diesen Spieltag sind noch keine Spiele angesetzt.",
      "empty.live.title": "Keine Live-Spiele",
      "empty.live.text": "An Spieltag {matchday} läuft gerade kein Spiel.",
      "empty.finished.title": "Noch keine Ergebnisse",
      "empty.finished.text": "An Spieltag {matchday} ist noch kein Spiel beendet.",
      "empty.upcoming.title": "Alles angepfiffen",
      "empty.upcoming.text": "Alle Spiele von Spieltag {matchday} wurden angepfiffen.",
      "empty.showAll": "Alle Spiele anzeigen",
      "error.scores.title": "Ergebnisse konnten nicht geladen werden",
      "error.scores.text": "Bitte Verbindung prüfen und erneut versuchen.",
      "error.retry": "Erneut versuchen",
      "error.standings.caption": "Tabelle nicht verfügbar",
      "error.standings.text": "Bitte aktualisieren, um die Spielergebnisse zu laden.",

      /* Tabelle */
      "table.eyebrow": "Tabellenstand",
      "table.title": "Tabelle",
      "table.viewLabel": "Tabellenansicht",
      "table.overall": "Gesamt",
      "table.home": "Heim",
      "table.away": "Auswärts",
      "table.loading": "Tabelle wird geladen…",
      "table.captionDefault": "Bundesliga-Tabelle",
      "table.col.position": "Platz",
      "table.col.club": "Verein",
      "table.col.played": "Sp",
      "table.col.playedTitle": "Spiele",
      "table.col.won": "S",
      "table.col.wonTitle": "Siege",
      "table.col.drawn": "U",
      "table.col.drawnTitle": "Unentschieden",
      "table.col.lost": "N",
      "table.col.lostTitle": "Niederlagen",
      "table.col.goals": "Tore",
      "table.col.gd": "Diff.",
      "table.col.gdTitle": "Tordifferenz",
      "table.col.points": "Pkt.",
      "table.col.pointsTitle": "Punkte",
      "table.col.form": "Form",
      "table.legend.label": "Farblegende der Tabelle",
      "table.legend.ucl": "Champions League",
      "table.legend.uel": "Europa League",
      "table.legend.uecl": "Conference League",
      "table.legend.playoff": "Relegation",
      "table.legend.down": "Abstieg",
      "table.note": "Berechnet aus abgeschlossenen Spielen. Bei Punktgleichheit entscheidet die Tordifferenz, danach die erzielten Tore. Verein antippen, um ihm auf der ganzen Seite zu folgen.",
      "table.venue.home": "Heimtabelle · ",
      "table.venue.away": "Auswärtstabelle · ",
      "table.caption": "{venue}Nach Spieltag {matchday}{progress}",
      "table.progressNone": " · noch keine Ergebnisse von diesem Spieltag",
      "table.progressPending": { one: " · noch {count} Spiel offen", other: " · noch {count} Spiele offen" },
      "table.ariaCaption.all": "Bundesliga-Tabelle nach Spieltag {matchday}",
      "table.ariaCaption.home": "Bundesliga-Heimtabelle nach Spieltag {matchday}",
      "table.ariaCaption.away": "Bundesliga-Auswärtstabelle nach Spieltag {matchday}",
      "table.empty": "Für diese Saison sind noch keine Vereine gelistet.",
      "table.follow": "{team} folgen",
      "table.unfollow": "{team} nicht mehr folgen",
      "table.up": { one: "{count} Platz höher seit Spieltag {matchday}", other: "{count} Plätze höher seit Spieltag {matchday}" },
      "table.down": { one: "{count} Platz tiefer seit Spieltag {matchday}", other: "{count} Plätze tiefer seit Spieltag {matchday}" },
      "table.upSr": { one: " {count} Platz höher", other: " {count} Plätze höher" },
      "table.downSr": { one: " {count} Platz tiefer", other: " {count} Plätze tiefer" },
      "form.W": "S",
      "form.D": "U",
      "form.L": "N",
      "form.win": "Sieg",
      "form.draw": "Unentschieden",
      "form.loss": "Niederlage",
      "form.aria": "Letzte {count}: {results}",
      "form.none": "Noch keine Spiele",
      "form.titleHome": "Spieltag {matchday}: {score} gegen {opponent}",
      "form.titleAway": "Spieltag {matchday}: {score} bei {opponent}",

      /* Statistik */
      "insights.title": "Statistik",
      "insights.eyebrow": "Saison bisher",
      "insights.eyebrowThrough": "Saison bisher · bis Spieltag {matchday}",
      "insights.follow": "Folgen",
      "insights.followTop": "Tabellenführer",
      "chart.showTable": "Als Tabelle anzeigen",
      "chart.points.title": "Punkteverlauf",
      "chart.points.default": "Gesammelte Punkte nach jedem Spieltag.",
      "chart.points.empty": "Der Punkteverlauf beginnt mit den ersten Ergebnissen.",
      "chart.points.aria": "Punkteverlauf, {team} hervorgehoben. Mit den Pfeiltasten nach links und rechts durch die Spieltage gehen.",
      "chart.points.start": "Saisonstart",
      "chart.points.after": "Nach Spieltag {matchday}",
      "chart.points.pts": "{points} Pkt.",
      "chart.points.position": "Platz {n}",
      "chart.points.leader": "{team} · Tabellenführer",
      "chart.points.leadClear": {
        one: "{team} führt nach Spieltag {matchday} mit {count} Punkt Vorsprung. Alle anderen Vereine in Grau.",
        other: "{team} führt nach Spieltag {matchday} mit {count} Punkten Vorsprung. Alle anderen Vereine in Grau.",
      },
      "chart.points.leadGd": "{team} führt nach Spieltag {matchday} dank der besseren Tordifferenz. Alle anderen Vereine in Grau.",
      "chart.points.behind": {
        one: "{team} liegt auf {position}, {count} Punkt hinter {leader} nach Spieltag {matchday}.",
        other: "{team} liegt auf {position}, {count} Punkte hinter {leader} nach Spieltag {matchday}.",
      },
      "chart.points.colClub": "Verein",
      "chart.points.colMatchday": "ST{matchday}",
      "chart.minutes.title": "Wann die Tore fallen",
      "chart.minutes.default": "Tore nach Spielminute.",
      "chart.minutes.empty": "Noch keine Tore erfasst.",
      "chart.minutes.aria": "Tore nach Spielminute",
      "chart.minutes.halfTime": "Halbzeit",
      "chart.minutes.range": "Minuten {label}",
      "chart.minutes.bar": { one: "Minuten {label}: {count} Tor, {share}", other: "Minuten {label}: {count} Tore, {share}" },
      "chart.minutes.tooltip": { one: "Tor · {share} aller Tore", other: "Tore · {share} aller Tore" },
      "chart.minutes.summary": "{goals} in {matches} ({avg} pro Spiel). Die torreichste Phase sind die Minuten {label}.",
      "chart.minutes.unknown": { one: " {count} Tor ohne erfasste Minute bleibt unberücksichtigt.", other: " {count} Tore ohne erfasste Minute bleiben unberücksichtigt." },
      "chart.minutes.colMinutes": "Minuten",
      "chart.minutes.colGoals": "Tore",
      "chart.minutes.colShare": "Anteil",

      /* Zählwörter innerhalb anderer Sätze */
      "count.matches": { one: "{count} Spiel", other: "{count} Spiele" },
      // after "in": 44 Spielen (dative plural)
      "count.matchesIn": { one: "{count} Spiel", other: "{count} Spielen" },
      "count.goals": { one: "{count} Tor", other: "{count} Tore" },

      /* Analysen */
      "analysis.eyebrow": "Ein Spiel, drei Modelle, jede Woche",
      "analysis.title": "Analysen",
      "analysis.pageTitleMd6": "Hamburg gegen Stuttgart: die Prognose — Jan’s Matchday",
      "analysis.metaMd6": "Prognose vor dem Spiel Hamburger SV gegen VfB Stuttgart, 6. Spieltag der Bundesliga 2026/27: drei Modelle gegen die Buchmacher, und wer recht hatte, wenn sie sich uneinig waren.",
      "analysis.pageTitleMd6Bl": "Bayern gegen Leipzig: die Prognose — Jan’s Matchday",
      "analysis.metaMd6Bl": "Prognose vor dem Spiel FC Bayern gegen RB Leipzig, 6. Spieltag der Bundesliga 2026/27: drei xG-Modelle gegen die Buchmacher bei einem klaren Favoriten und einer Torlinie von 4,5.",
      "analysis.pageTitleMd5": "Augsburg gegen Bayern: die Prognose — Jan’s Matchday",
      "analysis.metaMd5": "Prognose vor dem Spiel FC Augsburg gegen FC Bayern, 5. Spieltag der Bundesliga 2026/27: Dixon–Coles, ein bayesianisches Schüsse-zu-Toren-Modell und XGBoost im Backtest gegen die Buchmacher.",
      "analysis.back": "← Alle Analysen",
      "nav.skipPage": "Zum Inhalt springen",
      "learn.pageTitle": "So funktioniert’s: Wahrscheinlichkeiten, Quoten und Bewertung — Jan’s Matchday",
      "learn.meta": "So funktionieren die Prognosen auf Jan’s Matchday: was eine Wahrscheinlichkeit bedeutet, wie man Wettquoten in Chancen übersetzt, wie Prognosen bewertet werden, dazu ein Glossar.",
      "record.pageTitle": "Bilanz: Modelle gegen Buchmacher — Jan’s Matchday",
      "record.meta": "Die Bilanz von Jan’s Matchday: jede veröffentlichte Bundesliga-Prognose nach dem Abpfiff gegen die Buchmacher bewertet, dazu der Backtest und ein Wett-Kassenbuch auf dem Papier.",

      /* Neugestaltung: Navigation, Spieltag, Prognosen, Analysen, Bilanz */
      "nav.matchday": "Spieltag",
      "nav.dives": "Analysen",
      "nav.record": "Bilanz",
      "nav.learn": "Grundlagen",
      "nav.main": "Hauptmenü",
      "tab.matchday": "Spieltag",
      "tab.table": "Tabelle",
      "tab.dives": "Analysen",
      "tab.record": "Bilanz",
      "tab.learn": "Grundlagen",
      "hub.when.current": "Dieses Wochenende",
      "hub.when.past": "Ergebnisse",
      "hub.when.future": "Demnächst",
      "countdown.next": "Nächster Anstoß",
      "countdown.startsIn": "Anpfiff in",
      "countdown.hours": "Std.",
      "countdown.days": { one: "{count} Tag", other: "{count} Tagen" },
      "countdown.live": "Jetzt live",
      "countdown.liveCount": { one: "{count} Spiel läuft", other: "{count} Spiele laufen" },
      "countdown.refreshing": "Die Ergebnisse aktualisieren sich jede Minute",
      "countdown.status": "Status",
      "countdown.liveBadge": "Live",
      "countdown.complete": "Spieltag beendet",
      "countdown.completeGoals": "{goals} in {matches}",
      "countdown.nextMatchday": "Spieltag {matchday} beginnt {date}",
      "follow.button": "Klub folgen",
      "follow.change": "Du folgst {team}. Klub wechseln",
      "follow.title": "Einem Klub folgen",
      "follow.text": "Dein Klub wird in Spielplan, Tabelle und Grafiken hervorgehoben. Die Wahl bleibt auf diesem Gerät gespeichert.",
      "follow.clear": "Nicht mehr folgen",
      "dialog.close": "Schließen",
      "featured.label": "Neueste Analyse",
      "featured.tag": "Neueste Analyse",
      "featured.played": "Gespielt am {date}",
      "featured.locked": "Festgelegt am {date}",
      "featured.v": "–",
      "featured.teamMeta": "{position} · {points}",
      "featured.mostLikely": "Am wahrscheinlichsten {score} ({p} %)",
      "featured.over25": "Über 2,5 Tore {p}",
      "featured.btts": "Beide treffen {p}",
      "featured.read": "Zur Analyse",
      "count.points": { one: "{count} Punkt", other: "{count} Punkte" },
      "prob.models": "Meine Modelle",
      "prob.market": "Buchmacher",
      "prob.draw": "Remis",
      "prob.win": "Sieg {team}",
      "prob.marketShort": "Markt {value}",
      "prob.fairOdds": "faire Quote {value}",
      "prob.aria": "Sieg {home} {h}, Remis {d}, Sieg {away} {a}",
      "legend.home": "Heimsieg",
      "legend.draw": "Remis",
      "legend.away": "Auswärtssieg",
      "legend.explain": "So liest man einen Balken",
      "fixtures.oddsFoot": "Quoten: {sources}, ohne Marge",
      "odds.source": "{bookmaker}, {date}",
      "odds.sourceUnnamed": "Buchmacherquoten, {date}",
      "forecast.heading": "Die Prognose",
      "forecast.col.outcome": "Ausgang",
      "forecast.col.market": "Buchmacher",
      "forecast.col.fair": "Faire Quote",
      "forecast.col.odds": "Quote",
      "forecast.sourceLead": "Buchmacher: {source}, ohne die",
      "forecast.marginValue": "Buchmachermarge von {margin} %",
      "forecast.margin": "Buchmachermarge",
      "forecast.surprise": "Die Buchmacher gaben diesem Ergebnis {chance}, also etwa einmal in {count} Spielen.",
      "forecast.fullTime": "Endstand: {home} {score} {away}.",
      "forecast.gradeLead": "Bewertet mit dem",
      "forecast.rps": "Ranked Probability Score",
      "forecast.grade": "Modelle {models}, Markt {market}.",
      "forecast.modelsCloser": "Modelle näher dran",
      "forecast.marketCloser": "Buchmacher näher dran",
      "forecast.tie": "Gleichstand",
      "forecast.lessSure": "Meine Modelle trauen {team} weniger zu als die Buchmacher.",
      "forecast.moreSure": "Meine Modelle trauen {team} mehr zu als die Buchmacher.",
      "forecast.history": "In {count} früheren Spielen mit so großer Lücke gewann der Favorit in {actual} der Fälle. Die Buchmacher hatten {market} gesagt, meine Modelle {models}. Eher den Buchmachern folgen.",
      "forecast.historyShort": "Bei so großen Abweichungen lagen bisher meist die Buchmacher näher dran.",
      "glance.favourite": "Größter Favorit",
      "glance.closest": "Knappste Partie",
      "glance.vs": "gegen {team}",
      "glance.at": "bei {team}",
      "glance.upset": "Größte Überraschung",
      "glance.upsetSub": "Markt: {chance}, etwa einmal in {count} Spielen",
      "glance.seasonGoals": "Tore pro Spiel",
      "glance.seasonGoalsSub": { one: "diese Saison, aus {count} Spiel", other: "diese Saison, aus {count} Spielen" },
      "analysis.minutes": { one: "{count} Min. Lesezeit", other: "{count} Min. Lesezeit" },
      "analysis.thumbResult": "die Modelle gaben diesem Ergebnis {p}",
      "analysis.learnThumb": "So arbeiten die Modelle",
      "analysis.learnTag": "Grundlagen · hier anfangen",
      "analysis.learnTitle": "Wahrscheinlichkeiten, Quoten und warum die Buchmacher meist gewinnen",
      "analysis.learnDesc": "Die drei Modelle, wie eine Prognose bewertet wird, und ein Glossar für jede Zahl auf dieser Seite.",
      "teaser.eyebrow": "Die Bilanz",
      "teaser.title": "Taugen die Modelle etwas?",
      "teaser.text": "Jede Prognose wird nach dem Abpfiff bewertet: Wie weit lagen die Prozente von dem entfernt, was passiert ist? Je niedriger der Wert, desto besser.",
      "teaser.what": "So funktioniert die Wertung",
      "teaser.link": "Alle bewerteten Prognosen ansehen",
      "teaser.seasonModels": "Diese Saison, Modelle",
      "teaser.seasonMarket": "Diese Saison, Markt",
      "teaser.modelsAhead": "Modelle vorn, vorerst",
      "teaser.marketAhead": "Markt vorn",
      "teaser.longRun": "Seit 2019/20",
      "teaser.market": "Markt",
      "teaser.models": "Modelle",
      "teaser.longRunSub": "{market} zu {models} · {count} Spiele",
      "teaser.dives": "Bewertete Analysen",
      "teaser.divesSub": { one: "Modelle {count}-mal näher dran", other: "Modelle {count}-mal näher dran" },
      "explain.label": "Erklärung",
      "explain.close": "Erklärung schließen",
      "explain.howToRead": "So liest man das:",
      "explain.glossaryLink": "Alle Begriffe im Glossar",
      "depth.label": "Lesetiefe",
      "depth.quick": "Kurzfassung",
      "depth.full": "Ganze Analyse",
      "depth.nerd": "Für Nerds",
      "depth.minutes": { one: "{count} Min.", other: "{count} Min." },
      "toc.title": "Auf dieser Seite",
      "figure.enlarge": "Grafik vergrößern",
      "figure.close": "Grafik schließen",
      "figure.hint": "Seitwärts wischen, um die ganze Grafik zu sehen.",
      "footer.more": "Mehr",
      "footer.howItWorks": "So funktioniert’s",
      "footer.glossary": "Glossar",
      "footer.github": "Notebooks auf GitHub",

      /* Fußzeile */
      "footer.tagline": "Jans Platz. Bundesliga-Leidenschaft.",
      "footer.install": "Auf iPhone oder iPad: <strong>Teilen</strong> antippen, dann <strong>Zum Home-Bildschirm</strong> wählen, um Jan’s Matchday zu installieren.",
      "footer.photos": "Hintergrundfotos:",
      "footer.photoBall": "Fußball auf Rasen",
      "footer.by": "von",
      "footer.responsible": "Ab 18. Prognosen sind Analysen, keine Wettempfehlungen. Wenn Wetten keinen Spaß mehr macht: <a href=\"https://www.check-dein-spiel.de/\" target=\"_blank\" rel=\"noreferrer\">check-dein-spiel.de</a> (Deutschland) · <a href=\"https://www.sos-spielsucht.ch/\" target=\"_blank\" rel=\"noreferrer\">sos-spielsucht.ch</a> (Schweiz).",

      /* The weekend board */
      "strip.caption": "{played} von {total} Spieltagen gespielt",
      "board.title.both": { one: "{count} Spiel, zwei Meinungen", other: "{count} Spiele, zwei Meinungen" },
      "board.title.done": "So lagen die Prognosen",
      "board.intro.both": "Jeder Balken ist die Prognose meiner Modelle. Die beiden weißen Nadeln zeigen, wo die Buchmacher denselben Balken teilen würden. Sitzen sie neben den Nahtstellen, sind wir uns uneinig.",
      "board.intro.models": "Jeder Balken ist die Prognose meiner Modelle für das Spiel.",
      "board.intro.market": "Meine Prognose für diesen Spieltag steht noch aus. Bis dahin zeigen die umrandeten Balken die Quoten der Buchmacher, umgerechnet in Wahrscheinlichkeiten.",
      "board.intro.marketPast": "Für diesen Spieltag gab es keine Modellprognose. Die umrandeten Balken zeigen, was die Buchmacher vor dem Anpfiff erwarteten.",
      "board.intro.mixed": "Ein umrandeter Balken heißt: nur Buchmacher, keine Modellprognose für dieses Spiel.",
      "legend.pin": "Aufteilung der Buchmacher",
      "lead.argument.label": "Größter Streitfall des Spieltags",
      "lead.argument.team": "Meine Modelle geben {team} {models}, die Buchmacher {market}.",
      "lead.argument.draw": "Meine Modelle sehen ein Remis bei {models}, die Buchmacher bei {market}.",
      "lead.agree.label": "Kein großer Streitfall",
      "lead.agree.text": { one: "Meine Modelle und die Buchmacher liegen bei jedem Spiel höchstens {count} Punkt auseinander.", other: "Meine Modelle und die Buchmacher liegen bei jedem Spiel höchstens {count} Punkte auseinander." },
      "lead.market.label": "Was die Buchmacher erwarten",
      "lead.market.closest": "Engstes Spiel:",
      "lead.market.favourite": "Klarster Favorit:",
      "lead.market.at": "mit {chance}.",
      "lead.upset.label": "Größte Überraschung",
      "lead.upset.models": "Meine Modelle gaben diesem Ergebnis {chance}, also etwa einmal in {count} Spielen.",
      "lead.upset.market": "Die Buchmacher gaben diesem Ergebnis {chance}, also etwa einmal in {count} Spielen.",
      "lead.results.label": "Der Spieltag in Zahlen",
      "lead.results.split": "Heimsiege {h}, Remis {d}, Auswärtssiege {a}.",
      "row.bookmakers": "Buchmacher {h} / {d} / {a}",
      "row.gap": { one: "{count} Punkt Abstand bei {team}", other: "{count} Punkte Abstand bei {team}" },
      "row.theDraw": "Remis",
      "row.locked": "Prognose seit Anpfiff eingefroren",
      "row.modelsOnly": "Keine Buchmacherquoten für dieses Spiel",
      "row.marketOnly": "Nur Buchmacher",
      "row.marketResult": "Die Buchmacher gaben diesem Ergebnis {chance}",
      "row.fullTime": "Ende",
      "forecast.headingPast": "Die Prognose vor dem Anpfiff",
      "hundred.models": "Spielt man dieses Spiel 100-mal, gewinnt nach meinen Modellen {home} etwa {h}-mal, {d}-mal endet es remis und {a}-mal gewinnt {away}.",
      "hundred.market": "Spielt man dieses Spiel 100-mal, gewinnt nach den Quoten der Buchmacher {home} etwa {h}-mal, {d}-mal endet es remis und {a}-mal gewinnt {away}.",
      "split.heading": "Drei Modelle, ein Mittelwert",
      "split.note": "Heimsieg / Remis / Auswärtssieg. Meine Prognose ist der einfache Mittelwert der drei.",
      "facts.heading": "Tore",
      "facts.xg": "Erwartete Tore",
      "facts.likely": "Wahrscheinlichstes Ergebnis",
      "facts.over25": "Über 2,5 Tore",
      "facts.btts": "Beide treffen",
      "grid.caption": "Wahrscheinlichkeit jedes Ergebnisses in Prozent. Tore {home} links, Tore {away} oben. Das umrandete Feld ist das wahrscheinlichste.",
      "grid.captionFinal": "Wahrscheinlichkeit jedes Ergebnisses in Prozent, vor dem Anpfiff. Tore {home} links, Tore {away} oben. Das gestrichelte Feld ist der Endstand.",
      "grid.aria": "Ergebnisraster {home} gegen {away}. Am wahrscheinlichsten: {score} mit {p}.",
      "grade.heading": "So lag die Prognose",
      "grade.surpriseModels": "Meine Modelle gaben diesem Ergebnis {chance}, also etwa einmal in {count} Spielen.",
      "grade.term": "Ranked Probability Score:",
      "grade.note": "0 ist perfekt, der kürzere Balken lag also näher dran.",
      "gauge.guess": "Reines Raten",
      "gauge.better": "Näher am Geschehen",
      "gauge.worse": "Weiter daneben",
      "gauge.longMarket": "Auf lange Sicht: {count} Spiele seit 2019/20, jede Prognose nur mit dem Wissen vor dem Anpfiff. Die Buchmacher liegen vorn.",
      "gauge.longModels": "Auf lange Sicht: {count} Spiele seit 2019/20, jede Prognose nur mit dem Wissen vor dem Anpfiff. Meine Modelle liegen vorn.",
      "gauge.seasonAhead": { one: "In dieser Saison liegen meine Modelle nach {count} Spiel vorn: {models} gegen {market} bei den Buchmachern. Schön, beweist aber noch fast nichts.", other: "In dieser Saison liegen meine Modelle nach {count} Spielen vorn: {models} gegen {market} bei den Buchmachern. Schön, beweist aber noch fast nichts." },
      "gauge.seasonBehind": { one: "In dieser Saison liegen die Buchmacher nach {count} Spiel vorn: {market} gegen {models} bei meinen Modellen.", other: "In dieser Saison liegen die Buchmacher nach {count} Spielen vorn: {market} gegen {models} bei meinen Modellen." },
      "gauge.aria": "Ranked Probability Score über {count} Spiele, niedriger ist besser: Buchmacher {market}, meine Modelle {models}, reines Raten {guess}.",
      "dive.latest": "Neueste",
      "analysis.intro": "Ein Spiel wird vor dem Anpfiff zerlegt und nach dem Abpfiff benotet.",
      "analysis.learnLink": "Neu hier? So arbeiten die Modelle",
      "table.zone.mid": "Mittelfeld",
    },
  };

  const listeners = [];
  let lang = FALLBACK;
  let locale = LOCALES[FALLBACK];
  let pluralRules = new Intl.PluralRules(locale);
  let numberFormats = new Map();

  /* ---------- Reading and saving the choice ---------- */

  function isSupported(value) {
    return SUPPORTED.includes(value);
  }

  function readStored() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return isSupported(value) ? value : null;
    } catch {
      return null;
    }
  }

  function store(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // Storage can be unavailable (private mode); the choice then lasts for this visit only.
    }
  }

  function detect() {
    const preferred = navigator.languages?.length ? navigator.languages : [navigator.language];
    for (const tag of preferred) {
      const base = String(tag ?? "").slice(0, 2).toLowerCase();
      if (isSupported(base)) return base;
    }
    return FALLBACK;
  }

  /* ---------- Translating ---------- */

  function t(key, params = {}) {
    let entry = messages[lang][key] ?? messages[FALLBACK][key];
    if (entry === undefined) {
      console.warn(`Missing translation: ${key}`);
      return key;
    }
    if (typeof entry === "object") entry = entry[pluralRules.select(Number(params.count))] ?? entry.other;
    return entry.replace(/\{(\w+)\}/g, (placeholder, name) => (
      params[name] === undefined ? placeholder : String(params[name])
    ));
  }

  function numberFormat(options) {
    const id = JSON.stringify(options);
    if (!numberFormats.has(id)) numberFormats.set(id, new Intl.NumberFormat(locale, options));
    return numberFormats.get(id);
  }

  // 1,234 in English, 1.234 in German; `digits` fixes the decimals (2.8 or 2,8).
  function number(value, digits = 0) {
    return numberFormat({ minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
  }

  // 12% in English, 12 % in German.
  function percent(fraction) {
    return numberFormat({ style: "percent", maximumFractionDigits: 0 }).format(fraction);
  }

  // 3rd in English, 3. in German.
  function ordinal(value) {
    if (lang === "de") return `${value}.`;
    const suffix = value % 100 >= 11 && value % 100 <= 13
      ? "th"
      : ({ 1: "st", 2: "nd", 3: "rd" })[value % 10] ?? "th";
    return `${value}${suffix}`;
  }

  // Scores read 2–1 in English and 2:1 in German.
  function scoreSeparator() {
    return lang === "de" ? ":" : "–";
  }

  function score(home, away) {
    return `${home}${scoreSeparator()}${away}`;
  }

  function dateFormat(value, options) {
    return new Intl.DateTimeFormat(locale, options).format(new Date(value));
  }

  // Fills in everything marked up in the HTML:
  //   data-i18n="key"                   replaces the element's text
  //   data-i18n-html="key"              the same, for text with <strong> (our own strings only)
  //   data-i18n-attrs="attr:key;attr2:key2"   sets attributes such as aria-label or title
  //   data-lang-only="de"               shown only while that language is active
  function apply(root = document) {
    for (const element of root.querySelectorAll("[data-i18n]")) {
      element.textContent = t(element.dataset.i18n);
    }
    for (const element of root.querySelectorAll("[data-i18n-html]")) {
      element.innerHTML = t(element.dataset.i18nHtml);
    }
    for (const element of root.querySelectorAll("[data-i18n-attrs]")) {
      for (const pair of element.dataset.i18nAttrs.split(";")) {
        const [attribute, key] = pair.split(":").map((part) => part.trim());
        if (attribute && key) element.setAttribute(attribute, t(key));
      }
    }
    for (const element of root.querySelectorAll("[data-lang-only]")) {
      element.hidden = element.dataset.langOnly !== lang;
    }
  }

  function updateSwitch() {
    for (const button of document.querySelectorAll(".lang-switch [data-lang]")) {
      button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
    }
  }

  // Keeps a shared ?lang= link in step with the switch so a reload does not undo the choice.
  function syncUrl() {
    const url = new URL(location.href);
    if (!url.searchParams.has("lang")) return;
    url.searchParams.set("lang", lang);
    history.replaceState(null, "", url);
  }

  function setLang(next, { persist = true } = {}) {
    if (!isSupported(next)) return;
    const changed = next !== lang;
    lang = next;
    locale = LOCALES[lang];
    pluralRules = new Intl.PluralRules(locale);
    numberFormats = new Map();
    document.documentElement.lang = lang;
    if (persist) store(lang);
    syncUrl();
    apply();
    updateSwitch();
    if (changed) listeners.forEach((listener) => listener(lang));
  }

  function onChange(listener) {
    listeners.push(listener);
  }

  /* ---------- Start-up ---------- */

  const requested = new URLSearchParams(location.search).get("lang");
  const initial = isSupported(requested) ? requested : readStored() ?? detect();
  // A ?lang= link is an explicit choice, so it becomes the saved one too.
  setLang(initial, { persist: isSupported(requested) });

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".lang-switch [data-lang]");
    if (button) setLang(button.dataset.lang);
  });

  window.I18N = {
    messages,
    get lang() { return lang; },
    get locale() { return locale; },
    get scoreSeparator() { return scoreSeparator(); },
    t,
    number,
    percent,
    ordinal,
    score,
    dateFormat,
    apply,
    setLang,
    onChange,
  };
})();
