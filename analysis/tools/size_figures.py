"""Give every chart in a post its width and height, so the page does not jump while charts load.

Reads each <img src="figs/….svg"> in the post's index.html, takes the size from the SVG itself
(matplotlib writes it in points; 1 pt = 4/3 px) and writes width="…" height="…" on the tag.
Safe to run again: tags that already have a width are left alone.

Usage (from the repository root):
    python analysis/tools/size_figures.py analysis/<post folder> [more post folders]
"""
import re
import sys
from pathlib import Path

IMG = re.compile(r'<img\b(?P<attrs>[^>]*?)\bsrc="(?P<src>figs/[^"]+\.svg)"(?P<rest>[^>]*)>')
SIZE = re.compile(r'<svg\b[^>]*?\bwidth="(?P<w>[\d.]+)(?P<wu>pt|px)?"[^>]*?\bheight="(?P<h>[\d.]+)(?P<hu>pt|px)?"', re.S)


def svg_size(path):
    match = SIZE.search(path.read_text(encoding="utf-8")[:4000])
    if not match:
        raise ValueError(f"No width/height in {path}")
    scale = lambda unit: 4 / 3 if unit in (None, "pt") else 1
    return round(float(match["w"]) * scale(match["wu"])), round(float(match["h"]) * scale(match["hu"]))


def size_post(folder):
    page = folder / "index.html"
    html = page.read_text(encoding="utf-8")
    changed = 0

    def add_size(match):
        nonlocal changed
        tag = match.group(0)
        if re.search(r'\bwidth="', tag):
            return tag
        width, height = svg_size(folder / match["src"])
        changed += 1
        return tag.replace(f'src="{match["src"]}"', f'src="{match["src"]}" width="{width}" height="{height}"', 1)

    html = IMG.sub(add_size, html)
    page.write_text(html, encoding="utf-8")
    print(f"{page}: sized {changed} chart(s)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for argument in sys.argv[1:]:
        size_post(Path(argument))
