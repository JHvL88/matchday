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
const filterButtons = [...document.querySelectorAll("[data-filter]")];

const currentDate = new Date();
const season = currentDate.getMonth() >= 6
  ? currentDate.getFullYear()
  : currentDate.getFullYear() - 1;
let selectedMatchday = 1;
let activeFilter = "all";
let currentMatches = [];
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
  const container = createElement("div", `team ${isHome ? "team-home" : "team-away"}`);
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
  const card = createElement("article", "match-card");
  const score = getScore(match);
  const status = getMatchStatus(match);
  const [homeScore, awayScore] = score ?? [];
  const homeWon = score && homeScore > awayScore;
  const awayWon = score && awayScore > homeScore;
  const time = formatBerlinDate(match.matchDateTimeUTC ?? match.matchDateTime, {
    hour: "2-digit",
    minute: "2-digit",
  });

  card.append(
    createTeam(match.team1 ?? {}, true, homeWon),
  );

  const scoreBlock = createElement("div", "score-block");
  if (score) {
    const scoreLine = createElement("div", "score");
    const home = createElement("span", homeWon ? "score-winner" : "", String(homeScore));
    const separator = createElement("span", "score-separator", "–");
    const away = createElement("span", awayWon ? "score-winner" : "", String(awayScore));
    scoreLine.append(home, separator, away);
    scoreBlock.append(scoreLine);
  } else {
    scoreBlock.append(createElement("div", "match-time", time));
  }

  const statusLabel = status === "finished"
    ? "FULL TIME"
    : status === "live"
      ? "IN PROGRESS"
      : status === "pending"
        ? "RESULT PENDING"
        : "KICK-OFF";
  const statusElement = createElement("div", `match-status${status === "live" ? " is-live" : ""}${status === "finished" ? " is-finished" : ""}`, statusLabel);
  scoreBlock.append(statusElement);
  card.append(scoreBlock, createTeam(match.team2 ?? {}, false, awayWon));
  return card;
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

async function loadSelectedMatchday() {
  const request = ++loadRequest;
  updateMatchdayControls();
  setLoading(true);
  resultsElement.replaceChildren(createLoadingState());

  try {
    const response = await fetch(`${API_BASE}/getmatchdata/${LEAGUE}/${season}/${selectedMatchday}`);
    if (!response.ok) throw new Error(`OpenLigaDB returned HTTP ${response.status}.`);
    const matches = await response.json();
    if (!Array.isArray(matches)) throw new Error("OpenLigaDB returned an unexpected match list.");
    if (request !== loadRequest) return;
    currentMatches = matches;
    renderMatches();
  } catch (error) {
    if (request !== loadRequest) return;
    console.error("Unable to load Bundesliga results.", error);
    showMessage("Scores could not be loaded", "Please check your connection and try again.", true);
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
refreshButton.addEventListener("click", loadSelectedMatchday);
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
