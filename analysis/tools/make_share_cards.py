"""Draw the 1200 × 630 preview images that appear when a page is shared (WhatsApp, X, LinkedIn, Slack).

Writes assets/share/home.jpg and analysis/<post>/share.jpg for every post in analysis/posts.json,
using the site's own fonts and colours. Run it after adding a post:

    pip install playwright && playwright install chromium
    python analysis/tools/make_share_cards.py

Each post page points its og:image / twitter:image tags at its share.jpg.
"""
import base64
import html
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts"


def font(name):
    # Inlined, because a page built with set_content may not load file:// fonts.
    return "data:font/woff2;base64," + base64.b64encode((FONT_DIR / name).read_bytes()).decode()


HOME, DRAW, AWAY = "#2f6fdb", "#b4b4bd", "#f08c1a"

BASE_CSS = f"""
@font-face {{ font-family: "Barlow Condensed"; font-weight: 700; src: url("{font("barlow-condensed-latin-700-normal.woff2")}"); }}
@font-face {{ font-family: "Barlow Condensed"; font-weight: 700; src: url("{font("barlow-condensed-latin-ext-700-normal.woff2")}"); unicode-range: U+0100-024F; }}
@font-face {{ font-family: "DM Sans"; font-weight: 400; src: url("{font("dm-sans-latin-400-normal.woff2")}"); }}
@font-face {{ font-family: "DM Sans"; font-weight: 700; src: url("{font("dm-sans-latin-700-normal.woff2")}"); }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.card {{ position: relative; overflow: hidden; width: 1200px; height: 630px; padding: 64px 72px; background: #0c0c10;
  color: #fff; font-family: "DM Sans", sans-serif; display: flex; flex-direction: column; gap: 22px; }}
.card::after {{ content: ""; position: absolute; top: -20px; bottom: -20px; right: 40px; width: 96px; background: #d20515;
  transform: skewX(-22deg); box-shadow: -40px 0 0 -14px rgb(255 255 255 / 85%); }}
.card > * {{ position: relative; z-index: 1; max-width: 880px; }}
.eyebrow {{ margin: 0; color: #ff6b76; font-size: 24px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }}
.title {{ margin: 0; font-family: "Barlow Condensed", sans-serif; font-weight: 700; text-transform: uppercase; line-height: .92; }}
.title span {{ color: #d20515; }}
.sub {{ margin: 0; color: #d8d8de; font-size: 30px; line-height: 1.3; }}
.brand {{ margin-top: auto; display: flex; align-items: center; gap: 16px; font-family: "Barlow Condensed", sans-serif;
  font-weight: 700; font-size: 32px; letter-spacing: .12em; text-transform: uppercase; }}
.mark {{ width: 52px; height: 52px; border-radius: 50%; background: #d20515; box-shadow: 0 0 0 3px #fff; display: grid;
  place-items: center; font-size: 34px; letter-spacing: 0; }}
.rows {{ display: grid; grid-template-columns: 120px 1fr; gap: 14px 18px; align-items: center; width: 820px; }}
.rows .label {{ font-size: 24px; font-weight: 700; color: #d8d8de; }}
.bar {{ display: flex; height: 40px; border-radius: 4px; overflow: hidden; }}
.bar.thin {{ height: 22px; opacity: .85; }}
.bar span {{ display: block; }}
.nums {{ display: flex; justify-content: space-between; width: 820px; padding-left: 138px; font-size: 26px; color: #fff; }}
.chip {{ display: inline-block; padding: 6px 14px; border-radius: 4px; background: #fff; color: #0c0c10; font-size: 24px; font-weight: 700; }}
"""


def bar(probs, thin=False):
    return (f'<div class="bar{" thin" if thin else ""}">'
            f'<span style="width:{probs[0] * 100:.1f}%;background:{HOME}"></span>'
            f'<span style="width:{probs[1] * 100:.1f}%;background:{DRAW}"></span>'
            f'<span style="width:{probs[2] * 100:.1f}%;background:{AWAY}"></span></div>')


def short(name):
    return {"Hamburger SV": "Hamburg", "VfB Stuttgart": "Stuttgart", "FC Augsburg": "Augsburg",
            "FC Bayern München": "Bayern"}.get(name, name)


def home_card():
    return f"""<div class="card">
      <p class="eyebrow">Bundesliga · English &amp; Deutsch</p>
      <h1 class="title" style="font-size:150px">Jan’s Matchday<span>.</span></h1>
      <p class="sub">Forecasts from three models, the bookmakers’ view, live scores and the table. With the maths explained.</p>
      <div class="brand"><span class="mark">J</span>jhvl88.github.io/matchday</div>
    </div>"""


def post_card(post):
    f = post.get("forecast", {})
    model, market = f.get("model"), f.get("market")
    home, away = short(post["home"]["name"]), short(post["away"]["name"])
    pct = lambda p: f"{round(p * 100)}%"
    rows = ""
    if model and market:
        rows = f"""<div class="rows"><span class="label">Models</span>{bar(model)}<span class="label">Market</span>{bar(market, True)}</div>
        <div class="nums"><span>{html.escape(home)} {pct(model[0])}</span><span>Draw {pct(model[1])}</span><span>{html.escape(away)} {pct(model[2])}</span></div>"""
    return f"""<div class="card">
      <p class="eyebrow">{html.escape(post["en"]["tag"])}</p>
      <h1 class="title" style="font-size:112px">{html.escape(home)} v {html.escape(away)}<span>.</span></h1>
      {rows}
      <div class="brand"><span class="mark">J</span>Jan’s Matchday</div>
    </div>"""


def render(page, body, out):
    page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{BASE_CSS}</style></head><body>{body}</body></html>")
    page.evaluate("document.fonts.ready.then(() => document.fonts.size)")
    page.wait_for_timeout(100)
    out.parent.mkdir(parents=True, exist_ok=True)
    page.locator(".card").screenshot(path=str(out), type="jpeg", quality=88)
    print("wrote", out.relative_to(ROOT))


def main():
    posts = json.loads((ROOT / "analysis" / "posts.json").read_text(encoding="utf-8"))["posts"]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=sys.argv[1] if len(sys.argv) > 1 else None)
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        render(page, home_card(), ROOT / "assets" / "share" / "home.jpg")
        for post in posts:
            render(page, post_card(post), ROOT / post["path"] / "share.jpg")
        browser.close()


if __name__ == "__main__":
    main()
