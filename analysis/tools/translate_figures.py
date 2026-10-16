"""Make German copies of the analysis charts.

The charts are matplotlib SVGs with the text stored as glyph outlines (svg.fonttype = "path"), and
re-running the notebooks would not reproduce them exactly (MCMC). So this script edits the published
SVGs instead: every number and every mark stays as it is, and only the words and number formats change.

For each text line it
  1. reads the original string from the comment matplotlib writes above it,
  2. translates it (rules below) and formats numbers the German way (1,47 · 25 %),
  3. lays the new string out with matplotlib and the same font, so the glyphs are exactly what
     matplotlib would have drawn,
  4. keeps the original alignment (left, centred or right) by shifting the line by the width change,
  5. moves legend entries so they still line up, and widens the canvas if a longer label needs room.

Usage (from the repository root):
    pip install matplotlib==3.11.2 lxml
    python analysis/tools/translate_figures.py analysis/2026-27-md6-hamburg-stuttgart [more post folders]
Writes <post>/figs/de/*.svg. Use the matplotlib version named in the charts' metadata, so the glyph
layout matches; the script stops if it does not. It downloads the DM Sans font the charts use on
first run, from the same place as the notebooks.

New wording in a new chart: add a rule to RULES. The script lists any English text it left alone.
"""
import copy
import html
import io
import math
import re
import sys
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lxml import etree
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz,wght%5D.ttf"
FONT = Path.home() / ".cache" / "jans-matchday" / "DMSans.ttf"
if not FONT.exists():
    FONT.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(FONT_URL, FONT)
font_manager.fontManager.addfont(str(FONT))
FAMILY = FontProperties(fname=str(FONT)).get_name()
plt.rcParams.update({"font.family": FAMILY, "svg.fonttype": "path"})

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
HREF = f"{{{XLINK}}}href"
PAD = 0.15 * 72          # pad_inches used when the charts were saved

# ------------------------------------------------------------------------------------------ wording
# Applied in order; the first rule that matches wins. Club names stay as they are.
RULES = [
    (r"^Bookmakers$", "Buchmacher"),
    (r"^Bayesian$", "Bayes-Modell"),
    (r"^Draw$", "Remis"),
    (r"^(.+) win$", r"Sieg \1"),
    (r"^(.+) goals  ·  expected (.+)$", r"Tore \1  ·  erwartet \2"),
    (r"^Shots on target created \(× Bundesliga average\)$", "Erzeugte Schüsse aufs Tor (× Ligaschnitt)"),
    (r"^Shots on target conceded \(× Bundesliga average\)$", "Zugelassene Schüsse aufs Tor (× Ligaschnitt)"),
    (r"^Shots on target created \(× average\)  →  better$", "Erzeugte Schüsse aufs Tor (× Schnitt)  →  besser"),
    (r"^Shots on target conceded \(× average\)  ↑ fewer$", "Zugelassene Schüsse aufs Tor (× Schnitt)  ↑ weniger"),
    (r"^Ranked probability score, (\d+) out-of-sample matches \(lower is better\)$",
     r"Ranked Probability Score, \1 Out-of-Sample-Spiele (niedriger ist besser)"),
    (r"^Forecast probability$", "Prognostizierte Wahrscheinlichkeit"),
    (r"^How often it happened$", "Tatsächliche Häufigkeit"),
    (r"^perfect calibration$", "perfekte Kalibrierung"),
    (r"^lies on the diagonal$", "liegt auf der Diagonale"),
    (r"^What moves (.+)'s expected goals$", r"Was \1s erwartete Tore bewegt"),
    (r"^Elo gap$", "Elo-Differenz"),
    (r"^Goals-scored gap$", "Differenz erzielte Tore"),
    (r"^Shots-on-target gap$", "Differenz Schüsse aufs Tor"),
    (r"^(.+) goals conceded \(form\)$", r"\1: Gegentore (Form)"),
    (r"^(.+) goals scored \(form\)$", r"\1: erzielte Tore (Form)"),
    (r"^(.+) goals per shot on target faced$", r"\1: Gegentore pro Schuss aufs Tor"),
    (r"^(.+) shots on target \(form\)$", r"\1: Schüsse aufs Tor (Form)"),
    (r"^(.+) shots \(form\)$", r"\1: Schüsse (Form)"),
    (r"^(.+) shots faced$", r"\1: zugelassene Schüsse"),
    (r"^(.+) Elo$", r"\1: Elo"),
    (r"^(.+) goals$", r"Tore \1"),
    (r"^Points after (\d+) matchdays$", r"Punkte nach \1 Spieltagen"),
    (r"^Actual points$", "Tatsächliche Punkte"),
    (r"^Expected from shots on target$", "Erwartet aus Schüssen aufs Tor"),
    (r"^(.+)   ← full time$", r"\1   ← Endstand"),
    (r"^Chance the bookmakers' favourite wins$", "Siegchance des Buchmacher-Favoriten"),
    (r"^Models (\S+) points less sure$", r"Modelle \1 Punkte skeptischer"),
    (r"^Models (\S+) points more sure$", r"Modelle \1 Punkte zuversichtlicher"),
    (r"^Within (\d+) points$", r"Abstand unter \1 Punkten"),
    (r"^(\d+) matches  ← this match$", r"\1 Spiele  ← dieses Spiel"),
    (r"^(\d+) matches$", r"\1 Spiele"),
    (r"^Models said$", "Modelle sagten"),
    (r"^Bookmakers said$", "Buchmacher sagten"),
    (r"^Actually happened$", "Tatsächlich eingetreten"),
]

# Text that is the same in both languages (club names, model names, seasons).
KEEP = {"Ensemble", "XGBoost", "Dixon–Coles", "Augsburg – Bayern", "Bayern", "Augsburg", "Hamburg", "Stuttgart",
        "Dortmund", "Frankfurt", "Elversberg", "Köln", "Freiburg", "Hoffenheim", "Leverkusen", "Gladbach", "Mainz",
        "Paderborn", "Leipzig", "Schalke", "Union", "Bremen"}

# Per chart: alignment of free-standing text (ax.text, titles) that the SVG cannot tell us,
# whether scores read 1:2, and how the legend is anchored.
CHARTS = {
    "fig1_forecast": {"center": r"%$|^Sieg |^Remis$"},
    "fig2_scorelines": {"center": r"%$"},
    "fig3_goals": {"center": r"%$"},
    "fig6_xpts": {"legend": "right"},
    "fig9_fulltime": {"scores": True},
    "fig10_disagreement": {"legend": "center"},
}


def translate(text, chart):
    new = text
    for pattern, repl in RULES:
        if re.search(pattern, text):
            new = re.sub(pattern, repl, text)
            break
    if CHARTS.get(chart, {}).get("scores"):
        new = re.sub(r"^(\d+)–(\d+)$", r"\1:\2", new)
    new = re.sub(r"(\d)\.(\d)", r"\1,\2", new)          # 1.47 -> 1,47
    new = re.sub(r"(\d)%", "\\1\u00a0%", new)           # 25% -> 25 % (no-break space)
    return new


# ------------------------------------------------------------------------------------------ layout
_t2p = TextToPath()


def width(text, size):
    """Line width in points, computed exactly as matplotlib's SVG backend does for alignment."""
    w, _, _ = _t2p.get_text_width_height_descent(text, FontProperties(family=FAMILY, size=size), ismath=False)
    return w


_glyph_cache = {}


def glyphs(text, size):
    """(uses, defs): the <use> list matplotlib writes for this string, and the glyph outlines it needs."""
    key = (text, size)
    if key not in _glyph_cache:
        fig = plt.figure(figsize=(30, 1), dpi=72)
        fig.text(0, 0.5, text, fontsize=size)
        buf = io.BytesIO()
        fig.savefig(buf, format="svg")
        plt.close(fig)
        root = etree.fromstring(buf.getvalue())
        line = root.find(f".//{{{SVG}}}g[@id='text_1']/{{{SVG}}}g")
        uses = [(u.get(HREF)[1:], u.get("transform")) for u in line.iter(f"{{{SVG}}}use")]
        defs = {p.get("id"): p for p in root.iter(f"{{{SVG}}}path") if p.get("id")}
        _glyph_cache[key] = (uses, defs)
    return _glyph_cache[key]


TRANSFORM = re.compile(r"translate\(([-\d.e]+) ([-\d.e]+)\)(?: rotate\(([-\d.e]+)\))? scale\(([-\d.e]+) ([-\d.e]+)\)")


def fmt(v):
    return f"{v:.6f}".rstrip("0").rstrip(".")


def ancestors(el):
    out = []
    p = el.getparent()
    while p is not None:
        out.append(p.get("id") or "")
        p = p.getparent()
    return out


def alignment(line, original, chart):
    ids = ancestors(line)
    if any(i.startswith("legend_") for i in ids):
        return "left"
    if any(i.startswith("xtick_") for i in ids):
        return "center"
    if any(i.startswith("ytick_") for i in ids):
        return "right"
    text_group_parent = ids[1] if len(ids) > 1 else ""
    if text_group_parent in ("matplotlib.axis_1", "matplotlib.axis_2"):
        return "center"                                     # axis labels
    rule = CHARTS.get(chart, {}).get("center")
    if rule and re.search(rule, translate(original, chart)):
        return "center"
    return "left"                                           # titles (axes.titlelocation = left) and ax.text


def process(src, dst):
    chart = src.stem
    tree = etree.parse(str(src), etree.XMLParser(remove_blank_text=False))
    root = tree.getroot()
    defined = {p.get("id") for p in root.iter(f"{{{SVG}}}path") if p.get("id")}
    changed, kept, boxes, legend_items = [], [], [], []

    for comment in list(root.iter(etree.Comment)):
        line = comment.getnext()
        if line is None or line.tag != f"{{{SVG}}}g" or not TRANSFORM.search(line.get("transform", "")):
            continue
        original = html.unescape(comment.text.strip())
        new = translate(original, chart)
        m = TRANSFORM.search(line.get("transform"))
        x, y = float(m.group(1)), float(m.group(2))
        rot = float(m.group(3) or 0)
        scale = float(m.group(4))
        size = round(scale * 100, 4)

        # The comment, our font and our layout must reproduce the published glyphs exactly.
        published = [(u.get(HREF)[1:], u.get("transform")) for u in line.iter(f"{{{SVG}}}use")]
        if glyphs(original, size)[0] != published:
            raise SystemExit(f"{src}: glyphs for {original!r} do not match a fresh layout "
                             f"(different matplotlib version or font?)")

        legend = next((i for i in ancestors(line) if i.startswith("legend_")), None)
        w_old, w_new = width(original, size), width(new, size)
        if new == original:
            if re.search(r"[A-Za-z]", original) and original not in KEEP:
                kept.append(original)
            if legend:
                legend_items.append((legend, line, x, w_old, w_old))
            continue

        align = alignment(line, original, chart)
        shift = {"left": 0.0, "center": (w_old - w_new) / 2, "right": w_old - w_new}[align]
        dx, dy = shift * math.cos(math.radians(rot)), shift * math.sin(math.radians(rot))
        x, y = x + dx, y + dy
        parts = [f"translate({fmt(x)} {fmt(y)})"]
        if m.group(3):
            parts.append(f"rotate({m.group(3)})")
        parts.append(f"scale({m.group(4)} {m.group(5)})")
        line.set("transform", " ".join(parts))

        uses, glyph_defs = glyphs(new, size)
        for u in list(line.iter(f"{{{SVG}}}use")):
            u.getparent().remove(u)
        missing = [g for g, _ in uses if g not in defined]
        if missing:
            defs = line.find(f"{{{SVG}}}defs")
            if defs is None:
                defs = etree.SubElement(line, f"{{{SVG}}}defs")
                line.insert(0, defs)
            for g in dict.fromkeys(missing):
                defs.append(copy.deepcopy(glyph_defs[g]))
                defined.add(g)
            _reindent(defs, line)
        for g, transform in uses:
            use = etree.SubElement(line, f"{{{SVG}}}use")
            use.set(HREF, f"#{g}")
            if transform:
                use.set("transform", transform)
        _reindent(line)
        comment.text = " " + html.escape(new, quote=False) + " "
        changed.append((original, new, align))

        # Extent of the old and new line, for the canvas check.
        boxes.append((_box(x - dx, y - dy, w_old, size, rot), _box(x, y, w_new, size, rot)))
        if legend:
            legend_items.append((legend, line, x, w_old, w_new))

    _shift_legends(root, legend_items, CHARTS.get(chart, {}).get("legend"))
    for legend, line, x, w_old, w_new in legend_items:
        off = float(line.getparent().get("data-shift", 0))
        m = TRANSFORM.search(line.get("transform"))
        ly, size = float(m.group(2)), float(m.group(4)) * 100
        boxes.append((_box(x, ly, w_old, size, 0), _box(x + off, ly, w_new, size, 0)))
    _fit_canvas(root, boxes)
    for g in root.iter(f"{{{SVG}}}g"):
        g.attrib.pop("data-shift", None)

    dst.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(dst), xml_declaration=True, encoding="utf-8", standalone=False)
    return changed, kept


def _reindent(el, parent=None):
    """Keep matplotlib's one-element-per-line layout so the files stay diff-friendly."""
    if parent is not None:                       # a <defs> we just created or extended
        outer = parent.text.split("\n")[-1] if parent.text and "\n" in parent.text else ""
        el.text = "\n" + outer + " "
    depth = el.text.split("\n")[-1] if el.text and "\n" in el.text else ""
    children = list(el)
    for i, child in enumerate(children):
        child.tail = "\n" + (depth if i < len(children) - 1 else depth[:-1])


def _shift_legends(root, items, anchor):
    """Legend entries keep their handle-to-text spacing; whole columns move when their text width changes."""
    by_legend = {}
    for legend, line, x, w_old, w_new in items:
        by_legend.setdefault(legend, []).append((line, x, w_old, w_new))
    for legend_id, entries in by_legend.items():
        if all(abs(w_old - w_new) < 1e-6 for _, _, w_old, w_new in entries):
            continue
        if anchor is None:
            raise SystemExit(f"legend {legend_id} changed width but the chart has no legend anchor")
        legend = root.find(f".//{{{SVG}}}g[@id='{legend_id}']")
        columns = {}
        for line, x, w_old, w_new in entries:
            columns.setdefault(round(x, 1), []).append((line, w_old, w_new))
        xs = sorted(columns)
        growth = [max(w for _, _, w in columns[c]) - max(w for _, w, _ in columns[c]) for c in xs]
        total = sum(growth)
        start = {"left": 0.0, "center": -total / 2, "right": -total}[anchor]
        shift_of = {}
        for k, c in enumerate(xs):
            shift_of[c] = start + sum(growth[:k])
        # Every child of the legend group is an entry handle or an entry text; the handle comes first.
        children = list(legend)
        pending = []
        for child in children:
            if (child.get("id") or "").startswith("patch_"):
                raise SystemExit(f"legend {legend_id} has a frame; widening framed legends is not supported")
            text_line = child.find(f"{{{SVG}}}g") if (child.get("id") or "").startswith("text_") else None
            if text_line is None:
                pending.append(child)
                continue
            col = min(xs, key=lambda c: abs(c - _orig_x(entries, text_line)))
            dx = shift_of[col]
            for el in pending + [child]:
                if abs(dx) > 1e-9:
                    el.set("transform", f"translate({fmt(dx)} 0)")
                el.set("data-shift", str(dx))
            pending = []


def _orig_x(entries, text_line):
    for line, x, _, _ in entries:
        if line is text_line:
            return x
    raise KeyError


def _box(x, y, w, size, rot):
    """Rough extent of a text line (height ~ font size); only ever compared with another _box."""
    if abs(rot) < 1:
        return (x, y - size, x + w, y + 0.3 * size)
    return (x - size, y - w, x + 0.3 * size, y)


def _fit_canvas(root, boxes):
    """Grow the canvas (never shrink it) where a new label reaches further out than the old one did
    and closer to the edge than matplotlib's padding."""
    if not boxes:
        return
    x0, y0, w, h = [float(v) for v in root.get("viewBox").split()]
    left = min([x0] + [new[0] - PAD for old, new in boxes if new[0] < min(old[0], x0 + PAD)])
    top = min([y0] + [new[1] - PAD for old, new in boxes if new[1] < min(old[1], y0 + PAD)])
    right = max([x0 + w] + [new[2] + PAD for old, new in boxes if new[2] > max(old[2], x0 + w - PAD)])
    bottom = max([y0 + h] + [new[3] + PAD for old, new in boxes if new[3] > max(old[3], y0 + h - PAD)])
    if (left, top, right, bottom) == (x0, y0, x0 + w, y0 + h):
        return
    nw, nh = right - left, bottom - top
    root.set("viewBox", f"{fmt(left)} {fmt(top)} {fmt(nw)} {fmt(nh)}")
    root.set("width", f"{fmt(nw)}pt")
    root.set("height", f"{fmt(nh)}pt")
    figure = root.find(f"{{{SVG}}}g[@id='figure_1']")
    background = figure.find(f"{{{SVG}}}g[@id='patch_1']/{{{SVG}}}path")
    fill = re.search(r"fill: (#[0-9a-fA-F]+)", background.get("style", "")).group(1)
    rect = etree.Element(f"{{{SVG}}}rect", x=fmt(left), y=fmt(top), width=fmt(nw), height=fmt(nh), style=f"fill: {fill}")
    rect.tail = figure.text
    figure.insert(0, rect)


def main(dirs):
    problems = 0
    for d in dirs:
        for src in sorted(Path(d, "figs").glob("*.svg")):
            changed, kept = process(src, Path(d, "figs", "de", src.name))
            print(f"{src}: {len(changed)} lines translated")
            for original, new, align in changed:
                print(f"    {align:6} {original!r} -> {new!r}")
            for text in kept:
                problems += 1
                print(f"    UNTRANSLATED {text!r}")
    if problems:
        raise SystemExit(f"{problems} English strings left untranslated")


if __name__ == "__main__":
    main(sys.argv[1:])
