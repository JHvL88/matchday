# Jan’s Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves the current matchday and match results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

The app offers matchday navigation, live/finished/upcoming filters, manual refresh, and an OpenLigaDB data attribution link. Match information is displayed in the Europe/Berlin time zone.

## Background photo credits

- “Hongkou Football Stadium at night” by Windmemories, used under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). [Source](https://commons.wikimedia.org/wiki/File:20240107_Night_view_of_Hongkou_Football_Stadium.jpg).
- “Adidas soccer ball on a grass pitch” by Peter Glaser, dedicated to the public domain under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). [Source](https://commons.wikimedia.org/wiki/File:Adidas_soccer_ball_on_a_grass_pitch_(Unsplash).jpg).
