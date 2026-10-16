const API_BASE = "https://api.openligadb.de";
const LEAGUE = "bl1";
const MAX_MATCHDAYS = 34;
const LIVE_WINDOW_MINUTES = 180;
const LIVE_REFRESH_MS = 60_000;
const STALE_AFTER_MS = 2 * 60_000;
const BERLIN_TIME_ZONE = "Europe/Berlin";
const TEAM_STORAGE_KEY = "jans-matchday:team";
const SVG_NS = "http://www.w3.org/2000/svg";

// Text comes from i18n.js (loaded first); numbers, dates and scores follow the chosen language too.
const { t } = I18N;

// OpenLigaDB identifies result types by resultTypeID: 1 is half-time, 2 is the final score
// used for the table. resultTypeKind is kept as a fallback for older cached responses.
const RESULT_TYPE = { halfTime: 1, final: 2 };
const LEGACY_RESULT_KIND = { 1: "HalfTime", 2: "After90Minutes" };
const MINUTE_BINS = [
  { label: "1–15", max: 15 },
  { label: "16–30", max: 30 },
  { label: "31–45+", max: 45 },
  { label: "46–60", max: 60 },
  { label: "61–75", max: 75 },
  { label: "76–90+", max: Infinity },
];

const resultsElement = document.querySelector("#results");
const matchdayTitle = document.querySelector("#matchday-title");
const matchdayDates = document.querySelector("#matchday-dates");
const matchdayStrip = document.querySelector("#matchday-strip");
const previousButton = document.querySelector("#previous-matchday");
const nextButton = document.querySelector("#next-matchday");
const currentButton = document.querySelector("#current-matchday");
const refreshButton = document.querySelector("#refresh-results");
const updatedAt = document.querySelector("#updated-at");
const leagueSeason = document.querySelector("#league-season");
const hubSeason = document.querySelector("#hub-season");
const glance = document.querySelector("#glance");
const dashboard = document.querySelector(".dashboard");
const standingsSection = document.querySelector(".standings-panel");
const standingsCaption = document.querySelector("#standings-caption");
const standingsRows = document.querySelector("#standings-rows");
const standingsLegend = document.querySelector("#standings-legend");
const filterButtons = [...document.querySelectorAll("[data-filter]")];
const venueButtons = [...document.querySelectorAll("[data-venue]")];
const teamSelect = document.querySelector("#team-select");
const insightsCaption = document.querySelector("#insights-caption");
const pointsChart = document.querySelector("#points-chart");
const pointsSummary = document.querySelector("#points-chart-summary");
const pointsTable = document.querySelector("#points-table");
const minutesChart = document.querySelector("#minutes-chart");
const minutesSummary = document.querySelector("#minutes-chart-summary");
const minutesTable = document.querySelector("#minutes-table");

const currentDate = new Date();
const season = currentDate.getMonth() >= 6
  ? currentDate.getFullYear()
  : currentDate.getFullYear() - 1;

const state = {
  matchday: 1,
  currentMatchday: null,
  filter: "all",
  venue: "all",
  teamId: readStoredTeam(),
  matches: null,
  loadedAt: 0,
  loadFailed: false,
  openMatches: new Set(),
};
let loadRequest = 0;
let refreshTimer = null;

/* ---------- Small helpers ---------- */

function seasonLabel(year) {
  return `${year}/${String(year + 1).slice(-2)}`;
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function createSvg(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

function readStoredTeam() {
  try {
    const value = Number(localStorage.getItem(TEAM_STORAGE_KEY));
    return Number.isFinite(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

function storeTeam(teamId) {
  try {
    if (teamId) localStorage.setItem(TEAM_STORAGE_KEY, String(teamId));
    else localStorage.removeItem(TEAM_STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode); following a team still works for this visit.
  }
}

function formatBerlinDate(date, options) {
  return I18N.dateFormat(date, { ...options, timeZone: BERLIN_TIME_ZONE });
}

function getBerlinDateKey(time) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BERLIN_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(time));
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

/* ---------- Match data ---------- */

function kickoffOf(match) {
  return Date.parse(match.matchDateTimeUTC ?? match.matchDateTime);
}

function matchdayOf(match) {
  return Number(match.group?.groupOrderID);
}

function teamName(team) {
  return team?.shortName || team?.teamName || "TBC";
}

function toScore(home, away) {
  if ([home, away].some((value) => value === null || value === undefined || value === "")) return null;
  const score = [Number(home), Number(away)];
  return score.every(Number.isFinite) ? score : null;
}

function getResult(match, typeId) {
  const results = Array.isArray(match.matchResults) ? match.matchResults : [];
  const result = results.find((item) => Number(item.resultTypeID) === typeId)
    ?? results.find((item) => item.resultTypeKind === LEGACY_RESULT_KIND[typeId]);
  return result ? toScore(result.pointsTeam1, result.pointsTeam2) : null;
}

function getLatestResult(match) {
  const results = Array.isArray(match.matchResults) ? match.matchResults : [];
  const latest = [...results].sort((a, b) => b.resultOrderID - a.resultOrderID)[0];
  return latest ? toScore(latest.pointsTeam1, latest.pointsTeam2) : null;
}

function getFinalScore(match) {
  if (!match.matchIsFinished) return null;
  return getResult(match, RESULT_TYPE.final) ?? getLatestResult(match);
}

function getHalfTimeScore(match) {
  return getResult(match, RESULT_TYPE.halfTime);
}

// Goals in scoring order, each tagged with the side that benefited (1 = home, 2 = away).
// OpenLigaDB gives the running score with every goal, so the side is whichever total went up.
function getGoals(match) {
  const goals = Array.isArray(match.goals) ? [...match.goals] : [];
  goals.sort((a, b) => (
    (Number(a.scoreTeam1) + Number(a.scoreTeam2)) - (Number(b.scoreTeam1) + Number(b.scoreTeam2))
    || (a.matchMinute ?? 0) - (b.matchMinute ?? 0)
  ));

  let previous = [0, 0];
  return goals.map((goal) => {
    const score = toScore(goal.scoreTeam1, goal.scoreTeam2);
    let side = null;
    if (score) {
      if (score[0] > previous[0] && score[1] === previous[1]) side = 1;
      else if (score[1] > previous[1] && score[0] === previous[0]) side = 2;
      previous = score;
    }
    if (!side && goal.scoringTeamId !== undefined && goal.scoringTeamId !== null) {
      const scorer = Number(goal.scoringTeamId);
      side = scorer === Number(match.team1?.teamId) ? 1 : scorer === Number(match.team2?.teamId) ? 2 : null;
    }
    const minute = Number(goal.matchMinute);
    return { goal, side, score, minute: goal.matchMinute !== null && Number.isFinite(minute) ? minute : null };
  });
}

function getMatchStatus(match, now = Date.now()) {
  if (match.matchIsFinished) return "finished";

  const kickoff = kickoffOf(match);
  if (!Number.isFinite(kickoff) || kickoff > now) return "upcoming";
  if (now - kickoff <= LIVE_WINDOW_MINUTES * 60_000) return "live";
  return "pending";
}

// The score to show on the card: the final result, otherwise the running score from the goals.
function getDisplayScore(match, status) {
  if (status === "finished") return getFinalScore(match);
  if (status === "upcoming") return null;
  const lastGoal = getGoals(match).at(-1);
  return lastGoal?.score ?? getLatestResult(match) ?? (status === "live" ? [0, 0] : null);
}

function matchesForMatchday(matches, matchday) {
  return matches
    .filter((match) => matchdayOf(match) === matchday)
    .sort((a, b) => kickoffOf(a) - kickoffOf(b));
}

function getMatchdayStatus(matches) {
  if (!matches.length) return "upcoming";
  const statuses = matches.map((match) => getMatchStatus(match));
  if (statuses.includes("live")) return "live";
  if (statuses.every((status) => status === "finished")) return "played";
  if (statuses.some((status) => status !== "upcoming")) return "partial";
  return "upcoming";
}

function deriveCurrentMatchday(matches) {
  const now = Date.now();
  const started = matches.filter((match) => kickoffOf(match) <= now);
  const unfinished = matches
    .filter((match) => !match.matchIsFinished)
    .sort((a, b) => kickoffOf(a) - kickoffOf(b));
  if (unfinished.length) return matchdayOf(unfinished[0]);
  return started.length ? Math.max(...started.map(matchdayOf)) : 1;
}

/* ---------- Standings and season statistics ---------- */

function calculateStandings(matches, throughMatchday, venue = "all") {
  const table = new Map();

  function getTeam(team) {
    if (!team || team.teamId === undefined || team.teamId === null) return null;
    if (!table.has(team.teamId)) {
      table.set(team.teamId, {
        team,
        played: 0,
        won: 0,
        drawn: 0,
        lost: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
        results: [],
      });
    }
    return table.get(team.teamId);
  }

  function record(entry, goalsFor, goalsAgainst, match, opponent, isHome) {
    entry.played += 1;
    entry.goalsFor += goalsFor;
    entry.goalsAgainst += goalsAgainst;
    const outcome = goalsFor > goalsAgainst ? "W" : goalsFor < goalsAgainst ? "L" : "D";
    if (outcome === "W") {
      entry.won += 1;
      entry.points += 3;
    } else if (outcome === "D") {
      entry.drawn += 1;
      entry.points += 1;
    } else {
      entry.lost += 1;
    }
    entry.results.push({ outcome, goalsFor, goalsAgainst, opponent, isHome, matchday: matchdayOf(match) });
  }

  // Seed every club so the table is complete before the first results are in.
  for (const match of matches) {
    getTeam(match.team1);
    getTeam(match.team2);
  }

  const completed = matches
    .filter((match) => {
      const matchday = matchdayOf(match);
      return match.matchIsFinished && Number.isInteger(matchday) && matchday <= throughMatchday;
    })
    .sort((a, b) => kickoffOf(a) - kickoffOf(b));

  for (const match of completed) {
    const score = getFinalScore(match);
    const home = getTeam(match.team1);
    const away = getTeam(match.team2);
    if (!score || !home || !away) continue;
    const [homeGoals, awayGoals] = score;
    if (venue !== "away") record(home, homeGoals, awayGoals, match, match.team2, true);
    if (venue !== "home") record(away, awayGoals, homeGoals, match, match.team1, false);
  }

  return [...table.values()].sort(compareStandings);
}

function compareStandings(a, b) {
  return b.points - a.points
    || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst)
    || b.goalsFor - a.goalsFor
    || teamName(a.team).localeCompare(teamName(b.team));
}

function lastCompletedMatchday(matches, throughMatchday) {
  return matches.reduce((latest, match) => {
    const matchday = matchdayOf(match);
    return match.matchIsFinished && matchday <= throughMatchday ? Math.max(latest, matchday) : latest;
  }, 0);
}

// Cumulative points and position for every club after matchdays 0..N.
function calculateProgression(matches, throughMatchday) {
  const lastMatchday = lastCompletedMatchday(matches, throughMatchday);
  const clubs = new Map();
  function getClub(team) {
    if (!team || team.teamId === undefined || team.teamId === null) return null;
    if (!clubs.has(team.teamId)) {
      clubs.set(team.teamId, {
        team,
        points: Array(lastMatchday + 1).fill(0),
        goalDifference: Array(lastMatchday + 1).fill(0),
        goalsFor: Array(lastMatchday + 1).fill(0),
        positions: Array(lastMatchday + 1).fill(null),
      });
    }
    return clubs.get(team.teamId);
  }

  for (const match of matches) {
    const home = getClub(match.team1);
    const away = getClub(match.team2);
    const matchday = matchdayOf(match);
    const score = getFinalScore(match);
    if (!home || !away || !score || matchday > lastMatchday) continue;
    const [homeGoals, awayGoals] = score;
    home.points[matchday] += homeGoals > awayGoals ? 3 : homeGoals === awayGoals ? 1 : 0;
    away.points[matchday] += awayGoals > homeGoals ? 3 : homeGoals === awayGoals ? 1 : 0;
    home.goalDifference[matchday] += homeGoals - awayGoals;
    away.goalDifference[matchday] += awayGoals - homeGoals;
    home.goalsFor[matchday] += homeGoals;
    away.goalsFor[matchday] += awayGoals;
  }

  const list = [...clubs.values()];
  for (const club of list) {
    for (let day = 1; day <= lastMatchday; day += 1) {
      club.points[day] += club.points[day - 1];
      club.goalDifference[day] += club.goalDifference[day - 1];
      club.goalsFor[day] += club.goalsFor[day - 1];
    }
  }
  for (let day = 1; day <= lastMatchday; day += 1) {
    [...list]
      .sort((a, b) => (
        b.points[day] - a.points[day]
        || b.goalDifference[day] - a.goalDifference[day]
        || b.goalsFor[day] - a.goalsFor[day]
        || teamName(a.team).localeCompare(teamName(b.team))
      ))
      .forEach((club, index) => { club.positions[day] = index + 1; });
  }
  return { lastMatchday, clubs: list };
}

function calculateGoalMinutes(matches, throughMatchday) {
  const bins = MINUTE_BINS.map((bin) => ({ ...bin, goals: 0 }));
  let total = 0;
  let unknown = 0;
  let matchesCounted = 0;
  for (const match of matches) {
    const status = getMatchStatus(match);
    if (matchdayOf(match) > throughMatchday || (status !== "finished" && status !== "live")) continue;
    matchesCounted += 1;
    for (const { minute } of getGoals(match)) {
      total += 1;
      if (minute === null) {
        unknown += 1;
        continue;
      }
      bins.find((bin) => minute <= bin.max).goals += 1;
    }
  }
  return { bins, total, unknown, matchesCounted };
}

/* ---------- Loading ---------- */

async function fetchJson(path, forceRefresh) {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: forceRefresh ? "no-cache" : "default",
  });
  if (!response.ok) throw new Error(`OpenLigaDB returned HTTP ${response.status}.`);
  return response.json();
}

async function loadSeasonMatches(forceRefresh = false) {
  const matches = await fetchJson(`/getmatchdata/${LEAGUE}/${season}`, forceRefresh);
  if (!Array.isArray(matches)) throw new Error("OpenLigaDB returned an unexpected season match list.");
  return matches;
}

async function loadCurrentMatchday() {
  const group = await fetchJson(`/getcurrentgroup/${LEAGUE}`);
  const matchday = Number(group.groupOrderID);
  if (!Number.isInteger(matchday) || matchday < 1 || matchday > MAX_MATCHDAYS) {
    throw new Error("OpenLigaDB returned an invalid current matchday.");
  }
  return matchday;
}

function setBusy(isBusy) {
  resultsElement.setAttribute("aria-busy", String(isBusy));
  standingsSection.setAttribute("aria-busy", String(isBusy));
  refreshButton.disabled = isBusy;
  refreshButton.classList.toggle("is-refreshing", isBusy);
  dashboard.classList.toggle("is-updating", isBusy && Boolean(state.matches));
}

function showLoadFailure() {
  state.loadFailed = true;
  showMessage(t("error.scores.title"), t("error.scores.text"), true);
  showStandingsMessage(t("error.standings.caption"), t("error.standings.text"));
}

// Background refreshes (live updates, returning to the tab) are quiet; the button gives feedback.
async function refresh({ forceRefresh = false, quiet = false } = {}) {
  const request = ++loadRequest;
  if (!quiet) setBusy(true);
  try {
    const matches = await loadSeasonMatches(forceRefresh);
    if (request !== loadRequest) return;
    state.matches = matches;
    state.loadedAt = Date.now();
    state.loadFailed = false;
    renderAll();
  } catch (error) {
    if (request !== loadRequest) return;
    console.error("Unable to load Bundesliga results.", error);
    if (!state.matches) {
      showLoadFailure();
    } else {
      updatedAt.textContent = t("hub.updateFailed");
    }
  } finally {
    if (request === loadRequest) {
      setBusy(false);
      scheduleRefresh();
    }
  }
}

async function start() {
  const request = ++loadRequest;
  setBusy(true);
  const requestedMatchday = Number(new URLSearchParams(location.search).get("md"));
  const [currentResult, matchesResult] = await Promise.allSettled([loadCurrentMatchday(), loadSeasonMatches()]);
  if (request !== loadRequest) return;
  setBusy(false);
  if (matchesResult.status === "rejected") {
    console.error("Unable to load Bundesliga results.", matchesResult.reason);
    showLoadFailure();
    return;
  }

  state.matches = matchesResult.value;
  state.loadedAt = Date.now();
  state.loadFailed = false;
  state.currentMatchday = currentResult.status === "fulfilled"
    ? currentResult.value
    : deriveCurrentMatchday(state.matches);
  if (currentResult.status === "rejected") {
    console.error("Unable to find the current Bundesliga matchday.", currentResult.reason);
  }
  state.matchday = Number.isInteger(requestedMatchday) && requestedMatchday >= 1 && requestedMatchday <= MAX_MATCHDAYS
    ? requestedMatchday
    : state.currentMatchday;
  renderAll();
  scrollStripToSelected("auto");
  scheduleRefresh();
}

// While matches are live, refresh every minute; otherwise wake up for the next kick-off.
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = null;
  if (!state.matches || document.visibilityState === "hidden") return;

  const now = Date.now();
  const hasLive = state.matches.some((match) => getMatchStatus(match, now) === "live");
  const nextKickoff = Math.min(...state.matches
    .map(kickoffOf)
    .filter((kickoff) => Number.isFinite(kickoff) && kickoff > now));
  const delay = hasLive ? LIVE_REFRESH_MS : nextKickoff - now + 30_000;
  if (delay <= 6 * 60 * 60_000) {
    refreshTimer = setTimeout(() => refresh({ forceRefresh: true, quiet: true }), delay);
  }
}

/* ---------- Matchday hub ---------- */

function selectMatchday(matchday) {
  if (!state.matches || matchday < 1 || matchday > MAX_MATCHDAYS || matchday === state.matchday) return;
  const stripHadFocus = matchdayStrip.contains(document.activeElement);
  state.matchday = matchday;
  const url = new URL(location.href);
  if (matchday === state.currentMatchday) url.searchParams.delete("md");
  else url.searchParams.set("md", String(matchday));
  history.replaceState(null, "", url);
  renderAll();
  scrollStripToSelected("smooth");
  if (stripHadFocus) matchdayStrip.querySelector('[aria-pressed="true"]').focus({ preventScroll: true });
}

function scrollStripToSelected(behavior) {
  const button = matchdayStrip.querySelector('[aria-pressed="true"]');
  if (!button || matchdayStrip.scrollWidth <= matchdayStrip.clientWidth) return;
  const left = button.offsetLeft - (matchdayStrip.clientWidth - button.offsetWidth) / 2;
  matchdayStrip.scrollTo({ left, behavior });
}

function renderMatchdayStrip() {
  const fragment = document.createDocumentFragment();
  for (let day = 1; day <= MAX_MATCHDAYS; day += 1) {
    const status = getMatchdayStatus(matchesForMatchday(state.matches, day));
    const button = createElement("button", `strip-day is-${status}`, String(day));
    button.type = "button";
    button.dataset.matchday = String(day);
    button.setAttribute("aria-pressed", String(day === state.matchday));
    button.tabIndex = day === state.matchday ? 0 : -1;
    if (day === state.currentMatchday) button.classList.add("is-current");
    button.setAttribute("aria-label", t(day === state.currentMatchday ? "strip.ariaCurrent" : "strip.aria", {
      matchday: day,
      status: t(`strip.${status}`),
    }));
    fragment.append(button);
  }
  matchdayStrip.replaceChildren(fragment);
}

function formatMatchdayDates(matches) {
  const kickoffs = matches.map(kickoffOf).filter(Number.isFinite);
  if (!kickoffs.length) return t("hub.datesTbc");
  const first = Math.min(...kickoffs);
  const last = Math.max(...kickoffs);
  const day = (time, withMonth) => formatBerlinDate(time, {
    weekday: "short",
    day: "numeric",
    ...(withMonth ? { month: "long" } : {}),
  });
  if (getBerlinDateKey(first) === getBerlinDateKey(last)) return day(first, true);
  const sameMonth = formatBerlinDate(first, { month: "long" }) === formatBerlinDate(last, { month: "long" });
  return `${day(first, !sameMonth)} – ${day(last, true)}`;
}

function renderHub(matches) {
  matchdayTitle.textContent = t("hub.title", { matchday: state.matchday });
  matchdayDates.textContent = formatMatchdayDates(matches);
  previousButton.disabled = state.matchday <= 1;
  nextButton.disabled = state.matchday >= MAX_MATCHDAYS;
  currentButton.hidden = !state.currentMatchday || state.matchday === state.currentMatchday;
  currentButton.textContent = t("hub.goTo", { matchday: state.currentMatchday });
  updatedAt.textContent = state.loadedAt
    ? t("hub.updated", { time: formatBerlinDate(state.loadedAt, { hour: "2-digit", minute: "2-digit" }) })
    : "";
  renderMatchdayStrip();
}

function setGlanceTile(tile, value, sub, { compact = false } = {}) {
  const valueElement = tile.querySelector(".glance-value");
  valueElement.replaceChildren(value);
  valueElement.classList.toggle("is-compact", compact && value !== "–");
  tile.querySelector(".glance-sub").textContent = sub;
}

function renderGlance(matches, standings) {
  const [goalsTile, resultsTile, winTile, leaderTile] = glance.querySelectorAll(".glance-tile");
  const now = Date.now();
  const started = matches.filter((match) => ["finished", "live"].includes(getMatchStatus(match, now)));
  const finished = matches.filter((match) => match.matchIsFinished && getFinalScore(match));
  const liveCount = started.length - finished.length;

  if (started.length) {
    const goals = started.reduce((sum, match) => {
      const score = getDisplayScore(match, getMatchStatus(match, now)) ?? [0, 0];
      return sum + score[0] + score[1];
    }, 0);
    const seasonFinished = state.matches.filter((match) => (
      match.matchIsFinished && matchdayOf(match) <= state.matchday && getFinalScore(match)
    ));
    const seasonGoals = seasonFinished.reduce((sum, match) => sum + getFinalScore(match)[0] + getFinalScore(match)[1], 0);
    const parts = [t("glance.perMatch", { avg: I18N.number(goals / started.length, 1) })];
    if (seasonFinished.length) parts.push(t("glance.season", { avg: I18N.number(seasonGoals / seasonFinished.length, 1) }));
    if (liveCount) parts.push(t("glance.live", { count: liveCount }));
    setGlanceTile(goalsTile, String(goals), parts.join(" · "));
  } else {
    setGlanceTile(goalsTile, "–", t("glance.toPlay", { matches: t("count.matches", { count: matches.length }) }));
  }

  if (finished.length) {
    let homeWins = 0;
    let draws = 0;
    let awayWins = 0;
    for (const match of finished) {
      const [home, away] = getFinalScore(match);
      if (home > away) homeWins += 1;
      else if (home < away) awayWins += 1;
      else draws += 1;
    }
    setGlanceTile(resultsTile, `${homeWins} · ${draws} · ${awayWins}`, t("glance.resultsSub"));

    const ranked = [...finished].sort((a, b) => {
      const [ah, aa] = getFinalScore(a);
      const [bh, ba] = getFinalScore(b);
      return Math.abs(bh - ba) - Math.abs(ah - aa) || (bh + ba) - (ah + aa);
    });
    const [biggestHome, biggestAway] = getFinalScore(ranked[0]);
    const margin = Math.abs(biggestHome - biggestAway);
    if (margin === 0) {
      setGlanceTile(winTile, "–", t("glance.allDraws"));
    } else {
      const sameMargin = ranked.filter((match) => {
        const [home, away] = getFinalScore(match);
        return Math.abs(home - away) === margin;
      }).length - 1;
      setGlanceTile(
        winTile,
        `${teamName(ranked[0].team1)} ${I18N.score(biggestHome, biggestAway)} ${teamName(ranked[0].team2)}`,
        t("glance.margin", { count: margin }) + (sameMargin ? t("glance.sameMargin", { count: sameMargin }) : ""),
        { compact: true },
      );
    }
  } else {
    setGlanceTile(resultsTile, "–", t("glance.noResults"));
    setGlanceTile(winTile, "–", t("glance.noResults"));
  }

  const [leader, second] = standings;
  if (leader?.played) {
    const name = createElement("span", "glance-team");
    name.append(createLogo(leader.team, "glance-logo"), createElement("span", "", teamName(leader.team)));
    const gap = leader.points - (second?.points ?? 0);
    const detail = gap
      ? t("glance.leaderClear", { points: leader.points, gap, count: gap })
      : t("glance.leaderGd", { points: leader.points });
    setGlanceTile(leaderTile, name, detail, { compact: true });
  } else {
    setGlanceTile(leaderTile, "–", t("glance.leaderNone"));
  }
}

/* ---------- Fixtures ---------- */

function createLogo(team, className) {
  const logo = document.createElement("img");
  logo.className = className;
  logo.src = team?.teamIconUrl || "";
  logo.alt = "";
  logo.loading = "lazy";
  logo.decoding = "async";
  logo.addEventListener("error", () => {
    logo.replaceWith(createElement("span", `${className} logo-fallback`, teamName(team).slice(0, 2)));
  }, { once: true });
  return logo;
}

function createTeam(team, isHome, outcome) {
  const container = createElement("span", `team ${isHome ? "team-home" : "team-away"}${outcome ? ` is-${outcome}` : ""}`);
  const name = createElement("span", "team-name", teamName(team));
  const logo = createLogo(team, "team-logo");
  container.append(isHome ? name : logo, isHome ? logo : name);
  return container;
}

function isFollowed(match) {
  return Boolean(state.teamId)
    && [Number(match.team1?.teamId), Number(match.team2?.teamId)].includes(state.teamId);
}

function createMatchCard(match) {
  const status = getMatchStatus(match);
  const score = getDisplayScore(match, status);
  const [homeScore, awayScore] = score ?? [];
  const decided = status === "finished" && score;
  const homeOutcome = decided ? (homeScore > awayScore ? "winner" : homeScore < awayScore ? "loser" : "") : "";
  const awayOutcome = decided ? (awayScore > homeScore ? "winner" : awayScore < homeScore ? "loser" : "") : "";
  const kickoff = kickoffOf(match);
  const time = formatBerlinDate(kickoff, { hour: "2-digit", minute: "2-digit" });

  const card = createElement("details", `match-card is-${status}${isFollowed(match) ? " is-followed" : ""}`);
  card.dataset.matchId = String(match.matchID);
  card.open = state.openMatches.has(String(match.matchID));
  card.addEventListener("toggle", () => {
    if (card.open) state.openMatches.add(card.dataset.matchId);
    else state.openMatches.delete(card.dataset.matchId);
  });

  const summary = createElement("summary", "match-summary");
  const scoreBlock = createElement("span", "score-block");
  if (score) {
    const scoreLine = createElement("span", "score");
    scoreLine.append(
      createElement("span", homeOutcome === "winner" ? "score-winner" : "", String(homeScore)),
      createElement("span", "score-separator", I18N.scoreSeparator),
      createElement("span", awayOutcome === "winner" ? "score-winner" : "", String(awayScore)),
    );
    scoreBlock.append(scoreLine);
  } else {
    scoreBlock.append(createElement("span", "match-time", time));
  }

  const halfTime = getHalfTimeScore(match);
  const statusText = {
    finished: halfTime ? t("match.fullTimeHt", { score: I18N.score(halfTime[0], halfTime[1]) }) : t("match.fullTime"),
    live: halfTime ? t("match.liveSecondHalf") : t("match.live"),
    pending: t("match.pending"),
    upcoming: Number.isFinite(kickoff) ? t("match.kickoff") : t("match.dateTbc"),
  }[status];
  scoreBlock.append(createElement("span", "match-status", statusText));

  summary.append(
    createTeam(match.team1, true, homeOutcome),
    scoreBlock,
    createTeam(match.team2, false, awayOutcome),
    createElement("span", "visually-hidden", t("match.showDetails")),
  );
  card.append(summary, createMatchDetails(match, status, time));
  return card;
}

function createMatchDetails(match, status, kickoffTime) {
  const details = createElement("div", "match-details");
  const kickoff = kickoffOf(match);
  const meta = createElement("p", "match-detail-meta");
  const metaParts = [];
  if (Number.isFinite(kickoff)) {
    metaParts.push(`${formatBerlinDate(kickoff, { weekday: "long", day: "numeric", month: "long", year: "numeric" })} · ${kickoffTime}`);
  }
  const venue = [match.location?.locationStadium, match.location?.locationCity].filter(Boolean).join(", ");
  if (venue) metaParts.push(venue);
  const viewers = Number(match.numberOfViewers);
  if (viewers > 0) metaParts.push(t("match.spectators", { viewers: I18N.number(viewers) }));
  meta.textContent = metaParts.join(" · ");
  details.append(meta);

  const goals = getGoals(match);
  if (goals.length) {
    details.append(createElement("h3", "match-events-heading", t("match.goals")));
    const timeline = createElement("ol", "goal-timeline");
    for (const { goal, side, score, minute } of goals) {
      const event = createElement("li", `goal-event${side === 2 ? " is-away" : side === 1 ? " is-home" : ""}`);
      const notes = [goal.isOwnGoal ? t("match.ownGoal") : "", goal.isPenalty ? t("match.penalty") : ""].filter(Boolean);
      const scorer = createElement("span", "goal-scorer");
      scorer.append(
        createElement("span", "", goal.goalGetterName || t("match.unknownScorer")),
        ...(notes.length ? [createElement("span", "goal-note", ` (${notes.join(", ")})`)] : []),
      );
      const team = side === 1 ? match.team1 : side === 2 ? match.team2 : null;
      if (team) scorer.append(createElement("span", "visually-hidden", t("match.scoredFor", { team: teamName(team) })));
      const centre = createElement("span", "goal-centre");
      centre.append(
        createElement("span", "goal-minute", minute === null ? "•" : `${minute}${goal.isOvertime ? "+" : ""}′`),
        createElement("span", "goal-score", score ? I18N.score(score[0], score[1]) : ""),
      );
      const homeSlot = createElement("span", "goal-side goal-side-home");
      const awaySlot = createElement("span", "goal-side goal-side-away");
      (side === 2 ? awaySlot : homeSlot).append(scorer);
      event.append(homeSlot, centre, awaySlot);
      timeline.append(event);
    }
    details.append(timeline);
  } else {
    const message = {
      finished: getFinalScore(match)?.every((count) => count === 0) ? t("match.noGoals.goalless") : t("match.noGoals.unavailable"),
      live: t("match.noGoals.live"),
      pending: t("match.noGoals.pending"),
      upcoming: t("match.noGoals.upcoming"),
    }[status];
    details.append(createElement("p", "no-goals-message", message));
  }

  return details;
}

function matchesFilter(match, filter) {
  const status = getMatchStatus(match);
  if (filter === "all") return true;
  if (filter === "upcoming") return status === "upcoming" || status === "pending";
  return status === filter;
}

function renderFilterCounts(matches) {
  for (const button of filterButtons) {
    const count = matches.filter((match) => matchesFilter(match, button.dataset.filter)).length;
    button.querySelector(".chip-count").textContent = String(count);
    button.classList.toggle("is-empty", count === 0);
  }
}

function showMessage(title, message, action) {
  const box = createElement("div", action === true ? "error-state" : "empty-state");
  box.append(createElement("strong", "", title), createElement("p", "", message));
  if (action) {
    const button = createElement("button", "", action === true ? t("error.retry") : action.label);
    button.type = "button";
    button.addEventListener("click", action === true ? () => start() : action.onClick);
    box.append(button);
  }
  resultsElement.replaceChildren(box);
}

function renderMatches(matches) {
  renderFilterCounts(matches);
  const filteredMatches = matches.filter((match) => matchesFilter(match, state.filter));

  if (!filteredMatches.length) {
    if (!matches.length) {
      showMessage(t("empty.noMatches.title"), t("empty.noMatches.text"));
    } else {
      const params = { matchday: state.matchday };
      showMessage(t(`empty.${state.filter}.title`), t(`empty.${state.filter}.text`, params), {
        label: t("empty.showAll"),
        onClick: () => setFilter("all"),
      });
    }
    return;
  }

  const groups = new Map();
  for (const match of filteredMatches) {
    const kickoff = kickoffOf(match);
    const dateKey = Number.isFinite(kickoff) ? getBerlinDateKey(kickoff) : "tbc";
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey).push(match);
  }

  const fragment = document.createDocumentFragment();
  for (const [dateKey, group] of groups) {
    const dateGroup = createElement("section", "date-group");
    const heading = createElement("h3", "date-heading");
    heading.append(
      createElement("span", "", dateKey === "tbc"
        ? t("match.dateTbc")
        : formatBerlinDate(kickoffOf(group[0]), { weekday: "long", day: "numeric", month: "long" })),
      createElement("span", "date-count", t("count.matches", { count: group.length })),
    );
    dateGroup.append(heading, ...group.map(createMatchCard));
    fragment.append(dateGroup);
  }
  resultsElement.replaceChildren(fragment);
}

function setFilter(filter) {
  state.filter = filter;
  filterButtons.forEach((button) => {
    const isActive = button.dataset.filter === filter;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
  renderMatches(matchesForMatchday(state.matches ?? [], state.matchday));
}

/* ---------- Standings ---------- */

function getZone(index, size) {
  if (size !== 18) return "";
  if (index < 4) return "zone-champions";
  if (index === 4) return "zone-europa";
  if (index === 5) return "zone-conference";
  if (index === 15) return "zone-playoff";
  return index >= 16 ? "zone-relegation" : "";
}

function createForm(results) {
  const recent = results.slice(-5);
  const list = createElement("span", "form-list");
  const words = { W: t("form.win"), D: t("form.draw"), L: t("form.loss") };
  list.setAttribute("aria-label", recent.length
    ? t("form.aria", { count: recent.length, results: recent.map((result) => words[result.outcome]).join(", ") })
    : t("form.none"));
  for (const result of recent) {
    const pill = createElement("span", `form-pill is-${result.outcome.toLowerCase()}`, t(`form.${result.outcome}`));
    pill.title = t(result.isHome ? "form.titleHome" : "form.titleAway", {
      matchday: result.matchday,
      score: I18N.score(result.goalsFor, result.goalsAgainst),
      opponent: teamName(result.opponent),
    });
    pill.setAttribute("aria-hidden", "true");
    list.append(pill);
  }
  return list;
}

function createMovement(change) {
  if (!change) return createElement("span", "movement is-same", "");
  const movement = createElement("span", `movement ${change > 0 ? "is-up" : "is-down"}`, change > 0 ? "▲" : "▼");
  const places = { count: Math.abs(change) };
  movement.title = t(change > 0 ? "table.up" : "table.down", { ...places, matchday: state.matchday - 1 });
  movement.append(createElement("span", "visually-hidden", t(change > 0 ? "table.upSr" : "table.downSr", places)));
  return movement;
}

function renderStandings(table) {
  const venueLabel = { all: "", home: t("table.venue.home"), away: t("table.venue.away") }[state.venue];
  const matchdayMatches = matchesForMatchday(state.matches, state.matchday);
  const toFinish = matchdayMatches.filter((match) => !match.matchIsFinished).length;
  const started = matchdayMatches.some((match) => getMatchStatus(match) !== "upcoming");
  let progress = "";
  if (toFinish && !started) progress = t("table.progressNone");
  else if (toFinish) progress = t("table.progressPending", { count: toFinish });
  standingsCaption.textContent = t("table.caption", { venue: venueLabel, matchday: state.matchday, progress });
  document.querySelector("#standings-table-caption").textContent = t(`table.ariaCaption.${state.venue}`, { matchday: state.matchday });
  standingsLegend.hidden = state.venue !== "all";

  if (!table.length) {
    showStandingsMessage(standingsCaption.textContent, t("table.empty"));
    return;
  }

  const previous = state.venue === "all" && state.matchday > 1
    ? new Map(calculateStandings(state.matches, state.matchday - 1).map((entry, index) => [entry.team.teamId, index]))
    : null;

  const fragment = document.createDocumentFragment();
  table.forEach((standing, index) => {
    const followed = Number(standing.team.teamId) === state.teamId;
    const row = createElement("tr", [
      state.venue === "all" ? getZone(index, table.length) : "",
      followed ? "is-followed" : "",
    ].filter(Boolean).join(" "));

    const position = createElement("td", "position-column");
    position.append(createElement("span", "position-number", String(index + 1)));
    if (previous?.has(standing.team.teamId)) position.append(createMovement(previous.get(standing.team.teamId) - index));

    const clubCell = createElement("td", "club-column");
    const club = createElement("button", "club-button");
    club.type = "button";
    club.setAttribute("aria-pressed", String(followed));
    club.title = t(followed ? "table.unfollow" : "table.follow", { team: teamName(standing.team) });
    club.dataset.teamId = String(standing.team.teamId);
    club.append(createLogo(standing.team, "standing-logo"), createElement("span", "standing-name", teamName(standing.team)));
    club.addEventListener("click", () => {
      setFollowedTeam(followed ? null : Number(standing.team.teamId));
      standingsRows.querySelector(`[data-team-id="${club.dataset.teamId}"]`)?.focus();
    });
    clubCell.append(club);

    const goalDifference = standing.goalsFor - standing.goalsAgainst;
    const formCell = createElement("td", "form-column");
    formCell.append(createForm(standing.results));
    row.append(
      position,
      clubCell,
      createElement("td", "", String(standing.played)),
      createElement("td", "detail-column", String(standing.won)),
      createElement("td", "detail-column", String(standing.drawn)),
      createElement("td", "detail-column", String(standing.lost)),
      createElement("td", "detail-column goal-total", `${standing.goalsFor}:${standing.goalsAgainst}`),
      createElement("td", "", `${goalDifference > 0 ? "+" : ""}${goalDifference}`),
      createElement("td", "points-column", String(standing.points)),
      formCell,
    );
    fragment.append(row);
  });
  standingsRows.replaceChildren(fragment);
}

function showStandingsMessage(caption, message) {
  standingsCaption.textContent = caption;
  const row = createElement("tr");
  const cell = createElement("td", "standings-message", message);
  cell.colSpan = 10;
  row.append(cell);
  standingsRows.replaceChildren(row);
}

function setVenue(venue) {
  state.venue = venue;
  venueButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.venue === venue)));
  if (state.matches) renderStandings(calculateStandings(state.matches, state.matchday, venue));
}

/* ---------- Following a club ---------- */

function setFollowedTeam(teamId) {
  state.teamId = teamId;
  storeTeam(teamId);
  renderAll();
}

function renderTeamSelect(clubs) {
  const options = [createElement("option", "", t("insights.followTop"))];
  options[0].value = "";
  for (const club of [...clubs].sort((a, b) => teamName(a.team).localeCompare(teamName(b.team)))) {
    const option = createElement("option", "", teamName(club.team));
    option.value = String(club.team.teamId);
    options.push(option);
  }
  teamSelect.replaceChildren(...options);
  teamSelect.value = state.teamId && clubs.some((club) => Number(club.team.teamId) === state.teamId)
    ? String(state.teamId)
    : "";
}

/* ---------- Charts ---------- */

function niceStep(max) {
  if (max <= 12) return 3;
  if (max <= 30) return 5;
  return 10;
}

function createTooltip(container) {
  const tooltip = createElement("div", "chart-tooltip");
  tooltip.hidden = true;
  container.append(tooltip);
  return tooltip;
}

function placeTooltip(container, tooltip, x, y) {
  tooltip.hidden = false;
  const maxLeft = container.clientWidth - tooltip.offsetWidth - 4;
  const left = x + 14 + tooltip.offsetWidth > container.clientWidth ? x - tooltip.offsetWidth - 14 : x + 14;
  tooltip.style.left = `${Math.max(4, Math.min(maxLeft, left))}px`;
  tooltip.style.top = `${Math.max(4, y - tooltip.offsetHeight / 2)}px`;
}

function tooltipRow(value, label, keyClass) {
  const row = createElement("span", "tooltip-row");
  if (keyClass) row.append(createElement("span", `tooltip-key ${keyClass}`));
  row.append(createElement("strong", "", value), createElement("span", "", label));
  return row;
}

function renderPointsChart(progression) {
  const { lastMatchday, clubs } = progression;
  pointsChart.replaceChildren();
  if (!lastMatchday) {
    pointsChart.append(createElement("p", "chart-empty", t("chart.points.empty")));
    pointsSummary.textContent = t("chart.points.default");
    pointsTable.replaceChildren();
    return;
  }

  const ranked = [...clubs].sort((a, b) => a.positions[lastMatchday] - b.positions[lastMatchday]);
  const focus = clubs.find((club) => Number(club.team.teamId) === state.teamId) ?? ranked[0];
  const leader = ranked[0];
  const width = Math.max(280, pointsChart.clientWidth);
  const height = width < 480 ? 240 : 290;
  const margin = { top: 14, right: Math.min(110, Math.max(78, teamName(focus.team).length * 8 + 34)), bottom: 26, left: 30 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maxPoints = Math.max(...clubs.map((club) => club.points[lastMatchday]), 1);
  const step = niceStep(maxPoints);
  const yMax = Math.ceil(maxPoints / step) * step;
  const x = (day) => margin.left + (day / lastMatchday) * plotWidth;
  const y = (points) => margin.top + plotHeight - (points / yMax) * plotHeight;

  const chartSvg = createSvg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true" });
  const grid = createSvg("g", { class: "chart-grid" });
  for (let value = 0; value <= yMax; value += step) {
    grid.append(createSvg("line", { x1: margin.left, x2: margin.left + plotWidth, y1: y(value), y2: y(value), class: value === 0 ? "chart-baseline" : "" }));
    const label = createSvg("text", { x: margin.left - 8, y: y(value), class: "chart-tick", "text-anchor": "end", "dominant-baseline": "middle" });
    label.textContent = String(value);
    grid.append(label);
  }
  const labelEvery = Math.max(1, Math.ceil(lastMatchday / Math.floor(plotWidth / 34)));
  for (let day = 1; day <= lastMatchday; day += 1) {
    if (day % labelEvery !== 0 && day !== lastMatchday) continue;
    const label = createSvg("text", { x: x(day), y: height - 8, class: "chart-tick", "text-anchor": "middle" });
    label.textContent = String(day);
    grid.append(label);
  }
  chartSvg.append(grid);

  const line = (club) => club.points.map((points, day) => `${day ? "L" : "M"}${x(day).toFixed(1)},${y(points).toFixed(1)}`).join("");
  const others = createSvg("g", { class: "chart-context" });
  for (const club of clubs) {
    if (club !== focus) others.append(createSvg("path", { d: line(club) }));
  }
  chartSvg.append(others);
  chartSvg.append(createSvg("path", { d: line(focus), class: "chart-focus-line" }));
  const endPoints = focus.points[lastMatchday];
  chartSvg.append(createSvg("circle", { cx: x(lastMatchday), cy: y(endPoints), r: 4.5, class: "chart-focus-dot" }));
  const endLabel = createSvg("text", { x: x(lastMatchday) + 10, y: y(endPoints), class: "chart-end-label", "dominant-baseline": "middle" });
  endLabel.textContent = `${teamName(focus.team)} ${endPoints}`;
  chartSvg.append(endLabel);

  const crosshair = createSvg("line", { y1: margin.top, y2: margin.top + plotHeight, class: "chart-crosshair", visibility: "hidden" });
  const hoverDot = createSvg("circle", { r: 4.5, class: "chart-focus-dot", visibility: "hidden" });
  chartSvg.append(crosshair, hoverDot);

  const frame = createElement("div", "chart-frame");
  frame.tabIndex = 0;
  frame.setAttribute("role", "group");
  frame.setAttribute("aria-label", t("chart.points.aria", { team: teamName(focus.team) }));
  frame.append(chartSvg);
  pointsChart.append(frame);
  const tooltip = createTooltip(frame);
  tooltip.setAttribute("aria-live", "polite");

  let activeDay = null;
  function showDay(day) {
    activeDay = day;
    const points = focus.points[day];
    const position = focus.positions[day];
    crosshair.setAttribute("x1", x(day));
    crosshair.setAttribute("x2", x(day));
    crosshair.setAttribute("visibility", "visible");
    hoverDot.setAttribute("cx", x(day));
    hoverDot.setAttribute("cy", y(points));
    hoverDot.setAttribute("visibility", "visible");
    const dayLeader = clubs.find((club) => club.positions[day] === 1);
    const rows = [createElement("span", "tooltip-title", day ? t("chart.points.after", { matchday: day }) : t("chart.points.start"))];
    const placing = position ? ` · ${t("chart.points.position", { n: position, ord: I18N.ordinal(position) })}` : "";
    rows.push(tooltipRow(t("chart.points.pts", { points }), `${teamName(focus.team)}${placing}`, "is-focus"));
    if (day && dayLeader && dayLeader !== focus) {
      rows.push(tooltipRow(
        t("chart.points.pts", { points: dayLeader.points[day] }),
        t("chart.points.leader", { team: teamName(dayLeader.team) }),
        "is-context",
      ));
    }
    tooltip.replaceChildren(...rows);
    placeTooltip(frame, tooltip, x(day), y(points));
  }
  function hide() {
    activeDay = null;
    tooltip.hidden = true;
    crosshair.setAttribute("visibility", "hidden");
    hoverDot.setAttribute("visibility", "hidden");
  }
  frame.addEventListener("pointermove", (event) => {
    const bounds = chartSvg.getBoundingClientRect();
    const day = Math.round(((event.clientX - bounds.left - margin.left) / plotWidth) * lastMatchday);
    showDay(Math.max(0, Math.min(lastMatchday, day)));
  });
  frame.addEventListener("pointerleave", hide);
  frame.addEventListener("blur", hide);
  frame.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const from = activeDay ?? lastMatchday;
    const next = { ArrowLeft: from - 1, ArrowRight: from + 1, Home: 0, End: lastMatchday }[event.key];
    showDay(Math.max(0, Math.min(lastMatchday, next)));
  });

  const isLeader = focus === leader;
  const gap = isLeader
    ? leader.points[lastMatchday] - (ranked[1]?.points[lastMatchday] ?? 0)
    : leader.points[lastMatchday] - focus.points[lastMatchday];
  const summary = { team: teamName(focus.team), matchday: lastMatchday, count: gap };
  if (isLeader) {
    pointsSummary.textContent = t(gap ? "chart.points.leadClear" : "chart.points.leadGd", summary);
  } else {
    const rank = focus.positions[lastMatchday];
    pointsSummary.textContent = t("chart.points.behind", {
      ...summary,
      position: t("chart.points.position", { n: rank, ord: I18N.ordinal(rank) }),
      leader: teamName(leader.team),
    });
  }

  renderPointsTable(ranked, lastMatchday, focus);
}

function renderPointsTable(ranked, lastMatchday, focus) {
  const table = createElement("table", "data-table");
  const head = createElement("tr");
  head.append(createElement("th", "", t("chart.points.colClub")));
  for (let day = 1; day <= lastMatchday; day += 1) head.append(createElement("th", "", t("chart.points.colMatchday", { matchday: day })));
  const thead = createElement("thead");
  thead.append(head);
  const tbody = createElement("tbody");
  for (const club of ranked) {
    const row = createElement("tr", club === focus ? "is-followed" : "");
    const name = createElement("th", "", teamName(club.team));
    name.scope = "row";
    row.append(name, ...club.points.slice(1).map((points) => createElement("td", "", String(points))));
    tbody.append(row);
  }
  table.append(thead, tbody);
  pointsTable.replaceChildren(table);
}

function renderMinutesChart({ bins, total, unknown, matchesCounted }) {
  minutesChart.replaceChildren();
  if (!total) {
    minutesChart.append(createElement("p", "chart-empty", t("chart.minutes.empty")));
    minutesSummary.textContent = t("chart.minutes.default");
    minutesTable.replaceChildren();
    return;
  }

  const width = Math.max(260, minutesChart.clientWidth);
  const height = width < 480 ? 220 : 250;
  const margin = { top: 22, right: 8, bottom: 30, left: 8 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const slot = plotWidth / bins.length;
  const barWidth = Math.min(24, slot * 0.6);
  const maxGoals = Math.max(...bins.map((bin) => bin.goals), 1);
  const y = (goals) => margin.top + plotHeight - (goals / maxGoals) * plotHeight;
  const busiest = bins.reduce((best, bin) => (bin.goals > best.goals ? bin : best), bins[0]);

  const chartSvg = createSvg("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  chartSvg.setAttribute("role", "group");
  chartSvg.setAttribute("aria-label", t("chart.minutes.aria"));
  const baseline = margin.top + plotHeight;
  chartSvg.append(createSvg("line", { x1: margin.left, x2: width - margin.right, y1: baseline, y2: baseline, class: "chart-baseline" }));
  const halfTime = margin.left + slot * 3;
  chartSvg.append(createSvg("line", { x1: halfTime, x2: halfTime, y1: margin.top - 6, y2: baseline, class: "chart-divider" }));
  const halfTimeLabel = createSvg("text", { x: halfTime, y: margin.top - 10, class: "chart-tick", "text-anchor": "middle" });
  halfTimeLabel.textContent = t("chart.minutes.halfTime");
  chartSvg.append(halfTimeLabel);

  const frame = createElement("div", "chart-frame");
  frame.append(chartSvg);
  minutesChart.append(frame);
  const tooltip = createTooltip(frame);

  bins.forEach((bin, index) => {
    const centre = margin.left + slot * index + slot / 2;
    const top = y(bin.goals);
    const barHeight = baseline - top;
    const radius = Math.min(4, barHeight);
    const group = createSvg("g", { class: `chart-bar${bin === busiest ? " is-peak" : ""}`, tabindex: 0, role: "img" });
    const share = I18N.percent(Math.round((bin.goals / (total - unknown || 1)) * 100) / 100);
    group.setAttribute("aria-label", t("chart.minutes.bar", { label: bin.label, count: bin.goals, share }));
    group.append(createSvg("rect", { x: centre - slot / 2, y: margin.top, width: slot, height: plotHeight, class: "chart-hit" }));
    if (barHeight > 0) {
      const left = centre - barWidth / 2;
      const right = centre + barWidth / 2;
      group.append(createSvg("path", {
        class: "chart-bar-fill",
        d: `M${left},${baseline}V${top + radius}Q${left},${top} ${left + radius},${top}H${right - radius}Q${right},${top} ${right},${top + radius}V${baseline}Z`,
      }));
    }
    const value = createSvg("text", { x: centre, y: top - 6, class: "chart-value", "text-anchor": "middle" });
    value.textContent = String(bin.goals);
    const label = createSvg("text", { x: centre, y: height - 10, class: "chart-tick", "text-anchor": "middle" });
    label.textContent = bin.label;
    group.append(value, label);
    const show = () => {
      tooltip.replaceChildren(
        createElement("span", "tooltip-title", t("chart.minutes.range", { label: bin.label })),
        tooltipRow(String(bin.goals), t("chart.minutes.tooltip", { count: bin.goals, share }), "is-bar"),
      );
      placeTooltip(frame, tooltip, centre, top);
    };
    group.addEventListener("pointerenter", show);
    group.addEventListener("focus", show);
    group.addEventListener("pointerleave", () => { tooltip.hidden = true; });
    group.addEventListener("blur", () => { tooltip.hidden = true; });
    chartSvg.append(group);
  });

  minutesSummary.textContent = t("chart.minutes.summary", {
    goals: t("count.goals", { count: total }),
    matches: t("count.matchesIn", { count: matchesCounted }),
    avg: I18N.number(total / matchesCounted, 1),
    label: busiest.label.replace("–", "–\u2060"),
  }) + (unknown ? t("chart.minutes.unknown", { count: unknown }) : "");

  const table = createElement("table", "data-table");
  const head = createElement("tr");
  head.append(
    createElement("th", "", t("chart.minutes.colMinutes")),
    createElement("th", "", t("chart.minutes.colGoals")),
    createElement("th", "", t("chart.minutes.colShare")),
  );
  const thead = createElement("thead");
  thead.append(head);
  const tbody = createElement("tbody");
  for (const bin of bins) {
    const row = createElement("tr");
    const label = createElement("th", "", bin.label);
    label.scope = "row";
    const binShare = I18N.percent(Math.round((bin.goals / (total - unknown || 1)) * 100) / 100);
    row.append(label, createElement("td", "", String(bin.goals)), createElement("td", "", binShare));
    tbody.append(row);
  }
  table.append(thead, tbody);
  minutesTable.replaceChildren(table);
}

function renderCharts(progression = calculateProgression(state.matches, state.matchday)) {
  renderPointsChart(progression);
  renderMinutesChart(calculateGoalMinutes(state.matches, state.matchday));
}

function renderInsights() {
  const progression = calculateProgression(state.matches, state.matchday);
  insightsCaption.textContent = progression.lastMatchday
    ? t("insights.eyebrowThrough", { matchday: progression.lastMatchday })
    : t("insights.eyebrow");
  renderTeamSelect(progression.clubs);
  renderCharts(progression);
}

/* ---------- Rendering ---------- */

function renderAll() {
  if (!state.matches) return;
  const matches = matchesForMatchday(state.matches, state.matchday);
  const overall = calculateStandings(state.matches, state.matchday);
  renderHub(matches);
  renderGlance(matches, overall);
  renderMatches(matches);
  renderStandings(state.venue === "all" ? overall : calculateStandings(state.matches, state.matchday, state.venue));
  renderInsights();
}

/* ---------- Events ---------- */

leagueSeason.textContent = `Bundesliga ${seasonLabel(season)}`;
hubSeason.textContent = `Bundesliga ${seasonLabel(season)}`;
previousButton.addEventListener("click", () => selectMatchday(state.matchday - 1));
nextButton.addEventListener("click", () => selectMatchday(state.matchday + 1));
currentButton.addEventListener("click", () => selectMatchday(state.currentMatchday));
matchdayStrip.addEventListener("click", (event) => {
  const button = event.target.closest("[data-matchday]");
  if (button) selectMatchday(Number(button.dataset.matchday));
});
matchdayStrip.addEventListener("keydown", (event) => {
  const next = {
    ArrowLeft: state.matchday - 1,
    ArrowRight: state.matchday + 1,
    Home: 1,
    End: MAX_MATCHDAYS,
  }[event.key];
  if (next === undefined) return;
  event.preventDefault();
  selectMatchday(next);
});
refreshButton.addEventListener("click", () => refresh({ forceRefresh: true }));
filterButtons.forEach((button) => button.addEventListener("click", () => setFilter(button.dataset.filter)));
venueButtons.forEach((button) => button.addEventListener("click", () => setVenue(button.dataset.venue)));
teamSelect.addEventListener("change", () => setFollowedTeam(teamSelect.value ? Number(teamSelect.value) : null));

// i18n.js has already swapped the static text; redraw everything built from match data.
// Open match cards stay open (state.openMatches) and no new request is made.
I18N.onChange(() => {
  if (state.matches) renderAll();
  else if (state.loadFailed) showLoadFailure();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    clearTimeout(refreshTimer);
  } else if (state.matches && Date.now() - state.loadedAt > STALE_AFTER_MS) {
    refresh({ forceRefresh: true, quiet: true });
  } else {
    scheduleRefresh();
  }
});

let resizeFrame = null;
let chartWidth = 0;
const chartObserver = new ResizeObserver(([entry]) => {
  const width = Math.round(entry.contentRect.width);
  if (width === chartWidth) return;
  chartWidth = width;
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => { if (state.matches) renderCharts(); });
});
chartObserver.observe(document.querySelector(".insights-grid"));

const installHint = document.querySelector("#install-hint");
const isAppleMobile = /iPad|iPhone|iPod/.test(navigator.userAgent)
  || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const isInstalled = navigator.standalone || window.matchMedia("(display-mode: standalone)").matches;
installHint.hidden = !isAppleMobile || isInstalled;

start();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js")
      .catch((error) => console.error("Unable to enable offline app support.", error));
  });
}
