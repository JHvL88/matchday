"""Draw the 1200 × 630 preview images that appear when a page is shared (WhatsApp, X, LinkedIn, Slack).

Writes assets/share/home.jpg, assets/share/season.jpg and analysis/<post>/share.jpg for every post in
analysis/posts.json,
using the site's own fonts, colours and forecast bar. Run it after adding a post:

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


# The site's colours (styles.css): filled segments are my models, the white pins the bookmakers.
BG, INK, INK_2, MUTED, RED = "#1b1e25", "#f2f3f6", "#cfd3dc", "#a3a9b6", "#e02b3b"
HOME, DRAW, AWAY = "#4f8fee", "#868d9c", "#f5a155"

BASE_CSS = f"""
@font-face {{ font-family: "Barlow Condensed"; font-weight: 600; src: url("{font("barlow-condensed-latin-600-normal.woff2")}"); }}
@font-face {{ font-family: "Barlow Condensed"; font-weight: 600; src: url("{font("barlow-condensed-latin-ext-600-normal.woff2")}"); unicode-range: U+0100-024F; }}
@font-face {{ font-family: "DM Sans"; font-weight: 400; src: url("{font("dm-sans-latin-400-normal.woff2")}"); }}
@font-face {{ font-family: "DM Sans"; font-weight: 600; src: url("{font("dm-sans-latin-600-normal.woff2")}"); }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.card {{ width: 1200px; height: 630px; padding: 60px 72px 56px; background: {BG}; color: {INK};
  font-family: "DM Sans", sans-serif; display: flex; flex-direction: column; }}
.tag {{ margin: 0 0 14px; color: {MUTED}; font-size: 26px; }}
.title {{ margin: 0; font-family: "Barlow Condensed", sans-serif; font-weight: 600; line-height: 1; }}
.sub {{ margin: 22px 0 0; max-width: 900px; color: {INK_2}; font-size: 32px; line-height: 1.3; }}
.forecast {{ margin-top: auto; }}
.bar {{ position: relative; height: 92px; }}
.track {{ position: absolute; inset: 24px 0; display: flex; }}
.track span {{ height: 100%; }}
.track span:not(:last-child) {{ border-right: 4px solid {BG}; }}
.track span:first-child {{ border-radius: 6px 0 0 6px; }}
.track span:last-child {{ flex: 1 1 0; border-radius: 0 6px 6px 0; }}
.pin {{ position: absolute; top: 4px; width: 4px; height: 84px; margin-left: -2px; border-radius: 2px; background: #fff;
  box-shadow: 0 0 0 4px {BG}; }}
.nums {{ display: flex; justify-content: space-between; margin-top: 6px; color: {INK_2}; font-size: 28px; }}
.nums b {{ color: {INK}; font-weight: 600; }}
.key {{ margin: 14px 0 0; color: {MUTED}; font-size: 24px; }}
.brand {{ margin-top: 34px; display: flex; align-items: center; gap: 14px; font-family: "Barlow Condensed", sans-serif;
  font-weight: 600; font-size: 34px; }}
.forecast + .brand {{ margin-top: 30px; }}
.mark {{ width: 48px; height: 48px; border-radius: 50%; background: {RED}; color: #fff; display: grid; place-items: center;
  font-size: 30px; }}
.where {{ color: {MUTED}; font-family: "DM Sans", sans-serif; font-weight: 400; font-size: 24px; }}
"""


def bar(model, market=None):
    """The site's forecast bar: three filled segments for the models, two pins for the bookmakers."""
    segments = "".join(
        f'<span style="{f"width:{model[i] * 100:.1f}%;" if i < 2 else ""}background:{colour}"></span>'
        for i, colour in enumerate((HOME, DRAW, AWAY)))
    pins = "" if not market else "".join(
        f'<i class="pin" style="left:{cut * 100:.1f}%"></i>' for cut in (market[0], market[0] + market[1]))
    return f'<div class="bar"><div class="track">{segments}</div>{pins}</div>'


def short(name):
    return {"Hamburger SV": "Hamburg", "VfB Stuttgart": "Stuttgart", "FC Augsburg": "Augsburg",
            "FC Bayern München": "Bayern", "RB Leipzig": "Leipzig"}.get(name, name)


def brand(where="", name="Jan’s Matchday"):
    return f'<div class="brand"><span class="mark">J</span>{name}<span class="where">{where}</span></div>'


def home_card():
    # The bar here is the page's legend, not a forecast: it shows how every match is drawn.
    return f"""<div class="card">
      <h1 class="title" style="font-size:132px">Jan’s Matchday</h1>
      <p class="sub">Every Bundesliga match forecast by three models, published before kick-off and graded against the bookmakers after full time.</p>
      <div class="forecast">
        {bar((0.46, 0.25, 0.29), (0.52, 0.24, 0.24))}
        <div class="nums"><span>Home win</span><span>Draw</span><span>Away win</span></div>
        <p class="key">Filled bar: my models. White pins: the bookmakers.</p>
      </div>
      {brand("jhvl88.github.io/matchday", name="")}
    </div>"""


def season_card():
    # Like the home card, the bars are a picture of how the page draws chances, not this week's numbers.
    rows = "".join(f"""<div style="display:flex;align-items:center;gap:22px;margin-top:18px">
          <div style="position:relative;flex:1;height:22px;border-radius:5px;background:#2b303b">
            <div style="position:absolute;inset:0 {100 - fill}% 0 0;border-radius:5px;background:{INK_2}"></div>
            <i style="position:absolute;top:-9px;left:{pin}%;width:5px;height:40px;margin-left:-2.5px;border-radius:2px;background:#fff;box-shadow:0 0 0 4px {BG}"></i>
          </div></div>""" for fill, pin in ((82, 88), (11, 7), (4, 3)))
    return f"""<div class="card">
      <p class="tag">Season simulator</p>
      <h1 class="title" style="font-size:96px">The Bundesliga season,<br>played 50,000 times</h1>
      <p class="sub" style="font-size:28px;margin-top:18px">Title, Champions League and relegation chances for every club. Plus: pick the results yourself.</p>
      <div class="forecast">{rows}
        <p class="key">Filled bar: my models. White pin: the bookmakers’ version.</p>
      </div>
      {brand("jhvl88.github.io/matchday/season")}
    </div>"""


def post_card(post):
    f = post.get("forecast", {})
    model, market = f.get("model"), f.get("market")
    home, away = short(post["home"]["name"]), short(post["away"]["name"])
    pct = lambda p: f"{round(p * 100)}%"
    forecast = ""
    if model:
        forecast = f"""<div class="forecast">
        {bar(model, market)}
        <div class="nums"><span>{html.escape(home)} <b>{pct(model[0])}</b></span><span>Draw <b>{pct(model[1])}</b></span><span>{html.escape(away)} <b>{pct(model[2])}</b></span></div>
        <p class="key">Filled bar: my models. White pins: the bookmakers.</p>
      </div>"""
    return f"""<div class="card">
      <p class="tag">{html.escape(post["en"]["tag"])}</p>
      <h1 class="title" style="font-size:{108 if len(home) + len(away) > 18 else 124}px">{html.escape(home)} v {html.escape(away)}</h1>
      {forecast}
      {brand()}
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
        render(page, season_card(), ROOT / "assets" / "share" / "season.jpg")
        for post in posts:
            render(page, post_card(post), ROOT / post["path"] / "share.jpg")
        browser.close()


if __name__ == "__main__":
    main()
