/*
 * The Learn page's playthings (loaded after learn.js):
 *
 *   - Replay machine     one forecast played once or a hundred times
 *   - Goal machine       two expected-goals sliders, a Poisson score grid and the forecast it gives
 *   - Shot map           tap a pitch to shoot; a toy xG model (distance and angle) prices each shot
 *   - Three models       this matchday's forecasts, model by model, from data/forecasts.json
 *   - The long run       bettors at odds of 1.90, to show what the margin and luck do over time
 *   - Guess the forecast this matchday's fixtures as a game
 *   - Quick checks       one question per drill; what is done is remembered on this device
 *
 * The prose is in the HTML (one copy per language); the words these widgets need live here.
 * Nothing is sent anywhere: the only thing stored is which drills are done (localStorage).
 */
(() => {
  "use strict";

  const I18N = window.I18N;
  const { element, triSlider } = window.LEARN;
  const STORE_KEY = "jans-matchday:learn";
  const GUESS_KEY = "jans-matchday:guesses";
  const HERE = new URL(".", document.currentScript.src);
  const API = "https://api.openligadb.de";
  // Part one (learn/) has the first seven, part two (learn/part-two/) the other four.
  const DRILLS = ["probabilities", "goals", "xg", "models", "odds", "grading", "market", "luck", "elo", "calibration", "staking"];
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)");

  const WORDS = {
    en: {
      home: "Home win",
      draw: "Draw",
      away: "Away win",
      teamWin: "{team} win",
      // Replay machine
      replayTitle: "Replay machine",
      replaySource: "{match}, {date} · my forecast",
      playOnce: "Play once",
      play100: "Play 100 times",
      clear: "Clear",
      forecastIn100: "forecast: {n} in 100",
      replayNone: "Nothing played yet. Every press plays the match once, with my forecast as the dice.",
      replayOne: "Replay 1: {result}. One match proves nothing, which is the point.",
      replaySome: "Replay {n}: {result}.",
      replayFull: "100 replays: {h} – {d} – {a}. The forecast said {fh} – {fd} – {fa}. Press again: the forecast stays put, the count doesn’t.",
      replayReveal: "What actually happened?",
      replayRevealText: "Hamburg won 1–0. One blue dot. The forecast was no more wrong than a weather report that says 30% rain on a day it rains.",
      // Goal machine
      goalTitle: "Goal machine",
      goalSource: "Any match you like",
      goalPick: "Or load a match from matchday {md}",
      goalPickNone: "Your own numbers",
      xgHome: "Home side: goals on average",
      xgAway: "Away side: goals on average",
      xgTeam: "{team}: goals on average",
      likeliest: "Likeliest score",
      over25: "Over 2.5 goals",
      btts: "Both teams score",
      gridCaption: "Chance of each score in percent. Home goals down the side, away goals along the top. The outlined cell is the likeliest.",
      gridAria: "Score grid. Most likely: {score} at {p}.",
      goalFine: "Plain Poisson: each side’s goals are worked out separately. Dixon–Coles adds a small correction for low scores, which this toy leaves out.",
      // Shot map
      shotTitle: "Shot map",
      shotSource: "Tap the pitch to shoot",
      shotAria: "The attacking end of a pitch seen from above, goal at the top. {count} shots taken.",
      shotNone: "No shots yet. Tap anywhere in front of goal, or use the buttons.",
      shotLast: "xG {xg}: {odds} {outcome}",
      oneIn: "A shot from here goes in about 1 time in {n}.",
      mostly: "A shot from here goes in more often than not.",
      goal: "Goal!",
      noGoal: "No goal.",
      shots: "Shots",
      xg: "xG",
      goals: "Goals",
      presets: "Shoot from",
      presetSix: "Six-yard box",
      presetSpot: "Penalty spot",
      presetEdge: "Edge of the box",
      presetAngle: "Tight angle",
      presetFar: "25 metres out",
      again: "Same shots again",
      shotPar: "Goals and xG agree, near enough.",
      shotHot: "Running hot: {diff} more goals than the chances were worth. Enjoy it while it lasts.",
      shotCold: "Running cold: {diff} fewer goals than the chances were worth. The xG says keep shooting.",
      shotFull: "The pitch is full. Clear it to keep shooting.",
      shotLegend: "Filled: goal. Outline: no goal. Bigger: better chance.",
      shotFine: "A toy model: distance and angle only. Real xG models, such as the Understat one my models learn from, also know whether it was a header, how the ball arrived and where the defenders stood.",
      // Three models
      modelsTitle: "Three models, one average",
      modelsSource: "Matchday {md}, as published",
      modelsExample: "Example: matchday 10",
      match: "Match",
      dixonColes: "Dixon–Coles",
      bayesian: "Shots to goals",
      xgboost: "XGBoost",
      ensemble: "Ensemble",
      bookmakers: "Bookmakers",
      spread: "On a {team} win the three models sit between {low} and {high}: {gap} apart.",
      spreadTight: "On a {team} win the three models agree to within a point.",
      barAria: "{name}: {home} {h}, draw {d}, {away} {a}",
      point: { one: "{count} point", other: "{count} points" },
      // The long run
      longTitle: "The long run",
      longSource: "€1 bets at odds of 1.90",
      skill: "The bettor is right",
      skillFlip: "a coin flip",
      skillEven: "about break-even",
      bets: "Number of bets",
      rerun: "Run again",
      perBet: "Expected per €1 bet",
      inProfit: "In profit after {n} bets",
      average: "Average result",
      longAria: "{paths} simulated bettors over {n} bets. {share} of bettors like these end in profit; the average result is {avg}.",
      longLose: "No edge here, so the margin wins in the end. The lucky ones just take longer to find out.",
      longEven: "Right at break-even: about half end up ahead, half behind, and the bookmaker still gets paid on time.",
      longWin: "A real edge, and still {behind} of these bettors are behind after {n} bets. Skill takes a long time to show; luck shows up at once.",
      longLegend: "Each line is one bettor. Bright lines finish in profit, dim lines don’t. Dashed: the average.",
      axisBets: "bets",
      // Guess the forecast
      gameTitle: "Guess the forecast",
      gameSource: "Matchday {md}",
      gameCount: "Match {n} of {total}",
      gameAsk: "What are the chances? Set the sliders, then lock it in.",
      lock: "Lock it in",
      next: "Next match",
      finish: "See how you did",
      you: "You",
      models: "My models",
      gameOff: "{gap} away from my models.",
      gameOffBooks: "The bookmakers are {gap} away from them.",
      gameBooksAgree: "The bookmakers and my models all but agree on this one.",
      gameSpot: "Spot on.",
      gameDone: "Full time",
      gameAvg: "On average you were {gap} away from my models. The bookmakers were {books} away.",
      gameDraw: "You gave the draw {you} on average; my models gave it {models}.",
      gameSharp: "Sharp. You and the models would get along.",
      gameDecent: "A decent eye. The models would let you sit in on the meeting.",
      gameFar: "The models politely disagree. So did the bookmakers.",
      gameAgain: "Play again",
      gameBoard: "See the matchday board",
      gameFine: "The game compares you with the forecast; the scorecard grades you against the result after full time. Guesses close at kick-off and stay on this device.",
      gameClosed: "Matchday {md} has kicked off, so guesses are closed. The next matchday opens when its forecasts are published, usually on Thursday.",
      gameSaved: "Your guesses are saved on this device. Come back after the final whistle: the scorecard grades you against the results.",
      cardTitle: "Your scorecard",
      cardYours: "You: {h} · {d} · {a}",
      cardKickoff: "kick-off {when}",
      cardWaiting: "waiting for the result",
      cardTotal: "After {n} graded: you {you}, my models {models}{books}.",
      cardBooks: ", the bookmakers {books}",
      cardWin: "You’re ahead. Enjoy it; it is a small sample.",
      cardLose: "Not ahead yet. Small samples are cruel in both directions.",
      cardFine: "Ranked probability score per match, lower is better. The lowest in each row is in bold. Bookmakers: their average price when the forecast was published.",
      // Quick checks and progress
      check: "Quick check",
      checkDone: "Quick check · done",
      right: "Right.",
      wrong: "Not quite. Have another go.",
      progress: "{done} of {total} drills done",
      rankLabel: "Your league:",
      ranks: ["Kreisliga", "Regionalliga", "2. Bundesliga", "Bundesliga", "Champions"],
      rankLines: [
        "Sunday league. Everybody starts here.",
        "Semi-pro. You know a margin when you see one.",
        "Second tier. Part two is where promotion is won.",
        "Top flight. You can read every number on this site, and argue with it.",
        "Champions. You know what a table, a rating and a stake are really telling you, which puts you ahead of most of the people betting this weekend.",
      ],
      fullTime: "Full time",
      halfTime: "Half time",
      toPartTwo: "On to part two",
      toPartOne: "Back to part one",
      reset: "Start again",
      toBoard: "To this week’s forecasts",
      q: {
        probabilities: {
          q: "In October my models gave Hamburg a 32% chance against Stuttgart. Hamburg won 1–0. Was the forecast wrong?",
          options: ["Yes: 32% is less than half", "One match can’t tell you", "No: they won, so it was right"],
          answer: 1,
          why: "Things forecast at 32% should happen about one time in three. Whether they do only shows over many forecasts, which is what the track record is for.",
        },
        goals: {
          q: "Both teams are expected to score 1.5 goals. Which exact score is the likeliest?",
          options: ["1–1", "2–2", "1.5–1.5, obviously"],
          answer: 0,
          why: "1–1, at about 11%. So even the likeliest score misses nine times in ten. Exact scores are for fun, not for the mortgage.",
        },
        xg: {
          q: "A team scores three goals from chances worth 0.9 xG. What is the best guess for next week?",
          options: ["Three again: they are clinical", "Goals closer to what the chances are worth", "None: they have used up their luck"],
          answer: 1,
          why: "Finishing that hot rarely lasts, so expect goals in line with the chances. And luck doesn’t run out either: last week owes them nothing.",
        },
        models: {
          q: "Why publish the average of three models and not just the best one?",
          options: ["The average always beats the best model", "Nobody knows in advance which model will have a bad week", "Three models look more impressive than one"],
          answer: 1,
          why: "The average is graded no worse than the worst of the three in any match, and usually close to the best. Which one was best I only know afterwards.",
        },
        odds: {
          q: "A coin toss is priced at 1.90 for heads and 1.90 for tails. What is the bookmaker’s margin?",
          options: ["Nothing: the coin is fair", "About 5%", "10%"],
          answer: 1,
          why: "1 ÷ 1.90 = 52.6% for each side, 105.3% together. The 5.3% on top is the margin. Remember the 1.90: it comes back in the last drill.",
        },
        grading: {
          q: "Two forecasters both give the home side 20%. A puts 60% on the draw, B puts 60% on the away win. The home side wins. Who gets the worse score?",
          options: ["A", "B", "The same: both gave the winner 20%"],
          answer: 1,
          why: "B: 0.50 against 0.34 for A. Both missed, but B leaned towards the opposite result, and for the ranked probability score a draw is the nearer miss.",
        },
        market: {
          q: "After 100 bets at odds of 1.90, a friend is €8 up. What does that tell you?",
          options: ["He can beat the bookmakers", "Not much: plenty of coin-flippers are up by then", "The bookmaker got its prices wrong"],
          answer: 1,
          why: "About one pure guesser in ten is at least €8 up after 100 such bets, and three in ten are in profit. Ask again after 2,000.",
        },
        luck: {
          q: "Eighteen identical clubs play a full season, every match settled by dice. Roughly how many points does the champion finish with?",
          options: ["About 47, the same as everyone", "About 61", "About 80, like a real champion"],
          answer: 1,
          why: "About 61, with the bottom club on about 33. Luck alone spreads identical teams by nearly 30 points. Real Bundesliga champions average 80 and the bottom club 24: the rest of that gap is quality.",
        },
        elo: {
          q: "A club rated 1700 draws at home with one rated 1350. What happens to its rating?",
          options: ["It goes up: a point is a point", "It goes down", "Nothing: draws don’t count"],
          answer: 1,
          why: "With home advantage it was expected to take about 0.91 of a win. A draw is worth 0.5, so it drops about 8 points and the visitors gain the same 8.",
        },
        calibration: {
          q: "Of 200 matches a forecaster called 70% home wins, 110 ended in a home win (55%). The forecaster is…",
          options: ["Too bold", "Too shy", "Well calibrated: 55% is close enough"],
          answer: 0,
          why: "It said 70% and the world said 55%: more sure than it had reason to be. On a calibration chart that dot sits below the diagonal. Over 200 matches, a 15-point gap is not bad luck.",
        },
        staking: {
          q: "Odds of 2.10, and you are sure your chance is 50%. What share of your pot does Kelly say to bet?",
          options: ["About 5%", "About 25%", "Half: it’s 50–50"],
          answer: 0,
          why: "Your edge is 0.50 × 2.10 − 1 = 0.05. Divide by the odds minus one (1.10) and you get 4.5%. Kelly bets are small, and that is with an edge you are sure of.",
        },
      },
    },
    de: {
      home: "Heim\u00adsieg",
      draw: "Remis",
      away: "Auswärts\u00adsieg",
      teamWin: "Sieg {team}",
      replayTitle: "Wiederholungsmaschine",
      replaySource: "{match}, {date} · meine Prognose",
      playOnce: "Einmal spielen",
      play100: "100-mal spielen",
      clear: "Leeren",
      forecastIn100: "Prognose: {n} von 100",
      replayNone: "Noch nichts gespielt. Jeder Klick spielt das Spiel einmal, meine Prognose ist der Würfel.",
      replayOne: "Wiederholung 1: {result}. Ein Spiel beweist gar nichts, und genau darum geht es.",
      replaySome: "Wiederholung {n}: {result}.",
      replayFull: "100 Wiederholungen: {h} – {d} – {a}. Die Prognose sagte {fh} – {fd} – {fa}. Noch mal klicken: Die Prognose bleibt, die Zählung nicht.",
      replayReveal: "Und was ist wirklich passiert?",
      replayRevealText: "Hamburg gewann 1:0. Ein blauer Punkt. Die Prognose war so wenig falsch wie ein Wetterbericht mit 30\u00a0% Regenrisiko an einem Tag, an dem es regnet.",
      goalTitle: "Tormaschine",
      goalSource: "Ein beliebiges Spiel",
      goalPick: "Oder ein Spiel vom {md}. Spieltag laden",
      goalPickNone: "Eigene Zahlen",
      xgHome: "Heimteam: Tore im Schnitt",
      xgAway: "Auswärtsteam: Tore im Schnitt",
      xgTeam: "{team}: Tore im Schnitt",
      likeliest: "Häufigstes Ergebnis",
      over25: "Über 2,5 Tore",
      btts: "Beide treffen",
      gridCaption: "Wahrscheinlichkeit jedes Ergebnisses in Prozent. Heimtore links, Auswärtstore oben. Das umrandete Feld ist das wahrscheinlichste.",
      gridAria: "Ergebnisraster. Am wahrscheinlichsten: {score} mit {p}.",
      goalFine: "Reines Poisson: Die Tore beider Teams werden getrennt berechnet. Dixon–Coles korrigiert zusätzlich die niedrigen Ergebnisse ein wenig, das lässt dieses Spielzeug weg.",
      shotTitle: "Schusskarte",
      shotSource: "Aufs Feld tippen, um zu schießen",
      shotAria: "Das Angriffsdrittel von oben gesehen, das Tor ist oben. {count} Schüsse abgegeben.",
      shotNone: "Noch kein Schuss. Irgendwo vor dem Tor tippen oder die Knöpfe benutzen.",
      shotLast: "xG {xg}: {odds} {outcome}",
      oneIn: "Ein Schuss von hier geht etwa jedes {n}. Mal rein.",
      mostly: "Ein Schuss von hier geht öfter rein als daneben.",
      goal: "Tor!",
      noGoal: "Kein Tor.",
      shots: "Schüsse",
      xg: "xG",
      goals: "Tore",
      presets: "Schuss von",
      presetSix: "Fünfmeterraum",
      presetSpot: "Elfmeterpunkt",
      presetEdge: "Strafraumgrenze",
      presetAngle: "Spitzer Winkel",
      presetFar: "25 Meter",
      again: "Dieselben Schüsse noch mal",
      shotPar: "Tore und xG passen ungefähr zusammen.",
      shotHot: "Es läuft: {diff} Tore mehr, als die Chancen wert waren. Genießen, solange es hält.",
      shotCold: "Ladehemmung: {diff} Tore weniger, als die Chancen wert waren. Die xG sagen: weiterschießen.",
      shotFull: "Das Feld ist voll. Leeren, um weiterzuschießen.",
      shotLegend: "Gefüllt: Tor. Umriss: kein Tor. Größer: bessere Chance.",
      shotFine: "Ein Spielzeugmodell: nur Entfernung und Winkel. Echte xG-Modelle wie das von Understat, aus dem meine Modelle lernen, wissen auch, ob es ein Kopfball war, wie der Ball kam und wo die Verteidiger standen.",
      modelsTitle: "Drei Modelle, ein Mittelwert",
      modelsSource: "{md}. Spieltag, wie veröffentlicht",
      modelsExample: "Beispiel: 10. Spieltag",
      match: "Spiel",
      dixonColes: "Dixon–Coles",
      bayesian: "Schüsse zu Toren",
      xgboost: "XGBoost",
      ensemble: "Ensemble",
      bookmakers: "Buchmacher",
      spread: "Beim Sieg von {team} liegen die drei Modelle zwischen {low} und {high}: {gap} auseinander.",
      spreadTight: "Beim Sieg von {team} sind sich die drei Modelle bis auf einen Punkt einig.",
      barAria: "{name}: {home} {h}, Remis {d}, {away} {a}",
      point: { one: "{count} Punkt", other: "{count} Punkte" },
      longTitle: "Auf lange Sicht",
      longSource: "1-€-Wetten zur Quote 1,90",
      skill: "Trefferquote",
      skillFlip: "Münzwurf",
      skillEven: "etwa Gewinnschwelle",
      bets: "Anzahl Wetten",
      rerun: "Noch mal laufen lassen",
      perBet: "Erwartung pro 1\u00a0€",
      inProfit: "Im Plus nach {n} Wetten",
      average: "Ergebnis im Schnitt",
      longAria: "{paths} simulierte Wettende über {n} Wetten. {share} solcher Wettenden landen im Plus; das durchschnittliche Ergebnis ist {avg}.",
      longLose: "Kein Vorteil, also gewinnt am Ende die Marge. Die Glücklichen merken es nur später.",
      longEven: "Ziemlich genau an der Gewinnschwelle: Etwa die Hälfte landet im Plus, die Hälfte im Minus, und der Buchmacher bekommt trotzdem pünktlich sein Geld.",
      longWin: "Ein echter Vorteil, und trotzdem liegen nach {n} Wetten noch {behind} dieser Wettenden hinten. Können braucht lange, um sich zu zeigen; Glück ist sofort da.",
      longLegend: "Jede Linie ist eine Person. Helle Linien enden im Plus, blasse nicht. Gestrichelt: der Durchschnitt.",
      axisBets: "Wetten",
      gameTitle: "Rate die Prognose",
      gameSource: "{md}. Spieltag",
      gameCount: "Spiel {n} von {total}",
      gameAsk: "Wie stehen die Chancen? Regler einstellen, dann festlegen.",
      lock: "Festlegen",
      next: "Nächstes Spiel",
      finish: "Zur Auswertung",
      you: "Du",
      models: "Meine Modelle",
      gameOff: "{gap} von meinen Modellen entfernt.",
      gameOffBooks: "Die Buchmacher liegen {gap} von ihnen entfernt.",
      gameBooksAgree: "Buchmacher und Modelle sind sich hier so gut wie einig.",
      gameSpot: "Punktlandung.",
      gameDone: "Abpfiff",
      gameAvg: "Im Schnitt lagst du {gap} von meinen Modellen entfernt. Die Buchmacher lagen {books} entfernt.",
      gameDraw: "Dem Remis hast du im Schnitt {you} gegeben, meine Modelle {models}.",
      gameSharp: "Stark. Du und die Modelle würdet euch gut verstehen.",
      gameDecent: "Gutes Auge. Die Modelle würden dich zur Sitzung dazuholen.",
      gameFar: "Die Modelle widersprechen höflich. Die Buchmacher übrigens auch.",
      gameAgain: "Noch mal spielen",
      gameBoard: "Zum Spieltag",
      gameFine: "Das Spiel vergleicht dich mit der Prognose; die Auswertung bewertet dich nach Abpfiff gegen das Ergebnis. Tipps schließen mit dem Anpfiff und bleiben auf diesem Gerät.",
      gameClosed: "Der {md}. Spieltag hat begonnen, Tipps sind geschlossen. Der nächste Spieltag öffnet, sobald seine Prognosen erscheinen, meist am Donnerstag.",
      gameSaved: "Deine Tipps sind auf diesem Gerät gespeichert. Nach dem Abpfiff wiederkommen: Die Auswertung bewertet dich gegen die Ergebnisse.",
      cardTitle: "Deine Auswertung",
      cardYours: "Du: {h} · {d} · {a}",
      cardKickoff: "Anpfiff {when}",
      cardWaiting: "Ergebnis steht noch aus",
      cardTotal: "Nach {n} bewerteten Spielen: du {you}, meine Modelle {models}{books}.",
      cardBooks: ", die Buchmacher {books}",
      cardWin: "Du liegst vorn. Genießen, die Stichprobe ist klein.",
      cardLose: "Noch nicht vorn. Kleine Stichproben sind in beide Richtungen gnadenlos.",
      cardFine: "Ranked Probability Score pro Spiel, niedriger ist besser. Der beste Wert jeder Zeile ist fett. Buchmacher: ihr Durchschnittspreis bei Veröffentlichung der Prognose.",
      check: "Kurzer Check",
      checkDone: "Kurzer Check · erledigt",
      right: "Richtig.",
      wrong: "Nicht ganz. Noch ein Versuch.",
      progress: "{done} von {total} Übungen geschafft",
      rankLabel: "Deine Liga:",
      ranks: ["Kreisliga", "Regionalliga", "2. Bundesliga", "Bundesliga", "Meister"],
      rankLines: [
        "Kreisliga. Hier fängt jeder an.",
        "Halbprofi. Eine Marge erkennst du, wenn du sie siehst.",
        "Zweite Liga. Der Aufstieg wird in Teil zwei entschieden.",
        "Erste Liga. Du kannst jede Zahl auf dieser Seite lesen, und ihr widersprechen.",
        "Meister. Du weißt, was eine Tabelle, ein Rating und ein Einsatz wirklich sagen, und damit mehr als die meisten, die an diesem Wochenende wetten.",
      ],
      fullTime: "Abpfiff",
      halfTime: "Halbzeit",
      toPartTwo: "Weiter zu Teil zwei",
      toPartOne: "Zurück zu Teil eins",
      reset: "Von vorn anfangen",
      toBoard: "Zu den Prognosen der Woche",
      q: {
        probabilities: {
          q: "Im Oktober gaben meine Modelle Hamburg gegen Stuttgart 32\u00a0%. Hamburg gewann 1:0. War die Prognose falsch?",
          options: ["Ja: 32\u00a0% sind weniger als die Hälfte", "Ein einzelnes Spiel kann das nicht zeigen", "Nein: Sie haben gewonnen, also stimmte sie"],
          answer: 1,
          why: "Was mit 32\u00a0% vorhergesagt wird, sollte etwa jedes dritte Mal eintreten. Ob das stimmt, zeigt sich erst über viele Prognosen, und dafür gibt es die Bilanz.",
        },
        goals: {
          q: "Beide Teams treffen im Schnitt 1,5-mal. Welches genaue Ergebnis ist am wahrscheinlichsten?",
          options: ["1:1", "2:2", "1,5:1,5, ist doch klar"],
          answer: 0,
          why: "1:1, mit etwa 11\u00a0%. Selbst das wahrscheinlichste Ergebnis geht also neunmal von zehn daneben. Genaue Ergebnisse sind etwas für die Tipprunde, nicht für die Altersvorsorge.",
        },
        xg: {
          q: "Ein Team macht drei Tore aus Chancen im Wert von 0,9 xG. Was ist die beste Schätzung für nächste Woche?",
          options: ["Wieder drei: Die sind eben eiskalt", "Tore näher an dem, was die Chancen wert sind", "Keins: Das Glück ist aufgebraucht"],
          answer: 1,
          why: "So eine Chancenverwertung hält selten, also eher Tore im Rahmen der Chancen. Aufgebraucht ist das Glück aber auch nicht: Die letzte Woche schuldet niemandem etwas.",
        },
        models: {
          q: "Warum der Mittelwert aus drei Modellen und nicht einfach das beste?",
          options: ["Der Mittelwert schlägt immer das beste Modell", "Niemand weiß vorher, welches Modell eine schlechte Woche hat", "Drei Modelle machen mehr her als eins"],
          answer: 1,
          why: "Der Mittelwert wird in keinem Spiel schlechter bewertet als das schlechteste der drei und liegt meist nah am besten. Welches das beste war, weiß ich erst hinterher.",
        },
        odds: {
          q: "Ein Münzwurf steht bei 1,90 für Kopf und 1,90 für Zahl. Wie hoch ist die Marge des Buchmachers?",
          options: ["Null: Die Münze ist fair", "Etwa 5\u00a0%", "10\u00a0%"],
          answer: 1,
          why: "1 ÷ 1,90 = 52,6\u00a0% für jede Seite, zusammen 105,3\u00a0%. Die 5,3\u00a0% obendrauf sind die Marge. Die 1,90 bitte merken: Sie kommt in der letzten Übung wieder.",
        },
        grading: {
          q: "Zwei Prognosen geben dem Heimteam je 20\u00a0%. A setzt 60\u00a0% aufs Remis, B 60\u00a0% auf den Auswärtssieg. Das Heimteam gewinnt. Wer bekommt die schlechtere Note?",
          options: ["A", "B", "Gleich: Beide gaben dem Sieger 20\u00a0%"],
          answer: 1,
          why: "B: 0,50 gegenüber 0,34 für A. Beide lagen daneben, aber B tendierte zum entgegengesetzten Ergebnis, und für den Ranked Probability Score liegt ein Remis näher dran.",
        },
        market: {
          q: "Nach 100 Wetten zur Quote 1,90 liegt ein Kumpel 8\u00a0€ im Plus. Was sagt dir das?",
          options: ["Er kann die Buchmacher schlagen", "Wenig: Viele Münzwerfer liegen dann auch im Plus", "Der Buchmacher hat sich verrechnet"],
          answer: 1,
          why: "Etwa jeder Zehnte, der nur rät, liegt nach 100 solchen Wetten mindestens 8\u00a0€ vorn, drei von zehn sind im Plus. Nach 2.000 noch mal fragen.",
        },
        luck: {
          q: "Achtzehn gleich starke Klubs spielen eine ganze Saison, jedes Spiel entscheidet der Würfel. Wie viele Punkte hat der Meister am Ende ungefähr?",
          options: ["Etwa 47, wie alle anderen", "Etwa 61", "Etwa 80, wie ein echter Meister"],
          answer: 1,
          why: "Etwa 61, der Letzte etwa 33. Allein das Glück zieht gleich starke Teams fast 30 Punkte auseinander. Echte Bundesliga-Meister holen im Schnitt 80 Punkte, der Letzte 24: Der Rest des Abstands ist Qualität.",
        },
        elo: {
          q: "Ein Klub mit 1700 Punkten spielt zu Hause 1:1 gegen einen mit 1350. Was passiert mit seinem Rating?",
          options: ["Es steigt: Punkt ist Punkt", "Es sinkt", "Nichts: Remis zählen nicht"],
          answer: 1,
          why: "Mit Heimvorteil wurden von ihm etwa 0,91 eines Siegs erwartet. Ein Remis zählt 0,5, also verliert er etwa 8 Punkte, und die Gäste bekommen dieselben 8.",
        },
        calibration: {
          q: "Von 200 Spielen, denen eine Prognose 70\u00a0% Heimsieg gab, endeten 110 mit einem Heimsieg (55\u00a0%). Die Prognose ist …",
          options: ["zu forsch", "zu zaghaft", "gut kalibriert: 55\u00a0% ist nah genug"],
          answer: 0,
          why: "Sie sagte 70\u00a0%, die Wirklichkeit 55\u00a0%: sicherer, als sie Grund hatte. In einer Kalibrierungsgrafik liegt dieser Punkt unter der Diagonale. Bei 200 Spielen sind 15 Punkte Abstand kein Pech mehr.",
        },
        staking: {
          q: "Quote 2,10, und du bist dir sicher, dass deine Chance 50\u00a0% ist. Welchen Anteil deines Topfs setzt Kelly?",
          options: ["Etwa 5\u00a0%", "Etwa 25\u00a0%", "Die Hälfte: Es steht 50:50"],
          answer: 0,
          why: "Dein Vorteil ist 0,50 × 2,10 − 1 = 0,05. Geteilt durch Quote minus eins (1,10) ergibt das 4,5\u00a0%. Kelly-Einsätze sind klein, und das bei einem Vorteil, bei dem du dir sicher bist.",
        },
      },
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
  const points = (value) => say("point", { count: Math.round(value * 100) });
  const euro = (value, digits = 0) => new Intl.NumberFormat(I18N.locale, {
    style: "currency", currency: "EUR", signDisplay: "exceptZero", minimumFractionDigits: digits, maximumFractionDigits: digits,
  }).format(value);

  function button(className, text, onClick) {
    const node = element("button", className, text);
    node.type = "button";
    node.addEventListener("click", onClick);
    return node;
  }

  function head(title, source) {
    const node = element("div", "calc-head");
    node.append(element("p", "calc-title", title), element("p", "calc-source", source));
    return node;
  }

  function stat(label, value) {
    const node = element("div", "stat");
    const number = element("dd", "stat-value", value);
    node.append(element("dt", "stat-label", label), number);
    return { node, number };
  }

  // A forecast bar in the site's three colours. Filled is a model, outline is the bookmakers.
  function forecastBar(probs, { outline = false } = {}) {
    const bar = element("div", `calc-bar mini-bar${outline ? " is-outline" : ""}`);
    probs.forEach((p, index) => {
      const part = element("span", `calc-bar-part part-${index}`);
      part.style.flexGrow = String(Math.max(p, 0.001));
      bar.append(part);
    });
    return bar;
  }

  function barRow(name, probs, teams, options = {}) {
    const row = element("div", `bar-row${options.key ? " is-key" : ""}`);
    const bar = forecastBar(probs, options);
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", say("barAria", { name, home: teams.home, away: teams.away, h: pct(probs[0]), d: pct(probs[1]), a: pct(probs[2]) }));
    row.append(element("span", "bar-name", name), element("span", "bar-nums", probs.map(pct).join(" · ")), bar);
    return row;
  }

  // Bookmaker odds as chances that add up to 100% (margin removed proportionally, as everywhere on the site).
  function marketProbs(odds) {
    if (!Array.isArray(odds) || !odds.every((value) => value > 1)) return null;
    const inverse = odds.map((value) => 1 / value);
    const total = inverse.reduce((sum, value) => sum + value, 0);
    return inverse.map((value) => value / total);
  }

  /* ---------- This matchday's forecasts ---------- */

  // One real forecast (matchday 10, 2026/27), in case data/forecasts.json cannot be read.
  const EXAMPLE = {
    home: "FC Bayern München",
    away: "1. FC Köln",
    model: [0.8704, 0.0852, 0.0444],
    models: { dixonColes: [0.8714, 0.0862, 0.0424], bayesian: [0.8911, 0.0702, 0.0387], xgboost: [0.8487, 0.099, 0.0523] },
    expectedGoals: [3.68, 0.83],
    market: marketProbs([1.08, 11.57, 19.72]),
  };
  let week = null; // { matchday, matches: [...] } once loaded

  async function loadWeek() {
    try {
      const response = await fetch(new URL("../data/forecasts.json", HERE), { cache: "no-cache" });
      if (!response.ok) return;
      const data = await response.json();
      const matchday = Object.keys(data.matchdays ?? {}).map(Number).sort((a, b) => b - a)[0];
      const block = data.matchdays?.[matchday];
      const matches = Object.entries(block?.matches ?? {})
        .filter(([, match]) => Array.isArray(match.model) && match.models && match.home && match.away)
        .sort(([, a], [, b]) => String(a.kickoff).localeCompare(String(b.kickoff)))
        .map(([matchId, match]) => ({
          matchId,
          kickoff: match.kickoff ? new Date(match.kickoff) : null,
          home: match.home,
          away: match.away,
          model: match.model,
          models: match.models,
          expectedGoals: match.expectedGoals ?? null,
          market: marketProbs(match.market?.odds),
        }));
      if (!matches.length) return;
      week = { season: data.season, matchday, matches };
      buildGoals();
      buildModels();
      buildGame();
      loadResults();
    } catch {
      // The built-in example stays; the game stays hidden.
    }
  }

  /* ---------- Replay machine ---------- */

  const replayBox = document.getElementById("replay-toy");
  const REPLAY = { home: "Hamburger SV", away: "VfB Stuttgart", model: [0.32, 0.24, 0.44], date: "2026-10-17T13:30:00Z" };
  let plays = [];

  function draw(probs) {
    const roll = Math.random();
    return roll < probs[0] ? 0 : roll < probs[0] + probs[1] ? 1 : 2;
  }

  function buildReplay() {
    if (!replayBox) return;
    const labels = [say("teamWin", { team: REPLAY.home }), say("draw"), say("teamWin", { team: REPLAY.away })];
    const date = I18N.dateFormat(REPLAY.date, { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Berlin" });
    const top = head(say("replayTitle"), say("replaySource", { match: `${REPLAY.home} – ${REPLAY.away}`, date }));

    const stats = element("dl", "stats");
    const tiles = labels.map((label, index) => {
      const tile = stat(label, "0");
      tile.node.classList.add(`key-${index}`);
      tile.node.append(element("dd", "stat-sub", say("forecastIn100", { n: Math.round(REPLAY.model[index] * 100) })));
      stats.append(tile.node);
      return tile;
    });

    const dots = element("div", "replay-dots");
    dots.setAttribute("aria-hidden", "true");
    const cells = Array.from({ length: 100 }, (_, index) => {
      const dot = element("span", "replay-dot");
      dot.style.setProperty("--i", String(index));
      dots.append(dot);
      return dot;
    });

    const line = element("p", "calc-note toy-line");
    line.setAttribute("aria-live", "polite");

    function paint(stagger) {
      dots.classList.toggle("is-staggered", Boolean(stagger) && !calm.matches);
      cells.forEach((dot, index) => {
        dot.className = `replay-dot${index < plays.length ? ` part-${plays[index]} is-on` : ""}`;
      });
      const counts = [0, 1, 2].map((outcome) => plays.filter((play) => play === outcome).length);
      tiles.forEach((tile, index) => { tile.number.textContent = String(counts[index]); });
      const n = plays.length;
      const result = n ? labels[plays[n - 1]] : "";
      const forecast = REPLAY.model.map((p) => Math.round(p * 100));
      line.textContent = n === 0 ? say("replayNone")
        : n === 100 ? say("replayFull", { h: counts[0], d: counts[1], a: counts[2], fh: forecast[0], fd: forecast[1], fa: forecast[2] })
          : say(n === 1 ? "replayOne" : "replaySome", { n, result });
    }

    const actions = element("div", "toy-actions");
    actions.append(
      button("toy-button is-primary", say("playOnce"), () => {
        if (plays.length >= 100) plays = [];
        plays.push(draw(REPLAY.model));
        paint(false);
      }),
      button("toy-button", say("play100"), () => {
        // Empty the board first, so every dot drops in again on a second press.
        plays = [];
        paint(false);
        void dots.offsetWidth;
        plays = Array.from({ length: 100 }, () => draw(REPLAY.model));
        paint(true);
      }),
      button("toy-button is-quiet", say("clear"), () => {
        plays = [];
        paint(false);
      }),
    );

    const reveal = element("details", "howto");
    reveal.append(element("summary", "", say("replayReveal")), element("p", "", say("replayRevealText")));
    replayBox.replaceChildren(top, stats, dots, line, actions, reveal);
    paint(false);
  }

  /* ---------- Goal machine ---------- */

  const goalBox = document.getElementById("goal-toy");
  const goalState = { lambda: [1.5, 1.2], match: -1 };
  const MAX_GOALS = 14; // enough that nothing measurable is left out, even at four goals a side

  function poisson(lambda) {
    const out = [Math.exp(-lambda)];
    for (let k = 1; k <= MAX_GOALS; k += 1) out.push(out[k - 1] * lambda / k);
    return out;
  }

  function scoreMaths([home, away]) {
    const h = poisson(home);
    const a = poisson(away);
    const probs = [0, 0, 0];
    let over = 0;
    let top = [0, 0];
    for (let i = 0; i <= MAX_GOALS; i += 1) {
      for (let j = 0; j <= MAX_GOALS; j += 1) {
        const p = h[i] * a[j];
        probs[i > j ? 0 : i === j ? 1 : 2] += p;
        if (i + j >= 3) over += p;
        if (p > h[top[0]] * a[top[1]]) top = [i, j];
      }
    }
    const total = probs[0] + probs[1] + probs[2];
    return {
      probs: probs.map((p) => p / total),
      over,
      btts: (1 - h[0]) * (1 - a[0]),
      top,
      topP: h[top[0]] * a[top[1]],
      cell: (i, j) => h[i] * a[j],
    };
  }

  function buildGoals() {
    if (!goalBox) return;
    const match = week?.matches[goalState.match] ?? null;
    const top = head(say("goalTitle"), match ? `${match.home} – ${match.away}` : say("goalSource"));

    const bar = element("div", "calc-bar");
    bar.setAttribute("aria-hidden", "true");
    const parts = [0, 1, 2].map((index) => {
      const part = element("span", `calc-bar-part part-${index}`);
      bar.append(part);
      return part;
    });
    const barKey = element("p", "bar-key");
    const keys = [say("home"), say("draw"), say("away")].map((label, index) => {
      const item = element("span", `key-${index}`);
      const value = element("strong");
      item.append(`${label} `, value);
      barKey.append(item);
      return value;
    });

    const sliders = element("div", "sliders");
    const fields = [0, 1].map((side) => {
      const row = element("label", `slider-row ${side === 0 ? "tri-home" : "tri-away"}`);
      const label = match ? say("xgTeam", { team: side === 0 ? match.home : match.away }) : say(side === 0 ? "xgHome" : "xgAway");
      const field = element("input", "tri-range");
      field.type = "range";
      field.min = "0.2";
      field.max = "4";
      field.step = "0.1";
      field.value = String(goalState.lambda[side]);
      const out = element("output", "tri-value");
      field.addEventListener("input", () => {
        goalState.lambda[side] = Number(field.value);
        update();
      });
      row.append(element("span", "tri-label", label), field, out);
      sliders.append(row);
      return { field, out };
    });

    const facts = element("dl", "stats");
    const likeliest = stat(say("likeliest"), "");
    const overTile = stat("", "");
    const bttsTile = stat("", "");
    for (const [tile, term, label] of [[overTile, "over-25", say("over25")], [bttsTile, "btts", say("btts")]]) {
      const link = element("button", "term", label);
      link.type = "button";
      link.dataset.term = term;
      tile.node.querySelector("dt").append(link);
    }
    const likeliestSub = element("dd", "stat-sub", "");
    likeliest.node.append(likeliestSub);
    facts.append(likeliest.node, overTile.node, bttsTile.node);

    const figure = element("figure", "score-grid toy-grid");
    const grid = element("div", "score-grid-cells");
    grid.setAttribute("role", "img");
    const cells = [];
    grid.append(element("span", "is-axis", ""));
    for (let j = 0; j < 6; j += 1) grid.append(element("span", "is-axis", String(j)));
    for (let i = 0; i < 6; i += 1) {
      grid.append(element("span", "is-axis", String(i)));
      cells.push([]);
      for (let j = 0; j < 6; j += 1) {
        const cell = element("span");
        cells[i].push(cell);
        grid.append(cell);
      }
    }
    figure.append(grid, element("figcaption", "", say("gridCaption")));

    function update() {
      const maths = scoreMaths(goalState.lambda);
      fields.forEach((item, side) => { item.out.textContent = num(goalState.lambda[side], 1); });
      maths.probs.forEach((p, index) => {
        parts[index].style.flexGrow = String(Math.max(p, 0.001));
        parts[index].textContent = p >= 0.12 ? pct(p) : "";
        keys[index].textContent = pct(p);
      });
      likeliest.number.textContent = I18N.score(maths.top[0], maths.top[1]);
      likeliestSub.textContent = pct(maths.topP);
      overTile.number.textContent = pct(maths.over);
      bttsTile.number.textContent = pct(maths.btts);
      const max = maths.topP;
      cells.forEach((line, i) => line.forEach((cell, j) => {
        const p = maths.cell(i, j);
        const colour = i > j ? "79 143 238" : i === j ? "122 129 145" : "245 161 85";
        cell.textContent = p >= 0.005 ? String(Math.round(p * 100)) : "";
        cell.title = `${I18N.score(i, j)}: ${pct1(p)}`;
        cell.style.background = `rgb(${colour} / ${(8 + 72 * Math.min(1, p / max)).toFixed(0)}%)`;
        cell.classList.toggle("is-top", i === maths.top[0] && j === maths.top[1]);
      }));
      grid.setAttribute("aria-label", say("gridAria", { score: I18N.score(maths.top[0], maths.top[1]), p: pct(maths.topP) }));
    }

    const children = [top, sliders, bar, barKey, facts, figure];
    if (week) {
      const pick = element("label", "toy-pick");
      const select = element("select", "toy-select");
      select.append(new Option(say("goalPickNone"), "-1"));
      week.matches.forEach((item, index) => {
        if (item.expectedGoals) select.append(new Option(`${item.home} – ${item.away}`, String(index)));
      });
      select.value = String(goalState.match);
      select.addEventListener("change", () => {
        goalState.match = Number(select.value);
        const chosen = week.matches[goalState.match];
        // The sliders move in tenths between 0.2 and 4.
        if (chosen) goalState.lambda = chosen.expectedGoals.map((value) => Math.min(4, Math.max(0.2, Math.round(value * 10) / 10)));
        buildGoals();
        goalBox.querySelector(".toy-select")?.focus();
      });
      pick.append(element("span", "toy-pick-label", say("goalPick", { md: week.matchday })), select);
      children.push(pick);
    }
    children.push(element("p", "calc-fine", say("goalFine")));
    goalBox.replaceChildren(...children);
    update();
  }

  /* ---------- Shot map ---------- */

  const shotBox = document.getElementById("shot-toy");
  const SVG = "http://www.w3.org/2000/svg";
  // The pitch in metres: 60 wide, goal line 3 from the top, 33 deep.
  const PITCH = { width: 60, height: 36, centre: 30, line: 3 };
  const POST = 3.66; // half a goal
  const MAX_SHOTS = 60;
  let shotList = []; // { x (metres from the middle of the goal), d (metres from the goal line), xg, goal }

  function svg(tag, attributes = {}) {
    const node = document.createElementNS(SVG, tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    return node;
  }

  // A toy xG model: a logistic curve on the angle the goal fills (radians) and the distance (metres).
  // Tuned by hand to land near the usual figures: about 0.35 from the edge of the six-yard box,
  // 0.12 from the penalty spot in open play, 0.05 from the edge of the area, under 0.03 from 25 metres.
  function toyXg(x, d) {
    const distance = Math.hypot(x, d);
    let angle = Math.atan2(2 * POST * d, x * x + d * d - POST * POST);
    if (angle < 0) angle += Math.PI;
    return 1 / (1 + Math.exp(-(-2.45 + 1.86 * angle - 0.07 * distance)));
  }

  function shoot(x, d) {
    if (shotList.length >= MAX_SHOTS) return false;
    const depth = Math.max(0.3, d);
    const xg = toyXg(x, depth);
    shotList.push({ x, d: depth, xg, goal: Math.random() < xg });
    return true;
  }

  function buildShots() {
    if (!shotBox) return;
    const top = head(say("shotTitle"), say("shotSource"));
    const { width, height, centre, line } = PITCH;
    const pitch = svg("svg", { viewBox: `0 0 ${width} ${height}`, class: "pitch", role: "img" });
    const lines = svg("g", { class: "pitch-lines" });
    lines.append(
      svg("rect", { x: 0, y: line, width, height: height - line, class: "pitch-grass" }),
      svg("path", { d: `M0 ${line}H${width}` }),
      svg("rect", { x: centre - POST, y: line - 1.6, width: 2 * POST, height: 1.6, class: "pitch-goal" }),
      svg("rect", { x: centre - 9.16, y: line, width: 18.32, height: 5.5 }),
      svg("rect", { x: centre - 20.16, y: line, width: 40.32, height: 16.5 }),
      svg("circle", { cx: centre, cy: line + 11, r: 0.35, class: "pitch-spot" }),
      svg("path", { d: `M${centre - 7.31} ${line + 16.5}A9.15 9.15 0 0 0 ${centre + 7.31} ${line + 16.5}` }),
    );
    const marks = svg("g", { class: "pitch-shots" });
    pitch.append(lines, marks);

    const readout = element("p", "calc-note toy-line");
    readout.setAttribute("aria-live", "polite");
    const stats = element("dl", "stats");
    const tiles = [stat(say("shots"), "0"), stat(say("xg"), "0"), stat(say("goals"), "0")];
    stats.append(...tiles.map((tile) => tile.node));
    const verdict = element("p", "calc-note");

    function paint(announceLast) {
      marks.replaceChildren(...shotList.map((shot, index) => svg("circle", {
        cx: centre + shot.x,
        cy: line + shot.d,
        r: (0.8 + 1.3 * Math.sqrt(shot.xg)).toFixed(2),
        class: `shot${shot.goal ? " is-goal" : ""}${index === shotList.length - 1 ? " is-last" : ""}`,
      })));
      const total = shotList.reduce((sum, shot) => sum + shot.xg, 0);
      const goals = shotList.filter((shot) => shot.goal).length;
      tiles[0].number.textContent = String(shotList.length);
      tiles[1].number.textContent = num(total, 2);
      tiles[2].number.textContent = String(goals);
      pitch.setAttribute("aria-label", say("shotAria", { count: shotList.length }));
      const last = shotList[shotList.length - 1];
      if (!last) readout.textContent = say("shotNone");
      else if (announceLast) {
        readout.textContent = say("shotLast", {
          xg: num(last.xg, 2),
          odds: last.xg > 0.5 ? say("mostly") : say("oneIn", { n: Math.round(1 / last.xg) }),
          outcome: say(last.goal ? "goal" : "noGoal"),
        });
      }
      const diff = goals - total;
      verdict.hidden = shotList.length < 5;
      verdict.textContent = shotList.length >= MAX_SHOTS ? say("shotFull")
        : Math.abs(diff) < 0.75 ? say("shotPar")
          : say(diff > 0 ? "shotHot" : "shotCold", { diff: num(Math.abs(diff), 1) });
    }

    pitch.addEventListener("click", (event) => {
      const matrix = pitch.getScreenCTM();
      if (!matrix) return;
      const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
      if (point.y < line) return;
      shoot(point.x - centre, point.y - line);
      paint(true);
    });

    const presets = element("div", "toy-actions");
    presets.setAttribute("role", "group");
    presets.setAttribute("aria-label", say("presets"));
    presets.append(element("span", "toy-actions-label", say("presets")));
    for (const [key, x, d] of [["presetSix", 0, 5.5], ["presetSpot", 0, 11], ["presetEdge", 0, 17], ["presetAngle", 9, 2.5], ["presetFar", -4, 25]]) {
      presets.append(button("toy-chip", say(key), () => {
        shoot(x, d);
        paint(true);
      }));
    }
    const actions = element("div", "toy-actions");
    actions.append(
      button("toy-button", say("again"), () => {
        for (const shot of shotList) shot.goal = Math.random() < shot.xg;
        paint(false);
      }),
      button("toy-button is-quiet", say("clear"), () => {
        shotList = [];
        paint(false);
      }),
    );
    shotBox.replaceChildren(top, pitch, element("p", "calc-fine pitch-legend", say("shotLegend")), readout, presets, stats, verdict, actions, element("p", "calc-fine", say("shotFine")));
    paint(true);
  }

  /* ---------- Three models, one average ---------- */

  const modelsBox = document.getElementById("models-toy");
  let modelsMatch = 0;

  function buildModels() {
    if (!modelsBox) return;
    const matches = week?.matches ?? [EXAMPLE];
    const match = matches[Math.min(modelsMatch, matches.length - 1)];
    const top = head(say("modelsTitle"), week ? say("modelsSource", { md: week.matchday }) : say("modelsExample"));
    const children = [top];
    if (matches.length > 1) {
      const pick = element("label", "toy-pick");
      const select = element("select", "toy-select");
      matches.forEach((item, index) => select.append(new Option(`${item.home} – ${item.away}`, String(index))));
      select.value = String(modelsMatch);
      select.addEventListener("change", () => {
        modelsMatch = Number(select.value);
        buildModels();
        modelsBox.querySelector(".toy-select")?.focus();
      });
      pick.append(element("span", "toy-pick-label", say("match")), select);
      children.push(pick);
    } else {
      children.push(element("p", "toy-match", `${match.home} – ${match.away}`));
    }

    const rows = element("div", "bar-rows");
    for (const key of ["dixonColes", "bayesian", "xgboost"]) rows.append(barRow(say(key), match.models[key], match));
    rows.append(barRow(say("ensemble"), match.model, match, { key: true }));
    if (match.market) rows.append(barRow(say("bookmakers"), match.market, match, { outline: true }));
    const key = element("p", "bar-key");
    [say("teamWin", { team: match.home }), say("draw"), say("teamWin", { team: match.away })].forEach((label, index) => {
      key.append(element("span", `key-${index}`, label));
    });

    // Where the three models differ most: on the home win or the away win, whichever is wider.
    const three = ["dixonColes", "bayesian", "xgboost"].map((name) => match.models[name]);
    const gaps = [0, 2].map((outcome) => {
      const values = three.map((probs) => probs[outcome]);
      return { outcome, low: Math.min(...values), high: Math.max(...values) };
    }).sort((a, b) => (b.high - b.low) - (a.high - a.low))[0];
    const team = gaps.outcome === 0 ? match.home : match.away;
    const gap = Math.round(gaps.high * 100) - Math.round(gaps.low * 100);
    const note = element("p", "calc-note", gap <= 1 ? say("spreadTight", { team })
      : say("spread", { team, low: pct(gaps.low), high: pct(gaps.high), gap: say("point", { count: gap }) }));
    children.push(rows, key, note);
    modelsBox.replaceChildren(...children);
  }

  /* ---------- The long run ---------- */

  const longBox = document.getElementById("long-toy");
  const ODDS = 1.9;
  const PATHS = 40;
  const longState = { skill: 0.5, bets: 500, seed: 1 };

  // A small seeded generator, so a resize or a language switch redraws the same lines.
  function random(seed) {
    let state = seed >>> 0;
    return () => {
      state = (state + 0x6d2b79f5) >>> 0;
      let t = state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // The exact chance of being in profit after n bets: more wins than n ÷ 1.90.
  function profitShare(n, p) {
    const need = Math.floor(n / ODDS) + 1;
    let logPmf = n * Math.log(1 - p); // P(0 wins)
    let share = 0;
    for (let k = 0; k <= n; k += 1) {
      if (k >= need) share += Math.exp(logPmf);
      logPmf += Math.log((n - k) / (k + 1)) + Math.log(p / (1 - p));
    }
    return share;
  }

  function niceStep(span, target) {
    const raw = span / target;
    const power = 10 ** Math.floor(Math.log10(raw));
    return [1, 2, 5, 10].map((factor) => factor * power).find((step) => step >= raw);
  }

  function buildLong() {
    if (!longBox) return;
    const top = head(say("longTitle"), say("longSource"));
    const breakEven = 1 / ODDS;

    const skillRow = element("label", "slider-row");
    const field = element("input", "tri-range");
    field.type = "range";
    field.min = "45";
    field.max = "60";
    field.step = "0.5";
    field.value = String(longState.skill * 100);
    const out = element("output", "tri-value is-wide");
    skillRow.append(element("span", "tri-label", say("skill")), field, out);

    const betsRow = element("div", "slider-row");
    const seg = element("div", "segmented toy-seg");
    seg.setAttribute("role", "group");
    seg.setAttribute("aria-label", say("bets"));
    const segButtons = [100, 500, 2000].map((count) => {
      const node = button("", num(count), () => {
        longState.bets = count;
        update();
      });
      seg.append(node);
      return { count, node };
    });
    betsRow.append(element("span", "tri-label", say("bets")), seg);

    const chart = element("div", "long-chart");
    const stats = element("dl", "stats");
    const perBet = stat(say("perBet"), "");
    const share = stat("", "");
    const average = stat(say("average"), "");
    stats.append(perBet.node, share.node, average.node);
    const verdict = element("p", "calc-note toy-line");
    verdict.setAttribute("aria-live", "polite");

    function drawChart() {
      const { skill, bets } = longState;
      const boxWidth = Math.max(260, Math.round(chart.clientWidth || 320));
      const boxHeight = 230;
      const pad = { left: 48, right: 10, top: 10, bottom: 26 };
      const next = random(longState.seed * 7919 + bets);
      const stride = Math.max(1, Math.round(bets / 160));
      const paths = [];
      let low = 0;
      let high = 0;
      for (let index = 0; index < PATHS; index += 1) {
        let money = 0;
        const points = [[0, 0]];
        for (let bet = 1; bet <= bets; bet += 1) {
          money += next() < skill ? ODDS - 1 : -1;
          if (bet % stride === 0 || bet === bets) points.push([bet, money]);
          if (money < low) low = money;
          if (money > high) high = money;
        }
        paths.push({ points, end: money });
      }
      const drift = bets * (skill * ODDS - 1);
      low = Math.min(low, drift);
      high = Math.max(high, drift);
      const step = niceStep(high - low, 4);
      low = Math.floor(low / step) * step;
      high = Math.ceil(high / step) * step;
      const x = (bet) => pad.left + (bet / bets) * (boxWidth - pad.left - pad.right);
      const y = (money) => pad.top + ((high - money) / (high - low)) * (boxHeight - pad.top - pad.bottom);

      const node = svg("svg", { viewBox: `0 0 ${boxWidth} ${boxHeight}`, width: boxWidth, height: boxHeight, class: "long-svg", role: "img" });
      const axis = svg("g", { class: "long-axis" });
      for (let tick = low; tick <= high + step / 2; tick += step) {
        axis.append(svg("line", { x1: pad.left, x2: boxWidth - pad.right, y1: y(tick), y2: y(tick), class: Math.abs(tick) < step / 2 ? "is-zero" : "" }));
        const label = svg("text", { x: pad.left - 6, y: y(tick) + 4, "text-anchor": "end" });
        label.textContent = euro(tick);
        axis.append(label);
      }
      for (const fraction of [0, 0.5, 1]) {
        const label = svg("text", { x: x(bets * fraction), y: boxHeight - 6, "text-anchor": fraction === 0 ? "start" : fraction === 1 ? "end" : "middle" });
        label.textContent = fraction === 1 ? `${num(bets)} ${say("axisBets")}` : num(bets * fraction);
        axis.append(label);
      }
      const linesGroup = svg("g", { class: "long-lines" });
      // Losing lines first, so the winners are drawn on top.
      for (const path of [...paths].sort((a, b) => a.end - b.end)) {
        linesGroup.append(svg("polyline", {
          points: path.points.map(([bet, money]) => `${x(bet).toFixed(1)},${y(money).toFixed(1)}`).join(" "),
          class: path.end > 0 ? "is-up" : "is-down",
        }));
      }
      const ends = { x1: x(0), y1: y(0), x2: x(bets), y2: y(drift) };
      node.append(axis, linesGroup, svg("line", { ...ends, class: "long-mean-halo" }), svg("line", { ...ends, class: "long-mean" }));
      const exact = profitShare(bets, skill);
      node.setAttribute("aria-label", say("longAria", { paths: PATHS, n: num(bets), share: pct(exact), avg: euro(drift) }));
      chart.replaceChildren(node);
    }

    function update() {
      const { skill, bets } = longState;
      const exact = profitShare(bets, skill);
      const drift = bets * (skill * ODDS - 1);
      const tag = Math.abs(skill - 0.5) < 0.001 ? ` · ${say("skillFlip")}` : Math.abs(skill - breakEven) < 0.0026 ? ` · ${say("skillEven")}` : "";
      out.textContent = `${pct1(skill)}${tag}`;
      segButtons.forEach((item) => item.node.setAttribute("aria-pressed", String(item.count === bets)));
      perBet.number.textContent = euro(skill * ODDS - 1, 2);
      share.node.querySelector("dt").textContent = say("inProfit", { n: num(bets) });
      share.number.textContent = pct(exact);
      average.number.textContent = euro(drift);
      const edge = skill * ODDS - 1;
      verdict.textContent = Math.abs(edge) < 0.006 ? say("longEven")
        : edge < 0 ? say("longLose")
          : say("longWin", { n: num(bets), behind: pct(1 - exact) });
      drawChart();
    }

    field.addEventListener("input", () => {
      longState.skill = Number(field.value) / 100;
      update();
    });
    const actions = element("div", "toy-actions");
    actions.append(button("toy-button", say("rerun"), () => {
      longState.seed += 1;
      drawChart();
    }));
    longBox.replaceChildren(top, skillRow, betsRow, chart, element("p", "calc-fine", say("longLegend")), stats, verdict, actions);
    update();
    longBox.redraw = drawChart;
  }

  if (longBox && "ResizeObserver" in window) {
    let lastWidth = 0;
    new ResizeObserver(() => {
      const width = longBox.clientWidth;
      if (width !== lastWidth && longBox.redraw) {
        lastWidth = width;
        longBox.redraw();
      }
    }).observe(longBox);
  }

  /* ---------- Guess the forecast ---------- */

  const gameSection = document.getElementById("game");
  const gameBox = document.getElementById("game-toy");
  const cardBox = document.getElementById("scorecard");
  let game = { index: 0, guesses: [], locked: false, guess: [0.33, 0.34, 0.33] };
  const results = new Map(); // matchId -> [home goals, away goals], once OpenLigaDB has the final score
  let resultsAsked = false;

  // How far apart two forecasts are: the share of probability one would have to move to match the other.
  const distance = (a, b) => a.reduce((sum, p, index) => sum + Math.abs(p - b[index]), 0) / 2;
  const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length;

  // Saved guesses, per season and matchday: { "2026-10": { "83237": [0.6, 0.25, 0.15] } }.
  function readGuesses() {
    try {
      return JSON.parse(localStorage.getItem(GUESS_KEY) ?? "{}") ?? {};
    } catch {
      return {};
    }
  }
  let saved = readGuesses();
  const roundKey = () => `${week.season}-${week.matchday}`;

  function saveGuess(matchId, guess) {
    const key = roundKey();
    // Only the current matchday and the one before are kept.
    const keep = Object.keys(saved).sort((a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1])).slice(0, 1);
    saved = Object.fromEntries(Object.entries(saved).filter(([name]) => name === key || keep.includes(name)));
    saved[key] = { ...(saved[key] ?? {}), [matchId]: guess.map((p) => Math.round(p * 1000) / 1000) };
    try {
      localStorage.setItem(GUESS_KEY, JSON.stringify(saved));
    } catch {
      // Private mode: the scorecard only lasts for this visit.
    }
  }

  // Guesses close at kick-off.
  const isOpen = (match) => !match.kickoff || Date.now() < match.kickoff.getTime();

  function finalScore(match) {
    if (!match?.matchIsFinished) return null;
    const list = Array.isArray(match.matchResults) ? match.matchResults : [];
    const final = list.find((item) => Number(item.resultTypeID) === 2) ?? [...list].sort((a, b) => b.resultOrderID - a.resultOrderID)[0];
    return final ? [Number(final.pointsTeam1), Number(final.pointsTeam2)] : null;
  }

  // One request for the matchday, and only once something with a saved guess has kicked off.
  async function loadResults() {
    if (!week || resultsAsked) return;
    const mine = saved[roundKey()] ?? {};
    if (!week.matches.some((match) => mine[match.matchId] && !isOpen(match))) return;
    resultsAsked = true;
    try {
      const response = await fetch(`${API}/getmatchdata/bl1/${encodeURIComponent(week.season)}/${encodeURIComponent(week.matchday)}`, { cache: "no-cache" });
      if (!response.ok) return;
      const list = await response.json();
      for (const match of Array.isArray(list) ? list : []) {
        const score = finalScore(match);
        if (score) results.set(String(match.matchID), score);
      }
      buildScorecard();
    } catch {
      // The scorecard keeps saying "waiting for the result".
    }
  }

  const outcomeOf = ([home, away]) => (home > away ? 0 : home === away ? 1 : 2);

  function buildScorecard() {
    if (!cardBox) return;
    const mine = week ? saved[roundKey()] ?? {} : {};
    const rows = week ? week.matches.filter((match) => mine[match.matchId]) : [];
    cardBox.hidden = rows.length === 0;
    if (!rows.length) return;
    const top = head(say("cardTitle"), say("gameSource", { md: week.matchday }));
    const list = element("ol", "card-list");
    const graded = [];
    for (const match of rows) {
      const guess = mine[match.matchId];
      const item = element("li", "card-row");
      const name = element("p", "card-match");
      name.append(element("span", "", `${match.home} – ${match.away}`));
      const score = results.get(String(match.matchId));
      item.append(name);
      if (!score) {
        const when = isOpen(match) && match.kickoff
          ? say("cardKickoff", { when: I18N.dateFormat(match.kickoff, { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Berlin" }) })
          : say("cardWaiting");
        item.append(element("p", "card-status", `${say("cardYours", { h: pct(guess[0]), d: pct(guess[1]), a: pct(guess[2]) })} · ${when}`));
      } else {
        const outcome = outcomeOf(score);
        const rpsYou = window.LEARN.rps(guess, outcome);
        const rpsModels = window.LEARN.rps(match.model, outcome);
        const rpsBooks = match.market ? window.LEARN.rps(match.market, outcome) : null;
        graded.push({ rpsYou, rpsModels, rpsBooks });
        const best = Math.min(rpsYou, rpsModels, rpsBooks ?? Infinity);
        name.append(element("span", "card-score", I18N.score(score[0], score[1])));
        const grades = element("p", "card-grades");
        const part = (label, value) => {
          const node = element("span", value <= best + 0.0005 ? "is-best" : "", `${label} ${num(value, 3)}`);
          return node;
        };
        grades.append(part(say("you"), rpsYou), " · ", part(say("models"), rpsModels));
        if (rpsBooks !== null) grades.append(" · ", part(say("bookmakers"), rpsBooks));
        item.append(grades);
      }
      list.append(item);
    }
    const children = [top, list];
    if (graded.length) {
      const total = element("p", "grade-verdict");
      const you = mean(graded.map((g) => g.rpsYou));
      const models = mean(graded.map((g) => g.rpsModels));
      const books = graded.every((g) => g.rpsBooks !== null) ? mean(graded.map((g) => g.rpsBooks)) : null;
      total.textContent = say("cardTotal", { n: graded.length, you: num(you, 3), models: num(models, 3), books: books === null ? "" : say("cardBooks", { books: num(books, 3) }) })
        + ` ${say(you < Math.min(models, books ?? Infinity) - 0.0005 ? "cardWin" : "cardLose")}`;
      children.push(total);
    }
    children.push(element("p", "calc-fine", say("cardFine")));
    cardBox.replaceChildren(...children);
  }

  function buildGame() {
    if (!gameBox || !gameSection) return;
    gameSection.hidden = !week;
    for (const link of document.querySelectorAll('.page-jump a[href="#game"]')) link.hidden = !week;
    if (!week) return;
    buildScorecard();
    const matches = week.matches.filter(isOpen);
    const top = head(say("gameTitle"), say("gameSource", { md: week.matchday }));

    if (!matches.length) {
      gameBox.replaceChildren(top, element("p", "calc-note", say("gameClosed", { md: week.matchday })), element("p", "calc-fine", say("gameFine")));
      return;
    }

    if (game.index >= matches.length) {
      const own = mean(game.guesses.map((guess, index) => distance(guess, matches[index].model)));
      const priced = matches.filter((match) => match.market);
      const lines = [element("p", "game-result", say("gameDone"))];
      lines.push(element("p", "calc-note", priced.length
        ? say("gameAvg", { gap: points(own), books: points(mean(priced.map((match) => distance(match.market, match.model)))) })
        : say("gameOff", { gap: points(own) })));
      lines.push(element("p", "calc-note", say("gameDraw", {
        you: pct(mean(game.guesses.map((guess) => guess[1]))),
        models: pct(mean(matches.map((match) => match.model[1]))),
      })));
      lines.push(element("p", "grade-verdict", say(own < 0.055 ? "gameSharp" : own < 0.105 ? "gameDecent" : "gameFar")));
      lines.push(element("p", "calc-note", say("gameSaved")));
      const actions = element("div", "toy-actions");
      const board = element("a", "toy-button", say("gameBoard"));
      board.href = new URL("../#matchday", HERE).href;
      actions.append(button("toy-button is-primary", say("gameAgain"), () => {
        game = { index: 0, guesses: [], locked: false, guess: [0.33, 0.34, 0.33] };
        buildGame();
        gameBox.querySelector(".tri-range")?.focus();
      }), board);
      gameBox.replaceChildren(top, ...lines, actions, element("p", "calc-fine", say("gameFine")));
      return;
    }

    const match = matches[game.index];
    const count = element("p", "game-count", say("gameCount", { n: game.index + 1, total: matches.length }));
    const name = element("p", "toy-match", `${match.home} – ${match.away}`);
    const labels = [say("teamWin", { team: match.home }), say("draw"), say("teamWin", { team: match.away })];
    const children = [top, count, name];

    if (!game.locked) {
      const sliders = triSlider({ labels, value: game.guess, onInput: (value) => { game.guess = value; } });
      game.guess = sliders.value;
      const actions = element("div", "toy-actions");
      actions.append(button("toy-button is-primary", say("lock"), () => {
        game.guesses[game.index] = game.guess;
        game.locked = true;
        saveGuess(match.matchId, game.guess);
        buildGame();
        gameBox.querySelector(".toy-button")?.focus();
      }));
      children.push(element("p", "calc-note", say("gameAsk")), sliders.node, actions);
    } else {
      const guess = game.guesses[game.index];
      const rows = element("div", "bar-rows");
      rows.append(barRow(say("you"), guess, match), barRow(say("models"), match.model, match, { key: true }));
      if (match.market) rows.append(barRow(say("bookmakers"), match.market, match, { outline: true }));
      const key = element("p", "bar-key");
      labels.forEach((label, index) => key.append(element("span", `key-${index}`, label)));
      const gap = distance(guess, match.model);
      const verdict = element("p", "grade-verdict", gap < 0.015 ? say("gameSpot") : say("gameOff", { gap: points(gap) }));
      verdict.setAttribute("aria-live", "polite");
      if (match.market) {
        const books = distance(match.market, match.model);
        verdict.append(` ${books < 0.015 ? say("gameBooksAgree") : say("gameOffBooks", { gap: points(books) })}`);
      }
      const last = game.index === matches.length - 1;
      const actions = element("div", "toy-actions");
      actions.append(button("toy-button is-primary", say(last ? "finish" : "next"), () => {
        game.index += 1;
        game.locked = false;
        game.guess = [0.33, 0.34, 0.33];
        buildGame();
        (gameBox.querySelector(".tri-range") ?? gameBox.querySelector(".toy-button"))?.focus();
      }));
      children.push(rows, key, verdict, actions);
    }
    children.push(element("p", "calc-fine", say("gameFine")));
    gameBox.replaceChildren(...children);
  }

  /* ---------- Quick checks and progress ---------- */

  let done = new Set();
  try {
    const stored = JSON.parse(localStorage.getItem(STORE_KEY) ?? "{}");
    done = new Set((stored.done ?? []).filter((id) => DRILLS.includes(id)));
  } catch {
    // Private mode or a full store: progress just lasts until the page is closed.
  }
  const answers = {}; // what was tapped in this visit: { drill: option index }

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ done: [...done] }));
    } catch {
      // See above.
    }
  }

  function buildCheck(box) {
    const id = box.dataset.check;
    const item = words().q[id] ?? WORDS.en.q[id];
    if (!item) return;
    const kicker = element("p", "check-kicker", say(done.has(id) ? "checkDone" : "check"));
    const question = element("p", "check-question", item.q);
    const options = element("div", "check-options");
    options.setAttribute("role", "group");
    options.setAttribute("aria-label", say("check"));
    const feedback = element("p", "check-feedback");
    feedback.setAttribute("aria-live", "polite");

    function show() {
      const chosen = answers[id];
      kicker.textContent = say(done.has(id) ? "checkDone" : "check");
      box.classList.toggle("is-done", done.has(id));
      [...options.children].forEach((node, index) => {
        node.setAttribute("aria-pressed", String(index === chosen));
        node.classList.toggle("is-right", index === chosen && index === item.answer);
        node.classList.toggle("is-wrong", index === chosen && index !== item.answer);
      });
      feedback.hidden = chosen === undefined;
      if (chosen !== undefined) {
        feedback.replaceChildren(element("strong", "", `${say(chosen === item.answer ? "right" : "wrong")} `), chosen === item.answer ? item.why : "");
      }
    }

    item.options.forEach((label, index) => {
      options.append(button("check-option", label, () => {
        answers[id] = index;
        if (index === item.answer && !done.has(id)) {
          done.add(id);
          save();
          buildProgress();
        }
        show();
      }));
    });
    box.replaceChildren(kicker, question, options, feedback);
    show();
  }

  const progressBox = document.getElementById("drill-progress");
  const finishBox = document.getElementById("full-time");

  // 0-2 drills Kreisliga, 3-5 Regionalliga, 6-8 2. Bundesliga, 9-10 Bundesliga, all 11 champions.
  function rank() {
    const count = done.size;
    return count >= DRILLS.length ? 4 : count >= 9 ? 3 : count >= 6 ? 2 : count >= 3 ? 1 : 0;
  }

  function buildProgress() {
    const count = done.size;
    const level = rank();
    const names = words().ranks;
    if (progressBox) {
      const text = element("p", "progress-text");
      text.append(say("progress", { done: count, total: DRILLS.length }), " · ", element("strong", "", names[level]));
      const meter = element("div", "progress-meter");
      meter.setAttribute("aria-hidden", "true");
      DRILLS.forEach((id, index) => meter.append(element("span", `${done.has(id) ? "is-done" : ""}${index === 7 ? " is-half" : ""}`)));
      progressBox.replaceChildren(text, meter);
    }
    for (const link of document.querySelectorAll(".page-jump a")) {
      const id = link.getAttribute("href").slice(1);
      link.classList.toggle("is-done", done.has(id));
    }
    for (const kicker of document.querySelectorAll("[data-drill]")) {
      kicker.classList.toggle("is-done", done.has(kicker.dataset.drill));
    }
    if (finishBox) {
      // Half time at the end of part one, full time at the end of part two.
      const half = finishBox.dataset.stage === "half";
      const title = element("p", "finish-title");
      title.append(element("span", "finish-label", `${say("rankLabel")} `), names[level]);
      const actions = element("div", "toy-actions");
      const next = element("a", "toy-button is-primary", say(half ? "toPartTwo" : "toBoard"));
      next.href = half ? new URL("part-two/", HERE).href : new URL("../#matchday", HERE).href;
      actions.append(next);
      if (!half) {
        const back = element("a", "toy-button", say("toPartOne"));
        back.href = HERE.href;
        actions.append(back);
      }
      if (count > 0) {
        actions.append(button("toy-button is-quiet", say("reset"), () => {
          done.clear();
          for (const key of Object.keys(answers)) delete answers[key];
          save();
          buildChecks();
          buildProgress();
        }));
      }
      const ladder = element("ol", "finish-ladder");
      ladder.setAttribute("aria-hidden", "true");
      names.forEach((label, index) => ladder.append(element("li", index === level ? "is-here" : index < level ? "is-past" : "", label)));
      finishBox.replaceChildren(
        element("p", "check-kicker", `${say(half ? "halfTime" : "fullTime")} · ${say("progress", { done: count, total: DRILLS.length })}`),
        title, element("p", "finish-line", words().rankLines[level]), ladder, actions,
      );
      finishBox.classList.toggle("is-complete", level === 4);
    }
  }

  function buildChecks() {
    document.querySelectorAll("[data-check]").forEach(buildCheck);
  }

  /* ---------- Start ---------- */

  function renderAll() {
    buildReplay();
    buildGoals();
    buildShots();
    buildModels();
    buildLong();
    buildGame();
    buildChecks();
    buildProgress();
  }

  // Shared with advanced.js (part two).
  Object.assign(window.LEARN, { head, stat, button, barRow, svg, random, niceStep });

  // The playthings and the game change the page's height after it has loaded, so an address such
  // as #rps or #game is followed again once they are in place, unless the reader has already moved on.
  let moved = false;
  for (const type of ["wheel", "touchstart", "keydown", "pointerdown"]) {
    window.addEventListener(type, () => { moved = true; }, { once: true, passive: true });
  }
  function followHash() {
    if (moved || location.hash.length < 2) return;
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target && !target.closest("[hidden]")) requestAnimationFrame(() => target.scrollIntoView({ behavior: "instant" }));
  }

  renderAll();
  followHash();
  if (goalBox || modelsBox || gameBox) loadWeek().then(followHash);
  I18N.onChange(renderAll);
})();
