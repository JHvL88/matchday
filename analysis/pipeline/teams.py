"""One key per club, whatever the source calls it.

football-data.co.uk says "M'gladbach", OpenLigaDB "Borussia Mönchengladbach", The Odds API
"Borussia Monchengladbach". `club_key()` maps all of them to "gladbach". An unknown name returns
None, so a new spelling shows up as an unmatched match instead of a silent mix-up.
"""
import re
import unicodedata

# key: substrings that identify the club in a normalised name (lower case, no accents).
# Checked in order; the first hit wins, so more specific patterns come first.
CLUBS = [
    ("munich1860", ["1860"]),
    ("bayern", ["bayern"]),
    ("dortmund", ["dortmund"]),
    ("gladbach", ["gladbach"]),
    ("leverkusen", ["leverkusen"]),
    ("leipzig", ["leipzig"]),
    ("fsvfrankfurt", ["frankfurt fsv", "fsv frankfurt"]),
    ("frankfurt", ["eintracht frankfurt", "ein frankfurt", "frankfurt"]),
    ("stuttgart", ["stuttgart"]),
    ("stpauli", ["pauli"]),
    ("hamburg", ["hamburg"]),
    ("koln", ["koln", "koeln", "cologne"]),
    ("bremen", ["bremen"]),
    ("wolfsburg", ["wolfsburg"]),
    ("freiburg", ["freiburg"]),
    ("mainz", ["mainz"]),
    ("augsburg", ["augsburg"]),
    ("hoffenheim", ["hoffenheim"]),
    ("union", ["union berlin", "union"]),
    ("hertha", ["hertha"]),
    ("heidenheim", ["heidenheim"]),
    ("bochum", ["bochum"]),
    ("kiel", ["kiel"]),
    ("elversberg", ["elversberg"]),
    ("paderborn", ["paderborn"]),
    ("darmstadt", ["darmstadt"]),
    ("schalke", ["schalke"]),
    ("hannover", ["hannover", "hanover"]),
    ("nurnberg", ["nurnberg", "nuernberg", "nuremberg"]),
    ("dusseldorf", ["dusseldorf", "duesseldorf"]),
    ("kaiserslautern", ["kaiserslautern"]),
    ("karlsruhe", ["karlsruhe"]),
    ("magdeburg", ["magdeburg"]),
    ("furth", ["furth", "fuerth"]),
    ("braunschweig", ["braunschweig"]),
    ("munster", ["munster", "muenster"]),
    ("bielefeld", ["bielefeld"]),
    ("regensburg", ["regensburg"]),
    ("ulm", ["ulm"]),
    ("rostock", ["rostock"]),
    ("dresden", ["dresden"]),
    ("osnabruck", ["osnabruck", "osnabrueck"]),
    ("wiesbaden", ["wiesbaden", "wehen"]),
    ("sandhausen", ["sandhausen"]),
    ("ingolstadt", ["ingolstadt"]),
    ("aue", ["aue"]),
    ("aachen", ["aachen"]), ("aalen", ["aalen"]), ("ahlen", ["ahlen"]), ("burghausen", ["burghausen"]),
    ("jena", ["jena"]), ("cottbus", ["cottbus"]), ("duisburg", ["duisburg"]), ("essen", ["essen"]),
    ("koblenz", ["koblenz"]), ("oberhausen", ["oberhausen"]), ("offenbach", ["offenbach"]),
    ("saarbrucken", ["saarbrucken", "saarbruecken"]), ("siegen", ["siegen"]), ("unterhaching", ["unterhaching"]),
    ("wurzburg", ["wurzburg", "wuerzburg"]),
]


def normalise(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s.replace("'", "").replace(".", " ")).strip()


def club_key(name):
    s = normalise(name)
    for key, patterns in CLUBS:
        if any(re.search(rf"(?<![a-z]){re.escape(p)}(?![a-z])", s) or (len(p) >= 6 and p in s) for p in patterns):
            return key
    return None
