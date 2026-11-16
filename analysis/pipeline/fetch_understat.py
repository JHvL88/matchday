"""Download Understat's Bundesliga match list (with xG) for every season since 2014/15.

One request per season: https://understat.com/getLeagueData/Bundesliga/<season start year>, the
JSON the league page itself loads. If that endpoint ever disappears, the script falls back to the
older page layout (the `datesData` blob in the league page's HTML).

Saved byte-for-byte with a SHA-256 manifest. Understat publishes no licence, so the raw files go to
the private data repository, never the public one; only derived numbers are published.

    python analysis/pipeline/fetch_understat.py --out understat-out [--previous ../matchday-data/understat]

Three outcomes, told apart by the exit code and by `status` in the manifest:

  0   ok           every season downloaded
  75  unavailable  Understat itself is down (no answer, a server error or its "come back soon"
                   page). Nothing is wrong on our side and nothing was downloaded: keep the stored
                   copy. `understat.add_xg` fills newer matches from football-data.co.uk meanwhile.
  1   failed       Understat answered but something is wrong: a page layout we can't read, a season
                   missing, or (with --previous) a season with fewer played matches than the stored
                   copy, which would mean Understat came back with data missing.
"""
import argparse
import codecs
import datetime as dt
import glob
import gzip
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
EXIT_UNAVAILABLE = 75        # sysexits.h EX_TEMPFAIL: try again later
DOWN_HTTP = (500, 502, 503, 504, 520, 521, 522, 523, 524)


class Unavailable(Exception):
    """Understat is down, as opposed to having changed its pages."""


def get(url, headers, retries=3, pause=3.0, timeout=30):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip", **headers})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            # Understat answers gzip-compressed whether or not it was asked to
            return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                raise
            if attempt < retries - 1:
                time.sleep(pause * 2 ** attempt)
    raise last


def is_down(error):
    """True for errors that mean "the site isn't there": no connection, a timeout, a server error."""
    if isinstance(error, urllib.error.HTTPError):
        return error.code in DOWN_HTTP
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError))


def page_text(html, limit=120):
    text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()[:limit]


def placeholder(html):
    """True for the page Understat serves while it is down ("We will come back soon")."""
    low = html.lower()
    return "errors.css" in low or "come back soon" in low or len(html) < 2000


def season_data(season, pause=3.0):
    """(raw bytes, how) for one season; `how` says which route worked. Raises Unavailable if the site is down."""
    referer = f"{BASE}/league/{LEAGUE}/{season}"
    try:
        body = get(f"{BASE}/getLeagueData/{LEAGUE}/{season}", {"X-Requested-With": "XMLHttpRequest", "Referer": referer},
                   pause=pause)
        data = json.loads(body)
        if data.get("dates"):
            return body, "getLeagueData"
    except Exception as e:  # noqa: BLE001 - try the old layout next
        detail = getattr(e, "read", lambda: b"")()[:200] if hasattr(e, "read") else b""
        print(f"  getLeagueData {season}: {type(e).__name__}: {e} {detail!r}", flush=True)
    try:
        html = get(referer, {}, pause=pause).decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        if is_down(e):
            raise Unavailable(f"no answer from understat.com ({type(e).__name__}: {e})") from e
        raise
    m = re.search(r"datesData\s*=\s*JSON\.parse\('(?P<j>.*?)'\)", html)
    if not m:
        if placeholder(html):
            raise Unavailable(f"understat.com shows a holding page: \"{page_text(html) or 'empty page'}\"")
        snippet = re.sub(r"\s+", " ", html[:600])
        raise RuntimeError(f"no match data found for {season}; page starts: {snippet}")
    dates = json.loads(codecs.decode(m.group("j"), "unicode_escape"))
    return json.dumps({"dates": dates}, ensure_ascii=False).encode(), "league page"


def played(body):
    """Matches with a result in one season file."""
    return sum(1 for e in json.loads(body).get("dates", []) if e.get("isResult"))


def stored_summary(previous):
    """(played matches, date of the newest one) in a stored copy; (0, None) if there is none."""
    n, newest = 0, None
    for path in glob.glob(os.path.join(previous or "", LEAGUE, "*.json")):
        for e in json.load(open(path, encoding="utf-8")).get("dates", []):
            if e.get("isResult"):
                n += 1
                newest = max(newest or "", str(e.get("datetime", ""))[:10])
    return n, newest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="understat-out")
    ap.add_argument("--from", dest="first", type=int, default=FIRST)
    ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--previous", help="the stored understat/ folder: refuse a season with fewer played matches than it has")
    a = ap.parse_args(argv)
    today = dt.date.today()
    last = today.year if today.month >= 7 else today.year - 1
    files, failed, down = [], [], None
    for season in range(a.first, last + 1):
        rel = f"understat/{LEAGUE}/{season}.json"
        if len(failed) >= 2 and not files:
            print("Two seasons failed and none worked: is understat.com reachable from here? Stopping.", flush=True)
            break
        try:
            body, how = season_data(season, a.pause)
        except Unavailable as e:
            if not files and not failed:      # down from the start: nothing to save, nothing broken
                down = str(e)[:300]
                break
            print(f"FAILED {rel}: {str(e)[:300]}", flush=True)
            failed.append(dict(path=rel, error=str(e)[:300]))
            continue
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {rel}: {str(e)[:300]}", flush=True)
            failed.append(dict(path=rel, error=str(e)[:300]))
            continue
        n, done = len(json.loads(body).get("dates", [])), played(body)
        old = os.path.join(a.previous, LEAGUE, f"{season}.json") if a.previous else None
        if old and os.path.exists(old) and done < played(open(old, "rb").read()):
            error = f"{done} played matches, but the stored copy has {played(open(old, 'rb').read())}: Understat is missing data"
            print(f"FAILED {rel}: {error}", flush=True)
            failed.append(dict(path=rel, error=error))
            continue
        path = os.path.join(a.out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(body)
        files.append(dict(path=rel, season=season, route=how, matches=n, played=done, bytes=len(body),
                          sha256=hashlib.sha256(body).hexdigest(),
                          fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")))
        print(f"ok {rel}: {n} matches ({done} played) via {how}", flush=True)
        time.sleep(a.pause)
    status = "unavailable" if down else "failed" if failed or not files else "ok"
    os.makedirs(os.path.join(a.out, "understat"), exist_ok=True)
    json.dump(dict(source="understat.com", league=LEAGUE, status=status, reason=down, files=files, failed=failed),
              open(os.path.join(a.out, "understat", "manifest.json"), "w"), indent=1)
    if down:
        n, newest = stored_summary(a.previous)
        kept = f" The stored copy is untouched: {n} played matches, the newest on {newest}." if n else ""
        print(f"Understat is offline: {down}.{kept} Newer matches take their xG from football-data.co.uk until it is back.")
        return EXIT_UNAVAILABLE
    print(f"{len(files)} seasons saved, {len(failed)} failed")
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
