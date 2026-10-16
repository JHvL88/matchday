# Jan’s Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves Bundesliga fixtures and results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

What’s on the home page:

- **Matchday hub.** Step through matchdays with the arrows or the 1–34 strip (arrow keys work too). The choice is kept in the URL (`?md=5`), so a matchday can be linked. Before a matchday starts, the hub shows the next kick-off, the top clash and the bottom clash (by current table position); once games are played it summarises goals, home wins/draws/away wins, the biggest win and the leader.
- **Matches.** Filters with counts (all, live, finished, upcoming); each match expands to show the venue, attendance, half-time score and a goal timeline with the running score. While a match is live the page refreshes itself every minute, and again when you come back to it. A match with a deep dive gets a link under it with the published forecast (from `analysis/posts.json`).
- **Table.** Overall, home and away tables after the selected matchday, with the last five results, the movement since the previous matchday and European/relegation zones. This is not an official historical table: it is calculated from completed OpenLigaDB results and orders tied teams by points, goal difference, goals scored, then club name.
- **Follow a club.** Tap a club in the table (or pick one under Insights) to highlight it in the fixtures, the table and the charts. The choice is remembered on that device.
- **Insights.** A points race for the season so far and when the goals go in, each with hover/keyboard tooltips and a table view.
- **English and German.** The **EN / DE** switch in the top bar changes the whole app: labels, dates, number formats, plurals and score notation (2–1 or 2:1). The first visit follows the browser language, the choice is remembered on that device, and a link such as `?lang=de` opens the page in German. The analysis posts switch too, charts included.

Match information is displayed in the Europe/Berlin time zone.

When you change `styles.css`, `app.js`, `i18n.js` or `analysis/analysis.css`, bump the `?v=` number where they are linked (`index.html`, `404.html` and the analysis pages) and `SHELL_CACHE` in `sw.js`, so installed copies pick up the new files together.

Fonts (DM Sans and Barlow Condensed, SIL Open Font License) are served from `assets/fonts`, not Google Fonts: no third-party request, nothing render-blocking, and they work offline. Club crests still come from the links OpenLigaDB provides, but `app.js` asks for 120 px Wikimedia thumbnails of the same crests (about 110 KB for all 18 clubs instead of about 1.2 MB of full-size originals) and falls back to OpenLigaDB's own link, then to the club's initials.

Sharing: every page carries Open Graph and Twitter tags with a 1200 × 630 preview image (`assets/share/home.jpg`, `analysis/<post>/share.jpg`), so links show a card on WhatsApp, X, LinkedIn and Slack. `sitemap.xml` lists the pages for Google Search Console. A `robots.txt` would have to sit at `jhvl88.github.io/robots.txt`, outside this repository, so there is none. `404.html` is the page GitHub Pages shows for a missing address.

## Languages

All interface text lives in `i18n.js`, in two dictionaries (`en` and `de`) that must hold the same keys. Static markup uses `data-i18n="key"` (text), `data-i18n-attrs="aria-label:key"` (attributes) or `data-i18n-html="key"` (text with `<strong>`); text built in `app.js` calls `t("key", { values })`. Plural strings are `{ one, other }` pairs that read `{count}`. Dates, numbers, ordinals and scores go through the helpers on `I18N` so they follow the chosen language. To add a language, add a dictionary, its locale in `LOCALES` and a button in the `.lang-switch` of each page.

Longer content that is not interface text, such as an analysis article or a thumbnail, is written once per language in the HTML and marked `data-lang-only="en"` or `data-lang-only="de"` (with `lang` set and `hidden` on the copy that is not the default). `i18n.js` shows the copy that matches the switch.

## Match analyses

Longer pieces live in `analysis/`, one folder per post, sharing `analysis/analysis.css`. They are listed in the **Analysis** section of the home page (also reachable from the top navigation). Each post folder holds the page, its charts in `figs/` and a Google Colab notebook that reproduces the analysis from public data. To add a post:

1. Create a new folder and copy an existing page into it, so the top bar, the language switch, the share tags and the two article copies (`data-lang-only="en"` and `"de"`) come along. Write the article in both languages and update the share tags (`og:` and `twitter:`) and the canonical link at the top.
2. Make the German charts: `python analysis/tools/translate_figures.py analysis/<new post>` writes `figs/de/` from the English SVGs, keeping every number and mark and changing only the words and number formats (1,47 · 25 %). It lists any English label it does not know yet; add a rule for it at the top of the script. The German article uses `figs/de/…`.
3. Give the charts their size, so the page does not jump while they load: `python analysis/tools/size_figures.py analysis/<new post>`.
4. Add the post to `analysis/posts.json`: its OpenLigaDB `matchId` (the fixture on the home page then links to it), the published probabilities (home, draw, away) for the models and the market, and the card text in both languages.
5. Draw its share image: `python analysis/tools/make_share_cards.py` (needs `pip install playwright`).
6. Add a card to the Analysis section in `index.html` (one thumbnail per language) and its keys in both dictionaries in `i18n.js`: `analysis.tag…`, `analysis.title…`, `analysis.desc…`, plus `analysis.pageTitle…` and `analysis.meta…` for the post's `<title>` and meta description. Add the page to `sitemap.xml`.

Posts so far:

- [Hamburg vs Stuttgart, matchday 6 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md6-hamburg-stuttgart/): the same three models with matchday 5 added, shot-based expected points, and a backtest of who was right when the models and the bookmakers disagreed. The notebook reads the fixture from `match.json`, so it can forecast any match. [Notebook](analysis/2026-27-md6-hamburg-stuttgart/hamburg_stuttgart_md6.ipynb).
- [Augsburg vs Bayern, matchday 5 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md5-augsburg-bayern/): pre-match forecast from Dixon–Coles, a Bayesian shots-to-goals model (NumPyro) and XGBoost, backtested against bookmaker odds. [Notebook](analysis/2026-27-md5-augsburg-bayern/augsburg_bayern_md5.ipynb).

## Install on iPhone or iPad

Open [Jan’s Matchday](https://jhvl88.github.io/matchday/) in Safari, tap **Share**, then tap **Add to Home Screen**. The app opens in its own window and caches the app shell and latest successfully loaded match data so it can reopen when offline. Live results still need an internet connection.

## Background photo credits

- “Hongkou Football Stadium at night” by Windmemories, used under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). [Source](https://commons.wikimedia.org/wiki/File:20240107_Night_view_of_Hongkou_Football_Stadium.jpg).
- “Adidas soccer ball on a grass pitch” by Peter Glaser, dedicated to the public domain under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). [Source](https://commons.wikimedia.org/wiki/File:Adidas_soccer_ball_on_a_grass_pitch_(Unsplash).jpg).
