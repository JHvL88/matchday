# Jan’s Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves Bundesliga fixtures and results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

The app offers matchday navigation, live/finished/upcoming filters, expandable match details with available goal events and half-time scores, and a reconstructed league table through the selected matchday. This is not an official historical table: it is calculated from completed OpenLigaDB results and orders tied teams by points, goal difference, goals scored, then club name. Match information is displayed in the Europe/Berlin time zone.

## Match analyses

Longer pieces live in `analysis/`, one folder per post, sharing `analysis/analysis.css`. Each post folder holds the page, its charts in `figs/` and a Google Colab notebook that reproduces the analysis from public data:

- [Augsburg vs Bayern, matchday 5 2026/27](https://jhvl88.github.io/matchday/analysis/2026-27-md5-augsburg-bayern/): pre-match forecast from Dixon–Coles, a Bayesian shots-to-goals model (NumPyro) and XGBoost, backtested against bookmaker odds. [Notebook](analysis/2026-27-md5-augsburg-bayern/augsburg_bayern_md5.ipynb).

## Install on iPhone or iPad

Open [Jan’s Matchday](https://jhvl88.github.io/matchday/) in Safari, tap **Share**, then tap **Add to Home Screen**. The app opens in its own window and caches the app shell and latest successfully loaded match data so it can reopen when offline. Live results still need an internet connection.

## Background photo credits

- “Hongkou Football Stadium at night” by Windmemories, used under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). [Source](https://commons.wikimedia.org/wiki/File:20240107_Night_view_of_Hongkou_Football_Stadium.jpg).
- “Adidas soccer ball on a grass pitch” by Peter Glaser, dedicated to the public domain under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). [Source](https://commons.wikimedia.org/wiki/File:Adidas_soccer_ball_on_a_grass_pitch_(Unsplash).jpg).
