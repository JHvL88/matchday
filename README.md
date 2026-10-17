# Jan’s Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves Bundesliga fixtures and results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

What’s on the home page:

- **This weekend.** The matchday, a countdown to the next kick-off (or what is live), and the latest deep dive with its forecast next to the bookmakers’ (always the newest post, whichever matchday is on screen: its full-time review counts from two hours after kick-off, or set `updated` in `posts.json` to an exact time). Step through matchdays with the arrows or the 1–34 strip (arrow keys work too). The choice is kept in the URL (`?md=5`), so a matchday can be linked. Before a matchday starts, the tiles show the top and bottom clash, the biggest favourite and the closest call; once games are played they show goals, the biggest upset or the results, the biggest win and the leader.
- **Matches.** Filters with counts (all, live, finished, upcoming). Every match with bookmaker odds gets a thin home/draw/away bar (blue, grey, orange). Each match expands to show the forecast against the market with fair odds, then the venue, attendance, half-time score and a goal timeline; after full time the forecast is graded. While a match is live the page refreshes itself every minute, and again when you come back to it.
- **Table.** Overall, home and away tables after the selected matchday, with the last five results, the movement since the previous matchday and European/relegation zones. This is not an official historical table: it is calculated from completed OpenLigaDB results and orders tied teams by points, goal difference, goals scored, then club name.
- **Follow a club.** The button in the top bar, a tap on a club in the table or the picker under Insights highlights it in the fixtures, the table and the charts. The choice is remembered on that device.
- **Insights.** A points race for the season so far and when the goals go in, each with hover/keyboard tooltips and a table view.
- **Deep dives and the track record.** Cards for every post (from `analysis/posts.json`) and a teaser of the scoreboard.
- **Phones.** The sections move to a tab bar at the bottom of the screen.
- **English and German.** The **EN / DE** switch in the top bar changes the whole app: labels, dates, number formats, plurals and score notation (2–1 or 2:1). The first visit follows the browser language, the choice is remembered on that device, and a link such as `?lang=de` opens the page in German. The analysis posts switch too, charts included.

Match information is displayed in the Europe/Berlin time zone.

Two more pages: **Learn** (`learn/`) explains probabilities, odds and grading, with an odds calculator, a "grade it yourself" box and the glossary; **Track record** (`record/`) grades every published forecast against the bookmakers, with the season and backtest figures, the disagreement check and a paper-betting ledger.

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

### Site data

| File | What | When to update |
|---|---|---|
| `analysis/posts.json` | Every deep dive: match id, published probabilities (models and market), card text in both languages; after the match `fullTime` with the score and the grades quoted in the post | With each post, and after full time |
| `data/odds.json` | Bookmaker home/draw/away odds per match, one block per matchday, for the bars on the home page | Automatically, once a day, by the odds recorder (see *Odds*) |
| `data/record.json` | Season and backtest figures for the track record, written by `analysis/pipeline/evaluate.py` (see *Data and the backtest*) | After each matchday |

When you change `styles.css`, `app.js`, `i18n.js`, `glossary.js`, `explain.js`, `pages.css` or `analysis/analysis.css`, bump the `?v=` number where they are linked (`index.html`, `404.html`, `learn/`, `record/` and the analysis pages) and `SHELL_CACHE` in `sw.js`, so installed copies pick up the new files together.

Fonts (DM Sans and Barlow Condensed, SIL Open Font License) are served from `assets/fonts`, not Google Fonts: no third-party request, nothing render-blocking, and they work offline. Club crests still come from the links OpenLigaDB provides, but `app.js` asks for 120 px Wikimedia thumbnails of the same crests (about 110 KB for all 18 clubs instead of about 1.2 MB of full-size originals) and falls back to OpenLigaDB's own link, then to the club's initials.

Sharing: every page carries Open Graph and Twitter tags with a 1200 × 630 preview image (`assets/share/home.jpg`, `analysis/<post>/share.jpg`), so links show a card on WhatsApp, X, LinkedIn and Slack. `sitemap.xml` lists the pages for Google Search Console. A `robots.txt` would have to sit at `jhvl88.github.io/robots.txt`, outside this repository, so there is none. `404.html` is the page GitHub Pages shows for a missing address.

## Languages

All interface text lives in `i18n.js`, in two dictionaries (`en` and `de`) that must hold the same keys. Static markup uses `data-i18n="key"` (text), `data-i18n-attrs="aria-label:key"` (attributes) or `data-i18n-html="key"` (text with `<strong>`); text built in `app.js` calls `t("key", { values })`. Plural strings are `{ one, other }` pairs that read `{count}`. Dates, numbers, ordinals and scores go through the helpers on `I18N` so they follow the chosen language. To add a language, add a dictionary, its locale in `LOCALES` and a button in the `.lang-switch` of each page.

Longer content that is not interface text, such as an analysis article or a thumbnail, is written once per language in the HTML and marked `data-lang-only="en"` or `data-lang-only="de"` (with `lang` set and `hidden` on the copy that is not the default). `i18n.js` shows the copy that matches the switch.

## Match analyses

Longer pieces live in `analysis/`, one folder per post, sharing `analysis/analysis.css`. They are listed under **Deep dives** on the home page. Each post folder holds the page, its charts in `figs/` and a Google Colab notebook that reproduces the analysis from public data. To add a post:

1. Create a new folder and copy an existing page into it, so the top bar, the tab bar, the language switch, the share tags, the contents column, the depth switch and the two article copies (`data-lang-only="en"` and `"de"`) come along. Write the article in both languages, with a three-point quick take, the depth marks and explainer terms (see *The explanatory layer*), and update the share tags (`og:` and `twitter:`) and the canonical link at the top. The reading times in the depth switch are filled in by `explain.js`; copy the numbers it shows into the HTML so nothing changes when the page loads.
2. Make the German charts: `python analysis/tools/translate_figures.py analysis/<new post>` writes `figs/de/` from the English SVGs, keeping every number and mark and changing only the words and number formats (1,47 · 25 %). It lists any English label it does not know yet; add a rule for it at the top of the script. The German article uses `figs/de/…`.
3. Give the charts their size, so the page does not jump while they load: `python analysis/tools/size_figures.py analysis/<new post>`.
4. Add the post to `analysis/posts.json`, newest first: its OpenLigaDB `matchId` (the fixture and the hub on the home page then link to it), the models' probabilities (home, draw, away), the market, and the card text in both languages. For the market, take a snapshot when the post is ready (Actions › Record odds › Run workflow, label `md<N> post`), then run `python analysis/pipeline/odds_at.py --data-dir <matchday-data>/odds --home <club> --away <club>`. It prints the `forecast` fields to paste:
   - `market`: the consensus probabilities across the sportsbooks;
   - `marketOdds`: the best price at Tipico or Winamax, a price a reader could actually take, which the paper bets use;
   - `marketQuoted` and `marketSnapshot`: when the price was recorded. The home page card, the track record and the Learn calculators all read from here. Refresh `data/record.json` as described under *Data and the backtest*.
5. Draw its share image: `python analysis/tools/make_share_cards.py` (needs `pip install playwright`).
6. Add `analysis.pageTitle…` and `analysis.meta…` to both dictionaries in `i18n.js` for the post's `<title>` and meta description, and the page to `sitemap.xml`.
7. After full time, add `fullTime` to the post in `posts.json` (the score and the grades quoted in the article); the track record uses them, and falls back to OpenLigaDB's score until then.

## Data and the backtest

The models and their data live in `analysis/pipeline/`, one copy for every post, the backtest and the Track record page.

| Step | Where | What it does |
|---|---|---|
| Source files | `fetch_football_data.py`, workflow **Fetch source data** | Downloads the 1. and 2. Bundesliga season files from [football-data.co.uk](https://www.football-data.co.uk/) exactly as served, with a SHA-256 checksum each, and stores them on the `source-data` branch. Runs twice a week, on demand, and when the fetcher changes. That branch's history records which exact files every result used. |
| xG | `fetch_understat.py`, `understat.py`, workflow **Fetch Understat xG** | Understat's match xG for every 1. Bundesliga match since 2014/15, fetched weekly into the private `matchday-data` repo (Understat publishes no licence, so only checksums are public). |
| Match table | `build_matches.py` | One table from those files, every row pointing back to its file and line, with all odds sets; `--understat <dir>` adds xG. |
| Posts' data check | `verify_sources.py` | Compares the 2026/27 rows embedded in each post's notebook, and the old GitHub mirror, with the source files. |
| Models | `bl_models.py`, `bayes_model.py`, `features.py`, `backtest_utils.py` | Dixon–Coles, the Bayesian shots-to-goals model and XGBoost. Since October 2026 the published versions learn from xG (`--xg`), after a [pre-registered test](analysis/backtest/xg/README.md); without the switch they are the original models. |
| Backtest | `backtest.py`, workflows **Backtest (xG variants)** and **Backtest** | Walk-forward from 2019/20: Dixon–Coles refit weekly, XGBoost per season, the Bayesian model monthly (one parallel job per season). Predictions land on the `backtest-results` branch: `xg/` for the published models, `latest/` for the original ones. |
| Grades | `evaluate.py`, `make_figures.py` | Grades against one benchmark, the market-average closing price, and writes `data/record.json` (never by hand). |

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

A post's forecast uses the same switches: build the match table with `--understat` and fit the models with xG (`DixonColes(xi=0.0019, xg_weight=0.25)`, `build_features(..., use_xg=True)` with `FEATURES_XG`, `bayes_model.USE_XG = True`).

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

## Background photo credits

- “Hongkou Football Stadium at night” by Windmemories, used under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). [Source](https://commons.wikimedia.org/wiki/File:20240107_Night_view_of_Hongkou_Football_Stadium.jpg).
- “Adidas soccer ball on a grass pitch” by Peter Glaser, dedicated to the public domain under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). [Source](https://commons.wikimedia.org/wiki/File:Adidas_soccer_ball_on_a_grass_pitch_(Unsplash).jpg).
