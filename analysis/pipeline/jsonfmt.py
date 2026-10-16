"""JSON written the way the site's hand-edited files look: indented, short number lists on one line."""
import json
import re

_NUMBERS = re.compile(r"\[\s*([-0-9.eE,\s]+?)\s*\]")
_FLAT = re.compile(r'\{\n\s*((?:"[^"\n]+": -?[0-9.eE]+,?\n\s*)+)\}')


def dumps(obj, inline_number_objects=False):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    text = _NUMBERS.sub(lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",")) + "]", text)
    if inline_number_objects:   # {"models": 0.267, "market": 0.331} on one line, as in posts.json
        text = _FLAT.sub(lambda m: "{ " + " ".join(m.group(1).split()) + " }", text)
    return text
