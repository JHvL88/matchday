"""Download Bundesliga (D1) and 2. Bundesliga (D2) season files from football-data.co.uk.

Files are saved byte-for-byte as served, next to a manifest with a SHA-256 checksum per file,
so every number in a forecast can be traced back to an exact source file.

    python analysis/pipeline/fetch_football_data.py --out source            # all seasons
    python analysis/pipeline/fetch_football_data.py --out source --from 2019 # 2019/20 onwards

Runs anywhere with internet access: Google Colab, GitHub Actions, a laptop.
Only the standard library is used.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"
DIVISIONS = ("D1", "D2")
FIRST_SEASON = 2000          # 2000/01
USER_AGENT = "Mozilla/5.0 (compatible; jans-matchday-data/1.0; +https://jhvl88.github.io/matchday/)"


def season_code(start_year):
    """2026 -> '2627' (football-data's folder name for 2026/27)."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def current_season(today=None):
    today = today or dt.date.today()
    return today.year if today.month >= 7 else today.year - 1


def download(url, retries=4, pause=3.0):
    """Return (bytes, headers). Retries with backoff on 429/5xx and network errors."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                raise
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        wait = pause * (2 ** attempt)
        print(f"  retry {attempt + 1}/{retries - 1} in {wait:.0f}s ({last})", flush=True)
        time.sleep(wait)
    raise last


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="source", help="output folder")
    ap.add_argument("--from", dest="first", type=int, default=FIRST_SEASON, help="first season start year")
    ap.add_argument("--to", dest="last", type=int, default=None, help="last season start year (default: current)")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between requests (be polite)")
    args = ap.parse_args(argv)

    last = args.last or current_season()
    files, failed = [], []
    for season in range(args.first, last + 1):
        code = season_code(season)
        for div in DIVISIONS:
            url = BASE.format(code=code, div=div)
            rel = f"football-data/{code}/{div}.csv"
            try:
                body, headers = download(url)
            except Exception as e:  # noqa: BLE001 - record and carry on, fail at the end
                print(f"FAILED {rel}: {e}", flush=True)
                failed.append(dict(path=rel, url=url, error=str(e)))
                continue
            path = os.path.join(args.out, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(body)
            files.append(dict(
                path=rel, url=url, season=season, division=div, bytes=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
                last_modified=headers.get("Last-Modified"), etag=headers.get("ETag"),
                fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            ))
            print(f"ok {rel}  {len(body):>7} bytes  sha256 {files[-1]['sha256'][:12]}", flush=True)
            time.sleep(args.pause)

    manifest = dict(
        source="football-data.co.uk (results, match statistics and odds; see https://www.football-data.co.uk/notes.txt)",
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        seasons=[args.first, last], files=files, failed=failed,
    )
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"{len(files)} files saved, {len(failed)} failed -> {args.out}/manifest.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
