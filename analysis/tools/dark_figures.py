"""Recolour a post's charts for the site's dark page.

The notebooks draw their charts for a white page, which is right for Colab and for GitHub. The
site is dark, so the published copies are recoloured: same marks, same numbers, same positions,
only the palette changes. Run it last, after translate_figures.py has made the German copies:

    python analysis/tools/dark_figures.py analysis/2026-27-md6-bayern-leipzig/figs

It rewrites every .svg below the folder in place and marks it (data-theme="dark" on the root
element), so a second run leaves converted files alone. A colour it does not know stops the run
and is listed, so a new chart cannot slip through half converted: add it to PALETTE.

    --check   change nothing; exit 1 if a chart is still light or uses an unknown colour
"""
import argparse
import base64
import io
import re
import sys
from pathlib import Path

# The page (styles.css): background, text, muted text, lines; home win, draw, away win.
BG, INK, MUTED, LINE, LINE_STRONG = "#1b1e25", "#f2f3f6", "#a3a9b6", "#313642", "#4d5464"
HOME, DRAW, AWAY = "#4f8fee", "#868d9c", "#f5a155"

# Light palette (make_figures.py, post_charts.py, fulltime.py, the notebooks) -> dark page.
# White and ink swap places, so a label inside a bar stays readable: white-on-blue becomes
# dark-on-light-blue. Tints that meant "weaker" on white become dimmer, not paler.
PALETTE = {
    "#ffffff": BG,            # paper, bar joins, marker edges, text inside bars
    "#16161c": INK,           # text, outlines, the final score
    "#5f5f69": MUTED,         # tick labels, captions, the bookmakers' markers
    "#e6e6ea": LINE,          # grid
    "#ececf0": LINE,
    "#cfcfd6": LINE_STRONG,
    "#2f6fdb": HOME,
    "#c25a00": AWAY,
    "#9a9aa4": DRAW,          # the draw segment
    "#bdbdc5": "#687082",     # neutral marks: other clubs, "against" bars
    "#d4d4da": "#454b59",     # draw scores, tinted
    "#256abf": "#6aa5f6",     # strong blue (the published forecast)
    "#6da7ec": "#3f72c2",     # weaker blue (single models)
    "#9ec5f4": "#31568f",     # weakest blue
    "#a9c4f2": "#31568f",     # home-win scores, tinted
    "#ebbd99": "#8b5d33",     # away-win scores, tinted
    "#eb6834": "#ff8f66",     # "what the models said"
}

# Heat maps are embedded pictures. Their ramp ran from white (unlikely) to navy (likely); on the
# dark page it runs from the page colour to a light blue, so "more likely" is still "stands out".
LIGHT_RAMP = ["#f6f9fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# The charts print dark text on the cells above 55% of the maximum and light text below, and the
# swap of white and ink turns that round, so the ramp steps up between its fourth and fifth stop.
DARK_RAMP = ["#20242d", "#222f47", "#253d66", "#2c528c", "#5596f0", "#7bb0f6", "#9fc6f9", "#c2dafb"]

COLOUR = re.compile(r"(?P<lead>(?:fill|stroke|stop-color|color)\s*[:=]\s*\"?\s*)(?P<hex>#[0-9a-fA-F]{6})\b")
IMAGE = re.compile(r"(xlink:href=\"data:image/png;base64,)([^\"]+)(\")")
MARK = 'data-theme="dark"'


def rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def ramp(stops, steps=256):
    """The stops as evenly spaced points on a line, sampled at `steps` positions."""
    points = [rgb(stop) for stop in stops]
    out = []
    for k in range(steps):
        pos = k / (steps - 1) * (len(points) - 1)
        i = min(int(pos), len(points) - 2)
        f = pos - i
        out.append(tuple(round(points[i][c] + (points[i + 1][c] - points[i][c]) * f) for c in range(3)))
    return out


def recolour_png(data):
    """Move every pixel from its place on the light ramp to the same place on the dark ramp."""
    from PIL import Image
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    light, dark = ramp(LIGHT_RAMP), ramp(DARK_RAMP)
    cache = {}

    def swap(pixel):
        key = pixel[:3]
        if key not in cache:
            nearest = min(range(len(light)), key=lambda k: sum((light[k][c] - key[c]) ** 2 for c in range(3)))
            distance = sum((light[nearest][c] - key[c]) ** 2 for c in range(3)) ** 0.5
            if distance > 12:
                raise ValueError(f"a picture inside the chart has a colour off the known ramp: {key}")
            cache[key] = dark[nearest]
        return cache[key] + (pixel[3],)

    raw = image.tobytes()
    pixels = b"".join(bytes(swap(tuple(raw[i:i + 4]))) for i in range(0, len(raw), 4))
    image = Image.frombytes("RGBA", image.size, pixels)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def convert(text):
    """(dark SVG, unknown colours). The input must be a light chart."""
    unknown = sorted({m.group("hex").lower() for m in COLOUR.finditer(text)} - set(PALETTE))
    if unknown:
        return None, unknown
    text = COLOUR.sub(lambda m: m.group("lead") + PALETTE[m.group("hex").lower()], text)
    text = IMAGE.sub(lambda m: m.group(1) + base64.b64encode(recolour_png(base64.b64decode(m.group(2)))).decode() + m.group(3), text)
    return re.sub(r"<svg\b", f"<svg {MARK}", text, count=1), []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folders", nargs="+", help="figs folders (every .svg below is converted in place)")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = sorted(path for folder in a.folders for path in Path(folder).rglob("*.svg"))
    if not files:
        raise SystemExit("no .svg files found")
    done = skipped = 0
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if MARK in text[:2000]:
            skipped += 1
            continue
        dark, unknown = convert(text)
        if unknown:
            problems.append(f"{path}: unknown colours {', '.join(unknown)}")
        elif a.check:
            problems.append(f"{path}: still drawn for a white page")
        else:
            path.write_text(dark, encoding="utf-8")
            done += 1
    for line in problems:
        print(line, file=sys.stderr)
    print(f"{done} converted, {skipped} already dark, {len(problems)} with problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
