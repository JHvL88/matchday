"""Download Understat's Bundesliga match list (with xG) for every season since 2014/15.

One request per season: https://understat.com/getLeagueData/Bundesliga/<season start year>, the
JSON the league page itself loads. If that endpoint ever disappears, the script falls back to the
older page layout (the `datesData` blob in the league page's HTML).

Saved byte-for-byte with a SHA-256 manifest. Understat publishes no licence, so the raw files go to
the private data repository, never the public one; only derived numbers are published.

    python analysis/pipeline/fetch_understat.py --out understat-out
"""
import argparse
import codecs
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://understat.com"
LEAGUE = "Bundesliga"
FIRST = 2014
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def get(url, headers, retries=3, pause=3.0):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **headers})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                raise
            if attempt < retries - 1:
                time.sleep(pause * 2 ** attempt)
    raise last


def season_data(season):
    """(raw bytes, how) for one season; `how` says which route worked."""
    referer = f"{BASE}/league/{LEAGUE}/{season}"
    try:
        body = get(f"{BASE}/getLeagueData/{LEAGUE}/{season}", {"X-Requested-With": "XMLHttpRequest", "Referer": referer})
        data = json.loads(body)
        if data.get("dates"):
            return body, "getLeagueData"
    except Exception as e:  # noqa: BLE001 - try the old layout next
        print(f"  getLeagueData {season}: {e}", flush=True)
    html = get(referer, {}).decode("utf-8", errors="replace")
    m = re.search(r"datesData\s*=\s*JSON\.parse\('(?P<j>.*?)'\)", html)
    if not m:
        raise RuntimeError(f"no match data found for {season}")
    dates = json.loads(codecs.decode(m.group("j"), "unicode_escape"))
    return json.dumps({"dates": dates}, ensure_ascii=False).encode(), "league page"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="understat-out")
    ap.add_argument("--from", dest="first", type=int, default=FIRST)
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args(argv)
    today = dt.date.today()
    last = today.year if today.month >= 7 else today.year - 1
    files, failed = [], []
    for season in range(a.first, last + 1):
        rel = f"understat/{LEAGUE}/{season}.json"
        try:
            body, how = season_data(season)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {rel}: {e}", flush=True)
            failed.append(dict(path=rel, error=str(e)))
            continue
        n = len(json.loads(body).get("dates", []))
        path = os.path.join(a.out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(body)
        files.append(dict(path=rel, season=season, route=how, matches=n, bytes=len(body),
                          sha256=hashlib.sha256(body).hexdigest(),
                          fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")))
        print(f"ok {rel}: {n} matches via {how}", flush=True)
        time.sleep(a.pause)
    os.makedirs(os.path.join(a.out, "understat"), exist_ok=True)
    json.dump(dict(source="understat.com", league=LEAGUE, files=files, failed=failed),
              open(os.path.join(a.out, "understat", "manifest.json"), "w"), indent=1)
    print(f"{len(files)} seasons saved, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
