/*
 * The glossary: one entry per term, in English and German.
 * Used by the explainers in the deep dives (explain.js) and by the Learn page.
 * Each entry: term (the name), short (what it is, one or two sentences), read (how to read it).
 * To link a word in an article to an entry: <button type="button" class="term" data-term="rps">…</button>
 */
window.GLOSSARY = {
  order: [
    "market-probability", "margin", "fair-odds", "edge", "rps", "log-loss", "calibration", "backtest",
    "expected-goals", "xg", "expected-points", "dixon-coles", "bayesian-model", "xgboost", "ensemble", "elo",
    "shap", "credible-interval", "over-25", "btts", "clv",
  ],
  en: {
    "market-probability": {
      term: "Market probability",
      short: "The bookmakers’ view of a match, turned into chances that add up to 100%. Take 1 ÷ odds for each outcome, then scale the three numbers down until they sum to 100%.",
      read: "It is the benchmark to beat. Bookmakers see team news and heavy betting, so their prices are hard to improve on.",
    },
    margin: {
      term: "Bookmaker margin",
      short: "Turn a bookmaker’s three odds into chances and they add up to more than 100%. The extra is the bookmaker’s cut, also called the overround.",
      read: "Odds of 3.80, 4.20 and 1.80 imply 26% + 24% + 56% = 106%, a margin of about 6%. The lower the margin, the better the prices for bettors.",
    },
    "fair-odds": {
      term: "Fair odds",
      short: "The odds that would be fair if a probability were exactly right: 1 ÷ probability. A 32% chance has fair odds of 3.12.",
      read: "Odds on offer above the fair odds look like value, but only if the probability is right. That is a big if.",
    },
    edge: {
      term: "Edge",
      short: "The gap between a model’s probability and the market’s. A model at 32% against a market at 25% has a 7-point edge on that outcome.",
      read: "An edge is a claim, not a profit. On this site, big edges against the market have so far pointed the wrong way more often than not.",
    },
    rps: {
      term: "Ranked probability score (RPS)",
      short: "Grades a whole home/draw/away forecast, not just the pick. It gives some credit for being close: a draw is nearer a home win than an away win is.",
      read: "0 is perfect and lower is better. A shrug of one-third for everything scores 0.238; good Bundesliga forecasts land around 0.19 to 0.20.",
    },
    "log-loss": {
      term: "Log loss",
      short: "Another score for probability forecasts: the negative logarithm of the probability given to what actually happened, averaged over matches.",
      read: "Lower is better. It punishes confident misses hard: calling something 2% that then happens costs far more than calling it 20%.",
    },
    calibration: {
      term: "Calibration",
      short: "Whether forecasts mean what they say. Of all the times a model says 60%, the outcome should happen about 60% of the time.",
      read: "On a calibration chart, dots on the diagonal are well calibrated. Dots above it mean the model was too timid; below it, too bold.",
    },
    backtest: {
      term: "Backtest (out of sample)",
      short: "Replaying past matches as if they were next weekend’s: each model is refitted using only what it could have known before kick-off, then graded.",
      read: "It is the honest way to test a model. Grading a model on matches it was fitted to flatters it.",
    },
    "expected-goals": {
      term: "Expected goals",
      short: "In these forecasts, the average number of goals a model expects each side to score, for example 1.47 for Hamburg and 1.77 for Stuttgart.",
      read: "It is an average over many imagined replays, so 1.47 means one goal most often and two goals quite often. Not to be confused with shot-based xG from tracking data.",
    },
    xg: {
      term: "xG (shot-based expected goals)",
      short: "How many goals a team’s chances were worth, judged shot by shot from where and how each was taken. The numbers here come from Understat.",
      read: "It measures the quality of chances rather than luck in front of goal, so over a few weeks it says more about a team than goals do. Since October 2026 the models learn from it, after a pre-registered test showed it helps.",
    },
    "expected-points": {
      term: "Expected points",
      short: "The points a team would collect on average if its shots on target went in at the league rate, about one in three.",
      read: "It strips out luck in finishing and goalkeeping. Six points from shots worth 4.8 suggests a team has been lucky.",
    },
    "dixon-coles": {
      term: "Dixon–Coles",
      short: "A classic football model from 1997. Every club gets an attack and a defence rating, goals follow a Poisson distribution, and a small correction fixes low scores.",
      read: "It only looks at goals, so it reacts to results rather than to how chances were created. Recent matches count more than old ones.",
    },
    "bayesian-model": {
      term: "Bayesian shots-to-goals model",
      short: "A model in two steps: how many shots on target each side creates, then how many of those go in. Fitted by sampling, so every number comes with its uncertainty.",
      read: "Shots on target are less noisy than goals, so it spots teams whose results run ahead of or behind their chances.",
    },
    xgboost: {
      term: "XGBoost",
      short: "A machine-learning method that builds many small decision trees. Here it predicts each side’s goals from 30 pre-match features such as Elo, form and rest days.",
      read: "It finds patterns the other two models are not built to see, but it needs a lot of data and can chase noise.",
    },
    ensemble: {
      term: "Ensemble",
      short: "The plain average of the three models’ score grids, with equal weights fixed before any results were seen.",
      read: "Averaging rarely beats the best single model by much, but it protects against any one model having a bad week.",
    },
    elo: {
      term: "Elo rating",
      short: "A strength rating that goes up after a win and down after a defeat, by more when the result is a surprise.",
      read: "The gap between two clubs’ Elo ratings is a quick guide to who is favourite. It is the most important feature in the XGBoost model.",
    },
    shap: {
      term: "SHAP values",
      short: "A way to show how much each input pushed a machine-learning forecast up or down for one particular match.",
      read: "Bars to the right raised the expected goals, bars to the left lowered them. The longest bars matter most.",
    },
    "credible-interval": {
      term: "Credible interval",
      short: "The range a Bayesian model thinks a value lies in, with a stated probability. An 80% credible interval contains the true value with 80% probability, given the model.",
      read: "Wide bands mean little evidence, for example after only five matches. Narrow bands mean the model is fairly sure.",
    },
    "over-25": {
      term: "Over 2.5 goals",
      short: "The chance that a match has three or more goals in total. A common betting market.",
      read: "The Bundesliga averages about three goals a game, so 55% to 65% is ordinary for this market.",
    },
    btts: {
      term: "Both teams to score",
      short: "The chance that each side scores at least once.",
      read: "It depends mostly on the weaker attack: one side likely to draw a blank pulls it down.",
    },
    clv: {
      term: "Closing-line value",
      short: "Whether a bet got better odds than the final price just before kick-off.",
      read: "Closing odds carry all the late news, so beating them over many bets is the best single sign of real skill. Winning money without beating them is usually luck. Here it is the odds taken times the closing probability (margin removed), minus one: +5% means the bet was worth 5% more than its stake at kick-off.",
    },
  },
  de: {
    "market-probability": {
      term: "Marktwahrscheinlichkeit",
      short: "Die Sicht der Buchmacher auf ein Spiel, umgerechnet in Chancen, die zusammen 100 % ergeben: für jeden Ausgang 1 ÷ Quote, dann die drei Werte auf 100 % herunterskalieren.",
      read: "Das ist die Messlatte. Buchmacher kennen Personalnachrichten und sehen große Einsätze, ihre Preise sind schwer zu schlagen.",
    },
    margin: {
      term: "Buchmachermarge",
      short: "Rechnet man die drei Quoten eines Buchmachers in Chancen um, ergeben sie mehr als 100 %. Der Überschuss ist der Anteil des Buchmachers.",
      read: "Quoten von 3,80, 4,20 und 1,80 entsprechen 26 % + 24 % + 56 % = 106 %, also rund 6 % Marge. Je kleiner die Marge, desto besser die Quoten für Wettende.",
    },
    "fair-odds": {
      term: "Faire Quote",
      short: "Die Quote, die fair wäre, wenn eine Wahrscheinlichkeit genau stimmt: 1 ÷ Wahrscheinlichkeit. Eine Chance von 32 % entspricht einer fairen Quote von 3,12.",
      read: "Liegt die angebotene Quote darüber, sieht das nach Value aus, aber nur, wenn die Wahrscheinlichkeit stimmt. Das ist ein großes Wenn.",
    },
    edge: {
      term: "Vorteil (Edge)",
      short: "Der Abstand zwischen der Wahrscheinlichkeit eines Modells und der des Marktes. Modell 32 %, Markt 25 %: 7 Prozentpunkte Vorteil auf diesen Ausgang.",
      read: "Ein Vorteil ist eine Behauptung, kein Gewinn. Große Abweichungen vom Markt lagen auf dieser Seite bisher öfter falsch als richtig.",
    },
    rps: {
      term: "Ranked Probability Score (RPS)",
      short: "Bewertet die ganze Prognose für Heimsieg, Remis und Auswärtssieg, nicht nur den Tipp, und gibt Teilpunkte für knapp daneben: Ein Remis liegt näher an einem Heimsieg als ein Auswärtssieg.",
      read: "0 ist perfekt, niedriger ist besser. Ein Drittel für alles ergibt 0,238; gute Bundesliga-Prognosen liegen bei etwa 0,19 bis 0,20.",
    },
    "log-loss": {
      term: "Log-Loss",
      short: "Eine weitere Bewertung für Wahrscheinlichkeitsprognosen: der negative Logarithmus der Wahrscheinlichkeit, die dem tatsächlichen Ausgang gegeben wurde, gemittelt über alle Spiele.",
      read: "Niedriger ist besser. Selbstsichere Fehler werden hart bestraft: Was mit 2 % angesetzt war und dann eintritt, kostet viel mehr als bei 20 %.",
    },
    calibration: {
      term: "Kalibrierung",
      short: "Ob Prognosen halten, was sie sagen. Von allen Fällen, in denen ein Modell 60 % sagt, sollte der Ausgang in etwa 60 % eintreten.",
      read: "Im Kalibrierungsdiagramm liegen gut kalibrierte Punkte auf der Diagonale. Darüber war das Modell zu zaghaft, darunter zu forsch.",
    },
    backtest: {
      term: "Backtest (Out-of-Sample)",
      short: "Vergangene Spiele werden nachgespielt, als wären sie die Partien am kommenden Wochenende: Jedes Modell kennt nur, was vor dem Anpfiff bekannt war, und wird dann bewertet.",
      read: "So testet man ehrlich. Ein Modell an Spielen zu messen, mit denen es angepasst wurde, schönt das Ergebnis.",
    },
    "expected-goals": {
      term: "Erwartete Tore",
      short: "In diesen Prognosen die durchschnittliche Zahl an Toren, die ein Modell jeder Mannschaft zutraut, zum Beispiel 1,47 für Hamburg und 1,77 für Stuttgart.",
      read: "Ein Mittelwert über viele gedachte Wiederholungen: 1,47 heißt meist ein Tor, recht oft zwei. Nicht zu verwechseln mit schussbasiertem xG aus Trackingdaten.",
    },
    xg: {
      term: "xG (Expected Goals aus Schüssen)",
      short: "Wie viele Tore die Chancen einer Mannschaft wert waren, Schuss für Schuss nach Ort und Art bewertet. Die Zahlen hier stammen von Understat.",
      read: "Es misst die Qualität der Chancen statt des Glücks vor dem Tor und sagt deshalb über wenige Wochen mehr über eine Mannschaft als die Tore. Seit Oktober 2026 lernen die Modelle daraus, nachdem ein vorab festgelegter Test gezeigt hat, dass es hilft.",
    },
    "expected-points": {
      term: "Erwartete Punkte",
      short: "Die Punkte, die eine Mannschaft im Schnitt hätte, wenn ihre Schüsse aufs Tor so oft treffen würden wie im Ligaschnitt, etwa jeder dritte.",
      read: "Das rechnet Glück beim Abschluss und im Tor heraus. Sechs Punkte aus Schüssen im Wert von 4,8 deuten auf Glück hin.",
    },
    "dixon-coles": {
      term: "Dixon–Coles",
      short: "Ein klassisches Fußballmodell von 1997. Jeder Klub bekommt eine Angriffs- und eine Abwehrstärke, Tore folgen einer Poisson-Verteilung, eine kleine Korrektur behandelt torarme Ergebnisse.",
      read: "Es schaut nur auf Tore und reagiert damit auf Ergebnisse, nicht darauf, wie Chancen entstehen. Neuere Spiele zählen mehr als alte.",
    },
    "bayesian-model": {
      term: "Bayesianisches Schüsse-zu-Toren-Modell",
      short: "Ein Modell in zwei Schritten: Wie viele Schüsse aufs Tor gibt jede Seite ab, und wie viele davon gehen rein? Angepasst per Stichprobenverfahren, daher kommt jede Zahl mit ihrer Unsicherheit.",
      read: "Schüsse aufs Tor schwanken weniger als Tore, daher erkennt es Teams, deren Ergebnisse besser oder schlechter sind als ihre Chancen.",
    },
    xgboost: {
      term: "XGBoost",
      short: "Ein Verfahren des maschinellen Lernens aus vielen kleinen Entscheidungsbäumen. Hier sagt es die Tore jeder Seite aus 30 Merkmalen vor dem Spiel voraus, etwa Elo, Form und Ruhetage.",
      read: "Es findet Muster, für die die anderen beiden Modelle nicht gebaut sind, braucht aber viele Daten und kann Zufall hinterherlaufen.",
    },
    ensemble: {
      term: "Ensemble",
      short: "Der einfache Mittelwert der Ergebnis-Wahrscheinlichkeiten der drei Modelle, mit gleichen Gewichten, die vor jedem Ergebnis festgelegt wurden.",
      read: "Mitteln schlägt das beste Einzelmodell selten deutlich, schützt aber davor, dass ein Modell eine schlechte Woche hat.",
    },
    elo: {
      term: "Elo-Zahl",
      short: "Eine Stärkezahl, die nach einem Sieg steigt und nach einer Niederlage sinkt, und zwar umso mehr, je überraschender das Ergebnis war.",
      read: "Der Elo-Abstand zweier Klubs zeigt schnell, wer Favorit ist. Er ist das wichtigste Merkmal im XGBoost-Modell.",
    },
    shap: {
      term: "SHAP-Werte",
      short: "Zeigen, wie stark jedes Merkmal eine Prognose des maschinellen Lernens für ein bestimmtes Spiel nach oben oder unten geschoben hat.",
      read: "Balken nach rechts erhöhen die erwarteten Tore, Balken nach links senken sie. Die längsten Balken zählen am meisten.",
    },
    "credible-interval": {
      term: "Kredibilitätsintervall",
      short: "Der Bereich, in dem ein bayesianisches Modell einen Wert vermutet, mit einer angegebenen Wahrscheinlichkeit. Ein 80-%-Intervall enthält den wahren Wert laut Modell mit 80 % Wahrscheinlichkeit.",
      read: "Breite Bänder bedeuten wenig Daten, etwa nach nur fünf Spielen. Schmale Bänder bedeuten, dass das Modell recht sicher ist.",
    },
    "over-25": {
      term: "Über 2,5 Tore",
      short: "Die Chance, dass in einem Spiel insgesamt drei oder mehr Tore fallen. Ein verbreiteter Wettmarkt.",
      read: "In der Bundesliga fallen im Schnitt etwa drei Tore pro Spiel, 55 % bis 65 % sind für diesen Markt normal.",
    },
    btts: {
      term: "Beide Teams treffen",
      short: "Die Chance, dass jede Mannschaft mindestens ein Tor schießt.",
      read: "Sie hängt vor allem am schwächeren Angriff: Ist eine Seite wahrscheinlich torlos, sinkt der Wert.",
    },
    clv: {
      term: "Closing Line Value",
      short: "Ob eine Wette eine bessere Quote bekommen hat als den letzten Preis kurz vor dem Anpfiff.",
      read: "Die Schlussquote enthält alle späten Nachrichten. Sie über viele Wetten zu schlagen, ist das beste einzelne Zeichen für echtes Können. Wer gewinnt, ohne sie zu schlagen, hatte meist Glück. Hier: die genommene Quote mal die Schlusswahrscheinlichkeit (ohne Marge), minus eins. +5 % heißt, die Wette war zum Anpfiff 5 % mehr wert als ihr Einsatz.",
    },
  },
};
