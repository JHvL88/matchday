# Jan’s Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves Bundesliga fixtures and results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

What’s on the home page:

- **The matchday.** Its number, dates and one status line: the next kick-off and how long until then, what is live, or how the matchday ended. Step through matchdays with the arrows or the strip of 34 ticks (played, on screen, still to come; arrow keys work too). The choice is kept in the URL (`?md=5`), so a matchday can be linked.
- **The board.** One row per match. The bar is the models’ forecast (home win blue, draw grey, away win orange) and two white pins mark where the bookmakers would cut the same bar, so a pin off a join is a disagreement. Every number carries its name (“Bayern 87%”), the bookmakers’ split sits underneath, and from five points apart the row says so in words. A match without a model forecast gets an outlined bar: bookmakers only. One rule holds across the site: **filled is the models, outline is the bookmakers** (bars, grade bars, verdict labels, the marks on the track-record line). Above the rows, one sentence says how to read a bar and a box names the biggest argument of the matchday (afterwards: the biggest upset, or the matchday in numbers). The filters (all, live, finished, upcoming) only appear when there is something to filter.
- **An opened match.** “Play this match 100 times” as a sentence and 100 dots; the models against the bookmakers with fair odds; the three models behind the average; expected goals, the likeliest score and a small grid of score probabilities. After full time: the goals, then how far off the models and the bookmakers were, as two bars on one scale. While a match is live the page refreshes itself every minute, and again when you come back to it.
- **Table.** Overall, home and away tables after the selected matchday, with the last five results and the movement since the previous matchday. Caption rows say where each group of places leads (Champions League, Europa League, …) instead of a colour code, and the form letters are filled for a win, grey for a draw and outlined for a defeat, so nothing depends on red and green. This is not an official historical table: it is calculated from completed OpenLigaDB results and orders tied teams by points, goal difference, goals scored, then club name.
- **Follow a club.** The button in the top bar, a tap on a club in the table or the picker under Insights highlights it in the fixtures, the table and the charts. The choice is remembered on that device.
- **Deep dives.** Every post (from `analysis/posts.json`), newest first, with the result and whether the models or the bookmakers were closer.
- **Insights.** A points race for the season so far and when the goals go in, each with hover/keyboard tooltips and a table view.
- **Are the models any good?** One line with three marks: the bookmakers, the models and pure guessing (a third for each outcome), from `data/record.json`.
- **Phones.** The sections move to a tab bar at the bottom of the screen.
- **English and German.** The **EN / DE** switch in the top bar changes the whole app: labels, dates, number formats, plurals and score notation (2–1 or 2:1). The first visit follows the browser language, the choice is remembered on that device, and a link such as `?lang=de` opens the page in German. The analysis posts switch too, charts included.

### Look

One dark page, kept light: charcoal surfaces lifted in two small steps, thin lines, no shadows, no photos. The tokens are at the top of `styles.css`; `pages.css` and `analysis/analysis.css` use the same names. Red is the brand and “live”, nothing else. Blue, grey and orange are home win, draw and away win everywhere. Type runs on one scale (12, 14, 16, 20, 28 px, and the matchday headline), Barlow Condensed for headlines and DM Sans for everything else. The same rule runs through every page: filled is my models, outline or white pins are the bookmakers (forecast bars, grade bars, verdict labels). The charts in the posts use the page's colours too: the notebooks still draw them for a white page, so they read well in Colab and on GitHub, and `analysis/tools/dark_figures.py` recolours the published copies (see *Match analyses*).

Match information is displayed in the Europe/Berlin time zone.

Two more pages: **Learn** (`learn/` and `learn/part-two/`) is a short course in eleven drills, from what a probability means to how much to bet, each with something to play with and one question at the end, plus two games and the glossary (see *The Learn page*); **Track record** (`record/`) grades every published forecast against the bookmakers: the weekly forecasts matchday by matchday (`data/forecasts.json` against the latest price in `data/odds.json`, the same two numbers the home page grades with), then the deep dives, the season and backtest figures, the disagreement check and a paper-betting ledger for the deep dives.

### The explanatory layer

`glossary.js` holds every term in both languages (what it is, how to read it). `explain.js` turns any `<button type="button" class="term" data-term="rps">…</button>` into an explainer: next to the word on wide screens, a sheet from the bottom on phones, with a link to the entry on the Learn page. Keep the button text short (a word or two), because it does not break across lines.

On deep dives `explain.js` also runs the reading depth (Quick take, Full analysis, Nerd mode, remembered per device), the contents column, the reading-progress line and "Enlarge chart" on phones. The article marks blocks with `data-show`:

| Mark | Shown in |
|---|---|
| none | every depth |
| `data-show="quick"` | Quick take only (the three-point summary) |
| `data-show="full"` | Full analysis and Nerd mode |
| `data-show="nerd"` | Nerd mode only (code, model internals) |
| `data-show="full-only"` | Full analysis only (the "show the code" buttons) |

Blocks can be nested, and a link to a hidden block switches to a depth that shows it. Chart notes use `<details class="howto"><summary>How to read this chart</summary><p>…</p></details>` inside the `<figure>`.

### The Learn page

A short course in two halves, eleven drills in the order a forecast is made, judged and (maybe) bet on. Part one is `learn/`, part two `learn/part-two/`. The prose is in the two HTML pages (one copy per language); the playthings are drawn by `learn/learn.js` (odds calculator, "grade it yourself", glossary), `learn/play.js` (part one's playthings, the matchday game, the quick checks and progress, shared by both pages) and `learn/advanced.js` (part two), styled by `learn/learn.css`.

| Drill | Plaything | Where its numbers come from |
|---|---|---|
| 1 What 32% means | Replay machine: one forecast played once or 100 times | The Hamburg–Stuttgart forecast of matchday 6, fixed in `play.js` |
| 2 From goals to a forecast | Goal machine: two expected-goals sliders, a score grid and the forecast it gives | Plain Poisson, worked out in the browser; can load a match from `data/forecasts.json` |
| 3 What a chance is worth | Shot map: tap a pitch to shoot | A toy xG model (distance and angle only, tuned by hand, labelled as a toy) |
| 4 How a forecast is made | The three models and their average for any match of the matchday | `data/forecasts.json`, latest matchday |
| 5 From odds to chances | Odds calculator | Latest deep dive in `analysis/posts.json` |
| 6 How a forecast gets graded | Grade it yourself, with the reader's own forecast | Latest deep dive |
| 7 Why the bookmakers usually win | The long run: 40 bettors at odds of 1.90 | Simulated; the "in profit" share is the exact binomial figure |
| 8 Is the table lying? | League of clones: 18 identical clubs play a season; the real table's spread against theirs | `data/learn.json` (`table`) |
| 9 Ratings that learn | Elo calculator on the real current ratings, with the ladder | `data/learn.json` (`elo`), from `features.elo_ratings` |
| 10 Too sure, too shy | Boldness dial on every published out-of-sample forecast since 2019/20, with a calibration chart | `data/learn.json` (`matches`), graded as `evaluate.py` grades them |
| 11 How much to bet | Stake simulator: flat stakes, Kelly and its fractions when the belief about the edge is off | Simulated in the browser |

- **Quick checks.** Each drill ends with `<div class="check" data-check="<drill id>">`; the question, its three options, the right answer and the explanation are in `WORDS.…q` in `play.js`, in both languages. A right answer ticks the drill off. Which drills are done is kept in `localStorage` (`jans-matchday:learn`) and nowhere else, so both pages share it. The league in the header (Kreisliga to Champions) is just that count; part one ends with a half-time box, part two with full time.
- **Guess the forecast** (part one). The reader sets home/draw/away for each match of the latest matchday in `data/forecasts.json` and sees the models and the bookmakers. Guesses close at kick-off and are saved on the device (`jans-matchday:guesses`, the current and previous matchday only). Once a guessed match has kicked off, one OpenLigaDB request for the matchday fills the **scorecard**: the reader, the models and the bookmakers (their price when the forecast was published) graded on the result by RPS.
- **Penalty shoot-out** (part two). Ten random matches from `data/learn.json`; the reader forecasts blind, then sees the models (out of sample) and the bookmakers (closing average) and the result. The closest forecast scores the penalty; the shoot-out is decided on the average score, as the track record is.
- **Show the code.** Part two's drills each have a short Python snippet (`<details class="code-peek">`). [`learn/training_ground.ipynb`](learn/training_ground.ipynb) runs every drill in Google Colab from public data: it fetches the `source-data` and `backtest-results` branches, rebuilds `data/learn.json` with `learn_data.py` and reproduces the numbers on both pages (about 20 seconds, no GPU needed). Keep it without outputs.
- **To add a drill:** a `<section class="page-section" id="…">` with a `drill-kicker`, the two language blocks, a `<div class="calc toy" id="…">` and a check; then its id in `DRILLS` in `play.js`, a link in the page's `page-jump`, the count in every kicker ("Drill 8 of 11"), the columns of `.progress-meter` and the rank thresholds in `rank()` (`play.js`).

### Site data

| File | What | When to update |
|---|---|---|
| `analysis/posts.json` | Every deep dive: match id, published probabilities (models and market), card text in both languages; after the match `fullTime` with the score and the grades quoted in the post | With each post, and after full time |
| `data/odds.json` | Bookmaker home/draw/away odds per match, one block per matchday, for the bars on the home page | Automatically, once a day, by the odds recorder (see *Odds*) |
| `data/forecasts.json` | The models' forecast for every match of a matchday: the ensemble, the three models behind it, expected goals and a 6 × 6 grid of score probabilities | Automatically, once per matchday, by the **Forecast the matchday** workflow (see *Weekly forecasts*); never edited afterwards |
| `data/learn.json` | The real numbers behind part two of the Learn course: the table's spread by matchday, the current Elo ratings, and every graded backtest forecast (models and closing market) with its result. Written by `analysis/pipeline/learn_data.py` from the match table and the `xg/` backtest predictions | Automatically, with each published forecast (**Forecast the matchday**); by hand: `python analysis/pipeline/learn_data.py /tmp/matches.csv /tmp/results/xg data/learn.json --as-of YYYY-MM-DD` |
| `data/record.json` | Season and backtest figures for the track record and the line on the home page (`uniform` is the score of a forecast of one third each), written by `analysis/pipeline/evaluate.py` (see *Data and the backtest*) | After each matchday |

When you change `styles.css`, `app.js`, `i18n.js`, `glossary.js`, `explain.js`, `pages.css` or `analysis/analysis.css`, bump the `?v=` number where they are linked (`index.html`, `404.html`, `learn/`, `record/` and the analysis pages) and `SHELL_CACHE` in `sw.js`, so installed copies pick up the new files together. The same goes for `learn/learn.js`, `learn/play.js`, `learn/advanced.js` and `learn/learn.css`, which are linked from the two Learn pages only.

Fonts (DM Sans and Barlow Condensed, SIL Open Font License) are served from `assets/fonts`, not Google Fonts: no third-party request, nothing render-blocking, and they work offline. Club crests still come from the links OpenLigaDB provides, but `app.js` asks for 120 px Wikimedia thumbnails of the same crests (about 110 KB for all 18 clubs instead of about 1.2 MB of full-size originals) and falls back to OpenLigaDB's own link, then to the club's initials.

Sharing: every page carries Open Graph and Twitter tags with a 1200 × 630 preview image (`assets/share/home.jpg`, `analysis/<post>/share.jpg`), so links show a card on WhatsApp, X, LinkedIn and Slack. `sitemap.xml` lists the pages for Google Search Console. A `robots.txt` would have to sit at `jhvl88.github.io/robots.txt`, outside this repository, so there is none. `404.html` is the page GitHub Pages shows for a missing address.

## Languages

All interface text lives in `i18n.js`, in two dictionaries (`en` and `de`) that must hold the same keys. Static markup uses `data-i18n="key"` (text), `data-i18n-attrs="aria-label:key"` (attributes) or `data-i18n-html="key"` (text with `<strong>`); text built in `app.js` calls `t("key", { values })`. Plural strings are `{ one, other }` pairs that read `{count}`. Dates, numbers, ordinals and scores go through the helpers on `I18N` so they follow the chosen language. To add a language, add a dictionary, its locale in `LOCALES` and a button in the `.lang-switch` of each page.

Longer content that is not interface text, such as an analysis article or a thumbnail, is written once per language in the HTML and marked `data-lang-only="en"` or `data-lang-only="de"` (with `lang` set and `hidden` on the copy that is not the default). `i18n.js` shows the copy that matches the switch.

## Match analyses

Longer pieces live in `analysis/`, one folder per post, sharing `analysis/analysis.css`. They are listed under **Deep dives** on the home page. Each post folder holds the page, its charts in `figs/` and a Google Colab notebook that reproduces the analysis from public data. To add a post:

1. Create a new folder and copy an existing page into it, so the top bar, the tab bar, the language switch, the share tags, the contents column, the depth switch and the two article copies (`data-lang-only="en"` and `"de"`) come along. Write the article in both languages, with a three-point quick take, the depth marks and explainer terms (see *The explanatory layer*), and update the share tags (`og:` and `twitter:`) and the canonical link at the top. The reading times in the depth switch are filled in by `explain.js`; copy the numbers it shows into the HTML so nothing changes when the page loads.
2. Make the German charts: `python analysis/tools/translate_figures.py analysis/<new post>` writes `figs/de/` from the English SVGs, keeping every number and mark and changing only the words and number formats (1,47 · 25 %). It lists any English label it does not know yet; add a rule for it at the top of the script. The German article uses `figs/de/…`.
3. Recolour the charts for the dark page, English and German in one go: `python analysis/tools/dark_figures.py analysis/<new post>/figs`. Run it last, after the translation. It maps the notebook's colours onto the site's and stops if it meets a colour it does not know, so nothing is half converted; add that colour to the table at the top of the script. Running it twice does no harm (`--check` only reports).
4. Give the charts their size, so the page does not jump while they load: `python analysis/tools/size_figures.py analysis/<new post>`.
5. Add the post to `analysis/posts.json`, newest first: its OpenLigaDB `matchId` (the fixture and the hub on the home page then link to it), the models' probabilities (home, draw, away), the market, and the card text in both languages. For the market, take a snapshot when the post is ready (Actions › Record odds › Run workflow, label `md<N> post`), then run `python analysis/pipeline/odds_at.py --data-dir <matchday-data>/odds --home <club> --away <club>`. It prints the `forecast` fields to paste:
   - `market`: the consensus probabilities across the sportsbooks;
   - `marketOdds`: the best price at Tipico or Winamax, a price a reader could actually take, which the paper bets use;
   - `marketQuoted` and `marketSnapshot`: when the price was recorded. The home page, the track record and the Learn calculators all read from here. Refresh `data/record.json` as described under *Data and the backtest*.
6. Draw its share image: `python analysis/tools/make_share_cards.py` (needs `pip install playwright`).
7. Add `analysis.pageTitle…` and `analysis.meta…` to both dictionaries in `i18n.js` for the post's `<title>` and meta description, and the page to `sitemap.xml`.
8. After full time, add `fullTime` to the post in `posts.json` (the score and the grades quoted in the article); the track record uses them, and falls back to OpenLigaDB's score until then. The full-time charts come from `python analysis/tools/fulltime.py` (its header has the arguments); run `dark_figures.py` on the post's `figs` again afterwards, it converts the new charts and leaves the others alone.

## Data and the backtest

The models and their data live in `analysis/pipeline/`, one copy for every post, the backtest and the Track record page.

| Step | Where | What it does |
|---|---|---|
| Source files | `fetch_football_data.py`, workflow **Fetch source data** | Downloads the season files from [football-data.co.uk](https://www.football-data.co.uk/) exactly as served, with a SHA-256 checksum each, and stores them on the `source-data` branch: the 1. and 2. Bundesliga since 2000/01, and the top two tiers of England, Spain, Italy and France since 2005/06 (`--leagues all`; the script alone fetches Germany). Runs twice a week, on demand, and when the fetcher changes. That branch's history records which exact files every result used. |
| xG | `fetch_understat.py`, `understat.py`, workflow **Fetch Understat xG** | Understat's match xG for every 1. Bundesliga match since 2014/15, fetched weekly into the private `matchday-data` repo (Understat publishes no licence, so only checksums are public). Where Understat has no xG for a played match, the match table takes football-data.co.uk's own xG (`HxG`/`AxG`, in its files from 2026/27) and puts it on Understat's scale; `xg_src` records the source of each match. See [When Understat is offline](#when-understat-is-offline). |
| Match table | `build_matches.py` | One table from those files, every row pointing back to its file and line, with all odds sets; `--understat <dir>` adds xG (`--understat-only` leaves out the football-data fill). `--league ENG` (or `ESP`, `ITA`, `FRA`) builds the same table for another league, with `div` as the tier (D1 top flight, D2 second tier), so the models run on it unchanged. |
| Posts' data check | `verify_sources.py` | Compares the 2026/27 rows embedded in each post's notebook, and the old GitHub mirror, with the source files. |
| Models | `bl_models.py`, `bayes_model.py`, `features.py`, `backtest_utils.py` | Dixon–Coles, the Bayesian shots-to-goals model and XGBoost. Since October 2026 the published versions learn from xG (`--xg`), after a [pre-registered test](analysis/backtest/xg/README.md); without the switch they are the original models. Since November 2026 the published XGBoost is trained on the top flights of all five leagues (`forecast.py --pool`), after the [four-league test](analysis/backtest/leagues/README.md). |
| Backtest | `backtest.py`, workflows **Backtest (xG variants)** and **Backtest** | Walk-forward from 2019/20: Dixon–Coles refit weekly, XGBoost per season, the Bayesian model monthly (one parallel job per season). Predictions land on the `backtest-results` branch: `xg/` for the published models, `latest/` for the original ones. |
| Grades | `evaluate.py`, `make_figures.py` | Grades against one benchmark, the market-average closing price, and writes `data/record.json` (never by hand). |
| Other leagues | `leagues.py`, `pooled_xgb.py`, `evaluate_leagues.py`, `make_league_figures.py`, workflow **Backtest (leagues)** | The [pre-registered four-league test](analysis/backtest/leagues/README.md): the original models on England, Spain, Italy and France as well, and XGBoost trained on all five leagues at once. The site still forecasts the Bundesliga only; the other leagues are the test bed for methods. Predictions land in `leagues/` on `backtest-results`. |
| Closing line | `evaluate_clv.py`, `make_clv_figures.py` | The [pre-registered closing-line test](analysis/backtest/clv/README.md): do prices move toward the models between the early snapshot and kick-off, and what would the paper-betting rule have earned at the early price? Over 12,958 matches in five leagues: no, and it would have lost. No model is refitted; it grades the stored forecasts against the two prices in the source files. |

**The benchmark.** "The market" means football-data.co.uk's market-average closing odds (`AvgC…`), with the margin removed proportionally: the best public estimate of the true probabilities, recorded for every match since 2019/20. Pinnacle's prices are kept in the table but never used, because football-data.co.uk flags them as stale since 23 July 2025. A post still quotes the odds that were on offer when it was published; that is a different question (could you have got that price?) from the backtest's (who forecasts better?).

To refresh the Track record after new matches: run the **Backtest (xG variants)** workflow (Actions tab), then

```bash
git fetch origin source-data backtest-results
git worktree add /tmp/source origin/source-data
git worktree add /tmp/results origin/backtest-results
git clone https://github.com/JHvL88/matchday-data /tmp/matchday-data      # private: needs your GitHub login
python analysis/pipeline/build_matches.py /tmp/source /tmp/matches.csv --understat /tmp/matchday-data/understat
python analysis/pipeline/evaluate.py /tmp/matches.csv /tmp/results/xg analysis/backtest/xg/results_vs_market.json --no-bridge --record data/record.json --as-of YYYY-MM-DD
```

A post's forecast uses the same switches: build the match table with `--understat` and fit the models with xG (`DixonColes(xi=0.0019, xg_weight=0.25)`, `build_features(..., use_xg=True)` with `FEATURES_XG`, `bayes_model.USE_XG = True`), with XGBoost trained on all five leagues. `forecast.py` does all of it:

```bash
for league in ENG ESP ITA FRA; do
  python analysis/pipeline/build_matches.py /tmp/source /tmp/tables/$league.csv --league $league
done
python analysis/pipeline/forecast.py /tmp/matches.csv forecast.json --freeze 2026-11-20 \
    --fixture 2026-11-21 "Bayern Munich" Leverkusen --xg --pool /tmp/tables
```

Without `--pool`, XGBoost learns from the Bundesliga alone, as the forecasts published before 16 November 2026 did.

### When Understat is offline

Understat is one small site. It went offline on 2 November 2026 and was still showing "We will come back soon" two weeks later. Two things keep the pipeline going without it:

- **The fetch stands down.** If Understat doesn't answer, or answers with its holding page, **Fetch Understat xG** ends green with a warning and leaves the stored copy alone. It still fails when something needs a look: Understat answers but the page can't be read, a season is missing, or a season comes back with fewer played matches than the stored copy (a restore from an old backup must not overwrite good data).
- **football-data.co.uk fills the gap.** Its season files carry xG since 2026/27 (the provider isn't named). `understat.add_xg` uses it for every played 1. Bundesliga match Understat lacks. The two xG models differ, so the numbers are first put on Understat's scale with a straight line fitted on the matches that have both. On the 63 matches of 2026/27 both sources cover, they agree closely (correlation 0.93 per team and match) and football-data runs about 7% lower: Understat ≈ 0.07 + 1.04 × football-data. Building the match table prints how many matches were filled and the line it used.

Nothing in the pre-registered xG test changes: every match in it has Understat's own xG. When Understat returns, its numbers replace the filled ones on the next build. football-data.co.uk updates on Sunday and Wednesday nights, so its xG arrives a day or two after a match; Understat's used to arrive within the hour.

### Weekly forecasts

The **Forecast the matchday** workflow forecasts every match of the coming matchday, not only the one with a deep dive, and writes `data/forecasts.json`. The home page shows the forecast on each fixture, next to the bookmakers, and grades it after full time. In the same run it refreshes `data/learn.json` for the Learn course (with a warning, never a failure, if that step goes wrong).

- **Same models, same data.** `site_forecasts.py` reads the fixtures from OpenLigaDB, translates the club names (`teams.py`) and calls `forecast.py --xg --pool`: the three published models and their plain average, fitted on the match table built from the `source-data` branch and the private xG files. A forecast here is made exactly the way the backtest grades them.
- **Published once.** A matchday is due from 72 hours before its first kick-off: on a normal weekend that is Thursday morning, after **Fetch source data** has brought in the last results. It is forecast once and never refitted; a matchday that has kicked off is refused. The file records when it was published, the freeze date, the last match the models saw, the code commit and the checksum of the match table. `--force` (a tick box when the workflow is started by hand) replaces a forecast before kick-off and says so in the file.
- **Waiting for results.** If the source files still miss a match OpenLigaDB has as played, the run waits for the next morning. Less than 30 hours before kick-off it goes ahead and notes which matches were missing.
- **The market, for the record.** The bookmakers' average odds on the day of publication are stored with each forecast. The home page compares with the latest price in `data/odds.json`.
- **By hand.** Actions › Forecast the matchday › Run workflow (optionally with a matchday number), or locally:

```bash
python analysis/pipeline/site_forecasts.py /tmp/matches.csv --pool /tmp/tables --season 2026 --matchday 11
```

- **Setup.** It needs the `DATA_REPO_TOKEN` secret the odds recorder already uses (for the xG files). A run takes about 15 minutes; most mornings it only checks the fixture list and stops. `SITE_BOT=off` stops the automatic commit here too.
- **Graded in public.** The Track record lists every weekly forecast, matchday by matchday, and grades it after full time against the bookmakers' average odds as last recorded before kick-off (the price stored with the forecast if `data/odds.json` has none). The paper bets stay with the deep dives: their rule was fixed for those, and extending it to the weekly forecasts would be a new rule.

### Odds

The **Record odds** workflow snapshots Bundesliga odds from [The Odds API](https://the-odds-api.com/): every bookmaker in its EU feed (Pinnacle, Betfair Exchange, Tipico, Winamax DE and about 20 more), match odds and total goals.

| When | Why |
|---|---|
| Once a day from 07:00 UTC, while a match is less than 8 days away | The week's prices, and the home page bars |
| 75–30 minutes before each kick-off time | The price after team news |
| The last 30 minutes before kick-off | Our own closing line |
| On demand: Actions › Record odds › Run workflow, with a label such as `md7 post` | The price at the moment a post goes out |

It runs every 30 minutes; checking the fixture list is free, so most runs cost nothing. A snapshot costs 2 credits, about 170 a month against the free plan's 500. Below 40 credits left it only takes closing and manual snapshots.

- **Where the data goes.** Raw snapshots go to the private repository `JHvL88/matchday-data` (`odds/snapshots/…json.gz`, log in `odds/state.json`), because The Odds API's terms allow storing and displaying their data but not publishing raw files. The public site gets only `data/odds.json`, the average price per match, refreshed after the daily snapshot (`site_odds.py`).
- **Closing odds and CLV.** After each football-data.co.uk fetch, `grade_posts.py` adds every played forecast's closing odds (market average at kick-off) to `analysis/posts.json`, and the Track record shows each paper bet's closing-line value: odds taken × closing probability (margin removed) − 1.
- **Setup, once.**
  1. Create a free key at the-odds-api.com.
  2. Create the private repository `matchday-data`.
  3. Create a fine-grained token with *Contents: read and write* on that repository only.
  4. Add both as Actions secrets in this repository: `ODDS_API_KEY` and `DATA_REPO_TOKEN`.
  Until then the workflow logs a notice and stops.
- **Not covered.** Swiss readers' only legal option, Swisslos Sporttip, isn't in any odds feed.
- **Switch off the bot.** Set the repository variable `SITE_BOT` to `off` to stop the automatic commits of `data/odds.json` and `analysis/posts.json`.
- **Tests.** `python -m pytest analysis/pipeline/tests` (no network needed).

The Colab notebook [`analysis/backtest/backtest.ipynb`](analysis/backtest/backtest.ipynb) does the same from scratch, downloading from football-data.co.uk and checking every file against the published run. What changed in October 2026 and why is in [`analysis/backtest/README.md`](analysis/backtest/README.md).

Posts so far:

- [Bayern vs Leipzig, matchday 6 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md6-bayern-leipzig/): the first forecast from the xG versions of the models, and a backtest of where they are too timid (big favourites, goal-heavy games). This post runs on the shared pipeline: `post_model.py` fits the models through `analysis/pipeline/forecast.py` and freezes `forecast.json`, `post_charts.py` draws every chart in English and German from the same numbers (so no `translate_figures.py` step) and writes `numbers.json`, and `post_fill.py` fills the article's `[[placeholders]]` from it, so no figure is typed by hand. `post_market.py` turns the recorded odds into `market.json`. [Notebook](analysis/2026-27-md6-bayern-leipzig/bayern_leipzig_md6.ipynb).
- [Hamburg vs Stuttgart, matchday 6 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md6-hamburg-stuttgart/): the same three models with matchday 5 added, shot-based expected points, and a backtest of who was right when the models and the bookmakers disagreed. The notebook reads the fixture from `match.json`, so it can forecast any match. [Notebook](analysis/2026-27-md6-hamburg-stuttgart/hamburg_stuttgart_md6.ipynb).
- [Augsburg vs Bayern, matchday 5 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md5-augsburg-bayern/): pre-match forecast from Dixon–Coles, a Bayesian shots-to-goals model (NumPyro) and XGBoost, backtested against bookmaker odds. [Notebook](analysis/2026-27-md5-augsburg-bayern/augsburg_bayern_md5.ipynb).

## Install on iPhone or iPad

Open [Jan’s Matchday](https://jhvl88.github.io/matchday/) in Safari, tap **Share**, then tap **Add to Home Screen**. The app opens in its own window and caches the app shell and latest successfully loaded match data so it can reopen when offline. Live results still need an internet connection.
