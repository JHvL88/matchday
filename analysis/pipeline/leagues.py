"""The leagues the pipeline knows, by football-data.co.uk's division codes.

Each league is its own world: a top flight and the second tier below it, so promoted clubs arrive
with a record. Germany is the one the site forecasts; the other four are the test bed for methods
(analysis/backtest/leagues/). Only the standard library is used.
"""

# league: (top flight, second tier, name of the top flight)
LEAGUES = {
    "GER": ("D1", "D2", "Bundesliga"),
    "ENG": ("E0", "E1", "Premier League"),
    "ESP": ("SP1", "SP2", "La Liga"),
    "ITA": ("I1", "I2", "Serie A"),
    "FRA": ("F1", "F2", "Ligue 1"),
}
HOME = "GER"


def divisions(league):
    return LEAGUES[league][:2]


def league_names(arg):
    """['all'] or a list of league codes -> list of league codes, Germany first."""
    names = list(LEAGUES) if not arg or list(arg) == ["all"] else [a.upper() for a in arg]
    unknown = [n for n in names if n not in LEAGUES]
    if unknown:
        raise SystemExit(f"unknown league(s) {unknown}; known: {list(LEAGUES)}")
    return sorted(set(names), key=list(LEAGUES).index)
