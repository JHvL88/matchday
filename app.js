const API_BASE = "https://api.openligadb.de";
const LEAGUE = "bl1";
const MAX_MATCHDAYS = 34;
const LIVE_WINDOW_MINUTES = 180;
const BERLIN_TIME_ZONE = "Europe/Berlin";

const resultsElement = document.querySelector("#results");
const matchdayTitle = document.querySelector("#matchday-title");
const matchdaySelect = document.querySelector("#matchday-select");
const previousButton = document.querySelector("#previous-matchday");
const nextButton = document.querySelector("#next-matchday");
const refreshButton = document.querySelector("#refresh-results");
const leagueSeason = document.querySelector("#league-season");
const standingsSection = document.querySelector(".standings-panel");
const standingsCaption = document.querySelector("#standings-caption");
const standingsRows = document.querySelector("#standings-rows");
const filterButtons = [...document.querySelectorAll("[data-filter]")];

const currentDate = new Date();
const season = currentDate.getMonth() >= 6
  ? currentDate.getFullYear()
  : currentDate.getFullYear() - 1;
let selectedMatchday = 1;
let activeFilter = "all";
let currentMatches = [];
let seasonMatches = null;
let loadRequest = 0;

function seasonLabel(year) {
  return `${year}/${String(year + 1).slice(-2)}`;
}

function getScore(match) {
  const results = Array.isArray(match.matchResults) ? match.matchResults : [];
  const finalResult = results.find((result) => result.resultTypeKind === "After90Minutes")
    ?? [...results].sort((a, b) => b.resultOrderID - a.resultOrderID)[0];

  return finalResult
    ? [finalResult.pointsTeam1, finalResult.pointsTeam2]
    : null;
}

function getHalfTimeScore(match) {
  const result = match.matchResults?.find((item) => item.resultTypeKind === "HalfTime");
  return result ? [result.pointsTeam1, result.pointsTeam2] : null;
}

function getMatchStatus(match, now = Date.now()) {
  if (match.matchIsFinished) return "finished";

  const kickoff = Date.parse(match.matchDateTimeUTC ?? match.matchDateTime);
  if (!Number.isFinite(kickoff) || kickoff > now) return "upcoming";
  if (now - kickoff <= LIVE_WINDOW_MINUTES * 60_000) return "live";
  return "pending";
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setLoading(isLoading) {
  resultsElement.setAttribute("aria-busy", String(isLoading));
  standingsSection.setAttribute("aria-busy", String(isLoading));
  refreshButton.disabled = isLoading;
  refreshButton.classList.toggle("is-refreshing", isLoading);
  previousButton.disabled = isLoading || selectedMatchday <= 1;
  nextButton.disabled = isLoading || selectedMatchday >= MAX_MATCHDAYS;
  matchdaySelect.disabled = isLoading;
}

function showMessage(title, message, canRetry = false) {
  const state = createElement("div", canRetry ? "error-state" : "empty-state");
  state.append(
    createElement("strong", "", title),
    createElement("p", "", message),
  );

  if (canRetry) {
    const retryButton = createElement("button", "", "Try again");
    retryButton.type = "button";
    retryButton.addEventListener("click", loadSelectedMatchday);
    state.append(retryButton);
  }

  resultsElement.replaceChildren(state);
}

function formatBerlinDate(dateString, options) {
  return new Intl.DateTimeFormat("en-GB", {
    ...options,
    timeZone: BERLIN_TIME_ZONE,
  }).format(new Date(dateString));
}

function getMatchDateKey(match) {
  const date = new Date(match.matchDateTimeUTC ?? match.matchDateTime);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BERLIN_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function createTeam(team, isHome, isWinner) {
  const container = createElement("span", `team ${isHome ? "team-home" : "team-away"}`);
  const name = createElement("span", "team-name", team.shortName || team.teamName || "TBC");

  const logo = document.createElement("img");
  logo.className = "team-logo";
  logo.src = team.teamIconUrl || "";
  logo.alt = "";
  logo.loading = "lazy";
  logo.addEventListener("error", () => {
    logo.replaceWith(createElement("span", "team-fallback", (team.shortName || team.teamName || "?").slice(0, 2)));
  }, { once: true });

  if (isWinner) name.style.color = "#17241c";
  container.append(isHome ? name : logo, isHome ? logo : name);
  return container;
}

function createMatchCard(match) {
  const card = createElement("details", "match-card");
  const summary = createElement("summary", "match-summary");
  const score = getScore(match);
  const status = getMatchStatus(match);
  const [homeScore, awayScore] = score ?? [];
  const homeWon = score && homeScore > awayScore;
  const awayWon = score && awayScore > homeScore;
  const time = formatBerlinDate(match.matchDateTimeUTC ?? match.matchDateTime, {
    hour: "2-digit",
    minute: "2-digit",
  });

  summary.append(
    createTeam(match.team1 ?? {}, true, homeWon),
    createElement("span", "visually-hidden", "Toggle match details"),
  );

  const scoreBlock = createElement("span", "score-block");
  if (score) {
    const scoreLine = createElement("span", "score");
    const home = createElement("span", homeWon ? "score-winner" : "", String(homeScore));
    const separator = createElement("span", "score-separator", "–");
    const away = createElement("span", awayWon ? "score-winner" : "", String(awayScore));
    scoreLine.append(home, separator, away);
    scoreBlock.append(scoreLine);
  } else {
    scoreBlock.append(createElement("span", "match-time", time));
  }

  const statusLabel = status === "finished"
    ? "FULL TIME"
    : status === "live"
      ? "IN PROGRESS"
      : status === "pending"
        ? "RESULT PENDING"
        : "KICK-OFF";
  const statusElement = createElement("span", `match-status${status === "live" ? " is-live" : ""}${status === "finished" ? " is-finished" : ""}`, statusLabel);
  scoreBlock.append(statusElement);
  summary.append(scoreBlock, createTeam(match.team2 ?? {}, false, awayWon));
  card.append(summary, createMatchDetails(match, status, time));
  return card;
}

function createMatchDetails(match, status, kickoffTime) {
  const details = createElement("div", "match-details");
  const kickoff = formatBerlinDate(match.matchDateTimeUTC ?? match.matchDateTime, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const meta = createElement("p", "match-detail-meta", `${kickoff} · ${kickoffTime} · Europe/Berlin`);
  details.append(meta);

  const halfTimeScore = getHalfTimeScore(match);
  if (halfTimeScore) {
    details.append(createElement(
      "p",
      "half-time-result",
      `Half-time: ${match.team1?.shortName || match.team1?.teamName || "Home"} ${halfTimeScore[0]}–${halfTimeScore[1]} ${match.team2?.shortName || match.team2?.teamName || "Away"}`,
    ));
  }

  details.append(createElement("h3", "match-events-heading", "Goal timeline"));
  const goals = Array.isArray(match.goals)
    ? [...match.goals].sort((a, b) => (a.matchMinute ?? 0) - (b.matchMinute ?? 0))
    : [];

  if (goals.length) {
    const timeline = createElement("ol", "goal-timeline");
    for (const goal of goals) {
      const scoringTeamId = Number(goal.scoringTeamId);
      const goalTeam = scoringTeamId === Number(match.team1?.teamId)
        ? match.team1
        : scoringTeamId === Number(match.team2?.teamId)
          ? match.team2
          : null;
      const minute = goal.matchMinute !== null
        && goal.matchMinute !== undefined
        && Number.isFinite(Number(goal.matchMinute))
        ? `${goal.matchMinute}${goal.isOvertime ? "+" : ""}′`
        : "•";
      const notes = [
        goal.isOwnGoal ? "OG" : "",
        goal.isPenalty ? "Penalty" : "",
      ].filter(Boolean);
      const event = createElement("li", "goal-event");
      event.append(
        createElement("span", "goal-minute", minute),
        createElement("span", "goal-scorer", goal.goalGetterName || "Unknown scorer"),
        createElement(
          "span",
          "goal-team",
          `${goalTeam?.shortName || goalTeam?.teamName || "Team"}${notes.length ? ` · ${notes.join(", ")}` : ""}`,
        ),
      );
      timeline.append(event);
    }
    details.append(timeline);
  } else {
    const message = status === "finished"
      ? "No goal events are available for this match."
      : status === "live"
        ? "No goal events have been reported yet."
        : status === "pending"
          ? "Goal events are unavailable while the final result is pending."
        : "Goal events will appear here during the match.";
    details.append(createElement("p", "no-goals-message", message));
  }

  return details;
}

function renderMatches() {
  const filteredMatches = currentMatches
    .filter((match) => {
      const status = getMatchStatus(match);
      if (activeFilter === "all") return true;
      if (activeFilter === "finished") return status === "finished";
      if (activeFilter === "live") return status === "live";
      return status === "upcoming" || status === "pending";
    })
    .sort((a, b) => (
      Date.parse(a.matchDateTimeUTC ?? a.matchDateTime)
      - Date.parse(b.matchDateTimeUTC ?? b.matchDateTime)
    ));

  if (!filteredMatches.length) {
    const message = currentMatches.length
      ? "Try a different filter to see the matches for this matchday."
      : "There are no matches listed for this matchday yet.";
    showMessage("No matches to show", message);
    return;
  }

  const groups = new Map();
  for (const match of filteredMatches) {
    const dateKey = getMatchDateKey(match);
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey).push(match);
  }

  const fragment = document.createDocumentFragment();
  for (const [dateKey, matches] of groups) {
    const dateGroup = createElement("section", "date-group");
    const firstMatchDate = matches[0].matchDateTimeUTC ?? matches[0].matchDateTime;
    const heading = createElement("div", "date-heading");
    heading.append(
      createElement("span", "", formatBerlinDate(firstMatchDate, {
        weekday: "long",
        day: "numeric",
        month: "long",
      })),
      createElement("span", "", `${matches.length} ${matches.length === 1 ? "MATCH" : "MATCHES"}`),
    );
    dateGroup.append(heading, ...matches.map(createMatchCard));
    fragment.append(dateGroup);
  }
  resultsElement.replaceChildren(fragment);
}

function updateMatchdayControls() {
  matchdayTitle.textContent = `${selectedMatchday}${getOrdinalSuffix(selectedMatchday)} Matchday`;
  matchdaySelect.value = String(selectedMatchday);
  previousButton.disabled = selectedMatchday <= 1;
  nextButton.disabled = selectedMatchday >= MAX_MATCHDAYS;
}

function getOrdinalSuffix(number) {
  if (number % 100 >= 11 && number % 100 <= 13) return "th";
  return ({ 1: "st", 2: "nd", 3: "rd" })[number % 10] ?? "th";
}

function calculateStandings(matches, throughMatchday) {
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
      });
    }
    return table.get(team.teamId);
  }

  for (const match of matches) {
    const matchday = Number(match.group?.groupOrderID);
    if (!match.matchIsFinished || !Number.isInteger(matchday) || matchday > throughMatchday) continue;
    const result = match.matchResults?.find((item) => item.resultTypeKind === "After90Minutes");
    if (!result) continue;

    const home = getTeam(match.team1);
    const away = getTeam(match.team2);
    if (!home || !away) continue;

    const homeGoals = Number(result.pointsTeam1);
    const awayGoals = Number(result.pointsTeam2);
    if (!Number.isFinite(homeGoals) || !Number.isFinite(awayGoals)) continue;

    home.played += 1;
    away.played += 1;
    home.goalsFor += homeGoals;
    home.goalsAgainst += awayGoals;
    away.goalsFor += awayGoals;
    away.goalsAgainst += homeGoals;

    if (homeGoals > awayGoals) {
      home.won += 1;
      home.points += 3;
      away.lost += 1;
    } else if (homeGoals < awayGoals) {
      away.won += 1;
      away.points += 3;
      home.lost += 1;
    } else {
      home.drawn += 1;
      away.drawn += 1;
      home.points += 1;
      away.points += 1;
    }
  }

  return [...table.values()].sort((a, b) => (
    b.points - a.points
    || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst)
    || b.goalsFor - a.goalsFor
    || (a.team.shortName || a.team.teamName).localeCompare(b.team.shortName || b.team.teamName)
  ));
}

function renderStandings(matches, matchday) {
  standingsCaption.textContent = `After the ${matchday}${getOrdinalSuffix(matchday)} matchday · completed matches`;
  const table = calculateStandings(matches, matchday);
  if (!table.length) {
    const row = createElement("tr");
    const cell = createElement("td", "standings-message", "No completed matches through this matchday yet.");
    cell.colSpan = 9;
    row.append(cell);
    standingsRows.replaceChildren(row);
    return;
  }

  const fragment = document.createDocumentFragment();
  table.forEach((standing, index) => {
    const row = createElement("tr");
    const position = createElement("td", "position-column", String(index + 1));
    const clubCell = createElement("td", "club-column");
    const club = createElement("span", "standing-club");
    const logo = document.createElement("img");
    logo.className = "standing-logo";
    logo.src = standing.team.teamIconUrl || "";
    logo.alt = "";
    logo.loading = "lazy";
    logo.addEventListener("error", () => {
      logo.replaceWith(createElement(
        "span",
        "standing-logo-fallback",
        (standing.team.shortName || standing.team.teamName || "?").slice(0, 2),
      ));
    }, { once: true });
    club.append(logo, createElement("span", "standing-name", standing.team.shortName || standing.team.teamName || "Unknown team"));
    clubCell.append(club);

    const goalDifference = standing.goalsFor - standing.goalsAgainst;
    const cells = [
      position,
      clubCell,
      createElement("td", "", String(standing.played)),
      createElement("td", "", String(standing.won)),
      createElement("td", "", String(standing.drawn)),
      createElement("td", "", String(standing.lost)),
      createElement("td", "goal-total", `${standing.goalsFor}:${standing.goalsAgainst}`),
      createElement("td", "", `${goalDifference > 0 ? "+" : ""}${goalDifference}`),
      createElement("td", "points-column", String(standing.points)),
    ];
    row.append(...cells);
    fragment.append(row);
  });
  standingsRows.replaceChildren(fragment);
}

function showStandingsMessage(caption, message) {
  standingsCaption.textContent = caption;
  const row = createElement("tr");
  const cell = createElement("td", "standings-message", message);
  cell.colSpan = 9;
  row.append(cell);
  standingsRows.replaceChildren(row);
}

async function loadSeasonMatches(forceRefresh = false) {
  if (seasonMatches && !forceRefresh) return seasonMatches;

  const response = await fetch(`${API_BASE}/getmatchdata/${LEAGUE}/${season}`, {
    cache: forceRefresh ? "no-cache" : "default",
  });
  if (!response.ok) throw new Error(`OpenLigaDB returned HTTP ${response.status}.`);
  const matches = await response.json();
  if (!Array.isArray(matches)) throw new Error("OpenLigaDB returned an unexpected season match list.");
  seasonMatches = matches;
  return seasonMatches;
}

async function loadSelectedMatchday(forceRefresh = false) {
  const request = ++loadRequest;
  updateMatchdayControls();
  setLoading(true);
  resultsElement.replaceChildren(createLoadingState());

  try {
    const matches = await loadSeasonMatches(forceRefresh);
    if (request !== loadRequest) return;
    currentMatches = matches.filter((match) => Number(match.group?.groupOrderID) === selectedMatchday);
    renderMatches();
    renderStandings(matches, selectedMatchday);
  } catch (error) {
    if (request !== loadRequest) return;
    console.error("Unable to load Bundesliga results.", error);
    showMessage("Scores could not be loaded", "Please check your connection and try again.", true);
    showStandingsMessage("Standings unavailable", "Please refresh to load the match results.");
  } finally {
    if (request === loadRequest) setLoading(false);
  }
}

function createLoadingState() {
  const loading = createElement("div", "loading-state");
  const spinner = createElement("span", "loading-spinner");
  spinner.setAttribute("aria-hidden", "true");
  loading.append(spinner, createElement("p", "", "Finding the latest scores…"));
  return loading;
}

async function loadCurrentMatchday() {
  setLoading(true);
  try {
    const response = await fetch(`${API_BASE}/getcurrentgroup/${LEAGUE}`);
    if (!response.ok) throw new Error(`OpenLigaDB returned HTTP ${response.status}.`);
    const group = await response.json();
    const matchday = Number(group.groupOrderID);
    if (!Number.isInteger(matchday) || matchday < 1 || matchday > MAX_MATCHDAYS) {
      throw new Error("OpenLigaDB returned an invalid current matchday.");
    }
    selectedMatchday = matchday;
    updateMatchdayControls();
    await loadSelectedMatchday();
  } catch (error) {
    console.error("Unable to find the current Bundesliga matchday.", error);
    showMessage("Scores could not be loaded", "Please check your connection and try again.", true);
    showStandingsMessage("Standings unavailable", "Please refresh to load the match results.");
    setLoading(false);
  }
}

for (let day = 1; day <= MAX_MATCHDAYS; day += 1) {
  const option = document.createElement("option");
  option.value = String(day);
  option.textContent = String(day);
  matchdaySelect.append(option);
}

leagueSeason.textContent = `Bundesliga ${seasonLabel(season)}`;
document.querySelector("#standings-season").textContent = seasonLabel(season);
previousButton.addEventListener("click", () => {
  if (selectedMatchday > 1) {
    selectedMatchday -= 1;
    loadSelectedMatchday();
  }
});
nextButton.addEventListener("click", () => {
  if (selectedMatchday < MAX_MATCHDAYS) {
    selectedMatchday += 1;
    loadSelectedMatchday();
  }
});
matchdaySelect.addEventListener("change", () => {
  selectedMatchday = Number(matchdaySelect.value);
  loadSelectedMatchday();
});
refreshButton.addEventListener("click", () => loadSelectedMatchday(true));
filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    filterButtons.forEach((filterButton) => {
      const isActive = filterButton === button;
      filterButton.classList.toggle("is-active", isActive);
      filterButton.setAttribute("aria-pressed", String(isActive));
    });
    renderMatches();
  });
});

loadCurrentMatchday();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js")
      .catch((error) => console.error("Unable to enable offline app support.", error));
  });
}
