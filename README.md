# Matchday

A small, responsive Bundesliga results app built with plain HTML, CSS, and JavaScript. It retrieves the current matchday and match results from [OpenLigaDB](https://www.openligadb.de/), a free public API that does not require an API key.

## Run locally

Open `index.html` in a browser. If your browser restricts requests from local files, start a static server in this folder instead, for example:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

The app offers matchday navigation, live/finished/upcoming filters, manual refresh, and an OpenLigaDB data attribution link. Match information is displayed in the Europe/Berlin time zone.
