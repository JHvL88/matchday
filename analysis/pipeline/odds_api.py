"""Minimal client for The Odds API (https://the-odds-api.com), standard library only.

Costs (their docs): /events is free; /odds costs markets x regions credits per call, however many
matches come back. The quota headers of every response are returned with the data.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.the-odds-api.com/v4"
SPORT = "soccer_germany_bundesliga"


class OddsApiError(RuntimeError):
    pass


def _get(path, key, **params):
    query = urllib.parse.urlencode({"apiKey": key, **params})
    req = urllib.request.Request(f"{BASE}{path}?{query}", headers={"User-Agent": "jans-matchday-odds/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
            quota = {k: r.headers.get(f"x-requests-{k}") for k in ("remaining", "used", "last")}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise OddsApiError(f"{e.code} from {path}: {detail}") from None
    quota = {k: (float(v) if v not in (None, "") else None) for k, v in quota.items()}
    return body, quota


def events(key, sport=SPORT):
    """Upcoming and live matches with kick-off times. Free."""
    return _get(f"/sports/{sport}/events", key, dateFormat="iso")


def odds(key, sport=SPORT, regions="eu", markets="h2h,totals"):
    """Every bookmaker's current prices for every upcoming match. Costs markets x regions credits."""
    return _get(f"/sports/{sport}/odds", key, regions=regions, markets=markets, oddsFormat="decimal", dateFormat="iso")
