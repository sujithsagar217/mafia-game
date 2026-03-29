const appConfig = window.APP_CONFIG || {};
const gameMode = appConfig.game_mode || "dedicated-host";

let playerName = "";
let currentRole = null;
let roleLoaded = false;
let mafiaTeam = [];
let playerReady = false;

let currentPhase = "";
let actionRendered = false;
let voteRendered = false;
let suggestRendered = false;

let selectedVote = null;
let selectedAction = null;
let joinedGame = false;
let heartbeatTimerId = null;

const readyBtn = document.getElementById("readyBtn");
const openHostBtn = document.getElementById("openHostBtn");

document.getElementById("joinBtn").addEventListener("click", joinGame);
if (readyBtn) {
    readyBtn.addEventListener("click", toggleReady);
}
if (openHostBtn) {
    openHostBtn.addEventListener("click", openHostPanel);
}
window.addEventListener("pagehide", leaveGameSilently);
window.addEventListener("beforeunload", leaveGameSilently);

function joinGame() {
    playerName = document.getElementById("name").value.trim();
    if (!playerName) {
        return;
    }

    fetch("/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName })
    })
        .then((response) =>
            response.json().then((data) => ({
                ok: response.ok,
                data
            }))
        )
        .then(({ ok, data }) => {
            if (!ok) {
                joinedGame = false;
                showBanner(data.error || "Unable to join the game.");
                return;
            }

            joinedGame = true;
            document.getElementById("name").disabled = true;
            document.getElementById("joinBtn").disabled = true;

            if (readyBtn) {
                readyBtn.disabled = false;
            }

            document.getElementById("waitingBox").innerHTML = gameMode === "lobby-ready"
                ? '<div class="waiting-banner">Joined successfully. Mark yourself ready when you are set.</div>'
                : '<div class="waiting-banner">Joined successfully. Waiting for the host to start the game...</div>';

            startHeartbeat();
            updateUI();
        });
}

function updateUI() {
    if (!playerName) {
        return;
    }

    Promise.all([
        fetch("/lobby").then((res) => res.json()),
        fetch("/game_state").then((res) => res.json())
    ]).then(([lobby, state]) => {
        syncLobbyState(lobby, state);

        if (state.phase === "waiting") {
            roleLoaded = false;
            mafiaTeam = [];
            currentRole = null;

            document.getElementById("winner").innerText = "";
            resetUI();
            return;
        }

        document.getElementById("waitingBox").innerHTML = "";

        if (!roleLoaded) {
            fetch("/role/" + playerName)
                .then((r) => r.json())
                .then((data) => {
                    currentRole = data.role;
                    mafiaTeam = data.mafia_team || [];
                    roleLoaded = true;
                    renderRole();
                });
        }

        document.getElementById("round").innerText = "Round: " + state.round;
        document.getElementById("phase").innerText = "Phase: " + state.phase;

        renderList(state.alive, "alive");
        renderList(state.eliminated, "dead");
        handleDeadBanner(state);

        if (state.winner) {
            document.getElementById("winner").innerText = "Winner: " + state.winner;
            resetUI();
            return;
        }

        if (state.phase !== currentPhase) {
            currentPhase = state.phase;
            actionRendered = false;
            voteRendered = false;
            suggestRendered = false;
            selectedAction = null;
            selectedVote = null;
        }

        renderActions(state);
        renderSuggestions(state);
        renderVoting(state);
        renderLiveVotes(state);
        updatePoliceReportsVisibility();

        if (currentRole === "Police") {
            fetch("/police_reports/" + playerName)
                .then((r) => r.json())
                .then((data) => renderList(data, "reports"));
        }
    });
}

function syncLobbyState(lobby, state) {
    const hostNotice = document.getElementById("hostNotice");
    const players = gameMode === "lobby-ready"
        ? lobby.players.map((player) => {
            const readyState = lobby.ready[player] ? "Ready" : "Waiting";
            const hostTag = lobby.host_name === player ? " | Host" : "";
            return `${player} - ${readyState}${hostTag}`;
        })
        : lobby.players;

    renderList(players, "lobbyPlayers");

    if (gameMode === "lobby-ready") {
        playerReady = Boolean((lobby.ready || {})[playerName]);

        if (readyBtn) {
            readyBtn.disabled = !joinedGame || state.phase !== "waiting";
            readyBtn.innerText = playerReady ? "Not Ready Yet" : "I am Ready";
        }

        const readyHint = document.getElementById("readyHint");
        if (readyHint) {
            readyHint.innerText = joinedGame
                ? `${lobby.ready_count}/${lobby.players.length} players are ready.`
                : "Join first, then mark yourself ready.";
        }

        if (!lobby.host_name) {
            hostNotice.innerText = "Host will be assigned automatically when the match starts.";
            if (openHostBtn) {
                openHostBtn.classList.add("hidden");
            }
        } else if (lobby.host_name === playerName) {
            hostNotice.innerText = "You are the assigned host for this match. Use the button below to open the host controls.";
            if (openHostBtn) {
                openHostBtn.classList.remove("hidden");
            }
        } else {
            hostNotice.innerText = "Assigned host: " + lobby.host_name;
            if (openHostBtn) {
                openHostBtn.classList.add("hidden");
            }
        }

        if (state.phase !== "waiting") {
            document.getElementById("waitingBox").innerHTML =
                `<div class="waiting-banner">Game started. Assigned host: ${lobby.host_name || "-"}</div>`;
            return;
        }

        const missingPlayers = Math.max(0, lobby.minimum_players - lobby.players.length);
        if (missingPlayers > 0) {
            document.getElementById("waitingBox").innerHTML =
                `<div class="waiting-banner">Waiting for ${missingPlayers} more player${missingPlayers === 1 ? "" : "s"} to join.</div>`;
            return;
        }

        if (lobby.all_ready) {
            document.getElementById("waitingBox").innerHTML =
                '<div class="waiting-banner">Everyone is ready. Starting the match...</div>';
            return;
        }

        document.getElementById("waitingBox").innerHTML =
            '<div class="waiting-banner">Waiting for everyone in the lobby to click ready.</div>';
        return;
    }

    hostNotice.innerText = "A dedicated host controls this match from the host page.";

    if (state.phase !== "waiting") {
        document.getElementById("waitingBox").innerHTML =
            '<div class="waiting-banner">Game started. Follow the current phase and play your role.</div>';
        return;
    }

    const missingPlayers = Math.max(0, lobby.minimum_players - lobby.players.length);
    if (missingPlayers > 0) {
        document.getElementById("waitingBox").innerHTML =
            `<div class="waiting-banner">Waiting for ${missingPlayers} more player${missingPlayers === 1 ? "" : "s"} to join.</div>`;
        return;
    }

    document.getElementById("waitingBox").innerHTML =
        '<div class="waiting-banner">Waiting for the host to start the game...</div>';
}

function renderRole() {
    if (!currentRole) {
        return;
    }

    document.getElementById("role").innerText = "Role: " + currentRole;
    document.getElementById("mafiaTeam").innerText = "";
    updatePoliceReportsVisibility();

    if (currentRole === "Mafia") {
        document.getElementById("mafiaTeam").innerText =
            mafiaTeam.length ? "Team: " + mafiaTeam.join(", ") : "";
    } else if (currentRole === "Host") {
        document.getElementById("mafiaTeam").innerText =
            "You are moderating this match. Use the host panel to run the phases.";
    }
}

function renderActions(state) {
    const box = document.getElementById("actionBox");
    if (actionRendered) {
        return;
    }

    box.innerHTML = "";

    if (state.phase !== "night" || !state.alive.includes(playerName)) {
        return;
    }

    let targets = state.alive;

    if (currentRole !== "Doctor") {
        targets = targets.filter((player) => player !== playerName);
    }

    if (currentRole === "Mafia") {
        targets = targets.filter((player) => !mafiaTeam.includes(player));
    }

    if (!["Doctor", "Police", "Mafia"].includes(currentRole)) {
        return;
    }

    if (targets.length === 0) {
        box.innerHTML = "<h3>No valid targets</h3>";
        return;
    }

    const text = {
        Doctor: "Save",
        Police: "Investigate",
        Mafia: "Kill"
    };

    box.innerHTML = `
        <h3>${text[currentRole]}</h3>
        <select id="target">
            ${targets.map((player) => `<option value="${player}">${player}</option>`).join("")}
        </select>
        <button id="actionSubmitBtn" type="button">${text[currentRole]}</button>
    `;

    document
        .getElementById("actionSubmitBtn")
        .addEventListener("click", submitAction);

    actionRendered = true;
}

function renderSuggestions(state) {
    const box = document.getElementById("suggestBox");

    if (state.phase !== "night" || currentRole !== "Mafia" || !state.alive.includes(playerName)) {
        box.innerHTML = "";
        return;
    }

    if (!suggestRendered) {
        let targets = state.alive.filter((player) => player !== playerName);
        targets = targets.filter((player) => !mafiaTeam.includes(player));

        box.innerHTML = `
            <h3>Suggest Target</h3>
            <select id="suggestTarget">
                ${targets.map((player) => `<option value="${player}">${player}</option>`).join("")}
            </select>
            <button id="suggestBtn" type="button">Suggest</button>
            <ul id="suggestList"></ul>
        `;

        document.getElementById("suggestBtn").addEventListener("click", submitSuggestion);
        suggestRendered = true;
    }

    fetch("/suggestions/" + playerName)
        .then((r) => r.json())
        .then((data) => {
            const list = document.getElementById("suggestList");
            if (!list) {
                return;
            }

            list.innerHTML = "";

            Object.keys(data).forEach((mafiaPlayer) => {
                list.innerHTML += `<li>${mafiaPlayer} -> ${data[mafiaPlayer]}</li>`;
            });
        });
}

function submitSuggestion() {
    const target = document.getElementById("suggestTarget").value;

    fetch("/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName, target })
    });
}

function renderVoting(state) {
    const box = document.getElementById("voteBox");
    if (voteRendered) {
        return;
    }

    box.innerHTML = "";

    if (state.phase !== "voting" || !state.alive.includes(playerName)) {
        return;
    }

    const targets = state.alive.filter((player) => player !== playerName);

    if (targets.length === 0) {
        box.innerHTML = "<h3>No valid targets</h3>";
        return;
    }

    box.innerHTML = `
        <h3>Vote</h3>
        <select id="voteTarget">
            ${targets
                .map(
                    (player) =>
                        `<option value="${player}" ${selectedVote === player ? "selected" : ""}>${player}</option>`
                )
                .join("")}
        </select>
        <button id="voteSubmitBtn" type="button">Vote</button>
    `;

    document.getElementById("voteSubmitBtn").addEventListener("click", submitVote);
    voteRendered = true;
}

function renderLiveVotes(state) {
    const box = document.getElementById("liveVoteBox");

    if (state.phase !== "voting") {
        hideLiveVotes();
        return;
    }

    box.classList.remove("hidden");

    fetch("/votes")
        .then((r) => r.json())
        .then((data) => {
            const counts = Object.keys(data.counts || {});
            const voters = Object.keys(data.individual || {});

            renderList(
                counts.length
                    ? counts.map((target) => `${target} -> ${data.counts[target]}`)
                    : ["No votes yet"],
                "liveVoteCounts"
            );

            renderList(
                voters.length
                    ? voters.map((voter) => `${voter} -> ${data.individual[voter]}`)
                    : ["No votes submitted yet"],
                "liveVoteDetails"
            );
        });
}

function hideLiveVotes() {
    document.getElementById("liveVoteBox").classList.add("hidden");
    renderList([], "liveVoteCounts");
    renderList([], "liveVoteDetails");
}

function updatePoliceReportsVisibility() {
    const policeBox = document.getElementById("policeBox");
    if (currentRole === "Police") {
        policeBox.classList.remove("hidden");
    } else {
        policeBox.classList.add("hidden");
        renderList([], "reports");
    }
}

function showBanner(message) {
    document.getElementById("waitingBox").innerHTML =
        `<div class="dead-banner">${message}</div>`;
}

function toggleReady() {
    fetch("/ready", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName, ready: !playerReady })
    })
        .then((response) =>
            response.json().then((data) => ({
                ok: response.ok,
                data
            }))
        )
        .then(({ ok, data }) => {
            if (!ok) {
                showBanner(data.error || "Unable to update readiness.");
                return;
            }

            playerReady = Boolean(data.ready);
            updateUI();
        });
}

function openHostPanel() {
    const hostUrl = `/host?player_name=${encodeURIComponent(playerName)}`;
    window.open(hostUrl, "_blank", "noopener");
}

function leaveGameSilently() {
    if (!joinedGame || !playerName) {
        return;
    }

    const payload = JSON.stringify({ name: playerName });
    navigator.sendBeacon("/leave", new Blob([payload], { type: "application/json" }));
}

function sendHeartbeat() {
    if (!joinedGame || !playerName) {
        return;
    }

    fetch("/heartbeat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName })
    }).catch(() => {});
}

function startHeartbeat() {
    if (heartbeatTimerId !== null) {
        clearInterval(heartbeatTimerId);
    }

    sendHeartbeat();
    heartbeatTimerId = window.setInterval(sendHeartbeat, 5000);
}

function submitAction() {
    const target = document.getElementById("target").value;
    selectedAction = target;

    fetch("/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName, target })
    });
}

function submitVote() {
    const target = document.getElementById("voteTarget").value;
    selectedVote = target;

    fetch("/vote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: playerName, target })
    });
}

function handleDeadBanner(state) {
    const banner = document.getElementById("deadBanner");
    if (currentRole === "Host") {
        banner.innerHTML = "";
        return;
    }

    banner.innerHTML = state.alive.includes(playerName)
        ? ""
        : '<div class="dead-banner">You are eliminated.</div>';
}

function renderList(list, id) {
    const ul = document.getElementById(id);
    ul.innerHTML = "";
    list.forEach((item) => {
        const li = document.createElement("li");
        li.innerText = item;
        ul.appendChild(li);
    });
}

function resetUI() {
    document.getElementById("round").innerText = "";
    document.getElementById("phase").innerText = "";
    document.getElementById("role").innerText = "";
    document.getElementById("mafiaTeam").innerText = "";
    document.getElementById("actionBox").innerHTML = "";
    document.getElementById("voteBox").innerHTML = "";
    document.getElementById("suggestBox").innerHTML = "";
    document.getElementById("deadBanner").innerHTML = "";
    hideLiveVotes();
    updatePoliceReportsVisibility();
}

setInterval(updateUI, 2000);
